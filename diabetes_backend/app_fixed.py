#!/usr/bin/env python
# encoding: utf-8

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

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}) # <--- Ενεργοποίηση CORS για όλα τα /api/* (προσωρινά *)

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
if not DEEPSEEK_API_KEY:
    print("WARNING: DEEPSEEK_API_KEY not found in environment variables!")
if not app.config["JWT_SECRET_KEY"]:
    print("ERROR: JWT_SECRET_KEY not found in environment variables! JWT will not work.")

# --- Tesseract Setup ---
TESSERACT_CMD = r'C:\Users\Panos\OneDrive\Υπολογιστής\Tesseract-OCR\tesseract.exe'
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
    if db:
        return jsonify({"message": "Welcome to the Diabetes Management API!", "db_status": "connected"})
    else:
        return jsonify({"message": "Welcome to the Diabetes Management API!", "db_status": "disconnected"}), 500

# --- Doctor Specific Protected Endpoints --- 

@app.route('/api/doctor-portal/patients', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_my_managed_patients_list():
    """Επιστρέφει τη λίστα των ασθενών που διαχειρίζεται ο συνδεδεμένος γιατρός."""
    
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        return make_response('', 204) # Return 204 No Content with CORS headers from @cross_origin

    # --- Proceed with GET logic --- 
    try:
        # Για το GET, απαιτούμε JWT token
        verify_jwt_in_request()
        current_doctor_id_str = get_jwt_identity()
        
        if not current_doctor_id_str:
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        try:
            current_doctor_object_id = ObjectId(current_doctor_id_str)
        except InvalidId:
            return jsonify({"error": "Invalid doctor ID format in token"}), 401

        if db is None:
            return jsonify({"error": "Database connection failed"}), 500

        doctor = db.doctors.find_one({"_id": current_doctor_object_id}, {"managed_patients": 1})
        if not doctor:
            return jsonify({"error": "Doctor not found"}), 404 
            
        managed_patient_ids = doctor.get('managed_patients', [])
        if not managed_patient_ids:
            return jsonify([]), 200
            
        projection = {
            "_id": 1,
            "personal_details.first_name": 1,
            "personal_details.last_name": 1,
            "personal_details.amka": 1
        }
        patients_cursor = db.patients.find({"_id": {"$in": managed_patient_ids}}, projection)
            
        patients_list = []
        for patient in patients_cursor:
            patient['id'] = str(patient.pop('_id'))
            patients_list.append(patient)

        return jsonify(patients_list), 200

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
        processed_files = []
        for file_meta in files_list:
            temp_meta = file_meta.copy() # Work on a copy to avoid modifying the original dict in list
            if 'upload_date' in temp_meta and isinstance(temp_meta['upload_date'], datetime.datetime):
                temp_meta['upload_date'] = temp_meta['upload_date'].isoformat()
            if 'extracted_text' in temp_meta:
                del temp_meta['extracted_text']
            processed_files.append(temp_meta)

        processed_files.sort(key=lambda x: x.get('upload_date', '0'), reverse=True)

        return jsonify(processed_files), 200

    except Exception as e: # Catch potential errors during DB access or processing
        print(f"Error fetching file list for patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

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

@app.route('/api/doctors/<string:doctor_id>', methods=['GET'])
@jwt_required()
def get_doctor_by_id(doctor_id):
    """Επιστρέφει τα πλήρη στοιχεία ενός γιατρού."""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        object_id = ObjectId(doctor_id)
    except InvalidId:
        return jsonify({"error": "Invalid doctor ID format"}), 400

    try:
        doctor = db.doctors.find_one({"_id": object_id})

        if doctor:
            # Ο γιατρός βρέθηκε - Μετατροπές IDs/Timestamps σε string
            # Αλλαγή του _id σε id για το React-admin
            doctor['id'] = str(doctor.pop('_id'))
            
            if 'created_at' in doctor and isinstance(doctor['created_at'], datetime.datetime):
                doctor['created_at'] = doctor['created_at'].isoformat()
            if 'last_updated_at' in doctor and isinstance(doctor['last_updated_at'], datetime.datetime):
                doctor['last_updated_at'] = doctor['last_updated_at'].isoformat()
            if 'managed_patients' in doctor and isinstance(doctor['managed_patients'], list):
                doctor['managed_patients'] = [str(patient_id) for patient_id in doctor['managed_patients'] if isinstance(patient_id, ObjectId)]
                
            # Αφαίρεση του password hash πριν την επιστροφή!
            if 'account_details' in doctor and 'password_hash' in doctor['account_details']:
                del doctor['account_details']['password_hash']
                
            return jsonify(doctor), 200
        else:
            return jsonify({"error": "Doctor not found"}), 404

    except Exception as e:
        print(f"Error fetching doctor {doctor_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- ΥΠΟΛΟΙΠΑ ENDPOINTS ΑΠΟ ΕΔΩ ΚΑΙ ΚΑΤΩ --- 

# -- (Βάλε εδώ τον υπόλοιπο κώδικα από το app.py) ---

if __name__ == '__main__':
    print("Starting Flask-SocketIO server (Reloader Enabled)...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True)