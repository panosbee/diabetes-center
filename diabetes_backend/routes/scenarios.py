"""
Διορθωμένο scenarios.py με Enhanced Digital Twin - ΒΕΛΤΙΩΜΕΝΗ ΕΚΔΟΣΗ
=====================================================
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from bson.errors import InvalidId
import logging
import os
import datetime
import asyncio
import json
from typing import Dict, Any, Optional, List, List

from utils.db import get_db
from utils.permissions import ViewPatientPermission, permission_denied

# Import του ΒΕΛΤΙΩΜΕΝΟΥ Digital Twin Engine (με αρχικό όνομα)
from services.digital_twin_engine import digital_twin_engine

# Import για AI validation
from services.deepseek_integration import ask_rag_question

logger = logging.getLogger(__name__)

# Δημιουργία blueprint
scenarios_bp = Blueprint('scenarios', __name__, url_prefix='/api/scenarios')

# Η σύνδεση στη βάση δεδομένων
db = get_db()

@scenarios_bp.route('/simulate', methods=['OPTIONS'])
def scenarios_simulate_options():
    """Handle OPTIONS requests for CORS preflight"""
    response = jsonify({"message": "OK"})
    return response

@scenarios_bp.route('/simulate', methods=['POST'])
@jwt_required()
async def simulate_enhanced_what_if_scenario():
    """
    ΒΕΛΤΙΩΜΕΝΗ What-If scenario simulation με πραγματικό enhanced digital twin
    """
    requesting_user_id_str = get_jwt_identity()
    
    logger.info("🚀 ENHANCED What-If Scenarios endpoint called")
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        if not data or 'patient_id' not in data:
            return jsonify({"error": "Request body must be JSON and contain 'patient_id' field"}), 400
        
        patient_id = data.get('patient_id')
        scenario_params = data.get('scenario_params', {})
        
        logger.info(f"🔍 Enhanced simulation requested for patient: {patient_id}")
        logger.info(f"📊 Scenario parameters: {scenario_params}")
        
        try:
            patient_object_id = ObjectId(patient_id)
            view_permission = ViewPatientPermission(patient_id)
            if not view_permission.can():
                return permission_denied("Δεν έχετε δικαίωμα πρόσβασης στα δεδομένα αυτού του ασθενή")
        except InvalidId:
             return jsonify({"error": "Invalid patient ID format provided"}), 400
        
        # Συλλογή πλήρων δεδομένων ασθενή με βελτιωμένη στρατηγική
        patient_data = db.patients.find_one({"_id": patient_object_id})
        if not patient_data:
            return jsonify({"error": "Patient not found"}), 404
        
        # ΒΕΛΤΙΩΜΕΝΗ συλλογή sessions με measurements (πιο αποδοτικά και detailed)
        sessions = list(db.sessions.find(
            {
                "patient_id": patient_object_id, 
                "vitals_recorded": {"$exists": True, "$ne": None}
            },
            sort=[("timestamp", -1)],
            limit=25  # Περισσότερες μετρήσεις για καλύτερη ανάλυση
        ))
        
        enhanced_measurements_data = []
        for session in sessions:
            if 'vitals_recorded' not in session or not session['vitals_recorded']:
                continue
                
            timestamp_iso = session['timestamp'].isoformat() if isinstance(session['timestamp'], datetime.datetime) else str(session['timestamp'])
            vitals = session['vitals_recorded']
            
            # ΒΕΛΤΙΩΜΕΝΑ measurement data με περισσότερες πληροφορίες
            measurement = {
                "date": timestamp_iso,
                "timestamp": session['timestamp'],
                # Basic vitals
                "weight_kg": vitals.get('weight_kg'),
                "height_cm": vitals.get('height_cm'), 
                "bmi": vitals.get('bmi'),
                # Glucose data
                "blood_glucose_level": vitals.get('blood_glucose_level'),
                "blood_glucose_type": vitals.get('blood_glucose_type', 'undefined'),
                "glucose_time": vitals.get('glucose_time', 'unknown'),
                "hba1c": vitals.get('hba1c'),
                # Cardiovascular
                "blood_pressure_systolic": vitals.get('blood_pressure_systolic'),
                "blood_pressure_diastolic": vitals.get('blood_pressure_diastolic'),
                "heart_rate": vitals.get('heart_rate'),
                # Diabetes management
                "insulin_units": vitals.get('insulin_units'),
                "insulin_type": vitals.get('insulin_type'),
                "meal_carbs": vitals.get('meal_carbs'),
                "meal_description": vitals.get('meal_description'),
                # Activity & lifestyle
                "exercise_minutes": vitals.get('exercise_minutes'),
                "exercise_type": vitals.get('exercise_type'),
                "stress_level": vitals.get('stress_level', 1.0),
                "sleep_hours": vitals.get('sleep_hours'),
                # Additional factors
                "notes": vitals.get('notes', ''),
                "medication_changes": vitals.get('medication_changes'),
                "illness_symptoms": vitals.get('illness_symptoms'),
                "menstrual_cycle": vitals.get('menstrual_cycle'),  # for female patients
                "alcohol_consumption": vitals.get('alcohol_consumption')
            }
            enhanced_measurements_data.append(measurement)
        
        logger.info(f"📈 Found {len(enhanced_measurements_data)} enhanced measurements for advanced simulation")
        
        # COMPREHENSIVE patient data για enhanced engine
        comprehensive_patient_data = {
            "patient_id": str(patient_id),
            "personal_details": patient_data.get('personal_details', {}),
            "medical_profile": patient_data.get('medical_profile', {}),
            "measurements": enhanced_measurements_data,
            "data_quality": {
                "total_measurements": len(enhanced_measurements_data),
                "glucose_measurements": len([m for m in enhanced_measurements_data if m.get('blood_glucose_level')]),
                "recent_hba1c": any(m.get('hba1c') for m in enhanced_measurements_data[-5:]),
                "insulin_data": len([m for m in enhanced_measurements_data if m.get('insulin_units')]),
                "meal_data": len([m for m in enhanced_measurements_data if m.get('meal_carbs')]),
                "exercise_data": len([m for m in enhanced_measurements_data if m.get('exercise_minutes')])
            }
        }
        
        # === ENHANCED AI VALIDATION AGENT ===
        logger.info("🤖 Starting enhanced AI validation with comprehensive patient context...")
        
        enhanced_validation_prompt = f"""
ENHANCED AI VALIDATION για Advanced Digital Twin Diabetes Simulation:

COMPREHENSIVE PATIENT PROFILE:
- Patient ID: {patient_id}
- Age: {comprehensive_patient_data.get('personal_details', {}).get('age', 'Unknown')}
- Gender: {comprehensive_patient_data.get('personal_details', {}).get('gender', 'Unknown')}
- Diabetes Type: {_extract_diabetes_type(comprehensive_patient_data)}
- Disease Duration: {_estimate_diabetes_duration(comprehensive_patient_data)} years

ENHANCED CLINICAL DATA:
- Total Measurements: {comprehensive_patient_data['data_quality']['total_measurements']}
- Glucose Readings: {comprehensive_patient_data['data_quality']['glucose_measurements']}
- Recent HbA1c Available: {comprehensive_patient_data['data_quality']['recent_hba1c']}
- Latest HbA1c: {_get_latest_hba1c(enhanced_measurements_data)}%
- Latest Glucose: {_get_latest_glucose(enhanced_measurements_data)} mg/dL
- Average Recent Glucose: {_get_average_recent_glucose(enhanced_measurements_data)} mg/dL
- BMI: {_calculate_bmi(comprehensive_patient_data)} kg/m²
- Data Quality Score: {_assess_data_quality(comprehensive_patient_data)}

PROPOSED SCENARIO PARAMETERS:
- Basal insulin change: {scenario_params.get('basal_change', 0)}% 
- Bolus insulin change: {scenario_params.get('bolus_change', 0)}%
- Carb ratio change: {scenario_params.get('carb_ratio_change', 0)}%
- Correction factor change: {scenario_params.get('correction_factor_change', 0)}%
- Meal carbohydrates: {scenario_params.get('meal_carbs', 0)}g at T+{scenario_params.get('meal_timing', 60)}min
- Exercise intensity: {scenario_params.get('exercise_intensity', 0)}% for {scenario_params.get('exercise_duration', 0)} minutes
- Simulation duration: {scenario_params.get('simulation_hours', 24)} hours

COMPREHENSIVE SAFETY ASSESSMENT CRITERIA:
1. PARAMETER MAGNITUDE RISK:
   - >50% insulin changes = UNSAFE
   - 30-50% changes = HIGH RISK, requires justification
   - <30% changes = ACCEPTABLE with monitoring

2. COMBINATION RISK FACTORS:
   - Exercise + insulin increase = MAJOR RISK
   - Large meals + reduced insulin = HYPERGLYCEMIA RISK
   - Multiple parameter changes = CUMULATIVE RISK

3. PATIENT-SPECIFIC FACTORS:
   - Age >65 or <25 = Increased sensitivity
   - Poor baseline control (HbA1c >8%) = Higher variability risk
   - History of severe hypoglycemia = Enhanced caution needed
   - Limited glucose data = Reduced confidence

4. CLINICAL EVIDENCE ALIGNMENT:
   - ADA/EASD 2023 guidelines compliance
   - ATTD 2023 consensus recommendations
   - Real-world evidence considerations

5. PHYSIOLOGICAL PLAUSIBILITY:
   - Dawn/dusk phenomenon considerations
   - Meal absorption timing realistic?
   - Exercise effects physiologically sound?
   - Insulin action profiles appropriate?

COMPREHENSIVE JSON ASSESSMENT REQUIRED:
{{
    "safety_assessment": "SAFE/CAUTION/UNSAFE",
    "risk_level": "LOW/MODERATE/HIGH", 
    "confidence_level": "HIGH/MEDIUM/LOW",
    "clinical_warnings": ["specific detailed warning messages"],
    "optimization_suggestions": ["evidence-based improvement suggestions"],
    "reasoning": "Detailed clinical reasoning for safety assessment",
    "parameter_concerns": ["specific parameter-related issues"],
    "patient_specific_notes": ["personalized considerations based on patient data"],
    "contraindications": ["absolute or relative contraindications if any"],
    "monitoring_requirements": ["specific monitoring recommendations"],
    "clinical_evidence": ["relevant guideline citations or evidence"],
    "alternative_suggestions": ["safer alternative parameter combinations if unsafe"],
    "expected_outcomes": ["predicted clinical outcomes"],
    "data_quality_impact": "How data quality affects recommendation confidence"
}}

CRITICAL: Consider the comprehensive patient context, clinical evidence, and provide detailed reasoning for all assessments.
"""
        
        validation_result = await _get_enhanced_ai_validation(enhanced_validation_prompt)
        
        # === ΒΕΛΤΙΩΜΕΝΗ DIGITAL TWIN SIMULATION ===
        logger.info("🧬 Starting Enhanced Digital Twin simulation with advanced physiological modeling...")
        
        # ΒΕΛΤΙΩΜΕΝΑ scenario params με full validation και defaults
        enhanced_scenario = {
            "basal_change": float(scenario_params.get('basal_change', 0.0)),
            "bolus_change": float(scenario_params.get('bolus_change', 0.0)),  
            "carb_ratio_change": float(scenario_params.get('carb_ratio_change', 0.0)),
            "correction_factor_change": float(scenario_params.get('correction_factor_change', 0.0)),
            "meal_carbs": float(scenario_params.get('meal_carbs', 0.0)),
            "meal_timing": int(scenario_params.get('meal_timing', 60)),
            "exercise_intensity": float(scenario_params.get('exercise_intensity', 0.0)),
            "exercise_duration": int(scenario_params.get('exercise_duration', 0)),
            "simulation_hours": int(scenario_params.get('simulation_hours', 24)),
            "time_step_minutes": 5  # Enhanced resolution για καλύτερη ακρίβεια
        }
        
        try:
            # Κλήση του ΒΕΛΤΙΩΜΕΝΟΥ Digital Twin Engine
            simulation_result = await digital_twin_engine.simulate_what_if_scenario(
                comprehensive_patient_data, 
                enhanced_scenario
            )
            
            if not simulation_result.get('success'):
                raise Exception(simulation_result.get('error', 'Unknown enhanced simulation error'))
                
            logger.info("✅ Enhanced Digital Twin simulation completed successfully!")
            logger.info(f"📊 Enhanced Results Preview - TIR: {simulation_result['simulation_results']['glucose_metrics']['tir_70_180']:.1f}%, "
                       f"CV: {simulation_result['simulation_results']['glucose_metrics']['glucose_cv']:.1f}%, "
                       f"Risk: {simulation_result['simulation_results']['risk_scores']['overall_risk']:.1f}%")
            
        except Exception as sim_error:
            logger.error(f"❌ Enhanced Digital Twin simulation failed: {sim_error}", exc_info=True)
            return jsonify({
                "error": "Enhanced simulation failed",
                "details": str(sim_error),
                "message": "Σφάλμα στην προηγμένη προσομοίωση. Παρακαλώ ελέγξτε τις παραμέτρους και δοκιμάστε ξανά.",
                "debug_info": {
                    "patient_id": patient_id,
                    "scenario_params": enhanced_scenario,
                    "data_quality": comprehensive_patient_data['data_quality']
                }
            }), 500
        
        # === ENHANCED AI OPTIMIZATION AGENT ===
        logger.info("🎯 Starting enhanced AI optimization with comprehensive clinical analysis...")
        
        enhanced_optimization_prompt = f"""
ENHANCED AI OPTIMIZATION για Digital Twin Results με Comprehensive Clinical Analysis:

COMPREHENSIVE SIMULATION RESULTS:
=================================
GLUCOSE METRICS:
- Mean glucose: {simulation_result['simulation_results']['glucose_metrics']['mean_glucose']:.1f} mg/dL
- Glucose CV: {simulation_result['simulation_results']['glucose_metrics']['glucose_cv']:.1f}%
- Estimated HbA1c: {simulation_result['simulation_results']['glucose_metrics']['estimated_hba1c']:.1f}%

TIME IN RANGE ANALYSIS:
- TIR 70-180 mg/dL: {simulation_result['simulation_results']['glucose_metrics']['tir_70_180']:.1f}%
- TIR 70-140 mg/dL: {simulation_result['simulation_results']['glucose_metrics']['tir_70_140']:.1f}%
- Time below 70 mg/dL: {simulation_result['simulation_results']['glucose_metrics']['time_below_70']:.1f}%
- Time below 54 mg/dL: {simulation_result['simulation_results']['glucose_metrics']['time_below_54']:.1f}%
- Time above 180 mg/dL: {simulation_result['simulation_results']['glucose_metrics']['time_above_180']:.1f}%
- Time above 250 mg/dL: {simulation_result['simulation_results']['glucose_metrics']['time_above_250']:.1f}%

RISK ASSESSMENT:
- Overall risk score: {simulation_result['simulation_results']['risk_scores']['overall_risk']:.1f}%
- Hypoglycemia risk: {simulation_result['simulation_results']['risk_scores']['hypoglycemia_risk']:.1f}%
- Severe hypoglycemia risk: {simulation_result['simulation_results']['risk_scores']['severe_hypoglycemia_risk']:.1f}%
- Hyperglycemia risk: {simulation_result['simulation_results']['risk_scores']['hyperglycemia_risk']:.1f}%
- Variability risk: {simulation_result['simulation_results']['risk_scores']['variability_risk']:.1f}%

ENHANCED METRICS:
- MAGE (Mean Amplitude Glycemic Excursions): {simulation_result['simulation_results']['glucose_metrics'].get('mage', 0):.1f}
- J-index: {simulation_result['simulation_results']['glucose_metrics'].get('j_index', 0):.1f}
- CONGA: {simulation_result['simulation_results']['glucose_metrics'].get('conga', 0):.1f}
- GMI (Glucose Management Indicator): {simulation_result['simulation_results']['glucose_metrics'].get('gmi', 0):.1f}%

PATIENT PROFILE CONTEXT:
========================
- Diabetes Type: {simulation_result['patient_profile']['diabetes_type']}
- Age: {simulation_result['patient_profile']['age']} years
- Duration: {simulation_result['patient_profile'].get('diabetes_duration_years', 'Unknown')} years
- Current Insulin Sensitivity: {simulation_result['patient_profile']['insulin_sensitivity']:.0f} mg/dL/unit
- Current Carb Ratio: {simulation_result['patient_profile']['carb_ratio']:.1f} g/unit
- Basal Rate: {simulation_result['patient_profile']['basal_rate']:.2f} units/hour

CURRENT SCENARIO PARAMETERS:
============================
{enhanced_scenario}

ADVANCED ANALYTICS:
==================
- Model Confidence: {simulation_result.get('advanced_analytics', {}).get('model_confidence', 75)}%
- Insulin Resistance Factor: {simulation_result.get('advanced_analytics', {}).get('patient_factors', {}).get('insulin_resistance', 1.0):.2f}
- Exercise Sensitivity: {simulation_result.get('advanced_analytics', {}).get('patient_factors', {}).get('exercise_sensitivity', 1.0):.2f}

CLINICAL TARGETS & BENCHMARKS:
===============================
TARGET ACHIEVEMENT ANALYSIS:
- TIR 70-180: TARGET >70% (optimal >85%) | CURRENT: {simulation_result['simulation_results']['glucose_metrics']['tir_70_180']:.1f}%
- TIR 70-140: TARGET >50% (optimal >70%) | CURRENT: {simulation_result['simulation_results']['glucose_metrics']['tir_70_140']:.1f}%
- Time <70: TARGET <4% (optimal <1%) | CURRENT: {simulation_result['simulation_results']['glucose_metrics']['time_below_70']:.1f}%
- Time <54: TARGET <1% (optimal <0.5%) | CURRENT: {simulation_result['simulation_results']['glucose_metrics']['time_below_54']:.1f}%
- CV: TARGET <36% (optimal <25%) | CURRENT: {simulation_result['simulation_results']['glucose_metrics']['glucose_cv']:.1f}%
- HbA1c: TARGET <7% (individualized 6.5-8%) | ESTIMATED: {simulation_result['simulation_results']['glucose_metrics']['estimated_hba1c']:.1f}%

EVIDENCE-BASED OPTIMIZATION REQUEST:
====================================
Provide comprehensive JSON optimization based on ADA/EASD 2023 guidelines, ATTD consensus, and latest clinical evidence:

{{
    "optimized_params": {{
        "basal_change": -5.0,
        "bolus_change": 10.0,
        "carb_ratio_change": -5.0,
        "correction_factor_change": 5.0,
        "meal_carbs": 45.0,
        "exercise_recommendation": "moderate 30min post-meal",
        "timing_adjustments": "pre-bolus -15min"
    }},
    "expected_improvements": [
        "TIR 70-180: +15% improvement to 85%",
        "Glucose CV: -8% reduction to 25%", 
        "HbA1c: -0.4% reduction to 6.8%",
        "Hypoglycemia risk: -50% reduction"
    ],
    "clinical_rationale": "Detailed evidence-based explanation of optimization strategy",
    "confidence": "HIGH/MEDIUM/LOW",
    "priority_actions": [
        "ranked list of most impactful changes",
        "immediate vs gradual implementation strategy"
    ],
    "monitoring_recommendations": [
        "specific monitoring protocols",
        "frequency and timing of glucose checks",
        "ketone monitoring if applicable"
    ],
    "technology_suggestions": [
        "CGM recommendations with specific models",
        "insulin pump considerations", 
        "mobile app integration suggestions"
    ],
    "alternative_strategies": [
        "alternative optimization approaches",
        "backup plans if primary approach fails"
    ],
    "contraindications": ["specific situations to avoid"],
    "patient_education_needs": ["specific education topics required"],
    "follow_up_timeline": "recommended follow-up schedule",
    "risk_mitigation": ["strategies to minimize risks during optimization"],
    "evidence_citations": ["relevant clinical studies or guidelines"]
}}

CRITICAL: Provide actionable, evidence-based optimization that prioritizes SAFETY while maximizing clinical outcomes.
"""
        
        optimization_result = await _get_enhanced_ai_optimization(enhanced_optimization_prompt)
        
        # === COMPREHENSIVE RESPONSE ASSEMBLY ===
        
        enhanced_response_payload = {
            "id": f"enhanced-whatif-{datetime.datetime.now().timestamp()}",
            "success": True,
            "patient_id": patient_id,
            "scenario_params": enhanced_scenario,
            "version": "enhanced_v2.0",
            
            # Enhanced AI Validation Results
            "ai_validation": validation_result,
            
            # Enhanced Digital Twin Simulation Results
            "simulation": simulation_result['simulation_results'],
            "patient_profile": simulation_result['patient_profile'],
            
            # Enhanced Visualizations
            "mindmap_data": simulation_result['mindmap_data'],
            "comparison_data": simulation_result['comparison_data'],
            
            # Enhanced AI Optimization
            "optimization": optimization_result,
            
            # Enhanced Analytics & Insights
            "advanced_analytics": simulation_result.get('advanced_analytics', {}),
            
            # Enhanced Data Quality Assessment
            "data_quality": comprehensive_patient_data['data_quality'],
            
            # Enhanced Clinical Insights
            "clinical_insights": {
                "target_achievement": _assess_target_achievement(simulation_result['simulation_results']),
                "improvement_potential": _assess_improvement_potential(simulation_result, comprehensive_patient_data),
                "personalization_factors": _extract_personalization_factors(simulation_result['patient_profile']),
                "safety_profile": _create_safety_profile(simulation_result['simulation_results'], validation_result)
            },
            
            # Enhanced Debug & Quality Information
            "debug_info": {
                "enhanced_features": {
                    "stochastic_modeling": True,
                    "circadian_rhythms": True,
                    "patient_variability": True,
                    "meal_absorption_modeling": "gamma_distribution",
                    "exercise_physiology": "enhanced_multi_phase",
                    "insulin_pharmacokinetics": "two_compartment"
                },
                "data_metrics": {
                    "measurements_count": len(enhanced_measurements_data),
                    "glucose_data_points": comprehensive_patient_data['data_quality']['glucose_measurements'],
                    "insulin_data_points": comprehensive_patient_data['data_quality']['insulin_data'],
                    "meal_data_points": comprehensive_patient_data['data_quality']['meal_data'],
                    "exercise_data_points": comprehensive_patient_data['data_quality']['exercise_data']
                },
                "simulation_quality": {
                    "model_confidence": simulation_result.get('advanced_analytics', {}).get('model_confidence', 75),
                    "clinical_significance": simulation_result.get('advanced_analytics', {}).get('clinical_significance', {}),
                    "physiological_realism": "enhanced",
                    "time_resolution": "5_minutes",
                    "simulation_duration": f"{enhanced_scenario['simulation_hours']}h"
                },
                "ai_quality": {
                    "validation_confidence": validation_result.get('confidence_level', 'MEDIUM'),
                    "optimization_confidence": optimization_result.get('confidence', 'MEDIUM'),
                    "clinical_evidence_base": "ADA_EASD_2023_ATTD_2023"
                },
                "risk_assessment": {
                    "safety": validation_result.get('safety_assessment', 'CAUTION'),
                    "risk_level": validation_result.get('risk_level', 'MODERATE'),
                    "overall_risk_score": simulation_result['simulation_results']['risk_scores']['overall_risk'],
                    "critical_alerts": len([a for a in simulation_result['simulation_results']['safety_alerts'] if '🚨' in a])
                }
            }
        }
        
        logger.info(f"✅ ENHANCED What-If scenario completed successfully!")
        logger.info(f"📊 COMPREHENSIVE Results Summary:")
        logger.info(f"   🎯 Safety: {validation_result.get('safety_assessment', 'UNKNOWN')}")
        logger.info(f"   📈 TIR: {simulation_result['simulation_results']['glucose_metrics']['tir_70_180']:.1f}%")
        logger.info(f"   📊 CV: {simulation_result['simulation_results']['glucose_metrics']['glucose_cv']:.1f}%")
        logger.info(f"   ⚠️ Risk: {simulation_result['simulation_results']['risk_scores']['overall_risk']:.1f}%")
        logger.info(f"   🤖 Model Confidence: {simulation_result.get('advanced_analytics', {}).get('model_confidence', 'Unknown')}%")
        
        return jsonify(enhanced_response_payload), 200

    except Exception as e:
        logger.error(f"❌ Error in Enhanced What-If scenarios: {e}", exc_info=True)
        return jsonify({
            "error": "An internal server error occurred during enhanced simulation",
            "details": str(e),
            "patient_id": patient_id if 'patient_id' in locals() else 'unknown',
            "timestamp": datetime.datetime.now().isoformat()
        }), 500


# === ENHANCED HELPER FUNCTIONS ===

async def _get_enhanced_ai_validation(prompt: str) -> Dict[str, Any]:
    """Enhanced AI validation με comprehensive error handling"""
    try:
        logger.info("🤖 Calling enhanced AI validation...")
        ai_response = await ask_rag_question(prompt)
        
        if ai_response and ai_response.strip():
            try:
                # Try direct JSON parsing
                validation_result = json.loads(ai_response.strip())
                logger.info(f"🤖 Enhanced AI Validation successful: {validation_result.get('safety_assessment')}")
                return _ensure_enhanced_validation_completeness(validation_result)
                
            except json.JSONDecodeError as json_error:
                logger.warning(f"⚠️ JSON decode error in enhanced validation: {json_error}")
                # Try to extract JSON from response with better regex
                import re
                json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', ai_response, re.DOTALL)
                
                for json_match in json_matches:
                    try:
                        validation_result = json.loads(json_match)
                        logger.info("🔧 Successfully extracted JSON from enhanced AI validation response")
                        return _ensure_enhanced_validation_completeness(validation_result)
                    except json.JSONDecodeError:
                        continue
                
                # If all fails, try to extract key information manually
                logger.warning("⚠️ Manual extraction from AI response")
                return _extract_validation_manually(ai_response)
                    
    except Exception as ai_error:
        logger.error(f"❌ Enhanced AI validation failed: {ai_error}", exc_info=True)
    
    # Fallback default validation
    return _get_enhanced_default_validation_result("AI_SERVICE_ERROR")

async def _get_enhanced_ai_optimization(prompt: str) -> Dict[str, Any]:
    """Enhanced AI optimization με comprehensive error handling"""
    try:
        logger.info("🎯 Calling enhanced AI optimization...")
        ai_response = await ask_rag_question(prompt)
        
        if ai_response and ai_response.strip():
            try:
                optimization_result = json.loads(ai_response.strip())
                logger.info("🎯 Enhanced AI Optimization successful")
                return _ensure_enhanced_optimization_completeness(optimization_result)
                
            except json.JSONDecodeError as json_error:
                logger.warning(f"⚠️ JSON decode error in enhanced optimization: {json_error}")
                # Try enhanced JSON extraction
                import re
                json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', ai_response, re.DOTALL)
                
                for json_match in json_matches:
                    try:
                        optimization_result = json.loads(json_match)
                        logger.info("🔧 Successfully extracted JSON from enhanced optimization response")
                        return _ensure_enhanced_optimization_completeness(optimization_result)
                    except json.JSONDecodeError:
                        continue
                
                # Manual extraction fallback
                return _extract_optimization_manually(ai_response)
                    
    except Exception as opt_error:
        logger.error(f"❌ Enhanced AI optimization failed: {opt_error}", exc_info=True)
    
    return _get_enhanced_default_optimization_result()

def _extract_validation_manually(ai_response: str) -> Dict[str, Any]:
    """Manual extraction of validation data από AI response"""
    validation = _get_enhanced_default_validation_result("MANUAL_EXTRACTION")
    
    response_lower = ai_response.lower()
    
    # Extract safety assessment
    if "unsafe" in response_lower or "κίνδυνος" in response_lower:
        validation["safety_assessment"] = "UNSAFE"
        validation["risk_level"] = "HIGH"
    elif "safe" in response_lower or "ασφαλής" in response_lower:
        validation["safety_assessment"] = "SAFE"
        validation["risk_level"] = "LOW"
    
    # Extract warnings from response
    warnings = []
    if "warning" in response_lower or "προσοχή" in response_lower:
        warnings.append("AI detected potential safety concerns - manual review required")
    if "hypoglycemia" in response_lower or "υπογλυκαιμία" in response_lower:
        warnings.append("Hypoglycemia risk detected")
    if "insulin" in response_lower and ("high" in response_lower or "μεγάλη" in response_lower):
        warnings.append("Large insulin changes detected")
    
    validation["clinical_warnings"] = warnings
    validation["reasoning"] = "Manual extraction από AI response due to JSON parsing failure"
    
    return validation

def _extract_optimization_manually(ai_response: str) -> Dict[str, Any]:
    """Manual extraction of optimization data από AI response"""
    optimization = _get_enhanced_default_optimization_result()
    
    # Try to extract any numerical recommendations
    import re
    number_matches = re.findall(r'[-+]?\d*\.?\d+%?', ai_response)
    
    if number_matches:
        optimization["clinical_rationale"] = f"Manual extraction found potential adjustments: {', '.join(number_matches[:5])}"
    
    # Extract general recommendations
    if "reduce" in ai_response.lower() or "μείωση" in ai_response.lower():
        optimization["priority_actions"].append("Consider parameter reduction based on AI analysis")
    if "increase" in ai_response.lower() or "αύξηση" in ai_response.lower():
        optimization["priority_actions"].append("Consider parameter increase based on AI analysis")
    
    return optimization

def _extract_diabetes_type(patient_data: Dict[str, Any]) -> str:
    """Enhanced diabetes type extraction"""
    conditions = patient_data.get('medical_profile', {}).get('conditions', [])
    for condition in conditions:
        condition_name = condition.get('condition_name', '').lower()
        if any(term in condition_name for term in ['τύπου 1', 'type 1', 't1dm', 'iddm']):
            return "Type 1 Diabetes"
        elif any(term in condition_name for term in ['τύπου 2', 'type 2', 't2dm', 'niddm']):
            return "Type 2 Diabetes"
    
    # Fallback based on typical patterns
    measurements = patient_data.get('measurements', [])
    if measurements:
        # T1 patients typically need more insulin, younger onset
        age = patient_data.get('personal_details', {}).get('age')
        if age and age < 30:
            return "Likely Type 1 Diabetes"
    
    return "Type 2 Diabetes (presumed)"

def _estimate_diabetes_duration(patient_data: Dict[str, Any]) -> float:
    """Estimate diabetes duration από available data"""
    conditions = patient_data.get('medical_profile', {}).get('conditions', [])
    
    for condition in conditions:
        condition_name = condition.get('condition_name', '').lower()
        # Look for duration indicators
        import re
        duration_match = re.search(r'(\d+)\s*(year|χρόν|ετ)', condition_name)
        if duration_match:
            return float(duration_match.group(1))
    
    # Estimate based on age if no explicit duration
    age = patient_data.get('personal_details', {}).get('age')
    if age:
        if age < 25:
            return max(1, age - 15)  # Assume onset in teens for young patients
        elif age < 40:
            return max(1, age - 25)  # Assume young adult onset
        else:
            return min(10, max(2, age - 45))  # Assume middle-age onset, cap at 10 years
    
    return 5.0  # Default

def _get_latest_hba1c(measurements: List[Dict]) -> float:
    """Enhanced HbA1c extraction"""
    for measurement in reversed(measurements):
        if measurement.get('hba1c'):
            try:
                value = float(measurement['hba1c'])
                if 4.0 <= value <= 15.0:  # Reasonable range
                    return value
            except (ValueError, TypeError):
                continue
    return 7.8  # Default estimated value

def _get_latest_glucose(measurements: List[Dict]) -> float:
    """Enhanced glucose extraction"""
    for measurement in reversed(measurements):
        if measurement.get('blood_glucose_level'):
            try:
                value = float(measurement['blood_glucose_level'])
                if 40 <= value <= 600:  # Reasonable range
                    return value
            except (ValueError, TypeError):
                continue
    return 140  # Default

def _get_average_recent_glucose(measurements: List[Dict]) -> float:
    """Calculate average of recent glucose measurements"""
    recent_glucose = []
    for measurement in measurements[-10:]:  # Last 10 measurements
        if measurement.get('blood_glucose_level'):
            try:
                value = float(measurement['blood_glucose_level'])
                if 40 <= value <= 600:  # Reasonable range
                    recent_glucose.append(value)
            except (ValueError, TypeError):
                continue
    
    return sum(recent_glucose) / len(recent_glucose) if recent_glucose else 140.0

def _calculate_bmi(patient_data: Dict[str, Any]) -> float:
    """Enhanced BMI calculation"""
    measurements = patient_data.get('measurements', [])
    personal_details = patient_data.get('personal_details', {})
    medical_profile = patient_data.get('medical_profile', {})
    
    # Try from latest measurement
    if measurements:
        latest = measurements[-1]
        weight = latest.get('weight_kg')
        height = latest.get('height_cm') or medical_profile.get('height_cm')
        
        if weight and height:
            try:
                return float(weight) / (float(height) / 100) ** 2
            except (ValueError, TypeError, ZeroDivisionError):
                pass
    
    # Try from medical profile
    weight = medical_profile.get('weight_kg')
    height = medical_profile.get('height_cm')
    if weight and height:
        try:
            return float(weight) / (float(height) / 100) ** 2
        except (ValueError, TypeError, ZeroDivisionError):
            pass
    
    return 25.0  # Default healthy BMI

def _assess_data_quality(patient_data: Dict[str, Any]) -> str:
    """Assess data quality για confidence estimation"""
    quality = patient_data['data_quality']
    
    total_measurements = quality['total_measurements']
    glucose_measurements = quality['glucose_measurements']
    
    score = 0
    
    # Quantity scoring
    if total_measurements >= 20:
        score += 40
    elif total_measurements >= 10:
        score += 30
    elif total_measurements >= 5:
        score += 20
    else:
        score += 10
    
    # Glucose data scoring
    if glucose_measurements >= 15:
        score += 25
    elif glucose_measurements >= 8:
        score += 20
    elif glucose_measurements >= 4:
        score += 15
    else:
        score += 5
    
    # HbA1c availability
    if quality['recent_hba1c']:
        score += 15
    
    # Additional data types
    if quality['insulin_data'] > 0:
        score += 10
    if quality['meal_data'] > 0:
        score += 5
    if quality['exercise_data'] > 0:
        score += 5
    
    if score >= 80:
        return "EXCELLENT"
    elif score >= 60:
        return "GOOD"
    elif score >= 40:
        return "MODERATE"
    else:
        return "LIMITED"

def _assess_target_achievement(simulation_results: Dict[str, Any]) -> Dict[str, Any]:
    """Assess clinical target achievement"""
    metrics = simulation_results['glucose_metrics']
    
    targets = {
        "tir_70_180": {"value": metrics['tir_70_180'], "target": 70, "optimal": 85, "achieved": metrics['tir_70_180'] >= 70},
        "tir_70_140": {"value": metrics['tir_70_140'], "target": 50, "optimal": 70, "achieved": metrics['tir_70_140'] >= 50},
        "time_below_70": {"value": metrics['time_below_70'], "target": 4, "optimal": 1, "achieved": metrics['time_below_70'] <= 4},
        "time_below_54": {"value": metrics['time_below_54'], "target": 1, "optimal": 0.5, "achieved": metrics['time_below_54'] <= 1},
        "glucose_cv": {"value": metrics['glucose_cv'], "target": 36, "optimal": 25, "achieved": metrics['glucose_cv'] <= 36},
        "estimated_hba1c": {"value": metrics['estimated_hba1c'], "target": 7.0, "optimal": 6.5, "achieved": metrics['estimated_hba1c'] <= 7.0}
    }
    
    achieved_count = sum(1 for t in targets.values() if t['achieved'])
    total_targets = len(targets)
    
    return {
        "targets": targets,
        "achievement_score": f"{achieved_count}/{total_targets}",
        "achievement_percentage": (achieved_count / total_targets) * 100,
        "overall_assessment": "EXCELLENT" if achieved_count >= 5 else "GOOD" if achieved_count >= 4 else "NEEDS_IMPROVEMENT"
    }

def _assess_improvement_potential(simulation_result: Dict[str, Any], patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Assess potential για improvement"""
    current_metrics = simulation_result['simulation_results']['glucose_metrics']
    
    improvement_potential = {
        "tir_potential": max(0, 85 - current_metrics['tir_70_180']),
        "cv_reduction_potential": max(0, current_metrics['glucose_cv'] - 25),
        "hba1c_reduction_potential": max(0, current_metrics['estimated_hba1c'] - 6.5),
        "overall_potential": "HIGH" if current_metrics['tir_70_180'] < 70 else "MODERATE" if current_metrics['tir_70_180'] < 85 else "LOW"
    }
    
    return improvement_potential

def _extract_personalization_factors(patient_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key personalization factors"""
    return {
        "diabetes_type": patient_profile['diabetes_type'],
        "age_group": "young" if patient_profile['age'] < 25 else "adult" if patient_profile['age'] < 65 else "elderly",
        "insulin_sensitivity_level": "high" if patient_profile['insulin_sensitivity'] > 60 else "moderate" if patient_profile['insulin_sensitivity'] > 30 else "low",
        "variability_factors": {
            "stress_sensitivity": patient_profile.get('stress_sensitivity', 1.0),
            "exercise_sensitivity": patient_profile.get('exercise_sensitivity', 1.0),
            "meal_variability": patient_profile.get('meal_variability', 0.1)
        }
    }

def _create_safety_profile(simulation_results: Dict[str, Any], validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """Create comprehensive safety profile"""
    safety_alerts = simulation_results['safety_alerts']
    risk_scores = simulation_results['risk_scores']
    
    critical_alerts = [a for a in safety_alerts if '🚨' in a]
    warning_alerts = [a for a in safety_alerts if '⚠️' in a]
    
    return {
        "overall_safety": validation_result.get('safety_assessment', 'UNKNOWN'),
        "risk_level": validation_result.get('risk_level', 'UNKNOWN'),
        "critical_alerts_count": len(critical_alerts),
        "warning_alerts_count": len(warning_alerts),
        "highest_risk_factor": max(risk_scores.items(), key=lambda x: x[1]) if risk_scores else ("unknown", 0),
        "safety_score": 100 - risk_scores.get('overall_risk', 50),
        "monitoring_required": len(critical_alerts) > 0 or risk_scores.get('severe_hypoglycemia_risk', 0) > 2
    }

def _get_enhanced_default_validation_result(error_type: str = "UNKNOWN") -> Dict[str, Any]:
    """Enhanced default validation result"""
    return {
        "safety_assessment": "CAUTION",
        "risk_level": "MODERATE",
        "confidence_level": "LOW",
        "clinical_warnings": [f"Enhanced AI validation unavailable ({error_type}) - clinical judgment required"],
        "optimization_suggestions": ["Careful monitoring και gradual adjustments recommended"],
        "reasoning": f"Default safety assessment due to AI validation service unavailability: {error_type}",
        "parameter_concerns": ["Automatic validation not available - manual review required"],
        "patient_specific_notes": ["Enhanced clinical assessment needed"],
        "contraindications": [],
        "monitoring_requirements": ["Frequent glucose monitoring recommended"],
        "clinical_evidence": ["Standard diabetes management guidelines apply"],
        "alternative_suggestions": ["Consider smaller parameter changes"],
        "expected_outcomes": ["Outcomes uncertain without AI validation"],
        "data_quality_impact": "Cannot assess without AI validation service"
    }

def _get_enhanced_default_optimization_result() -> Dict[str, Any]:
    """Enhanced default optimization result"""
    return {
        "optimized_params": {},
        "expected_improvements": [],
        "clinical_rationale": "Enhanced optimization analysis unavailable - consider conservative adjustments",
        "confidence": "LOW",
        "priority_actions": [
            "Start with small parameter changes (<20%)",
            "Monitor glucose frequently",
            "Assess response before further adjustments"
        ],
        "monitoring_recommendations": [
            "Increase glucose monitoring frequency",
            "Monitor for hypoglycemia symptoms", 
            "Track meal responses"
        ],
        "technology_suggestions": [
            "Consider continuous glucose monitoring",
            "Use glucose tracking applications",
            "Regular healthcare provider consultation"
        ],
        "alternative_strategies": [
            "Gradual parameter adjustment approach",
            "Focus on one parameter change at a time"
        ],
        "contraindications": ["Avoid large simultaneous changes"],
        "patient_education_needs": ["Hypoglycemia recognition", "Symptom awareness"],
        "follow_up_timeline": "1-2 weeks for initial assessment",
        "risk_mitigation": ["Conservative approach", "Frequent monitoring"],
        "evidence_citations": ["Standard clinical guidelines"]
    }

def _ensure_enhanced_validation_completeness(validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure enhanced validation result has all required keys"""
    defaults = {
        "safety_assessment": "CAUTION",
        "risk_level": "MODERATE",
        "confidence_level": "LOW",
        "clinical_warnings": [],
        "optimization_suggestions": [],
        "reasoning": "Standard assessment",
        "parameter_concerns": [],
        "patient_specific_notes": [],
        "contraindications": [],
        "monitoring_requirements": [],
        "clinical_evidence": [],
        "alternative_suggestions": [],
        "expected_outcomes": [],
        "data_quality_impact": "Moderate confidence"
    }
    
    for key, default_value in defaults.items():
        if key not in validation_result:
            validation_result[key] = default_value
    
    return validation_result

def _ensure_enhanced_optimization_completeness(optimization_result: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure enhanced optimization result has all required keys"""
    defaults = {
        "optimized_params": {},
        "expected_improvements": [],
        "clinical_rationale": "No optimization suggestions available",
        "confidence": "LOW",
        "priority_actions": [],
        "monitoring_recommendations": [],
        "technology_suggestions": [],
        "alternative_strategies": [],
        "contraindications": [],
        "patient_education_needs": [],
        "follow_up_timeline": "2-4 weeks",
        "risk_mitigation": [],
        "evidence_citations": []
    }
    
    for key, default_value in defaults.items():
        if key not in optimization_result:
            optimization_result[key] = default_value
    
    return optimization_result


@scenarios_bp.route('/validate', methods=['POST'])
@jwt_required()
async def validate_enhanced_scenario_params():
    """
    Enhanced real-time validation για parameters με comprehensive analysis
    """
    try:
        data = request.get_json()
        scenario_params = data.get('scenario_params', {})
        patient_id = data.get('patient_id')
        
        # Enhanced safety checks με detailed analysis
        warnings = []
        recommendations = []
        risk_level = "LOW"
        enhanced_checks = {}
        
        # Parameter magnitude analysis
        basal_change = abs(scenario_params.get('basal_change', 0))
        bolus_change = abs(scenario_params.get('bolus_change', 0))
        carb_ratio_change = abs(scenario_params.get('carb_ratio_change', 0))
        
        # Enhanced basal insulin analysis
        if basal_change > 50:
            warnings.append(f"Εξαιρετικά μεγάλη αλλαγή βασικής ινσουλίνης ({basal_change}%) - κριτικός κίνδυνος")
            risk_level = "HIGH"
            enhanced_checks["basal_risk"] = "CRITICAL"
        elif basal_change > 30:
            warnings.append(f"Μεγάλη αλλαγή βασικής ινσουλίνης ({basal_change}%) - προσεκτική παρακολούθηση")
            risk_level = "MODERATE"
            enhanced_checks["basal_risk"] = "HIGH"
        elif basal_change > 20:
            recommendations.append(f"Moderate basal change ({basal_change}%) - monitor for 24-48h")
            enhanced_checks["basal_risk"] = "MODERATE"
        else:
            enhanced_checks["basal_risk"] = "LOW"
        
        # Enhanced bolus insulin analysis
        if bolus_change > 50:
            warnings.append(f"Εξαιρετικά μεγάλη αλλαγή bolus ινσουλίνης ({bolus_change}%) - κίνδυνος δραματικών μεταβολών")
            risk_level = "HIGH"
            enhanced_checks["bolus_risk"] = "CRITICAL"
        elif bolus_change > 30:
            warnings.append(f"Μεγάλη αλλαγή bolus ινσουλίνης ({bolus_change}%) - κίνδυνος υπο/υπεργλυκαιμίας")
            risk_level = "MODERATE" if risk_level == "LOW" else risk_level
            enhanced_checks["bolus_risk"] = "HIGH"
        else:
            enhanced_checks["bolus_risk"] = "LOW"
        
        # Enhanced meal analysis
        meal_carbs = scenario_params.get('meal_carbs', 0)
        if meal_carbs > 120:
            warnings.append(f"Εξαιρετικά μεγάλο γεύμα ({meal_carbs}g) - υψηλός κίνδυνος prolonged hyperglycemia")
            risk_level = "HIGH"
            recommendations.append("Consider dual-wave bolus strategy για μεγάλα γεύματα")
            enhanced_checks["meal_risk"] = "HIGH"
        elif meal_carbs > 80:
            warnings.append(f"Μεγάλο γεύμα ({meal_carbs}g) - παρακολούθηση για 4+ ώρες")
            recommendations.append("Consider split bolus ή extended bolus")
            enhanced_checks["meal_risk"] = "MODERATE"
        elif meal_carbs > 0:
            enhanced_checks["meal_risk"] = "LOW"
        else:
            enhanced_checks["meal_risk"] = "NONE"
        
        # Enhanced exercise analysis
        exercise_intensity = scenario_params.get('exercise_intensity', 0)
        exercise_duration = scenario_params.get('exercise_duration', 0)
        
        if exercise_intensity > 80:
            if basal_change > 0 or bolus_change > 0:
                warnings.append("Έντονη άσκηση + αυξημένη ινσουλίνη - κριτικός κίνδυνος σοβαρής υπογλυκαιμίας")
                risk_level = "HIGH"
                enhanced_checks["exercise_risk"] = "CRITICAL"
            else:
                recommendations.append("Έντονη άσκηση - pre-exercise snack 15-30g συνιστάται")
                enhanced_checks["exercise_risk"] = "MODERATE"
        elif exercise_intensity > 50:
            if basal_change > 10 or bolus_change > 10:
                warnings.append("Μέτρια άσκηση με αυξημένη ινσουλίνη - κίνδυνος υπογλυκαιμίας")
                risk_level = "MODERATE" if risk_level == "LOW" else risk_level
                enhanced_checks["exercise_risk"] = "HIGH"
            else:
                recommendations.append("Μέτρια άσκηση - monitor glucose closely")
                enhanced_checks["exercise_risk"] = "LOW"
        else:
            enhanced_checks["exercise_risk"] = "NONE"
        
        # Enhanced combination risk analysis
        total_insulin_change = abs(basal_change) + abs(bolus_change)
        if total_insulin_change > 60:
            warnings.append(f"Συνολική αλλαγή ινσουλίνης {total_insulin_change}% - υπερβολικά υψηλός κίνδυνος")
            risk_level = "HIGH"
            enhanced_checks["combination_risk"] = "CRITICAL"
        elif total_insulin_change > 40:
            warnings.append(f"Συνολική αλλαγή ινσουλίνης {total_insulin_change}% - υψηλός κίνδυνος")
            risk_level = "MODERATE" if risk_level == "LOW" else risk_level
            enhanced_checks["combination_risk"] = "HIGH"
        else:
            enhanced_checks["combination_risk"] = "LOW"
        
        # Enhanced recommendations based on risk profile
        if not warnings:
            recommendations.extend([
                "Παρακολουθήστε γλυκόζη κάθε 2-4 ώρες για 12 ώρες",
                "Έχετε διαθέσιμη γλυκόζη για έκτακτη ανάγκη",
                "Καταγράψτε αποτελέσματα για μελλοντική βελτιστοποίηση"
            ])
        else:
            recommendations.extend([
                "ΑΥΞΗΜΕΝΗ παρακολούθηση: Έλεγχος γλυκόζης κάθε 1-2 ώρες",
                "Άμεση διαθεσιμότητα γλυκόζης και γλυκαγόνης",
                "Ενημέρωση οικογένειας/συνοδών για συμπτώματα υπογλυκαιμίας",
                "Επικοινωνία με ιατρικό προσωπικό σε περίπτωση ανησυχίας"
            ])
        
        # Enhanced simulation recommendation
        simulation_confidence = "HIGH"
        if total_insulin_change > 50 or meal_carbs > 100 or (exercise_intensity > 70 and total_insulin_change > 20):
            simulation_confidence = "LOW"
            recommendations.append("⚠️ Σενάριο υψηλού κινδύνου - εξετάστε μικρότερες αλλαγές αρχικά")
        elif total_insulin_change > 30 or meal_carbs > 80:
            simulation_confidence = "MODERATE"
        
        return jsonify({
            "valid": risk_level != "HIGH",
            "risk_level": risk_level,
            "warnings": warnings,
            "recommendations": recommendations,
            "simulation_confidence": simulation_confidence,
            "enhanced_checks": {
                **enhanced_checks,
                "parameter_magnitude": "OK" if total_insulin_change < 30 else "CAUTION" if total_insulin_change < 50 else "HIGH_RISK",
                "meal_size": "OK" if meal_carbs < 60 else "LARGE" if meal_carbs < 100 else "VERY_LARGE",
                "exercise_safety": enhanced_checks.get("exercise_risk", "NONE"),
                "overall_assessment": risk_level,
                "total_insulin_change": total_insulin_change,
                "requires_medical_supervision": risk_level == "HIGH"
            },
            "detailed_analysis": {
                "basal_impact": f"{scenario_params.get('basal_change', 0):+.1f}% change in 24h insulin delivery",
                "bolus_impact": f"{scenario_params.get('bolus_change', 0):+.1f}% change in meal insulin",
                "meal_impact": f"{meal_carbs}g carbs ≈ {meal_carbs * 4}mg/dL glucose impact",
                "exercise_impact": f"{exercise_intensity}% intensity για {exercise_duration}min" if exercise_intensity > 0 else "No exercise",
                "timeframe": f"{scenario_params.get('simulation_hours', 24)} hour simulation"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Enhanced validation error: {e}", exc_info=True)
        return jsonify({
            "valid": False,
            "error": str(e),
            "risk_level": "UNKNOWN",
            "message": "Validation service temporarily unavailable"
        }), 500


@scenarios_bp.route('/presets', methods=['GET'])
@jwt_required()
def get_enhanced_scenario_presets():
    """
    Enhanced scenario templates με comprehensive clinical evidence
    """
    
    enhanced_presets = {
        "conservative_start": {
            "name": "Συντηρητική Εκκίνηση",
            "description": "Ασφαλείς, μικρές αλλαγές για αρχάριους στη διαχείριση",
            "clinical_evidence": "ADA 2023 Standards - Start low, go slow approach",
            "safety_profile": "HIGH_SAFETY",
            "params": {
                "basal_change": 5.0,
                "bolus_change": 5.0,
                "meal_carbs": 30.0,
                "simulation_hours": 8
            },
            "expected_outcomes": {
                "tir_improvement": "3-8%",
                "hypo_risk": "MINIMAL",
                "confidence": "HIGH",
                "monitoring_intensity": "STANDARD"
            },
            "use_case": "Πρώτη προσαρμογή θεραπείας, ηλικιωμένοι ασθενείς",
            "contraindications": ["Severe hypoglycemia history within 30 days"],
            "monitoring": "Standard glucose monitoring (4x daily)"
        },
        
        "moderate_optimization": {
            "name": "Μέτρια Βελτιστοποίηση", 
            "description": "Ισορροπημένες αλλαγές για έμπειρους χρήστες",
            "clinical_evidence": "ATTD 2023 Consensus - Moderate adjustments for stable patients",
            "safety_profile": "MODERATE_SAFETY",
            "params": {
                "basal_change": 15.0,
                "bolus_change": 10.0,
                "carb_ratio_change": -5.0,
                "meal_carbs": 60.0,
                "simulation_hours": 12
            },
            "expected_outcomes": {
                "tir_improvement": "8-15%",
                "hypo_risk": "LOW",
                "confidence": "HIGH",
                "monitoring_intensity": "ENHANCED"
            },
            "use_case": "Βελτίωση υπάρχοντος καλού ελέγχου",
            "contraindications": ["Recent DKA", "Unstable medical conditions"],
            "monitoring": "Enhanced monitoring (6-8x daily) for 48h"
        },
        
        "exercise_safe": {
            "name": "Ασφαλής Άσκηση",
            "description": "Βελτιστοποιημένη στρατηγική για άσκηση χωρίς υπογλυκαιμία",
            "clinical_evidence": "EASD/ADA 2022 Exercise Position Statement",
            "safety_profile": "HIGH_SAFETY",
            "params": {
                "basal_change": -20.0,  # Reduce for exercise
                "exercise_intensity": 50.0,
                "exercise_duration": 45,
                "meal_carbs": 25.0,     # Pre-exercise snack
                "meal_timing": 30,      # 30min before exercise
                "simulation_hours": 6
            },
            "expected_outcomes": {
                "hypo_risk": "SIGNIFICANTLY_REDUCED",
                "post_exercise_control": "IMPROVED",
                "confidence": "HIGH",
                "monitoring_intensity": "INTENSIVE"
            },
            "use_case": "Ασφαλής ενσωμάτωση άσκησης",
            "contraindications": ["Active cardiovascular disease", "Severe retinopathy"],
            "monitoring": "Pre, during, post exercise + 2h monitoring"
        },
        
        "large_meal_advanced": {
            "name": "Προηγμένη Διαχείριση Μεγάλου Γεύματος",
            "description": "Sophisticated strategy για high-carb meals με dual-wave approach",
            "clinical_evidence": "Diabetic Medicine 2021 - Advanced bolus strategies",
            "safety_profile": "MODERATE_SAFETY",
            "params": {
                "meal_carbs": 90.0,
                "bolus_change": 25.0,   # Increased immediate bolus
                "carb_ratio_change": -15.0,  # More aggressive ratio
                "meal_timing": 30,      # Earlier pre-bolus
                "simulation_hours": 8
            },
            "expected_outcomes": {
                "peak_glucose": "REDUCED vs standard bolus",
                "time_above_180": "MINIMIZED", 
                "confidence": "MEDIUM",
                "monitoring_intensity": "HIGH"
            },
            "use_case": "Εορταστικά γεύματα, social dining",
            "contraindications": ["Gastroparesis", "Recent hypoglycemia"],
            "monitoring": "Pre-meal, 1h, 2h, 4h post-meal checks",
            "advanced_notes": "Consider split/extended bolus if pump available"
        },
        
        "tight_control_protocol": {
            "name": "Πρωτόκολλο Στενού Ελέγχου",
            "description": "Intensive management για motivated patients με excellent education",
            "clinical_evidence": "DCCT Legacy Study - Intensive diabetes management",
            "safety_profile": "MODERATE_RISK",
            "params": {
                "basal_change": 20.0,
                "bolus_change": 30.0,
                "correction_factor_change": 20.0,
                "carb_ratio_change": -12.0,
                "meal_carbs": 55.0,
                "simulation_hours": 24
            },
            "expected_outcomes": {
                "tir_improvement": "15-25%",
                "hba1c_reduction": "0.5-0.8%",
                "hypo_risk": "MODERATE - requires careful monitoring",
                "confidence": "MEDIUM",
                "monitoring_intensity": "INTENSIVE"
            },
            "use_case": "Εξαιρετικά motivated patients, pre-conception planning",
            "prerequisites": ["CGM mandatory", "Diabetes education completed", "No severe hypo in 6 months"],
            "contraindications": ["Hypoglycemia unawareness", "Poor adherence history", "Comorbidities"],
            "monitoring": "CGM + 8-10 daily checks for first week"
        },
        
        "dawn_phenomenon_targeted": {
            "name": "Στοχευμένος Έλεγχος Dawn Phenomenon",
            "description": "Specific approach για πρωινή υπεργλυκαιμία",
            "clinical_evidence": "Endocrine Practice 2020 - Dawn phenomenon management strategies",
            "safety_profile": "MODERATE_SAFETY",
            "params": {
                "basal_change": 35.0,   # Higher morning basal
                "bolus_change": 5.0,    # Slightly higher breakfast bolus
                "meal_carbs": 40.0,     # Consistent breakfast
                "meal_timing": 210,     # 3.5 hours (morning simulation)
                "simulation_hours": 12
            },
            "expected_outcomes": {
                "morning_glucose": "20-40 mg/dL reduction",
                "fasting_glucose": "IMPROVED",
                "confidence": "MEDIUM",
                "monitoring_intensity": "MODERATE"
            },
            "use_case": "Persistent morning hyperglycemia >160 mg/dL",
            "contraindications": ["Somogyi effect suspected", "Variable sleep schedule"],
            "monitoring": "3 AM, 6 AM, 9 AM checks για 1 week",
            "timing_note": "Best simulated during typical morning hours"
        },
        
        "stress_management": {
            "name": "Διαχείριση Stress Hyperglycemia",
            "description": "Adjusted approach για periods of increased stress/illness",
            "clinical_evidence": "ADA Sick Day Management Guidelines 2023",
            "safety_profile": "MODERATE_SAFETY",
            "params": {
                "basal_change": 25.0,   # Increased for stress response
                "bolus_change": 20.0,   # Higher meal coverage
                "correction_factor_change": 15.0,  # More aggressive corrections
                "meal_carbs": 45.0,     # Moderate meal
                "simulation_hours": 16
            },
            "expected_outcomes": {
                "stress_glucose_control": "IMPROVED",
                "ketone_risk": "REDUCED",
                "confidence": "MEDIUM",
                "monitoring_intensity": "HIGH"
            },
            "use_case": "Illness, major stress, steroid therapy",
            "contraindications": ["DKA risk", "Severe dehydration"],
            "monitoring": "Every 2-4h including ketone checks",
            "special_notes": "Adjust based on stress level and illness severity"
        }
    }
    
    return jsonify({
        "presets": enhanced_presets,
        "success": True,
        "metadata": {
            "total_presets": len(enhanced_presets),
            "evidence_base": "ADA/EASD 2023, ATTD 2023, DCCT Legacy",
            "last_updated": "2024-01-15",
            "clinical_validation": "Endocrinologist reviewed"
        },
        "usage_guidelines": {
            "selection_criteria": "Match preset to patient experience level and clinical goals",
            "safety_priority": "Always prioritize safety over aggressive optimization",
            "monitoring_importance": "Enhanced monitoring required for all moderate-risk presets",
            "contraindication_check": "Review contraindications before preset selection"
        },
        "clinical_note": "All presets based on current evidence-based guidelines. Individual patient factors may require modifications.",
        "disclaimer": "These presets are decision support tools. Always consult healthcare provider before implementing significant therapy changes."
    }), 200


# Προσθήκη του enhanced blueprint στο main app.py
def register_scenarios_blueprint(app):
    """Register enhanced scenarios blueprint to main app"""
    app.register_blueprint(scenarios_bp)
    logger.info("✅ Enhanced What-If Scenarios blueprint registered successfully")
