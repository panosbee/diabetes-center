from flask import Flask, jsonify, request, send_from_directory, session, make_response
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from bson.objectid import ObjectId
from bson.errors import InvalidId
import datetime
from werkzeug.utils import secure_filename
import mimetypes
import pytesseract
import fitz
from PIL import Image
import io
import subprocess
import requests # Προσθήκη import για requests
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt # Import Bcrypt
from flask_jwt_extended import ( # <-- Βεβαιωθείτε ότι αυτά είναι import
    JWTManager, create_access_token, jwt_required, 
    get_jwt_identity, verify_jwt_in_request, decode_token 
)
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect # Προσθέτουμε disconnect
from flask_cors import CORS, cross_origin # <--- Import cross_origin
import json # <-- Προσθήκη import

app = Flask(__name__)
CORS(app, 
     resources={r"/api/*": {"origins": "*"}}, 
     supports_credentials=True, 
     methods=["GET", "POST", "OPTIONS", "PATCH", "PUT", "DELETE"],
     expose_headers=['Content-Range']) # <-- Προσθέτουμε το expose_headers

# --- Ορισμός Σταθερών --- 
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'txt', 'csv'}

# --- Αρχικοποίηση Επεκτάσεων ---
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Ρυθμίσεις Flask App ---
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# --- Φόρτωση .env & Keys (ΜΟΝΟ ΜΙΑ ΦΟΡΑ) ---
load_dotenv()
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL") # <-- Προσθήκη φόρτωσης URL

if not DEEPSEEK_API_KEY:
    print("WARNING: DEEPSEEK_API_KEY not found in environment variables!")
if not app.config["JWT_SECRET_KEY"]:
    print("ERROR: JWT_SECRET_KEY not found in environment variables! JWT will not work.")
if not DEEPSEEK_API_URL: # <-- Έλεγχος αν φορτώθηκε το URL
    print("ERROR: DEEPSEEK_API_URL not found in environment variables! AI query will not work.")

# --- Tesseract Setup ---
TESSERACT_CMD = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- MongoDB Connection ---
try:
    # Προτιμούμε μεταβλητή περιβάλλοντος αν υπάρχει, αλλιώς default
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    client = MongoClient(MONGO_URI)
    # Η εντολή ismaster() είναι ένας απλός τρόπος ελέγχου της σύνδεσης.
    client.admin.command('ismaster')
    db = client.diabetes_db # Επιλέγουμε τη βάση δεδομένων 'diabetes_db'
    print("MongoDB connection successful.")
    # Δημιουργία συλλογών αν δεν υπάρχουν (προαιρετικό, αλλά καλή πρακτική)
    if 'patients' not in db.list_collection_names():
        db.create_collection('patients')
        print("Created 'patients' collection.")
    if 'doctors' not in db.list_collection_names():
        db.create_collection('doctors')
        print("Created 'doctors' collection.")
    if 'sessions' not in db.list_collection_names():
        db.create_collection('sessions')
        print("Created 'sessions' collection.")

except ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    db = None # Ορίζουμε το db ως None για να αποφύγουμε λάθη παρακάτω

@app.route('/')
def home():
    if db is not None:
        return jsonify({"message": "Welcome to the Diabetes Management API!", "db_status": "connected"})
    else:
        return jsonify({"message": "Welcome to the Diabetes Management API!", "db_status": "disconnected"}), 500

# --- ΜΕΤΑΚΙΝΗΣΗ ΚΑΙ ΑΠΛΟΠΟΙΗΣΗ ΓΙΑ DEBUG --- 

# Endpoint για ανάκτηση λίστας συνεδριών του συνδεδεμένου ασθενή
@app.route('/api/patient-portal/sessions', methods=['GET'])
@jwt_required() # <--- ΕΠΑΝΑΦΟΡΑ
def get_my_sessions():
    current_patient_id_str = get_jwt_identity() # <--- ΕΠΑΝΑΦΟΡΑ
    try:
        patient_object_id = ObjectId(current_patient_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid identity in token"}), 401

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Φέρνουμε τις συνεδρίες ΜΟΝΟ για αυτόν τον ασθενή
        sessions_cursor = db.sessions.find({
            "patient_id": patient_object_id
        }).sort("timestamp", -1)
        
        sessions_list = []
        for session in sessions_cursor:
            # Μετατροπές IDs/Timestamps σε string
            session['_id'] = str(session['_id'])
            session['patient_id'] = str(session['patient_id']) 
            if 'doctor_id' in session:
                 session['doctor_id'] = str(session['doctor_id'])
            if 'timestamp' in session and isinstance(session['timestamp'], datetime.datetime):
                session['timestamp'] = session['timestamp'].isoformat()
            if 'created_at' in session and isinstance(session['created_at'], datetime.datetime):
                session['created_at'] = session['created_at'].isoformat()
            if 'last_updated_at' in session and isinstance(session['last_updated_at'], datetime.datetime):
                session['last_updated_at'] = session['last_updated_at'].isoformat()
            sessions_list.append(session)

        return jsonify(sessions_list), 200

    except Exception as e:
        print(f"Error fetching sessions for patient {current_patient_id_str}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500
    
# Endpoint για ανάκτηση λίστας αρχείων του συνδεδεμένου ασθενή
@app.route('/api/patient-portal/files', methods=['GET'])
@jwt_required() # <--- ΕΠΑΝΑΦΟΡΑ
def get_my_files_list():
    current_patient_id_str = get_jwt_identity() # <--- ΕΠΑΝΑΦΟΡΑ
    try:
        patient_object_id = ObjectId(current_patient_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid identity in token"}), 401

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Βρίσκουμε τον ασθενή και παίρνουμε ΜΟΝΟ τη λίστα αρχείων
        patient = db.patients.find_one({"_id": patient_object_id}, {"uploaded_files": 1, "_id": 0})
        
        if not patient or 'uploaded_files' not in patient:
            return jsonify([]), 200 # Δεν βρέθηκε ή δεν έχει αρχεία -> κενή λίστα

        files_list = patient['uploaded_files']
        
        # Μετατροπή ημερομηνιών σε string και αφαίρεση κειμένου OCR
        for file_meta in files_list:
             if 'upload_date' in file_meta and isinstance(file_meta['upload_date'], datetime.datetime):
                 file_meta['upload_date'] = file_meta['upload_date'].isoformat()
             if 'extracted_text' in file_meta:
                 del file_meta['extracted_text'] # Δεν στέλνουμε το κείμενο στη λίστα

        # Ταξινόμηση με βάση την ημερομηνία ανεβάσματος (νεότερα πρώτα)
        files_list.sort(key=lambda x: x.get('upload_date', '0'), reverse=True)

        return jsonify(files_list), 200

    except Exception as e:
        print(f"Error fetching file list for patient {current_patient_id_str}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- ΥΠΟΛΟΙΠΑ ENDPOINTS ΑΠΟ ΕΔΩ ΚΑΙ ΚΑΤΩ --- 

# --- Patient Specific Endpoints (Protected) --- 

@app.route('/api/patient-portal/profile', methods=['GET']) 
@jwt_required()
def get_my_patient_data():
    """Επιστρέφει τα πλήρη στοιχεία του συνδεδεμένου ασθενή."""
    current_patient_id_str = get_jwt_identity() # Παίρνουμε το ID από το token
    try:
        current_patient_object_id = ObjectId(current_patient_id_str)
    except InvalidId:
        # Αυτό υποδηλώνει πρόβλημα με το token (δεν είναι ID ασθενή;)
        return jsonify({"error": "Invalid identity in token"}), 401 

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        patient = db.patients.find_one({"_id": current_patient_object_id})

        if patient:
            # Ασθενής βρέθηκε
            # Μετατροπές IDs/Timestamps σε string (παρόμοια με get_patient_by_id)
            patient['_id'] = str(patient['_id'])
            patient['id'] = str(patient.pop('_id')) # <--- Μετατρέπουμε και μετονομάζουμε σε id
            if 'created_at' in patient and isinstance(patient['created_at'], datetime.datetime):
                patient['created_at'] = patient['created_at'].isoformat()
            if 'last_updated_at' in patient and isinstance(patient['last_updated_at'], datetime.datetime):
                patient['last_updated_at'] = patient['last_updated_at'].isoformat()
            if 'assigned_doctors' in patient and isinstance(patient['assigned_doctors'], list):
                patient['assigned_doctors'] = [str(doc_id) for doc_id in patient['assigned_doctors'] if isinstance(doc_id, ObjectId)]
            # Μετατροπή και στα uploaded_files (αν χρειάζεται αργότερα)
            if 'uploaded_files' in patient and isinstance(patient['uploaded_files'], list):
                for file_meta in patient['uploaded_files']:
                     if 'upload_date' in file_meta and isinstance(file_meta['upload_date'], datetime.datetime):
                         file_meta['upload_date'] = file_meta['upload_date'].isoformat()
            
            # Αφαίρεση του password hash πριν την επιστροφή!
            if 'account_details' in patient and 'password_hash' in patient['account_details']:
                 del patient['account_details']['password_hash']

            return jsonify(patient), 200
        else:
            # Δεν βρέθηκε ασθενής με το ID από το token (περίεργο)
            return jsonify({"error": "Patient data not found for this token"}), 404

    except Exception as e:
        print(f"Error fetching data for patient {current_patient_id_str}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/api/patient-portal/profile', methods=['PATCH']) 
@jwt_required()
def update_my_patient_data():
    """Επιτρέπει στον συνδεδεμένο ασθενή να ενημερώσει τα δικά του στοιχεία."""
    current_patient_id_str = get_jwt_identity()
    try:
        patient_object_id = ObjectId(current_patient_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid identity in token"}), 401

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        update_data = request.get_json()
        if not update_data:
            return jsonify({"error": "Request body must be JSON and non-empty"}), 400

        # --- Περιορισμός Ενημερώσιμων Πεδίων --- 
        allowed_updates = {}
        # Επιτρέπουμε αλλαγές μόνο σε συγκεκριμένα υπο-πεδία
        if 'personal_details' in update_data and isinstance(update_data['personal_details'], dict):
            allowed_personal = {}
            # Π.χ., επιτρέπουμε αλλαγή τηλεφώνου/email, αλλά ΟΧΙ ονόματος/ΑΜΚΑ/ημ. γέννησης
            if 'contact' in update_data['personal_details'] and isinstance(update_data['personal_details']['contact'], dict):
                 allowed_personal['personal_details.contact'] = update_data['personal_details']['contact']
            # Θα μπορούσαμε να προσθέσουμε κι άλλα εδώ (π.χ. διεύθυνση)
            if allowed_personal:
                allowed_updates.update(allowed_personal)
        
        if 'medical_profile' in update_data and isinstance(update_data['medical_profile'], dict):
            allowed_medical = {}
            # Επιτρέπουμε αλλαγή π.χ. ύψους, αλλεργιών, περιγραφής ιστορικού
            if 'height_cm' in update_data['medical_profile']:
                allowed_medical['medical_profile.height_cm'] = update_data['medical_profile']['height_cm']
            if 'allergies' in update_data['medical_profile']:
                 allowed_medical['medical_profile.allergies'] = update_data['medical_profile']['allergies']
            if 'medical_history_summary' in update_data['medical_profile']:
                 allowed_medical['medical_profile.medical_history_summary'] = update_data['medical_profile']['medical_history_summary']
            # ΔΕΝ επιτρέπουμε αλλαγή των conditions από τον ασθενή
            if allowed_medical:
                 allowed_updates.update(allowed_medical)

        # Αν δεν υπάρχουν επιτρεπτές αλλαγές στα δεδομένα που στάλθηκαν
        if not allowed_updates:
             return jsonify({"error": "No updatable fields provided or field not allowed for patient update"}), 400
        # ---------------------------------------

        # Προετοιμασία payload με χρήση dot notation για update συγκεκριμένων πεδίων
        update_payload = {
            "$set": allowed_updates,
            "$currentDate": { "last_updated_at": True }
        }

        result = db.patients.update_one({"_id": patient_object_id}, update_payload)

        if result.matched_count == 0:
            return jsonify({"error": "Patient not found for this token"}), 404
        elif result.modified_count == 0 and result.matched_count == 1:
             return jsonify({"message": "Patient data found but no changes applied"}), 200
        else:
            return jsonify({"message": "Patient data updated successfully"}), 200

    except Exception as e:
        print(f"Error updating data for patient {current_patient_id_str}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/api/patient-portal/files', methods=['POST']) 
@jwt_required()
def upload_my_patient_file():
    print("--- DEBUG: Inside upload_MY_patient_file (for patient portal) ---")
    current_patient_id_str = get_jwt_identity()
    try:
        patient_object_id = ObjectId(current_patient_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid identity in token"}), 401 

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    # Έλεγχος αν ο ασθενής υπάρχει (για σιγουριά)
    # Δεν χρειάζεται να φέρουμε assigned_doctors εδώ
    patient = db.patients.find_one({"_id": patient_object_id}, {"_id": 1})
    if patient is None:
        # Περίεργο αν το token ήταν έγκυρο
        return jsonify({"error": f"Patient data not found for this token"}), 404

    # Έλεγχος αν στάλθηκε αρχείο στο request (ίδιο με upload_patient_file)
    if 'file' not in request.files:
        # Πιο συγκεκριμένο μήνυμα
        return jsonify({"error": "Bad Request: Missing 'file' key in form data.", "details": "Ensure you are sending the file using multipart/form-data with the key named 'file'"}), 400 
    file = request.files['file']
    if file.filename == '':
        # Πιο συγκεκριμένο μήνυμα
        return jsonify({"error": "Bad Request: No file selected.", "details": "The 'file' part was sent, but no actual file was selected."}), 400

    if file and allowed_file(file.filename):
        # --- Η υπόλοιπη λογική είναι ΣΧΕΔΟΝ ΙΔΙΑ με την upload_patient_file --- 
        # (secure_filename, create folder, save file, get mime, create metadata)
        original_filename = secure_filename(file.filename)
        filename = original_filename 
        patient_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_patient_id_str) # Χρησιμοποιούμε το ID από το token
        os.makedirs(patient_upload_folder, exist_ok=True)
        file_path = os.path.join(patient_upload_folder, filename)
        try:
            file.save(file_path)
        except Exception as e:
             print(f"Error saving file uploaded by patient {current_patient_id_str}: {e}")
             return jsonify({"error": "Failed to save file on server"}), 500

        mime_type, _ = mimetypes.guess_type(file_path)
        file_metadata = {
            "file_id": str(ObjectId()),
            "filename": filename,
            "original_filename": original_filename,
            "file_path": file_path.replace(app.config['UPLOAD_FOLDER'], '').lstrip(os.sep),
            "mime_type": mime_type or 'application/octet-stream',
            "upload_date": datetime.datetime.now(datetime.timezone.utc),
            "size_bytes": os.path.getsize(file_path),
            "uploaded_by": "patient", # Προσθέτουμε ένδειξη ποιος το ανέβασε
            "extracted_text": None 
        }
        
        # Ενημέρωση βάσης (ίδιο με πριν)
        update_result = db.patients.update_one(
            {"_id": patient_object_id},
            {
                "$push": { "uploaded_files": file_metadata },
                "$currentDate": { "last_updated_at": True }
            }
        )

        if update_result.modified_count == 1:
            # --- ΕΚΤΕΛΕΣΗ OCR (Ίδιο με πριν) --- 
            ocr_text = "[OCR not attempted or failed]" 
            if file_metadata['mime_type'] == 'application/pdf':
                 print(f"Attempting OCR for file: {file_path}")
                 absolute_file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_metadata['file_path'])
                 ocr_text = extract_text_from_pdf(absolute_file_path)
                 print(f"OCR finished for {filename}. Extracted ~{len(ocr_text)} chars.")
                 db.patients.update_one(
                     {"_id": patient_object_id, "uploaded_files.file_id": file_metadata["file_id"]},
                     {"$set": { "uploaded_files.$.extracted_text": ocr_text } }
                 )
                 print(f"Updated DB record for file {file_metadata['file_id']} with OCR text.")
            else:
                 print(f"Skipping OCR for non-PDF file: {filename} (MIME: {file_metadata['mime_type']})")
            # -----------------------------------------------------
            return jsonify({
                "message": "File uploaded successfully by patient",
                "file_info": {
                    "file_id": file_metadata["file_id"],
                    "filename": filename,
                    "mime_type": file_metadata["mime_type"],
                    "ocr_status": "Processed" if file_metadata['mime_type'] == 'application/pdf' else "Skipped (not PDF)"
                }
            }), 201
        else:
            # ... (ίδιος χειρισμός σφάλματος όπως πριν) ...
            try:
                os.remove(file_path)
            except OSError as e:
                print(f"Error removing file after DB update failure: {e}")
            return jsonify({"error": "Failed to update patient record with file info"}), 500
    else:
        # Πιο συγκεκριμένο μήνυμα
        allowed_types_str = ", ".join(ALLOWED_EXTENSIONS)
        return jsonify({"error": "Bad Request: File type not allowed.", "details": f"The uploaded file type is not permitted. Allowed types: {allowed_types_str}"}), 400

    return jsonify({"error": "An unexpected error occurred during file upload"}), 500

@app.route('/api/patient-portal/files/<string:file_id>', methods=['GET']) 
@jwt_required()
def get_my_uploaded_file(file_id):
    """Στέλνει ένα συγκεκριμένο ανεβασμένο αρχείο που ανήκει στον συνδεδεμένο ασθενή."""
    current_patient_id_str = get_jwt_identity()
    try:
        patient_object_id = ObjectId(current_patient_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid identity in token"}), 401

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    # Δεν χρειάζεται έλεγχος format για το file_id εδώ

    try:
        # Βρίσκουμε τον ασθενή (βάσει token) και ψάχνουμε το αρχείο ΜΟΝΟ σε αυτόν
        patient = db.patients.find_one(
            {"_id": patient_object_id, "uploaded_files.file_id": file_id},
            {"uploaded_files.$": 1} # Παίρνουμε μόνο το ταιριαστό αρχείο
        )

        if not patient or 'uploaded_files' not in patient or not patient['uploaded_files']:
            # Είτε ο ασθενής δεν βρέθηκε (περίεργο) είτε το αρχείο δεν ανήκει σε αυτόν
            return jsonify({"error": "File not found or access denied"}), 404

        # Πήραμε το metadata του αρχείου
        file_metadata = patient['uploaded_files'][0]
        stored_filename = file_metadata.get('filename')

        if not stored_filename:
             print(f"Error: Missing filename in metadata for file_id {file_id} of patient {current_patient_id_str}")
             return jsonify({"error": "File metadata incomplete"}), 500

        # Κατασκευάζουμε τη διαδρομή
        directory = os.path.join(app.config['UPLOAD_FOLDER'], current_patient_id_str)
        absolute_directory_path = os.path.abspath(directory)
        absolute_file_path = os.path.join(absolute_directory_path, stored_filename)

        if not os.path.exists(absolute_file_path):
            print(f"Error: File not found on disk: {absolute_file_path}")
            return jsonify({"error": "File not found on server storage"}), 404

        # Στέλνουμε το αρχείο
        return send_from_directory(directory=absolute_directory_path,
                                   path=stored_filename,
                                   as_attachment=False)

    except Exception as e:
        print(f"Error fetching file {file_id} for patient {current_patient_id_str}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Patient Self-Registration Endpoint --- 
@app.route('/api/patients/register', methods=['POST'])
def register_patient():
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # --- Validation --- 
        personal_details = data.get('personal_details')
        account_details = data.get('account_details')
        selected_doctor_id_str = data.get('selected_doctor_id')

        if not personal_details or not isinstance(personal_details, dict) or \
           not all(k in personal_details for k in ('first_name', 'last_name', 'amka')):
            return jsonify({"error": "Missing required personal details (first_name, last_name, amka)"}), 400
            
        if not account_details or not isinstance(account_details, dict) or \
           'password' not in account_details or not account_details['password']:
            return jsonify({"error": "Missing account details (password)"}), 400
            
        if not selected_doctor_id_str:
             return jsonify({"error": "Missing selected_doctor_id"}), 400
             
        # Use AMKA as username
        username_amka = personal_details['amka']
        plain_password = account_details['password']

        # Check doctor ID format and existence
        try:
            selected_doctor_object_id = ObjectId(selected_doctor_id_str)
            if db.doctors.find_one({"_id": selected_doctor_object_id}) is None:
                 return jsonify({"error": f"Selected doctor with id {selected_doctor_id_str} not found"}), 404
        except InvalidId:
            return jsonify({"error": "Invalid selected_doctor_id format"}), 400

        # --- Έλεγχος Μοναδικότητας ΑΜΚΑ --- 
        # Check if patient with this AMKA (username) already exists
        if db.patients.find_one({"personal_details.amka": username_amka}):
            return jsonify({"error": f"Patient with AMKA {username_amka} already registered"}), 409
        # ----------------------------------

        # --- Hashing Password --- 
        hashed_password = bcrypt.generate_password_hash(plain_password).decode('utf-8')

        # --- Prepare Patient Document --- 
        patient_data = {
            "personal_details": personal_details,
            "account_details": { # Adding account details for patient
                "username": username_amka, # Using AMKA as username
                "password_hash": hashed_password
            },
            "medical_profile": data.get('medical_profile', { # Include medical profile if provided
                 'conditions': [], 'allergies': [], 'medical_history_summary': ''
             }),
            "assigned_doctors": [selected_doctor_object_id], # Assign selected doctor
            "is_in_common_space": False, # Default to False on self-registration
            "uploaded_files": [], # Default
            "cgm_integration": { # Default
                "dexcom_status": "not_configured",
                "glooko_status": "not_configured"
            },
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        }
        patient_data['last_updated_at'] = patient_data['created_at']

        # --- Insert Patient --- 
        result = db.patients.insert_one(patient_data)
        inserted_patient_id = result.inserted_id
        inserted_patient_id_str = str(inserted_patient_id)

        # --- Update Doctor's managed_patients --- 
        db.doctors.update_one(
            {"_id": selected_doctor_object_id},
            {"$addToSet": { "managed_patients": inserted_patient_id } }
        )

        # --- Response --- 
        # Maybe return a token immediately upon registration? For now, just success.
        return jsonify({
            "message": "Patient registered and assigned successfully",
            "patient_id": inserted_patient_id_str
        }), 201

    except Exception as e:
        print(f"Error during patient registration: {e}")
        return jsonify({"error": "An internal server error occurred during registration"}), 500

# --- Authentication Endpoints --- 
@app.route('/api/auth/login', methods=['POST'])
def login_doctor():
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Missing username or password"}), 400

        username = data['username']
        password = data['password']

        # Βρίσκουμε τον γιατρό με βάση το username
        doctor = db.doctors.find_one({"account_details.username": username})

        # Έλεγχος αν βρέθηκε ο γιατρός ΚΑΙ αν ο κωδικός ταιριάζει με το hash
        if doctor and bcrypt.check_password_hash(doctor['account_details']['password_hash'], password):
            # Ο κωδικός είναι σωστός! Δημιουργούμε το JWT token.
            access_token = create_access_token(identity=str(doctor['_id']))
            
            # ---> ΠΡΟΣΘΗΚΗ: Επιστρέφουμε και τα στοιχεία του γιατρού <---
            doctor_info = {
                "id": str(doctor['_id']),
                "first_name": doctor.get('personal_details', {}).get('first_name'),
                "last_name": doctor.get('personal_details', {}).get('last_name'),
                # Προσθέστε ό,τι άλλο θέλετε να είναι διαθέσιμο στο frontend
            }
            return jsonify(access_token=access_token, doctor_info=doctor_info), 200
        else:
            # Λάθος username ή password
            return jsonify({"error": "Invalid username or password"}), 401 # Unauthorized

    except Exception as e:
        print(f"Error during doctor login for username {data.get('username', '?')}: {e}")
        return jsonify({"error": "An internal server error occurred during login"}), 500

@app.route('/api/auth/patient/login', methods=['POST'])
def login_patient():
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        data = request.get_json()
        # Για τους ασθενείς, το username είναι το ΑΜΚΑ
        if not data or 'amka' not in data or 'password' not in data:
            return jsonify({"error": "Missing AMKA or password"}), 400

        amka = data['amka']
        password = data['password']

        # Βρίσκουμε τον ασθενή με βάση το ΑΜΚΑ (που είναι το username)
        patient = db.patients.find_one({"personal_details.amka": amka})

        # Έλεγχος αν βρέθηκε ο ασθενής ΚΑΙ αν ο κωδικός ταιριάζει
        if patient and 'account_details' in patient and \
           bcrypt.check_password_hash(patient['account_details'].get('password_hash'), password):
            
            # Ο κωδικός είναι σωστός! Δημιουργούμε το JWT token.
            # Η ταυτότητα τώρα είναι το ID του ΑΣΘΕΝΗ
            access_token = create_access_token(identity=str(patient['_id']))
            
            # Επιστρέφουμε το token ΚΑΙ ίσως κάποια βασικά στοιχεία ασθενή;
            return jsonify(
                access_token=access_token,
                patient_info={ # Προαιρετικά: Βασικά στοιχεία για το frontend
                     "id": str(patient['_id']),
                     "first_name": patient.get('personal_details', {}).get('first_name'),
                     "last_name": patient.get('personal_details', {}).get('last_name'),
                }
            ), 200
        else:
            # Λάθος ΑΜΚΑ ή password
            return jsonify({"error": "Invalid AMKA or password"}), 401 # Unauthorized

    except Exception as e:
        print(f"Error during patient login for AMKA {data.get('amka', '?')}: {e}")
        return jsonify({"error": "An internal server error occurred during login"}), 500

# --- AI Query Endpoint --- 
@app.route('/api/ai/query', methods=['POST'])
def handle_ai_query():
    if not DEEPSEEK_API_KEY:
         return jsonify({"error": "AI service is not configured (API key missing)"}), 503 # Service Unavailable
    
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Request body must be JSON and contain a 'query' field"}), 400
        
        user_query = data['query']
        patient_id = data.get('patient_id') 
        patient_amka = data.get('amka') # <-- Νέο: Παίρνουμε και το ΑΜΚΑ
        patient_object_id = None # <-- Θα το βρούμε είτε από ID είτε από ΑΜΚΑ

        # --- Βήμα 0: Εύρεση Patient ObjectId (αν δόθηκε ID ή AMKA) --- 
        if patient_id:
            try:
                patient_object_id = ObjectId(patient_id)
            except InvalidId:
                 return jsonify({"error": "Invalid patient ID format provided for context"}), 400
        elif patient_amka:
             if db is None: return jsonify({"error": "Database connection failed"}), 500
             patient_found_by_amka = db.patients.find_one({"personal_details.amka": patient_amka}, {"_id": 1})
             if patient_found_by_amka:
                 patient_object_id = patient_found_by_amka['_id']
             else:
                 # Επιστρέφουμε φιλικό μήνυμα αν δεν βρεθεί το ΑΜΚΑ
                 return jsonify({"id": f"ai-no-context-{datetime.datetime.now().timestamp()}", "response": f"Δεν βρέθηκε ασθενής με ΑΜΚΑ {patient_amka} για να φορτωθεί το context."}), 200
        # -------------------------------------------------------------

        # --- Βήμα 1: Συλλογή Context (Αν βρέθηκε patient_object_id) --- 
        context = ""
        # if patient_id: # <-- Αλλάζουμε τον έλεγχο σε patient_object_id
        if patient_object_id:
            try:
                # patient_object_id = ObjectId(patient_id) # <-- Δεν χρειάζεται πια εδώ
                
                # Φέρνουμε δεδομένα ασθενή
                patient_data = db.patients.find_one({"_id": patient_object_id})
                
                # ... (Η υπόλοιπη λογική συλλογής context παραμένει ίδια) ...
                sessions_data = list(db.sessions.find({"patient_id": patient_object_id}).sort("timestamp", -1).limit(5))
                # ... (μετατροπές κλπ) ...
                file_texts = []
                if patient_data and 'uploaded_files' in patient_data:
                     # --- Λήψη κειμένου από ΟΛΑ τα αρχεία με OCR --- 
                     files_with_text = sorted(
                         [f for f in patient_data['uploaded_files'] if f.get('extracted_text')],
                         key=lambda x: x.get('upload_date', datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)), # Χειρισμός αν λείπει το date
                         reverse=True
                     )
                     # Παίρνουμε τα κείμενα για ΟΛΑ τα αρχεία (όχι μόνο τα 2 πιο πρόσφατα)
                     for file_meta in files_with_text: # <-- Αφαίρεση του [:2]
                         # Προσοχή στο μέγεθος του context - ίσως χρειαστεί όριο στο μέλλον
                         file_texts.append({
                             "filename": file_meta['filename'],
                             "upload_date": file_meta['upload_date'].isoformat() if isinstance(file_meta.get('upload_date'), datetime.datetime) else 'N/A',
                             "text": file_meta['extracted_text']
                         })
                    # -------------------------------------------------

                # Μορφοποίηση του context
                if patient_data:
                     context = format_patient_context(patient_data, sessions_data, file_texts)
                else:
                     # Αυτό δεν θα έπρεπε να συμβεί αν βρήκαμε το object_id
                     context = f"[Error: Patient data not found for ObjectId {patient_object_id}]\n" 
                     
            # except InvalidId: # <-- Το πιάσαμε νωρίτερα
            #      return jsonify({"error": "Invalid patient ID format provided for context"}), 400
            except Exception as context_err:
                 print(f"Error retrieving context for patient {patient_object_id}: {context_err}")
                 context = f"[Error retrieving context: {context_err}]\n"
        else:
            # Δεν ζητήθηκε context (ούτε ID ούτε AMKA)
            context = "Context: No specific patient context requested.\n"
        # -----------------------------------------------------------------

        # --- Βήμα 2: Δημιουργία Prompt (με νέο, πιο στοχευμένο system message) --- 
        messages = [
            {"role": "system", "content": """You are a helpful medical assistant specializing in diabetes management.
Analyze the provided context, which includes Patient Information, Recent Sessions, and **Extracted Text from multiple Files (listed with filename and date)**.
When asked about specific data points (like 'Average Glucose', 'Time in Range', 'GMI', 'HbA1c'):
1. Search for the information within the text of **all provided files**.
2. If found in multiple files, prioritize the **most recent file** unless the user specifies otherwise. Clearly state which file you are referencing in your answer (e.g., "According to tidepool.pdf (May 4, 2025), the Average Glucose is...").
3. If the user asks for trends or data over a period, synthesize information from **all relevant files** provided in the context.
4. If the information is not found in any of the provided text extracts or session data, state that clearly. Do not guess.
Answer the user's query concisely based *specifically* on the provided context."""},
            {"role": "user", "content": f"{context}\nUser Query: {user_query}"} 
        ]

        # --- Βήμα 3: Κλήση στο DeepSeek API (όπως πριν) --- 
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            "model": "deepseek-chat", # Υποθετικό όνομα μοντέλου - ΕΛΕΓΞΕ ΤΟ!
            "messages": messages,
            "max_tokens": 300, # <-- Αύξηση ορίου απάντησης
            "temperature": 0.7 # Έλεγχος δημιουργικότητας
        }

        print(f"Sending request to DeepSeek API...")
        try:
            response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30) # timeout 30 δευτ.
            response.raise_for_status() # Έλεγχος για HTTP errors (4xx, 5xx)
            
            response_data = response.json()
            print("Received response from DeepSeek API.")
            
            # --- Βήμα 4: Επεξεργασία απάντησης --- 
            # Η δομή της απάντησης μπορεί να διαφέρει - ΥΠΟΘΕΤΙΚΗ ΔΟΜΗ!
            if 'choices' in response_data and len(response_data['choices']) > 0:
                ai_message = response_data['choices'][0].get('message', {}).get('content', '')
                ai_response = ai_message.strip()
            else:
                ai_response = "AI model did not return a valid response structure."
                print(f"Unexpected DeepSeek API response format: {response_data}")

        except requests.exceptions.RequestException as req_err:
            print(f"Error calling DeepSeek API: {req_err}")
            return jsonify({"error": f"Failed to communicate with AI service: {req_err}"}), 504 # Gateway Timeout
        except Exception as api_err: # Άλλα πιθανά λάθη (π.χ. JSON decode)
             print(f"Error processing DeepSeek API response: {api_err}")
             return jsonify({"error": f"Error processing AI response: {api_err}"}), 500

        # -------------------------------------

        # Return the response payload directly, matching what create might expect
        response_payload = {
            "id": f"ai-response-{datetime.datetime.now().timestamp()}", # Dummy ID
            "response": ai_response
        }
        return jsonify(response_payload), 200

    except Exception as e:
        print(f"Error handling AI query: {e}")
        return jsonify({"error": "An internal server error occurred during AI query"}), 500

# --- CRUD Endpoints for Doctors --- 
@app.route('/api/doctors', methods=['POST'])
def add_doctor():
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # --- Βασική Επικύρωση Δεδομένων ---
        personal_details = data.get('personal_details')
        if not personal_details or not isinstance(personal_details, dict):
            return jsonify({"error": "Missing or invalid 'personal_details'"}), 400

        required_personal_fields = ['first_name', 'last_name', 'specialty'] # Προσθέσαμε ειδικότητα
        for field in required_personal_fields:
            if field not in personal_details or not personal_details[field]:
                return jsonify({"error": f"Missing required field in personal_details: {field}"}), 400

        # Έλεγχος για υπο-πεδία στο contact (προαιρετικά)
        contact_details = personal_details.get('contact')
        if not contact_details or not isinstance(contact_details, dict) or 'email' not in contact_details:
             return jsonify({"error": "Missing or invalid 'contact' details or missing 'email'"}), 400

        # Προαιρετικά: Έλεγχος για μοναδικότητα email γιατρού
        # if db.doctors.find_one({"personal_details.contact.email": contact_details['email']}):
        #     return jsonify({"error": f"Doctor with email {contact_details['email']} already exists"}), 409

        # --- ΝΕΟ: Έλεγχος Account Details & Hashing --- 
        account_details = data.get('account_details')
        if not account_details or not isinstance(account_details, dict) or \
           'username' not in account_details or not account_details['username'] or \
           'password' not in account_details or not account_details['password']:
            return jsonify({"error": "Missing or invalid 'account_details' or missing 'username'/'password'"}), 400
        
        username = account_details['username']
        plain_password = account_details['password']

        # Έλεγχος αν υπάρχει ήδη γιατρός με αυτό το username
        if db.doctors.find_one({"account_details.username": username}):
            return jsonify({"error": f"Username '{username}' already exists"}), 409

        # Hashing του κωδικού
        hashed_password = bcrypt.generate_password_hash(plain_password).decode('utf-8')
        # ------------------------------------------------

        # --- Προετοιμασία Εγγράφου Γιατρού (με hashed password) ---
        doctor_data = {
            "personal_details": personal_details,
            "account_details": {
                "username": username,
                "password_hash": hashed_password # Αποθηκεύουμε το hash!
            },
            "managed_patients": data.get('managed_patients', []),
            "availability_status": data.get('availability_status', 'unavailable'), 
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        }
        doctor_data['last_updated_at'] = doctor_data['created_at']
        
        # --- Εισαγωγή στη Βάση Δεδομένων ---
        result = db.doctors.insert_one(doctor_data)
        inserted_id_str = str(result.inserted_id)

        return jsonify({
            "message": "Doctor registered successfully", # Άλλαξα το μήνυμα
            "doctor_id": inserted_id_str
        }), 201

    except Exception as e:
        print(f"Error adding doctor: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/api/doctors', methods=['GET'])
def get_doctors():
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Προβολή: Μόνο βασικά στοιχεία για τη λίστα
        projection = {
            "_id": 1,
            "personal_details.first_name": 1,
            "personal_details.last_name": 1,
            "personal_details.specialty": 1,
            "availability_status": 1
        }
        
        # Μέτρηση συνόλου γιατρών
        total_doctors = db.doctors.count_documents({})
        
        # Ανάκτηση δεδομένων (προς το παρόν χωρίς pagination/sort)
        doctors_cursor = db.doctors.find({}, projection)
        doctors_list = []
        for doctor in doctors_cursor:
            # Μετονομάζουμε _id σε id
            doctor['id'] = str(doctor.pop('_id')) 
            doctors_list.append(doctor)

        # Δημιουργία response και προσθήκη header
        resp = make_response(jsonify(doctors_list), 200)
        if total_doctors > 0:
            resp.headers['Content-Range'] = f'doctors 0-{total_doctors-1}/{total_doctors}'
        else:
            resp.headers['Content-Range'] = f'doctors 0-0/0'
        return resp

    except Exception as e:
        print(f"Error fetching doctors list: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/api/doctors/me/status', methods=['PATCH'])
@jwt_required()
def update_my_availability():
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    # Παίρνουμε την ταυτότητα (doctor ID) από το JWT token
    current_user_id_str = get_jwt_identity()
    try:
        doctor_object_id = ObjectId(current_user_id_str) 
        except InvalidId:
         # Αυτό δεν θα έπρεπε να συμβεί αν το token είναι έγκυρο
         return jsonify({"error": "Invalid doctor ID in token"}), 401 
    
    try:
        data = request.get_json()
        # ... (υπόλοιπος κώδικας παραμένει ίδιος: έλεγχος status, update στη βάση) ...
        if not data or 'status' not in data:
            return jsonify({"error": "Request body must be JSON and contain 'status' field"}), 400
            
        new_status = data['status']
        allowed_statuses = ['available', 'unavailable', 'busy']
        if new_status not in allowed_statuses:
            return jsonify({"error": f"Invalid status. Allowed statuses: {allowed_statuses}"}), 400

        # Ενημέρωση μόνο του availability_status και του last_updated_at
        update_payload = {
            "$set": { "availability_status": new_status },
            "$currentDate": { "last_updated_at": True }
        }

        result = db.doctors.update_one({"_id": doctor_object_id}, update_payload)

        if result.matched_count == 0:
             # Αυτό σημαίνει ότι το ID από το (υποτιθέμενο) token δεν βρέθηκε στη βάση
            return jsonify({"error": "Doctor not found (invalid token?)"}), 404 
        else:
            return jsonify({"message": f"Availability updated to '{new_status}'"}), 200

    except Exception as e:
        print(f"Error updating availability for doctor {doctor_object_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/api/doctors/<string:doctor_id>', methods=['GET'])
@jwt_required() # <--- ΠΡΟΣΤΕΘΗΚΕ ΠΡΟΣΤΑΣΙΑ
def get_doctor_by_id(doctor_id):
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity() 
    is_self_request = (requesting_user_id_str == doctor_id)
             
        if db is None: 
            return jsonify({"error": "Database connection failed"}), 500
            
    try:
        object_id = ObjectId(doctor_id)
    except InvalidId:
        return jsonify({"error": "Invalid doctor ID format"}), 400

    try:
        # Αν ζητάει ο ίδιος ο γιατρός, φέρνουμε όλα τα πεδία (εκτός hash).
        # Αλλιώς, φέρνουμε μόνο τα δημόσια/μη ευαίσθητα πεδία.
        if is_self_request:
            projection = {"account_details.password_hash": 0} # Αφαίρεση μόνο του hash
        else:
            # Προβολή για άλλους χρήστες: Μόνο βασικά στοιχεία
            projection = {
                "_id": 1,
                "personal_details.first_name": 1,
                "personal_details.last_name": 1,
                "personal_details.specialty": 1,
                "availability_status": 1 # Ίσως και το status διαθεσιμότητας;
                # ΔΕΝ επιστρέφουμε account_details, managed_patients κλπ.
            }
            
        doctor = db.doctors.find_one({"_id": object_id}, projection)

        if doctor:
            # Γιατρός βρέθηκε
            # Μετατροπή _id σε id
            doctor['id'] = str(doctor.pop('_id')) # <--- Η διόρθωση
            
            if 'created_at' in doctor and isinstance(doctor['created_at'], datetime.datetime):
                doctor['created_at'] = doctor['created_at'].isoformat()
            if 'last_updated_at' in doctor and isinstance(doctor['last_updated_at'], datetime.datetime):
                doctor['last_updated_at'] = doctor['last_updated_at'].isoformat()
            
            # Μετατροπή managed_patients ΜΟΝΟ αν είναι self-request και υπάρχουν
            if is_self_request and 'managed_patients' in doctor and isinstance(doctor['managed_patients'], list):
                doctor['managed_patients'] = [str(patient_id) for patient_id in doctor['managed_patients'] if isinstance(patient_id, ObjectId)]
            
            # Αφαίρεση password hash (αν υπάρχει ακόμα μετά το projection - διπλός έλεγχος)
            if 'account_details' in doctor and 'password_hash' in doctor['account_details']:
                 del doctor['account_details']['password_hash']

            # Αφαίρεση ολόκληρου του account_details αν δεν είναι self-request
            if not is_self_request and 'account_details' in doctor:
                del doctor['account_details']


            return jsonify(doctor), 200
        else:
            # Γιατρός δεν βρέθηκε
            return jsonify({"error": "Doctor not found"}), 404

    except Exception as e:
        print(f"Error fetching doctor {doctor_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/api/doctors/<string:doctor_id>', methods=['PATCH'])
@jwt_required() # <--- ΠΡΟΣΤΕΘΗΚΕ ΠΡΟΣΤΑΣΙΑ
def update_doctor(doctor_id):
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity() 
    
    # --- Έλεγχος Εξουσιοδότησης: Μόνο ο ίδιος ο γιατρός ---
    if requesting_user_id_str != doctor_id:
        return jsonify({"error": "Unauthorized to modify this doctor's profile"}), 403
    # ----------------------------------------------------

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        object_id = ObjectId(doctor_id)
    except InvalidId:
        return jsonify({"error": "Invalid doctor ID format"}), 400

    try:
        update_data = request.get_json()
        if not update_data:
            return jsonify({"error": "Request body must be JSON and non-empty"}), 400

        # Απαγορεύουμε την αλλαγή του _id, created_at
        if '_id' in update_data: del update_data['_id']
        if 'created_at' in update_data: del update_data['created_at']
        # Απαγορεύουμε την αλλαγή username/password μέσω αυτού του endpoint
        if 'account_details' in update_data: del update_data['account_details'] 
        # Απαγορεύουμε την άμεση αλλαγή των managed_patients εδώ
        if 'managed_patients' in update_data: del update_data['managed_patients']

        # ---> ΝΕΑ ΓΡΑΜΜΗ: Αφαιρούμε το last_updated_at αν ήρθε από το frontend
        if 'last_updated_at' in update_data: del update_data['last_updated_at']

        # Αν δεν έμεινε τίποτα για update μετά τους περιορισμούς
        if not update_data:
             return jsonify({"error": "No updatable fields provided or fields not allowed for update via this endpoint"}), 400

        # Ενημέρωση του last_updated_at
        update_payload = {
            "$set": update_data,
            "$currentDate": { "last_updated_at": True }
        }

        result = db.doctors.update_one({"_id": object_id}, update_payload)

        if result.matched_count == 0:
            return jsonify({"error": "Doctor not found"}), 404
        elif result.modified_count == 0 and result.matched_count == 1:
             return jsonify({"message": "Doctor found but no changes applied"}), 200
        else:
            return jsonify({"message": "Doctor updated successfully"}), 200

    except Exception as e:
        print(f"Error updating doctor {doctor_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/api/doctors/<string:doctor_id>', methods=['DELETE'])
@jwt_required() # <--- ΠΡΟΣΤΕΘΗΚΕ ΠΡΟΣΤΑΣΙΑ
def delete_doctor(doctor_id):
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity() 
    
    # --- Έλεγχος Εξουσιοδότησης: Μόνο ο ίδιος ο γιατρός ---
    if requesting_user_id_str != doctor_id:
        return jsonify({"error": "Unauthorized to delete this doctor's profile"}), 403
    # ----------------------------------------------------

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        object_id = ObjectId(doctor_id)
    except InvalidId:
        return jsonify({"error": "Invalid doctor ID format"}), 400

    try:
        # Εκτέλεση της διαγραφής
        result = db.doctors.delete_one({"_id": object_id})

        if result.deleted_count == 1:
            # TODO: Πρέπει να αφαιρεθεί το doctor_id από τους assigned_doctors των ασθενών
            print(f"Warning: Doctor {doctor_id} deleted. Patients need to be updated.")
            return jsonify({"message": "Doctor deleted successfully"}), 200
        else:
            return jsonify({"error": "Doctor not found"}), 404

    except Exception as e:
        print(f"Error deleting doctor {doctor_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- CRUD Endpoints for Sessions --- 
@app.route('/api/sessions', methods=['POST'])
@jwt_required()
def add_session():
    current_doctor_id_str = get_jwt_identity()
    try:
        current_doctor_object_id = ObjectId(current_doctor_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid doctor ID in token"}), 401

    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # --- Βασική Επικύρωση Δεδομένων ---
        required_fields = ['patient_id', 'doctor_id', 'timestamp', 'session_type']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        patient_id_str = data['patient_id']
        # --- ΕΛΕΓΧΟΣ: Ο doctor_id που δίνεται πρέπει να είναι ο ίδιος με του token --- 
        doctor_id_from_data_str = data['doctor_id']
        if doctor_id_from_data_str != current_doctor_id_str:
            return jsonify({"error": "Cannot create session for another doctor"}), 403
        # --------------------------------------------------------------------------
        timestamp_str = data['timestamp']
        session_type = data['session_type']

        try:
            patient_object_id = ObjectId(patient_id_str)
            # doctor_object_id is already current_doctor_object_id
        except InvalidId:
            return jsonify({"error": "Invalid patient_id format"}), 400

        # --- Έλεγχος Εξουσιοδότησης: Ο γιατρός έχει πρόσβαση στον ασθενή; ---
        patient = db.patients.find_one({"_id": patient_object_id}, {"assigned_doctors": 1, "is_in_common_space": 1})
        if not patient: return jsonify({"error": f"Patient with id {patient_id_str} not found"}), 404
             
        is_assigned_doctor = current_doctor_object_id in patient.get('assigned_doctors', [])
        is_common_space = patient.get('is_in_common_space', False)
        
        # Allowed if assigned OR common space
        if not (is_assigned_doctor or is_common_space):
             return jsonify({"error": "Unauthorized to create session for this patient"}), 403
        # -----------------------------------------------------------------
        
        # Έλεγχος τύπου συνεδρίας και timestamp (όπως πριν)
        # ...

        # --- Προετοιμασία Εγγράφου Συνεδρίας --- 
        session_data = {
            "patient_id": patient_object_id, 
            "doctor_id": current_doctor_object_id, # Χρησιμοποιούμε το ID από το token
            "timestamp": timestamp_str,
            "session_type": session_type,
            "vitals_recorded": data.get('vitals_recorded', {}),
            "doctor_notes": data.get('doctor_notes', ''),
            "therapy_adjustments": data.get('therapy_adjustments', ''),
            "patient_reported_outcome": data.get('patient_reported_outcome', ''),
            "files_attached": data.get('files_attached', []),
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        }
        # Το last_updated_at θα είναι ίδιο με το created_at αρχικά
        session_data['last_updated_at'] = session_data['created_at']

        # --- Εισαγωγή στη Βάση Δεδομένων ---
        result = db.sessions.insert_one(session_data)
        inserted_id_str = str(result.inserted_id)

        return jsonify({
            "message": "Session added successfully",
            "session_id": inserted_id_str
        }), 201

    except Exception as e:
        print(f"Error adding session: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/api/sessions', methods=['GET'])
@jwt_required()
def get_sessions():
    request_user_id = get_jwt_identity()
    current_doctor_object_id = None
    try: 
        current_doctor_object_id = ObjectId(request_user_id)
    except InvalidId: return jsonify({"error": "Access denied. Doctor credentials required."}), 403
        
    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        target_patient_id_str = request.args.get('patient_id')
        query_filter = {}
        resource_name = 'sessions' # Default resource name for header
        
        if target_patient_id_str:
            try:
                target_patient_object_id = ObjectId(target_patient_id_str)
            except InvalidId: return jsonify({"error": "Invalid patient_id format"}), 400
            
            # ... (Έλεγχος Εξουσιοδότησης παραμένει ίδιος) ...
            patient = db.patients.find_one({"_id": target_patient_object_id}, {"assigned_doctors": 1, "is_in_common_space": 1})
            if not patient: return jsonify({"error": f"Patient not found"}), 404
            is_assigned = current_doctor_object_id in patient.get('assigned_doctors', [])
            is_common = patient.get('is_in_common_space', False)
            if not (is_assigned or is_common): return jsonify({"error": "Unauthorized"}), 403
            # ---------------------------------------------------------
            
            query_filter = {"patient_id": target_patient_object_id}
            print(f"Doctor {current_doctor_object_id} fetching sessions for specific patient {target_patient_object_id}")
        else:
            doctor = db.doctors.find_one({"_id": current_doctor_object_id}, {"managed_patients": 1})
            if not doctor: return jsonify({"error": "Doctor not found"}), 404 
            managed_patient_ids = doctor.get('managed_patients', [])
            if managed_patient_ids:
                query_filter = {"patient_id": {"$in": managed_patient_ids}} 
            else:
                # Αν δεν διαχειρίζεται ασθενείς, επιστρέφουμε κενή λίστα με σωστό header
                resp = make_response(jsonify([]), 200)
                resp.headers['Content-Range'] = f'{resource_name} 0-0/0'
                return resp
            print(f"Doctor {current_doctor_object_id} fetching sessions for all managed patients.")

        # Μέτρηση συνόλου *με βάση το φίλτρο*
        total_sessions = db.sessions.count_documents(query_filter)

        # Εκτέλεση query με το κατάλληλο φίλτρο (προς το παρόν χωρίς pagination/sort)
        sessions_cursor = db.sessions.find(query_filter).sort("timestamp", -1)
        
        sessions_list = []
        for session in sessions_cursor:
            # Μετονομάζουμε _id σε id
            session['id'] = str(session.pop('_id')) 
            session['patient_id'] = str(session['patient_id'])
            if 'doctor_id' in session: session['doctor_id'] = str(session['doctor_id'])
            # ... (άλλες μετατροπές timestamps παραμένουν ίδιες) ...
            if 'timestamp' in session and isinstance(session['timestamp'], datetime.datetime):
                session['timestamp'] = session['timestamp'].isoformat()
            if 'created_at' in session and isinstance(session['created_at'], datetime.datetime):
                session['created_at'] = session['created_at'].isoformat()
            if 'last_updated_at' in session and isinstance(session['last_updated_at'], datetime.datetime):
                session['last_updated_at'] = session['last_updated_at'].isoformat()
            sessions_list.append(session)

        # Δημιουργία response και προσθήκη header
        resp = make_response(jsonify(sessions_list), 200)
        if total_sessions > 0:
            resp.headers['Content-Range'] = f'{resource_name} 0-{total_sessions-1}/{total_sessions}'
        else:
            resp.headers['Content-Range'] = f'{resource_name} 0-0/0'
        return resp

    except Exception as e:
        print(f"Error fetching sessions for doctor {current_doctor_object_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/api/sessions/<string:session_id>', methods=['GET'])
@jwt_required()
def get_session_by_id(session_id):
    request_user_id = get_jwt_identity()
    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        session_object_id = ObjectId(session_id)
    except InvalidId: return jsonify({"error": "Invalid session ID format"}), 400

    try:
        session = db.sessions.find_one({"_id": session_object_id})
        if not session: return jsonify({"error": "Session not found"}), 404

        session_patient_id = session.get("patient_id")
        if not session_patient_id: return jsonify({"error": "Session data incomplete"}), 500

        # --- Έλεγχος Εξουσιοδότησης (Γιατρός ή ο Ασθενής της Συνεδρίας) --- 
        is_session_patient = (request_user_id == str(session_patient_id))
        is_authorized_doctor = False
        current_doctor_object_id = None
        try: 
            current_doctor_object_id = ObjectId(request_user_id)
        except InvalidId: pass # Not a doctor ID

        if current_doctor_object_id:
            patient = db.patients.find_one({"_id": session_patient_id}, {"assigned_doctors": 1, "is_in_common_space": 1})
            if patient:
                is_assigned_doctor = current_doctor_object_id in patient.get('assigned_doctors', [])
                is_common_space = patient.get('is_in_common_space', False)
                if is_assigned_doctor or is_common_space:
                    is_authorized_doctor = True
            else: # Should not happen
                 return jsonify({"error": "Patient associated with session not found"}), 404
                     
        # Allowed if patient owns session OR doctor is authorized (assigned or common space)
        if not (is_session_patient or is_authorized_doctor):
             return jsonify({"error": "Unauthorized to access this session"}), 403
        # ----------------------------- 

        # ... (Convert IDs/Timestamps and return session) ...
        session['_id'] = str(session['_id'])
        # ... (μετατροπές patient_id, doctor_id, timestamp, created_at, last_updated_at)

        return jsonify(session), 200
    except Exception as e:
        print(f"Error fetching session {session_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/api/sessions/<string:session_id>', methods=['PATCH'])
@jwt_required()
def update_session(session_id):
    current_doctor_id_str = get_jwt_identity()
    try:
        current_doctor_object_id = ObjectId(current_doctor_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid doctor ID in token"}), 401
        
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        session_object_id = ObjectId(session_id)
    except InvalidId:
        return jsonify({"error": "Invalid session ID format"}), 400

    # --- Έλεγχος Εξουσιοδότησης --- 
    # Βρίσκουμε τη συνεδρία και το ID του ασθενή της
    session = db.sessions.find_one({"_id": session_object_id}, {"patient_id": 1})
    if not session:
         return jsonify({"error": "Session not found"}), 404
    session_patient_id = session.get("patient_id") # Αυτό είναι ObjectId
    if not session_patient_id:
         return jsonify({"error": "Session data incomplete"}), 500
    
    # Βρίσκουμε τον ασθενή για να δούμε τους γιατρούς του
    patient = db.patients.find_one({"_id": session_patient_id}, {"assigned_doctors": 1})
    if not patient:
         # Περίεργο αν η συνεδρία υπάρχει αλλά ο ασθενής όχι...
         return jsonify({"error": "Patient associated with session not found"}), 404
    if current_doctor_object_id not in patient.get('assigned_doctors', []):
         return jsonify({"error": "Unauthorized to modify this session"}), 403
    # ----------------------------- 

    try:
        update_data = request.get_json()
        if not update_data:
            return jsonify({"error": "Request body must be JSON and non-empty"}), 400

        # Απαγορεύουμε την αλλαγή κρίσιμων αναγνωριστικών ή του αρχικού timestamp
        if '_id' in update_data:
            del update_data['_id']
        if 'patient_id' in update_data:
            del update_data['patient_id']
        if 'doctor_id' in update_data:
            del update_data['doctor_id']
        if 'timestamp' in update_data:
            del update_data['timestamp']
        if 'created_at' in update_data:
            del update_data['created_at']

        # Έλεγχος για session_type αν επιχειρείται αλλαγή
        if 'session_type' in update_data:
            allowed_session_types = ["telemedicine", "in_person", "data_review", "note"]
            if update_data['session_type'] not in allowed_session_types:
                 return jsonify({"error": f"Invalid session_type. Allowed types: {allowed_session_types}"}), 400

        # Ενημέρωση του last_updated_at
        update_payload = {
            "$set": update_data,
            "$currentDate": { "last_updated_at": True }
        }

        result = db.sessions.update_one({"_id": session_object_id}, update_payload)

        if result.matched_count == 0:
            return jsonify({"error": "Session not found"}), 404
        elif result.modified_count == 0 and result.matched_count == 1:
             return jsonify({"message": "Session found but no changes applied"}), 200
        else:
            return jsonify({"message": "Session updated successfully"}), 200

    except Exception as e:
        print(f"Error updating session {session_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@app.route('/api/sessions/<string:session_id>', methods=['DELETE'])
@jwt_required()
def delete_session(session_id):
    current_doctor_id_str = get_jwt_identity()
    try:
        current_doctor_object_id = ObjectId(current_doctor_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid doctor ID in token"}), 401
        
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        session_object_id = ObjectId(session_id)
    except InvalidId:
        return jsonify({"error": "Invalid session ID format"}), 400

    # --- Έλεγχος Εξουσιοδότησης --- 
    session = db.sessions.find_one({"_id": session_object_id}, {"patient_id": 1})
    if not session:
         return jsonify({"error": "Session not found"}), 404
    session_patient_id = session.get("patient_id")
    if not session_patient_id:
         return jsonify({"error": "Session data incomplete"}), 500
         
    patient = db.patients.find_one({"_id": session_patient_id}, {"assigned_doctors": 1})
    if not patient:
         return jsonify({"error": "Patient associated with session not found"}), 404
    if current_doctor_object_id not in patient.get('assigned_doctors', []):
         return jsonify({"error": "Unauthorized to delete this session"}), 403
    # ----------------------------- 

    try:
        result = db.sessions.delete_one({"_id": session_object_id})
        # ... (rest of delete logic)

    except Exception as e:
        print(f"Error deleting session {session_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- File Endpoints (Doctor Access) --- 
@app.route('/api/patients/<string:patient_id>/files', methods=['POST'])
@jwt_required()
def upload_patient_file(patient_id):
    print(f"--- DEBUG: Inside upload_patient_file (for /<id>/files) with id: {patient_id} ---") # <--- ΚΑΤΑΣΚΟΠΟΣ 2
    current_doctor_id_str = get_jwt_identity()
    try:
        current_doctor_object_id = ObjectId(current_doctor_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid doctor ID in token"}), 401
        
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id)
    except InvalidId:
        return jsonify({"error": "Invalid patient ID format"}), 400

    # --- Έλεγχος Εξουσιοδότησης --- 
    patient = db.patients.find_one({"_id": patient_object_id}, {"assigned_doctors": 1, "is_in_common_space": 1}) 
    if not patient: return jsonify({"error": "Patient not found"}), 404
    
    is_assigned_doctor = current_doctor_object_id in patient.get('assigned_doctors', [])
    is_common_space = patient.get('is_in_common_space', False)
    
    # Allowed if assigned OR common space
    if not (is_assigned_doctor or is_common_space):
         return jsonify({"error": "Unauthorized to upload files for this patient"}), 403
    # ----------------------------- 

    # Έλεγχος αν στάλθηκε αρχείο στο request
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files['file']

    # Έλεγχος αν επιλέχθηκε αρχείο
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        # Δημιουργία ασφαλούς ονόματος αρχείου
        original_filename = secure_filename(file.filename)
        # Προαιρετικά: Προσθήκη timestamp ή UUID στο όνομα για μοναδικότητα
        # filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{original_filename}"
        filename = original_filename # Προς το παρόν κρατάμε το ασφαλές αρχικό όνομα

        # Δημιουργία φακέλου για τον ασθενή αν δεν υπάρχει
        patient_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], patient_id)
        os.makedirs(patient_upload_folder, exist_ok=True)

        # Αποθήκευση του αρχείου
        file_path = os.path.join(patient_upload_folder, filename)
        try:
            file.save(file_path)
        except Exception as e:
             print(f"Error saving file: {e}")
             return jsonify({"error": "Failed to save file on server"}), 500

        # Λήψη τύπου αρχείου (MIME type)
        mime_type, _ = mimetypes.guess_type(file_path)

        # Δημιουργία εγγραφής για τη βάση δεδομένων
        file_metadata = {
            "file_id": str(ObjectId()), # Δίνουμε ένα νέο μοναδικό ID και στο αρχείο
            "filename": filename, # Το ασφαλές όνομα αρχείου
            "original_filename": original_filename, # Το αρχικό όνομα (για εμφάνιση ίσως)
            "file_path": file_path.replace(app.config['UPLOAD_FOLDER'], '').lstrip(os.sep), # Σχετική διαδρομή από τον φάκελο uploads
            "mime_type": mime_type or 'application/octet-stream',
            "upload_date": datetime.datetime.now(datetime.timezone.utc),
            "size_bytes": os.path.getsize(file_path),
            "extracted_text": None # Placeholder για το OCR κείμενο
        }

        # Ενημέρωση του ασθενή στη βάση (προσθήκη στη λίστα uploaded_files)
        update_result = db.patients.update_one(
            {"_id": patient_object_id},
            {
                "$push": { "uploaded_files": file_metadata },
                "$currentDate": { "last_updated_at": True }
            }
        )

        if update_result.modified_count == 1:
             # --- ΕΚΤΕΛΕΣΗ OCR ΜΕΤΑ ΤΗΝ ΕΠΙΤΥΧΗ ΑΠΟΘΗΚΕΥΣΗ --- 
            ocr_text = "[OCR not attempted or failed]" # Default τιμή
            # Ελέγχουμε αν είναι PDF για να κάνουμε OCR
            if file_metadata['mime_type'] == 'application/pdf':
                 print(f"Attempting OCR for file: {file_path}")
                 # Χρησιμοποιούμε την πλήρη διαδρομή για το OCR
                 absolute_file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_metadata['file_path'])
                 ocr_text = extract_text_from_pdf(absolute_file_path)
                 print(f"OCR finished for {filename}. Extracted ~{len(ocr_text)} chars.")
                 # Ενημέρωση της εγγραφής του αρχείου στη βάση με το κείμενο OCR
                 db.patients.update_one(
                     {"_id": patient_object_id, "uploaded_files.file_id": file_metadata["file_id"]},
                     {"$set": { "uploaded_files.$.extracted_text": ocr_text } }
                 )
                 print(f"Updated DB record for file {file_metadata['file_id']} with OCR text.")
            else:
                 print(f"Skipping OCR for non-PDF file: {filename} (MIME: {file_metadata['mime_type']})")
            # -----------------------------------------------------

            return jsonify({
                "message": "File uploaded successfully",
                "file_info": {
                    "file_id": file_metadata["file_id"],
                    "filename": filename,
                    "mime_type": file_metadata["mime_type"],
                    "ocr_status": "Processed" if file_metadata['mime_type'] == 'application/pdf' else "Skipped (not PDF)"
                }
            }), 201
        else:
            # Προσπάθεια καθαρισμού αν η ενημέρωση της βάσης απέτυχε;
            try:
                os.remove(file_path)
            except OSError as e:
                print(f"Error removing file after DB update failure: {e}")
            return jsonify({"error": "Failed to update patient record with file info"}), 500

    else:
        # Μη επιτρεπτός τύπος αρχείου
        return jsonify({"error": f"File type not allowed. Allowed types: {list(ALLOWED_EXTENSIONS)}"}), 400

    # Fallback για απρόβλεπτα σφάλματα
    return jsonify({"error": "An unexpected error occurred during file upload"}), 500

@app.route('/api/files/<string:patient_id>/<string:file_id>', methods=['GET'])
@jwt_required()
def get_uploaded_file(patient_id, file_id):
    request_user_id = get_jwt_identity()
    current_doctor_object_id = None
    is_requesting_patient = False
    try: 
        current_doctor_object_id = ObjectId(request_user_id) # Check if requester is a doctor
    except InvalidId:
        # Could be the patient requesting their own file
        if request_user_id == patient_id:
             is_requesting_patient = True
        else: # Invalid token if not ObjectID and not matching patient ID
             return jsonify({"error": "Invalid token or unauthorized access"}), 401

    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id)
    except InvalidId: return jsonify({"error": "Invalid patient ID format"}), 400
    
    try:
        # Fetch patient data needed for auth check + file metadata
        patient = db.patients.find_one(
            {"_id": patient_object_id, "uploaded_files.file_id": file_id},
            {"uploaded_files.$": 1, "assigned_doctors": 1, "is_in_common_space": 1}
        )
        if not patient or 'uploaded_files' not in patient or not patient['uploaded_files']:
            return jsonify({"error": "File not found for this patient"}), 404

        file_metadata = patient['uploaded_files'][0]

        # --- Έλεγχος Εξουσιοδότησης (Γιατρός ή ο Ασθενής του αρχείου) --- 
        is_authorized_doctor = False
        if current_doctor_object_id: # If requester is potentially a doctor
            is_assigned_doctor = current_doctor_object_id in patient.get('assigned_doctors', [])
            is_common_space = patient.get('is_in_common_space', False)
            if is_assigned_doctor or is_common_space:
                is_authorized_doctor = True
        
        # Allowed if patient owns file OR doctor is authorized
        if not (is_requesting_patient or is_authorized_doctor):
             return jsonify({"error": "Unauthorized to access this file"}), 403
        # ----------------------------- 

        # ... (rest of file serving logic: get filename, check path, send_from_directory) ...
        relative_file_path = file_metadata.get('file_path')
        stored_filename = file_metadata.get('filename') # Το όνομα όπως αποθηκεύτηκε

        if not relative_file_path or not stored_filename:
             print(f"Error: Missing file_path or filename in metadata for file_id {file_id}")
             return jsonify({"error": "File metadata incomplete"}), 500
        
        # Η διαδρομή στο metadata είναι ήδη σχετική με τον φάκελο uploads/<patient_id>
        # Το send_from_directory θέλει τη διαδρομή *μέσα* στον κατάλογο που του ορίζουμε.
        # Οπότε, ο κατάλογος είναι uploads/patient_id και το αρχείο είναι το filename.
        directory = os.path.join(app.config['UPLOAD_FOLDER'], patient_id)
        
        # Έλεγχος αν ο φάκελος και το αρχείο όντως υπάρχουν στον δίσκο
        absolute_directory_path = os.path.abspath(directory)
        absolute_file_path = os.path.join(absolute_directory_path, stored_filename)
        
        if not os.path.exists(absolute_file_path):
            print(f"Error: File not found on disk: {absolute_file_path}")
            return jsonify({"error": "File not found on server storage"}), 404

        # Χρήση send_from_directory για ασφαλή αποστολή
        # as_attachment=False προσπαθεί να το δείξει ο browser (αν μπορεί πχ PDF/Image)
        # as_attachment=True θα πρότεινε πάντα λήψη (download)
        return send_from_directory(directory=absolute_directory_path, 
                                   path=stored_filename, 
                                   as_attachment=False) 

    except Exception as e:
        print(f"Error fetching file {file_id} for patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint for Deleting a Specific File ---
@app.route('/api/files/<string:patient_id>/<string:file_id>', methods=['DELETE'])
@jwt_required()
def delete_uploaded_file(patient_id, file_id):
    request_user_id = get_jwt_identity()
    current_doctor_object_id = None
    is_requesting_patient = False
    try: 
        current_doctor_object_id = ObjectId(request_user_id)
    except InvalidId:
        if request_user_id == patient_id:
            is_requesting_patient = True
        else:
            return jsonify({"error": "Invalid token or unauthorized file deletion attempt"}), 401

    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id)
    except InvalidId: return jsonify({"error": "Invalid patient ID format"}), 400

    try:
        # Find the patient and check if the file exists
        patient = db.patients.find_one(
            {"_id": patient_object_id, "uploaded_files.file_id": file_id},
            {"uploaded_files.$": 1, "assigned_doctors": 1, "is_in_common_space": 1} 
        )
        if not patient or 'uploaded_files' not in patient or not patient['uploaded_files']:
            return jsonify({"error": "File not found for this patient"}), 404

        file_metadata = patient['uploaded_files'][0]
        stored_filename = file_metadata.get('filename')

        # --- Authorization Check --- 
        is_authorized_doctor = False
        if current_doctor_object_id: # If requester is potentially a doctor
            is_assigned_doctor = current_doctor_object_id in patient.get('assigned_doctors', [])
            is_common_space = patient.get('is_in_common_space', False)
            # Delete allowed only by assigned doctor OR the patient themselves
            if is_assigned_doctor:
                is_authorized_doctor = True
        
        if not (is_requesting_patient or is_authorized_doctor):
             return jsonify({"error": "Unauthorized to delete this file (only assigned doctor or owner)"}), 403
        # -------------------------

        # 1. Remove file metadata from MongoDB patient record
        update_result = db.patients.update_one(
            {"_id": patient_object_id},
            {"$pull": { "uploaded_files": { "file_id": file_id } } }
        )

        if update_result.modified_count == 1:
            print(f"Removed file metadata {file_id} from patient {patient_id}'s record.")
            # 2. Delete the actual file from the filesystem
            if stored_filename:
                try:
                    directory = os.path.join(app.config['UPLOAD_FOLDER'], patient_id)
                    absolute_file_path = os.path.abspath(os.path.join(directory, stored_filename))
                    if os.path.exists(absolute_file_path):
                        os.remove(absolute_file_path)
                        print(f"Deleted file from disk: {absolute_file_path}")
                    else:
                        print(f"Warning: File not found on disk, but metadata removed: {absolute_file_path}")
                except OSError as e:
                    # Log error but continue since DB entry is removed
                    print(f"Error deleting file from disk {absolute_file_path}: {e}") 
            else:
                 print(f"Warning: Filename missing in metadata for file_id {file_id}. Cannot delete from disk.")
                 
            return jsonify({"message": "File deleted successfully"}), 200
        else:
             # This might happen if the file_id was wrong despite the initial find_one check
             # or a race condition. 
             print(f"Failed to remove file metadata {file_id} from patient {patient_id}. modified_count=0")
             return jsonify({"error": "Failed to update patient record to remove file info"}), 500

    except Exception as e:
        print(f"Error deleting file {file_id} for patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred during file deletion"}), 500

# --- Endpoint for Updating a File's Tag --- 
@app.route('/api/files/<string:patient_id>/<string:file_id>/tag', methods=['PATCH'])
@jwt_required()
def update_file_tag(patient_id, file_id):
    request_user_id = get_jwt_identity()
    current_doctor_object_id = None
    is_requesting_patient = False
    try: 
        current_doctor_object_id = ObjectId(request_user_id)
    except InvalidId:
        if request_user_id == patient_id:
            is_requesting_patient = True
        else:
            return jsonify({"error": "Invalid token or unauthorized tag update"}), 401

    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id)
    except InvalidId: return jsonify({"error": "Invalid patient ID format"}), 400

    try:
        update_data = request.get_json()
        if not update_data or 'tag' not in update_data:
            return jsonify({"error": "Request body must be JSON and contain 'tag' field"}), 400
        new_tag = update_data['tag']
        # Προαιρετικά: validation του tag (π.χ. μήκος, χαρακτήρες)

        # Find the patient to check authorization and if the file exists
        patient = db.patients.find_one(
            {"_id": patient_object_id, "uploaded_files.file_id": file_id},
            {"uploaded_files.$": 1, "assigned_doctors": 1, "is_in_common_space": 1} 
        )
        if not patient or 'uploaded_files' not in patient or not patient['uploaded_files']:
            return jsonify({"error": "File not found for this patient"}), 404

        # --- Authorization Check (Same as delete: Only assigned doctor or owner) --- 
        is_authorized_doctor = False
        if current_doctor_object_id: 
            is_assigned_doctor = current_doctor_object_id in patient.get('assigned_doctors', [])
            # is_common_space = patient.get('is_in_common_space', False) # Common space doctors cannot change tags?
            if is_assigned_doctor:
                is_authorized_doctor = True
        
        if not (is_requesting_patient or is_authorized_doctor):
             return jsonify({"error": "Unauthorized to update tag for this file (only assigned doctor or owner)"}), 403
        # --------------------------------------------------------------------

        # Update the tag for the specific file within the uploaded_files array
        update_result = db.patients.update_one(
            {"_id": patient_object_id, "uploaded_files.file_id": file_id},
            {
                "$set": { "uploaded_files.$.tag": new_tag },
                "$currentDate": { "last_updated_at": True } # Ενημέρωση και του ασθενή
            }
        )

        if update_result.matched_count == 0:
             # Should not happen if the initial find_one worked
             return jsonify({"error": "File not found during update"}), 404
        elif update_result.modified_count == 1:
            return jsonify({"message": "File tag updated successfully"}), 200
        else:
             # Tag was likely already the same
             return jsonify({"message": "File tag unchanged"}), 200

    except Exception as e:
        print(f"Error updating tag for file {file_id} of patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred during tag update"}), 500

# --- Βοηθητική συνάρτηση OCR ---
def extract_text_from_pdf(pdf_path):
    """Εξάγει κείμενο από ένα αρχείο PDF χρησιμοποιώντας PyMuPDF και καλώντας απευθείας το Tesseract."""
    full_text = ""
    # tessdata_dir = r"C:\Users\Panos\OneDrive\Υπολογιστής\Tesseract-OCR\tessdata" # Δεν το χρειαζόμαστε πια εδώ
    tesseract_dir = os.path.dirname(TESSERACT_CMD) # Παίρνουμε τον φάκελο του tesseract.exe
    tessdata_path = os.path.join(tesseract_dir, 'tessdata') # <-- Κατασκευάζουμε τη διαδρομή προς το tessdata
    
    # --- Ορισμός TESSDATA_PREFIX (Δείχνει απευθείας στο tessdata) --- 
    os.environ['TESSDATA_PREFIX'] = tessdata_path # <-- Αλλαγή: Δείχνει στο tessdata
    print(f"[OCR Setup] Setting TESSDATA_PREFIX='{tessdata_path}'") # Debug log
    # -------------------------------

    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")

            try:
                # Προετοιμασία της εντολής tesseract (ΧΩΡΙΣ --tessdata-dir)
                command = [
                    TESSERACT_CMD,    # Η διαδρομή του tesseract.exe
                    'stdin',        # Είσοδος από stdin
                    'stdout',       # Έξοδος σε stdout
                    '-l', 'eng+ell', # Γλώσσες
                    '--psm', '3'     # Page Segmentation Mode (default)
                    # '--tessdata-dir', tessdata_dir # ΑΦΑΙΡΟΥΜΕ ΑΥΤΗ ΤΗ ΓΡΑΜΜΗ
                ]
                
                # Εκτέλεση της εντολής με subprocess
                # Περνάμε το ενημερωμένο περιβάλλον (αν και το os.environ το αλλάζει global)
                result = subprocess.run(
                    command, 
                    input=img_bytes, 
                    capture_output=True, 
                    check=False, # Δεν θέλουμε να πετάξει exception αν το tesseract δώσει error code
                    env=os.environ # Περνάμε το τρέχον περιβάλλον
                )

                # Έλεγχος για σφάλματα από το tesseract
                if result.returncode != 0:
                    # Προσπάθεια αποκωδικοποίησης του stderr για να δούμε το σφάλμα
                    try:
                        stderr_output = result.stderr.decode('utf-8', errors='replace')
                    except Exception:
                        stderr_output = "(Could not decode stderr)"
                    print(f"Tesseract command failed on page {page_num + 1} with error code {result.returncode}: {stderr_output}")
                    page_text = f"[Tesseract Execution Error on page {page_num + 1}]\n"
                else:
                    # Επιτυχής εκτέλεση, αποκωδικοποίηση stdout με χειρισμό σφαλμάτων
                    page_text = result.stdout.decode('utf-8', errors='replace')

                full_text += page_text + "\n\n--- Page Break ---\n\n"

            except FileNotFoundError:
                 print(f"TESSERACT NOT FOUND at: {TESSERACT_CMD}. OCR failed for page {page_num + 1}.")
                 full_text += f"[OCR Error: Tesseract executable not found for page {page_num + 1}]\n"
            except Exception as subproc_err:
                 print(f"Subprocess error on page {page_num + 1}: {subproc_err}")
                 full_text += f"[OCR Subprocess Error on page {page_num + 1}: {subproc_err}]\n"

        doc.close()
        return full_text
    except Exception as e:
        print(f"Error opening or processing PDF {pdf_path}: {e}")
        return f"[Error processing PDF: {e}]"

# --- Βοηθητική συνάρτηση για context (μπορεί να μεγαλώσει) ---
def format_patient_context(patient_data, sessions_data, file_texts):
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
             # --- Σαφής αναφορά ονόματος/ημερομηνίας --- 
             context_str += f"\n--- File {i+1}: {file_info['filename']} (Uploaded: {file_info['upload_date']}) ---\n"
             # -----------------------------------------
             # Αφαίρεση ορίου χαρακτήρων (προς το παρόν)
             # max_chars = 5000 
             # preview_text = (file_info['text'][:max_chars] + '...') if len(file_info['text']) > max_chars else file_info['text']
             full_file_text = file_info['text'] # Παίρνουμε όλο το κείμενο
             context_str += f"{full_file_text}\n--- End of File {i+1} ---"
             # -----------------------------

    context_str += "\n===================\n"
    return context_str

# --- Endpoint για ανάκτηση λίστας όλων των ασθενών
@app.route('/api/patients', methods=['GET'])
# @jwt_required() # Προσωρινά αφαιρούμε την προστασία για ευκολία στο testing
def get_patients():
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # --- Διαχείριση Φίλτρων --- 
        query_filter = {}
        filter_param = request.args.get('filter')
        if filter_param:
            try:
                parsed_filter = json.loads(filter_param)
                # --- ΣΩΣΤΟΣ Χειρισμός AMKA Filter (Τελική Προσπάθεια!) --- 
                if 'personal_details' in parsed_filter and isinstance(parsed_filter['personal_details'], dict) and 'amka' in parsed_filter['personal_details']:
                    amka_value = parsed_filter['personal_details']['amka']
                    if amka_value:
                         # Δημιουργούμε το query με dot notation
                         query_filter['personal_details.amka'] = amka_value
                    # Αφαιρούμε το personal_details από το parsed για να μην μπλεχτεί με άλλα φίλτρα
                    del parsed_filter['personal_details'] 
                # -----------------------------------------------------
                # Προσθέτουμε τυχόν άλλα φίλτρα (αν υπήρχαν)
                query_filter.update(parsed_filter)
                print(f"[get_patients] Applying filter: {query_filter}") # Debug
            except json.JSONDecodeError:
                print(f"[get_patients] Warning: Could not decode filter param: {filter_param}")
        # -------------------------

        # Πρώτα μετράμε το σύνολο των ασθενών *με το φίλτρο*
        total_patients = db.patients.count_documents(query_filter)

        # Μετά παίρνουμε τα δεδομένα *με το φίλτρο* (προς το παρόν χωρίς pagination/sort)
        patients_cursor = db.patients.find(query_filter)
        patients_list = []
        for patient in patients_cursor:
            # Μετατροπή _id
            patient['id'] = str(patient.pop('_id'));
            
            # Μετατροπή timestamps
            if 'created_at' in patient and isinstance(patient['created_at'], datetime.datetime):
                patient['created_at'] = patient['created_at'].isoformat()
            if 'last_updated_at' in patient and isinstance(patient['last_updated_at'], datetime.datetime):
                patient['last_updated_at'] = patient['last_updated_at'].isoformat()
                
            # Μετατροπή assigned_doctors
            if 'assigned_doctors' in patient and isinstance(patient['assigned_doctors'], list):
                patient['assigned_doctors'] = [str(doc_id) for doc_id in patient['assigned_doctors'] if isinstance(doc_id, ObjectId)]
                
            # Μετατροπή file_id και upload_date στα uploaded_files
            if 'uploaded_files' in patient and isinstance(patient['uploaded_files'], list):
                for file_meta in patient['uploaded_files']:
                    # Το file_id αποθηκεύεται ήδη ως string, αλλά καλό είναι να το ελέγχουμε
                    # if 'file_id' in file_meta and isinstance(file_meta['file_id'], ObjectId):
                    #     file_meta['file_id'] = str(file_meta['file_id'])
                    if 'upload_date' in file_meta and isinstance(file_meta['upload_date'], datetime.datetime):
                        file_meta['upload_date'] = file_meta['upload_date'].isoformat()
            
            # Αφαίρεση password hash!
            if 'account_details' in patient and 'password_hash' in patient['account_details']:
                 del patient['account_details']['password_hash']

            patients_list.append(patient)

        # Δημιουργία response και προσθήκη header
        resp = make_response(jsonify(patients_list), 200)
        # Προσαρμόζουμε το Content-Range ανάλογα με το αν υπάρχουν ασθενείς
        if total_patients > 0:
            resp.headers['Content-Range'] = f'patients 0-{total_patients-1}/{total_patients}'
        else:
            resp.headers['Content-Range'] = f'patients 0-0/0'
        return resp

    except Exception as e:
        print(f"Error fetching patients: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για ανάκτηση συγκεκριμένου ασθενή με βάση το ID του
@app.route('/api/patients/<string:patient_id>', methods=['GET'])
@jwt_required()
def get_patient_by_id(patient_id):
    request_user_id = get_jwt_identity()
    current_doctor_object_id = None
    is_requesting_patient = False
    try: 
        current_doctor_object_id = ObjectId(request_user_id)
    except InvalidId:
        # Not a doctor ID, check if it matches the patient ID being requested
        if request_user_id == patient_id:
            is_requesting_patient = True
        else:
            return jsonify({"error": "Invalid token or unauthorized access"}), 401

    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id)
    except InvalidId: return jsonify({"error": "Invalid patient ID format"}), 400

    try:
        # Fetch patient data, excluding password hash by default
        patient = db.patients.find_one({"_id": patient_object_id}, {"account_details.password_hash": 0})
        if not patient: return jsonify({"error": "Patient not found"}), 404

        # --- Έλεγχος Εξουσιοδότησης (Γιατρός ή ο ίδιος ο Ασθενής) ---
        is_authorized_doctor = False
        print(f"[AUTH CHECK] Requesting User ID: {request_user_id}") # DEBUG
        print(f"[AUTH CHECK] Patient ID: {patient_id}") # DEBUG
        print(f"[AUTH CHECK] Is Requesting Patient: {is_requesting_patient}") # DEBUG
        
        if current_doctor_object_id: # If requester is a doctor
            assigned_doctors_list = patient.get('assigned_doctors', [])
            is_common_space = patient.get('is_in_common_space', False)
            print(f"[AUTH CHECK] Current Doctor ObjectId: {current_doctor_object_id}") # DEBUG
            print(f"[AUTH CHECK] Patient Assigned Doctors: {assigned_doctors_list}") # DEBUG
            print(f"[AUTH CHECK] Is Common Space: {is_common_space}") # DEBUG
            
            is_assigned_doctor = current_doctor_object_id in assigned_doctors_list
            print(f"[AUTH CHECK] Is Assigned Doctor: {is_assigned_doctor}") # DEBUG
            
            if is_assigned_doctor or is_common_space:
                is_authorized_doctor = True
                print("[AUTH CHECK] Doctor IS authorized (assigned or common space).") # DEBUG
            else:
                 print("[AUTH CHECK] Doctor IS NOT authorized (not assigned and not common space).") # DEBUG
        else:
             print("[AUTH CHECK] Requester is not identified as a doctor.") # DEBUG

        if not (is_requesting_patient or is_authorized_doctor):
             print("[AUTH CHECK] FINAL DECISION: Unauthorized (403)") # DEBUG
             return jsonify({"error": "Unauthorized to access this patient"}), 403
        else:
             print("[AUTH CHECK] FINAL DECISION: Authorized (200)") # DEBUG
        # -----------------------------

        # Convert IDs/Timestamps
        patient['_id'] = str(patient['_id'])
        patient['id'] = str(patient.pop('_id')) # <--- Μετατρέπουμε και μετονομάζουμε σε id
        if 'created_at' in patient and isinstance(patient['created_at'], datetime.datetime):
             patient['created_at'] = patient['created_at'].isoformat()
        if 'last_updated_at' in patient and isinstance(patient['last_updated_at'], datetime.datetime):
             patient['last_updated_at'] = patient['last_updated_at'].isoformat()
        if 'assigned_doctors' in patient and isinstance(patient['assigned_doctors'], list):
            patient['assigned_doctors'] = [str(doc_id) for doc_id in patient['assigned_doctors'] if isinstance(doc_id, ObjectId)]
        if 'uploaded_files' in patient and isinstance(patient['uploaded_files'], list):
            for file_meta in patient['uploaded_files']:
                if 'upload_date' in file_meta and isinstance(file_meta['upload_date'], datetime.datetime):
                    file_meta['upload_date'] = file_meta['upload_date'].isoformat()
                # Do not include extracted_text here for GET patient by ID endpoint
                if 'extracted_text' in file_meta: del file_meta['extracted_text']
        
        # Remove account details if not requested by the patient themselves
        if not is_requesting_patient and 'account_details' in patient:
             del patient['account_details']

        return jsonify(patient), 200

    except Exception as e:
        print(f"Error fetching patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για μερική ενημέρωση (PATCH) ασθενή (ΜΟΝΟ από assigned doctor)
@app.route('/api/patients/<string:patient_id>', methods=['PATCH'])
@jwt_required()
def update_patient(patient_id):
    current_doctor_id_str = get_jwt_identity()
    try:
        current_doctor_object_id = ObjectId(current_doctor_id_str)
    except InvalidId: return jsonify({"error": "Invalid doctor ID in token"}), 401

    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id)
    except InvalidId: return jsonify({"error": "Invalid patient ID format"}), 400
        
    # --- Έλεγχος Εξουσιοδότησης ΠΡΙΝ την ενημέρωση (Μόνο assigned doctor) --- 
    patient = db.patients.find_one({"_id": patient_object_id}, {"assigned_doctors": 1})
    if not patient: return jsonify({"error": "Patient not found"}), 404
    
    if current_doctor_object_id not in patient.get('assigned_doctors', []):
         return jsonify({"error": "Unauthorized to modify this patient (only assigned doctors)"}), 403
    # ------------------------------------------------- 

    try:
        update_data = request.get_json()
        if not update_data: return jsonify({"error": "Request body must be JSON and non-empty"}), 400

        # Prevent critical/managed field updates (allow is_in_common_space)
        if '_id' in update_data: del update_data['_id']
        if 'created_at' in update_data: del update_data['created_at']
        if 'assigned_doctors' in update_data: del update_data['assigned_doctors'] # Managed via doctor assignment?
        if 'account_details' in update_data: del update_data['account_details'] # Managed via specific auth routes
        # Allow updating 'is_in_common_space' but validate it's boolean if present
        if 'is_in_common_space' in update_data and not isinstance(update_data['is_in_common_space'], bool):
            return jsonify({"error": "Invalid value for is_in_common_space, must be true or false"}), 400
        if 'last_updated_at' in update_data: del update_data['last_updated_at']
        if not update_data: return jsonify({"error": "No updatable fields provided or only non-updatable fields sent"}), 400 # Ενημερωμένο μήνυμα

        # Τώρα το update_payload δεν θα έχει conflict για το last_updated_at
        update_payload = {"$set": update_data, "$currentDate": { "last_updated_at": True }}
        result = db.patients.update_one({"_id": patient_object_id}, update_payload)

        if result.matched_count == 0: return jsonify({"error": "Patient not found"}), 404 # Should not happen
        elif result.modified_count == 0: return jsonify({"message": "Patient found but no changes applied"}), 200
        else: 
            # Optionally fetch and return updated patient data
            updated_patient = db.patients.find_one({"_id": patient_object_id}, {"account_details.password_hash": 0})
            if updated_patient: # Convert fields before returning
                 updated_patient['id'] = str(updated_patient.pop('_id')) # Μετονομασία _id σε id
                 if 'created_at' in updated_patient and isinstance(updated_patient['created_at'], datetime.datetime):
                     updated_patient['created_at'] = updated_patient['created_at'].isoformat()
                 if 'last_updated_at' in updated_patient and isinstance(updated_patient['last_updated_at'], datetime.datetime):
                     updated_patient['last_updated_at'] = updated_patient['last_updated_at'].isoformat()
                 if 'assigned_doctors' in updated_patient and isinstance(updated_patient['assigned_doctors'], list):
                     updated_patient['assigned_doctors'] = [str(doc_id) for doc_id in updated_patient['assigned_doctors'] if isinstance(doc_id, ObjectId)]
                 if 'uploaded_files' in updated_patient and isinstance(updated_patient['uploaded_files'], list):
                     for file_meta in updated_patient['uploaded_files']:
                         if 'upload_date' in file_meta and isinstance(file_meta['upload_date'], datetime.datetime):
                             file_meta['upload_date'] = file_meta['upload_date'].isoformat()
                         if 'extracted_text' in file_meta: del file_meta['extracted_text'] # Δεν το στέλνουμε πίσω
                 # Αφαίρεση account_details (εκτός αν το ζητάει ο ίδιος ο ασθενής, που εδώ δεν γίνεται)
                 if 'account_details' in updated_patient: del updated_patient['account_details']
                 # --------------------------------------------------------
                 return jsonify(updated_patient), 200
            else:
                 # Αυτό δεν θα έπρεπε να συμβεί αν το update πέτυχε
                 return jsonify({"message": "Patient updated successfully, but failed to fetch updated data"}), 200

    except Exception as e:
        print(f"Error updating patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για διαγραφή ασθενή (ΜΟΝΟ από assigned doctor)
@app.route('/api/patients/<string:patient_id>', methods=['DELETE'])
@jwt_required()
def delete_patient(patient_id):
    current_doctor_id_str = get_jwt_identity()
    try:
        current_doctor_object_id = ObjectId(current_doctor_id_str)
    except InvalidId: return jsonify({"error": "Invalid doctor ID in token"}), 401
        
    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id)
    except InvalidId: return jsonify({"error": "Invalid patient ID format"}), 400

    # --- Έλεγχος Εξουσιοδότησης ΠΡΙΝ τη διαγραφή (Μόνο assigned doctor) --- 
    patient = db.patients.find_one({"_id": patient_object_id}, {"assigned_doctors": 1})
    if not patient: return jsonify({"error": "Patient not found"}), 404
    
    if current_doctor_object_id not in patient.get('assigned_doctors', []):
         return jsonify({"error": "Unauthorized to delete this patient (only assigned doctors)"}), 403
    # ------------------------------------------------- 

    try:
        # TODO: Consider implications - remove files, sessions, doctor associations?
        result = db.patients.delete_one({"_id": patient_object_id})
        if result.deleted_count == 1:
            # Remove patient_id from the deleting doctor's managed_patients list
            db.doctors.update_one(
                {"_id": current_doctor_object_id},
                {"$pull": { "managed_patients": patient_object_id } }
            )
            print(f"Patient {patient_id} deleted. Associated data cleanup might be needed.")
            return jsonify({"message": "Patient deleted successfully"}), 200
        else:
            return jsonify({"error": "Patient not found"}), 404 # Should not happen

    except Exception as e:
        print(f"Error deleting patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint προσθήκης ασθενή από Γιατρό --- 
@app.route('/api/patients', methods=['POST'])
@jwt_required()
def add_patient():
    doctor_id_str = get_jwt_identity()
    try:
        doctor_object_id = ObjectId(doctor_id_str)
    except InvalidId: return jsonify({"error": "Invalid doctor ID in token"}), 401
        
    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Request body must be JSON"}), 400

        personal_details = data.get('personal_details')
        if not personal_details or not isinstance(personal_details, dict): 
            return jsonify({"error": "Missing or invalid 'personal_details'"}), 400
        required_personal = ['first_name', 'last_name', 'amka']
        if not all(k in personal_details and personal_details[k] for k in required_personal):
            return jsonify({"error": f"Missing required fields in personal_details: {required_personal}"}), 400
        
        # --- Έλεγχος Μοναδικότητας ΑΜΚΑ --- 
        amka_to_check = personal_details['amka']
        if db.patients.find_one({"personal_details.amka": amka_to_check}):
            return jsonify({"error": f"Patient with AMKA {amka_to_check} already exists"}), 409 # 409 Conflict
        # ----------------------------------

        # Validate is_in_common_space if provided
        is_common_space = data.get('is_in_common_space', False)
        if not isinstance(is_common_space, bool):
             return jsonify({"error": "Invalid value for is_in_common_space, must be true or false"}), 400

        # Check uniqueness if needed (e.g., AMKA)
        # if db.patients.find_one({"personal_details.amka": personal_details['amka']}):
        #     return jsonify({"error": "Patient with this AMKA already exists"}), 409

        patient_data = {
            "personal_details": personal_details,
            "medical_profile": data.get('medical_profile', {}),
            "is_in_common_space": is_common_space, # Use validated value
            "assigned_doctors": [doctor_object_id], # Assign creator doctor
            "uploaded_files": [],
            "cgm_integration": {"dexcom_status": "not_configured", "glooko_status": "not_configured"},
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        }
        patient_data['last_updated_at'] = patient_data['created_at']
        
        # Ensure defaults in medical profile if not provided
        patient_data['medical_profile'].setdefault('conditions', [])
        patient_data['medical_profile'].setdefault('allergies', [])
        patient_data['medical_profile'].setdefault('medical_history_summary', '')

        result = db.patients.insert_one(patient_data)
        inserted_id = result.inserted_id

        db.doctors.update_one( # Add patient to doctor's list
            {"_id": doctor_object_id},
            {"$addToSet": { "managed_patients": inserted_id } }
        )

        # Fetch the newly created patient to return it (excluding hash)
        new_patient = db.patients.find_one({"_id": inserted_id}, {"account_details": 0}) # Exclude account details
        if new_patient:
            # Convert ALL ObjectId and datetime fields before returning JSON
            new_patient['_id'] = str(new_patient['_id']) 
            if 'assigned_doctors' in new_patient and isinstance(new_patient['assigned_doctors'], list):
                new_patient['assigned_doctors'] = [str(doc_id) for doc_id in new_patient['assigned_doctors'] if isinstance(doc_id, ObjectId)]
            if 'created_at' in new_patient and isinstance(new_patient['created_at'], datetime.datetime):
                new_patient['created_at'] = new_patient['created_at'].isoformat()
            if 'last_updated_at' in new_patient and isinstance(new_patient['last_updated_at'], datetime.datetime):
                new_patient['last_updated_at'] = new_patient['last_updated_at'].isoformat()
            # Add conversions for any other potential ObjectId/datetime fields if needed

            return jsonify(new_patient), 201
        else:
             return jsonify({"message": "Patient added but failed to retrieve data", "patient_id": str(inserted_id)}), 201

    except Exception as e:
        print(f"Error adding patient: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- SocketIO Event Handlers for Signaling --- 

@socketio.on('connect')
def handle_connect():
    # --- Έλεγχος Ταυτότητας WebSocket με JWT --- 
    print(f"SocketIO connection attempt from {request.sid}")
    auth_token = request.args.get('token') # Παίρνουμε το token από τα query params

    if not auth_token:
        print(f"SocketIO connection rejected for {request.sid}: No token provided.")
        return False # Απόρριψη σύνδεσης (σημαντικό να επιστρέφει False)

    try:
        # Μη αυτόματη αποκωδικοποίηση και έλεγχος του token
        # Χρειαζόμαστε το SECRET_KEY που έχει ρυθμιστεί στην Flask app
        decoded_token = decode_token(auth_token)
        user_identity = decoded_token['sub'] # Η ταυτότητα (doctor/patient ID)
        
        # Έλεγχος αν η ταυτότητα είναι έγκυρη (π.χ. υπάρχει στη βάση; Προαιρετικό εδώ)
        # user = db.doctors.find_one({"_id": ObjectId(user_identity)}) or db.patients.find_one({"_id": ObjectId(user_identity)})
        # if not user:
        #     print(f"SocketIO connection rejected for {request.sid}: Invalid user identity in token.")
        #     return False

        # Αποθήκευση της ταυτότητας στη session του SocketIO
        session['user_identity'] = user_identity 
        print(f'Client connected: {request.sid}, User Identity: {user_identity}')
        # Η σύνδεση επιτρέπεται (δεν επιστρέφουμε τίποτα ή επιστρέφουμε True)
        
    except Exception as e: # Καλύπτει ληγμένα/άκυρα tokens κ.λπ.
         print(f"SocketIO connection rejected for {request.sid}: Invalid token ({e})")
         return False # Απόρριψη σύνδεσης

@socketio.on('disconnect')
def handle_disconnect():
    user_identity = session.get('user_identity', 'unknown')
    print(f'Client disconnected: {request.sid}, User Identity: {user_identity}')
    # Καθαρισμός session αν θέλουμε
    # session.pop('user_identity', None)
    # Εδώ θα μπορούσαμε να καθαρίσουμε δωμάτια αν χρειάζεται

@socketio.on('join_room')
def handle_join_room(data):
    room = data.get('room')
    user_sid = request.sid
    user_identity = session.get('user_identity') # Παίρνουμε την ταυτότητα από τη session

    if not user_identity:
        print(f"Rejecting join_room for {user_sid}: User not authenticated.")
        emit('error', {'message': 'Authentication required to join room.'}, room=user_sid)
        return

    if not room:
        print(f"Client {user_sid} (User: {user_identity}) tried to join without room name.")
        emit('error', {'message': 'Room name is required.'}, room=user_sid)
        return
        
    # --- Έλεγχος Εξουσιοδότησης --- 
    # TODO: Υλοποίηση λογικής ελέγχου: Επιτρέπεται ο user_identity να μπει στο room;
    # Παράδειγμα: Αν το room είναι session_id, έλεγξε αν ο χρήστης (γιατρός/ασθενής) σχετίζεται με τη συνεδρία.
    is_authorized = True # Placeholder - Πρέπει να γίνει πραγματικός έλεγχος!
    print(f"Authorization check for User: {user_identity}, Room: {room} -> Authorized: {is_authorized}") 
    # ----------------------------- 

    if is_authorized:
        join_room(room)
        print(f'Client {user_sid} (User: {user_identity}) joined room: {room}')
        # Ενημερώνουμε τους άλλους στο δωμάτιο (εκτός από τον εαυτό μας)
        emit('user_joined', {'sid': user_sid, 'userIdentity': user_identity}, room=room, include_self=False)
    else:
        print(f"Rejecting join_room for {user_sid} (User: {user_identity}) to room {room}: Not authorized.")
        emit('error', {'message': f'You are not authorized to join room {room}.'}, room=user_sid)


@socketio.on('leave_room')
def handle_leave_room(data):
    room = data.get('room')
    user_identity = session.get('user_identity', 'unknown')
    if room:
        leave_room(room)
        print(f'Client {request.sid} (User: {user_identity}) left room: {room}')
        # Ενημερώνουμε τους άλλους στο δωμάτιο
        emit('user_left', {'sid': request.sid, 'userIdentity': user_identity}, room=room, include_self=False)

# Τα παρακάτω είναι τα βασικά μηνύματα για WebRTC signaling
# Το 'data' που στέλνεται εδώ περιέχει συνήθως το SDP ή τον ICE candidate
# και πιθανόν ένα 'target_sid' για να ξέρουμε σε ποιον πάει το μήνυμα

@socketio.on('signal')
def handle_signal(data):
    target_sid = data.get('target_sid')
    room = data.get('room')
    signal_type = data.get('type') # π.χ., 'offer', 'answer', 'ice_candidate'
    payload = data.get('payload') # Το eigentliche SDP ή ICE candidate
    
    if target_sid:
        print(f"Relaying signal '{signal_type}' from {request.sid} to {target_sid}")
        # Στέλνουμε το σήμα ΜΟΝΟ στον συγκεκριμένο client (target_sid)
        emit('signal', {'type': signal_type, 'payload': payload, 'sender_sid': request.sid}, room=target_sid)
    elif room: # Αν δεν υπάρχει target_sid, στείλε σε όλους τους άλλους στο δωμάτιο (λιγότερο συνηθισμένο για signaling)
        print(f"Broadcasting signal '{signal_type}' from {request.sid} in room {room}")
        emit('signal', {'type': signal_type, 'payload': payload, 'sender_sid': request.sid}, room=room, include_self=False)
    else:
        print(f"Received signal from {request.sid} without target_sid or room.")

# --- Εκκίνηση Server --- 
if __name__ == '__main__':
    print("Starting Flask-SocketIO server (Reloader Enabled)...")
    # Η κλήση socketio.run() μπλοκάρει την εκτέλεση, οπότε την αφήνουμε μόνο στο τέλος του αρχείου
    # socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True)

# --- ΥΠΟΛΟΙΠΑ ENDPOINTS ΑΠΟ ΕΔΩ ΚΑΙ ΚΑΤΩ --- 

# --- Doctor Specific Protected Endpoints --- 
@app.route('/api/doctor-portal/patients', methods=['GET', 'OPTIONS'])
@cross_origin() # Handles CORS headers
def get_my_managed_patients_list():
    """Επιστρέφει τη λίστα των ασθενών που διαχειρίζεται ο συνδεδεμένος γιατρός."""
    
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        print("OPTIONS request received for /api/doctor-portal/patients, returning 204")
        response = make_response('', 204)
        # Δεν χρειάζεται να προσθέτουμε headers χειροκίνητα εδώ, το @cross_origin το κάνει
        return response

    # --- Proceed with GET logic --- 
    try:
        verify_jwt_in_request()
        current_doctor_id_str = get_jwt_identity()
        
        if not current_doctor_id_str:
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        try:
            current_doctor_object_id = ObjectId(current_doctor_id_str)
        except InvalidId:
            return jsonify({"error": "Invalid doctor ID format in token"}), 401

        if db is None: return jsonify({"error": "Database connection failed"}), 500

        doctor = db.doctors.find_one({"_id": current_doctor_object_id}, {"managed_patients": 1})
        if not doctor: return jsonify({"error": "Doctor not found"}), 404 
            
        managed_patient_ids = doctor.get('managed_patients', [])
        
        # --- Διορθωμένη Διαχείριση Φίλτρων --- 
        query_filter = {"_id": {"$in": managed_patient_ids}} # Βασικό φίλτρο
        
        filter_param = request.args.get('filter')
        if filter_param:
            try:
                parsed_filter = json.loads(filter_param)
                
                # Έλεγχος και προσθήκη φίλτρου ΑΜΚΑ αν υπάρχει
                if 'personal_details.amka' in parsed_filter:
                    amka_value = parsed_filter.get('personal_details.amka')
                    if amka_value: # Προσθήκη μόνο αν υπάρχει τιμή
                         query_filter['personal_details.amka'] = amka_value
                    # Αφαιρούμε το κλειδί από το parsed_filter για να μην προστεθεί ξανά στο update
                    # (Αν και το update θα το αντικαθιστούσε)
                    if 'personal_details.amka' in parsed_filter: # Check again before del
                         del parsed_filter['personal_details.amka']
                         
                # Προσθήκη τυχόν *άλλων* φίλτρων από το request
                # (ΠΡΟΣΟΧΗ: Αν έρθει π.χ. φίλτρο ID, θα αντικαταστήσει το αρχικό)
                # Ίσως χρειαστεί πιο έξυπνος συνδυασμός στο μέλλον
                query_filter.update(parsed_filter)
                
                print(f"[get_my_managed_patients_list] Applying filter: {query_filter}") # Debug
            except json.JSONDecodeError:
                print(f"[get_my_managed_patients_list] Warning: Could not decode filter param: {filter_param}")
            except Exception as e:
                 print(f"[get_my_managed_patients_list] Error processing filter: {e}")
        # ----------------------------------------------------
        
        total_patients = db.patients.count_documents(query_filter) # <--- Σωστός υπολογισμός συνόλου
        
        if total_patients == 0:
            # Αν δεν βρέθηκαν ασθενείς *με τα φίλτρα* (ή ο γιατρός δεν έχει ασθενείς)
            resp = make_response(jsonify([]), 200)
            resp.headers['Content-Range'] = f'patients 0-0/{total_patients}'
            return resp
            
        # Προς το παρόν, δεν υλοποιούμε pagination/sorting από τα params του react-admin
        # Επιστρέφουμε τους ασθενείς που ταιριάζουν στα φίλτρα
        projection = {
            "_id": 1,
            "personal_details.first_name": 1,
            "personal_details.last_name": 1,
            "personal_details.amka": 1
        }
        patients_cursor = db.patients.find(query_filter, projection)
            
        patients_list = []
        for patient in patients_cursor:
            # Μετατροπή _id σε id
            patient['id'] = str(patient.pop('_id')) # Διασφαλίζουμε ότι το πεδίο ονομάζεται 'id'
            
            # Μετατροπή timestamps
            if 'created_at' in patient and isinstance(patient['created_at'], datetime.datetime):
                patient['created_at'] = patient['created_at'].isoformat()
            if 'last_updated_at' in patient and isinstance(patient['last_updated_at'], datetime.datetime):
                patient['last_updated_at'] = patient['last_updated_at'].isoformat()
            if 'assigned_doctors' in patient and isinstance(patient['assigned_doctors'], list):
                patient['assigned_doctors'] = [str(doc_id) for doc_id in patient['assigned_doctors'] if isinstance(doc_id, ObjectId)]
            if 'uploaded_files' in patient and isinstance(patient['uploaded_files'], list):
                for file_meta in patient['uploaded_files']:
                    if 'upload_date' in file_meta and isinstance(file_meta['upload_date'], datetime.datetime):
                        file_meta['upload_date'] = file_meta['upload_date'].isoformat()
            if 'account_details' in patient and 'password_hash' in patient['account_details']:
                 del patient['account_details']['password_hash']
                 
            # Επίσης αφαιρούμε το πλήρες account_details για τη λίστα 
            if 'account_details' in patient:
                del patient['account_details']
                
            patients_list.append(patient)

        # Δημιουργία response και προσθήκη header
        resp = make_response(jsonify(patients_list), 200)
        # Ορίζουμε το Content-Range (εδώ επιστρέφουμε όλους, 0 έως total-1)
        resp.headers['Content-Range'] = f'patients 0-{total_patients-1}/{total_patients}'
        return resp

    except Exception as e:
        print(f"Error in doctor-portal/patients endpoint: {e}")
        if "jwt" in str(e).lower():  # JWT related error
            return jsonify({"error": "Invalid or missing token"}), 401
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint to get the list of files for a specific patient (Doctor access) ---
@app.route('/api/patients/<string:patient_id>/files/list', methods=['GET'])
@jwt_required()
def get_patient_files_list(patient_id):
    current_doctor_id_str = get_jwt_identity()
    try:
        current_doctor_object_id = ObjectId(current_doctor_id_str)
    except InvalidId: return jsonify({"error": "Invalid doctor ID in token"}), 401
        
    if db is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        patient_object_id = ObjectId(patient_id)
    except InvalidId: return jsonify({"error": "Invalid patient ID format"}), 400

    # Separate try block for database operations
    try:
        # --- Authorization Check --- 
        patient = db.patients.find_one(
            {"_id": patient_object_id},
            {"assigned_doctors": 1, "is_in_common_space": 1, "uploaded_files": 1} # Fetch fields needed for auth and the files
        )
        if not patient: return jsonify({"error": "Patient not found"}), 404

        is_assigned_doctor = current_doctor_object_id in patient.get('assigned_doctors', [])
        is_common_space = patient.get('is_in_common_space', False)
        
        if not (is_assigned_doctor or is_common_space):
            return jsonify({"error": "Unauthorized to access files for this patient"}), 403
        # -------------------------

        files_list = patient.get('uploaded_files', [])
        total_files = len(files_list) # <-- Υπολογισμός συνόλου
        
        processed_files = []
        for file_meta in files_list:
            temp_meta = file_meta.copy() # Work on a copy to avoid modifying the original dict in list
            if 'upload_date' in temp_meta and isinstance(temp_meta['upload_date'], datetime.datetime):
                temp_meta['upload_date'] = temp_meta['upload_date'].isoformat()
            if 'extracted_text' in temp_meta:
                del temp_meta['extracted_text']
            
            # --- ΠΡΟΣΘΗΚΗ: Αντιστοίχιση file_id στο id --- 
            if 'file_id' in temp_meta:
                temp_meta['id'] = temp_meta['file_id'] # React-admin needs 'id'
            # -----------------------------------------
            
            processed_files.append(temp_meta)

        processed_files.sort(key=lambda x: x.get('upload_date', '0'), reverse=True)

        # --- Δημιουργία response με Content-Range --- 
        resource_name = 'files' # Όνομα πόρου για το header
        resp = make_response(jsonify(processed_files), 200)
        if total_files > 0:
            resp.headers['Content-Range'] = f'{resource_name} 0-{total_files-1}/{total_files}'
        else:
            resp.headers['Content-Range'] = f'{resource_name} 0-0/0'
        return resp # <-- Επιστροφή του response object
        # -------------------------------------------

    except Exception as e: # Catch potential errors during DB access or processing
        print(f"Error fetching file list for patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Εκκίνηση Server --- 
if __name__ == '__main__':
    print("Starting Flask-SocketIO server (Reloader Enabled)...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True)