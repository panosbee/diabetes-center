"""
Digital Twin Simulation Engine για What-If Scenarios - ΒΕΛΤΙΩΜΕΝΗ ΕΚΔΟΣΗ (FIXED)
==============================================================================

Ακριβή φαρμακοκινητικά/φαρμακοδυναμικά models για diabetes management.
Βασίζεται στα πραγματικά patient data και παράγει realistic scenarios.

FIXED: JSON serialization error με numpy types
"""

import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import json
import asyncio
import random

# Mathematical models
from scipy.integrate import odeint, solve_ivp
from scipy.optimize import minimize_scalar

logger = logging.getLogger(__name__)


def convert_numpy_types(obj):
    """
    ΝΕΟΣ: Recursive function για μετατροπή numpy types σε native Python types
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj


@dataclass
class PatientProfile:
    """Enhanced patient-specific parameters for digital twin"""
    weight_kg: float
    height_cm: float
    age: int
    diabetes_type: str  # "T1" or "T2"
    
    # Insulin sensitivity factors (derived from patient data)
    insulin_sensitivity: float  # mg/dL per unit
    carb_ratio: float  # grams per unit
    correction_factor: float  # mg/dL per unit
    basal_rate: float  # units per hour
    
    # Enhanced physiological parameters
    glucose_absorption_rate: float = 0.3  # per hour
    insulin_absorption_rate: float = 0.15  # per hour
    liver_glucose_production: float = 2.0  # mg/dL per hour
    glucose_clearance_rate: float = 0.05  # per hour
    
    # NEW: Patient-specific variability factors
    diabetes_duration_years: float = 5.0
    stress_sensitivity: float = 1.0  # How much stress affects glucose
    exercise_sensitivity: float = 1.0  # Response to exercise
    meal_variability: float = 0.1  # Variability in meal absorption
    insulin_variability: float = 0.05  # Insulin absorption variability
    
    # NEW: Current condition factors
    recent_hba1c: Optional[float] = None
    recent_glucose_mean: Optional[float] = None
    recent_glucose_cv: Optional[float] = None
    infection_factor: float = 1.0  # 1.0 = healthy, >1.0 = fighting infection
    
    # NEW: Circadian rhythms
    dawn_phenomenon: float = 0.8  # Glucose rise in early morning
    dusk_phenomenon: float = 0.3  # Evening insulin resistance


@dataclass
class ScenarioParams:
    """What-if scenario parameters - ENHANCED"""
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
    
    # Enhanced simulation parameters
    simulation_hours: int = 24
    time_step_minutes: int = 5  # Higher resolution - ΒΕΛΤΙΩΣΗ


@dataclass
class SimulationResult:
    """Results from digital twin simulation - ENHANCED"""
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
    ΒΕΛΤΙΩΜΕΝΟ pharmacokinetic/pharmacodynamic model για insulin και glucose dynamics
    """
    
    def __init__(self, patient_profile: PatientProfile):
        self.patient = patient_profile
        self.current_time = 0.0
        
        # Enhanced kinetic parameters
        self.Ka_insulin_fast = 0.25  # Fast-acting insulin absorption
        self.Ka_insulin_slow = 0.08  # Long-acting insulin absorption  
        self.Ke_insulin = 0.12  # Insulin elimination rate
        self.Ka_glucose = 0.3   # Glucose absorption rate
        
        # NEW: Compartment model parameters
        self.Vd_glucose = 0.16 * patient_profile.weight_kg  # L/kg
        self.Vd_insulin = 0.12 * patient_profile.weight_kg
        
        # Enhanced patient-specific adjustments
        self.insulin_resistance_factor = self._calculate_insulin_resistance()
        self.metabolic_rate_factor = self._calculate_metabolic_rate()
        
        # NEW: Stochastic noise parameters για realism
        self.glucose_noise_std = 8.0  # mg/dL standard deviation
        self.insulin_noise_std = 0.03  # Relative noise in insulin action
        
        logger.info(f"🧬 Enhanced PK model initialized - IR factor: {self.insulin_resistance_factor:.2f}, "
                   f"Metabolic rate: {self.metabolic_rate_factor:.2f}")
    
    def _calculate_insulin_resistance(self) -> float:
        """ΝΕΟΣ: Υπολογισμός insulin resistance βασισμένος σε κλινικούς παράγοντες"""
        base_resistance = 1.0
        
        # Type 2 diabetes effect
        if self.patient.diabetes_type == "T2":
            base_resistance *= 1.6  # Significant insulin resistance
            
        # BMI effect
        bmi = self.patient.weight_kg / (self.patient.height_cm / 100) ** 2
        if bmi > 30:
            base_resistance *= 1.3
        elif bmi > 25:
            base_resistance *= 1.15
            
        # Age effect
        if self.patient.age > 60:
            base_resistance *= 1.1
        elif self.patient.age > 50:
            base_resistance *= 1.05
            
        # Duration effect (complications)
        if self.patient.diabetes_duration_years > 15:
            base_resistance *= 1.2
        elif self.patient.diabetes_duration_years > 10:
            base_resistance *= 1.1
            
        # HbA1c effect (poor control = more resistance)
        if self.patient.recent_hba1c:
            if self.patient.recent_hba1c > 9.0:
                base_resistance *= 1.4
            elif self.patient.recent_hba1c > 8.0:
                base_resistance *= 1.25
            elif self.patient.recent_hba1c > 7.0:
                base_resistance *= 1.1
            
        return base_resistance
    
    def _calculate_metabolic_rate(self) -> float:
        """ΝΕΟΣ: Υπολογισμός μεταβολικού ρυθμού"""
        base_rate = 1.0
        
        # Age effect on metabolism
        if self.patient.age < 30:
            base_rate = 1.15
        elif self.patient.age > 65:
            base_rate = 0.85
        elif self.patient.age > 50:
            base_rate = 0.95
            
        # Weight effect
        bmi = self.patient.weight_kg / (self.patient.height_cm / 100) ** 2
        if bmi < 20:
            base_rate *= 1.1
        elif bmi > 35:
            base_rate *= 0.9
            
        return base_rate
    
    def _add_circadian_effects(self, t: float, glucose: float, insulin_action: float) -> Tuple[float, float]:
        """ΝΕΟΣ: Προσθήκη κιρκάδιων ρυθμών"""
        hour_of_day = (t % 24)
        
        # Dawn phenomenon (4-8 AM)
        if 4 <= hour_of_day <= 8:
            dawn_intensity = self.patient.dawn_phenomenon * np.sin(np.pi * (hour_of_day - 4) / 4)
            glucose += dawn_intensity * 25  # Up to 25 mg/dL rise
            
        # Dusk phenomenon (6-10 PM) - evening insulin resistance
        if 18 <= hour_of_day <= 22:
            dusk_intensity = self.patient.dusk_phenomenon * np.sin(np.pi * (hour_of_day - 18) / 4)
            insulin_action *= (1 - dusk_intensity * 0.25)  # Up to 25% reduction
            
        return glucose, insulin_action
    
    def _add_stochastic_noise(self, glucose: float, insulin: float) -> Tuple[float, float]:
        """ΝΕΟΣ: Προσθήκη στοχαστικού θορύβου για ρεαλισμό"""
        # Glucose measurement noise - ρεαλιστικό
        glucose_noise = np.random.normal(0, self.glucose_noise_std)
        glucose_with_noise = max(30, glucose + glucose_noise)  # Minimum 30 mg/dL
        
        # Insulin action variability
        insulin_noise = np.random.normal(1.0, self.insulin_noise_std)
        insulin_with_noise = max(0, insulin * insulin_noise)
        
        return glucose_with_noise, insulin_with_noise
    
    def _gamma_absorption(self, time_minutes: float, total_carbs: float) -> float:
        """ΝΕΟΣ: Gamma distribution για realistic meal absorption"""
        if time_minutes <= 0:
            return 0
        
        # Gamma parameters για typical meal absorption
        alpha = 2.0  # Shape parameter
        beta = 45.0  # Scale parameter (minutes) - faster than original
        
        # Enhanced absorption curve
        t_scaled = time_minutes / beta
        if t_scaled > 0:
            absorption_rate = (total_carbs * 4 *  # 4 mg/dL per gram carb
                              (t_scaled ** (alpha - 1) * np.exp(-t_scaled)) / 
                              (beta * np.math.gamma(alpha)))
        else:
            absorption_rate = 0
        
        return max(0, absorption_rate)
    
    def enhanced_glucose_insulin_ode(self, t: float, state: List[float], 
                                   insulin_input: float, glucose_input: float,
                                   exercise_effect: float = 0.0) -> List[float]:
        """
        ΒΕΛΤΙΩΜΕΝΕΣ διαφορικές εξισώσεις για glucose-insulin dynamics
        
        State variables:
        [0] Plasma glucose (mg/dL)
        [1] Plasma insulin (mU/L)  
        [2] Subcutaneous insulin depot - fast acting (units)
        [3] Subcutaneous insulin depot - long acting (units)
        [4] Interstitial glucose (mg/dL)
        [5] Liver glucose stores (mg/dL equivalent)
        """
        glucose, insulin, insulin_fast, insulin_long, glucose_interstitial, liver_glucose = state
        
        # Enhanced insulin kinetics
        insulin_absorption_fast = self.Ka_insulin_fast * insulin_fast * (1 + np.random.normal(0, self.patient.insulin_variability))
        insulin_absorption_slow = self.Ka_insulin_slow * insulin_long * (1 + np.random.normal(0, self.patient.insulin_variability))
        total_insulin_absorption = max(0, insulin_absorption_fast + insulin_absorption_slow)
        
        insulin_elimination = self.Ke_insulin * insulin
        
        # Enhanced glucose dynamics με πραγματικούς παράγοντες
        # Hepatic glucose production με insulin suppression
        insulin_suppression = insulin / (insulin + 15)  # Hill equation - more sensitive
        hepatic_glucose_production = (self.patient.liver_glucose_production * 
                                    (1 - insulin_suppression * 0.8) * 
                                    self.patient.infection_factor *
                                    self.metabolic_rate_factor)
        
        # Glucose utilization με enhanced insulin sensitivity
        glucose_utilization = (glucose * self.patient.glucose_clearance_rate * 
                              self.metabolic_rate_factor *
                              (1 + insulin * self.patient.insulin_sensitivity / 100 / self.insulin_resistance_factor) * 
                              (1 + exercise_effect * self.patient.exercise_sensitivity * 2))
        
        # Enhanced exercise effects με delayed response
        exercise_glucose_uptake = exercise_effect * glucose * 0.12 * self.patient.exercise_sensitivity
        
        # Enhanced meal absorption με variability
        meal_absorption_rate = glucose_input * (1 + np.random.normal(0, self.patient.meal_variability))
        
        # Apply circadian effects
        glucose_circadian, insulin_action_circadian = self._add_circadian_effects(
            t, glucose, total_insulin_absorption
        )
        
        # Διαφορικές εξισώσεις με βελτιωμένη φυσιολογία
        dglucose_dt = (hepatic_glucose_production - glucose_utilization - 
                      exercise_glucose_uptake + meal_absorption_rate)
        
        dinsulin_dt = insulin_action_circadian - insulin_elimination
        
        dinsulin_fast_dt = -insulin_absorption_fast  # Depletes as absorbed
        dinsulin_long_dt = -insulin_absorption_slow   # Depletes as absorbed
        
        dglucose_interstitial_dt = self.Ka_glucose * (glucose - glucose_interstitial)
        
        # Liver glucose stores (enhanced)
        dliver_glucose_dt = -hepatic_glucose_production * 0.15 + glucose_utilization * 0.1  # Replenishment
        
        return [dglucose_dt, dinsulin_dt, dinsulin_fast_dt, 
                dinsulin_long_dt, dglucose_interstitial_dt, dliver_glucose_dt]
    
    def simulate_scenario(self, initial_state: List[float], 
                         scenario: ScenarioParams,
                         current_vitals: Dict[str, Any]) -> SimulationResult:
        """
        ΒΕΛΤΙΩΜΕΝΗ simulation με enhanced realism
        """
        
        # Enhanced time grid με higher resolution
        total_minutes = scenario.simulation_hours * 60
        time_minutes = np.arange(0, total_minutes + 1, scenario.time_step_minutes)
        time_hours = time_minutes / 60.0
        
        logger.info(f"🔬 Starting enhanced simulation: {len(time_minutes)} timepoints over {scenario.simulation_hours}h")
        
        # Adjusted patient parameters based on scenario
        adjusted_basal = self.patient.basal_rate * (1 + scenario.basal_change / 100)
        adjusted_carb_ratio = self.patient.carb_ratio * (1 + scenario.carb_ratio_change / 100)
        adjusted_correction = self.patient.correction_factor * (1 + scenario.correction_factor_change / 100)
        
        # Enhanced initial state handling
        if len(initial_state) == 4:
            # Convert old format to new enhanced format
            enhanced_initial_state = [
                initial_state[0] + np.random.normal(0, 5),  # glucose με noise
                initial_state[1] + np.random.normal(0, 1),  # insulin με noise
                0.0,  # insulin_fast
                initial_state[2],  # insulin_long (from old insulin_depot)
                initial_state[3] + np.random.normal(0, 3),  # glucose_interstitial με noise
                180.0 + np.random.normal(0, 20)  # liver_glucose με variability
            ]
        else:
            enhanced_initial_state = initial_state.copy()
        
        # Enhanced input arrays
        insulin_inputs_fast = np.zeros_like(time_minutes, dtype=float)
        insulin_inputs_long = np.zeros_like(time_minutes, dtype=float)
        glucose_inputs = np.zeros_like(time_minutes, dtype=float)
        exercise_effects = np.zeros_like(time_minutes, dtype=float)
        
        # Enhanced basal insulin (continuous long-acting)
        basal_per_timestep = adjusted_basal * (scenario.time_step_minutes / 60.0)
        insulin_inputs_long[:] = basal_per_timestep
        
        # Enhanced meal handling με realistic absorption
        if scenario.meal_carbs > 0:
            meal_timestep = int(scenario.meal_timing / scenario.time_step_minutes)
            if meal_timestep < len(insulin_inputs_fast):
                # Meal bolus (fast-acting)
                meal_bolus = scenario.meal_carbs / adjusted_carb_ratio
                meal_bolus *= (1 + scenario.bolus_change / 100)
                insulin_inputs_fast[meal_timestep] += meal_bolus
                
                # Enhanced glucose absorption με gamma distribution
                for i in range(int(300 / scenario.time_step_minutes)):  # 5 hours absorption
                    if meal_timestep + i < len(glucose_inputs):
                        time_since_meal = i * scenario.time_step_minutes
                        absorption_rate = self._gamma_absorption(time_since_meal, scenario.meal_carbs)
                        glucose_inputs[meal_timestep + i] += absorption_rate
        
        # Enhanced exercise modeling με realistic effects
        if scenario.exercise_duration > 0:
            exercise_start = int(120 / scenario.time_step_minutes)  # Start after 2 hours
            exercise_timesteps = int(scenario.exercise_duration / scenario.time_step_minutes)
            exercise_intensity_factor = scenario.exercise_intensity / 100.0
            
            for i in range(exercise_timesteps + int(120 / scenario.time_step_minutes)):  # +2h post-exercise
                if exercise_start + i < len(exercise_effects):
                    if i < exercise_timesteps:
                        # During exercise - full effect
                        exercise_effects[exercise_start + i] = exercise_intensity_factor
                    else:
                        # Post-exercise effect (decaying exponentially)
                        post_minutes = (i - exercise_timesteps) * scenario.time_step_minutes
                        decay_factor = np.exp(-post_minutes / 60)  # 1-hour half-life
                        exercise_effects[exercise_start + i] = exercise_intensity_factor * 0.4 * decay_factor
        
        # Enhanced ODE solving με adaptive methods
        solution = []
        current_state = enhanced_initial_state.copy()
        
        for i, t in enumerate(time_hours):
            if i == 0:
                solution.append(current_state.copy())
                continue
            
            # Time span for this step
            t_span = [time_hours[i-1], t]
            
            try:
                def ode_func(t, y):
                    return self.enhanced_glucose_insulin_ode(
                        t, y, 
                        insulin_inputs_fast[i] + insulin_inputs_long[i],
                        glucose_inputs[i], 
                        exercise_effects[i]
                    )
                
                # Enhanced ODE solving με better accuracy
                sol = solve_ivp(
                    ode_func, 
                    t_span, 
                    current_state,
                    method='RK45',  # Runge-Kutta 4th/5th order
                    rtol=1e-6,
                    atol=1e-8,
                    dense_output=True
                )
                
                if sol.success:
                    current_state = sol.y[:, -1].tolist()
                    
                    # Add realistic stochastic noise
                    current_state[0], current_state[1] = self._add_stochastic_noise(
                        current_state[0], current_state[1]
                    )
                    
                    # Physiological bounds
                    current_state[0] = max(20, min(600, current_state[0]))  # Glucose bounds
                    current_state[1] = max(0, min(200, current_state[1]))   # Insulin bounds
                else:
                    logger.warning(f"ODE solver failed at t={t:.2f}, using previous state")
                
                solution.append(current_state.copy())
                
            except Exception as e:
                logger.error(f"Enhanced ODE integration error at t={t:.2f}: {e}")
                solution.append(current_state.copy())
        
        # Extract enhanced results
        solution = np.array(solution)
        glucose_levels = solution[:, 0].tolist()
        insulin_levels = solution[:, 1].tolist()
        
        logger.info(f"📊 Simulation completed: Glucose range {min(glucose_levels):.0f}-{max(glucose_levels):.0f} mg/dL")
        
        # Enhanced metrics calculation
        glucose_metrics = self._calculate_enhanced_glucose_metrics(glucose_levels, time_hours.tolist())
        
        # Enhanced risk assessment
        risk_scores = self._assess_enhanced_scenario_risks(glucose_levels, insulin_levels, scenario)
        
        # Enhanced safety alerts
        safety_alerts = self._generate_enhanced_safety_alerts(glucose_levels, insulin_levels, scenario)
        
        # Enhanced recommendations
        recommendations = self._generate_enhanced_recommendations(glucose_metrics, risk_scores, scenario)
        
        # Enhanced scenario summary
        scenario_summary = {
            "parameters": asdict(scenario),
            "adjusted_basal": adjusted_basal,
            "adjusted_carb_ratio": adjusted_carb_ratio,
            "meal_bolus": scenario.meal_carbs / adjusted_carb_ratio if scenario.meal_carbs > 0 else 0,
            "total_insulin_fast": sum(insulin_inputs_fast),
            "total_insulin_long": sum(insulin_inputs_long),
            "peak_glucose": max(glucose_levels),
            "min_glucose": min(glucose_levels),
            "glucose_excursions": self._count_glucose_excursions(glucose_levels),
            "insulin_resistance_factor": self.insulin_resistance_factor,
            "metabolic_rate_factor": self.metabolic_rate_factor,
            "simulation_quality": {
                "time_resolution": f"{scenario.time_step_minutes} minutes",
                "total_timepoints": len(time_minutes),
                "physiological_noise": "enabled",
                "circadian_effects": "enabled"
            }
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
    
    def _count_glucose_excursions(self, glucose_levels: List[float]) -> Dict[str, int]:
        """ΝΕΟΣ: Μέτρηση glucose excursions"""
        excursions = {"hypo_events": 0, "hyper_events": 0, "severe_hypo": 0, "severe_hyper": 0}
        
        in_hypo = False
        in_hyper = False
        
        for glucose in glucose_levels:
            # Hypoglycemia detection
            if glucose < 70 and not in_hypo:
                excursions["hypo_events"] += 1
                in_hypo = True
                if glucose < 54:
                    excursions["severe_hypo"] += 1
            elif glucose >= 70:
                in_hypo = False
                
            # Hyperglycemia detection
            if glucose > 180 and not in_hyper:
                excursions["hyper_events"] += 1
                in_hyper = True
                if glucose > 250:
                    excursions["severe_hyper"] += 1
            elif glucose <= 180:
                in_hyper = False
                
        return excursions
    
    def _calculate_enhanced_glucose_metrics(self, glucose_levels: List[float], 
                                          time_hours: List[float]) -> Dict[str, float]:
        """ΒΕΛΤΙΩΜΕΝΑ glucose metrics με πρόσθετες κλινικές μετρικές"""
        glucose_array = np.array(glucose_levels)
        
        # Standard metrics
        tir_70_180 = np.sum((glucose_array >= 70) & (glucose_array <= 180)) / len(glucose_array) * 100
        tir_70_140 = np.sum((glucose_array >= 70) & (glucose_array <= 140)) / len(glucose_array) * 100
        time_below_70 = np.sum(glucose_array < 70) / len(glucose_array) * 100
        time_below_54 = np.sum(glucose_array < 54) / len(glucose_array) * 100
        time_above_180 = np.sum(glucose_array > 180) / len(glucose_array) * 100
        time_above_250 = np.sum(glucose_array > 250) / len(glucose_array) * 100
        
        # Enhanced metrics
        mean_glucose = np.mean(glucose_array)
        glucose_std = np.std(glucose_array)
        cv = (glucose_std / mean_glucose) * 100 if mean_glucose > 0 else 0
        
        # Estimated HbA1c (Nathan formula)
        estimated_hba1c = (mean_glucose + 46.7) / 28.7
        
        # NEW: Glucose Management Indicator (GMI)
        gmi = 3.31 + 0.02392 * mean_glucose
        
        # NEW: Mean amplitude of glycemic excursions (MAGE)
        mage = self._calculate_mage(glucose_levels)
        
        # NEW: J-index (combines mean and variability)
        j_index = 0.324 * (mean_glucose + glucose_std) ** 2
        
        # NEW: Continuous Overlapping Net Glycemic Action (CONGA)
        conga = self._calculate_conga(glucose_levels, time_hours)
        
        # FIXED: Convert all numpy types to Python types
        return convert_numpy_types({
            "mean_glucose": float(mean_glucose),
            "glucose_std": float(glucose_std),
            "glucose_cv": float(cv),
            "estimated_hba1c": float(estimated_hba1c),
            "gmi": float(gmi),
            "tir_70_180": float(tir_70_180),
            "tir_70_140": float(tir_70_140),
            "time_below_70": float(time_below_70),
            "time_below_54": float(time_below_54),
            "time_above_180": float(time_above_180),
            "time_above_250": float(time_above_250),
            "peak_glucose": float(np.max(glucose_array)),
            "min_glucose": float(np.min(glucose_array)),
            "mage": float(mage),
            "j_index": float(j_index),
            "conga": float(conga),
            "glucose_risk_index": float(self._calculate_glucose_risk_index(glucose_array))
        })
    
    def _calculate_mage(self, glucose_levels: List[float]) -> float:
        """ΝΕΟΣ: Mean Amplitude of Glycemic Excursions"""
        if len(glucose_levels) < 3:
            return 0.0
            
        excursions = []
        direction = 0  # 0=none, 1=up, -1=down
        last_peak = glucose_levels[0]
        
        for i in range(1, len(glucose_levels)):
            diff = glucose_levels[i] - glucose_levels[i-1]
            
            if abs(diff) > 10:  # Significant change (lowered threshold)
                if direction == 0:
                    direction = 1 if diff > 0 else -1
                    last_peak = glucose_levels[i-1]
                elif (direction == 1 and diff < 0) or (direction == -1 and diff > 0):
                    # Direction change - record excursion
                    excursion_magnitude = abs(glucose_levels[i-1] - last_peak)
                    if excursion_magnitude > 15:  # Only significant excursions
                        excursions.append(excursion_magnitude)
                    direction = 1 if diff > 0 else -1
                    last_peak = glucose_levels[i-1]
        
        return np.mean(excursions) if excursions else 0.0
    
    def _calculate_conga(self, glucose_levels: List[float], time_hours: List[float]) -> float:
        """ΝΕΟΣ: Continuous Overlapping Net Glycemic Action"""
        if len(glucose_levels) < 12:  # Need at least 1 hour of data at 5-min intervals
            return 0.0
            
        # Calculate 1-hour differences
        hour_diffs = []
        timestep_per_hour = int(60 / 5)  # 12 points per hour at 5-min intervals
        
        for i in range(len(glucose_levels) - timestep_per_hour):
            diff = glucose_levels[i + timestep_per_hour] - glucose_levels[i]
            hour_diffs.append(diff ** 2)
            
        return np.sqrt(np.mean(hour_diffs)) if hour_diffs else 0.0
    
    def _calculate_glucose_risk_index(self, glucose_array: np.ndarray) -> float:
        """ΝΕΟΣ: Composite glucose risk index"""
        # Enhanced risk calculation
        hypo_risk = np.sum(glucose_array < 70) / len(glucose_array) * 100
        severe_hypo_risk = np.sum(glucose_array < 54) / len(glucose_array) * 100
        hyper_risk = np.sum(glucose_array > 250) / len(glucose_array) * 100
        moderate_hyper_risk = np.sum(glucose_array > 180) / len(glucose_array) * 100
        
        # Variability risk
        cv = (np.std(glucose_array) / np.mean(glucose_array)) * 100
        variability_risk = min(100, max(0, (cv - 20) * 2.5))
        
        # Weighted combination με clinical priorities
        total_risk = (severe_hypo_risk * 5 + hypo_risk * 3 + hyper_risk * 2 + 
                     moderate_hyper_risk * 1 + variability_risk * 1.5) / 12.5
        
        return min(100, total_risk)
    
    def _assess_enhanced_scenario_risks(self, glucose_levels: List[float], 
                                      insulin_levels: List[float], 
                                      scenario: ScenarioParams) -> Dict[str, float]:
        """ΒΕΛΤΙΩΜΕΝΗ risk assessment με πρόσθετους παράγοντες"""
        glucose_array = np.array(glucose_levels)
        
        # Basic risks με enhanced calculation
        severe_hypo_risk = np.sum(glucose_array < 54) / len(glucose_array) * 100
        mild_hypo_risk = np.sum(glucose_array < 70) / len(glucose_array) * 100
        mild_hyper_risk = np.sum(glucose_array > 180) / len(glucose_array) * 100
        severe_hyper_risk = np.sum(glucose_array > 250) / len(glucose_array) * 100
        
        # NEW: Enhanced risk factors
        prolonged_hyper_risk = self._calculate_prolonged_exposure_risk(glucose_array, 200, 120)
        prolonged_hypo_risk = self._calculate_prolonged_exposure_risk(glucose_array, 70, 60, below=True)
        
        # Enhanced variability risk
        cv = (np.std(glucose_array) / np.mean(glucose_array)) * 100
        variability_risk = min(100, max(0, (cv - 25) * 2))  # Risk increases above 25% CV
        
        # NEW: Scenario-specific risks
        insulin_stacking_risk = self._assess_insulin_stacking_risk(scenario)
        exercise_hypo_risk = self._assess_exercise_hypo_risk(scenario, mild_hypo_risk)
        meal_spike_risk = self._assess_meal_spike_risk(scenario, severe_hyper_risk)
        
        # Enhanced overall risk calculation
        risk_weights = {
            'severe_hypo': 6,
            'mild_hypo': 3,
            'severe_hyper': 4,
            'mild_hyper': 1.5,
            'prolonged_hyper': 2,
            'prolonged_hypo': 4,
            'variability': 2,
            'insulin_stacking': 3,
            'exercise_hypo': 2,
            'meal_spike': 1.5
        }
        
        total_weight = sum(risk_weights.values())
        overall_risk = (
            severe_hypo_risk * risk_weights['severe_hypo'] +
            mild_hypo_risk * risk_weights['mild_hypo'] +
            severe_hyper_risk * risk_weights['severe_hyper'] +
            mild_hyper_risk * risk_weights['mild_hyper'] +
            prolonged_hyper_risk * risk_weights['prolonged_hyper'] +
            prolonged_hypo_risk * risk_weights['prolonged_hypo'] +
            variability_risk * risk_weights['variability'] +
            insulin_stacking_risk * risk_weights['insulin_stacking'] +
            exercise_hypo_risk * risk_weights['exercise_hypo'] +
            meal_spike_risk * risk_weights['meal_spike']
        ) / total_weight
        
        # FIXED: Convert all numpy types to Python types
        return convert_numpy_types({
            "hypoglycemia_risk": float(mild_hypo_risk),
            "severe_hypoglycemia_risk": float(severe_hypo_risk),
            "hyperglycemia_risk": float(mild_hyper_risk),
            "severe_hyperglycemia_risk": float(severe_hyper_risk),
            "prolonged_hyperglycemia_risk": float(prolonged_hyper_risk),
            "prolonged_hypoglycemia_risk": float(prolonged_hypo_risk),
            "variability_risk": float(variability_risk),
            "insulin_stacking_risk": float(insulin_stacking_risk),
            "exercise_related_risk": float(exercise_hypo_risk),
            "meal_spike_risk": float(meal_spike_risk),
            "overall_risk": float(min(100, overall_risk))
        })
    
    def _calculate_prolonged_exposure_risk(self, glucose_array: np.ndarray, 
                                         threshold: float, duration_minutes: int,
                                         below: bool = False) -> float:
        """ΝΕΟΣ: Calculate risk of prolonged exposure above/below threshold"""
        duration_points = max(1, duration_minutes // 5)  # 5-minute intervals
        
        consecutive_count = 0
        max_consecutive = 0
        total_exposure_time = 0
        
        for glucose in glucose_array:
            condition = glucose < threshold if below else glucose > threshold
            
            if condition:
                consecutive_count += 1
                total_exposure_time += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 0
        
        # Risk based on both duration and frequency
        duration_risk = min(100, (max_consecutive / duration_points) * 30) if max_consecutive >= duration_points else 0
        frequency_risk = min(100, (total_exposure_time / len(glucose_array)) * 100)
        
        return max(duration_risk, frequency_risk * 0.5)
    
    def _assess_insulin_stacking_risk(self, scenario: ScenarioParams) -> float:
        """ΝΕΟΣ: Assess risk of insulin stacking"""
        risk = 0.0
        
        # Large parameter changes
        if abs(scenario.bolus_change) > 40:
            risk += 25
        elif abs(scenario.bolus_change) > 25:
            risk += 15
            
        if abs(scenario.basal_change) > 30:
            risk += 20
        elif abs(scenario.basal_change) > 20:
            risk += 10
            
        # Timing-related risks
        if scenario.meal_carbs > 0 and scenario.meal_timing < 90:  # Meal too close to previous
            risk += 15
            
        # Exercise + insulin increase combination
        if scenario.exercise_intensity > 0:
            if scenario.basal_change > 0:
                risk += 30
            if scenario.bolus_change > 0:
                risk += 20
                
        return min(60, risk)
    
    def _assess_exercise_hypo_risk(self, scenario: ScenarioParams, baseline_hypo_risk: float) -> float:
        """ΝΕΟΣ: Assess exercise-related hypoglycemia risk"""
        if scenario.exercise_intensity == 0:
            return 0.0
            
        base_risk = scenario.exercise_intensity * 0.4  # Base risk from exercise intensity
        
        # Increased risk if insulin also increased
        if scenario.basal_change > 0 or scenario.bolus_change > 0:
            base_risk *= 1.8
            
        # Reduced risk if meal provided
        if scenario.meal_carbs > 20:
            base_risk *= 0.6
            
        # Factor in baseline hypoglycemia risk
        combined_risk = base_risk + baseline_hypo_risk * 0.3
        
        return min(80, combined_risk)
    
    def _assess_meal_spike_risk(self, scenario: ScenarioParams, baseline_hyper_risk: float) -> float:
        """ΝΕΟΣ: Assess meal-related hyperglycemia risk"""
        if scenario.meal_carbs == 0:
            return 0.0
            
        # Risk increases with meal size
        base_risk = max(0, (scenario.meal_carbs - 40) * 0.5)  # Risk starts at 40g
        
        # Reduced risk if bolus increased appropriately
        if scenario.bolus_change > 0:
            base_risk *= max(0.3, 1 - scenario.bolus_change / 100)
            
        # Increased risk if bolus decreased
        elif scenario.bolus_change < 0:
            base_risk *= (1 + abs(scenario.bolus_change) / 50)
            
        return min(60, base_risk + baseline_hyper_risk * 0.2)
    
    def _generate_enhanced_safety_alerts(self, glucose_levels: List[float], 
                                       insulin_levels: List[float], 
                                       scenario: ScenarioParams) -> List[str]:
        """ΒΕΛΤΙΩΜΕΝΑ safety alerts με προτεραιότητες και περισσότερη λεπτομέρεια"""
        alerts = []
        glucose_array = np.array(glucose_levels)
        
        # ΚΡΙΤΙΚΟΙ ΚΙΝΔΥΝΟΙ (🚨)
        min_glucose = np.min(glucose_array)
        max_glucose = np.max(glucose_array)
        
        if min_glucose < 40:
            alerts.append("🚨 ΚΡΙΤΙΚΟΣ ΚΙΝΔΥΝΟΣ: Εξαιρετικά σοβαρή υπογλυκαιμία (<40 mg/dL) - άμεση ιατρική παρέμβαση απαιτείται")
        
        if max_glucose > 400:
            alerts.append("🚨 ΚΡΙΤΙΚΟΣ ΚΙΝΔΥΝΟΣ: Εξαιρετικά υψηλή γλυκόζη (>400 mg/dL) - κίνδυνος κετοξέωσης")
        
        # ΥΨΗΛΗ ΠΡΟΤΕΡΑΙΟΤΗΤΑ (⚠️)
        if min_glucose < 54:
            duration = np.sum(glucose_array < 54) * 5  # minutes in severe hypo
            alerts.append(f"⚠️ ΥΨΗΛΗ ΠΡΟΤΕΡΑΙΟΤΗΤΑ: Σοβαρή υπογλυκαιμία (<54 mg/dL) για {duration:.0f} λεπτά")
        
        if max_glucose > 300:
            duration = np.sum(glucose_array > 300) * 5
            alerts.append(f"⚠️ ΥΨΗΛΗ ΠΡΟΤΕΡΑΙΟΤΗΤΑ: Σοβαρή υπεργλυκαιμία (>300 mg/dL) για {duration:.0f} λεπτά")
        
        # ΠΑΡΑΜΕΤΡΙΚΟΙ ΚΙΝΔΥΝΟΙ
        if abs(scenario.basal_change) > 50:
            alerts.append(f"⚠️ ΕΞΑΙΡΕΤΙΚΗ ΑΛΛΑΓΗ: Βασική ινσουλίνη {scenario.basal_change:+.0f}% - απαιτείται εξαιρετικά προσεκτική παρακολούθηση")
        
        if abs(scenario.bolus_change) > 50:
            alerts.append(f"⚠️ ΕΞΑΙΡΕΤΙΚΗ ΑΛΛΑΓΗ: Bolus ινσουλίνη {scenario.bolus_change:+.0f}% - κίνδυνος δραματικών μεταβολών γλυκόζης")
        
        # ΣΥΝΔΥΑΣΤΙΚΟΙ ΚΙΝΔΥΝΟΙ
        if (scenario.exercise_intensity > 70 and 
            (scenario.basal_change > 0 or scenario.bolus_change > 0)):
            alerts.append("⚠️ ΣΥΝΔΥΑΣΤΙΚΟΣ ΚΙΝΔΥΝΟΣ: Έντονη άσκηση + αυξημένη ινσουλίνη - εξαιρετικά υψηλός κίνδυνος υπογλυκαιμίας")
        
        # ΓΕΥΜΑΤΙΚΟΙ ΚΙΝΔΥΝΟΙ
        if scenario.meal_carbs > 100:
            postprandial_peak = max(glucose_array[int(len(glucose_array)*0.3):int(len(glucose_array)*0.7)])
            alerts.append(f"🍽️ ΜΕΓΑΛΟ ΓΕΥΜΑ: {scenario.meal_carbs}g - προβλεπόμενη κορυφή {postprandial_peak:.0f} mg/dL")
        
        # ΜΕΤΑΒΛΗΤΟΤΗΤΑ
        cv = (np.std(glucose_array) / np.mean(glucose_array)) * 100
        if cv > 50:
            alerts.append(f"📊 ΥΨΗΛΗ ΜΕΤΑΒΛΗΤΟΤΗΤΑ: CV {cv:.1f}% - ασταθής γλυκαιμικός έλεγχος")
        elif cv > 40:
            alerts.append(f"📊 ΑΥΞΗΜΕΝΗ ΜΕΤΑΒΛΗΤΟΤΗΤΑ: CV {cv:.1f}% - παρακολούθηση για σταθεροποίηση")
        
        # ΧΡΟΝΙΚΟΙ ΚΙΝΔΥΝΟΙ
        time_in_severe_hypo = np.sum(glucose_array < 54) / len(glucose_array) * 100
        if time_in_severe_hypo > 1:
            alerts.append(f"⏰ ΠΑΡΑΤΕΤΑΜΕΝΗ ΥΠΟΓΛΥΚΑΙΜΙΑ: {time_in_severe_hypo:.1f}% χρόνου σε <54 mg/dL")
        
        time_in_severe_hyper = np.sum(glucose_array > 250) / len(glucose_array) * 100
        if time_in_severe_hyper > 10:
            alerts.append(f"⏰ ΠΑΡΑΤΕΤΑΜΕΝΗ ΥΠΕΡΓΛΥΚΑΙΜΙΑ: {time_in_severe_hyper:.1f}% χρόνου σε >250 mg/dL")
        
        return alerts
    
    def _generate_enhanced_recommendations(self, glucose_metrics: Dict[str, float], 
                                         risk_scores: Dict[str, float], 
                                         scenario: ScenarioParams) -> List[str]:
        """ΒΕΛΤΙΩΜΕΝΕΣ clinical recommendations με evidence-based προτάσεις"""
        recommendations = []
        
        tir = glucose_metrics["tir_70_180"]
        cv = glucose_metrics["glucose_cv"]
        mean_glucose = glucose_metrics["mean_glucose"]
        
        # TIME IN RANGE OPTIMIZATION με εξειδικευμένες συστάσεις
        if tir < 40:
            recommendations.append("🚨 ΚΡΙΤΙΚΟ TIR: <40% - άμεση ολική αναθεώρηση θεραπευτικού σχήματος με ενδοκρινολόγο")
        elif tir < 50:
            recommendations.append("⚠️ ΧΑΜΗΛΟ TIR: <50% - εκτεταμένη επανεκτίμηση παραμέτρων, CGM και structured education")
        elif tir < 70:
            recommendations.append("📊 TIR ΒΕΛΤΙΩΣΗ: Στόχος >70% - fine-tuning basal/bolus ratios, meal timing optimization")
        elif tir > 85:
            recommendations.append("⭐ ΕΞΑΙΡΕΤΙΚΟΣ ΕΛΕΓΧΟΣ: TIR >85% - διατήρηση τρέχοντος πρωτοκόλλου με συνεχή παρακολούθηση")
        
        # HYPOGLYCEMIA PREVENTION με εξειδικευμένες στρατηγικές
        severe_hypo_risk = risk_scores.get("severe_hypoglycemia_risk", 0)
        mild_hypo_risk = risk_scores.get("hypoglycemia_risk", 0)
        
        if severe_hypo_risk > 3:
            recommendations.append("🚨 ΣΟΒΑΡΗ ΥΠΟΓΛΥΚΑΙΜΙΑ: Άμεση μείωση insulin regimen κατά 15-20%, CGM με predictive alerts")
        elif mild_hypo_risk > 10:
            recommendations.append("🔽 ΥΠΟΓΛΥΚΑΙΜΙΑ PREVENTION: Μείωση basal 10-15% ή carb ratio adjustment, frequent monitoring")
        elif mild_hypo_risk > 5:
            recommendations.append("🔽 MILD HYPO RISK: Pre-meal glucose checks, exercise snacks, review correction factors")
        
        # HYPERGLYCEMIA MANAGEMENT με progressive approach
        severe_hyper_risk = risk_scores.get("severe_hyperglycemia_risk", 0)
        mild_hyper_risk = risk_scores.get("hyperglycemia_risk", 0)
        
        if severe_hyper_risk > 15:
            recommendations.append("🔼 ΣΟΒΑΡΗ ΥΠΕΡΓΛΥΚΑΙΜΙΑ: Αύξηση correction factors 20%, review carb counting accuracy")
        elif mild_hyper_risk > 25:
            recommendations.append("🔼 ΥΠΕΡΓΛΥΚΑΙΜΙΑ CONTROL: Αύξηση basal 10-15% ή bolus optimization, post-meal checks")
        elif mean_glucose > 180:
            recommendations.append("🔼 ELEVATED GLUCOSE: Fine-tune meal bolus timing (-15 to -20 minutes), portion control")
        
        # VARIABILITY REDUCTION με targeted interventions
        if cv > 45:
            recommendations.append("📈 ΚΡΙΤΙΚΗ ΜΕΤΑΒΛΗΤΟΤΗΤΑ: Structured meal plans, CGM με alerts, stress management")
        elif cv > 36:
            recommendations.append("📊 ΥΨΗΛΗ ΜΕΤΑΒΛΗΤΟΤΗΤΑ: Consistent meal timing, carb counting accuracy, sleep hygiene")
        elif cv > 30:
            recommendations.append("📈 MODERATE VARIABILITY: Pre-bolus timing consistency, exercise scheduling")
        elif cv < 25:
            recommendations.append("✅ EXCELLENT VARIABILITY: Maintain current practices - CV <25% is optimal")
        
        # EXERCISE RECOMMENDATIONS με safety considerations
        if scenario.exercise_intensity == 0 and mean_glucose > 140:
            recommendations.append("🏃‍♂️ EXERCISE THERAPY: 150min/week moderate exercise - improves insulin sensitivity by 20-30%")
        elif scenario.exercise_intensity > 0:
            if risk_scores.get("exercise_related_risk", 0) > 20:
                recommendations.append("🏃‍♂️ EXERCISE SAFETY: 25% basal reduction 1h pre-exercise, 15-30g carb snack")
            else:
                recommendations.append("🏃‍♂️ EXERCISE OPTIMIZATION: Current exercise plan is well-tolerated")
        
        # MEAL MANAGEMENT με evidence-based strategies
        if scenario.meal_carbs > 80:
            recommendations.append("🍽️ LARGE MEAL STRATEGY: Consider dual/square wave bolus - 60% immediate, 40% over 2h")
        elif scenario.meal_carbs > 0:
            mage = glucose_metrics.get("mage", 0)
            if mage > 60:
                recommendations.append("🍽️ MEAL TIMING: Pre-bolus 15-20 minutes για reduction of post-meal spikes")
        
        # TECHNOLOGY RECOMMENDATIONS
        if cv > 35 or severe_hypo_risk > 2:
            recommendations.append("📱 TECHNOLOGY: CGM με predictive low glucose alerts strongly recommended")
        elif tir < 70 and cv > 30:
            recommendations.append("📱 CGM UPGRADE: Consider integrated insulin pump/CGM system (AID)")
        
        # MEDICATION ADJUSTMENTS (Type-specific)
        if self.patient.diabetes_type == "T1":
            if tir < 60:
                recommendations.append("💊 T1D THERAPY: Evaluate rapid-acting insulin analog switch, consider AID system")
        elif self.patient.diabetes_type == "T2":
            if mean_glucose > 200:
                recommendations.append("💊 T2D THERAPY: Consider GLP-1 agonist addition, metformin optimization")
        
        # ADVANCED ANALYTICS INSIGHTS
        j_index = glucose_metrics.get("j_index", 0)
        if j_index > 50:
            recommendations.append("📊 J-INDEX ELEVATED: Focus on both mean glucose AND variability reduction")
        
        conga = glucose_metrics.get("conga", 0)
        if conga > 15:
            recommendations.append("📊 CONGA HIGH: 1-hour glucose stability needs improvement - consistent meal absorption")
        
        # PATIENT EDUCATION & SUPPORT
        if risk_scores.get("overall_risk", 0) > 40:
            recommendations.append("📚 EDUCATION: Diabetes self-management education (DSME) referral recommended")
        
        # MONITORING RECOMMENDATIONS
        if severe_hypo_risk > 1 or severe_hyper_risk > 10:
            recommendations.append("🔍 MONITORING: Increase glucose monitoring frequency to 8+ checks/day for 1 week")
        
        # OPTIMAL CONTROL RECOGNITION
        if tir > 80 and cv < 30 and risk_scores.get("overall_risk", 0) < 20:
            recommendations.append("🏆 OUTSTANDING CONTROL: TIR >80%, CV <30%, low risk - continue current approach!")
        
        return recommendations


class DigitalTwinEngine:
    """
    ΒΕΛΤΙΩΜΕΝΟΣ Digital Twin Engine που ενσωματώνει όλα τα enhanced components
    """
    
    def __init__(self):
        self.pk_models = {}  # Cache για patient-specific models
        self.simulation_history = {}  # Track simulation history per patient
        logger.info("🧬 Enhanced Digital Twin Engine initialized")
    
    def create_patient_profile(self, patient_data: Dict[str, Any]) -> PatientProfile:
        """Create ENHANCED patient profile από real patient data"""
        
        measurements = patient_data.get('measurements', [])
        personal_details = patient_data.get('personal_details', {})
        medical_profile = patient_data.get('medical_profile', {})
        
        logger.info(f"🔍 Creating enhanced patient profile from {len(measurements)} measurements")
        
        # Enhanced measurements analysis
        latest_measurements = {}
        glucose_history = []
        
        if measurements:
            # Get glucose history για enhanced analysis
            for m in measurements[-15:]:  # Last 15 measurements για better analysis
                if m.get('blood_glucose_level'):
                    try:
                        glucose_val = float(m['blood_glucose_level'])
                        if 40 <= glucose_val <= 600:  # Reasonable range
                            glucose_history.append(glucose_val)
                    except (ValueError, TypeError):
                        continue
            
            latest = measurements[-1]
            latest_measurements = {
                'weight_kg': latest.get('weight_kg'),
                'bmi': latest.get('bmi'),
                'hba1c': latest.get('hba1c'),
                'glucose_level': latest.get('blood_glucose_level')
            }
        
        # Enhanced diabetes type detection
        conditions = medical_profile.get('conditions', [])
        diabetes_type = "T2"  # Default
        diabetes_duration = 5.0  # Default years
        
        for condition in conditions:
            condition_name = condition.get('condition_name', '').lower()
            if 'τύπου 1' in condition_name or 'type 1' in condition_name or 't1' in condition_name:
                diabetes_type = "T1"
                break
            
            # Extract duration if available
            if 'years' in condition_name or 'χρόνια' in condition_name:
                import re
                duration_match = re.search(r'(\d+)', condition_name)
                if duration_match:
                    diabetes_duration = float(duration_match.group(1))
        
        # Enhanced age calculation με fallback
        age = 45  # Default
        if personal_details.get('date_of_birth'):
            try:
                from datetime import datetime
                birth_date = datetime.fromisoformat(personal_details['date_of_birth'].replace('Z', '+00:00'))
                age = (datetime.now() - birth_date).days // 365
            except:
                pass
        elif personal_details.get('age'):
            try:
                age = int(personal_details['age'])
            except:
                pass
        
        # Enhanced parameter estimation με realistic values
        weight_kg = float(latest_measurements.get('weight_kg', 75.0))
        height_cm = float(medical_profile.get('height_cm', 170.0))
        bmi = weight_kg / (height_cm / 100) ** 2
        
        # Advanced insulin parameters based on clinical formulas
        if diabetes_type == "T1":
            base_daily_insulin = weight_kg * random.uniform(0.4, 0.6)  # 0.4-0.6 units/kg/day
            basal_percentage = random.uniform(0.45, 0.55)  # 45-55% basal
            basal_rate = base_daily_insulin * basal_percentage / 24
            insulin_sensitivity = random.uniform(40, 80)  # mg/dL per unit
            carb_ratio = random.uniform(10, 20)  # grams per unit
            correction_factor = insulin_sensitivity * random.uniform(0.9, 1.1)
        else:  # T2
            base_daily_insulin = weight_kg * random.uniform(0.6, 1.0)  # Higher for T2
            basal_percentage = random.uniform(0.5, 0.65)  # 50-65% basal
            basal_rate = base_daily_insulin * basal_percentage / 24
            insulin_sensitivity = random.uniform(25, 50)  # Lower sensitivity
            carb_ratio = random.uniform(6, 15)  # More insulin needed
            correction_factor = insulin_sensitivity * random.uniform(0.8, 1.0)
        
        # Enhanced adjustments based on control and patient factors
        if latest_measurements.get('hba1c'):
            try:
                hba1c = float(latest_measurements['hba1c'])
                if hba1c > 9.0:  # Poor control
                    insulin_sensitivity *= 0.6
                    correction_factor *= 0.6
                    carb_ratio *= 0.75
                elif hba1c > 8.0:
                    insulin_sensitivity *= 0.75
                    correction_factor *= 0.75
                    carb_ratio *= 0.85
                elif hba1c < 6.5:  # Tight control
                    insulin_sensitivity *= 1.25
                    correction_factor *= 1.25
                    carb_ratio *= 1.15
                elif hba1c < 7.0:
                    insulin_sensitivity *= 1.1
                    correction_factor *= 1.1
                    carb_ratio *= 1.05
            except (ValueError, TypeError):
                pass
        
        # Calculate enhanced physiological parameters
        glucose_cv = 0.25  # Default
        recent_glucose_mean = None
        
        if len(glucose_history) > 3:
            recent_glucose_mean = np.mean(glucose_history)
            glucose_cv = np.std(glucose_history) / recent_glucose_mean
            
            # Adjust parameters based on glucose variability
            if glucose_cv > 0.4:  # High variability
                insulin_sensitivity *= 0.9
                carb_ratio *= 0.95
            elif glucose_cv < 0.2:  # Low variability
                insulin_sensitivity *= 1.05
                carb_ratio *= 1.02
        
        # Enhanced patient-specific factors
        stress_sensitivity = 1.0
        if age > 65:
            stress_sensitivity = 1.25
        elif diabetes_duration > 15:
            stress_sensitivity = 1.2
        elif bmi > 30:
            stress_sensitivity = 1.15
        
        exercise_sensitivity = 1.0
        if bmi < 25:
            exercise_sensitivity = 1.15
        elif bmi > 30:
            exercise_sensitivity = 0.85
        elif diabetes_type == "T1":
            exercise_sensitivity = 1.1
        
        # Add realistic individual variation
        dawn_phenomenon = 0.8 + random.uniform(-0.3, 0.3)
        dusk_phenomenon = 0.3 + random.uniform(-0.15, 0.15)
        
        enhanced_profile = PatientProfile(
            weight_kg=weight_kg,
            height_cm=height_cm,
            age=age,
            diabetes_type=diabetes_type,
            insulin_sensitivity=max(15, insulin_sensitivity),  # Minimum safety
            carb_ratio=max(5, carb_ratio),  # Minimum safety
            correction_factor=max(15, correction_factor),  # Minimum safety
            basal_rate=max(0.1, basal_rate),  # Minimum safety
            glucose_absorption_rate=0.3 * (1 + random.uniform(-0.1, 0.1)),
            insulin_absorption_rate=0.15 * (1 + random.uniform(-0.05, 0.05)),
            liver_glucose_production=2.0 * (1 + random.uniform(-0.2, 0.2)),
            glucose_clearance_rate=0.05 * (1 + random.uniform(-0.1, 0.1)),
            diabetes_duration_years=diabetes_duration,
            stress_sensitivity=stress_sensitivity,
            exercise_sensitivity=exercise_sensitivity,
            meal_variability=min(0.2, glucose_cv * 0.5),
            insulin_variability=0.03 + glucose_cv * 0.1,
            recent_hba1c=latest_measurements.get('hba1c'),
            recent_glucose_mean=recent_glucose_mean,
            recent_glucose_cv=glucose_cv if glucose_history else None,
            infection_factor=1.0,  # Could be enhanced with vital signs
            dawn_phenomenon=max(0.2, min(1.5, dawn_phenomenon)),
            dusk_phenomenon=max(0.1, min(0.8, dusk_phenomenon))
        )
        
        logger.info(f"✅ Enhanced patient profile created: {diabetes_type}, Age {age}, "
                   f"BMI {bmi:.1f}, Insulin sensitivity {insulin_sensitivity:.0f}, "
                   f"Carb ratio {carb_ratio:.1f}")
        
        return enhanced_profile
    
    def get_current_state(self, patient_data: Dict[str, Any]) -> List[float]:
        """Get ENHANCED initial state με realistic values"""
        
        measurements = patient_data.get('measurements', [])
        
        # Enhanced initial state estimation
        if measurements:
            latest = measurements[-1]
            try:
                initial_glucose = float(latest.get('blood_glucose_level', 120))
                # Add some realistic variation
                initial_glucose += random.uniform(-15, 25)
            except (ValueError, TypeError):
                initial_glucose = 120 + random.uniform(-20, 40)
        else:
            initial_glucose = 120 + random.uniform(-30, 50)
        
        # Estimate insulin levels based on recent therapy and glucose
        if initial_glucose < 80:
            initial_insulin = random.uniform(15, 25)  # Higher insulin if low glucose
        elif initial_glucose > 200:
            initial_insulin = random.uniform(5, 12)   # Lower insulin if high glucose
        else:
            initial_insulin = random.uniform(8, 18)   # Normal range
        
        # Enhanced state vector - 6 compartments
        enhanced_state = [
            max(40, initial_glucose),  # Plasma glucose με minimum
            max(2, initial_insulin),   # Plasma insulin με minimum
            0.0,  # Subcutaneous insulin depot - fast acting
            random.uniform(1.0, 4.0),  # Subcutaneous insulin depot - long acting
            max(40, initial_glucose + random.uniform(-8, 8)),  # Interstitial glucose
            random.uniform(160, 220)  # Liver glucose stores
        ]
        
        logger.info(f"🎯 Enhanced initial state: Glucose {enhanced_state[0]:.0f} mg/dL, "
                   f"Insulin {enhanced_state[1]:.1f} mU/L")
        
        return enhanced_state
    
    async def simulate_what_if_scenario(self, patient_data: Dict[str, Any], 
                                      scenario_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        ΒΕΛΤΙΩΜΕΝΗ What-If scenario simulation με enhanced features
        """
        
        try:
            logger.info("🚀 Starting enhanced What-If scenario simulation")
            
            # Create enhanced patient profile
            patient_profile = self.create_patient_profile(patient_data)
            
            # Create enhanced pharmacokinetic model
            pk_model = DiabetesPharmacokineticModel(patient_profile)
            
            # Get enhanced current physiological state
            initial_state = self.get_current_state(patient_data)
            
            # Create enhanced scenario parameters
            scenario = ScenarioParams(**scenario_params)
            
            # Run enhanced simulation
            result = pk_model.simulate_scenario(initial_state, scenario, patient_data)
            
            # Enhanced results formatting με JSON serialization fix
            formatted_result = {
                "success": True,
                "patient_profile": convert_numpy_types(asdict(patient_profile)),
                "simulation_results": {
                    "time_points": result.time_points,
                    "glucose_levels": result.glucose_levels,
                    "insulin_levels": result.insulin_levels,
                    "glucose_metrics": convert_numpy_types(result.glucose_metrics),
                    "risk_scores": convert_numpy_types(result.risk_scores),
                    "safety_alerts": result.safety_alerts,
                    "recommendations": result.recommendations,
                    "scenario_summary": convert_numpy_types(result.scenario_summary)
                },
                "mindmap_data": convert_numpy_types(self._create_enhanced_mindmap_data(result, scenario, patient_profile)),
                "comparison_data": convert_numpy_types(self._create_enhanced_comparison_data(result, patient_data, patient_profile)),
                "advanced_analytics": convert_numpy_types({
                    "model_confidence": self._calculate_model_confidence(patient_data, result),
                    "clinical_significance": self._assess_clinical_significance(result),
                    "simulation_quality": result.scenario_summary.get("simulation_quality", {}),
                    "patient_factors": {
                        "insulin_resistance": pk_model.insulin_resistance_factor,
                        "metabolic_rate": pk_model.metabolic_rate_factor,
                        "exercise_sensitivity": patient_profile.exercise_sensitivity,
                        "stress_sensitivity": patient_profile.stress_sensitivity
                    }
                })
            }
            
            logger.info("✅ Enhanced What-If simulation completed successfully")
            return formatted_result
            
        except Exception as e:
            logger.error(f"❌ Enhanced digital twin simulation error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Σφάλμα στην προηγμένη προσομοίωση. Παρακαλώ ελέγξτε τα δεδομένα και δοκιμάστε ξανά."
            }
    
    def _create_enhanced_mindmap_data(self, result: SimulationResult, scenario: ScenarioParams, 
                                    patient_profile: PatientProfile) -> Dict[str, Any]:
        """Enhanced mindmap με πρόσθετα clinical insights"""
        
        mindmap = {
            "id": "enhanced_scenario_root",
            "label": f"Enhanced Digital Twin",
            "type": "root",
            "data": {
                "patient_type": patient_profile.diabetes_type,
                "overall_risk": result.risk_scores["overall_risk"],
                "tir": result.glucose_metrics["tir_70_180"],
                "confidence": "HIGH",
                "simulation_quality": "ENHANCED"
            },
            "children": []
        }
        
        # Patient Characteristics Node με enhanced data
        patient_node = {
            "id": "patient_profile",
            "label": "Patient Profile", 
            "type": "category",
            "data": {"icon": "👤", "color": "#9c27b0"},
            "children": [
                {
                    "id": "diabetes_type",
                    "label": f"Type {patient_profile.diabetes_type}",
                    "type": "info",
                    "data": {"value": patient_profile.diabetes_type, "color": "#e91e63"}
                },
                {
                    "id": "duration",
                    "label": f"{patient_profile.diabetes_duration_years:.0f} years",
                    "type": "info", 
                    "data": {"value": patient_profile.diabetes_duration_years, "color": "#ff9800"}
                },
                {
                    "id": "age_group",
                    "label": f"Age {patient_profile.age}",
                    "type": "info",
                    "data": {"value": patient_profile.age, "color": "#607d8b"}
                }
            ]
        }
        mindmap["children"].append(patient_node)
        
        # Enhanced Parameters Node
        params_node = {
            "id": "enhanced_parameters",
            "label": "Scenario Parameters",
            "type": "category",
            "data": {"icon": "⚙️", "color": "#2196f3"},
            "children": []
        }
        
        if scenario.basal_change != 0:
            params_node["children"].append({
                "id": "basal",
                "label": f"Basal {scenario.basal_change:+.0f}%",
                "type": "parameter",
                "data": {
                    "value": scenario.basal_change, 
                    "color": "#f44336" if abs(scenario.basal_change) > 30 else "#2196f3"
                }
            })
        
        if scenario.bolus_change != 0:
            params_node["children"].append({
                "id": "bolus",
                "label": f"Bolus {scenario.bolus_change:+.0f}%",
                "type": "parameter",
                "data": {
                    "value": scenario.bolus_change,
                    "color": "#f44336" if abs(scenario.bolus_change) > 30 else "#ff9800"
                }
            })
        
        if scenario.meal_carbs > 0:
            params_node["children"].append({
                "id": "meal",
                "label": f"Meal {scenario.meal_carbs:.0f}g",
                "type": "parameter",
                "data": {
                    "value": scenario.meal_carbs,
                    "color": "#ff9800" if scenario.meal_carbs > 80 else "#4caf50"
                }
            })
        
        if scenario.exercise_intensity > 0:
            params_node["children"].append({
                "id": "exercise",
                "label": f"Exercise {scenario.exercise_intensity:.0f}%",
                "type": "parameter",
                "data": {
                    "value": scenario.exercise_intensity,
                    "color": "#4caf50"
                }
            })
        
        mindmap["children"].append(params_node)
        
        # Enhanced Outcomes Node
        outcomes_node = {
            "id": "enhanced_outcomes",
            "label": "Clinical Outcomes",
            "type": "category",
            "data": {"icon": "📊", "color": "#4caf50"},
            "children": [
                {
                    "id": "tir_70_180",
                    "label": f"TIR 70-180: {result.glucose_metrics['tir_70_180']:.0f}%",
                    "type": "outcome",
                    "data": {
                        "value": result.glucose_metrics["tir_70_180"],
                        "color": "#4caf50" if result.glucose_metrics["tir_70_180"] > 70 else "#ff9800"
                    }
                },
                {
                    "id": "mean_glucose",
                    "label": f"Mean: {result.glucose_metrics['mean_glucose']:.0f} mg/dL",
                    "type": "outcome",
                    "data": {
                        "value": result.glucose_metrics["mean_glucose"],
                        "color": "#2196f3"
                    }
                },
                {
                    "id": "cv",
                    "label": f"CV: {result.glucose_metrics['glucose_cv']:.0f}%",
                    "type": "outcome",
                    "data": {
                        "value": result.glucose_metrics["glucose_cv"],
                        "color": "#4caf50" if result.glucose_metrics["glucose_cv"] < 36 else "#ff9800"
                    }
                },
                {
                    "id": "estimated_hba1c",
                    "label": f"Est. HbA1c: {result.glucose_metrics['estimated_hba1c']:.1f}%",
                    "type": "outcome",
                    "data": {
                        "value": result.glucose_metrics["estimated_hba1c"],
                        "color": "#4caf50" if result.glucose_metrics["estimated_hba1c"] < 7.0 else "#ff9800"
                    }
                }
            ]
        }
        
        mindmap["children"].append(outcomes_node)
        
        # Enhanced Risks Node με detailed breakdown
        risks_node = {
            "id": "enhanced_risks",
            "label": "Risk Assessment",
            "type": "category",
            "data": {"icon": "⚠️", "color": "#f44336"},
            "children": []
        }
        
        # Only show significant risks
        significant_risks = {k: v for k, v in result.risk_scores.items() if v > 5}
        for risk_name, risk_value in significant_risks.items():
            color = "#f44336" if risk_value > 25 else "#ff9800" if risk_value > 15 else "#ffeb3b"
            display_name = risk_name.replace('_', ' ').title()
            
            risks_node["children"].append({
                "id": f"risk_{risk_name}",
                "label": f"{display_name}: {risk_value:.0f}%",
                "type": "risk",
                "data": {"value": risk_value, "color": color}
            })
        
        if risks_node["children"]:
            mindmap["children"].append(risks_node)
        
        # Enhanced Recommendations Node (top 3)
        if result.recommendations:
            rec_node = {
                "id": "enhanced_recommendations",
                "label": "AI Recommendations",
                "type": "category",
                "data": {"icon": "💡", "color": "#9c27b0"},
                "children": []
            }
            
            for i, rec in enumerate(result.recommendations[:3]):  # Top 3
                # Extract emoji and priority
                priority_color = "#4caf50"  # Default
                if "🚨" in rec or "ΚΡΙΤΙΚΟ" in rec:
                    priority_color = "#f44336"
                elif "⚠️" in rec or "ΥΨΗΛΗ" in rec:
                    priority_color = "#ff9800"
                
                rec_node["children"].append({
                    "id": f"rec_{i}",
                    "label": rec[:45] + "..." if len(rec) > 45 else rec,
                    "type": "recommendation",
                    "data": {"full_text": rec, "color": priority_color}
                })
            
            mindmap["children"].append(rec_node)
        
        return mindmap
    
    def _create_enhanced_comparison_data(self, result: SimulationResult, patient_data: Dict[str, Any],
                                       patient_profile: PatientProfile) -> Dict[str, Any]:
        """Enhanced comparison με realistic baselines"""
        
        measurements = patient_data.get('measurements', [])
        
        # Enhanced baseline estimation από patient data
        if measurements and len(measurements) >= 3:
            recent_glucose = []
            for m in measurements[-10:]:  # Last 10 measurements
                if m.get('blood_glucose_level'):
                    try:
                        glucose = float(m['blood_glucose_level'])
                        if 40 <= glucose <= 600:  # Reasonable range
                            recent_glucose.append(glucose)
                    except (ValueError, TypeError):
                        continue
            
            if recent_glucose:
                baseline_glucose = np.mean(recent_glucose)
                baseline_cv = (np.std(recent_glucose) / np.mean(recent_glucose)) * 100
            else:
                baseline_glucose = 160  # Conservative estimate
                baseline_cv = 38
        else:
            baseline_glucose = 160  # Conservative estimate for limited data
            baseline_cv = 40
        
        # Enhanced HbA1c estimation
        baseline_hba1c = patient_profile.recent_hba1c or (baseline_glucose + 46.7) / 28.7
        
        # Enhanced TIR estimation based on HbA1c or glucose data
        if baseline_hba1c:
            # Rough TIR estimation from HbA1c (clinical correlation)
            if baseline_hba1c < 6.5:
                baseline_tir = random.uniform(80, 95)
            elif baseline_hba1c < 7.0:
                baseline_tir = random.uniform(65, 80)
            elif baseline_hba1c < 8.0:
                baseline_tir = random.uniform(45, 65)
            elif baseline_hba1c < 9.0:
                baseline_tir = random.uniform(25, 45)
            else:
                baseline_tir = random.uniform(10, 30)
        else:
            baseline_tir = max(15, 100 - (baseline_glucose - 100) * 0.4)
        
        return {
            "baseline": {
                "glucose": baseline_glucose,
                "hba1c": baseline_hba1c,
                "tir_70_180": baseline_tir,
                "glucose_cv": baseline_cv,
                "estimated": len(measurements) < 3,
                "data_quality": "HIGH" if len(measurements) >= 10 else "MODERATE" if len(measurements) >= 5 else "LIMITED"
            },
            "scenario": {
                "glucose": result.glucose_metrics["mean_glucose"],
                "hba1c": result.glucose_metrics["estimated_hba1c"],
                "tir_70_180": result.glucose_metrics["tir_70_180"],
                "glucose_cv": result.glucose_metrics["glucose_cv"],
                "estimated": False,
                "simulation_quality": "ENHANCED"
            },
            "improvements": {
                "glucose_change": result.glucose_metrics["mean_glucose"] - baseline_glucose,
                "hba1c_change": result.glucose_metrics["estimated_hba1c"] - baseline_hba1c,
                "tir_improvement": result.glucose_metrics["tir_70_180"] - baseline_tir,
                "cv_improvement": baseline_cv - result.glucose_metrics["glucose_cv"]
            },
            "clinical_significance": {
                "glucose_meaningful": abs(result.glucose_metrics["mean_glucose"] - baseline_glucose) > 15,
                "hba1c_meaningful": abs(result.glucose_metrics["estimated_hba1c"] - baseline_hba1c) > 0.3,
                "tir_meaningful": abs(result.glucose_metrics["tir_70_180"] - baseline_tir) > 5,
                "cv_meaningful": abs(baseline_cv - result.glucose_metrics["glucose_cv"]) > 5
            },
            "interpretation": {
                "overall_improvement": (
                    (result.glucose_metrics["tir_70_180"] - baseline_tir) > 5 and
                    (baseline_cv - result.glucose_metrics["glucose_cv"]) > 3 and
                    result.risk_scores["overall_risk"] < 30
                ),
                "safety_maintained": result.risk_scores["severe_hypoglycemia_risk"] < 3,
                "clinically_significant": (
                    abs(result.glucose_metrics["estimated_hba1c"] - baseline_hba1c) > 0.3 or
                    abs(result.glucose_metrics["tir_70_180"] - baseline_tir) > 10
                )
            }
        }
    
    def _calculate_model_confidence(self, patient_data: Dict[str, Any], result: SimulationResult) -> float:
        """Enhanced model confidence calculation"""
        confidence = 65  # Enhanced base confidence
        
        measurements = patient_data.get('measurements', [])
        
        # Data quantity bonus
        if len(measurements) > 20:
            confidence += 20
        elif len(measurements) > 10:
            confidence += 15
        elif len(measurements) > 5:
            confidence += 10
        elif len(measurements) < 3:
            confidence -= 15
        
        # Data quality bonus
        glucose_measurements = [m for m in measurements if m.get('blood_glucose_level')]
        if len(glucose_measurements) > 10:
            confidence += 10
        
        # HbA1c data bonus
        hba1c_available = any(m.get('hba1c') for m in measurements)
        if hba1c_available:
            confidence += 10
        
        # Recent data bonus
        if measurements:
            latest = measurements[-1]
            if latest.get('hba1c') and latest.get('blood_glucose_level'):
                confidence += 10
        
        # Simulation quality factors
        overall_risk = result.risk_scores.get("overall_risk", 50)
        if 15 <= overall_risk <= 40:  # Reasonable risk range
            confidence += 10
        elif overall_risk > 60:
            confidence -= 10
        
        # Parameter reasonableness
        scenario_summary = result.scenario_summary
        if scenario_summary:
            insulin_resistance = scenario_summary.get("insulin_resistance_factor", 1.0)
            if 0.8 <= insulin_resistance <= 2.0:  # Reasonable range
                confidence += 5
        
        # Glucose metrics reasonableness
        tir = result.glucose_metrics.get("tir_70_180", 0)
        cv = result.glucose_metrics.get("glucose_cv", 0)
        
        if 40 <= tir <= 95 and 15 <= cv <= 60:  # Realistic ranges
            confidence += 5
        
        return min(95, max(30, confidence))
    
    def _assess_clinical_significance(self, result: SimulationResult) -> Dict[str, Any]:
        """Enhanced clinical significance assessment"""
        
        tir = result.glucose_metrics["tir_70_180"]
        cv = result.glucose_metrics["glucose_cv"]
        hba1c = result.glucose_metrics["estimated_hba1c"]
        overall_risk = result.risk_scores["overall_risk"]
        
        # Enhanced clinical assessment
        significance = {
            "level": "MODERATE",
            "clinical_impact": "MEANINGFUL",
            "action_required": "MONITORING",
            "evidence_strength": "GOOD"
        }
        
        # Excellent control
        if tir > 85 and cv < 25 and hba1c < 7.0 and overall_risk < 20:
            significance.update({
                "level": "HIGH",
                "clinical_impact": "EXCELLENT",
                "action_required": "CONTINUE_CURRENT",
                "evidence_strength": "STRONG",
                "recommendation": "Outstanding glucose management - maintain current approach"
            })
        # Concerning results
        elif tir < 50 or result.risk_scores["severe_hypoglycemia_risk"] > 5 or overall_risk > 60:
            significance.update({
                "level": "HIGH", 
                "clinical_impact": "CONCERNING",
                "action_required": "IMMEDIATE_REVIEW",
                "evidence_strength": "STRONG",
                "recommendation": "Immediate clinical review required - high risk scenario"
            })
        # Good control
        elif tir > 70 and cv < 36 and overall_risk < 35:
            significance.update({
                "level": "MODERATE",
                "clinical_impact": "POSITIVE",
                "action_required": "OPTIMIZE",
                "evidence_strength": "GOOD",
                "recommendation": "Good control with room for optimization"
            })
        # Poor control
        elif tir < 60 or cv > 40 or hba1c > 8.5:
            significance.update({
                "level": "MODERATE",
                "clinical_impact": "NEEDS_IMPROVEMENT",
                "action_required": "ADJUST_THERAPY",
                "evidence_strength": "GOOD",
                "recommendation": "Significant therapy adjustments needed"
            })
        
        # Add specific clinical targets achievement - FIXED for JSON serialization
        significance["targets_achieved"] = convert_numpy_types({
            "tir_target": bool(tir > 70),  # ADA/EASD target
            "cv_target": bool(cv < 36),    # <36% CV target
            "hba1c_target": bool(hba1c < 7.0),  # <7% for most adults
            "safety_target": bool(result.risk_scores["severe_hypoglycemia_risk"] < 1)
        })
        
        # Calculate overall target achievement score
        targets_met = sum(significance["targets_achieved"].values())
        significance["target_achievement_score"] = f"{targets_met}/4 targets achieved"
        
        return significance


# Global instance
digital_twin_engine = DigitalTwinEngine()
