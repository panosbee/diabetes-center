from flask import Blueprint, jsonify, request, make_response, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from bson.errors import InvalidId
import datetime
import logging
from utils.db import get_db

# Ρύθμιση logger
logger = logging.getLogger(__name__)

# Δημιουργία blueprint
doctors_bp = Blueprint('doctors', __name__, url_prefix='/api/doctors')

# Η σύνδεση στη βάση δεδομένων
db = get_db()

# --- Endpoint για λήψη όλων των γιατρών ---
@doctors_bp.route('', methods=['GET'])
@jwt_required() # Απαιτεί JWT για τη γενική λίστα
def get_doctors():
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # --- React-admin Pagination & Sorting Params --- 
        start = request.args.get('_start', default=0, type=int)
        end = request.args.get('_end', default=-1, type=int) # Default -1 για να πιάσουμε όλους αν δεν δοθεί
        sort_by = request.args.get('_sort', default='_id') # Default sort by ID
        order = request.args.get('_order', default='ASC')
        
        sort_direction = 1 if order.upper() == 'ASC' else -1
        limit = (end - start) if end != -1 else 0 # Limit 0 σημαίνει χωρίς όριο
        skip = start
        resource_name = 'doctors'
        # ---------------------------------------------

        # Προβολή: Μόνο βασικά στοιχεία για τη λίστα
        projection = {
            "_id": 1,
            "personal_details.first_name": 1,
            "personal_details.last_name": 1,
            "personal_details.specialty": 1,
            "availability_status": 1
        }
        
        query_filter = {}
        
        # Μέτρηση συνόλου γιατρών (με βάση το φίλτρο)
        total_doctors = db.doctors.count_documents(query_filter)
        
        # Ανάκτηση δεδομένων με pagination και sorting
        doctors_cursor = db.doctors.find(query_filter, projection)\
                           .sort(sort_by, sort_direction)\
                           .skip(skip)
        if limit > 0:
             doctors_cursor = doctors_cursor.limit(limit)
             
        doctors_list = []
        count_in_page = 0 # Μετράμε πόσα είναι στη σελίδα για το Content-Range
        for doctor in doctors_cursor:
            # Μετονομάζουμε _id σε id
            doctor['id'] = str(doctor.pop('_id')) 
            doctors_list.append(doctor)
            count_in_page += 1

        # Δημιουργία response και προσθήκη header Content-Range
        resp = make_response(jsonify(doctors_list), 200)
        range_end = (start + count_in_page - 1) if count_in_page > 0 else start
        resp.headers['Content-Range'] = f'{resource_name} {start}-{range_end}/{total_doctors}'
        return resp

    except Exception as e:
        logger.error(f"Error fetching doctors: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- ΝΕΟ Endpoint για λήψη διαθέσιμων γιατρών (ΔΗΜΟΣΙΟ) ---
@doctors_bp.route('/available', methods=['GET'])
def get_available_doctors():
    """Επιστρέφει λίστα με τους διαθέσιμους γιατρούς (id, όνομα, ειδικότητα)."""
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Φίλτρο για διαθέσιμους γιατρούς
        query_filter = {"availability_status": "available"}
        
        # Προβολή: Μόνο τα απαραίτητα στοιχεία για την επιλογή από τον ασθενή
        projection = {
            "_id": 1,
            "personal_details.first_name": 1,
            "personal_details.last_name": 1,
            "personal_details.specialty": 1
        }
        
        # Ανάκτηση δεδομένων (χωρίς pagination προς το παρόν, συνήθως οι γιατροί δεν είναι πάρα πολλοί)
        doctors_cursor = db.doctors.find(query_filter, projection).sort("personal_details.last_name", 1) # Ταξινόμηση με βάση το επώνυμο
             
        doctors_list = []
        for doctor in doctors_cursor:
            # Μετονομάζουμε _id σε id
            doctor['id'] = str(doctor.pop('_id')) 
            doctors_list.append(doctor)

        return jsonify(doctors_list), 200

    except Exception as e:
        logger.error(f"Error fetching available doctors: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για λήψη στοιχείων συγκεκριμένου γιατρού ---
@doctors_bp.route('/<string:doctor_id>', methods=['GET'])
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
        logger.error(f"Error fetching doctor {doctor_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για προσθήκη νέου γιατρού ---
@doctors_bp.route('', methods=['POST'])
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

        # Το bcrypt μεταφέρθηκε στην κύρια εφαρμογή - στείλε πίσω τα δεδομένα για hashing
        # --- ΠΡΟΣΘΗΚΗ LOGIC ΓΙΑ HASHING ---
        bcrypt_instance = current_app.extensions.get('bcrypt')
        if not bcrypt_instance:
            logger.error("Bcrypt extension not found on current_app")
            return jsonify({"error": "Internal server error - bcrypt not configured"}), 500
        hashed_password = bcrypt_instance.generate_password_hash(plain_password).decode('utf-8')
        # ------------------------------------

        # --- Προετοιμασία Εγγράφου Γιατρού ---
        doctor_data = {
            "personal_details": personal_details,
            "account_details": {
                "username": username,
                # "password": plain_password  # Θα γίνει hash στο app.py <--- ΑΦΑΙΡΕΣΗ ΑΥΤΟΥ
                "password_hash": hashed_password # <--- ΠΡΟΣΘΗΚΗ HASHED PASSWORD
            },
            "managed_patients": data.get('managed_patients', []),
            "availability_status": data.get('availability_status', 'unavailable'), 
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        }
        doctor_data['last_updated_at'] = doctor_data['created_at']
        
        # --- ΕΙΣΑΓΩΓΗ ΣΤΗ ΒΑΣΗ & ΕΠΙΣΤΡΟΦΗ ΑΠΑΝΤΗΣΗΣ ---
        result = db.doctors.insert_one(doctor_data)
        
        if result.inserted_id:
            # Επιστροφή του νέου γιατρού (με id και χωρίς password hash)
            created_doctor = db.doctors.find_one({"_id": result.inserted_id})
            if created_doctor:
                created_doctor['id'] = str(created_doctor.pop('_id'))
                if 'created_at' in created_doctor: created_doctor['created_at'] = created_doctor['created_at'].isoformat()
                if 'last_updated_at' in created_doctor: created_doctor['last_updated_at'] = created_doctor['last_updated_at'].isoformat()
                if 'account_details' in created_doctor and 'password_hash' in created_doctor['account_details']:
                    del created_doctor['account_details']['password_hash'] # Αφαίρεση του hash από την απάντηση
                # Μετατροπή managed_patients σε λίστα από strings
                if 'managed_patients' in created_doctor and isinstance(created_doctor['managed_patients'], list):
                    created_doctor['managed_patients'] = [str(patient_id) for patient_id in created_doctor['managed_patients'] if isinstance(patient_id, ObjectId)]

                return jsonify(created_doctor), 201
            else:
                logger.error(f"Doctor created (id: {result.inserted_id}) but could not be retrieved from DB.")
                return jsonify({"error": "Doctor created but could not be retrieved"}), 500
        else:
            logger.error("Failed to insert new doctor into DB.")
            return jsonify({"error": "Failed to create doctor"}), 500
        # ----------------------------------------------------

    except Exception as e:
        logger.error(f"Error preparing doctor: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για ενημέρωση στοιχείων γιατρού ---
@doctors_bp.route('/<string:doctor_id>', methods=['PATCH'])
@jwt_required()
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
        if 'id' in update_data: del update_data['id'] # Για React-admin
        if 'created_at' in update_data: del update_data['created_at']
        if 'last_updated_at' in update_data: del update_data['last_updated_at']
        if 'account_details' in update_data: del update_data['account_details'] 
        if 'managed_patients' in update_data: del update_data['managed_patients']

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
        else:
            # Είτε έγινε update είτε όχι, φέρνουμε το (ενημερωμένο) record
            updated_doctor = db.doctors.find_one({"_id": object_id})
            if updated_doctor:
                # Μετατροπές για το react-admin
                updated_doctor['id'] = str(updated_doctor.pop('_id'))
                if 'created_at' in updated_doctor and isinstance(updated_doctor['created_at'], datetime.datetime):
                    updated_doctor['created_at'] = updated_doctor['created_at'].isoformat()
                if 'last_updated_at' in updated_doctor and isinstance(updated_doctor['last_updated_at'], datetime.datetime):
                    updated_doctor['last_updated_at'] = updated_doctor['last_updated_at'].isoformat()
                if 'managed_patients' in updated_doctor and isinstance(updated_doctor['managed_patients'], list):
                     updated_doctor['managed_patients'] = [str(p_id) for p_id in updated_doctor['managed_patients']]
                # Αφαίρεση hash κωδικού
                if 'account_details' in updated_doctor and 'password_hash' in updated_doctor['account_details']:
                    del updated_doctor['account_details']['password_hash']
                    
                # Επιστροφή στη μορφή { data: ... }
                return jsonify({"data": updated_doctor}), 200 
            else:
                 # Αυτό δεν θα έπρεπε να συμβεί αν matched_count > 0
                 logger.error(f"Failed to retrieve doctor {doctor_id} after update.")
                 return jsonify({"error": "Failed to retrieve updated doctor data"}), 500

    except Exception as e:
        logger.error(f"Error updating doctor {doctor_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για διαγραφή γιατρού ---
@doctors_bp.route('/<string:doctor_id>', methods=['DELETE'])
@jwt_required()
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
        # --- Βήμα 1: Αφαίρεση Doctor ID από τους Patients --- 
        # Βρίσκουμε τους ασθενείς που διαχειρίζεται αυτός ο γιατρός
        # (Δεν χρειάζεται να τους φέρουμε όλους, απλά κάνουμε update)
        update_patients_result = db.patients.update_many(
            {"assigned_doctors": object_id},
            {"$pull": { "assigned_doctors": object_id } }
        )
        logger.info(f"Removed doctor {doctor_id} from {update_patients_result.modified_count} patients' assigned lists.")
        
        # --- Βήμα 2: Διαγραφή Εγγραφής Γιατρού --- 
        result = db.doctors.delete_one({"_id": object_id})

        if result.deleted_count == 1:
            # TODO: Decide what happens to sessions created by this doctor.
            # Option 1: Leave them as is (doctor_id will point to non-existent doctor)
            # Option 2: Update sessions to set doctor_id to null?
            # Option 3: Delete sessions? (Probably not ideal)
            logger.info(f"Doctor {doctor_id} deleted. Associated patients updated. Sessions created by this doctor remain.")
            return jsonify({
                "message": "Doctor deleted successfully",
                "details": {
                     "patients_updated": update_patients_result.modified_count
                }
            }), 200
        else:
            return jsonify({"error": "Doctor not found"}), 404

    except Exception as e:
        logger.error(f"Error deleting doctor {doctor_id}: {e}")
        return jsonify({"error": "An internal server error occurred during doctor deletion"}), 500

# Προσθέστε αυτόν τον κώδικα στο doctors.py για να διαγνώσετε το πρόβλημα

@doctors_bp.route('/debug-connections', methods=['GET'])
@jwt_required()
def debug_doctor_patient_connections():
    """Διαγνωστικό endpoint για τις συνδέσεις γιατρών-ασθενών."""
    doctor_id_str = get_jwt_identity()
    
    try:
        doctor_object_id = ObjectId(doctor_id_str)
        doctor = db.doctors.find_one({"_id": doctor_object_id})
        
        if not doctor:
            return jsonify({"error": "Doctor not found"}), 404
            
        managed_patients = doctor.get('managed_patients', [])
        patients_data = []
        
        for patient_id in managed_patients:
            patient = db.patients.find_one({"_id": patient_id})
            if patient:
                patient_assigned_doctors = patient.get('assigned_doctors', [])
                patients_data.append({
                    "patient_id": str(patient_id),
                    "patient_name": f"{patient.get('personal_details', {}).get('last_name', '?')}, {patient.get('personal_details', {}).get('first_name', '?')}",
                    "has_doctor_assigned": doctor_object_id in patient_assigned_doctors,
                    "assigned_doctors": [str(doc_id) for doc_id in patient_assigned_doctors]
                })
        
        return jsonify({
            "doctor_id": doctor_id_str,
            "doctor_name": f"{doctor.get('personal_details', {}).get('last_name', '?')}, {doctor.get('personal_details', {}).get('first_name', '?')}",
            "managed_patients_count": len(managed_patients),
            "managed_patients": patients_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500