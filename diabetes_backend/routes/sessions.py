from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from bson.errors import InvalidId
import datetime
import json
import os
import logging
from utils.db import get_db
from config.config import UPLOAD_FOLDER
from werkzeug.utils import secure_filename
from utils.file_utils import allowed_file, extract_text_from_pdf

# Ρύθμιση logger
logger = logging.getLogger(__name__)

# Δημιουργία blueprint
sessions_bp = Blueprint('sessions', __name__, url_prefix='/api/sessions')

# Η σύνδεση στη βάση δεδομένων
db = get_db()

# --- Endpoint για λήψη όλων των συνεδριών ---
@sessions_bp.route('', methods=['GET'])
@jwt_required()
def get_sessions():
    """Επιστρέφει λίστα με όλες τις συνεδρίες του γιατρού"""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Μετατροπή σε ObjectId
        requesting_user_id = ObjectId(requesting_user_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid doctor ID format"}), 400

    try:
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
                sort_by, order = "timestamp", "DESC"  # default
        else:
            sort_by = request.args.get('_sort', default='timestamp')
            order = request.args.get('_order', default='DESC').upper()
            
        # Μετατροπή του sort_by 'id' σε '_id' για MongoDB
        if sort_by == 'id':
            sort_by = '_id'
            
        sort_direction = 1 if order == 'ASC' else -1
        limit = (end - start) + 1
        skip = start
        resource_name = 'sessions'
        # ---------------------------------------------

        # Φίλτρα αναζήτησης
        filter_param = request.args.get('filter')
        filter_data = {}
        if filter_param:
            try:
                filter_data = json.loads(filter_param)
            except json.JSONDecodeError:
                pass  # Αγνόηση προβληματικών φίλτρων
                
        # Βασικό φίλτρο: Ο γιατρός βλέπει μόνο τις δικές του συνεδρίες
        query_filter = {
            "doctor_id": requesting_user_id
        }
        
        # Προσθήκη επιπλέον φίλτρων από query params
        if 'patient_id' in filter_data and filter_data['patient_id']:
            try:
                patient_id = ObjectId(filter_data['patient_id'])
                query_filter['patient_id'] = patient_id
            except InvalidId:
                pass
                
        if 'session_type' in filter_data and filter_data['session_type']:
            query_filter['session_type'] = filter_data['session_type']
            
        # Επιπλέον φίλτρα για εύρος ημερομηνιών
        if 'date_from' in filter_data and filter_data['date_from']:
            try:
                date_from = datetime.datetime.fromisoformat(filter_data['date_from'])
                query_filter['timestamp'] = {"$gte": date_from}
            except (ValueError, TypeError):
                pass
                
        if 'date_to' in filter_data and filter_data['date_to']:
            try:
                date_to = datetime.datetime.fromisoformat(filter_data['date_to'])
                if 'timestamp' in query_filter and isinstance(query_filter['timestamp'], dict):
                    query_filter['timestamp']["$lte"] = date_to
                else:
                    query_filter['timestamp'] = {"$lte": date_to}
            except (ValueError, TypeError):
                pass
                
        # Μέτρηση συνόλου συνεδριών (με βάση το φίλτρο)
        total_sessions = db.sessions.count_documents(query_filter)
        
        # Ανάκτηση δεδομένων με pagination και sorting
        sessions_cursor = db.sessions.find(query_filter)\
                           .sort(sort_by, sort_direction)\
                           .skip(skip)
        if limit > 0:
             sessions_cursor = sessions_cursor.limit(limit)
             
        sessions_list = []
        count_in_page = 0
        
        # Διαπέραση των αποτελεσμάτων
        for session in sessions_cursor:
            # Μετατροπή τύπων για JSON serialization
            session['id'] = str(session.pop('_id'))
            
            # Μετατροπή ObjectIds
            if 'doctor_id' in session and isinstance(session['doctor_id'], ObjectId):
                session['doctor_id'] = str(session['doctor_id'])
            if 'patient_id' in session and isinstance(session['patient_id'], ObjectId):
                session['patient_id'] = str(session['patient_id'])
                
            # Μετατροπή timestamps
            if 'timestamp' in session and isinstance(session['timestamp'], datetime.datetime):
                session['timestamp'] = session['timestamp'].isoformat()
                
            # Προσθήκη στη λίστα
            sessions_list.append(session)
            count_in_page += 1
            
        # Δημιουργία response και προσθήκη header Content-Range
        resp = make_response(jsonify(sessions_list), 200)
        range_end = (start + count_in_page - 1) if count_in_page > 0 else start
        resp.headers['Content-Range'] = f'{resource_name} {start}-{range_end}/{total_sessions}'
        return resp
        
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για λήψη στοιχείων συγκεκριμένης συνεδρίας ---
@sessions_bp.route('/<string:session_id>', methods=['GET'])
@jwt_required()
def get_session_by_id(session_id):
    """Επιστρέφει τα πλήρη στοιχεία μιας συνεδρίας."""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Μετατροπή IDs σε ObjectId
        requesting_user_id = ObjectId(requesting_user_id_str)
        session_object_id = ObjectId(session_id)
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400

    try:
        # Έλεγχος εξουσιοδότησης: Βρίσκουμε τη συνεδρία μόνο αν ανήκει στον γιατρό
        session = db.sessions.find_one({
            "_id": session_object_id,
            "doctor_id": requesting_user_id
        })

        if session:
            # Μετατροπές για JSON serialization
            session['id'] = str(session.pop('_id'))
            
            # Μετατροπή ObjectIds
            if 'doctor_id' in session and isinstance(session['doctor_id'], ObjectId):
                session['doctor_id'] = str(session['doctor_id'])
            if 'patient_id' in session and isinstance(session['patient_id'], ObjectId):
                session['patient_id'] = str(session['patient_id'])
                
            # Μετατροπή timestamps
            if 'timestamp' in session and isinstance(session['timestamp'], datetime.datetime):
                session['timestamp'] = session['timestamp'].isoformat()
                
            return jsonify(session), 200
        else:
            # Η συνεδρία δεν βρέθηκε ή ο γιατρός δεν έχει πρόσβαση
            return jsonify({"error": "Session not found or you don't have permission to view this session"}), 404

    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για προσθήκη νέας συνεδρίας ---
@sessions_bp.route('', methods=['POST'])
@jwt_required()
def add_session():
    """Προσθέτει μια νέα συνεδρία στη βάση."""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        requesting_user_id = ObjectId(requesting_user_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid doctor ID format"}), 400

    # Έλεγχος εάν το request είναι multipart/form-data ή application/json
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        # Χειρισμός ανεβάσματος αρχείου
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
            
        patient_id_str = request.form.get('patient_id')
        if not patient_id_str:
            return jsonify({"error": "Patient ID is required"}), 400
            
        try:
            patient_id = ObjectId(patient_id_str)
        except InvalidId:
            return jsonify({"error": "Invalid patient ID format"}), 400
            
        # Έλεγχος εξουσιοδότησης: Ο ασθενής πρέπει να είναι ανατεθειμένος στον γιατρό
        patient_exists = db.patients.find_one({
            "_id": patient_id,
            "assigned_doctors": requesting_user_id
        })
        
        if not patient_exists:
            return jsonify({"error": "Patient not found or you don't have permission"}), 403
            
        # Έλεγχος αρχείου και αποθήκευση
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            # Δημιουργία φακέλου για τον ασθενή αν δεν υπάρχει
            patient_folder = os.path.join(UPLOAD_FOLDER, str(patient_id))
            os.makedirs(patient_folder, exist_ok=True)
            
            # Αποθήκευση αρχείου
            file_path = os.path.join(patient_folder, filename)
            file.save(file_path)
            
            # Εξαγωγή κειμένου από PDF αν είναι PDF
            file_content = None
            if filename.lower().endswith('.pdf'):
                file_content = extract_text_from_pdf(file_path)
            
            # Δημιουργία εγγραφής συνεδρίας
            session_data = {
                "doctor_id": requesting_user_id,
                "patient_id": patient_id,
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "session_type": "file_upload",
                "file_info": {
                    "filename": filename,
                    "path": os.path.join(str(patient_id), filename),
                    "content_type": file.content_type
                }
            }
            
            if file_content:
                session_data["file_content"] = file_content
                
            # Αποθήκευση στη βάση
            result = db.sessions.insert_one(session_data)
            
            # Ενημέρωση του last_consultation_date του ασθενή
            db.patients.update_one(
                {"_id": patient_id},
                {"$set": {"last_consultation_date": session_data["timestamp"]}}
            )
            
            # Διόρθωση: Ανάκτηση και επιστροφή του πλήρους record που δημιουργήθηκε
            new_session = db.sessions.find_one({"_id": result.inserted_id})
            if new_session:
                new_session['id'] = str(new_session.pop('_id'))
                # Μετατροπή ObjectIds σε strings
                if 'doctor_id' in new_session and isinstance(new_session['doctor_id'], ObjectId):
                    new_session['doctor_id'] = str(new_session['doctor_id'])
                if 'patient_id' in new_session and isinstance(new_session['patient_id'], ObjectId):
                    new_session['patient_id'] = str(new_session['patient_id'])
                # Μετατροπή timestamps σε ISO format
                if 'timestamp' in new_session and isinstance(new_session['timestamp'], datetime.datetime):
                    new_session['timestamp'] = new_session['timestamp'].isoformat()
                if 'followup_date' in new_session and new_session['followup_date'] and isinstance(new_session['followup_date'], datetime.datetime):
                    new_session['followup_date'] = new_session['followup_date'].isoformat()
                
                return jsonify(new_session), 201
            else:
                # Επιστροφή σφάλματος αν δεν βρεθεί το record (απίθανο)
                logger.error(f"Failed to retrieve newly created session with id {result.inserted_id}")
                return jsonify({"error": "Failed to retrieve created session"}), 500
        else:
            return jsonify({"error": "File type not allowed"}), 400
    else:
        # Χειρισμός JSON data
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400
            
        # Έλεγχος απαραίτητων πεδίων
        if 'patient_id' not in data:
            return jsonify({"error": "Patient ID is required"}), 400
            
        try:
            patient_id = ObjectId(data['patient_id'])
        except InvalidId:
            return jsonify({"error": "Invalid patient ID format"}), 400
            
        # Έλεγχος εξουσιοδότησης: Ο ασθενής πρέπει να είναι ανατεθειμένος στον γιατρό
        patient_exists = db.patients.find_one({
            "_id": patient_id,
            "assigned_doctors": requesting_user_id
        })
        
        if not patient_exists:
            return jsonify({"error": "Patient not found or you don't have permission"}), 403
            
        # Δημιουργία εγγραφής συνεδρίας
        session_data = {
            "doctor_id": requesting_user_id,
            "patient_id": patient_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "session_type": data.get('session_type', 'consultation'),
            # Προσαρμογή στα πεδία του frontend:
            "vitals_recorded": data.get('vitals_recorded', {}),
            "doctor_notes": data.get('doctor_notes', ''),
            "therapy_adjustments": data.get('therapy_adjustments', ''),
            "patient_reported_outcome": data.get('patient_reported_outcome', ''),
            "followup_date": None  # Default null
        }
        
        # Επεξεργασία followup_date αν παρέχεται
        if 'followup_date' in data and data['followup_date']:
            try:
                session_data['followup_date'] = datetime.datetime.fromisoformat(data['followup_date'])
            except (ValueError, TypeError):
                pass
                
        # Αποθήκευση στη βάση
        result = db.sessions.insert_one(session_data)
        
        # Ενημέρωση του last_consultation_date του ασθενή
        db.patients.update_one(
            {"_id": patient_id},
            {"$set": {"last_consultation_date": session_data["timestamp"]}}
        )
        
        # Διόρθωση: Ανάκτηση και επιστροφή του πλήρους record που δημιουργήθηκε (ίδιο με την περίπτωση file upload)
        new_session = db.sessions.find_one({"_id": result.inserted_id})
        if new_session:
            new_session['id'] = str(new_session.pop('_id'))
            # Μετατροπή ObjectIds σε strings
            if 'doctor_id' in new_session and isinstance(new_session['doctor_id'], ObjectId):
                new_session['doctor_id'] = str(new_session['doctor_id'])
            if 'patient_id' in new_session and isinstance(new_session['patient_id'], ObjectId):
                new_session['patient_id'] = str(new_session['patient_id'])
            # Μετατροπή timestamps σε ISO format
            if 'timestamp' in new_session and isinstance(new_session['timestamp'], datetime.datetime):
                new_session['timestamp'] = new_session['timestamp'].isoformat()
            if 'followup_date' in new_session and new_session['followup_date'] and isinstance(new_session['followup_date'], datetime.datetime):
                new_session['followup_date'] = new_session['followup_date'].isoformat()
                
            return jsonify(new_session), 201
        else:
            # Επιστροφή σφάλματος αν δεν βρεθεί το record (απίθανο)
            logger.error(f"Failed to retrieve newly created session with id {result.inserted_id}")
            return jsonify({"error": "Failed to retrieve created session"}), 500

# --- Endpoint για ενημέρωση συνεδρίας ---
@sessions_bp.route('/<string:session_id>', methods=['PATCH'])
@jwt_required()
def update_session(session_id):
    """Ενημερώνει τα στοιχεία μιας συνεδρίας."""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Μετατροπή IDs σε ObjectId
        requesting_user_id = ObjectId(requesting_user_id_str)
        session_object_id = ObjectId(session_id)
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400

    try:
        # Έλεγχος εξουσιοδότησης: Η συνεδρία πρέπει να ανήκει στον γιατρό
        session_exists = db.sessions.find_one({
            "_id": session_object_id,
            "doctor_id": requesting_user_id
        })
        
        if not session_exists:
            return jsonify({"error": "Session not found or you don't have permission to update this session"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        # Προετοιμασία δεδομένων για update
        update_data = {}
        
        # Επιτρεπόμενα πεδία για ενημέρωση
        allowed_fields = [
            'session_type', 
            'vitals_recorded', 
            'doctor_notes', 
            'therapy_adjustments', 
            'patient_reported_outcome', 
            'followup_date' 
        ]
        
        for field in allowed_fields:
            if field in data:
                # Ειδική επεξεργασία για το followup_date
                if field == 'followup_date' and data[field]:
                    try:
                        update_data[field] = datetime.datetime.fromisoformat(data[field])
                    except (ValueError, TypeError):
                        return jsonify({"error": f"Invalid format for {field}"}), 400
                elif field == 'vitals_recorded':
                     # Έλεγχος ότι τα vitals είναι dictionary
                     if isinstance(data[field], dict):
                         update_data[field] = data[field]
                     else:
                         logger.warning(f"Received non-dict data for vitals_recorded: {data[field]}")
                         # Αποφασίζουμε να το αγνοήσουμε ή να επιστρέψουμε σφάλμα;
                         # Προς το παρόν το αγνοούμε.
                         pass 
                else:
                    update_data[field] = data[field]
                    
        # Έλεγχος αν υπάρχουν δεδομένα για ενημέρωση
        if not update_data:
            return jsonify({"error": "No updatable fields provided"}), 400
            
        # Ενημέρωση
        result = db.sessions.update_one(
            {"_id": session_object_id, "doctor_id": requesting_user_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            # Αυτό δεν θα έπρεπε να συμβεί αφού ελέγξαμε την ύπαρξη
            return jsonify({"error": "Session not found or permission denied"}), 404
        elif result.modified_count >= 0: # Ακόμα κι αν δεν άλλαξε κάτι, επιστρέφουμε το record
             # Επιστροφή του ενημερωμένου record όπως περιμένει το react-admin
             updated_session = db.sessions.find_one({"_id": session_object_id})
             if updated_session:
                 updated_session['id'] = str(updated_session.pop('_id'))
                 if 'doctor_id' in updated_session and isinstance(updated_session['doctor_id'], ObjectId):
                     updated_session['doctor_id'] = str(updated_session['doctor_id'])
                 if 'patient_id' in updated_session and isinstance(updated_session['patient_id'], ObjectId):
                     updated_session['patient_id'] = str(updated_session['patient_id'])
                 if 'timestamp' in updated_session and isinstance(updated_session['timestamp'], datetime.datetime):
                     updated_session['timestamp'] = updated_session['timestamp'].isoformat()
                 if 'followup_date' in updated_session and updated_session['followup_date'] and isinstance(updated_session['followup_date'], datetime.datetime):
                     updated_session['followup_date'] = updated_session['followup_date'].isoformat()
                     
                 return jsonify(updated_session), 200 # Επιστρέφουμε το πλήρες αντικείμενο
             else:
                 logger.error(f"Failed to retrieve session {session_id} after update.")
                 return jsonify({"error": "Failed to retrieve updated session data"}), 500
        # else: # Αυτή η συνθήκη δεν χρειάζεται πια
        #     # Αν result.matched_count == 1 και modified_count == 0
        #     return jsonify({"message": "Session found but no changes were applied"}), 200

    except Exception as e:
        logger.error(f"Error updating session {session_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για διαγραφή συνεδρίας ---
@sessions_bp.route('/<string:session_id>', methods=['DELETE'])
@jwt_required()
def delete_session(session_id):
    """Διαγράφει μια συνεδρία από τη βάση."""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Μετατροπή IDs σε ObjectId
        requesting_user_id = ObjectId(requesting_user_id_str)
        session_object_id = ObjectId(session_id)
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400

    try:
        # Έλεγχος εξουσιοδότησης και λήψη λεπτομερειών συνεδρίας
        session = db.sessions.find_one({
            "_id": session_object_id,
            "doctor_id": requesting_user_id
        })
        
        if not session:
            return jsonify({"error": "Session not found or you don't have permission to delete this session"}), 404
            
        # Έλεγχος αν υπάρχει αρχείο για διαγραφή
        file_to_delete = None
        if 'file_info' in session and 'path' in session['file_info']:
            file_to_delete = os.path.join(UPLOAD_FOLDER, session['file_info']['path'])
            
        # Διαγραφή της συνεδρίας
        result = db.sessions.delete_one({"_id": session_object_id})
        
        # Διαγραφή του αρχείου αν υπάρχει
        if file_to_delete and os.path.exists(file_to_delete):
            try:
                os.remove(file_to_delete)
                logger.info(f"File {file_to_delete} deleted successfully.")
            except Exception as file_err:
                logger.error(f"Error deleting file {file_to_delete}: {file_err}")
                # Συνεχίζουμε παρόλο που το αρχείο δεν διαγράφηκε
        
        if result.deleted_count == 1:
            return jsonify({
                "message": "Session deleted successfully",
                "file_deleted": file_to_delete is not None
            }), 200
        else:
            # Αυτό δεν πρέπει να συμβεί ποτέ, αφού ήδη ελέγξαμε ότι η συνεδρία υπάρχει
            return jsonify({"error": "Session not found"}), 404

    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500