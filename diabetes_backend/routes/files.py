from flask import Blueprint, jsonify, request, current_app, make_response, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from bson.objectid import ObjectId
from bson.errors import InvalidId
import os
import logging
import json
import datetime
from werkzeug.utils import secure_filename
from utils.db import get_db
from utils.file_utils import allowed_file, extract_text_from_pdf
from config.config import UPLOAD_FOLDER
from utils.permissions import ViewPatientPermission, EditPatientPermission, EditFilePermission, permission_denied

# Ρύθμιση logger
logger = logging.getLogger(__name__)

# Δημιουργία blueprint
files_bp = Blueprint('files', __name__, url_prefix='/api/patients')

# Η σύνδεση στη βάση δεδομένων
db = get_db()

# Βοηθητική συνάρτηση για τον έλεγχο επιτρεπόμενου τύπου αρχείου
def allowed_file(filename):
    ALLOWED_EXTENSIONS = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'png', 'jpg', 'jpeg', 'txt', 'csv'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@files_bp.route('/<string:patient_id>/files', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def get_patient_files(patient_id):
    """Επιστρέφει λίστα με όλα τα αρχεία ενός ασθενή - Για συμβατότητα με το frontend"""
    # Παίρνουμε την ταυτότητα του χρήστη που κάνει το request, με ασφαλή τρόπο
    try:
        # Εφόσον έχουμε optional=True, πρέπει να ελέγξουμε αν υπάρχει JWT πριν καλέσουμε get_jwt_identity
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        
        # Προσπαθούμε να επαληθεύσουμε το JWT χωρίς να απαιτείται (optional=True)
        verify_jwt_in_request(optional=True)
        requesting_user_id_str = get_jwt_identity()
    except Exception as e:
        logger.debug(f"No valid JWT found or error in JWT verification: {e}")
        requesting_user_id_str = None
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Μετατροπή IDs σε ObjectId
        patient_object_id = ObjectId(patient_id)
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400

    try:
        # Έλεγχος εξουσιοδότησης μόνο αν έχουμε ταυτοποιημένο χρήστη
        if requesting_user_id_str:
            view_permission = ViewPatientPermission(patient_id)
            if not view_permission.can():
                return permission_denied("Δεν έχετε δικαίωμα προβολής των αρχείων αυτού του ασθενή")
        
        # --- React-admin Pagination & Sorting Params --- 
        # Παράμετροι για range
        range_param = request.args.get('range')
        if range_param:
            try:
                range_json = json.loads(range_param)
                start, end = range_json[0], range_json[1]
            except (json.JSONDecodeError, IndexError, TypeError):
                start, end = 0, 99  # default
        else:
            start = request.args.get('_start', default=0, type=int)
            end = request.args.get('_end', default=99, type=int)
        
        # Παράμετροι για sort
        sort_param = request.args.get('sort')
        if sort_param:
            try:
                sort_json = json.loads(sort_param)
                sort_by, order = sort_json[0], sort_json[1].upper()
            except (json.JSONDecodeError, IndexError, TypeError):
                sort_by, order = "upload_date", "DESC"  # default
        else:
            sort_by = request.args.get('_sort', default='upload_date')
            order = request.args.get('_order', default='DESC').upper()
        
        resource_name = 'files'
        # ---------------------------------------------
        
        # Φίλτρα αναζήτησης από τα query params
        filter_param = request.args.get('filter')
        filter_data = {}
        if filter_param:
            try:
                filter_data = json.loads(filter_param)
            except json.JSONDecodeError:
                pass  # Αγνόηση προβληματικών φίλτρων
                
        # Βρίσκουμε τον ασθενή και παίρνουμε τη λίστα των αρχείων του
        patient = db.patients.find_one({"_id": patient_object_id}, {"uploaded_files": 1})
        
        if not patient or 'uploaded_files' not in patient:
            # Δεν βρέθηκε ασθενής ή δεν έχει αρχεία
            files_list = []
            total_files = 0
        else:
            # Παίρνουμε τη λίστα με τα αρχεία
            files_list = patient['uploaded_files']
            
            # Εφαρμογή φίλτρων (αν υπάρχουν)
            filtered_files = []
            for file in files_list:
                # Φιλτράρισμα με βάση το 'q' (αναζήτηση)
                if 'q' in filter_data and filter_data['q']:
                    search_term = filter_data['q'].lower()
                    found = False
                    # Αναζήτηση σε βασικά πεδία
                    for field in ['filename', 'original_filename', 'description']:
                        if field in file and search_term in str(file[field]).lower():
                            found = True
                            break
                    if not found:
                        continue
                
                # Φιλτράρισμα με βάση το id
                if 'id' in filter_data and filter_data['id']:
                    if 'file_id' in file and file['file_id'] != filter_data['id']:
                        continue
                        
                # Άλλα φίλτρα
                skip_file = False
                for key, value in filter_data.items():
                    if key not in ['q', 'id'] and value:
                        if key not in file or file[key] != value:
                            skip_file = True
                            break
                if skip_file:
                    continue
                    
                # Προσθήκη στη λίστα φιλτραρισμένων αρχείων
                filtered_files.append(file)
            
            # Ταξινόμηση
            reverse = order == 'DESC'
            try:
                filtered_files.sort(
                    key=lambda x: (str(x.get(sort_by, '')).lower() if sort_by in x else ''),
                    reverse=reverse
                )
            except Exception as e:
                logger.error(f"Error sorting files: {e}")
                # Αν αποτύχει η ταξινόμηση, χρησιμοποιούμε τη λίστα όπως είναι
            
            # Pagination
            total_files = len(filtered_files)
            if start < len(filtered_files):
                end_pos = min(end + 1, len(filtered_files))
                files_list = filtered_files[start:end_pos]
            else:
                files_list = []
        
        # Μετατροπές σε κάθε αρχείο
        processed_files = []
        for file in files_list:
            file_copy = file.copy()  # Δημιουργούμε αντίγραφο για να μην επηρεάσουμε το πρωτότυπο
            
            # Μετατροπή του file_id σε id για το frontend
            if 'file_id' in file_copy:
                file_copy['id'] = file_copy['file_id']
                
            # Μετατροπή timestamps
            if 'upload_date' in file_copy and isinstance(file_copy['upload_date'], datetime.datetime):
                file_copy['upload_date'] = file_copy['upload_date'].isoformat()
                
            # Αφαίρεση του extracted_text
            if 'extracted_text' in file_copy:
                del file_copy['extracted_text']
                
            processed_files.append(file_copy)
            
        # Δημιουργία response με Content-Range header
        resp = make_response(jsonify(processed_files), 200)
        if total_files > 0:
            resp.headers['Content-Range'] = f'{resource_name} {start}-{min(start + len(processed_files) - 1, total_files - 1)}/{total_files}'
        else:
            resp.headers['Content-Range'] = f'{resource_name} 0-0/0'
        return resp
        
    except Exception as e:
        logger.error(f"Error listing files for patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@files_bp.route('/<string:patient_id>/files', methods=['POST'])
@jwt_required()
def upload_patient_file(patient_id):
    """Ανεβάζει ένα αρχείο για έναν ασθενή"""
    # Εδώ το jwt_required είναι υποχρεωτικό (όχι optional)
    requesting_user_id_str = get_jwt_identity()
    
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Μετατροπή ID σε ObjectId
        patient_object_id = ObjectId(patient_id)
    except InvalidId:
        return jsonify({"error": "Invalid patient ID format"}), 400

    # Έλεγχος εξουσιοδότησης
    view_permission = ViewPatientPermission(patient_id)
    if not view_permission.can():
        return permission_denied("Δεν έχετε δικαίωμα ανεβάσματος αρχείων για αυτόν τον ασθενή")

    # Έλεγχος αν στάλθηκε αρχείο στο request
    if 'file' not in request.files:
        logger.error("Missing 'file' key in form data")
        return jsonify({
            "error": "Bad Request: Missing 'file' key in form data.", 
            "details": "Ensure you are sending the file using multipart/form-data with the key named 'file'"
        }), 400
        
    file = request.files['file']
    if file.filename == '':
        logger.error("No file selected")
        return jsonify({
            "error": "Bad Request: No file selected.", 
            "details": "The 'file' part was sent, but no actual file was selected."
        }), 400

    # Έλεγχος επιτρεπόμενου τύπου αρχείου
    if not allowed_file(file.filename):
        allowed_types_str = ", ".join(current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'png', 'jpg', 'jpeg', 'txt', 'csv'}))
        return jsonify({
            "error": "Bad Request: File type not allowed.", 
            "details": f"The uploaded file type is not permitted. Allowed types: {allowed_types_str}"
        }), 400

    # Αποθήκευση αρχείου
    try:
        from werkzeug.utils import secure_filename
        import os
        import mimetypes
        import datetime
        
        # Δημιουργία ασφαλούς ονόματος αρχείου
        original_filename = secure_filename(file.filename)
        filename = original_filename  # Προς το παρόν κρατάμε το ασφαλές αρχικό όνομα
        
        # Δημιουργία φακέλου για τον ασθενή αν δεν υπάρχει
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        patient_upload_folder = os.path.join(upload_folder, patient_id)
        os.makedirs(patient_upload_folder, exist_ok=True)
        
        # Αποθήκευση του αρχείου
        file_path = os.path.join(patient_upload_folder, filename)
        file.save(file_path)
        
        # Λήψη τύπου αρχείου (MIME type)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Δημιουργία εγγραφής για τη βάση δεδομένων
        file_metadata = {
            "file_id": str(ObjectId()),  # Δίνουμε ένα νέο μοναδικό ID και στο αρχείο
            "filename": filename,  # Το ασφαλές όνομα αρχείου
            "original_filename": original_filename,  # Το αρχικό όνομα (για εμφάνιση)
            "file_path": file_path.replace(upload_folder, '').lstrip(os.sep),  # Σχετική διαδρομή
            "mime_type": mime_type or 'application/octet-stream',
            "upload_date": datetime.datetime.now(datetime.timezone.utc),
            "size_bytes": os.path.getsize(file_path),
            "uploaded_by": requesting_user_id_str,  # ID του χρήστη που ανέβασε το αρχείο
            "extracted_text": None  # Placeholder για το OCR κείμενο
        }
        
        # Ενημέρωση του ασθενή στη βάση δεδομένων (προσθήκη στη λίστα uploaded_files)
        update_result = db.patients.update_one(
            {"_id": patient_object_id},
            {
                "$push": {"uploaded_files": file_metadata},
                "$currentDate": {"last_updated_at": True}
            }
        )
        
        if update_result.modified_count == 1:
            # Εκτέλεση OCR αν είναι PDF
            ocr_text = "[OCR not attempted or failed]"  # Default τιμή
            if file_metadata['mime_type'] == 'application/pdf':
                try:
                    from utils.file_utils import extract_text_from_pdf
                    
                    logger.info(f"Attempting OCR for file: {file_path}")
                    absolute_file_path = os.path.join(upload_folder, file_metadata['file_path'])
                    ocr_text = extract_text_from_pdf(absolute_file_path)
                    logger.info(f"OCR finished for {filename}. Extracted ~{len(ocr_text)} chars.")
                    
                    # Ενημέρωση της εγγραφής του αρχείου με το κείμενο OCR
                    db.patients.update_one(
                        {"_id": patient_object_id, "uploaded_files.file_id": file_metadata["file_id"]},
                        {"$set": {"uploaded_files.$.extracted_text": ocr_text}}
                    )
                    logger.info(f"Updated DB record for file {file_metadata['file_id']} with OCR text.")
                except Exception as ocr_err:
                    logger.error(f"OCR processing error: {ocr_err}")
            else:
                logger.info(f"Skipping OCR for non-PDF file: {filename} (MIME: {file_metadata['mime_type']})")
            
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
            # Προσπάθεια καθαρισμού αν η ενημέρωση της βάσης απέτυχε
            try:
                os.remove(file_path)
            except OSError as e:
                logger.error(f"Error removing file after DB update failure: {e}")
            return jsonify({"error": "Failed to update patient record with file info"}), 500
            
    except Exception as e:
        logger.error(f"Error during file upload: {e}")
        return jsonify({"error": f"An internal server error occurred during file upload: {str(e)}"}), 500
        
@files_bp.route('/<string:patient_id>/files/<string:file_id>', methods=['GET'])
@jwt_required()
def get_file(patient_id, file_id):
    """Επιστρέφει πληροφορίες για ένα συγκεκριμένο αρχείο"""
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
        # Έλεγχος εξουσιοδότησης με το νέο σύστημα δικαιωμάτων
        view_permission = ViewPatientPermission(patient_id)
        if not view_permission.can():
            return permission_denied("Δεν έχετε δικαίωμα προβολής των αρχείων αυτού του ασθενή")
            
        # Εύρεση του ασθενή και του συγκεκριμένου αρχείου
        patient = db.patients.find_one(
            {"_id": patient_object_id, "uploaded_files.file_id": file_id},
            {"uploaded_files.$": 1}  # Επιστρέφει μόνο το αρχείο που ταιριάζει
        )
        
        if not patient or 'uploaded_files' not in patient or not patient['uploaded_files']:
            return jsonify({"error": "File not found or does not belong to this patient"}), 404
            
        # Παίρνουμε το πρώτο (και μοναδικό) αρχείο από το αποτέλεσμα
        file = patient['uploaded_files'][0]
        
        # Μετατροπές για το frontend
        file_copy = file.copy()  # Χρήση αντιγράφου για να μην επηρεαστεί το πρωτότυπο
        
        # Μετατροπή του file_id σε id για το frontend
        if 'file_id' in file_copy:
            file_copy['id'] = file_copy['file_id']
            
        # Μετατροπή timestamps
        if 'upload_date' in file_copy and isinstance(file_copy['upload_date'], datetime.datetime):
            file_copy['upload_date'] = file_copy['upload_date'].isoformat()
            
        return jsonify(file_copy), 200
        
    except Exception as e:
        logger.error(f"Error getting file {file_id} for patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500
        
@files_bp.route('/<string:patient_id>/files/<string:file_id>', methods=['DELETE'])
@jwt_required()
def delete_file(patient_id, file_id):
    """Διαγράφει ένα αρχείο"""
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
        # Έλεγχος εξουσιοδότησης με το νέο σύστημα δικαιωμάτων
        edit_permission = EditFilePermission(patient_id, file_id)
        if not edit_permission.can():
            return permission_denied("Δεν έχετε δικαίωμα διαγραφής αρχείων αυτού του ασθενή")
            
        # Εύρεση του ασθενή και του συγκεκριμένου αρχείου
        patient = db.patients.find_one(
            {"_id": patient_object_id, "uploaded_files.file_id": file_id},
            {"uploaded_files.$": 1}  # Επιστρέφει μόνο το αρχείο που ταιριάζει
        )
        
        if not patient or 'uploaded_files' not in patient or not patient['uploaded_files']:
            return jsonify({"error": "File not found or does not belong to this patient"}), 404
            
        # Παίρνουμε το πρώτο (και μοναδικό) αρχείο από το αποτέλεσμα
        file = patient['uploaded_files'][0]
        
        # Αφαίρεση της εγγραφής από τη λίστα uploaded_files του ασθενή
        update_result = db.patients.update_one(
            {"_id": patient_object_id},
            {"$pull": {"uploaded_files": {"file_id": file_id}}}
        )
        
        if update_result.modified_count == 1:
            # Διαγραφή του αρχείου από το filesystem
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            file_path = os.path.join(upload_folder, file.get('file_path', ''))
            
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted file from disk: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting file from filesystem: {e}")
                    # Συνεχίζουμε ακόμα κι αν η διαγραφή του αρχείου αποτύχει
            
            return jsonify({"message": "File deleted successfully"}), 200
        else:
            return jsonify({"error": "Failed to remove file from patient record"}), 500
        
    except Exception as e:
        logger.error(f"Error deleting file {file_id} for patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500
        
@files_bp.route('/<string:patient_id>/files/<string:file_id>/download', methods=['GET'])
@jwt_required()
def download_file(patient_id, file_id):
    """Επιτρέπει τη λήψη ενός αρχείου"""
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
        # Έλεγχος εξουσιοδότησης με το νέο σύστημα δικαιωμάτων
        view_permission = ViewPatientPermission(patient_id)
        if not view_permission.can():
            return permission_denied("Δεν έχετε δικαίωμα λήψης των αρχείων αυτού του ασθενή")
            
        # Εύρεση του ασθενή και του συγκεκριμένου αρχείου
        patient = db.patients.find_one(
            {"_id": patient_object_id, "uploaded_files.file_id": file_id},
            {"uploaded_files.$": 1}  # Επιστρέφει μόνο το αρχείο που ταιριάζει
        )
        
        if not patient or 'uploaded_files' not in patient or not patient['uploaded_files']:
            return jsonify({"error": "File not found or does not belong to this patient"}), 404
            
        # Παίρνουμε το πρώτο (και μοναδικό) αρχείο από το αποτέλεσμα
        file = patient['uploaded_files'][0]
        
        # Λαμβάνουμε τις πληροφορίες διαδρομής του αρχείου
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        file_path = file.get('file_path', '')
        filename = file.get('filename', '')
        
        if not file_path or not filename:
            return jsonify({"error": "Invalid file metadata - missing path or filename"}), 500
            
        # Κατασκευή της πλήρους διαδρομής του αρχείου
        full_directory = os.path.dirname(os.path.join(upload_folder, file_path))
        
        # Έλεγχος αν το αρχείο υπάρχει
        absolute_file_path = os.path.join(upload_folder, file_path)
        if not os.path.exists(absolute_file_path):
            logger.error(f"File not found on disk: {absolute_file_path}")
            return jsonify({"error": "File not found on server storage"}), 404
            
        # Αποστολή του αρχείου
        return send_from_directory(
            directory=full_directory,
            path=os.path.basename(file_path),
            as_attachment=True,
            download_name=file.get('original_filename', filename)
        )
        
    except Exception as e:
        logger.error(f"Error downloading file {file_id} for patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@files_bp.route('/<string:patient_id>/files/metadata', methods=['GET'])
@jwt_required()
def get_files_metadata(patient_id):
    """Επιστρέφει πληροφορίες για τα αρχεία ενός ασθενή συμπεριλαμβανομένου του extracted_text"""
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
        # Έλεγχος εξουσιοδότησης με το σύστημα δικαιωμάτων
        view_permission = ViewPatientPermission(patient_id)
        if not view_permission.can():
            return permission_denied("Δεν έχετε δικαίωμα προβολής των αρχείων αυτού του ασθενή")
            
        # Εύρεση του ασθενή και των αρχείων του
        patient = db.patients.find_one({"_id": patient_object_id}, {"uploaded_files": 1})
        
        if not patient or 'uploaded_files' not in patient:
            return jsonify({"error": "Patient not found or has no files"}), 404
            
        # Ανάλυση τιμών extracted_text
        files_info = []
        for file in patient['uploaded_files']:
            file_copy = file.copy()
            
            # Μετατροπή του file_id σε id για το frontend
            if 'file_id' in file_copy:
                file_copy['id'] = file_copy['file_id']
                
            # Μετατροπή timestamps
            if 'upload_date' in file_copy and isinstance(file_copy['upload_date'], datetime.datetime):
                file_copy['upload_date'] = file_copy['upload_date'].isoformat()
                
            # Ελέγχουμε αν υπάρχει extracted_text και αν έχει περιεχόμενο
            has_text = False
            text_sample = "N/A"
            if 'extracted_text' in file_copy:
                if file_copy['extracted_text']:
                    has_text = True
                    # Παίρνουμε ένα δείγμα του κειμένου
                    text = file_copy['extracted_text']
                    text_sample = text[:100] + "..." if len(text) > 100 else text
                del file_copy['extracted_text']  # Αφαιρούμε το πλήρες κείμενο από την απάντηση
            
            file_copy['has_extracted_text'] = has_text
            file_copy['text_sample'] = text_sample
            files_info.append(file_copy)
            
        return jsonify({
            "files_count": len(files_info),
            "files_with_text": sum(1 for f in files_info if f['has_extracted_text']),
            "files": files_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting file metadata for patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500 