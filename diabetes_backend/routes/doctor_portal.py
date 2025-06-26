from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from bson.errors import InvalidId
import json
import logging
from utils.db import get_db
import datetime

# Ρύθμιση logger
logger = logging.getLogger(__name__)

# Δημιουργία blueprint
doctor_portal_bp = Blueprint('doctor_portal', __name__, url_prefix='/api/doctor-portal')

# Η σύνδεση στη βάση δεδομένων
db = get_db()

# --- Σύστημα ελέγχου δικαιωμάτων ---
def has_permission(doctor_id, permission_type, resource_id=None):
    """
    Ελέγχει αν ο γιατρός έχει το συγκεκριμένο δικαίωμα.
    
    Args:
        doctor_id: Το ID του γιατρού
        permission_type: Ο τύπος του δικαιώματος (view, edit, delete, add)
        resource_id: Το ID του πόρου (patient, session, κλπ.) αν χρειάζεται
        
    Returns:
        bool: True αν ο γιατρός έχει το δικαίωμα, False διαφορετικά
    """
    try:
        # Βρίσκουμε τον γιατρό και ελέγχουμε τα δικαιώματά του
        doctor = db.doctors.find_one({"_id": ObjectId(doctor_id)})
        
        if not doctor:
            return False
        
        # Έλεγχος για admin δικαιώματα - ο admin έχει όλα τα δικαιώματα
        if doctor.get("role") == "admin":
            return True
            
        # Έλεγχος ειδικών δικαιωμάτων με βάση το resource_id
        if resource_id:
            # Για τους ασθενείς, έλεγχος αν ο γιατρός είναι assigned_doctor
            if permission_type.startswith("patient."):
                patient = db.patients.find_one({"_id": ObjectId(resource_id)})
                if not patient:
                    return False
                
                # Ο γιατρός πρέπει να είναι στην λίστα assigned_doctors
                assigned_doctors = patient.get("assigned_doctors", [])
                if ObjectId(doctor_id) not in assigned_doctors:
                    return False
                    
                # Για view δικαιώματα, επιτρέπεται σε όλους τους assigned_doctors
                if permission_type == "patient.view":
                    return True
                    
                # Για edit δικαιώματα, έλεγχος του ρόλου του γιατρού
                elif permission_type == "patient.edit":
                    # Μόνο κύριοι γιατροί μπορούν να επεξεργαστούν ασθενείς
                    return doctor.get("role") in ["primary", "admin"]
                    
                # Για delete δικαιώματα, μόνο admin
                elif permission_type == "patient.delete":
                    return doctor.get("role") == "admin"
        
        # Γενικά δικαιώματα με βάση τον ρόλο
        role_permissions = {
            "admin": ["view_all", "edit_all", "delete_all", "add_all"],
            "primary": ["view_all", "add_patient", "edit_assigned", "delete_own"],
            "assistant": ["view_assigned", "edit_notes"]
        }
        
        doctor_role = doctor.get("role", "assistant")  # Default role
        allowed_permissions = role_permissions.get(doctor_role, [])
        
        # Έλεγχος αν το ζητούμενο δικαίωμα είναι στη λίστα επιτρεπόμενων δικαιωμάτων
        return permission_type in allowed_permissions
        
    except Exception as e:
        logger.error(f"Error checking permissions: {e}")
        return False

@doctor_portal_bp.route('/patients', methods=['GET'])
@jwt_required()
def get_doctor_patients():
    """Επιστρέφει τους ασθενείς που έχουν ανατεθεί στον γιατρό"""
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
            
        # Έλεγχος δικαιωμάτων - ο γιατρός πρέπει να έχει δικαίωμα view_all ή view_assigned
        has_view_all = has_permission(requesting_user_id_str, "view_all")
        
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
        
        # Βασικό φίλτρο: ο γιατρός βλέπει ΜΟΝΟ τους δικούς του ασθενείς (αυτό είναι το "Οι Ασθενείς μου" panel)
        query_filter = {"assigned_doctors": requesting_user_id}
        
        # Ενημέρωση φίλτρων αναζήτησης από query params
        if 'q' in filter_data and filter_data['q']:
            search_term = filter_data['q']
            # Αναζήτηση στα βασικά πεδία
            search_condition = [
                {"personal_details.first_name": {"$regex": search_term, "$options": "i"}},
                {"personal_details.last_name": {"$regex": search_term, "$options": "i"}},
                {"personal_details.amka": {"$regex": search_term, "$options": "i"}}
            ]
            
            # Συνδυάζουμε με το υπάρχον φίλτρο
            if "assigned_doctors" in query_filter:
                query_filter = {
                    "$and": [
                        {"assigned_doctors": requesting_user_id},
                        {"$or": search_condition}
                    ]
                }
            else:
                query_filter["$or"] = search_condition
        
        # Άλλα φίλτρα από το React-Admin
        for key, value in filter_data.items():
            if key != 'q' and value:  # Παραλείπουμε το 'q' και κενές τιμές
                if key == 'id':
                    try:
                        # Διόρθωση: Χειρισμός και λίστας και string για το id (όπως στο patients.py)
                        if isinstance(value, list):
                            object_ids = [ObjectId(item) for item in value if ObjectId.is_valid(item)]
                            if object_ids:
                                query_filter['_id'] = {"$in": object_ids}
                        elif isinstance(value, str) and ObjectId.is_valid(value):
                            query_filter['_id'] = ObjectId(value)
                    except InvalidId:
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
            "last_consultation_date": 1
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
            patient['id'] = str(patient.pop('_id')) 
            patients_list.append(patient)
            count_in_page += 1

        # Δημιουργία response και προσθήκη header Content-Range
        resp = make_response(jsonify(patients_list), 200)
        range_end = (start + count_in_page - 1) if count_in_page > 0 else start
        resp.headers['Content-Range'] = f'{resource_name} {start}-{range_end}/{total_patients}'
        return resp
        
    except Exception as e:
        logger.error(f"Error fetching doctor patients: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500
        
@doctor_portal_bp.route('/permissions/<string:resource_type>/<string:resource_id>', methods=['GET'])
@jwt_required()
def check_permissions(resource_type, resource_id):
    """Επιστρέφει τα δικαιώματα του γιατρού για τον συγκεκριμένο πόρο"""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        permissions = {
            "can_view": False,
            "can_edit": False,
            "can_delete": False
        }
        
        # Έλεγχος δικαιωμάτων με βάση τον τύπο πόρου
        if resource_type == "patient":
            permissions["can_view"] = has_permission(requesting_user_id_str, "patient.view", resource_id)
            permissions["can_edit"] = has_permission(requesting_user_id_str, "patient.edit", resource_id)
            permissions["can_delete"] = has_permission(requesting_user_id_str, "patient.delete", resource_id)
        elif resource_type == "session":
            permissions["can_view"] = has_permission(requesting_user_id_str, "session.view", resource_id)
            permissions["can_edit"] = has_permission(requesting_user_id_str, "session.edit", resource_id)
            permissions["can_delete"] = has_permission(requesting_user_id_str, "session.delete", resource_id)
        elif resource_type == "file":
            permissions["can_view"] = has_permission(requesting_user_id_str, "file.view", resource_id)
            permissions["can_edit"] = has_permission(requesting_user_id_str, "file.edit", resource_id)
            permissions["can_delete"] = has_permission(requesting_user_id_str, "file.delete", resource_id)
            
        return jsonify(permissions), 200
        
    except Exception as e:
        logger.error(f"Error checking permissions: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500
        
@doctor_portal_bp.route('/my-profile', methods=['GET'])
@jwt_required()
def get_doctor_profile():
    """Επιστρέφει το προφίλ του γιατρού"""
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
            
        # Ανάκτηση στοιχείων γιατρού
        doctor = db.doctors.find_one({"_id": requesting_user_id})
        
        if not doctor:
            return jsonify({"error": "Doctor not found"}), 404
            
        # Μετατροπή ObjectId σε string για JSON serialization
        doctor['id'] = str(doctor.pop('_id'))
        
        # Μετατροπή της λίστας managed_patients σε strings
        if 'managed_patients' in doctor:
            doctor['managed_patients'] = [str(p) for p in doctor['managed_patients']]
            
        return jsonify(doctor), 200
        
    except Exception as e:
        logger.error(f"Error fetching doctor profile: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για λήψη των ασθενών στον κοινό χώρο ---
@doctor_portal_bp.route('/common-space/patients', methods=['GET'])
@jwt_required()
def get_common_space_patients():
    """Επιστρέφει τους ασθενείς που βρίσκονται στον κοινό χώρο"""
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
            
        # Έλεγχος δικαιωμάτων
        from utils.permissions import ViewPatientPermission
        view_permission = ViewPatientPermission()
        if not view_permission.can():
            return jsonify({"error": "Δεν έχετε δικαίωμα προβολής των ασθενών στον κοινό χώρο"}), 403
        
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
        
        # Βασικό φίλτρο: ασθενείς στον κοινό χώρο
        query_filter = {"is_in_common_space": True}
        
        # Ενημέρωση φίλτρων αναζήτησης από query params
        if 'q' in filter_data and filter_data['q']:
            search_term = filter_data['q']
            # Αναζήτηση στα βασικά πεδία
            search_condition = [
                {"personal_details.first_name": {"$regex": search_term, "$options": "i"}},
                {"personal_details.last_name": {"$regex": search_term, "$options": "i"}},
                {"personal_details.amka": {"$regex": search_term, "$options": "i"}}
            ]
            
            # Συνδυάζουμε με το υπάρχον φίλτρο
            query_filter = {
                "$and": [
                    {"is_in_common_space": True},
                    {"$or": search_condition}
                ]
            }
        
        # Άλλα φίλτρα από το React-Admin
        for key, value in filter_data.items():
            if key != 'q' and value:  # Παραλείπουμε το 'q' και κενές τιμές
                if key == 'id':
                    try:
                        query_filter['_id'] = ObjectId(value)
                    except InvalidId:
                        pass
                elif key.startswith('personal_details.'):
                    query_filter[key] = value
                    
                # Ειδική περίπτωση για το ΑΜΚΑ
                elif key == 'amka' and value:
                    query_filter['personal_details.amka'] = value
        
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
            "assigned_doctors": 1,
            "is_in_common_space": 1
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
            patient['id'] = str(patient.pop('_id')) 
            
            # Μετατροπή ObjectIDs σε strings στη λίστα assigned_doctors
            if 'assigned_doctors' in patient:
                patient['assigned_doctors'] = [str(doc_id) for doc_id in patient['assigned_doctors']]
            
            # Έλεγχος αν ο γιατρός είναι assigned στον ασθενή
            is_assigned = False
            if 'assigned_doctors' in patient:
                is_assigned = requesting_user_id_str in patient['assigned_doctors']
                
            # Προσθήκη πεδίου has_access
            patient['has_access'] = is_assigned
            
            patients_list.append(patient)
            count_in_page += 1

        # Δημιουργία response και προσθήκη header Content-Range
        resp = make_response(jsonify(patients_list), 200)
        range_end = (start + count_in_page - 1) if count_in_page > 0 else start
        resp.headers['Content-Range'] = f'{resource_name} {start}-{range_end}/{total_patients}'
        return resp
        
    except Exception as e:
        logger.error(f"Error fetching common space patients: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για λήψη συγκεκριμένου ασθενή από τον κοινό χώρο ---
@doctor_portal_bp.route('/common-space/patients/<string:patient_id>', methods=['GET'])
@jwt_required()
def get_common_space_patient(patient_id):
    """Επιστρέφει έναν συγκεκριμένο ασθενή από τον κοινό χώρο"""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Μετατροπή του ID σε ObjectId
        try:
            requesting_user_id = ObjectId(requesting_user_id_str)
            patient_object_id = ObjectId(patient_id)
        except InvalidId:
            return jsonify({"error": "Invalid ID format"}), 400
            
        # Έλεγχος δικαιωμάτων
        from utils.permissions import ViewPatientPermission
        view_permission = ViewPatientPermission(patient_id)
        if not view_permission.can():
            return jsonify({"error": "Δεν έχετε δικαίωμα προβολής αυτού του ασθενή"}), 403
        
        # Ανάκτηση του ασθενή
        patient = db.patients.find_one({
            "_id": patient_object_id,
            "is_in_common_space": True
        })
        
        if not patient:
            return jsonify({"error": "Ο ασθενής δεν βρέθηκε ή δεν βρίσκεται στον κοινό χώρο"}), 404
        
        # Μετατροπή του _id σε id για το frontend
        patient['id'] = str(patient.pop('_id'))
        
        # Μετατροπή λίστας assigned_doctors
        if 'assigned_doctors' in patient and isinstance(patient['assigned_doctors'], list):
            patient['assigned_doctors'] = [str(doc_id) for doc_id in patient['assigned_doctors']]
        
        # Μετατροπή timestamps
        if 'created_at' in patient and isinstance(patient['created_at'], datetime.datetime):
            patient['created_at'] = patient['created_at'].isoformat()
        if 'last_updated_at' in patient and isinstance(patient['last_updated_at'], datetime.datetime):
            patient['last_updated_at'] = patient['last_updated_at'].isoformat()
        
        # Έλεγχος αν ο γιατρός είναι assigned στον ασθενή
        is_assigned = False
        if 'assigned_doctors' in patient:
            is_assigned = requesting_user_id_str in patient['assigned_doctors']
        
        # Για common space ασθενείς, έλεγχος edit permissions
        can_edit_patient = is_assigned or patient.get('is_in_common_space', False)
            
        # Προσθήκη πεδίων has_access και can_edit
        patient['has_access'] = is_assigned or patient.get('is_in_common_space', False)
        patient['can_edit'] = can_edit_patient
        
        # Αφαίρεση του password hash αν υπάρχει
        if 'account_details' in patient and 'password_hash' in patient['account_details']:
            del patient['account_details']['password_hash']
        
        return jsonify(patient), 200
        
    except Exception as e:
        logger.error(f"Error fetching common space patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500 