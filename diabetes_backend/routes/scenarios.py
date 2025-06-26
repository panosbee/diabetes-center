"""
Διορθωμένο scenarios.py με proper JSON handling
===============================================
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from bson.errors import InvalidId
import logging
import os
import datetime
import asyncio
import json  # ΠΡΟΣΘΗΚΗ - explicit import
from typing import Dict, Any, Optional  # ΠΡΟΣΘΗΚΗ - type hints

from utils.db import get_db
from utils.permissions import ViewPatientPermission, permission_denied

# Import του Digital Twin Engine
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
async def simulate_what_if_scenario():
    """
    Endpoint για What-If scenario simulation με AI validation
    """
    requesting_user_id_str = get_jwt_identity()
    
    logger.info("🚀 What-If Scenarios endpoint called")
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        if not data or 'patient_id' not in data:
            return jsonify({"error": "Request body must be JSON and contain 'patient_id' field"}), 400
        
        patient_id = data.get('patient_id')
        scenario_params = data.get('scenario_params', {})
        
        logger.info(f"🔍 What-If simulation requested for patient: {patient_id}")
        logger.info(f"📊 Scenario parameters: {scenario_params}")
        
        try:
            patient_object_id = ObjectId(patient_id)
            view_permission = ViewPatientPermission(patient_id)
            if not view_permission.can():
                return permission_denied("Δεν έχετε δικαίωμα πρόσβασης στα δεδομένα αυτού του ασθενή")
        except InvalidId:
             return jsonify({"error": "Invalid patient ID format provided"}), 400
        
        # Συλλογή πλήρων δεδομένων ασθενή (όπως στο analysis endpoint)
        patient_data = db.patients.find_one({"_id": patient_object_id})
        if not patient_data:
            return jsonify({"error": "Patient not found"}), 404
        
        # Συλλογή sessions με measurements
        sessions = list(db.sessions.find({"patient_id": patient_object_id}).sort("timestamp", -1))
        measurements_data = []
        
        for session in sessions:
            if 'vitals_recorded' not in session or not session['vitals_recorded']:
                continue
                
            timestamp_iso = session['timestamp'].isoformat() if isinstance(session['timestamp'], datetime.datetime) else str(session['timestamp'])
            vitals = session['vitals_recorded']
            
            measurement = {
                "date": timestamp_iso,
                "weight_kg": vitals.get('weight_kg'),
                "height_cm": vitals.get('height_cm'),
                "bmi": vitals.get('bmi'),
                "blood_glucose_level": vitals.get('blood_glucose_level'),
                "blood_glucose_type": vitals.get('blood_glucose_type', 'undefined'),
                "hba1c": vitals.get('hba1c'),
                "blood_pressure_systolic": vitals.get('blood_pressure_systolic'),
                "blood_pressure_diastolic": vitals.get('blood_pressure_diastolic'),
                "insulin_units": vitals.get('insulin_units')
            }
            measurements_data.append(measurement)
        
        logger.info(f"📈 Found {len(measurements_data)} measurements for simulation")
        
        # Προσθήκη measurements στα patient data
        comprehensive_patient_data = {
            **patient_data.get('personal_details', {}),
            **patient_data.get('medical_profile', {}),
            'measurements': measurements_data
        }
        
        # === AI VALIDATION AGENT ===
        logger.info("🤖 Starting AI validation of scenario parameters...")
        
        # Δημιουργία AI validation prompt
        validation_prompt = f"""
Αξιολόγηση What-If Scenario για διαχείριση διαβήτη:

PATIENT DATA:
- Conditions: {[c.get('condition_name', '') for c in comprehensive_patient_data.get('conditions', [])]}
- Latest measurements: {measurements_data[-1] if measurements_data else 'None'}

PROPOSED SCENARIO:
- Basal insulin change: {scenario_params.get('basal_change', 0)}%
- Bolus insulin change: {scenario_params.get('bolus_change', 0)}%
- Carb ratio change: {scenario_params.get('carb_ratio_change', 0)}%
- Meal carbs: {scenario_params.get('meal_carbs', 0)}g
- Exercise: {scenario_params.get('exercise_intensity', 0)}% for {scenario_params.get('exercise_duration', 0)} min

Παρέχεις JSON response με:
{{
    "safety_assessment": "SAFE/CAUTION/UNSAFE",
    "risk_level": "LOW/MODERATE/HIGH",
    "clinical_warnings": ["warning1", "warning2"],
    "optimization_suggestions": ["suggestion1", "suggestion2"],
    "confidence": "HIGH/MEDIUM/LOW"
}}

ΚΡΙΤΗΡΙΑ ΑΣΦΑΛΕΙΑΣ:
- Αλλαγές >50% σε insulin = UNSAFE
- Πολύ μεγάλα γεύματα (>100g carbs) = CAUTION
- Έντονη άσκηση + αύξηση insulin = UNSAFE
- Μη αλληλεπίδραση με τρέχουσα κατάσταση ασθενή
"""
        
        # AI VALIDATION με proper error handling
        validation_result: Dict[str, Any] = {}
        try:
            ai_validation_response: str = await ask_rag_question(validation_prompt)
            
            # Parse AI validation με proper error handling
            if ai_validation_response and ai_validation_response.strip():
                try:
                    validation_result = json.loads(ai_validation_response.strip())
                    logger.info(f"🤖 AI Validation parsed successfully: {validation_result.get('safety_assessment')}")
                except json.JSONDecodeError as json_error:
                    logger.warning(f"⚠️ JSON decode error in AI validation: {json_error}")
                    logger.warning(f"Raw AI response: {ai_validation_response[:200]}...")
                    # Try to extract JSON from response if it's embedded
                    try:
                        # Look for JSON-like content in the response
                        import re
                        json_match = re.search(r'\{.*\}', ai_validation_response, re.DOTALL)
                        if json_match:
                            validation_result = json.loads(json_match.group())
                            logger.info("🔧 Successfully extracted JSON from AI response")
                        else:
                            raise ValueError("No JSON found in response")
                    except (json.JSONDecodeError, ValueError) as fallback_error:
                        logger.error(f"❌ Fallback JSON parsing failed: {fallback_error}")
                        validation_result = _get_default_validation_result("JSON_PARSE_ERROR")
            else:
                logger.warning("⚠️ Empty AI validation response")
                validation_result = _get_default_validation_result("EMPTY_RESPONSE")
                
        except Exception as ai_error:
            logger.error(f"❌ AI validation failed: {ai_error}")
            validation_result = _get_default_validation_result("AI_ERROR")
        
        # Ensure validation_result has all required keys
        validation_result = _ensure_validation_completeness(validation_result)
        
        logger.info(f"🤖 Final AI Validation: {validation_result.get('safety_assessment')} - {validation_result.get('risk_level')}")
        
        # === DIGITAL TWIN SIMULATION ===
        logger.info("🧬 Starting Digital Twin simulation...")
        
        # Ensure scenario_params have default values
        default_scenario = {
            "basal_change": 0.0,
            "bolus_change": 0.0,  
            "carb_ratio_change": 0.0,
            "correction_factor_change": 0.0,
            "meal_carbs": 0.0,
            "meal_timing": 60,
            "exercise_intensity": 0.0,
            "exercise_duration": 0,
            "simulation_hours": 24,
            "time_step_minutes": 15
        }
        default_scenario.update(scenario_params)
        
        try:
            # Κλήση του Digital Twin Engine
            simulation_result = await digital_twin_engine.simulate_what_if_scenario(
                comprehensive_patient_data, 
                default_scenario
            )
            
            if not simulation_result.get('success'):
                raise Exception(simulation_result.get('error', 'Unknown simulation error'))
                
            logger.info("✅ Digital Twin simulation completed successfully")
            
        except Exception as sim_error:
            logger.error(f"❌ Digital Twin simulation failed: {sim_error}")
            return jsonify({
                "error": "Simulation failed",
                "details": str(sim_error),
                "message": "Σφάλμα κατά την προσομοίωση. Παρακαλώ ελέγξτε τις παραμέτρους."
            }), 500
        
        # === AI OPTIMIZATION AGENT ===
        logger.info("🎯 Starting AI optimization suggestions...")
        
        optimization_result: Dict[str, Any] = {}
        try:
            optimization_prompt = f"""
Βελτιστοποίηση αποτελεσμάτων Digital Twin simulation:

ΑΠΟΤΕΛΕΣΜΑΤΑ ΠΡΟΣΟΜΟΙΩΣΗΣ:
- Mean glucose: {simulation_result['simulation_results']['glucose_metrics']['mean_glucose']:.1f} mg/dL
- Time in Range: {simulation_result['simulation_results']['glucose_metrics']['tir_70_180']:.1f}%
- Glucose CV: {simulation_result['simulation_results']['glucose_metrics']['glucose_cv']:.1f}%
- Overall risk: {simulation_result['simulation_results']['risk_scores']['overall_risk']:.1f}%

SAFETY ALERTS: {simulation_result['simulation_results']['safety_alerts']}

Παρέχεις JSON με βελτιστοποιημένες παραμέτρους:
{{
    "optimized_params": {{
        "basal_change": -5.0,
        "bolus_change": 10.0,
        "carb_ratio_change": 0.0
    }},
    "expected_improvements": ["TIR +15%", "CV -10%"],
    "clinical_rationale": "Explanation here",
    "confidence": "HIGH/MEDIUM/LOW"
}}
"""
            
            optimization_response: str = await ask_rag_question(optimization_prompt)
            
            # ΔΙΟΡΘΩΜΕΝΟ JSON PARSING με proper error handling
            if optimization_response and optimization_response.strip():
                try:
                    optimization_result = json.loads(optimization_response.strip())
                    logger.info("🎯 AI Optimization parsed successfully")
                except json.JSONDecodeError as opt_json_error:
                    logger.warning(f"⚠️ JSON decode error in optimization: {opt_json_error}")
                    logger.warning(f"Raw optimization response: {optimization_response[:200]}...")
                    # Try to extract JSON from response
                    try:
                        import re
                        json_match = re.search(r'\{.*\}', optimization_response, re.DOTALL)
                        if json_match:
                            optimization_result = json.loads(json_match.group())
                            logger.info("🔧 Successfully extracted JSON from optimization response")
                        else:
                            raise ValueError("No JSON found in optimization response")
                    except (json.JSONDecodeError, ValueError):
                        logger.error("❌ Fallback optimization JSON parsing failed")
                        optimization_result = _get_default_optimization_result()
            else:
                logger.warning("⚠️ Empty optimization response")
                optimization_result = _get_default_optimization_result()
                
        except Exception as opt_error:
            logger.error(f"❌ AI optimization failed: {opt_error}")
            optimization_result = _get_default_optimization_result()
        
        # Ensure optimization_result has all required keys
        optimization_result = _ensure_optimization_completeness(optimization_result)
        
        # === FINAL RESPONSE ASSEMBLY ===
        
        response_payload = {
            "id": f"whatif-simulation-{datetime.datetime.now().timestamp()}",
            "success": True,
            "patient_id": patient_id,
            "scenario_params": default_scenario,
            
            # AI Validation Results
            "ai_validation": validation_result,
            
            # Digital Twin Simulation Results
            "simulation": simulation_result['simulation_results'],
            "patient_profile": simulation_result['patient_profile'],
            
            # Mindmap Data για Frontend
            "mindmap_data": simulation_result['mindmap_data'],
            
            # Comparison Data
            "comparison_data": simulation_result['comparison_data'],
            
            # AI Optimization
            "optimization": optimization_result,
            
            # Debug Information
            "debug_info": {
                "measurements_count": len(measurements_data),
                "simulation_success": simulation_result.get('success'),
                "ai_validation_confidence": validation_result.get('confidence'),
                "ai_optimization_confidence": optimization_result.get('confidence'),
                "total_simulation_time": simulation_result['simulation_results']['scenario_summary'].get('simulation_hours', 24),
                "risk_level": validation_result.get('risk_level'),
                "safety_assessment": validation_result.get('safety_assessment')
            }
        }
        
        logger.info(f"✅ What-If scenario completed successfully!")
        logger.info(f"📊 Safety: {validation_result.get('safety_assessment')}, TIR: {simulation_result['simulation_results']['glucose_metrics']['tir_70_180']:.1f}%")
        
        return jsonify(response_payload), 200

    except Exception as e:
        logger.error(f"❌ Error in What-If scenarios: {e}", exc_info=True)
        return jsonify({
            "error": "An internal server error occurred during simulation",
            "details": str(e)
        }), 500


# === HELPER FUNCTIONS για proper JSON handling ===

def _get_default_validation_result(error_type: str = "UNKNOWN") -> Dict[str, Any]:
    """Default validation result when AI parsing fails"""
    return {
        "safety_assessment": "CAUTION",
        "risk_level": "MODERATE",
        "clinical_warnings": [f"AI validation μη διαθέσιμο ({error_type}) - χρησιμοποιήστε κλινική κρίση"],
        "optimization_suggestions": ["Προσεκτική παρακολούθηση συνιστάται"],
        "confidence": "LOW"
    }

def _get_default_optimization_result() -> Dict[str, Any]:
    """Default optimization result when AI parsing fails"""
    return {
        "optimized_params": {},
        "expected_improvements": [],
        "clinical_rationale": "Optimization analysis unavailable",
        "confidence": "LOW"
    }

def _ensure_validation_completeness(validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure validation result has all required keys"""
    defaults = {
        "safety_assessment": "CAUTION",
        "risk_level": "MODERATE",
        "clinical_warnings": [],
        "optimization_suggestions": [],
        "confidence": "LOW"
    }
    
    for key, default_value in defaults.items():
        if key not in validation_result:
            validation_result[key] = default_value
    
    return validation_result

def _ensure_optimization_completeness(optimization_result: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure optimization result has all required keys"""
    defaults = {
        "optimized_params": {},
        "expected_improvements": [],
        "clinical_rationale": "No optimization suggestions available",
        "confidence": "LOW"
    }
    
    for key, default_value in defaults.items():
        if key not in optimization_result:
            optimization_result[key] = default_value
    
    return optimization_result


@scenarios_bp.route('/validate', methods=['POST'])
@jwt_required()
async def validate_scenario_params():
    """
    Quick validation endpoint για real-time parameter checking
    """
    try:
        data = request.get_json()
        scenario_params = data.get('scenario_params', {})
        
        # Quick safety checks
        warnings = []
        risk_level = "LOW"
        
        # Check for extreme parameter changes
        if abs(scenario_params.get('basal_change', 0)) > 50:
            warnings.append("Μεγάλη αλλαγή βασικής ινσουλίνης (>50%)")
            risk_level = "HIGH"
        
        if abs(scenario_params.get('bolus_change', 0)) > 50:
            warnings.append("Μεγάλη αλλαγή bolus ινσουλίνης (>50%)")
            risk_level = "HIGH"
        
        if scenario_params.get('meal_carbs', 0) > 100:
            warnings.append("Μεγάλο γεύμα (>100g υδατάνθρακες)")
            risk_level = "MODERATE" if risk_level == "LOW" else risk_level
        
        # Exercise + insulin interaction
        exercise_intensity = scenario_params.get('exercise_intensity', 0)
        if exercise_intensity > 70 and scenario_params.get('basal_change', 0) > 0:
            warnings.append("Έντονη άσκηση με αύξηση ινσουλίνης - κίνδυνος υπογλυκαιμίας")
            risk_level = "HIGH"
        
        return jsonify({
            "valid": risk_level != "HIGH",
            "risk_level": risk_level,
            "warnings": warnings,
            "recommendations": [
                "Ξεκινήστε με μικρές αλλαγές (<20%)",
                "Παρακολουθήστε στενά τη γλυκόζη",
                "Έχετε διαθέσιμη γλυκόζη για υπογλυκαιμία"
            ] if warnings else []
        }), 200
        
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return jsonify({
            "valid": False,
            "error": str(e)
        }), 500


@scenarios_bp.route('/presets', methods=['GET'])
@jwt_required()
def get_scenario_presets():
    """
    Επιστρέφει προκαθορισμένα scenario templates
    """
    
    presets = {
        "mild_adjustment": {
            "name": "Ήπια Προσαρμογή",
            "description": "Μικρές αλλαγές για fine-tuning",
            "params": {
                "basal_change": 10.0,
                "bolus_change": 5.0,
                "meal_carbs": 45.0,
                "simulation_hours": 12
            },
            "use_case": "Βελτίωση γλυκαιμικού ελέγχου"
        },
        "exercise_scenario": {
            "name": "Σενάριο Άσκησης",
            "description": "Προσαρμογή για άσκηση",
            "params": {
                "basal_change": -20.0,
                "exercise_intensity": 60.0,
                "exercise_duration": 45,
                "meal_carbs": 30.0,
                "simulation_hours": 8
            },
            "use_case": "Άσκηση χωρίς υπογλυκαιμία"
        },
        "large_meal": {
            "name": "Μεγάλο Γεύμα",
            "description": "Διαχείριση μεγάλου γεύματος",
            "params": {
                "meal_carbs": 80.0,
                "bolus_change": 15.0,
                "carb_ratio_change": -10.0,
                "simulation_hours": 6
            },
            "use_case": "Γεύματα με πολλούς υδατάνθρακες"
        },
        "tight_control": {
            "name": "Στενός Έλεγχος",
            "description": "Πιο αυστηρός γλυκαιμικός έλεγχος",
            "params": {
                "basal_change": 15.0,
                "bolus_change": 20.0,
                "correction_factor_change": 10.0,
                "simulation_hours": 24
            },
            "use_case": "Βελτίωση Time in Range"
        }
    }
    
    return jsonify({
        "presets": presets,
        "success": True
    }), 200


# Προσθήκη του blueprint στο main app.py
def register_scenarios_blueprint(app):
    """Register scenarios blueprint to main app"""
    app.register_blueprint(scenarios_bp)
    logger.info("✅ What-If Scenarios blueprint registered")