from flask import Blueprint, request, jsonify, current_app # Add current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId
import logging
import datetime
from utils.db import get_db

# Ρύθμιση logger
logger = logging.getLogger(__name__)

# Δημιουργία blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Η σύνδεση στη βάση δεδομένων
db = get_db()

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Endpoint για το login των χρηστών
    Δέχεται username και password, επιστρέφει JWT token
    """
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Missing username or password"}), 400
            
        username = data['username']
        password = data['password']
        
        # Αναζήτηση του χρήστη (γιατρού) με το συγκεκριμένο username
        doctor = db.doctors.find_one({"account_details.username": username})
        
        if doctor and 'account_details' in doctor and 'password_hash' in doctor['account_details']:
            # Έλεγχος του password
            stored_hash = doctor['account_details']['password_hash']
            
            # Έλεγχος του hash
            # Ensure we use the app's bcrypt instance
            app_bcrypt = current_app.bcrypt if hasattr(current_app, 'bcrypt') else current_app.extensions.get('bcrypt')
            if not app_bcrypt:
                logger.error("Bcrypt not available on app context in auth.py")
                return jsonify({"error": "Internal server error - auth misconfiguration"}), 500

            if app_bcrypt.check_password_hash(stored_hash, password):
                # Επιτυχής login
                user_id = str(doctor['_id'])
                
                # Δημιουργία access token με id του χρήστη στο identity
                logger.info(f"DEBUG: JWT_SECRET_KEY in auth.py before create_access_token: {current_app.config.get('JWT_SECRET_KEY')}") # DEBUG LINE
                access_token = create_access_token(
                    identity=user_id,
                    expires_delta=datetime.timedelta(days=1) # Token ισχύει για 1 ημέρα
                )
                
                # Συλλογή βασικών στοιχείων για το frontend
                doctor_info = {
                    "id": user_id,
                    "first_name": doctor['personal_details']['first_name'],
                    "last_name": doctor['personal_details']['last_name']
                }
                
                # Ενημέρωση του last_login
                db.doctors.update_one(
                    {"_id": doctor['_id']},
                    {"$set": {"last_login": datetime.datetime.now(datetime.timezone.utc)}}
                )
                
                return jsonify({
                    "access_token": access_token,
                    "doctor_info": doctor_info
                }), 200
            else:
                # Λάθος password
                return jsonify({"error": "Invalid username or password"}), 401
        else:
            # Ο χρήστης δεν βρέθηκε
            return jsonify({"error": "Invalid username or password"}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Endpoint για αλλαγή κωδικού χρήστη.
    Απαιτεί αυθεντικοποίηση με JWT token.
    """
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500
        
    # Παίρνουμε το ID του χρήστη από το JWT token
    user_id = get_jwt_identity()
    
    try:
        data = request.get_json()
        
        if not data or 'current_password' not in data or 'new_password' not in data:
            return jsonify({"error": "Missing current_password or new_password"}), 400
            
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Βασικός έλεγχος για το νέο password
        if len(new_password) < 8:
            return jsonify({"error": "New password must be at least 8 characters long"}), 400
            
        # Αναζήτηση του χρήστη (γιατρού) με το συγκεκριμένο ID
        doctor = db.doctors.find_one({"_id": ObjectId(user_id)})
        
        if doctor and 'account_details' in doctor and 'password_hash' in doctor['account_details']:
            # Έλεγχος του τρέχοντος password
            stored_hash = doctor['account_details']['password_hash']
            
            # Έλεγχος του hash
            app_bcrypt = current_app.bcrypt if hasattr(current_app, 'bcrypt') else current_app.extensions.get('bcrypt')
            if not app_bcrypt:
                logger.error("Bcrypt not available on app context in auth.py (change_password)")
                return jsonify({"error": "Internal server error - auth misconfiguration"}), 500

            if app_bcrypt.check_password_hash(stored_hash, current_password):
                # Το τρέχον password είναι σωστό, μπορούμε να το αλλάξουμε
                
                # Δημιουργία hash για το νέο password
                new_password_hash = app_bcrypt.generate_password_hash(new_password).decode('utf-8')
                
                # Ενημέρωση του password στη βάση
                db.doctors.update_one(
                    {"_id": ObjectId(user_id)},
                    {
                        "$set": {
                            "account_details.password_hash": new_password_hash,
                            "last_updated_at": datetime.datetime.now(datetime.timezone.utc)
                        }
                    }
                )
                
                return jsonify({"message": "Password changed successfully"}), 200
            else:
                # Λάθος τρέχον password
                return jsonify({"error": "Current password is incorrect"}), 401
        else:
            # Ο χρήστης δεν βρέθηκε
            return jsonify({"error": "User not found"}), 404
            
    except Exception as e:
        logger.error(f"Change password error: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500 