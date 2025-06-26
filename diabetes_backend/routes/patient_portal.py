from flask import Blueprint, jsonify, request, current_app, send_from_directory
# Removed local: from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId
from bson.errors import InvalidId
import datetime
import logging
from utils.db import get_db
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename
import os
import mimetypes
from utils.file_utils import extract_text_from_pdf
from config.config import UPLOAD_FOLDER

# Ρύθμιση logger
logger = logging.getLogger(__name__)

# Δημιουργία blueprint
patient_portal_bp = Blueprint('patient_portal', __name__, url_prefix='/api/patient-portal')

# Η σύνδεση στη βάση δεδομένων
# Removed local: bcrypt = Bcrypt()
db = get_db()

@patient_portal_bp.route('/register', methods=['POST'])
def register_patient():
    """Endpoint για την εγγραφή νέου ασθενή από το PWA."""
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # --- Απαραίτητα πεδία ---
        required_fields = ['first_name', 'last_name', 'amka', 'date_of_birth', 'email', 'phone', 'password', 'doctor_id']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # --- Έλεγχος Έγκυρου Γιατρού ---
        try:
            selected_doctor_id = ObjectId(data['doctor_id'])
            # Έλεγχος αν ο γιατρός υπάρχει και είναι διαθέσιμος
            doctor = db.doctors.find_one({
                "_id": selected_doctor_id,
                "availability_status": "available" 
            })
            if not doctor:
                 return jsonify({"error": "Selected doctor is invalid or not available"}), 400
        except InvalidId:
            return jsonify({"error": "Invalid doctor ID format"}), 400
            
        # --- Έλεγχος Μοναδικότητας ΑΜΚΑ ---
        amka = data['amka']
        existing_patient_amka = db.patients.find_one({"personal_details.amka": amka})
        if existing_patient_amka:
            return jsonify({"error": f"A patient with AMKA '{amka}' already exists"}), 409
            
        # --- Έλεγχος Μοναδικότητας Email ---
        email = data['email']
        existing_patient_email = db.patients.find_one({"personal_details.contact.email": email})
        if existing_patient_email:
             return jsonify({"error": f"A patient with email '{email}' already exists"}), 409
             
        # --- Hashing Κωδικού ---
        password = data['password']
        if len(password) < 8: # Απλός έλεγχος μήκους
             return jsonify({"error": "Password must be at least 8 characters long"}), 400
        # Χρήση του bcrypt της εφαρμογής
        app_bcrypt = current_app.bcrypt if hasattr(current_app, 'bcrypt') else current_app.extensions.get('bcrypt')
        if not app_bcrypt:
            logger.error("Bcrypt not available on app context in patient_portal.py (register_patient)")
            return jsonify({"error": "Internal server error - auth misconfiguration"}), 500
        password_hash = app_bcrypt.generate_password_hash(password).decode('utf-8')

        # --- Προετοιμασία Εγγράφου Ασθενή ---
        now = datetime.datetime.now(datetime.timezone.utc)
        patient_data = {
            "personal_details": {
                "first_name": data['first_name'],
                "last_name": data['last_name'],
                "amka": amka,
                "date_of_birth": data['date_of_birth'], # Πρέπει να είναι σε ISO format από το frontend
                "gender": data.get('gender'), # Προαιρετικό
                "contact": {
                    "email": email,
                    "phone": data['phone'],
                    "address": data.get('address') # Προαιρετικό
                }
            },
            "account_details": {
                 "password_hash": password_hash 
            },
            "medical_history": {}, # Αρχικά κενό
            "risk_factors": {},    # Αρχικά κενό
            "uploaded_files": [], # Αρχικά κενό
            "sessions": [],       # Αρχικά κενό
            "assigned_doctors": [selected_doctor_id], # Ο γιατρός που επιλέχθηκε
            "is_in_common_space": False, # Default
            "created_at": now,
            "last_updated_at": now,
            "last_consultation_date": None
        }
        
        # --- Εισαγωγή Ασθενή στη Βάση ---
        result = db.patients.insert_one(patient_data)
        patient_id = result.inserted_id
        
        # --- Ενημέρωση Λίστας Ασθενών Γιατρού ---
        db.doctors.update_one(
            {"_id": selected_doctor_id},
            {"$addToSet": {"managed_patients": patient_id}}
        )
        
        # --- Απάντηση Επιτυχίας ---
        # Εδώ θα μπορούσαμε να επιστρέψουμε και JWT token για αυτόματη σύνδεση
        return jsonify({
            "message": "Patient registered successfully",
            "patient_id": str(patient_id) 
        }), 201

    except Exception as e:
        logger.error(f"Error registering patient: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500 

@patient_portal_bp.route('/login', methods=['POST'])
def login_patient():
    """Endpoint για τη σύνδεση ασθενή από το PWA."""
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({"error": "Missing email or password"}), 400

        email = data['email']
        password = data['password']

        # Αναζήτηση του ασθενή με το email
        patient = db.patients.find_one({"personal_details.contact.email": email})

        if patient and 'account_details' in patient and 'password_hash' in patient['account_details']:
            stored_hash = patient['account_details']['password_hash']
            
            # Έλεγχος κωδικού με το bcrypt της εφαρμογής
            app_bcrypt = current_app.bcrypt if hasattr(current_app, 'bcrypt') else current_app.extensions.get('bcrypt')
            if not app_bcrypt:
                logger.error("Bcrypt not available on app context in patient_portal.py (login_patient)")
                return jsonify({"error": "Internal server error - auth misconfiguration"}), 500
            if app_bcrypt.check_password_hash(stored_hash, password):
                # Επιτυχής σύνδεση
                patient_id = str(patient['_id'])
                
                # Δημιουργία JWT token
                access_token = create_access_token(
                    identity=patient_id,
                    expires_delta=datetime.timedelta(days=7) # Token ισχύει για 7 ημέρες για το PWA
                )
                
                # Συλλογή βασικών στοιχείων για αποθήκευση στο frontend
                patient_info = {
                    "id": patient_id,
                    "first_name": patient['personal_details']['first_name'],
                    "last_name": patient['personal_details']['last_name'],
                    "amka": patient['personal_details']['amka'],
                    "email": patient['personal_details']['contact']['email']
                    # Προσθέστε κι άλλα πεδία αν χρειάζονται στο PWA
                }
                
                # Ενημέρωση last_login (προαιρετικά, αν θέλουμε να το παρακολουθούμε)
                # db.patients.update_one(...)
                
                return jsonify({
                    "access_token": access_token,
                    "patient_info": patient_info
                }), 200
            else:
                # Λάθος password
                return jsonify({"error": "Invalid email or password"}), 401
        else:
            # Ο ασθενής δεν βρέθηκε
            return jsonify({"error": "Invalid email or password"}), 401

    except Exception as e:
        logger.error(f"Error during patient login: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500 

@patient_portal_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_patient_profile():
    """Επιστρέφει τα στοιχεία προφίλ του συνδεδεμένου ασθενή."""
    patient_id_str = get_jwt_identity()
    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id_str)
        patient = db.patients.find_one({"_id": patient_object_id})
        
        if not patient:
            return jsonify({"error": "Patient not found"}), 404
            
        # Προετοιμασία δεδομένων για επιστροφή (αφαίρεση ευαίσθητων στοιχείων)
        profile_data = {
            "id": patient_id_str,
            "first_name": patient.get('personal_details', {}).get('first_name'),
            "last_name": patient.get('personal_details', {}).get('last_name'),
            "amka": patient.get('personal_details', {}).get('amka'),
            "date_of_birth": patient.get('personal_details', {}).get('date_of_birth'),
            "gender": patient.get('personal_details', {}).get('gender'),
            "email": patient.get('personal_details', {}).get('contact', {}).get('email'),
            "phone": patient.get('personal_details', {}).get('contact', {}).get('phone'),
            "address": patient.get('personal_details', {}).get('contact', {}).get('address'),
            # Μπορούμε να προσθέσουμε κι άλλα μη ευαίσθητα πεδία αν χρειάζεται
        }
        return jsonify(profile_data), 200
        
    except InvalidId:
        return jsonify({"error": "Invalid patient ID in token"}), 400
    except Exception as e:
        logger.error(f"Error fetching patient profile: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@patient_portal_bp.route('/profile', methods=['PATCH'])
@jwt_required()
def update_patient_profile():
    """Ενημερώνει τα στοιχεία επικοινωνίας του συνδεδεμένου ασθενή."""
    patient_id_str = get_jwt_identity()
    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid patient ID in token"}), 400

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # --- Επιτρεπόμενα πεδία για ενημέρωση --- 
        allowed_fields = ['email', 'phone', 'address']
        update_payload = {}
        
        for field in allowed_fields:
            if field in data:
                # Ελέγχουμε αν το πεδίο είναι κενό string, το μετατρέπουμε σε None 
                # ή διατηρούμε την τιμή αν δεν είναι κενό.
                value = data[field] if data[field] else None 
                update_payload[f"personal_details.contact.{field}"] = value

        # Έλεγχος αν υπάρχουν δεδομένα για ενημέρωση
        if not update_payload:
            return jsonify({"error": "No updatable contact fields provided (email, phone, address allowed)"}), 400

        # --- Έλεγχος Μοναδικότητας Email (αν αλλάζει) --- 
        if 'personal_details.contact.email' in update_payload:
            new_email = update_payload['personal_details.contact.email']
            # Έλεγχος μόνο αν το νέο email δεν είναι None και είναι διαφορετικό από το παλιό email του χρήστη
            current_patient = db.patients.find_one({"_id": patient_object_id}, {"personal_details.contact.email": 1})
            current_email = current_patient.get('personal_details', {}).get('contact', {}).get('email')
            
            if new_email and new_email != current_email:
                existing_patient_email = db.patients.find_one({"personal_details.contact.email": new_email})
                if existing_patient_email:
                    return jsonify({"error": f"Email '{new_email}' is already in use by another patient"}), 409

        # --- Ενημέρωση Βάσης Δεδομένων ---
        result = db.patients.update_one(
            {"_id": patient_object_id},
            {
                "$set": update_payload,
                "$currentDate": { "last_updated_at": True }
            }
        )

        if result.matched_count == 0:
            # Αυτό δεν θα έπρεπε να συμβεί αφού έχουμε έγκυρο token
            return jsonify({"error": "Patient not found"}), 404 
        elif result.modified_count == 0:
            return jsonify({"message": "Profile data is already up to date."}), 200
        else:
            # Αν θέλουμε να επιστρέψουμε το ενημερωμένο προφίλ:
            # updated_profile = db.patients.find_one(...) # όπως στο GET /profile
            # return jsonify(updated_profile), 200
            return jsonify({"message": "Profile updated successfully"}), 200

    except Exception as e:
        logger.error(f"Error updating patient profile: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500 

# --- Endpoints Αρχείων Ασθενή --- 

# Βοηθητική συνάρτηση για τον έλεγχο επιτρεπόμενου τύπου αρχείου
def allowed_file(filename):
    ALLOWED_EXTENSIONS = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'png', 'jpg', 'jpeg', 'txt', 'csv'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
@patient_portal_bp.route('/files', methods=['GET'])
@jwt_required()
def get_my_files():
    """Επιστρέφει τη λίστα των αρχείων του συνδεδεμένου ασθενή."""
    patient_id_str = get_jwt_identity()
    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id_str)
        patient = db.patients.find_one({"_id": patient_object_id}, {"uploaded_files": 1})
        
        if not patient or 'uploaded_files' not in patient:
            return jsonify([]), 200 # Επιστροφή κενής λίστας αν δεν υπάρχουν αρχεία
            
        files_list = patient['uploaded_files']
        
        # Απλή ταξινόμηση (νεότερα πρώτα) και αφαίρεση extracted_text
        processed_files = []
        for file in sorted(files_list, key=lambda x: x.get('upload_date'), reverse=True):
            file_copy = file.copy()
            if 'extracted_text' in file_copy: del file_copy['extracted_text']
            if 'upload_date' in file_copy and isinstance(file_copy['upload_date'], datetime.datetime):
                 file_copy['upload_date'] = file_copy['upload_date'].isoformat()
            # Προσθήκη του 'id' field για ευκολία στο frontend
            file_copy['id'] = file_copy['file_id'] 
            processed_files.append(file_copy)
            
        return jsonify(processed_files), 200
        
    except InvalidId:
        return jsonify({"error": "Invalid patient ID in token"}), 400
    except Exception as e:
        logger.error(f"Error fetching patient files: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@patient_portal_bp.route('/files', methods=['POST'])
@jwt_required()
def upload_my_file():
    """Επιτρέπει στον συνδεδεμένο ασθενή να ανεβάσει αρχείο."""
    patient_id_str = get_jwt_identity()
    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid patient ID in token"}), 400
        
    # Έλεγχος αν στάλθηκε αρχείο στο request
    if 'file' not in request.files:
        return jsonify({"error": "Missing 'file' in request"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    # Έλεγχος επιτρεπόμενου τύπου αρχείου
    if not allowed_file(file.filename):
        allowed_types_str = ", ".join(current_app.config.get('ALLOWED_EXTENSIONS', set()))
        return jsonify({"error": f"File type not allowed. Allowed: {allowed_types_str}"}), 400

    try:
        # Δημιουργία ασφαλούς ονόματος αρχείου & φακέλου
        original_filename = secure_filename(file.filename)
        filename = original_filename 
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        patient_upload_folder = os.path.join(upload_folder, patient_id_str) # Χρήση ID ως string για όνομα φακέλου
        os.makedirs(patient_upload_folder, exist_ok=True)
        file_path = os.path.join(patient_upload_folder, filename)
        
        # Αποθήκευση αρχείου
        file.save(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Δημιουργία metadata
        file_metadata = {
            "file_id": str(ObjectId()),
            "filename": filename,
            "original_filename": original_filename,
            "file_path": os.path.join(patient_id_str, filename), # Σχετική διαδρομή με ID
            "mime_type": mime_type or 'application/octet-stream',
            "upload_date": datetime.datetime.now(datetime.timezone.utc),
            "size_bytes": os.path.getsize(file_path),
            "uploaded_by": patient_id_str, # Ο ίδιος ο ασθενής
            "extracted_text": None
        }
        
        # Ενημέρωση του ασθενή στη βάση
        update_result = db.patients.update_one(
            {"_id": patient_object_id},
            {
                "$push": {"uploaded_files": file_metadata},
                "$currentDate": {"last_updated_at": True}
            }
        )

        if update_result.modified_count == 1:
            # Εκτέλεση OCR αν είναι PDF
            ocr_text = None
            if file_metadata['mime_type'] == 'application/pdf':
                try:
                    logger.info(f"Attempting OCR for file uploaded by patient: {file_path}")
                    # Χρήση της απόλυτης διαδρομής για το OCR
                    ocr_text = extract_text_from_pdf(file_path) 
                    logger.info(f"OCR finished for {filename}. Extracted ~{len(ocr_text or '')} chars.")
                    # Ενημέρωση του record με το OCR text
                    db.patients.update_one(
                        {"_id": patient_object_id, "uploaded_files.file_id": file_metadata["file_id"]},
                        {"$set": {"uploaded_files.$.extracted_text": ocr_text}}
                    )
                except Exception as ocr_err:
                    logger.error(f"OCR processing error for patient upload: {ocr_err}")
            
            # Επιστροφή των metadata του αρχείου που ανέβηκε
            response_data = file_metadata.copy()
            response_data['id'] = response_data['file_id']
            if 'extracted_text' in response_data: del response_data['extracted_text']
            response_data['upload_date'] = response_data['upload_date'].isoformat()
            return jsonify(response_data), 201
        else:
            try: os.remove(file_path) # Cleanup
            except: pass
            return jsonify({"error": "Failed to update patient record"}), 500
            
    except Exception as e:
        logger.error(f"Error during patient file upload: {e}")
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500

@patient_portal_bp.route('/files/<string:file_id>', methods=['DELETE'])
@jwt_required()
def delete_my_file(file_id):
    """Επιτρέπει στον συνδεδεμένο ασθενή να διαγράψει ένα αρχείο του."""
    patient_id_str = get_jwt_identity()
    if db is None: return jsonify({"error": "Database connection failed"}), 500
    
    try:
        patient_object_id = ObjectId(patient_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid patient ID in token"}), 400
        
    try:
        # Έλεγχος αν το αρχείο ανήκει στον ασθενή
        patient = db.patients.find_one(
            {"_id": patient_object_id, "uploaded_files.file_id": file_id},
            {"uploaded_files.$": 1} 
        )
        if not patient or not patient.get('uploaded_files'):
            return jsonify({"error": "File not found or does not belong to this patient"}), 404
            
        file_metadata = patient['uploaded_files'][0]
        
        # Διαγραφή από τη βάση
        update_result = db.patients.update_one(
            {"_id": patient_object_id},
            {"$pull": {"uploaded_files": {"file_id": file_id}}}
        )
        
        if update_result.modified_count == 1:
            # Διαγραφή από το filesystem
            try:
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                # Προσοχή: το file_path στα metadata είναι ήδη σχετικό
                file_disk_path = os.path.join(upload_folder, file_metadata.get('file_path', '')) 
                if os.path.exists(file_disk_path):
                    os.remove(file_disk_path)
                    logger.info(f"Deleted file from disk by patient: {file_disk_path}")
            except Exception as e:
                logger.error(f"Error deleting file from filesystem by patient: {e}")
            return jsonify({"message": "File deleted successfully"}), 200 # or 204 No Content
        else:
            return jsonify({"error": "Failed to remove file from record"}), 500
            
    except Exception as e:
        logger.error(f"Error deleting patient file: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@patient_portal_bp.route('/files/<string:file_id>/download', methods=['GET'])
@jwt_required()
def download_my_file(file_id):
    """Επιτρέπει στον συνδεδεμένο ασθενή να κατεβάσει ένα αρχείο του."""
    patient_id_str = get_jwt_identity()
    if db is None: return jsonify({"error": "Database connection failed"}), 500
    
    try:
        patient_object_id = ObjectId(patient_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid patient ID in token"}), 400
        
    try:
        # Έλεγχος αν το αρχείο ανήκει στον ασθενή
        patient = db.patients.find_one(
            {"_id": patient_object_id, "uploaded_files.file_id": file_id},
            {"uploaded_files.$": 1} 
        )
        if not patient or not patient.get('uploaded_files'):
            return jsonify({"error": "File not found or does not belong to this patient"}), 404
            
        file_metadata = patient['uploaded_files'][0]
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        file_path_relative = file_metadata.get('file_path', '')
        file_disk_path = os.path.join(upload_folder, file_path_relative)
        directory = os.path.dirname(file_disk_path)
        filename = os.path.basename(file_disk_path)
        original_filename = file_metadata.get('original_filename', filename)

        if not os.path.exists(file_disk_path):
            return jsonify({"error": "File not found on server storage"}), 404
            
        return send_from_directory(
            directory=directory,
            path=filename,
            as_attachment=True,
            download_name=original_filename
        )
            
    except Exception as e:
        logger.error(f"Error downloading patient file: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500 

# --- Endpoint Συνεδριών Ασθενή --- 
@patient_portal_bp.route('/sessions', methods=['GET'])
@jwt_required()
def get_my_sessions():
    """Επιστρέφει τη λίστα των συνεδριών του συνδεδεμένου ασθενή."""
    patient_id_str = get_jwt_identity()
    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id_str)
        
        # Βρίσκουμε τις συνεδρίες του ασθενή, ταξινομημένες (νεότερες πρώτα)
        sessions_cursor = db.sessions.find({"patient_id": patient_object_id}).sort("timestamp", -1)
        
        sessions_list = []
        for session in sessions_cursor:
            session_copy = session.copy()
            # Μετατροπή IDs και Timestamps
            session_copy['id'] = str(session_copy.pop('_id'))
            if 'doctor_id' in session_copy and isinstance(session_copy['doctor_id'], ObjectId):
                session_copy['doctor_id'] = str(session_copy['doctor_id'])
            if 'patient_id' in session_copy and isinstance(session_copy['patient_id'], ObjectId):
                session_copy['patient_id'] = str(session_copy['patient_id'])
            if 'timestamp' in session_copy and isinstance(session_copy['timestamp'], datetime.datetime):
                session_copy['timestamp'] = session_copy['timestamp'].isoformat()
            if 'followup_date' in session_copy and session_copy['followup_date'] and isinstance(session_copy['followup_date'], datetime.datetime):
                session_copy['followup_date'] = session_copy['followup_date'].isoformat()
                
            sessions_list.append(session_copy)
            
        return jsonify(sessions_list), 200
        
    except InvalidId:
        return jsonify({"error": "Invalid patient ID in token"}), 400
    except Exception as e:
        logger.error(f"Error fetching patient sessions: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500 

@patient_portal_bp.route('/sessions/<string:session_id>', methods=['GET'])
@jwt_required()
def get_my_session_details(session_id):
    """Επιστρέφει τις λεπτομέρειες μιας συγκεκριμένης συνεδρίας του ασθενή."""
    patient_id_str = get_jwt_identity()
    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id_str)
        session_object_id = ObjectId(session_id)
        
        # Βρίσκουμε τη συνεδρία, εξασφαλίζοντας ότι ανήκει στον ασθενή
        session = db.sessions.find_one({
            "_id": session_object_id,
            "patient_id": patient_object_id 
        })
        
        if not session:
            return jsonify({"error": "Session not found or does not belong to this patient"}), 404
            
        # Μετατροπές IDs και Timestamps
        session_copy = session.copy()
        session_copy['id'] = str(session_copy.pop('_id'))
        if 'doctor_id' in session_copy and isinstance(session_copy['doctor_id'], ObjectId):
            session_copy['doctor_id'] = str(session_copy['doctor_id'])
        if 'patient_id' in session_copy and isinstance(session_copy['patient_id'], ObjectId):
            session_copy['patient_id'] = str(session_copy['patient_id'])
        if 'timestamp' in session_copy and isinstance(session_copy['timestamp'], datetime.datetime):
            session_copy['timestamp'] = session_copy['timestamp'].isoformat()
        if 'followup_date' in session_copy and session_copy['followup_date'] and isinstance(session_copy['followup_date'], datetime.datetime):
            session_copy['followup_date'] = session_copy['followup_date'].isoformat()
            
        return jsonify(session_copy), 200
        
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400
    except Exception as e:
        logger.error(f"Error fetching patient session details: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500 