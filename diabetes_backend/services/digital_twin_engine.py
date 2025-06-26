"""
Digital Twin Simulation Engine για What-If Scenarios
================================================

Ακριβή φαρμακοκινητικά/φαρμακοδυναμικά models για diabetes management.
Βασίζεται στα πραγματικά patient data και παράγει realistic scenarios.
"""

import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import json
import asyncio

# Mathematical models
from scipy.integrate import odeint
from scipy.optimize import minimize_scalar

logger = logging.getLogger(__name__)


@dataclass
class PatientProfile:
    """Patient-specific parameters for digital twin"""
    weight_kg: float
    height_cm: float
    age: int
    diabetes_type: str  # "T1" or "T2"
    
    # Insulin sensitivity factors (derived from patient data)
    insulin_sensitivity: float  # mg/dL per unit
    carb_ratio: float  # grams per unit
    correction_factor: float  # mg/dL per unit
    basal_rate: float  # units per hour
    
    # Physiological parameters
    glucose_absorption_rate: float = 0.3  # per hour
    insulin_absorption_rate: float = 0.15  # per hour
    liver_glucose_production: float = 2.0  # mg/dL per hour
    glucose_clearance_rate: float = 0.05  # per hour


@dataclass
class ScenarioParams:
    """What-if scenario parameters"""
    # Insulin adjustments (as percentages)
    basal_change: float = 0.0  # +/- percentage
    bolus_change: float = 0.0  # +/- percentage
    carb_ratio_change: float = 0.0  # +/- percentage
    correction_factor_change: float = 0.0  # +/- percentage
    
    # Meal and activity changes
    meal_carbs: float = 60.0  # grams
    meal_timing: int = 60  # minutes from now
    exercise_intensity: float = 0.0  # 0-100%
    exercise_duration: int = 0  # minutes
    
    # Simulation parameters
    simulation_hours: int = 24
    time_step_minutes: int = 15


@dataclass
class SimulationResult:
    """Results from digital twin simulation"""
    time_points: List[float]  # hours
    glucose_levels: List[float]  # mg/dL
    insulin_levels: List[float]  # units
    risk_scores: Dict[str, float]
    safety_alerts: List[str]
    recommendations: List[str]
    glucose_metrics: Dict[str, float]
    scenario_summary: Dict[str, Any]


class DiabetesPharmacokineticModel:
    """
    Advanced pharmacokinetic/pharmacodynamic model για insulin και glucose dynamics
    """
    
    def __init__(self, patient_profile: PatientProfile):
        self.patient = patient_profile
        
        # Model parameters based on patient characteristics
        self.Ka_insulin = 0.15  # Insulin absorption rate (1/hour)
        self.Ke_insulin = 0.12  # Insulin elimination rate (1/hour)
        self.Ka_glucose = 0.3   # Glucose absorption rate (1/hour)
        
        # Patient-specific adjustments
        if patient_profile.diabetes_type == "T2":
            self.insulin_resistance_factor = 1.5
        else:
            self.insulin_resistance_factor = 1.0
            
        # Age and weight adjustments
        self.age_factor = 1.0 + (patient_profile.age - 40) * 0.005
        self.weight_factor = patient_profile.weight_kg / 70.0  # normalized to 70kg
    
    def glucose_insulin_ode(self, state: List[float], t: float, 
                           insulin_input: float, glucose_input: float,
                           exercise_effect: float = 0.0) -> List[float]:
        """
        Differential equations για glucose-insulin dynamics
        
        State variables:
        [0] Plasma glucose (mg/dL)
        [1] Plasma insulin (mU/L)
        [2] Subcutaneous insulin depot (units)
        [3] Interstitial glucose (mg/dL)
        """
        glucose, insulin, insulin_depot, glucose_interstitial = state
        
        # Insulin kinetics
        insulin_absorption = self.Ka_insulin * insulin_depot
        insulin_elimination = self.Ke_insulin * insulin
        
        # Glucose production and utilization
        hepatic_glucose_production = self.patient.liver_glucose_production * (1 - insulin * 0.01)
        glucose_utilization = (glucose * self.patient.glucose_clearance_rate * 
                              (1 + insulin * 0.02) * (1 + exercise_effect))
        
        # Exercise effects
        exercise_glucose_uptake = exercise_effect * glucose * 0.1
        
        # Differential equations
        dglucose_dt = (hepatic_glucose_production - glucose_utilization - 
                      exercise_glucose_uptake + glucose_input)
        
        dinsulin_dt = insulin_absorption - insulin_elimination
        
        dinsulin_depot_dt = insulin_input - insulin_absorption
        
        dglucose_interstitial_dt = self.Ka_glucose * (glucose - glucose_interstitial)
        
        return [dglucose_dt, dinsulin_dt, dinsulin_depot_dt, dglucose_interstitial_dt]
    
    def simulate_scenario(self, initial_state: List[float], 
                         scenario: ScenarioParams,
                         current_vitals: Dict[str, Any]) -> SimulationResult:
        """
        Simulate glucose-insulin dynamics για specific scenario
        """
        
        # Time grid
        total_minutes = scenario.simulation_hours * 60
        time_minutes = np.arange(0, total_minutes + 1, scenario.time_step_minutes)
        time_hours = time_minutes / 60.0
        
        # Adjusted patient parameters based on scenario
        adjusted_basal = self.patient.basal_rate * (1 + scenario.basal_change / 100)
        adjusted_carb_ratio = self.patient.carb_ratio * (1 + scenario.carb_ratio_change / 100)
        adjusted_correction = self.patient.correction_factor * (1 + scenario.correction_factor_change / 100)
        
        # Initialize arrays for inputs
        insulin_inputs = np.zeros_like(time_minutes, dtype=float)
        glucose_inputs = np.zeros_like(time_minutes, dtype=float)
        exercise_effects = np.zeros_like(time_minutes, dtype=float)
        
        # Basal insulin (continuous)
        basal_per_timestep = adjusted_basal * (scenario.time_step_minutes / 60.0)
        insulin_inputs[:] = basal_per_timestep
        
        # Meal bolus
        if scenario.meal_carbs > 0:
            meal_timestep = int(scenario.meal_timing / scenario.time_step_minutes)
            if meal_timestep < len(insulin_inputs):
                # Bolus insulin
                meal_bolus = scenario.meal_carbs / adjusted_carb_ratio
                meal_bolus *= (1 + scenario.bolus_change / 100)
                insulin_inputs[meal_timestep] += meal_bolus
                
                # Glucose from meal (absorbed over time)
                absorption_timesteps = int(180 / scenario.time_step_minutes)  # 3 hours
                for i in range(absorption_timesteps):
                    if meal_timestep + i < len(glucose_inputs):
                        glucose_per_timestep = (scenario.meal_carbs * 4 / absorption_timesteps)  # 4 mg/dL per gram
                        glucose_inputs[meal_timestep + i] += glucose_per_timestep
        
        # Exercise effects
        if scenario.exercise_duration > 0:
            exercise_start = int(120 / scenario.time_step_minutes)  # Start after 2 hours
            exercise_timesteps = int(scenario.exercise_duration / scenario.time_step_minutes)
            exercise_intensity_factor = scenario.exercise_intensity / 100.0
            
            for i in range(exercise_timesteps):
                if exercise_start + i < len(exercise_effects):
                    exercise_effects[exercise_start + i] = exercise_intensity_factor
        
        # Solve ODE system
        solution = []
        current_state = initial_state.copy()
        
        for i, t in enumerate(time_hours):
            if i == 0:
                solution.append(current_state.copy())
                continue
            
            # Time span for this step
            t_span = [time_hours[i-1], t]
            
            # Solve ODE for this timestep
            try:
                result = odeint(
                    self.glucose_insulin_ode, 
                    current_state, 
                    t_span,
                    args=(insulin_inputs[i], glucose_inputs[i], exercise_effects[i])
                )
                current_state = result[-1]
                solution.append(current_state.copy())
                
            except Exception as e:
                logger.error(f"ODE integration error at t={t}: {e}")
                # Use previous state if integration fails
                solution.append(current_state.copy())
        
        # Extract results
        solution = np.array(solution)
        glucose_levels = solution[:, 0].tolist()
        insulin_levels = solution[:, 1].tolist()
        
        # Calculate glucose metrics
        glucose_metrics = self._calculate_glucose_metrics(glucose_levels, time_hours.tolist())
        
        # Risk assessment
        risk_scores = self._assess_scenario_risks(glucose_levels, insulin_levels, scenario)
        
        # Safety alerts
        safety_alerts = self._generate_safety_alerts(glucose_levels, insulin_levels, scenario)
        
        # Recommendations
        recommendations = self._generate_recommendations(glucose_metrics, risk_scores, scenario)
        
        # Scenario summary
        scenario_summary = {
            "parameters": asdict(scenario),
            "adjusted_basal": adjusted_basal,
            "adjusted_carb_ratio": adjusted_carb_ratio,
            "meal_bolus": scenario.meal_carbs / adjusted_carb_ratio if scenario.meal_carbs > 0 else 0,
            "total_insulin": sum(insulin_inputs),
            "peak_glucose": max(glucose_levels),
            "min_glucose": min(glucose_levels)
        }
        
        return SimulationResult(
            time_points=time_hours.tolist(),
            glucose_levels=glucose_levels,
            insulin_levels=insulin_levels,
            risk_scores=risk_scores,
            safety_alerts=safety_alerts,
            recommendations=recommendations,
            glucose_metrics=glucose_metrics,
            scenario_summary=scenario_summary
        )
    
    def _calculate_glucose_metrics(self, glucose_levels: List[float], time_hours: List[float]) -> Dict[str, float]:
        """Calculate standard glucose metrics"""
        glucose_array = np.array(glucose_levels)
        
        # Time in range calculations
        tir_70_180 = np.sum((glucose_array >= 70) & (glucose_array <= 180)) / len(glucose_array) * 100
        tir_70_140 = np.sum((glucose_array >= 70) & (glucose_array <= 140)) / len(glucose_array) * 100
        time_below_70 = np.sum(glucose_array < 70) / len(glucose_array) * 100
        time_above_180 = np.sum(glucose_array > 180) / len(glucose_array) * 100
        time_above_250 = np.sum(glucose_array > 250) / len(glucose_array) * 100
        
        # Glucose variability
        cv = (np.std(glucose_array) / np.mean(glucose_array)) * 100 if np.mean(glucose_array) > 0 else 0
        
        # Mean glucose
        mean_glucose = np.mean(glucose_array)
        
        # Estimated HbA1c (using Nathan formula)
        estimated_hba1c = (mean_glucose + 46.7) / 28.7
        
        return {
            "mean_glucose": float(mean_glucose),
            "glucose_cv": float(cv),
            "estimated_hba1c": float(estimated_hba1c),
            "tir_70_180": float(tir_70_180),
            "tir_70_140": float(tir_70_140),
            "time_below_70": float(time_below_70),
            "time_above_180": float(time_above_180),
            "time_above_250": float(time_above_250),
            "peak_glucose": float(np.max(glucose_array)),
            "min_glucose": float(np.min(glucose_array))
        }
    
    def _assess_scenario_risks(self, glucose_levels: List[float], 
                              insulin_levels: List[float], 
                              scenario: ScenarioParams) -> Dict[str, float]:
        """Assess risks for the simulated scenario"""
        glucose_array = np.array(glucose_levels)
        
        # Hypoglycemia risk
        severe_hypo_risk = np.sum(glucose_array < 54) / len(glucose_array) * 100
        mild_hypo_risk = np.sum(glucose_array < 70) / len(glucose_array) * 100
        
        # Hyperglycemia risk
        mild_hyper_risk = np.sum(glucose_array > 180) / len(glucose_array) * 100
        severe_hyper_risk = np.sum(glucose_array > 250) / len(glucose_array) * 100
        
        # Variability risk (high CV is dangerous)
        cv = (np.std(glucose_array) / np.mean(glucose_array)) * 100
        variability_risk = min(100, max(0, (cv - 30) * 2))  # Risk increases above 30% CV
        
        # Overall risk score
        overall_risk = (severe_hypo_risk * 3 + mild_hypo_risk * 2 + 
                       severe_hyper_risk * 2 + mild_hyper_risk + 
                       variability_risk) / 9
        
        return {
            "hypoglycemia_risk": float(mild_hypo_risk),
            "severe_hypoglycemia_risk": float(severe_hypo_risk),
            "hyperglycemia_risk": float(mild_hyper_risk),
            "severe_hyperglycemia_risk": float(severe_hyper_risk),
            "variability_risk": float(variability_risk),
            "overall_risk": float(min(100, overall_risk))
        }
    
    def _generate_safety_alerts(self, glucose_levels: List[float], 
                               insulin_levels: List[float], 
                               scenario: ScenarioParams) -> List[str]:
        """Generate safety alerts based on simulation results"""
        alerts = []
        glucose_array = np.array(glucose_levels)
        
        # Critical hypoglycemia
        if np.min(glucose_array) < 54:
            alerts.append("⚠️ ΚΡΙΤΙΚΟΣ ΚΙΝΔΥΝΟΣ: Σοβαρή υπογλυκαιμία (<54 mg/dL) προβλέπεται")
        
        # Severe hyperglycemia
        if np.max(glucose_array) > 300:
            alerts.append("⚠️ ΚΡΙΤΙΚΟΣ ΚΙΝΔΥΝΟΣ: Σοβαρή υπεργλυκαιμία (>300 mg/dL) προβλέπεται")
        
        # Excessive insulin
        total_insulin = scenario.meal_carbs / self.patient.carb_ratio if scenario.meal_carbs > 0 else 0
        daily_basal = self.patient.basal_rate * 24 * (1 + scenario.basal_change / 100)
        total_daily_insulin = daily_basal + total_insulin
        
        if total_daily_insulin > self.patient.weight_kg * 1.5:  # >1.5 units/kg is high
            alerts.append("⚠️ ΠΡΟΣΟΧΗ: Υψηλή συνολική δόση ινσουλίνης - κίνδυνος υπογλυκαιμίας")
        
        # Large parameter changes
        if abs(scenario.basal_change) > 50:
            alerts.append("⚠️ ΠΡΟΣΟΧΗ: Μεγάλη αλλαγή βασικής ινσουλίνης (>50%) - απαιτείται προσεκτική παρακολούθηση")
        
        if abs(scenario.bolus_change) > 50:
            alerts.append("⚠️ ΠΡΟΣΟΧΗ: Μεγάλη αλλαγή bolus ινσουλίνης (>50%) - κίνδυνος υπο/υπεργλυκαιμίας")
        
        return alerts
    
    def _generate_recommendations(self, glucose_metrics: Dict[str, float], 
                                 risk_scores: Dict[str, float], 
                                 scenario: ScenarioParams) -> List[str]:
        """Generate clinical recommendations based on simulation"""
        recommendations = []
        
        # Time in range recommendations
        if glucose_metrics["tir_70_180"] < 70:
            recommendations.append("📊 Στόχος: Βελτίωση Time in Range (70-180 mg/dL) - τρέχον " + 
                                 f"{glucose_metrics['tir_70_180']:.1f}%, στόχος >70%")
        
        # Hypoglycemia prevention
        if risk_scores["hypoglycemia_risk"] > 10:
            recommendations.append("🔽 Μείωση κινδύνου υπογλυκαιμίας: Σκεφτείτε μείωση δόσης ινσουλίνης ή " +
                                 "αύξηση πρόσληψης υδατανθράκων")
        
        # Hyperglycemia management
        if risk_scores["hyperglycemia_risk"] > 20:
            recommendations.append("🔼 Βελτίωση γλυκαιμικού ελέγχου: Εξετάστε αύξηση ινσουλίνης ή " +
                                 "μείωση υδατανθράκων")
        
        # Variability reduction
        if glucose_metrics["glucose_cv"] > 36:
            recommendations.append("📈 Μείωση γλυκαιμικής μεταβλητότητας: Σταθεροποίηση χρόνων γευμάτων " +
                                 "και δόσεων ινσουλίνης")
        
        # Exercise benefits
        if scenario.exercise_intensity == 0:
            recommendations.append("🏃‍♂️ Η προσθήκη ήπιας άσκησης μπορεί να βελτιώσει τον γλυκαιμικό έλεγχο")
        
        # Optimal ranges achieved
        if glucose_metrics["tir_70_180"] > 80 and risk_scores["overall_risk"] < 20:
            recommendations.append("✅ Εξαιρετικός γλυκαιμικός έλεγχος - συνεχίστε το τρέχον σχήμα")
        
        return recommendations


class DigitalTwinEngine:
    """
    Main Digital Twin Engine που ενσωματώνει όλα τα components
    """
    
    def __init__(self):
        self.pk_models = {}  # Cache για patient-specific models
    
    def create_patient_profile(self, patient_data: Dict[str, Any]) -> PatientProfile:
        """Create patient profile from real patient data"""
        
        # Extract measurements
        measurements = patient_data.get('measurements', [])
        personal_details = patient_data.get('personal_details', {})
        medical_profile = patient_data.get('medical_profile', {})
        
        # Get latest measurements
        latest_measurements = {}
        if measurements:
            latest = measurements[-1]
            latest_measurements = {
                'weight_kg': latest.get('weight_kg'),
                'bmi': latest.get('bmi'),
                'hba1c': latest.get('hba1c')
            }
        
        # Determine diabetes type
        conditions = medical_profile.get('conditions', [])
        diabetes_type = "T2"  # Default
        for condition in conditions:
            condition_name = condition.get('condition_name', '').lower()
            if 'τύπου 1' in condition_name or 'type 1' in condition_name:
                diabetes_type = "T1"
                break
        
        # Calculate age
        age = 40  # Default
        if personal_details.get('date_of_birth'):
            try:
                from datetime import datetime
                birth_date = datetime.fromisoformat(personal_details['date_of_birth'].replace('Z', '+00:00'))
                age = (datetime.now() - birth_date).days // 365
            except:
                pass
        
        # Estimate patient-specific parameters from data
        weight_kg = latest_measurements.get('weight_kg', 70.0)
        height_cm = medical_profile.get('height_cm', 170.0)
        
        # Insulin parameters (estimated based on patient characteristics)
        if diabetes_type == "T1":
            basal_rate = weight_kg * 0.4 / 24  # ~0.4 units/kg/day basal
            insulin_sensitivity = 50.0  # mg/dL per unit
            carb_ratio = 15.0  # grams per unit
            correction_factor = 50.0  # mg/dL per unit
        else:  # T2
            basal_rate = weight_kg * 0.6 / 24  # ~0.6 units/kg/day basal
            insulin_sensitivity = 30.0  # Lower sensitivity
            carb_ratio = 10.0  # More insulin needed
            correction_factor = 30.0  # mg/dL per unit
        
        # Adjust based on HbA1c if available
        if latest_measurements.get('hba1c'):
            hba1c = float(latest_measurements['hba1c'])
            if hba1c > 8.0:  # Poor control - may need more insulin
                insulin_sensitivity *= 0.8
                correction_factor *= 0.8
            elif hba1c < 6.5:  # Tight control - more sensitive
                insulin_sensitivity *= 1.2
                correction_factor *= 1.2
        
        return PatientProfile(
            weight_kg=weight_kg,
            height_cm=height_cm,
            age=age,
            diabetes_type=diabetes_type,
            insulin_sensitivity=insulin_sensitivity,
            carb_ratio=carb_ratio,
            correction_factor=correction_factor,
            basal_rate=basal_rate
        )
    
    def get_current_state(self, patient_data: Dict[str, Any]) -> List[float]:
        """Estimate current physiological state from patient data"""
        
        measurements = patient_data.get('measurements', [])
        
        # Default initial state
        initial_glucose = 120.0  # mg/dL
        initial_insulin = 10.0   # mU/L
        initial_insulin_depot = 0.0  # units
        initial_glucose_interstitial = 120.0  # mg/dL
        
        # Use latest glucose measurement if available
        if measurements:
            latest = measurements[-1]
            if latest.get('blood_glucose_level'):
                initial_glucose = float(latest['blood_glucose_level'])
                initial_glucose_interstitial = initial_glucose
        
        return [initial_glucose, initial_insulin, initial_insulin_depot, initial_glucose_interstitial]
    
    async def simulate_what_if_scenario(self, patient_data: Dict[str, Any], 
                                      scenario_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main function για What-If scenario simulation
        """
        
        try:
            # Create patient profile
            patient_profile = self.create_patient_profile(patient_data)
            
            # Create pharmacokinetic model
            pk_model = DiabetesPharmacokineticModel(patient_profile)
            
            # Get current physiological state
            initial_state = self.get_current_state(patient_data)
            
            # Create scenario parameters
            scenario = ScenarioParams(**scenario_params)
            
            # Run simulation
            result = pk_model.simulate_scenario(initial_state, scenario, patient_data)
            
            # Format results for frontend
            formatted_result = {
                "success": True,
                "patient_profile": asdict(patient_profile),
                "simulation_results": {
                    "time_points": result.time_points,
                    "glucose_levels": result.glucose_levels,
                    "insulin_levels": result.insulin_levels,
                    "glucose_metrics": result.glucose_metrics,
                    "risk_scores": result.risk_scores,
                    "safety_alerts": result.safety_alerts,
                    "recommendations": result.recommendations,
                    "scenario_summary": result.scenario_summary
                },
                "mindmap_data": self._create_mindmap_data(result, scenario),
                "comparison_data": self._create_comparison_data(result, patient_data)
            }
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"Digital twin simulation error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Σφάλμα κατά την προσομοίωση. Παρακαλώ δοκιμάστε ξανά."
            }
    
    def _create_mindmap_data(self, result: SimulationResult, scenario: ScenarioParams) -> Dict[str, Any]:
        """Create mindmap data structure for visualization"""
        
        # Central node
        mindmap = {
            "id": "scenario_root",
            "label": "What-If Scenario",
            "type": "root",
            "data": {
                "peak_glucose": result.scenario_summary["peak_glucose"],
                "min_glucose": result.scenario_summary["min_glucose"],
                "overall_risk": result.risk_scores["overall_risk"]
            },
            "children": []
        }
        
        # Parameters node
        params_node = {
            "id": "parameters",
            "label": "Παράμετροι",
            "type": "category",
            "data": {"icon": "⚙️"},
            "children": []
        }
        
        if scenario.basal_change != 0:
            params_node["children"].append({
                "id": "basal",
                "label": f"Βασική Ινσουλίνη {scenario.basal_change:+.1f}%",
                "type": "parameter",
                "data": {"value": scenario.basal_change, "color": "#2196f3"}
            })
        
        if scenario.bolus_change != 0:
            params_node["children"].append({
                "id": "bolus",
                "label": f"Bolus Ινσουλίνη {scenario.bolus_change:+.1f}%",
                "type": "parameter",
                "data": {"value": scenario.bolus_change, "color": "#ff9800"}
            })
        
        if scenario.meal_carbs > 0:
            params_node["children"].append({
                "id": "meal",
                "label": f"Γεύμα {scenario.meal_carbs}g",
                "type": "parameter",
                "data": {"value": scenario.meal_carbs, "color": "#4caf50"}
            })
        
        mindmap["children"].append(params_node)
        
        # Outcomes node
        outcomes_node = {
            "id": "outcomes",
            "label": "Αποτελέσματα",
            "type": "category",
            "data": {"icon": "📊"},
            "children": [
                {
                    "id": "tir",
                    "label": f"Time in Range: {result.glucose_metrics['tir_70_180']:.1f}%",
                    "type": "outcome",
                    "data": {
                        "value": result.glucose_metrics["tir_70_180"],
                        "color": "#4caf50" if result.glucose_metrics["tir_70_180"] > 70 else "#ff9800"
                    }
                },
                {
                    "id": "mean_glucose",
                    "label": f"Μέση Γλυκόζη: {result.glucose_metrics['mean_glucose']:.0f} mg/dL",
                    "type": "outcome",
                    "data": {
                        "value": result.glucose_metrics["mean_glucose"],
                        "color": "#2196f3"
                    }
                },
                {
                    "id": "variability",
                    "label": f"Μεταβλητότητα: {result.glucose_metrics['glucose_cv']:.1f}%",
                    "type": "outcome",
                    "data": {
                        "value": result.glucose_metrics["glucose_cv"],
                        "color": "#ff9800" if result.glucose_metrics["glucose_cv"] > 36 else "#4caf50"
                    }
                }
            ]
        }
        
        mindmap["children"].append(outcomes_node)
        
        # Risks node
        risks_node = {
            "id": "risks",
            "label": "Κίνδυνοι",
            "type": "category",
            "data": {"icon": "⚠️"},
            "children": []
        }
        
        for risk_name, risk_value in result.risk_scores.items():
            if risk_value > 5:  # Only show significant risks
                risks_node["children"].append({
                    "id": f"risk_{risk_name}",
                    "label": f"{risk_name.replace('_', ' ').title()}: {risk_value:.1f}%",
                    "type": "risk",
                    "data": {
                        "value": risk_value,
                        "color": "#ff4444" if risk_value > 20 else "#ff9800" if risk_value > 10 else "#ffeb3b"
                    }
                })
        
        if risks_node["children"]:
            mindmap["children"].append(risks_node)
        
        # Recommendations node
        if result.recommendations:
            rec_node = {
                "id": "recommendations",
                "label": "Συστάσεις",
                "type": "category",
                "data": {"icon": "💡"},
                "children": []
            }
            
            for i, rec in enumerate(result.recommendations[:3]):  # Top 3
                rec_node["children"].append({
                    "id": f"rec_{i}",
                    "label": rec[:50] + "..." if len(rec) > 50 else rec,
                    "type": "recommendation",
                    "data": {"full_text": rec, "color": "#4caf50"}
                })
            
            mindmap["children"].append(rec_node)
        
        return mindmap
    
    def _create_comparison_data(self, result: SimulationResult, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create before/after comparison data"""
        
        # Get baseline from patient data
        measurements = patient_data.get('measurements', [])
        baseline_glucose = 120.0
        baseline_hba1c = 7.5
        
        if measurements:
            latest = measurements[-1]
            if latest.get('blood_glucose_level'):
                baseline_glucose = float(latest['blood_glucose_level'])
            if latest.get('hba1c'):
                baseline_hba1c = float(latest['hba1c'])
        
        return {
            "baseline": {
                "glucose": baseline_glucose,
                "hba1c": baseline_hba1c,
                "tir_70_180": 65.0,  # Estimated baseline
                "glucose_cv": 40.0   # Estimated baseline
            },
            "scenario": {
                "glucose": result.glucose_metrics["mean_glucose"],
                "hba1c": result.glucose_metrics["estimated_hba1c"],
                "tir_70_180": result.glucose_metrics["tir_70_180"],
                "glucose_cv": result.glucose_metrics["glucose_cv"]
            },
            "improvements": {
                "glucose_change": result.glucose_metrics["mean_glucose"] - baseline_glucose,
                "hba1c_change": result.glucose_metrics["estimated_hba1c"] - baseline_hba1c,
                "tir_improvement": result.glucose_metrics["tir_70_180"] - 65.0,
                "cv_improvement": 40.0 - result.glucose_metrics["glucose_cv"]
            }
        }


# Global instance
digital_twin_engine = DigitalTwinEngine()