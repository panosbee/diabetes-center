from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from bson.errors import InvalidId
import datetime
import logging
from utils.db import get_db
import json
from utils.permissions import EditPatientPermission, permission_denied, ViewPatientPermission, DeletePatientPermission

# Ρύθμιση logger
logger = logging.getLogger(__name__)

# Δημιουργία blueprint
patients_bp = Blueprint('patients', __name__, url_prefix='/api/patients')

# Η σύνδεση στη βάση δεδομένων
db = get_db()

# --- Endpoint για λήψη όλων των ασθενών ---
@patients_bp.route('', methods=['GET'])
@jwt_required()
def get_patients():
    """Επιστρέφει λίστα με όλους τους ασθενείς"""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Μετατροπή του ID σε ObjectId
        try:
            requesting_user_id = ObjectId(requesting_user_id_str)
        except InvalidId:
            return jsonify({"error": "Invalid user ID in token"}), 400

        # --- React-admin Pagination & Sorting Params --- 
        # Παράμετροι για range
        range_param = request.args.get('range')
        if range_param:
            try:
                range_json = json.loads(range_param)
                start, end = range_json[0], range_json[1]
            except (json.JSONDecodeError, IndexError, TypeError):
                start, end = 0, 9  # default
        else:
            start = request.args.get('_start', default=0, type=int)
            end = request.args.get('_end', default=9, type=int)
        
        # Παράμετροι για sort
        sort_param = request.args.get('sort')
        if sort_param:
            try:
                sort_json = json.loads(sort_param)
                sort_by, order = sort_json[0], sort_json[1].upper()
            except (json.JSONDecodeError, IndexError, TypeError):
                sort_by, order = "id", "ASC"  # default
        else:
            sort_by = request.args.get('_sort', default='id')
            order = request.args.get('_order', default='ASC').upper()
        
        # Μετατροπή του sort_by 'id' σε '_id' για MongoDB
        if sort_by == 'id':
            sort_by = '_id'
        
        sort_direction = 1 if order == 'ASC' else -1
        limit = (end - start) + 1
        skip = start
        resource_name = 'patients'
        # ---------------------------------------------

        # Φίλτρα αναζήτησης από τα query params
        filter_param = request.args.get('filter')
        filter_data = {}
        if filter_param:
            try:
                filter_data = json.loads(filter_param)
            except json.JSONDecodeError:
                pass  # Αγνόηση προβληματικών φίλτρων
        
        # ΣΩΣΤΗ ΛΟΓΙΚΗ: Στο "Ασθενείς" panel ο γιατρός βλέπει ΟΛΟΥΣ τους ασθενείς
        # αλλά μπορεί να επεξεργαστεί μόνο τους δικούς του + αυτούς στον κοινό χώρο
        query_filter = {}  # Εμφάνιση όλων για viewing
        
        # Ενημέρωση φίλτρων αναζήτησης από query params
        if 'q' in filter_data and filter_data['q']:
            search_term = filter_data['q']
            # Αναζήτηση στα βασικά πεδία
            query_filter['$or'] = [
                {"personal_details.first_name": {"$regex": search_term, "$options": "i"}},
                {"personal_details.last_name": {"$regex": search_term, "$options": "i"}},
                {"personal_details.amka": {"$regex": search_term, "$options": "i"}}
            ]
        
        # Άλλα φίλτρα από το React-Admin
        for key, value in filter_data.items():
            if key != 'q' and value:  # Παραλείπουμε το 'q' και κενές τιμές
                if key == 'id':
                    try:
                        # Διόρθωση: Χειρισμός και λίστας και string για το id
                        if isinstance(value, list):
                            # Αν είναι λίστα, παίρνουμε τα ObjectIds και χρησιμοποιούμε $in
                            object_ids = [ObjectId(item) for item in value if ObjectId.is_valid(item)]
                            if object_ids:
                                # Διόρθωση: Σωστή σύνταξη για το $in
                                query_filter['_id'] = {"$in": object_ids}
                        elif isinstance(value, str) and ObjectId.is_valid(value):
                            # Αν είναι string, το μετατρέπουμε σε ObjectId
                            query_filter['_id'] = ObjectId(value)
                    except InvalidId:
                        # Αγνόηση μη έγκυρων IDs
                        logger.warning(f"Invalid ObjectId format received in filter for id: {value}")
                        pass
                elif key == 'amka_filter':
                    # Εφαρμογή του φίλτρου στο σωστό πεδίο της βάσης
                    query_filter["personal_details.amka"] = {"$regex": value, "$options": "i"}
                elif key.startswith('personal_details.'):
                    # Διασφάλιση ότι δεν ξαναεφαρμόζουμε το amka αν ήρθε ως amka_filter
                    if key != 'personal_details.amka':
                         query_filter[key] = value
        
        # Μέτρηση συνόλου ασθενών (με βάση το φίλτρο)
        total_patients = db.patients.count_documents(query_filter)
        
        # Προβολή: Επιλέγουμε συγκεκριμένα πεδία για βελτίωση απόδοσης
        projection = {
            "_id": 1,
            "personal_details.first_name": 1,
            "personal_details.last_name": 1,
            "personal_details.amka": 1,
            "personal_details.date_of_birth": 1,
            "personal_details.gender": 1,
            "medical_history.diabetes_type": 1,
            "medical_history.diagnosis_date": 1,
            "risk_factors.smoking": 1,
            "last_consultation_date": 1,
            "assigned_doctors": 1,  # Χρειάζεται για τον έλεγχο δικαιωμάτων στο frontend
            "is_in_common_space": 1  # Χρειάζεται για common space logic
        }
        
        # Ανάκτηση δεδομένων με pagination και sorting
        patients_cursor = db.patients.find(query_filter, projection)\
                           .sort(sort_by, sort_direction)\
                           .skip(skip)
        if limit > 0:
             patients_cursor = patients_cursor.limit(limit)
             
        patients_list = []
        count_in_page = 0 # Μετράμε πόσα είναι στη σελίδα για το Content-Range
        for patient in patients_cursor:
            # Μετονομάζουμε _id σε id
            patient_id = str(patient.pop('_id'))
            patient['id'] = patient_id
            
            # Μετατρέπουμε τα ObjectId των γιατρών σε strings
            if 'assigned_doctors' in patient:
                patient['assigned_doctors'] = [str(doctor_id) for doctor_id in patient['assigned_doctors']]
            
            # Έλεγχος αν ο γιατρός είναι assigned στον ασθενή
            is_assigned = requesting_user_id_str in patient.get('assigned_doctors', [])
            
            # Έλεγχος αν ο ασθενής είναι στον κοινό χώρο
            is_in_common_space = patient.get('is_in_common_space', False)
            
            # Προσθήκη σημαίας που δείχνει αν ο τρέχων γιατρός έχει πρόσβαση viewing
            patient['has_access'] = is_assigned or is_in_common_space
            
            # Προσθήκη σημαίας που δείχνει αν μπορεί να επεξεργαστεί (μόνο δικούς του + common space)
            patient['can_edit'] = is_assigned or is_in_common_space
            
            patients_list.append(patient)
            count_in_page += 1

        # Δημιουργία response και προσθήκη header Content-Range
        resp = make_response(jsonify(patients_list), 200)
        range_end = (start + count_in_page - 1) if count_in_page > 0 else start
        resp.headers['Content-Range'] = f'{resource_name} {start}-{range_end}/{total_patients}'
        return resp

    except Exception as e:
        logger.error(f"Error fetching patients list: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για λήψη στοιχείων συγκεκριμένου ασθενή ---
@patients_bp.route('/<string:patient_id>', methods=['GET'])
@jwt_required()
def get_patient_by_id(patient_id):
    """Επιστρέφει τα πλήρη στοιχεία ενός ασθενή."""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Μετατροπή IDs σε ObjectId
        requesting_user_id = ObjectId(requesting_user_id_str)
        patient_object_id = ObjectId(patient_id)
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400

    try:
        # Έλεγχος αν υπάρχει ο ασθενής
        patient = db.patients.find_one({"_id": patient_object_id})
        
        if not patient:
            return jsonify({"error": "Patient not found"}), 404
            
        # Έλεγχος δικαιώματος προβολής με το νέο σύστημα
        view_permission = ViewPatientPermission(patient_id)
        if not view_permission.can():
            return permission_denied("Δεν έχετε δικαίωμα προβολής αυτού του ασθενή")
            
        # Έλεγχος αν ο χρήστης έχει δικαίωμα επεξεργασίας
        edit_permission = EditPatientPermission(patient_id)
        has_edit_access = edit_permission.can()
            
        # Μετατροπές IDs/Timestamps
        patient['id'] = str(patient.pop('_id'))
        
        # Προσθήκη πεδίων has_access και can_edit για το frontend
        patient['has_access'] = has_edit_access
        patient['can_edit'] = has_edit_access
        
        # Μετατροπή ObjectIDs σε strings στη λίστα assigned_doctors
        if 'assigned_doctors' in patient and isinstance(patient['assigned_doctors'], list):
            patient['assigned_doctors'] = [str(doc_id) for doc_id in patient['assigned_doctors']]
            
        # Μετατροπή timestamps σε ISO format
        if 'last_consultation_date' in patient and isinstance(patient['last_consultation_date'], datetime.datetime):
            patient['last_consultation_date'] = patient['last_consultation_date'].isoformat()
            
        if 'medical_history' in patient and 'diagnosis_date' in patient['medical_history'] and \
           isinstance(patient['medical_history']['diagnosis_date'], datetime.datetime):
            patient['medical_history']['diagnosis_date'] = patient['medical_history']['diagnosis_date'].isoformat()
            
        if 'created_at' in patient and isinstance(patient['created_at'], datetime.datetime):
            patient['created_at'] = patient['created_at'].isoformat()
        if 'last_updated_at' in patient and isinstance(patient['last_updated_at'], datetime.datetime):
            patient['last_updated_at'] = patient['last_updated_at'].isoformat()
            
        return jsonify(patient), 200

    except Exception as e:
        logger.error(f"Error fetching patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για προσθήκη νέου ασθενή ---
@patients_bp.route('', methods=['POST'])
@jwt_required()
def add_patient():
    """Προσθέτει έναν νέο ασθενή στη βάση."""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        requesting_user_id = ObjectId(requesting_user_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid user ID in token"}), 400

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # --- Βασική Επικύρωση Δεδομένων ---
        personal_details = data.get('personal_details')
        if not personal_details or not isinstance(personal_details, dict):
            return jsonify({"error": "Missing or invalid 'personal_details'"}), 400

        required_personal_fields = ['first_name', 'last_name', 'amka', 'date_of_birth']
        for field in required_personal_fields:
            if field not in personal_details or not personal_details[field]:
                return jsonify({"error": f"Missing required field in personal_details: {field}"}), 400

        # Έλεγχος εάν ο AMKA υπάρχει ήδη
        amka = personal_details.get('amka')
        existing_patient = db.patients.find_one({"personal_details.amka": amka})
        if existing_patient:
            return jsonify({
                "error": f"A patient with AMKA '{amka}' already exists", 
                "existing_patient_id": str(existing_patient['_id'])
            }), 409

        # --- Προετοιμασία Εγγράφου Ασθενή ---
        # Προσθήκη του γιατρού που κάνει την εισαγωγή στους assigned_doctors
        patient_data = data.copy()
        patient_data['assigned_doctors'] = [requesting_user_id]
        
        # Προσθήκη timestamps
        now = datetime.datetime.now(datetime.timezone.utc)
        patient_data['created_at'] = now
        patient_data['last_updated_at'] = now
        
        # Εισαγωγή στη βάση
        result = db.patients.insert_one(patient_data)
        
        # Προσθήκη του ασθενή στους managed_patients του γιατρού
        patient_id = result.inserted_id
        db.doctors.update_one(
            {"_id": requesting_user_id},
            {"$addToSet": {"managed_patients": patient_id}}
        )
        
        response_data = {
            "message": "Patient added successfully",
            "id": str(patient_id)
        }
        
        return jsonify(response_data), 201

    except Exception as e:
        logger.error(f"Error adding new patient: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για ενημέρωση στοιχείων ασθενή ---
@patients_bp.route('/<string:patient_id>', methods=['PATCH'])
@jwt_required()
def update_patient(patient_id):
    """Ενημερώνει τα στοιχεία ενός ασθενή."""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Μετατροπή IDs σε ObjectId
        patient_object_id = ObjectId(patient_id)
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400

    try:
        # Έλεγχος αν υπάρχει ο ασθενής
        patient_exists = db.patients.find_one({"_id": patient_object_id})
        
        if not patient_exists:
            return jsonify({"error": "Patient not found"}), 404
        
        # Έλεγχος δικαιώματος επεξεργασίας με το νέο σύστημα
        edit_permission = EditPatientPermission(patient_id)
        if not edit_permission.can():
            return permission_denied("Δεν έχετε δικαίωμα επεξεργασίας αυτού του ασθενή")

        update_data = request.get_json()
        if not update_data:
            return jsonify({"error": "Request body must be JSON and non-empty"}), 400

        # Απαγορεύουμε την αλλαγή του _id, created_at και assigned_doctors
        if '_id' in update_data: del update_data['_id']
        if 'id' in update_data: del update_data['id']  # Για React-admin
        if 'created_at' in update_data: del update_data['created_at']
        if 'last_updated_at' in update_data: del update_data['last_updated_at']  # Αφαιρούμε το last_updated_at για να αποφύγουμε conflict
        if 'assigned_doctors' in update_data: del update_data['assigned_doctors']
        if 'has_access' in update_data: del update_data['has_access']  # Αφαιρούμε το πεδίο has_access που προσθέτουμε στο frontend

        # Αν δεν έμεινε τίποτα για update μετά τους περιορισμούς
        if not update_data:
             return jsonify({"error": "No updatable fields provided"}), 400

        # Ενημέρωση του last_updated_at
        update_payload = {
            "$set": update_data,
            "$currentDate": { "last_updated_at": True }
        }

        result = db.patients.update_one(
            {"_id": patient_object_id}, 
            update_payload
        )

        if result.modified_count == 0 and result.matched_count == 1:
            # Επιστρέφουμε τον ασθενή μετά την ενημέρωση
            updated_patient = db.patients.find_one({"_id": patient_object_id})
            updated_patient['id'] = str(updated_patient.pop('_id'))
            
            # Μετατροπή των ObjectId σε strings για τη λίστα assigned_doctors
            if 'assigned_doctors' in updated_patient:
                updated_patient['assigned_doctors'] = [str(doc_id) for doc_id in updated_patient['assigned_doctors']]
                
            # Μετατροπή timestamps σε ISO format
            if 'last_consultation_date' in updated_patient and isinstance(updated_patient['last_consultation_date'], datetime.datetime):
                updated_patient['last_consultation_date'] = updated_patient['last_consultation_date'].isoformat()
                
            if 'medical_history' in updated_patient and 'diagnosis_date' in updated_patient['medical_history'] and \
               isinstance(updated_patient['medical_history']['diagnosis_date'], datetime.datetime):
                updated_patient['medical_history']['diagnosis_date'] = updated_patient['medical_history']['diagnosis_date'].isoformat()
                
            if 'created_at' in updated_patient and isinstance(updated_patient['created_at'], datetime.datetime):
                updated_patient['created_at'] = updated_patient['created_at'].isoformat()
            if 'last_updated_at' in updated_patient and isinstance(updated_patient['last_updated_at'], datetime.datetime):
                updated_patient['last_updated_at'] = updated_patient['last_updated_at'].isoformat()
            
            # Επιστρέφουμε στη μορφή που αναμένει το React Admin
            return jsonify({"data": updated_patient}), 200
        else:
            # Επιστρέφουμε τον ασθενή μετά την ενημέρωση
            updated_patient = db.patients.find_one({"_id": patient_object_id})
            updated_patient['id'] = str(updated_patient.pop('_id'))
            
            # Μετατροπή των ObjectId σε strings για τη λίστα assigned_doctors
            if 'assigned_doctors' in updated_patient:
                updated_patient['assigned_doctors'] = [str(doc_id) for doc_id in updated_patient['assigned_doctors']]
                
            # Μετατροπή timestamps σε ISO format
            if 'last_consultation_date' in updated_patient and isinstance(updated_patient['last_consultation_date'], datetime.datetime):
                updated_patient['last_consultation_date'] = updated_patient['last_consultation_date'].isoformat()
                
            if 'medical_history' in updated_patient and 'diagnosis_date' in updated_patient['medical_history'] and \
               isinstance(updated_patient['medical_history']['diagnosis_date'], datetime.datetime):
                updated_patient['medical_history']['diagnosis_date'] = updated_patient['medical_history']['diagnosis_date'].isoformat()
                
            if 'created_at' in updated_patient and isinstance(updated_patient['created_at'], datetime.datetime):
                updated_patient['created_at'] = updated_patient['created_at'].isoformat()
            if 'last_updated_at' in updated_patient and isinstance(updated_patient['last_updated_at'], datetime.datetime):
                updated_patient['last_updated_at'] = updated_patient['last_updated_at'].isoformat()
            
            # Επιστρέφουμε στη μορφή που αναμένει το React Admin
            return jsonify({"data": updated_patient}), 200

    except Exception as e:
        logger.error(f"Error updating patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για διαγραφή ασθενή ---
@patients_bp.route('/<string:patient_id>', methods=['DELETE'])
@jwt_required()
def delete_patient(patient_id):
    """Διαγράφει έναν ασθενή από τη βάση."""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Μετατροπή IDs σε ObjectId
        patient_object_id = ObjectId(patient_id)
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400

    try:
        # Έλεγχος αν υπάρχει ο ασθενής
        patient = db.patients.find_one({"_id": patient_object_id})
        
        if not patient:
            return jsonify({"error": "Patient not found"}), 404
            
        # Έλεγχος δικαιώματος διαγραφής με το νέο σύστημα
        delete_permission = DeletePatientPermission(patient_id)
        if not delete_permission.can():
            return permission_denied("Δεν έχετε δικαίωμα διαγραφής αυτού του ασθενή")

        # Αφαίρεση του ασθενή από τους managed_patients όλων των γιατρών
        doc_update_result = db.doctors.update_many(
            {"managed_patients": patient_object_id},
            {"$pull": {"managed_patients": patient_object_id}}
        )
        
        # Διαγραφή του ασθενή
        result = db.patients.delete_one({"_id": patient_object_id})
        
        if result.deleted_count == 1:
            # TODO: Διαγραφή επίσης των sessions που σχετίζονται με τον ασθενή
            # db.sessions.delete_many({"patient_id": patient_object_id})
            
            return jsonify({
                "message": "Patient deleted successfully",
                "details": {
                    "doctors_updated": doc_update_result.modified_count
                }
            }), 200
        else:
            # Αυτό δεν πρέπει να συμβεί ποτέ, αφού ήδη ελέγξαμε ότι ο ασθενής υπάρχει
            return jsonify({"error": "Patient not found"}), 404

    except Exception as e:
        logger.error(f"Error deleting patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για ενεργοποίηση/απενεργοποίηση του common space ---
@patients_bp.route('/<string:patient_id>/common-space', methods=['PATCH'])
@jwt_required()
def toggle_common_space(patient_id):
    """Ενεργοποίηση/απενεργοποίηση του common space για έναν ασθενή"""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Μετατροπή IDs σε ObjectId
        requesting_user_id = ObjectId(requesting_user_id_str)
        patient_object_id = ObjectId(patient_id)
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400

    try:
        # Έλεγχος εξουσιοδότησης: Ο γιατρός πρέπει να έχει δικαίωμα επεξεργασίας του ασθενή
        # Αυτό σημαίνει είτε να είναι assigned doctor, είτε να είναι admin
        edit_permission = EditPatientPermission(patient_id)
        if not edit_permission.can():
            return permission_denied("Δεν έχετε δικαίωμα αλλαγής του common space status αυτού του ασθενή")
            
        # Λήψη δεδομένων από το request
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON and non-empty"}), 400
            
        # Έλεγχος αν παρέχεται η παράμετρος is_in_common_space
        if 'is_in_common_space' not in data:
            return jsonify({"error": "Missing required parameter: is_in_common_space"}), 400
            
        is_in_common_space = bool(data['is_in_common_space'])
        
        # Ενημέρωση του ασθενή
        result = db.patients.update_one(
            {"_id": patient_object_id},
            {
                "$set": {"is_in_common_space": is_in_common_space},
                "$currentDate": {"last_updated_at": True}
            }
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Patient not found"}), 404
            
        # Επιτυχής ενημέρωση
        return jsonify({
            "message": "Common space status updated successfully",
            "is_in_common_space": is_in_common_space
        }), 200

    except Exception as e:
        logger.error(f"Error updating common space status for patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500 