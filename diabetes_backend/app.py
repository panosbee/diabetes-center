from flask import Flask, jsonify, request, send_from_directory
from flask_jwt_extended import JWTManager, jwt_required
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO
import os
import logging
from datetime import datetime
import traceback
from bson.objectid import ObjectId
from pymongo import MongoClient

import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
# Εισαγωγή των επιμέρους modules
from config import JWT_SECRET_KEY, UPLOAD_FOLDER, MAX_CONTENT_LENGTH
from utils import init_db, get_db
from utils.permissions import initialize_permissions, ViewPatientPermission

# Εισαγωγή των blueprints
from routes import all_blueprints

# === Προσθήκη εισαγωγής για τους SocketIO handlers ===
from socket_handlers import register_socketio_handlers 

# Ρύθμιση logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(threadName)s : %(message)s'
)
logger = logging.getLogger(__name__)

# Δημιουργία της Flask εφαρμογής
app = Flask(__name__)

# Initialize genetics analyzer with DeepSeek integration
from services.genetics_analyzer import DMPGeneticsAnalyzer
from services.deepseek_integration import ask_rag_question

genetics_analyzer = DMPGeneticsAnalyzer(deepseek_function=ask_rag_question)

# Ρυθμίσεις εφαρμογής (πρέπει να γίνουν πριν την αρχικοποίηση των extensions που τις χρησιμοποιούν)
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['SECRET_KEY'] = JWT_SECRET_KEY # Use the same key for Flask session signing
print(f"DEBUG: JWT_SECRET_KEY in app.py after config set: {app.config.get('JWT_SECRET_KEY')}") # DEBUG LINE
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Quick debug - προσθέστε αυτό στο app.py
import os
from config.config import PUBMED_API_KEY, PUBMED_API_URL

logger.info(f"🔍 PUBMED DEBUG:")
logger.info(f"  - API Key exists: {bool(PUBMED_API_KEY)}")
logger.info(f"  - API Key length: {len(PUBMED_API_KEY) if PUBMED_API_KEY else 0}")
logger.info(f"  - API URL: {PUBMED_API_URL}")
logger.info(f"  - From env directly: {bool(os.environ.get('PUBMED_API_KEY'))}")

# Αρχικοποίηση extensions
jwt = JWTManager(app)
cors = CORS(app,
           resources={r"/api/*": {"origins": "*"}},
           expose_headers=["Content-Range", "X-Total-Count"])
bcrypt = Bcrypt(app) # Original simple initialization
if 'bcrypt' not in app.extensions: # Explicitly ensure it's in extensions
    app.extensions['bcrypt'] = bcrypt
socketio = SocketIO(app, cors_allowed_origins="*")

# === Καταχώρηση των SocketIO handlers ===
register_socketio_handlers(socketio)

# Αρχικοποίηση του συστήματος δικαιωμάτων
principal = initialize_permissions(app, jwt)

# Σύνδεση με τη βάση δεδομένων MongoDB
try:
    client = init_db()
    if isinstance(client, MongoClient):
        db = client["diabetes_db"]
    else:
        logger.error("init_db() did not return a MongoClient - creating new connection")
        client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
        db = client["diabetes_db"]
    logger.info("MongoDB connection successful")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise  # Crash the app if DB connection fails

# Έλεγχος αν υπάρχει ο φάκελος uploads και δημιουργία αν δεν υπάρχει
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === ΔΙΟΡΘΩΜΕΝΗ Καταχώρηση όλων των blueprints ===
registered_blueprints = []
failed_blueprints = []

for blueprint in all_blueprints:
    try:
        if blueprint is not None:
            # Έλεγχος αν το blueprint είναι ήδη καταχωρημένο
            if blueprint.name not in app.blueprints:
                app.register_blueprint(blueprint)
                registered_blueprints.append(blueprint.name)
                logger.info(f"✅ Registered blueprint: {blueprint.name}")
            else:
                logger.warning(f"⚠️ Blueprint {blueprint.name} already registered, skipping")
        else:
            logger.warning("⚠️ Encountered None blueprint in all_blueprints list")
    except Exception as e:
        failed_blueprints.append(f"{blueprint.name if blueprint else 'Unknown'}: {str(e)}")
        logger.error(f"❌ Failed to register blueprint {blueprint.name if blueprint else 'Unknown'}: {e}")

logger.info(f"📊 Blueprint registration summary:")
logger.info(f"  ✅ Successfully registered: {len(registered_blueprints)} - {registered_blueprints}")
logger.info(f"  ❌ Failed: {len(failed_blueprints)} - {failed_blueprints}")

# Register genetics routes
from services.genetics_analyzer import add_genetics_to_existing_routes
add_genetics_to_existing_routes(app, genetics_analyzer)

# Διαχείριση σφαλμάτων JWT
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_data):
    return jsonify({
        'message': 'The token has expired.',
        'error': 'token_expired'
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({
        'message': 'Signature verification failed.',
        'error': 'invalid_token'
    }), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({
        'message': 'Request does not contain an access token.',
        'error': 'authorization_required'
    }), 401

@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_data):
    return jsonify({
        'message': 'The token has been revoked.',
        'error': 'token_revoked'
    }), 401

# Γενικό endpoint για τον έλεγχο health της εφαρμογής
@app.route('/api/health', methods=['GET'])
def health_check():
    """Επιστρέφει την κατάσταση της εφαρμογής."""
    db_status = "OK" if get_db() is not None else "ERROR"
    
    return jsonify({
        'status': 'UP',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'database': db_status
        },
        'blueprints': {
            'registered': registered_blueprints,
            'failed': failed_blueprints,
            'total_count': len(registered_blueprints)
        }
    })

# Endpoint για πρόσβαση στα αρχεία που έχουν ανέβει
@app.route('/uploads/<string:patient_id>/<path:filename>')
def uploaded_file(patient_id, filename):
    """Επιστρέφει ένα αρχείο από τον φάκελο uploads."""
    directory = os.path.join(app.config['UPLOAD_FOLDER'], patient_id)
    return send_from_directory(directory, filename)

# --- Endpoint για πρόσβαση στα αρχεία (για συμβατότητα με το frontend) ---
@app.route('/api/files/<string:patient_id>/<string:file_id>', methods=['GET'])
@jwt_required()
def get_file_compat(patient_id, file_id):
    """Endpoint συμβατότητας για πρόσβαση σε αρχεία"""
    try:
        # Έλεγχος εξουσιοδότησης
        view_permission = ViewPatientPermission(patient_id)
        if not view_permission.can():
            return jsonify({"error": "Δεν έχετε δικαίωμα προβολής των αρχείων αυτού του ασθενή"}), 403
        
        # Εύρεση του ασθενή και του συγκεκριμένου αρχείου
        patient = db.patients.find_one(
            {"_id": ObjectId(patient_id), "uploaded_files.file_id": file_id},
            {"uploaded_files.$": 1}  # Επιστρέφει μόνο το αρχείο που ταιριάζει
        )
        
        if not patient or 'uploaded_files' not in patient or not patient['uploaded_files']:
            return jsonify({"error": "File not found or does not belong to this patient"}), 404
            
        # Παίρνουμε το πρώτο (και μοναδικό) αρχείο από το αποτέλεσμα
        file = patient['uploaded_files'][0]
        
        # Λαμβάνουμε τις πληροφορίες διαδρομής του αρχείου
        upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        file_path = file.get('file_path', '')
        filename = file.get('filename', '')
        
        if not file_path or not filename:
            return jsonify({"error": "Invalid file metadata - missing path or filename"}), 500
            
        # Κατασκευή της πλήρους διαδρομής του αρχείου
        # Προσοχή: Το file_path μπορεί να είναι μόνο το όνομα αρχείου ή να περιέχει και το patient_id
        # Θα προσπαθήσουμε να χειριστούμε και τις δύο περιπτώσεις
        
        patient_directory = os.path.join(upload_folder, patient_id)
        
        # Έλεγχος αν το file_path περιέχει τον φάκελο με το patient_id
        if patient_id in file_path:
            # Το file_path είναι κάτι σαν "patient_id/filename" 
            absolute_file_path = os.path.join(upload_folder, file_path)
            directory_path = os.path.dirname(absolute_file_path)
            file_basename = os.path.basename(file_path)
        else:
            # Το file_path είναι απλώς το όνομα του αρχείου
            directory_path = patient_directory
            absolute_file_path = os.path.join(directory_path, filename)
            file_basename = filename
        
        logger.info(f"Serving file: {absolute_file_path}, directory: {directory_path}, basename: {file_basename}")
        
        # Έλεγχος αν το αρχείο υπάρχει
        if not os.path.exists(absolute_file_path):
            # Δοκιμάζουμε εναλλακτική διαδρομή αν η πρώτη αποτύχει
            alternative_path = os.path.join(patient_directory, filename)
            if os.path.exists(alternative_path):
                logger.info(f"File found at alternative path: {alternative_path}")
                absolute_file_path = alternative_path
                directory_path = patient_directory
                file_basename = filename
            else:
                logger.error(f"File not found on disk: {absolute_file_path} or {alternative_path}")
                return jsonify({"error": "File not found on server storage"}), 404
            
        # Αποστολή του αρχείου
        return send_from_directory(
            directory=directory_path,
            path=file_basename,
            as_attachment=False  # False για προβολή στο browser, True για κατέβασμα
        )
        
    except Exception as e:
        logger.error(f"Error serving file {file_id} for patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Endpoint για διαγραφή αρχείων (για συμβατότητα με το frontend) ---
@app.route('/api/files/<string:patient_id>/<string:file_id>', methods=['DELETE'])
@jwt_required()
def delete_file_compat(patient_id, file_id):
    """Endpoint συμβατότητας για διαγραφή αρχείων"""
    try:
        # Έλεγχος εξουσιοδότησης (πιο αυστηρός - μόνο ο ίδιος ο ασθενής ή ο assigned γιατρός)
        view_permission = ViewPatientPermission(patient_id)
        if not view_permission.can():
            return jsonify({"error": "Δεν έχετε δικαίωμα διαγραφής των αρχείων αυτού του ασθενή"}), 403
            
        # Εύρεση του ασθενή και του συγκεκριμένου αρχείου
        patient = db.patients.find_one(
            {"_id": ObjectId(patient_id), "uploaded_files.file_id": file_id},
            {"uploaded_files.$": 1}  # Επιστρέφει μόνο το αρχείο που ταιριάζει
        )
        
        if not patient or 'uploaded_files' not in patient or not patient['uploaded_files']:
            return jsonify({"error": "File not found or does not belong to this patient"}), 404
            
        # Παίρνουμε το πρώτο (και μοναδικό) αρχείο από το αποτέλεσμα
        file_metadata = patient['uploaded_files'][0]
        stored_filename = file_metadata.get('filename')
        
        # 1. Αφαίρεση των μεταδεδομένων του αρχείου από τη βάση
        update_result = db.patients.update_one(
            {"_id": ObjectId(patient_id)},
            {"$pull": { "uploaded_files": { "file_id": file_id } } }
        )
        
        if update_result.modified_count == 1:
            logger.info(f"Removed file metadata {file_id} from patient {patient_id}'s record.")
            
            # 2. Διαγραφή του πραγματικού αρχείου από το σύστημα αρχείων
            if stored_filename:
                try:
                    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
                    file_path = file_metadata.get('file_path', '')
                    
                    # Χρησιμοποιούμε την ίδια λογική για την εύρεση του αρχείου όπως στο GET
                    patient_directory = os.path.join(upload_folder, patient_id)
                    
                    if patient_id in file_path:
                        absolute_file_path = os.path.join(upload_folder, file_path)
                    else:
                        absolute_file_path = os.path.join(patient_directory, stored_filename)
                    
                    # Έλεγχος αν το αρχείο υπάρχει και διαγραφή
                    if os.path.exists(absolute_file_path):
                        os.remove(absolute_file_path)
                        logger.info(f"Deleted file from disk: {absolute_file_path}")
                    else:
                        # Δοκιμή εναλλακτικής διαδρομής
                        alternative_path = os.path.join(patient_directory, stored_filename)
                        if os.path.exists(alternative_path) and alternative_path != absolute_file_path:
                            os.remove(alternative_path)
                            logger.info(f"Deleted file from alternative path: {alternative_path}")
                        else:
                            logger.warning(f"File not found on disk, but metadata removed: {absolute_file_path}")
                except OSError as e:
                    # Καταγραφή σφάλματος αλλά συνέχιση αφού η εγγραφή στη βάση έχει αφαιρεθεί
                    logger.error(f"Error deleting file from disk: {e}")
            else:
                logger.warning(f"Filename missing in metadata for file_id {file_id}. Cannot delete from disk.")
                
            return jsonify({"message": "File deleted successfully"}), 200
        else:
            logger.error(f"Failed to remove file metadata {file_id} from patient {patient_id}. modified_count=0")
            return jsonify({"error": "Failed to update patient record to remove file info"}), 500
            
    except Exception as e:
        logger.error(f"Error deleting file {file_id} for patient {patient_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# Γενικός χειρισμός εξαιρέσεων
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}")
    logger.error(traceback.format_exc())
    return jsonify({
        "error": "An unexpected error occurred",
        "details": str(e) if app.debug else "See server logs for details"
    }), 500

# === ΑΦΑΙΡΕΘΗΚΕ Η ΔΙΠΛΗ ΚΑΤΑΧΩΡΗΣΗ ΤΟΥ SCENARIOS BLUEPRINT ===
# ΤΟ scenarios_bp καταχωρείται ήδη μέσα από το all_blueprints loop

# --- Εκκίνηση Server --- 
if __name__ == '__main__':
    print("Starting Flask server...")
    # Final blueprint status
    print(f"🎯 Final blueprint status: {list(app.blueprints.keys())}")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)