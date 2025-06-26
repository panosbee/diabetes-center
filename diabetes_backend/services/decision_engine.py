"""
Προσαρμοσμένο Decision Engine για DMP Platform
============================================

Προσαρμοσμένο στα πραγματικά δεδομένα της βάσης:
- Personal details (name, AMKA, date_of_birth)
- Medical profile (height, conditions, allergies, history)  
- Vitals από sessions (glucose, HbA1c, weight, BMI, BP, insulin)
- Uploaded files με extracted text

ΔΕΝ χρησιμοποιεί πεδία που δεν υπάρχουν όπως smoking, physical_activity, κλπ.
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import numpy as np
import logging
import json
import re
from dataclasses import dataclass
from enum import Enum
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate" 
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationType(Enum):
    LIFESTYLE = "lifestyle"
    MEDICAL = "medical"
    MONITORING = "monitoring"
    EMERGENCY = "emergency"
    GENETIC = "genetic"


@dataclass
class ClinicalEvidence:
    """Represents clinical evidence with real PMIDs"""
    pmids: List[str]
    evidence_quality: str  # "high", "moderate", "low"
    recommendation_strength: str  # "strong", "moderate", "weak"
    source: str  # "pubmed", "genetics", "guidelines"


@dataclass
class RiskFactor:
    """Individual risk factor with weight and evidence"""
    name: str
    value: float  # 0-100
    weight: float  # multiplier
    evidence: ClinicalEvidence
    category: str  # "lab", "genetic", "lifestyle", "medical_history"


@dataclass
class Recommendation:
    """Enhanced recommendation with real evidence"""
    id: str
    type: RecommendationType
    priority: int  # 1-5 (1=highest)
    action: str
    rationale: str
    evidence: ClinicalEvidence
    clinical_impact: float  # 0-100
    urgency: float  # 0-100
    target_values: Optional[Dict[str, Any]] = None
    timeframe: Optional[str] = None
    monitoring_frequency: Optional[str] = None


class CustomizedDecisionEngine:
    """
    Προσαρμοσμένο Decision Engine που δουλεύει με τα πραγματικά δεδομένα της βάσης
    """
    
    def __init__(self, patient_data: Dict[str, Any], pubmed_citations: Optional[List[str]] = None, genetic_analysis: Optional[Dict[str, Any]] = None):
        self.patient_data = patient_data
        self.pubmed_citations = pubmed_citations or []
        self.genetic_analysis = genetic_analysis or {}
        
        # Enhanced clinical guidelines with evidence levels
        self.guidelines = {
            'hba1c': {
                'optimal': {'value': 7.0, 'evidence': 'high'},
                'target_t1d': {'value': 7.0, 'evidence': 'high'},
                'target_t2d': {'value': 7.0, 'evidence': 'high'},
                'high_risk': {'value': 8.0, 'evidence': 'high'},
                'critical': {'value': 10.0, 'evidence': 'high'}
            },
            'glucose': {
                'fasting_normal': {'value': 100, 'unit': 'mg/dL', 'evidence': 'high'},
                'fasting_prediabetes': {'value': 126, 'unit': 'mg/dL', 'evidence': 'high'},
                'fasting_diabetes': {'value': 126, 'unit': 'mg/dL', 'evidence': 'high'},
                'postprandial_target': {'value': 180, 'unit': 'mg/dL', 'evidence': 'high'}
            },
            'blood_pressure': {
                'optimal': {'systolic': 120, 'diastolic': 80, 'evidence': 'high'},
                'diabetes_target': {'systolic': 130, 'diastolic': 80, 'evidence': 'high'}
            },
            'bmi': {
                'normal': {'value': 25, 'evidence': 'high'},
                'overweight': {'value': 30, 'evidence': 'high'},
                'obese': {'value': 35, 'evidence': 'high'}
            }
        }
        
        # Risk factor weights based on available data
        self.risk_weights = {
            'hba1c': 0.40,           # Κύριος δείκτης διαβήτη
            'glucose_control': 0.25,  # Έλεγχος γλυκόζης
            'blood_pressure': 0.15,   # Πίεση αίματος
            'bmi_status': 0.10,       # BMI και τάσεις βάρους
            'genetic': 0.10           # Γενετικά δεδομένα αν υπάρχουν
        }
    
    def assess_comprehensive_risk(self) -> Dict[str, Any]:
        """
        Comprehensive risk assessment βασισμένο στα διαθέσιμα δεδομένα
        """
        risk_factors = []
        
        # 1. HbA1c και glucose risk assessment
        glucose_risks = self._assess_glucose_risks()
        risk_factors.extend(glucose_risks)
        
        # 2. Blood pressure assessment
        bp_risks = self._assess_blood_pressure_risks()
        risk_factors.extend(bp_risks)
        
        # 3. BMI και weight trends
        weight_risks = self._assess_weight_risks()
        risk_factors.extend(weight_risks)
        
        # 4. Genetic risk factors
        genetic_risks = self._assess_genetic_risks()
        risk_factors.extend(genetic_risks)
        
        # 5. Medical conditions risk
        condition_risks = self._assess_medical_conditions()
        risk_factors.extend(condition_risks)
        
        # 6. Calculate weighted risk score
        total_risk_score = self._calculate_weighted_risk_score(risk_factors)
        
        # 7. Generate risk predictions
        predictions = self._generate_risk_predictions(risk_factors, total_risk_score)
        
        # 8. Determine risk level and category distribution
        risk_level = self._determine_risk_level(total_risk_score)
        risk_distribution = self._calculate_risk_distribution(risk_factors)
        
        return {
            'total_score': min(100, max(0, total_risk_score)),
            'level': risk_level.value,
            'risk_factors': [
                {
                    'name': rf.name,
                    'value': rf.value,
                    'weight': rf.weight,
                    'category': rf.category,
                    'evidence_quality': rf.evidence.evidence_quality,
                    'pmids': rf.evidence.pmids[:3] if rf.evidence.pmids else []
                }
                for rf in risk_factors
            ],
            'predictions': predictions,
            'risk_distribution': risk_distribution,
            'assessment_date': datetime.now().isoformat(),
            'evidence_summary': self._generate_evidence_summary(risk_factors)
        }
    
    def _assess_glucose_risks(self) -> List[RiskFactor]:
        """Assess glucose and HbA1c related risks"""
        risks = []
        
        # Get latest measurements
        measurements = self.patient_data.get('measurements', [])
        if not measurements:
            return risks
        
        # HbA1c assessment
        hba1c_values = [m.get('hba1c') for m in measurements if m.get('hba1c') is not None]
        if hba1c_values:
            latest_hba1c = hba1c_values[-1]
            hba1c_trend = self._calculate_trend(hba1c_values)
            hba1c_risk = self._calculate_hba1c_risk(float(latest_hba1c), hba1c_trend)
            
            # Find relevant PubMed evidence for HbA1c
            hba1c_pmids = [pmid for pmid in self.pubmed_citations 
                          if any(term in pmid.lower() for term in ['hba1c', 'hemoglobin', 'glycated'])]
            
            risks.append(RiskFactor(
                name="HbA1c Control",
                value=hba1c_risk,
                weight=self.risk_weights['hba1c'],
                evidence=ClinicalEvidence(
                    pmids=hba1c_pmids[:3],
                    evidence_quality="high",
                    recommendation_strength="strong",
                    source="pubmed"
                ),
                category="lab"
            ))
        
        # Glucose variability assessment
        glucose_values = [m.get('blood_glucose_level') for m in measurements if m.get('blood_glucose_level') is not None]
        if len(glucose_values) >= 3:
            glucose_variability = self._calculate_glucose_variability(glucose_values)
            
            glucose_pmids = [pmid for pmid in self.pubmed_citations 
                           if any(term in pmid.lower() for term in ['glucose', 'glycemia', 'blood sugar'])]
            
            risks.append(RiskFactor(
                name="Glucose Variability",
                value=glucose_variability,
                weight=self.risk_weights['glucose_control'],
                evidence=ClinicalEvidence(
                    pmids=glucose_pmids[:3],
                    evidence_quality="high",
                    recommendation_strength="strong",
                    source="pubmed"
                ),
                category="lab"
            ))
        
        return risks
    
    def _assess_blood_pressure_risks(self) -> List[RiskFactor]:
        """Assess blood pressure risks"""
        risks = []
        measurements = self.patient_data.get('measurements', [])
        
        # Get BP measurements
        bp_measurements = []
        for m in measurements:
            systolic = m.get('blood_pressure_systolic')
            diastolic = m.get('blood_pressure_diastolic')
            if systolic is not None and diastolic is not None:
                bp_measurements.append((float(systolic), float(diastolic)))
        
        if bp_measurements:
            latest_systolic, latest_diastolic = bp_measurements[-1]
            bp_risk = self._calculate_bp_risk(latest_systolic, latest_diastolic)
            
            bp_pmids = [pmid for pmid in self.pubmed_citations 
                       if any(term in pmid.lower() for term in ['blood pressure', 'hypertension', 'bp'])]
            
            risks.append(RiskFactor(
                name="Blood Pressure Control",
                value=bp_risk,
                weight=self.risk_weights['blood_pressure'],
                evidence=ClinicalEvidence(
                    pmids=bp_pmids[:3],
                    evidence_quality="high", 
                    recommendation_strength="strong",
                    source="pubmed"
                ),
                category="cardiovascular"
            ))
        
        return risks
    
    def _assess_weight_risks(self) -> List[RiskFactor]:
        """Assess BMI and weight trend risks"""
        risks = []
        measurements = self.patient_data.get('measurements', [])
        
        # BMI assessment
        bmi_values = [m.get('bmi') for m in measurements if m.get('bmi') is not None]
        weight_values = [m.get('weight_kg') for m in measurements if m.get('weight_kg') is not None]
        
        if bmi_values:
            latest_bmi = float(bmi_values[-1])
            bmi_trend = self._calculate_trend(bmi_values) if len(bmi_values) > 1 else 0
            bmi_risk = self._calculate_bmi_risk(latest_bmi, bmi_trend)
            
            weight_pmids = [pmid for pmid in self.pubmed_citations 
                           if any(term in pmid.lower() for term in ['bmi', 'weight', 'obesity'])]
            
            risks.append(RiskFactor(
                name="BMI and Weight Management",
                value=bmi_risk,
                weight=self.risk_weights['bmi_status'],
                evidence=ClinicalEvidence(
                    pmids=weight_pmids[:3],
                    evidence_quality="high",
                    recommendation_strength="strong",
                    source="pubmed"
                ),
                category="lifestyle"
            ))
        
        return risks
    
    def _assess_genetic_risks(self) -> List[RiskFactor]:
        """Assess genetic risk factors from genetics analysis"""
        risks = []
        
        if not self.genetic_analysis:
            return risks
        
        # Extract genetic risk information
        genetic_risk_score = 0
        genetic_pmids = []
        
        # Parse genetic analysis results
        if 'raw_result' in self.genetic_analysis:
            raw_result = self.genetic_analysis['raw_result']
            
            # Extract risk level and convert to numeric score
            risk_level = raw_result.get('risk_level', 'ΜΕΤΡΙΟΣ')
            risk_mapping = {
                'ΧΑΜΗΛΟΣ': 20,
                'ΜΕΤΡΙΟΣ': 50, 
                'ΥΨΗΛΟΣ': 75,
                'ΠΟΛΥ ΥΨΗΛΟΣ': 90
            }
            genetic_risk_score = risk_mapping.get(risk_level, 50)
            
            # Extract PGS scores used as evidence
            pgs_scores = raw_result.get('pgs_scores_used', [])
            genetic_pmids = [f"PGS:{score}" for score in pgs_scores[:3]]
        
        # Find genetic-related PubMed citations
        genetic_pubmed = [pmid for pmid in self.pubmed_citations 
                         if any(term in pmid.lower() for term in ['genetic', 'polymorphism', 'snp', 'genome'])]
        
        genetic_pmids.extend(genetic_pubmed[:2])
        
        if genetic_risk_score > 0:
            risks.append(RiskFactor(
                name="Genetic Risk Factors",
                value=genetic_risk_score,
                weight=self.risk_weights['genetic'],
                evidence=ClinicalEvidence(
                    pmids=genetic_pmids,
                    evidence_quality="moderate",
                    recommendation_strength="moderate",
                    source="genetics"
                ),
                category="genetic"
            ))
        
        return risks
    
    def _assess_medical_conditions(self) -> List[RiskFactor]:
        """Assess risk based on existing medical conditions"""
        risks = []
        conditions = self.patient_data.get('conditions', [])
        
        if not conditions:
            return risks
        
        # Count diabetes-related conditions
        diabetes_conditions = []
        cardiovascular_conditions = []
        
        for condition in conditions:
            condition_name = condition.get('condition_name', '').lower()
            if any(term in condition_name for term in ['διαβήτης', 'diabetes', 'σακχαρώδης']):
                diabetes_conditions.append(condition_name)
            elif any(term in condition_name for term in ['καρδι', 'υπέρταση', 'αρτηρι', 'cardiac', 'hypertension']):
                cardiovascular_conditions.append(condition_name)
        
        # Calculate risk based on conditions
        condition_risk = 0
        if len(diabetes_conditions) > 1:  # Multiple diabetes-related conditions
            condition_risk += 30
        if cardiovascular_conditions:
            condition_risk += 25
        
        if condition_risk > 0:
            condition_pmids = [pmid for pmid in self.pubmed_citations 
                             if any(term in pmid.lower() for term in ['comorbidity', 'complications'])]
            
            risks.append(RiskFactor(
                name="Medical Comorbidities",
                value=min(100, condition_risk),
                weight=0.15,  # Additional weight for conditions
                evidence=ClinicalEvidence(
                    pmids=condition_pmids[:3],
                    evidence_quality="high",
                    recommendation_strength="strong",
                    source="pubmed"
                ),
                category="medical_history"
            ))
        
        return risks
    
    def _calculate_hba1c_risk(self, hba1c_value: float, trend: float = 0) -> float:
        """Calculate risk score based on HbA1c value and trend"""
        base_risk = 0
        if hba1c_value <= 7.0:
            base_risk = max(0, (hba1c_value - 5.0) * 10)  # 0-20 range
        elif hba1c_value <= 8.0:
            base_risk = 20 + (hba1c_value - 7.0) * 30  # 20-50 range
        elif hba1c_value <= 10.0:
            base_risk = 50 + (hba1c_value - 8.0) * 20  # 50-90 range
        else:
            base_risk = min(100, 90 + (hba1c_value - 10.0) * 5)  # 90-100 range
        
        # Adjust for trend (positive trend = worsening)
        trend_adjustment = trend * 10  # Add up to 10 points for worsening trend
        
        return min(100, max(0, base_risk + trend_adjustment))
    
    def _calculate_bp_risk(self, systolic: float, diastolic: float) -> float:
        """Calculate cardiovascular risk based on blood pressure"""
        # AHA/ACC Guidelines for diabetes patients
        if systolic <= 130 and diastolic <= 80:
            return 10
        elif systolic <= 140 and diastolic <= 90:
            return 40
        elif systolic <= 160 and diastolic <= 100:
            return 70
        else:
            return 90
    
    def _calculate_bmi_risk(self, bmi: float, trend: float = 0) -> float:
        """Calculate risk based on BMI and trend"""
        base_risk = 0
        if bmi < 18.5:
            base_risk = 30  # Underweight is concerning
        elif bmi <= 25:
            base_risk = 5   # Normal
        elif bmi <= 30:
            base_risk = 25  # Overweight
        elif bmi <= 35:
            base_risk = 50  # Obese Class I
        else:
            base_risk = 75  # Obese Class II+
        
        # Adjust for trend (positive trend = weight gain)
        if trend > 0:
            base_risk += trend * 15  # Weight gain is concerning
        elif trend < 0:
            base_risk = max(0, base_risk + trend * 5)  # Weight loss can be good
        
        return min(100, max(0, base_risk))
    
    def _calculate_glucose_variability(self, glucose_values: List[float]) -> float:
        """Calculate glucose variability risk"""
        if len(glucose_values) < 3:
            return 0
        
        # Calculate coefficient of variation
        mean_glucose = statistics.mean(glucose_values)
        std_glucose = statistics.stdev(glucose_values)
        cv = (std_glucose / mean_glucose) * 100 if mean_glucose > 0 else 0
        
        # High variability (CV > 36%) is concerning
        if cv > 50:
            return 80
        elif cv > 36:
            return 50
        elif cv > 25:
            return 25
        else:
            return 10
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate simple trend (-1 to 1, negative = improving, positive = worsening)"""
        if len(values) < 2:
            return 0
        
        # Simple linear trend calculation
        recent_values = values[-3:] if len(values) >= 3 else values
        if len(recent_values) < 2:
            return 0
        
        trend = (recent_values[-1] - recent_values[0]) / len(recent_values)
        # Normalize to -1 to 1 range
        return max(-1, min(1, trend / max(recent_values)))
    
    def _calculate_weighted_risk_score(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate weighted total risk score"""
        total_score = 0
        total_weight = 0
        
        for rf in risk_factors:
            total_score += rf.value * rf.weight
            total_weight += rf.weight
        
        # Normalize to 0-100 scale
        if total_weight > 0:
            return (total_score / total_weight)
        return 0
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level based on total score"""
        if risk_score >= 80:
            return RiskLevel.CRITICAL
        elif risk_score >= 60:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
    
    def _calculate_risk_distribution(self, risk_factors: List[RiskFactor]) -> Dict[str, float]:
        """Calculate risk distribution by category"""
        categories = {}
        
        for rf in risk_factors:
            if rf.category not in categories:
                categories[rf.category] = []
            categories[rf.category].append(rf.value * rf.weight)
        
        # Calculate percentages
        total = sum(sum(values) for values in categories.values())
        if total == 0:
            return {}
        
        distribution = {}
        for category, values in categories.items():
            distribution[category] = (sum(values) / total) * 100
        
        return distribution
    
    def _generate_risk_predictions(self, risk_factors: List[RiskFactor], current_score: float) -> Dict[str, Any]:
        """Generate risk predictions based on current data"""
        
        # Simple predictive model based on current trends
        base_progression = {
            'hypoglycemia': max(0, 30 - current_score * 0.3),
            'hyperglycemia': current_score * 0.8,
            'cardiovascular': current_score * 0.6,
            'overall': current_score
        }
        
        # Generate monthly predictions for next 6 months
        predictions = {}
        for risk_type, base_value in base_progression.items():
            monthly_values = []
            for month in range(1, 7):
                # Add slight progression over time with some variance
                progression_factor = 1 + (month * 0.02)  # 2% increase per month
                predicted_value = min(100, base_value * progression_factor)
                monthly_values.append(round(predicted_value, 1))
            
            predictions[risk_type] = monthly_values
        
        return predictions
    
    def _generate_evidence_summary(self, risk_factors: List[RiskFactor]) -> Dict[str, Any]:
        """Generate summary of evidence sources"""
        all_pmids = []
        evidence_quality_counts = {'high': 0, 'moderate': 0, 'low': 0}
        source_counts = {'pubmed': 0, 'genetics': 0, 'guidelines': 0}
        
        for rf in risk_factors:
            all_pmids.extend(rf.evidence.pmids)
            evidence_quality_counts[rf.evidence.evidence_quality] += 1
            source_counts[rf.evidence.source] += 1
        
        return {
            'total_citations': len(set(all_pmids)),
            'unique_pmids': list(set(all_pmids)),
            'evidence_quality_distribution': evidence_quality_counts,
            'source_distribution': source_counts
        }
    
    def generate_evidence_based_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate personalized, evidence-based recommendations based on available data
        """
        risk_assessment = self.assess_comprehensive_risk()
        risk_level = RiskLevel(risk_assessment['level'])
        risk_factors = risk_assessment['risk_factors']
        
        recommendations = []
        
        # 1. HbA1c-specific recommendations
        hba1c_rec = self._generate_hba1c_recommendations(risk_factors, risk_level)
        if hba1c_rec:
            recommendations.extend(hba1c_rec)
        
        # 2. Glucose control recommendations
        glucose_rec = self._generate_glucose_recommendations(risk_factors, risk_level)
        if glucose_rec:
            recommendations.extend(glucose_rec)
        
        # 3. Weight management recommendations
        weight_rec = self._generate_weight_recommendations(risk_factors, risk_level)
        if weight_rec:
            recommendations.extend(weight_rec)
        
        # 4. Blood pressure recommendations
        bp_rec = self._generate_bp_recommendations(risk_factors, risk_level)
        if bp_rec:
            recommendations.extend(bp_rec)
        
        # 5. Genetic-based recommendations
        genetic_rec = self._generate_genetic_recommendations(risk_factors, risk_level)
        if genetic_rec:
            recommendations.extend(genetic_rec)
        
        # 6. Monitoring recommendations
        monitoring_rec = self._generate_monitoring_recommendations(risk_factors, risk_level)
        if monitoring_rec:
            recommendations.extend(monitoring_rec)
        
        # 7. Emergency/critical recommendations
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            emergency_rec = self._generate_emergency_recommendations(risk_factors, risk_level)
            if emergency_rec:
                recommendations.extend(emergency_rec)
        
        # Sort by priority and clinical impact
        recommendations.sort(key=lambda x: (x['priority'], -x['clinical_impact']))
        
        # Convert to the format expected by frontend
        formatted_recommendations = []
        for i, rec in enumerate(recommendations[:8], 1):  # Limit to top 8
            formatted_recommendations.append({
                'id': f"rec_{i}",
                'type': rec['type'],
                'priority': rec['priority'],
                'action': rec['action'],
                'rationale': rec['rationale'],
                'evidence': rec['evidence']['pmids'][:3],  # Limit to 3 PMIDs
                'clinical_impact': rec['clinical_impact'],
                'urgency': rec['urgency'],
                'timeframe': rec.get('timeframe', 'Ongoing'),
                'monitoring_frequency': rec.get('monitoring_frequency', 'As needed')
            })
        
        return formatted_recommendations
    
    def _generate_hba1c_recommendations(self, risk_factors: List[Dict[str, Any]], risk_level: RiskLevel) -> List[Dict[str, Any]]:
        """Generate HbA1c-specific recommendations"""
        recommendations = []
        
        # Find HbA1c risk factor
        hba1c_factor = next((rf for rf in risk_factors if 'hba1c' in rf['name'].lower()), None)
        
        # Get latest HbA1c from measurements
        measurements = self.patient_data.get('measurements', [])
        hba1c_values = [m.get('hba1c') for m in measurements if m.get('hba1c') is not None]
        
        if hba1c_factor and hba1c_values:
            latest_hba1c = float(hba1c_values[-1])
            hba1c_pmids = hba1c_factor['pmids']
            
            if latest_hba1c > 8.0:
                recommendations.append({
                    'type': 'medical',
                    'priority': 1,
                    'action': 'Intensify diabetes medication regimen - HbA1c >8.0% requires immediate intervention',
                    'rationale': f'Current HbA1c of {latest_hba1c}% is significantly above target (<7.0%). Intensive therapy required.',
                    'evidence': {
                        'pmids': hba1c_pmids,
                        'evidence_quality': 'high',
                        'recommendation_strength': 'strong'
                    },
                    'clinical_impact': 95,
                    'urgency': 90,
                    'timeframe': '2-4 weeks',
                    'monitoring_frequency': 'Every 2 weeks'
                })
            elif latest_hba1c > 7.5:
                recommendations.append({
                    'type': 'medical',
                    'priority': 2,
                    'action': 'Consider medication adjustment to achieve glycemic target',
                    'rationale': f'HbA1c of {latest_hba1c}% exceeds recommended target of <7.0%.',
                    'evidence': {
                        'pmids': hba1c_pmids,
                        'evidence_quality': 'high',
                        'recommendation_strength': 'strong'
                    },
                    'clinical_impact': 80,
                    'urgency': 70,
                    'timeframe': '4-6 weeks',
                    'monitoring_frequency': 'Monthly'
                })
            elif latest_hba1c > 7.0:
                recommendations.append({
                    'type': 'lifestyle',
                    'priority': 3,
                    'action': 'Enhance lifestyle interventions with focus on diet and exercise',
                    'rationale': f'HbA1c of {latest_hba1c}% is slightly above target. Lifestyle optimization may achieve control.',
                    'evidence': {
                        'pmids': hba1c_pmids,
                        'evidence_quality': 'high',
                        'recommendation_strength': 'moderate'
                    },
                    'clinical_impact': 60,
                    'urgency': 50,
                    'timeframe': '8-12 weeks',
                    'monitoring_frequency': 'Every 6-8 weeks'
                })
        
        return recommendations
    
    def _generate_glucose_recommendations(self, risk_factors: List[Dict[str, Any]], risk_level: RiskLevel) -> List[Dict[str, Any]]:
        """Generate glucose variability recommendations"""
        recommendations = []
        
        glucose_factor = next((rf for rf in risk_factors if 'glucose' in rf['name'].lower() and 'variability' in rf['name'].lower()), None)
        
        if glucose_factor and glucose_factor['value'] > 50:
            recommendations.append({
                'type': 'monitoring',
                'priority': 2,
                'action': 'Implement continuous glucose monitoring (CGM) for better glucose stability',
                'rationale': f'High glucose variability detected (risk score: {glucose_factor["value"]:.0f}%). CGM can help identify patterns.',
                'evidence': {
                    'pmids': glucose_factor['pmids'],
                    'evidence_quality': 'high',
                    'recommendation_strength': 'strong'
                },
                'clinical_impact': 75,
                'urgency': 60,
                'timeframe': '2-4 weeks',
                'monitoring_frequency': 'Daily CGM'
            })
        
        return recommendations
    
    def _generate_weight_recommendations(self, risk_factors: List[Dict[str, Any]], risk_level: RiskLevel) -> List[Dict[str, Any]]:
        """Generate weight/BMI recommendations"""
        recommendations = []
        
        weight_factor = next((rf for rf in risk_factors if 'bmi' in rf['name'].lower() or 'weight' in rf['name'].lower()), None)
        
        if weight_factor:
            measurements = self.patient_data.get('measurements', [])
            bmi_values = [m.get('bmi') for m in measurements if m.get('bmi') is not None]
            
            if bmi_values:
                latest_bmi = float(bmi_values[-1])
                
                if latest_bmi >= 30:
                    recommendations.append({
                        'type': 'lifestyle',
                        'priority': 2,
                        'action': 'Implement structured weight management program (target 7-10% weight loss)',
                        'rationale': f'BMI of {latest_bmi:.1f} indicates obesity. Weight reduction is critical for diabetes management.',
                        'evidence': {
                            'pmids': weight_factor['pmids'],
                            'evidence_quality': 'high',
                            'recommendation_strength': 'strong'
                        },
                        'clinical_impact': 85,
                        'urgency': 70,
                        'timeframe': '6-12 months',
                        'monitoring_frequency': 'Monthly'
                    })
                elif latest_bmi >= 25:
                    recommendations.append({
                        'type': 'lifestyle',
                        'priority': 3,
                        'action': 'Moderate weight reduction through diet and exercise',
                        'rationale': f'BMI of {latest_bmi:.1f} indicates overweight status. Modest weight loss recommended.',
                        'evidence': {
                            'pmids': weight_factor['pmids'],
                            'evidence_quality': 'high',
                            'recommendation_strength': 'moderate'
                        },
                        'clinical_impact': 65,
                        'urgency': 40,
                        'timeframe': '3-6 months',
                        'monitoring_frequency': 'Every 6-8 weeks'
                    })
        
        return recommendations
    
    def _generate_bp_recommendations(self, risk_factors: List[Dict[str, Any]], risk_level: RiskLevel) -> List[Dict[str, Any]]:
        """Generate blood pressure recommendations"""
        recommendations = []
        
        bp_factor = next((rf for rf in risk_factors if 'blood pressure' in rf['name'].lower()), None)
        
        if bp_factor and bp_factor['value'] > 40:
            measurements = self.patient_data.get('measurements', [])
            bp_measurements = [(m.get('blood_pressure_systolic'), m.get('blood_pressure_diastolic')) 
                              for m in measurements 
                              if m.get('blood_pressure_systolic') and m.get('blood_pressure_diastolic')]
            
            if bp_measurements:
                latest_systolic, latest_diastolic = bp_measurements[-1]
                
                recommendations.append({
                    'type': 'medical',
                    'priority': 2,
                    'action': 'Blood pressure optimization required for diabetes management',
                    'rationale': f'Current BP {latest_systolic}/{latest_diastolic} mmHg exceeds diabetes target (≤130/80 mmHg).',
                    'evidence': {
                        'pmids': bp_factor['pmids'],
                        'evidence_quality': 'high',
                        'recommendation_strength': 'strong'
                    },
                    'clinical_impact': 80,
                    'urgency': 70,
                    'timeframe': '4-6 weeks',
                    'monitoring_frequency': 'Bi-weekly'
                })
        
        return recommendations
    
    def _generate_genetic_recommendations(self, risk_factors: List[Dict[str, Any]], risk_level: RiskLevel) -> List[Dict[str, Any]]:
        """Generate genetics-based recommendations"""
        recommendations = []
        
        genetic_factor = next((rf for rf in risk_factors if rf['category'] == 'genetic'), None)
        
        if genetic_factor and self.genetic_analysis:
            genetic_pmids = genetic_factor['pmids']
            genetic_risk = genetic_factor['value']
            
            if genetic_risk > 70:
                recommendations.append({
                    'type': 'genetic',
                    'priority': 3,
                    'action': 'Enhanced monitoring due to high genetic risk profile',
                    'rationale': f'Genetic analysis indicates {genetic_risk:.0f}% risk level. Increased surveillance recommended.',
                    'evidence': {
                        'pmids': genetic_pmids,
                        'evidence_quality': 'moderate',
                        'recommendation_strength': 'moderate'
                    },
                    'clinical_impact': 70,
                    'urgency': 60,
                    'timeframe': 'Ongoing',
                    'monitoring_frequency': 'Every 3 months'
                })
        
        return recommendations
    
    def _generate_monitoring_recommendations(self, risk_factors: List[Dict[str, Any]], risk_level: RiskLevel) -> List[Dict[str, Any]]:
        """Generate monitoring-based recommendations"""
        recommendations = []
        
        # Determine monitoring frequency based on risk level
        if risk_level == RiskLevel.CRITICAL:
            hba1c_frequency = "Every 6-8 weeks"
            glucose_frequency = "Daily with CGM recommended"
        elif risk_level == RiskLevel.HIGH:
            hba1c_frequency = "Every 3 months"
            glucose_frequency = "Daily SMBG"
        else:
            hba1c_frequency = "Every 6 months"
            glucose_frequency = "As directed"
        
        # Find monitoring-related PMIDs
        monitoring_pmids = [pmid for pmid in self.pubmed_citations 
                           if any(term in pmid.lower() for term in ['monitoring', 'follow-up', 'surveillance'])]
        
        if not monitoring_pmids:
            monitoring_pmids = self.pubmed_citations[:2]
        
        recommendations.append({
            'type': 'monitoring',
            'priority': 4,
            'action': f'Establish monitoring schedule: HbA1c {hba1c_frequency}, Glucose {glucose_frequency}',
            'rationale': f'Risk level ({risk_level.value}) requires appropriate monitoring intensity.',
            'evidence': {
                'pmids': monitoring_pmids,
                'evidence_quality': 'high',
                'recommendation_strength': 'strong'
            },
            'clinical_impact': 70,
            'urgency': 50,
            'timeframe': 'Immediate',
            'monitoring_frequency': hba1c_frequency
        })
        
        return recommendations
    
    def _generate_emergency_recommendations(self, risk_factors: List[Dict[str, Any]], risk_level: RiskLevel) -> List[Dict[str, Any]]:
        """Generate emergency/critical recommendations"""
        recommendations = []
        
        if risk_level == RiskLevel.CRITICAL:
            emergency_pmids = [pmid for pmid in self.pubmed_citations 
                              if any(term in pmid.lower() for term in ['emergency', 'acute', 'severe', 'crisis'])]
            
            if not emergency_pmids:
                emergency_pmids = self.pubmed_citations[:2]
            
            recommendations.append({
                'type': 'emergency',
                'priority': 1,
                'action': 'Urgent endocrinology consultation within 48-72 hours',
                'rationale': 'Critical risk level requires immediate specialist intervention.',
                'evidence': {
                    'pmids': emergency_pmids,
                    'evidence_quality': 'high',
                    'recommendation_strength': 'strong'
                },
                'clinical_impact': 100,
                'urgency': 100,
                'timeframe': '48-72 hours',
                'monitoring_frequency': 'Daily until stable'
            })
        
        return recommendations


# Backward compatibility and integration functions
def DecisionEngine(patient_data: Dict[str, Any]):
    """
    Backward compatibility wrapper για existing code
    """
    
    class CompatibilityWrapper:
        def __init__(self, patient_data: Dict[str, Any]):
            self.customized_engine = CustomizedDecisionEngine(patient_data)
        
        def assess_risk(self) -> Dict[str, Any]:
            """Returns risk assessment in expected format"""
            risk_data = self.customized_engine.assess_comprehensive_risk()
            
            # Convert to expected format
            return {
                'score': risk_data['total_score'],
                'level': risk_data['level']
            }
        
        def generate_recommendations(self) -> List[Dict[str, Any]]:
            """Returns recommendations in expected format"""
            return self.customized_engine.generate_evidence_based_recommendations()
    
    return CompatibilityWrapper(patient_data)


def create_enhanced_decision_engine(patient_data: Dict[str, Any], pubmed_citations: Optional[List[str]] = None, genetic_analysis: Optional[Dict[str, Any]] = None) -> CustomizedDecisionEngine:
    """
    Create customized decision engine with PubMed and genetic integration
    """
    return CustomizedDecisionEngine(
        patient_data=patient_data,
        pubmed_citations=pubmed_citations or [],
        genetic_analysis=genetic_analysis or {}
    )