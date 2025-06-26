from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from bson.errors import InvalidId
import logging
import os
import datetime
import requests
import time
from utils.db import get_db
from utils.permissions import ViewPatientPermission, permission_denied

# Ρύθμιση logger
logger = logging.getLogger(__name__)

# DecisionEngine import with fallback
try:
    # First try relative import (works in development)
    from ..services.decision_engine import DecisionEngine
except ImportError:
    try:
        # Fall back to absolute import (works when package is installed)
        from diabetes_backend.services.decision_engine import DecisionEngine
    except ImportError as e:
        logger.error(f"Failed to import DecisionEngine: {e}")
        raise

# Δημιουργία blueprint
ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

# Η σύνδεση στη βάση δεδομένων
db = get_db()

# API Configuration
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL")
DEEPSEEK_API_TIMEOUT = 90  # seconds
DEEPSEEK_MAX_RETRIES = 3
DEEPSEEK_RETRY_DELAY = 1  # initial delay in seconds

def validate_deepseek_config():
    """Validate DeepSeek API configuration on startup"""
    if not DEEPSEEK_API_KEY or not DEEPSEEK_API_URL:
        logger.error("DeepSeek API configuration incomplete")
        return False
    
    # Test API connectivity
    try:
        test_payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 5
        }
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}'},
            json=test_payload,
            timeout=10
        )
        if response.status_code == 401:
            logger.error("DeepSeek API key validation failed - unauthorized")
            return False
        return True
    except Exception as e:
        logger.error(f"DeepSeek API validation failed: {str(e)}")
        return False

# Validate on import
if not validate_deepseek_config():
    logger.warning("DeepSeek API configuration validation failed - AI features may not work")

# PubMed RAG VectorDB initialization
from services.vector_db import VectorDB
PUBMED_API_KEY = os.environ.get("PUBMED_API_KEY")
vector_db = None

if PUBMED_API_KEY:
    try:
        vector_db = VectorDB()
        logger.info("✅ PubMed VectorDB initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize PubMed VectorDB: {e}")
        vector_db = None
else:
    logger.warning("⚠️ PUBMED_API_KEY not set - PubMed RAG disabled")

# Genetics Analyzer initialization
from services.genetics_analyzer import DMPGeneticsAnalyzer
from services.deepseek_integration import ask_rag_question
genetics_analyzer = DMPGeneticsAnalyzer(deepseek_function=ask_rag_question)

# Έλεγχος αν έχουν οριστεί οι μεταβλητές περιβάλλοντος
if not DEEPSEEK_API_KEY:
    logger.warning("DEEPSEEK_API_KEY not found in environment variables!")
if not DEEPSEEK_API_URL:
    logger.warning("DEEPSEEK_API_URL not found in environment variables! AI query will not work.")

@ai_bp.route('/query', methods=['OPTIONS'])
def ai_query_options():
    """Handle OPTIONS requests for CORS preflight"""
    response = jsonify({"message": "OK"})
    return response

@ai_bp.route('/query', methods=['POST'])
@jwt_required()
def ai_query():
    """Endpoint για αιτήματα προς το AI με enhanced evidence integration"""
    requesting_user_id_str = get_jwt_identity()
    measurements_data = []
    
    logger.info("🚀 AI Query endpoint called")
    
    if not DEEPSEEK_API_KEY or not DEEPSEEK_API_URL:
        error_msg = "AI service is not configured: "
        if not DEEPSEEK_API_KEY:
            error_msg += "API key missing. "
        if not DEEPSEEK_API_URL:
            error_msg += "API URL missing."
        return jsonify({"error": error_msg.strip()}), 503

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Request body must be JSON and contain a 'query' field"}), 400
        
        user_query = data['query']
        patient_id = data.get('patient_id') 
        patient_amka = data.get('amka')
        patient_object_id = None
        
        logger.info(f"🔍 User query: '{user_query[:100]}...'")
        logger.info(f"🔍 Patient ID: {patient_id}, AMKA: {patient_amka}")

        # Εύρεση Patient ObjectId
        if patient_id:
            try:
                patient_object_id = ObjectId(patient_id)
                view_permission = ViewPatientPermission(patient_id)
                if not view_permission.can():
                    return permission_denied("Δεν έχετε δικαίωμα πρόσβασης στα δεδομένα αυτού του ασθενή")
                logger.info(f"✅ Patient found by ID: {patient_object_id}")
            except InvalidId:
                 return jsonify({"error": "Invalid patient ID format provided for context"}), 400
        elif patient_amka:
             if db is None: 
                 return jsonify({"error": "Database connection failed"}), 500
             patient_found_by_amka = db.patients.find_one({"personal_details.amka": patient_amka}, {"_id": 1})
             if patient_found_by_amka:
                 patient_object_id = patient_found_by_amka['_id']
                 view_permission = ViewPatientPermission(str(patient_object_id))
                 if not view_permission.can():
                     return permission_denied("Δεν έχετε δικαίωμα πρόσβασης στα δεδομένα αυτού του ασθενή")
                 logger.info(f"✅ Patient found by AMKA: {patient_object_id}")
             else:
                 logger.info(f"❌ No patient found with AMKA: {patient_amka}")
                 return jsonify({
                     "id": f"ai-no-context-{datetime.datetime.now().timestamp()}", 
                     "response": f"Δεν βρέθηκε ασθενής με ΑΜΚΑ {patient_amka} για να φορτωθεί το context."
                 }), 200

        # Συλλογή Context
        context = ""
        if patient_object_id:
            try:
                logger.info(f"🔄 Collecting context for patient: {patient_object_id}")
                patient_data = db.patients.find_one({"_id": patient_object_id})
                sessions_data = list(db.sessions.find({"patient_id": patient_object_id}).sort("timestamp", -1).limit(5))
                
                logger.info(f"📊 Found {len(sessions_data)} sessions for patient")
                
                # Μετρήσεις για DecisionEngine
                recent_sessions_with_measurements = list(db.sessions.find({
                    "patient_id": patient_object_id,
                    "vitals_recorded": {"$exists": True}
                }).sort("timestamp", -1).limit(5))
                
                for session in recent_sessions_with_measurements:
                    if 'vitals_recorded' in session:
                        measurements_data.append({
                            "date": session['timestamp'].isoformat() if isinstance(session.get('timestamp'), datetime.datetime) else str(session.get('timestamp', '')),
                            "blood_glucose_level": session['vitals_recorded'].get('blood_glucose_level'),
                            "blood_glucose_type": session['vitals_recorded'].get('blood_glucose_type', 'undefined'),
                            "hba1c": session['vitals_recorded'].get('hba1c'),
                            "weight_kg": session['vitals_recorded'].get('weight_kg'),
                            "blood_pressure_systolic": session['vitals_recorded'].get('blood_pressure_systolic'),
                            "blood_pressure_diastolic": session['vitals_recorded'].get('blood_pressure_diastolic'),
                            "insulin_units": session['vitals_recorded'].get('insulin_units')
                        })
                
                logger.info(f"📈 Found {len(measurements_data)} measurements for patient")
                
                # Αρχεία
                file_texts = []
                if patient_data and 'uploaded_files' in patient_data:
                    files_with_text = [f for f in patient_data['uploaded_files'] if f.get('extracted_text')]
                    def get_safe_date(file_meta):
                        upload_date = file_meta.get('upload_date')
                        if isinstance(upload_date, datetime.datetime):
                            if upload_date.tzinfo is not None:
                                return upload_date.astimezone(datetime.timezone.utc)
                            return upload_date
                        elif isinstance(upload_date, str):
                            try:
                                parsed_date = datetime.datetime.fromisoformat(upload_date)
                                if parsed_date.tzinfo is not None:
                                    return parsed_date.astimezone(datetime.timezone.utc)
                                return parsed_date
                            except Exception as e:
                                logger.warning(f"Failed to parse date string '{upload_date}': {e}")
                        return datetime.datetime(1970, 1, 1)
                    files_with_text.sort(key=get_safe_date, reverse=True)
                    for file_meta in files_with_text:
                        extracted_text = file_meta.get('extracted_text', '')
                        file_texts.append({
                            "filename": file_meta['filename'],
                            "upload_date": file_meta['upload_date'].isoformat() if isinstance(file_meta.get('upload_date'), datetime.datetime) else str(file_meta.get('upload_date', 'N/A')),
                            "text": extracted_text
                        })

                # sessions: ήδη υπάρχουν (όλες οι συνεδρίες)
                # === Δημιουργία εμπλουτισμένου context string ===
                context = format_patient_context(patient_data, sessions_data, file_texts)
                     
            except Exception as context_err:
                 logger.error(f"❌ Error retrieving context for patient {patient_object_id}: {context_err}")
                 context = f"[Error retrieving context: {context_err}]\n"
        else:
            context = "Context: No specific patient context requested.\n"

        # === PubMed RAG VectorDB initialization ===
        evidence_text = ""
        pubmed_articles = []
        
        logger.info(f"🔍 PubMed RAG Status: {vector_db is not None}")
        
        if vector_db and user_query.strip():
            try:
                # Enhanced query for PubMed
                enhanced_query = user_query
                if patient_object_id:
                    patient_data = db.patients.find_one({"_id": patient_object_id})
                    if patient_data:
                        conditions = [c.get('condition_name', '') for c in patient_data.get('medical_profile', {}).get('conditions', [])]
                        if conditions:
                            enhanced_query = f"{user_query} {' '.join(conditions)} diabetes management"
                
                logger.info(f"📚 PubMed query: '{enhanced_query}'")
                articles = vector_db.retrieve_relevant_articles(enhanced_query, top_k=5)
                
                if articles:
                    logger.info(f"✅ Found {len(articles)} PubMed articles")
                    evidence_text = "\n\n=== 📚 EVIDENCE FROM RECENT PUBMED RESEARCH ===\n"
                    evidence_text += f"Search Query: '{enhanced_query}'\n"
                    evidence_text += f"Found {len(articles)} relevant studies:\n\n"
                    
                    for i, article in enumerate(articles, 1):
                        evidence_text += f"**STUDY {i}** (PMID: {article['pmid']})\n"
                        evidence_text += f"Title: {article['title']}\n"
                        abstract = article['abstract']
                        if len(abstract) > 300:
                            abstract = abstract[:300] + "..."
                        evidence_text += f"Abstract: {abstract}\n"
                        evidence_text += f"Relevance: {article.get('similarity', 0):.3f}\n\n"
                        
                        pubmed_articles.append({
                            'title': article['title'],
                            'pmid': article['pmid'],
                            'abstract': abstract,
                            'similarity': article.get('similarity', 0)
                        })
                    evidence_text += "=== END PUBMED EVIDENCE ===\n"
                else:
                    logger.warning(f"❌ No PubMed articles found for: '{enhanced_query}'")
                    evidence_text = "\n\n=== ⚠️ NO PUBMED EVIDENCE FOUND ===\n"
                    evidence_text += f"No relevant studies found for: '{enhanced_query}'\n"
                    
            except Exception as e:
                logger.error(f"❌ PubMed error: {e}")
                evidence_text = f"\n\n=== ❌ PUBMED ERROR ===\n{str(e)}\n"
        else:
            if not vector_db:
                logger.warning("⚠️ PubMed RAG not available")
                evidence_text = "\n\n=== ⚠️ PUBMED RAG SYSTEM NOT AVAILABLE ===\n"
            else:
                evidence_text = "\n\n=== ℹ️ NO PUBMED QUERY PROVIDED ===\n"

        context += evidence_text
        
        # === Genetics Analysis ===
        genetics_text = ""
        genetics_analysis = None
        
        if patient_object_id:
            try:
                logger.info(f"🧬 Starting genetics analysis for patient: {patient_object_id}")
                import asyncio
                
                genetics_query = f"{user_query} pharmacogenomics diabetes treatment"
                genetics_result = asyncio.run(
                    genetics_analyzer.answer_genetic_question(str(patient_object_id), genetics_query)
                )
                
                if genetics_result.get('status') == 'success':
                    genetics_analysis = genetics_result
                    genetics_text = f"\n\n=== 🧬 GENETICS/PHARMACOGENOMICS EVIDENCE ===\n"
                    genetics_text += f"Query: '{genetics_query}'\n"
                    genetics_text += f"{genetics_result.get('answer', '')}\n"
                    genetics_text += "=== END GENETICS EVIDENCE ===\n"
                    logger.info("✅ Genetics analysis completed successfully")
                elif genetics_result.get('status') == 'no_genetic_data':
                    genetics_text = f"\n\n=== ℹ️ NO GENETIC DATA AVAILABLE ===\n"
                    genetics_text += f"Message: {genetics_result.get('message', '')}\n"
                    logger.info("ℹ️ No genetic data found for this patient")
                else:
                    genetics_text = f"\n\n=== ⚠️ GENETICS ANALYSIS INCOMPLETE ===\n"
                    genetics_text += f"Status: {genetics_result.get('status')}\n"
                    logger.warning(f"⚠️ Genetics status: {genetics_result.get('status')}")
            except Exception as e:
                logger.error(f"❌ Genetics error: {e}", exc_info=True)
                genetics_text = f"\n\n=== ❌ GENETICS ERROR ===\n{str(e)}\n"
            
            context += genetics_text

        # === Create Enhanced Messages ===
        logger.info(f"📏 Total context length: {len(context)} characters")
        logger.info(f"🔍 PubMed evidence included: {'📚 EVIDENCE FROM RECENT PUBMED RESEARCH' in context}")
        logger.info(f"🔍 Genetics evidence included: {'🧬 GENETICS/PHARMACOGENOMICS EVIDENCE' in context}")

        # SIMPLIFIED System Prompt
        system_prompt = """You are a clinical decision support system for diabetes management.

🚨 MANDATORY CITATION RULES:
- When PubMed studies are provided (marked with PMID), you MUST cite them as (PMID: XXXXX, "Title")
- When genetics data is provided, you MUST reference it in your response
- Failure to cite available evidence = incomplete response

Provide evidence-based clinical advice with proper citations."""

        # Enhanced user message with forced citation requirement
        citation_requirement = ""
        if len(pubmed_articles) > 0:
            citation_requirement += f"\n\n🚨 MANDATORY CITATIONS REQUIRED:\n"
            for i, article in enumerate(pubmed_articles[:3], 1):
                citation_requirement += f"{i}. PMID: {article['pmid']} - {article['title'][:60]}...\n"
            citation_requirement += "\nYou MUST cite these PMIDs in your response using format (PMID: XXXXX, \"Title\")\n"
        
        if genetics_analysis:
            citation_requirement += f"\n🧬 GENETIC DATA: Include genetic findings in your clinical advice.\n"

        user_message = f"""{context}

🎯 **User Query**: {user_query}

{citation_requirement}

Provide an evidence-based clinical response with proper citations."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # === DeepSeek API Call ===
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Use recommended DeepSeek settings
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.6,  # DeepSeek recommendation
            "top_p": 0.95       # DeepSeek recommendation
        }

        logger.info(f"🚀 Sending request to DeepSeek API...")
        logger.info(f"🔧 Model: {payload['model']}, Temperature: {payload['temperature']}")
        
        # Retry logic
        last_error = None
        ai_response = None
        for attempt in range(DEEPSEEK_MAX_RETRIES):
            try:
                response = requests.post(
                    DEEPSEEK_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=DEEPSEEK_API_TIMEOUT
                )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', DEEPSEEK_RETRY_DELAY * (attempt + 1)))
                    logger.warning(f"Rate limited - retrying after {retry_after}s (attempt {attempt + 1}/{DEEPSEEK_MAX_RETRIES})")
                    time.sleep(retry_after)
                    continue
                elif response.status_code >= 500:
                    logger.warning(f"Server error - retrying (attempt {attempt + 1}/{DEEPSEEK_MAX_RETRIES})")
                    time.sleep(DEEPSEEK_RETRY_DELAY * (attempt + 1))
                    continue
                    
                response.raise_for_status()
                
                response_data = response.json()
                logger.info("✅ Received response from DeepSeek API")
                
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    ai_message = response_data['choices'][0].get('message', {}).get('content', '')
                    ai_response = ai_message.strip()[:8000]
                    
                    # Quality Check
                    citation_count = ai_response.count('PMID:')
                    genetics_mentions = sum(1 for word in ['genetic', 'pharmacogen', 'pgs'] if word in ai_response.lower())
                    
                    logger.info(f"📊 Response quality - PMID citations: {citation_count}, Genetics mentions: {genetics_mentions}")
                    
                    # Add warnings if evidence not cited
                    quality_warnings = ""
                    if len(pubmed_articles) > 0 and citation_count == 0:
                        logger.warning("⚠️ Response lacks PubMed citations despite available evidence")
                        quality_warnings += f"\n\n⚠️ **Technical Note**: {len(pubmed_articles)} relevant PubMed studies were available but not cited."
                        
                    if genetics_analysis and genetics_mentions == 0:
                        logger.warning("⚠️ Response lacks genetics integration despite available data")
                        quality_warnings += f"\n\n⚠️ **Technical Note**: Genetic/pharmacogenomic data was available but not integrated."
                    
                    ai_response += quality_warnings
                    
                else:
                    ai_response = "AI model did not return a valid response structure."
                    logger.error(f"Unexpected DeepSeek API response format: {response_data}")
                
                break

            except requests.exceptions.RequestException as req_err:
                last_error = req_err
                if attempt < DEEPSEEK_MAX_RETRIES - 1:
                    delay = DEEPSEEK_RETRY_DELAY * (attempt + 1)
                    logger.warning(f"API call failed (attempt {attempt + 1}/{DEEPSEEK_MAX_RETRIES}): {req_err} - retrying in {delay}s")
                    time.sleep(delay)
                    continue
                logger.error(f"Final API call failed after {DEEPSEEK_MAX_RETRIES} attempts: {req_err}")
                return jsonify({
                    "error": "AI service unavailable",
                    "details": str(req_err),
                    "retries": attempt + 1
                }), 504
            except Exception as api_err:
                logger.error(f"Error processing API response: {api_err}")
                return jsonify({
                    "error": "AI response processing failed",
                    "details": str(api_err)
                }), 500

        # Generate recommendations
        recommendations = []
        risk_assessment = {}
        if patient_object_id:
            try:
                patient_data = db.patients.find_one({"_id": patient_object_id})
                if patient_data:
                    engine = DecisionEngine({
                        **patient_data.get('personal_details', {}),
                        **patient_data.get('medical_profile', {}),
                        'measurements': measurements_data
                    })
                    recommendations = engine.generate_recommendations()
                    risk_assessment = engine.assess_risk()
            except Exception as e:
                logger.error(f"Decision engine error: {e}")

        # Enhanced response payload
        response_payload = {
            "id": f"ai-response-{datetime.datetime.now().timestamp()}",
            "response": ai_response,
            "recommendations": recommendations,
            "risk_assessment": risk_assessment,
            "pubmed_evidence": pubmed_articles,
            "genetics_analysis": genetics_analysis,
            "context": {
                "has_patient_data": bool(patient_object_id),
                "has_recommendations": len(recommendations) > 0,
                "has_pubmed_evidence": len(pubmed_articles) > 0,
                "has_genetics_analysis": genetics_analysis is not None
            },
            "debug_info": {
                "user_query": user_query,
                "context_length": len(context),
                "pubmed_articles_found": len(pubmed_articles),
                "genetics_status": "available" if genetics_analysis else "not_available",
                "citations_found": ai_response.count('PMID:') if ai_response else 0,
                "model_used": payload["model"],
                "temperature_used": payload["temperature"]
            }
        }
        
        logger.info(f"✅ Query completed successfully - Citations: {response_payload['debug_info']['citations_found']}")
        return jsonify(response_payload), 200

    except Exception as e:
        logger.error(f"❌ Error in AI query: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500


@ai_bp.route('/analysis', methods=['OPTIONS'])
def ai_analysis_options():
    """Handle OPTIONS requests for CORS preflight"""
    response = jsonify({"message": "OK"})
    return response

@ai_bp.route('/analysis', methods=['POST'])
@jwt_required()
def ai_analysis():
    """Enhanced endpoint για προχωρημένη ανάλυση δεδομένων και μετρήσεων ασθενούς με AI"""
    requesting_user_id_str = get_jwt_identity()
    
    logger.info("🚀 Enhanced AI Analysis endpoint called")
    
    if not DEEPSEEK_API_KEY or not DEEPSEEK_API_URL:
        error_msg = "AI service is not configured: "
        if not DEEPSEEK_API_KEY:
            error_msg += "API key missing. "
        if not DEEPSEEK_API_URL:
            error_msg += "API URL missing."
        return jsonify({"error": error_msg.strip()}), 503

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        if not data or 'patient_id' not in data:
            return jsonify({"error": "Request body must be JSON and contain 'patient_id' field"}), 400
        
        patient_id = data.get('patient_id')
        logger.info(f"🔍 Enhanced analysis requested for patient: {patient_id}")
        
        try:
            patient_object_id = ObjectId(patient_id)
            view_permission = ViewPatientPermission(patient_id)
            if not view_permission.can():
                return permission_denied("Δεν έχετε δικαίωμα πρόσβασης στα δεδομένα αυτού του ασθενή")
        except InvalidId:
             return jsonify({"error": "Invalid patient ID format provided"}), 400
        
        # Συλλογή δεδομένων ασθενή
        sessions = list(db.sessions.find({"patient_id": patient_object_id}).sort("timestamp", -1))
        logger.info(f"📊 Found {len(sessions)} total sessions for patient")
        
        if not sessions:
            return jsonify({
                "id": f"ai-analysis-{datetime.datetime.now().timestamp()}",
                "analysis": "Δεν βρέθηκαν συνεδρίες για ανάλυση των δεδομένων του ασθενή."
            }), 200
        
        # Επεξεργασία μετρήσεων
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
        
        logger.info(f"📈 Found {len(measurements_data)} measurements for analysis")
        
        if not measurements_data:
            return jsonify({
                "id": f"ai-analysis-{datetime.datetime.now().timestamp()}",
                "analysis": "Δεν βρέθηκαν επαρκή δεδομένα μετρήσεων για ανάλυση."
            }), 200
            
        # Φέρνουμε τα βασικά στοιχεία του ασθενή
        patient_data = db.patients.find_one({"_id": patient_object_id})
        if not patient_data:
            return jsonify({"error": "Patient not found"}), 404
        
        pd = patient_data.get('personal_details', {})
        mp = patient_data.get('medical_profile', {})
        
        # === ΔΙΟΡΘΩΣΗ: Συλλογή αρχείων όπως στο /query endpoint ===
        file_texts = []
        if patient_data and 'uploaded_files' in patient_data:
            files_with_text = [f for f in patient_data['uploaded_files'] if f.get('extracted_text')]
            
            def get_safe_date(file_meta):
                upload_date = file_meta.get('upload_date')
                if isinstance(upload_date, datetime.datetime):
                    if upload_date.tzinfo is not None:
                        return upload_date.astimezone(datetime.timezone.utc)
                    return upload_date
                elif isinstance(upload_date, str):
                    try:
                        parsed_date = datetime.datetime.fromisoformat(upload_date)
                        if parsed_date.tzinfo is not None:
                            return parsed_date.astimezone(datetime.timezone.utc)
                        return parsed_date
                    except Exception as e:
                        logger.warning(f"Failed to parse date string '{upload_date}': {e}")
                return datetime.datetime(1970, 1, 1)
                
            files_with_text.sort(key=get_safe_date, reverse=True)
            for file_meta in files_with_text:
                extracted_text = file_meta.get('extracted_text', '')
                file_texts.append({
                    "filename": file_meta['filename'],
                    "upload_date": file_meta['upload_date'].isoformat() if isinstance(file_meta.get('upload_date'), datetime.datetime) else str(file_meta.get('upload_date', 'N/A')),
                    "text": extracted_text
                })
        
        logger.info(f"📄 Found {len(file_texts)} files with extracted text for analysis")
        
        # === Enhanced PubMed Evidence Retrieval ===
        patient_conditions = [c.get('condition_name', '') for c in mp.get('conditions', [])]
        
        # Convert Greek conditions to English for PubMed search
        def translate_condition_to_english(condition):
            """Convert Greek diabetes terms to English for PubMed search"""
            greek_to_english = {
                'διαβητης': 'diabetes',
                'διαβήτης': 'diabetes', 
                'τ1': 'type 1',
                'τ2': 'type 2',
                'type1': 'type 1',
                'type2': 'type 2',
                'σακχαρωδης': 'diabetes mellitus',
                'σακχαρώδης': 'diabetes mellitus',
                'υπερταση': 'hypertension',
                'υπέρταση': 'hypertension',
                'παχυσαρκια': 'obesity',
                'παχυσαρκία': 'obesity',
                'δυσλιπιδαιμια': 'dyslipidemia',
                'δυσλιπιδαιμία': 'dyslipidemia'
            }
            
            if not condition:
                return ""
                
            condition_lower = condition.lower().strip()
            for greek, english in greek_to_english.items():
                condition_lower = condition_lower.replace(greek, english)
            
            return condition_lower

        # Convert conditions to English
        english_conditions = []
        for condition in patient_conditions:
            english_condition = translate_condition_to_english(condition)
            if english_condition and english_condition not in english_conditions:
                english_conditions.append(english_condition)

        # Create multiple English-only queries to try
        queries_to_try = []
        
        if english_conditions:
            # Query with patient-specific conditions
            queries_to_try.extend([
                f"diabetes management {' '.join(english_conditions)} HbA1c glucose monitoring",
                f"{' '.join(english_conditions)} clinical management guidelines",
                f"diabetes {' '.join(english_conditions)} treatment recommendations"
            ])
        
        # Add general diabetes queries
        queries_to_try.extend([
            "diabetes mellitus management HbA1c monitoring",
            "type 1 diabetes clinical guidelines",
            "diabetes glucose monitoring recommendations",
            "HbA1c diabetes management",
            "diabetes treatment clinical practice guidelines"
        ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for query in queries_to_try:
            if query not in seen:
                seen.add(query)
                unique_queries.append(query)
        
        queries_to_try = unique_queries[:5]  # Limit to 5 queries max
        
        pubmed_evidence_text = ""
        pubmed_articles = []
        pubmed_citations = []  # For Enhanced DecisionEngine
        
        logger.info(f"🔍 PubMed RAG Status: {vector_db is not None}")
        
        if vector_db:
            articles_found = False
            
            for i, query in enumerate(queries_to_try):
                try:
                    logger.info(f"📚 PubMed query attempt {i+1}: '{query}'")
                    articles = vector_db.retrieve_relevant_articles(query, top_k=5)
                    
                    if articles:
                        logger.info(f"✅ Found {len(articles)} PubMed articles with query {i+1}")
                        pubmed_evidence_text = "\n\n=== 📚 EVIDENCE FROM RECENT PUBMED RESEARCH ===\n"
                        pubmed_evidence_text += f"Search Query: '{query}'\n"
                        pubmed_evidence_text += f"Found {len(articles)} relevant studies:\n\n"
                        
                        for j, article in enumerate(articles, 1):
                            pubmed_evidence_text += f"**STUDY {j}** (PMID: {article['pmid']})\n"
                            pubmed_evidence_text += f"Title: {article['title']}\n"
                            abstract = article['abstract']
                            if len(abstract) > 300:
                                abstract = abstract[:300] + "..."
                            pubmed_evidence_text += f"Abstract: {abstract}\n"
                            pubmed_evidence_text += f"Relevance: {article.get('similarity', 0):.3f}\n\n"
                            
                            pubmed_articles.append({
                                'title': article['title'],
                                'pmid': article['pmid'],
                                'abstract': abstract,
                                'similarity': article.get('similarity', 0)
                            })
                            
                            # Extract PMIDs for Enhanced DecisionEngine
                            pubmed_citations.append(f"PMID:{article['pmid']}")
                            
                        pubmed_evidence_text += "=== END PUBMED EVIDENCE ===\n"
                        articles_found = True
                        break  # Stop trying more queries if we found articles
                        
                except Exception as e:
                    logger.error(f"❌ PubMed error with query {i+1} '{query}': {e}")
                    continue
            
            if not articles_found:
                logger.warning(f"❌ No PubMed articles found with any of {len(queries_to_try)} English queries")
                pubmed_evidence_text = "\n\n=== ⚠️ NO PUBMED EVIDENCE FOUND ===\n"
                pubmed_evidence_text += f"Attempted {len(queries_to_try)} different search queries:\n"
                for i, query in enumerate(queries_to_try, 1):
                    pubmed_evidence_text += f"  {i}. '{query}'\n"
                pubmed_evidence_text += "\nPossible reasons:\n"
                pubmed_evidence_text += "- PubMed API connectivity issues\n"
                pubmed_evidence_text += "- Index requires rebuilding\n"
                pubmed_evidence_text += "- No articles match current search criteria\n"
                
        else:
            logger.warning("⚠️ PubMed RAG not available for analysis")
            pubmed_evidence_text = "\n\n=== ⚠️ PUBMED RAG SYSTEM NOT AVAILABLE ===\n"
            pubmed_evidence_text += "PubMed vector database not initialized. Check PUBMED_API_KEY configuration.\n"

        # === Enhanced Genetics Analysis ===
        genetics_text = ""
        genetics_analysis = None
        
        try:
            logger.info(f"🧬 Starting genetics analysis for patient: {patient_object_id}")
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            genetics_result = loop.run_until_complete(
                genetics_analyzer.answer_genetic_question(str(patient_object_id), "diabetes management pharmacogenomics")
            )
            loop.close()
            
            if genetics_result.get('status') == 'success':
                genetics_analysis = genetics_result
                genetics_text = f"\n\n=== 🧬 GENETICS/PHARMACOGENOMICS EVIDENCE ===\n"
                genetics_text += f"Genetic Analysis Results:\n"
                genetics_text += f"{genetics_result.get('answer', '')}\n"
                genetics_text += "=== END GENETICS EVIDENCE ===\n"
                logger.info("✅ Genetics analysis completed for analysis endpoint")
            elif genetics_result.get('status') == 'no_genetic_data':
                genetics_text = f"\n\n=== ℹ️ NO GENETIC DATA AVAILABLE ===\n"
                genetics_text += f"Status: {genetics_result.get('message', 'No genetic data found for this patient')}\n"
                genetics_text += "Recommendation: Consider genetic testing for personalized diabetes management.\n"
                genetics_text += "Relevant tests may include:\n"
                genetics_text += "- Pharmacogenomic panels (CYP2D6, CYP2C19, SLCO1B1)\n"
                genetics_text += "- Diabetes risk variants (TCF7L2, PPARG, KCNJ11)\n"
                genetics_text += "- Polygenic risk scores for diabetes complications\n"
                genetics_text += "=== END GENETICS SECTION ===\n"
                logger.info("ℹ️ No genetic data found for analysis")
            else:
                genetics_text = f"\n\n=== ⚠️ GENETICS ANALYSIS INCOMPLETE ===\n"
                genetics_text += f"Status: {genetics_result.get('status')}\n"
                genetics_text += f"Details: {genetics_result.get('message', 'Unknown error in genetics analysis')}\n"
                genetics_text += "=== END GENETICS SECTION ===\n"
                logger.warning(f"⚠️ Genetics status for analysis: {genetics_result.get('status')}")
        except Exception as e:
            logger.error(f"❌ Genetics error in analysis: {e}", exc_info=True)
            genetics_text = f"\n\n=== ❌ GENETICS ERROR ===\n"
            genetics_text += f"Error during genetic analysis: {str(e)}\n"
            genetics_text += "Genetic recommendations cannot be provided at this time.\n"
            genetics_text += "=== END GENETICS SECTION ===\n"

        # === ΔΙΟΡΘΩΣΗ: Δημιουργία πλήρους context που περιλαμβάνει αρχεία ===
        patient_context = format_patient_context(patient_data, sessions[:5], file_texts)  # Limit sessions to latest 5
        
        # === Δημιουργία εμπλουτισμένου analysis_prompt ===
        # SIMPLIFIED System Prompt for Analysis
        system_prompt = """You are an advanced diabetes clinical decision support system.

🚨 FORMATTING REQUIREMENTS:
- Do NOT use mermaid diagrams, code blocks, or ```mermaid syntax
- Use clear section headers with **bold text**
- Use numbered lists and bullet points for organization
- Provide structured, readable clinical analysis
- Format action plans as clear numbered steps

🚨 MANDATORY EVIDENCE INTEGRATION:
- ALWAYS cite PubMed studies when provided (format: PMID: XXXXX, \"Title\")
- ALWAYS integrate genetics/pharmacogenomics data when available
- ALWAYS reference relevant information from uploaded documents/files
- Provide evidence-based clinical analysis with proper citations
- If no evidence is provided, clearly state the limitation

Focus on trend analysis, risk assessment, and actionable recommendations."""

        # Enhanced analysis prompt with forced citations
        citation_requirement = ""
        if len(pubmed_articles) > 0:
            citation_requirement += f"\n\n🚨 MANDATORY CITATIONS - YOU MUST CITE THESE STUDIES:\n"
            for i, article in enumerate(pubmed_articles[:3], 1):
                citation_requirement += f"{i}. PMID: {article['pmid']} - {article['title'][:60]}...\n"
            citation_requirement += "\nUse citation format: (PMID: XXXXX, \"Title\")\n"
        else:
            citation_requirement += f"\n\n📋 NOTE: No PubMed evidence was available for this analysis.\n"
            citation_requirement += "Base recommendations on clinical guidelines and best practices.\n"
        
        if genetics_analysis:
            citation_requirement += f"\n🧬 GENETIC DATA AVAILABLE: Integrate genetic findings into your analysis.\n"
        elif "NO GENETIC DATA AVAILABLE" in genetics_text:
            citation_requirement += f"\n🧬 NO GENETIC DATA: Note lack of genetic information in recommendations.\n"
        
        if len(file_texts) > 0:
            citation_requirement += f"\n📄 UPLOADED DOCUMENTS: {len(file_texts)} files with extracted text available. Reference relevant clinical information from these documents.\n"

        analysis_prompt = f"""
{patient_context}

{pubmed_evidence_text}

{genetics_text}

ADDITIONAL MEASUREMENTS DATA:
{format_measurements_table(measurements_data)}

{citation_requirement}

ANALYSIS REQUEST:
===============
Provide comprehensive diabetes management analysis including:

**1. CLINICAL ASSESSMENT**
- Current status summary
- Key trends and patterns from ALL available data (sessions, files, measurements)
- Concerning findings

**2. EVIDENCE-BASED RECOMMENDATIONS**
- Immediate actions needed
- Long-term management plan
- Cite PubMed studies if available
- Consider information from uploaded documents

**3. ACTION PLAN**
Instead of mermaid diagrams, format as:
- **Current Status**: [HbA1c, weight, key metrics]
- **Priority Actions**: 
  1. [First action with timeline]
  2. [Second action with timeline]
  3. [Third action with timeline]
- **Target Goals**: [Specific, measurable targets]
- **Monitoring Schedule**: [When to reassess]

**4. GENETIC/PHARMACOGENOMIC CONSIDERATIONS**
- Integrate genetic findings if available
- Personalization recommendations

**5. DOCUMENT INTEGRATION**
- Reference relevant information from uploaded files
- Integrate laboratory results, reports, or other clinical documents

CRITICAL REQUIREMENTS:
- NO mermaid diagrams or code blocks
- Use structured text with clear headers
- If PubMed studies are provided, you MUST cite them using PMID format
- If genetic data is available, you MUST integrate it into recommendations
- If uploaded documents contain relevant clinical information, reference them
- If evidence is limited, acknowledge this limitation
- Keep recommendations specific and actionable
"""

        logger.info(f"📏 Enhanced analysis prompt length: {len(analysis_prompt)} characters")
        logger.info(f"📄 Patient context includes {len(file_texts)} files")
        logger.info(f"🔍 PubMed evidence in prompt: {'📚 EVIDENCE FROM RECENT PUBMED RESEARCH' in analysis_prompt}")
        logger.info(f"🔍 Genetics evidence in prompt: {'🧬 GENETICS/PHARMACOGENOMICS EVIDENCE' in analysis_prompt}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": analysis_prompt}
        ]

        # === DeepSeek API Call with Optimized Settings ===
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": 4000,
            "temperature": 0.6,  # DeepSeek recommendation
            "top_p": 0.95       # DeepSeek recommendation
        }

        logger.info(f"🚀 Sending analysis request to DeepSeek API...")
        logger.info(f"🔧 Model: {payload['model']}, Temperature: {payload['temperature']}, Max tokens: {payload['max_tokens']}")
        
        try:
            response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            
            response_data = response.json()
            logger.info("✅ Received analysis response from DeepSeek API")
            
            if 'choices' in response_data and len(response_data['choices']) > 0:
                ai_message = response_data['choices'][0].get('message', {}).get('content', '')
                ai_analysis = ai_message.strip()
                
                # Quality Check
                citation_count = ai_analysis.count('PMID:')
                genetics_mentions = sum(1 for word in ['genetic', 'pharmacogen', 'pgs'] if word in ai_analysis.lower())
                
                logger.info(f"📊 Analysis quality - PMID citations: {citation_count}, Genetics mentions: {genetics_mentions}")
                
                # Add warnings if evidence not used properly
                quality_warnings = ""
                if len(pubmed_articles) > 0 and citation_count == 0:
                    logger.warning("⚠️ Analysis lacks PubMed citations despite available evidence")
                    quality_warnings += f"\n\n⚠️ **Technical Note**: {len(pubmed_articles)} relevant PubMed studies were available but not cited in this analysis."
                    
                if genetics_analysis and genetics_mentions == 0:
                    logger.warning("⚠️ Analysis lacks genetics integration despite available data")
                    quality_warnings += f"\n\n⚠️ **Technical Note**: Genetic/pharmacogenomic data was available but not integrated into this analysis."
                
                # Only add warnings if there are actual issues
                if quality_warnings:
                    ai_analysis += quality_warnings
                
            else:
                ai_analysis = "AI model did not return a valid response structure for the analysis."
                logger.error(f"Unexpected DeepSeek API response format in analysis: {response_data}")

        except requests.exceptions.RequestException as req_err:
            logger.error(f"❌ Error calling DeepSeek API for analysis: {req_err}")
            return jsonify({"error": f"Failed to communicate with AI service: {req_err}"}), 504
        except Exception as api_err:
             logger.error(f"❌ Error processing DeepSeek API analysis response: {api_err}")
             return jsonify({"error": f"Error processing AI analysis: {api_err}"}), 500

        # === ENHANCED DECISION ENGINE INTEGRATION ===
        recommendations = []
        risk_assessment = {}
        
        try:
            logger.info("🚀 Initializing Enhanced Decision Engine with evidence...")
            
            # Prepare comprehensive patient data for enhanced engine
            comprehensive_patient_data = {
                **patient_data.get('personal_details', {}),
                **patient_data.get('medical_profile', {}),
                'measurements': measurements_data
            }
            
            # Add latest measurements to patient data for better risk assessment
            if measurements_data:
                latest_measurement = measurements_data[-1]
                comprehensive_patient_data.update({
                    'hba1c': latest_measurement.get('hba1c'),
                    'bmi': latest_measurement.get('bmi'),
                    'systolic_bp': latest_measurement.get('blood_pressure_systolic'),
                    'diastolic_bp': latest_measurement.get('blood_pressure_diastolic'),
                    'glucose_level': latest_measurement.get('blood_glucose_level')
                })
            
            logger.info(f"📊 Enhanced engine data: {len(pubmed_citations)} PMIDs, genetics: {genetics_analysis is not None}")
            
            # Import and create enhanced decision engine
            from services.decision_engine import create_enhanced_decision_engine
            
            enhanced_engine = create_enhanced_decision_engine(
                patient_data=comprehensive_patient_data,
                pubmed_citations=pubmed_citations,
                genetic_analysis=genetics_analysis
            )
            
            # Generate evidence-based recommendations
            recommendations = enhanced_engine.generate_evidence_based_recommendations()
            logger.info(f"✅ Enhanced engine generated {len(recommendations)} evidence-based recommendations")
            
            # Generate comprehensive risk assessment
            risk_assessment = enhanced_engine.assess_comprehensive_risk()
            logger.info(f"✅ Enhanced risk assessment: {risk_assessment['level']} ({risk_assessment['total_score']:.1f}%)")
            
        except Exception as e:
            logger.error(f"❌ Enhanced Decision Engine failed: {e}", exc_info=True)
            
            # Fallback to basic decision engine if enhanced version fails
            try:
                logger.warning("🔄 Falling back to basic Decision Engine...")
                from services.decision_engine import DecisionEngine
                
                basic_engine = DecisionEngine(patient_data)
                recommendations = basic_engine.generate_recommendations()
                risk_assessment = basic_engine.assess_risk()
                
                logger.info(f"✅ Fallback engine generated {len(recommendations)} basic recommendations")
                
            except Exception as fallback_error:
                logger.error(f"❌ Even fallback Decision Engine failed: {fallback_error}")
                recommendations = [{
                    'id': 'fallback_1',
                    'type': 'monitoring',
                    'priority': 1,
                    'action': 'Schedule regular follow-up with healthcare provider',
                    'rationale': 'Automated recommendation generation currently unavailable',
                    'evidence': [],
                    'clinical_impact': 50,
                    'urgency': 50
                }]
                risk_assessment = {'score': 50, 'level': 'moderate'}

        # Enhanced response with comprehensive debugging info
        response_payload = {
            "id": f"ai-analysis-{datetime.datetime.now().timestamp()}",
            "analysis": ai_analysis,
            "recommendations": recommendations,
            "risk_assessment": risk_assessment,
            "pubmed_evidence": pubmed_articles,
            "genetics_analysis": genetics_analysis,
            "debug_info": {
                "patient_id": patient_id,
                "measurements_count": len(measurements_data),
                "files_with_text_count": len(file_texts),  # ΠΡΟΣΘΗΚΗ
                "pubmed_articles_found": len(pubmed_articles),
                "pubmed_citations_count": len(pubmed_citations),
                "genetics_status": "available" if genetics_analysis else "not_available",
                "context_length": len(analysis_prompt),
                "citations_found": ai_analysis.count('PMID:') if ai_analysis else 0,
                "genetics_mentions": sum(1 for word in ['genetic', 'pharmacogen'] if word in ai_analysis.lower()) if ai_analysis else 0,
                "model_used": payload["model"],
                "temperature_used": payload["temperature"],
                "queries_attempted": len(queries_to_try),
                "successful_query": queries_to_try[0] if pubmed_articles else None,
                "patient_conditions_original": patient_conditions,
                "patient_conditions_english": english_conditions,
                "enhanced_engine_status": "success" if len(recommendations) > 1 else "fallback",
                "risk_assessment_source": "enhanced" if 'total_score' in risk_assessment else "basic",
                "recommendations_have_evidence": any('evidence' in rec and rec['evidence'] for rec in recommendations),
                "files_included": [f["filename"] for f in file_texts]  # ΠΡΟΣΘΗΚΗ
            }
        }
        
        logger.info(f"✅ Enhanced analysis completed successfully!")
        logger.info(f"📊 Final metrics: Citations: {response_payload['debug_info']['citations_found']}, Genetics: {response_payload['debug_info']['genetics_mentions']}, Recommendations: {len(recommendations)}, Files: {len(file_texts)}")
        
        return jsonify(response_payload), 200

    except Exception as e:
        logger.error(f"❌ Error in Enhanced AI analysis: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred during analysis"}), 500
    
def calculate_age(date_of_birth_str):
    """Υπολογίζει την ηλικία από την ημερομηνία γέννησης"""
    if not date_of_birth_str:
        return "N/A"
        
    try:
        # Προσπαθούμε να διαχειριστούμε διάφορες πιθανές μορφές ημερομηνίας
        if isinstance(date_of_birth_str, datetime.datetime):
            date_of_birth = date_of_birth_str
        else:
            # Υποθέτουμε ISO format ή κάποιο άλλο συνηθισμένο format
            date_of_birth = datetime.datetime.fromisoformat(date_of_birth_str.replace('Z', '+00:00'))
            
        today = datetime.datetime.now(datetime.timezone.utc)
        age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        return f"{age} years"
    except Exception as e:
        logger.warning(f"Failed to calculate age from '{date_of_birth_str}': {e}")
        return "Unable to calculate"


def format_measurements_table(measurements):
    """Μορφοποιεί τις μετρήσεις σε πίνακα για το prompt"""
    if not measurements:
        return "No measurements available."
        
    formatted_data = "| Date | Weight | BMI | Blood Glucose | HbA1c | Blood Pressure | Insulin Units |\n"
    formatted_data += "|------|--------|-----|--------------|-------|----------------|---------------|\n"
    
    for m in measurements:
        date = m['date'][:10] if m['date'] else 'N/A'  # Παίρνουμε μόνο το date part του ISO
        weight = f"{m['weight_kg']} kg" if m['weight_kg'] else 'N/A'
        bmi = str(m['bmi']) if m['bmi'] else 'N/A'
        
        glucose_type = ''
        if m['blood_glucose_type'] and m['blood_glucose_type'] != 'undefined':
            glucose_type = f" ({m['blood_glucose_type']})"
        glucose = f"{m['blood_glucose_level']} mg/dL{glucose_type}" if m['blood_glucose_level'] else 'N/A'
        
        hba1c = f"{m['hba1c']}%" if m['hba1c'] else 'N/A'
        
        bp_sys = m['blood_pressure_systolic']
        bp_dia = m['blood_pressure_diastolic']
        blood_pressure = f"{bp_sys}/{bp_dia} mmHg" if bp_sys and bp_dia else 'N/A'
        
        insulin = str(m['insulin_units']) if m['insulin_units'] else 'N/A'
        
        formatted_data += f"| {date} | {weight} | {bmi} | {glucose} | {hba1c} | {blood_pressure} | {insulin} |\n"
    
    return formatted_data

def format_patient_context(patient_data, sessions_data, file_texts):
    """
    Δημιουργεί εμπλουτισμένο context για το AI με πληροφορίες ασθενή,
    συνεδρίες και αρχεία με OCR.
    """
    logger.info(f"📝 Formatting context with {len(file_texts)} file_texts entries")
    for i, file_info in enumerate(file_texts):
        text_preview = file_info.get('text', '')[:50] + "..." if len(file_info.get('text', '')) > 50 else file_info.get('text', '')
        logger.info(f"📄 File {i+1}: {file_info.get('filename', 'unknown')}, Text preview: {text_preview}")
    
    context_str = """Patient Context:
===================

"""
    
    # Βασικά Στοιχεία Ασθενή
    if patient_data:
        context_str += "**Patient Information:**\n"
        pd = patient_data.get('personal_details', {})
        mp = patient_data.get('medical_profile', {})
        context_str += f"- Name: {pd.get('first_name', '')} {pd.get('last_name', '')}\n"
        context_str += f"- AMKA: {pd.get('amka', 'N/A')}\n"
        context_str += f"- Date of Birth: {pd.get('date_of_birth', 'N/A')}\n"
        context_str += f"- Height (cm): {mp.get('height_cm', 'N/A')}\n"
        context_str += "- Conditions: " + (", ".join([c.get('condition_name', 'N/A') for c in mp.get('conditions', [])]) or "None listed") + "\n"
        context_str += "- Allergies: " + (", ".join(mp.get('allergies', [])) or "None listed") + "\n"
        context_str += f"- History Summary: {mp.get('medical_history_summary', 'N/A')}\n\n"

    # Τελευταίες Συνεδρίες
    if sessions_data:
        context_str += "**Recent Sessions (Latest First):**\n"
        for i, session in enumerate(sessions_data):
            context_str += f"* Session {i+1} (Timestamp: {session.get('timestamp', 'N/A')} , Type: {session.get('session_type', 'N/A')}):\n"
            context_str += f"    - Doctor Notes: {session.get('doctor_notes', 'N/A')}\n"
            context_str += f"    - Therapy Adjustments: {session.get('therapy_adjustments', 'N/A')}\n"
            context_str += f"    - Patient Reported: {session.get('patient_reported_outcome', 'N/A')}\n"
            if 'vitals_recorded' in session and session['vitals_recorded']:
                 # Καλύτερη μορφοποίηση για vitals
                 vitals_str = ", ".join([f'{k}: {v}' for k, v in session['vitals_recorded'].items()])
                 context_str += f"    - Vitals Recorded: {vitals_str}\n"
        context_str += "\n"
        
    # Κείμενο από Αρχεία
    if file_texts:
        context_str += "**Extracted Text from Files (Latest First):**\n"
        for i, file_info in enumerate(file_texts):
             context_str += f"\n--- File {i+1}: {file_info['filename']} (Uploaded: {file_info['upload_date']}) ---\n"
             full_file_text = file_info['text']
             context_str += f"{full_file_text}\n--- End of File {i+1} ---"

    context_str += "\n===================\n"
    
    logger.info(f"📏 Context formatted - total length: {len(context_str)} characters")
    return context_str