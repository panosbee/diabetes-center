from flask import Flask, jsonify, request, make_response
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

@app.route('/')
def home():
    return jsonify({"message": "CORS fix server running"})

@app.route('/api/doctor-portal/patients', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_patients():
    """Handle both GET and OPTIONS requests."""
    
    # Εκτύπωση πληροφοριών για debugging
    print(f"Received {request.method} request to {request.path}")
    print(f"Headers: {request.headers}")
    
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        print("Returning 204 No Content for OPTIONS")
        response = make_response('', 204)
        # Manually add CORS headers for extra safety
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        return response
        
    # For GET request, just return dummy data
    return jsonify([
        {"id": "1", "personal_details": {"first_name": "Γιάννης", "last_name": "Παπαδόπουλος", "amka": "01234567890"}},
        {"id": "2", "personal_details": {"first_name": "Μαρία", "last_name": "Κωνσταντίνου", "amka": "09876543210"}}
    ])

if __name__ == '__main__':
    print("Starting Flask-SocketIO server (Reloader Enabled)...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True)