from flask import Flask, jsonify, request, make_response
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, verify_jwt_in_request
from flask_cors import CORS, cross_origin

# --- Initialize App ---
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# --- JWT Config ---
app.config["JWT_SECRET_KEY"] = "your-secret-key-here"  # Κανονικά πρέπει να φορτωθεί από περιβαλλοντική μεταβλητή
jwt = JWTManager(app)

# --- MongoDB Connection ---
try:
    client = MongoClient('mongodb://localhost:27017/')
    client.admin.command('ismaster')  # Έλεγχος σύνδεσης
    db = client.diabetes_db
    print("MongoDB connection successful.")
except Exception as e:
    print(f"Could not connect to MongoDB: {e}")
    db = None

@app.route('/')
def home():
    if db is not None:
        return jsonify({"message": "Quick fix server is running!", "db_status": "connected"})
    else:
        return jsonify({"message": "Quick fix server is running!", "db_status": "disconnected"}), 500

# --- Doctor Portal Endpoint ---
@app.route('/api/doctor-portal/patients', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_my_managed_patients_list():
    """Επιστρέφει τη λίστα των ασθενών που διαχειρίζεται ο συνδεδεμένος γιατρός."""
    
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        print("OPTIONS request received, returning 204")
        return make_response('', 204)  # Return 204 No Content

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

# --- Run Server ---
if __name__ == '__main__':
    print("Starting Flask server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True) 