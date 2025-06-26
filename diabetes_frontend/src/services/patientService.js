import axios from 'axios';
import authService from './authService'; // Για να πάρουμε το token

const API_URL = 'http://localhost:5000/api'; // Το ίδιο base URL

// Συνάρτηση για να παίρνουμε τα headers με το token
const getAuthHeaders = () => {
    const token = authService.getCurrentToken();
    if (token) {
        return { Authorization: `Bearer ${token}` };
    } else {
        // Αν δεν υπάρχει token, ίσως πρέπει να κάνουμε logout ή redirect
        // Προς το παρόν επιστρέφουμε κενό αντικείμενο (η κλήση θα αποτύχει στο backend)
        console.warn("No auth token found for API call");
        return {}; 
    }
};

// Συνάρτηση για ανάκτηση των ασθενών που διαχειρίζεται ο γιατρός
// ΔΙΟΡΘΩΘΗΚΕ: Καλεί το προστατευμένο endpoint /api/doctor-portal/patients
const getMyManagedPatients = async () => {
    try {
        // console.warn(\"Returning to generic GET /api/patients. Backend needs dedicated endpoint.\");
        // const response = await axios.get(`${API_URL}/patients`); 
        
        // Καλεί το σωστό endpoint και περνάει τα headers
        const response = await axios.get(`${API_URL}/doctor-portal/patients`, { 
            headers: getAuthHeaders() 
        });
        return response.data; // Επιστρέφει τη λίστα των ασθενών του γιατρού
    } catch (error) {
        console.error("Error fetching managed patient list:", error.response || error.message);
        throw error;
    }
};

// Συνάρτηση για προσθήκη νέου ασθενή από τον γιατρό
const addPatient = async (patientData) => {
    try {
        const response = await axios.post(`${API_URL}/patients`, patientData, {
            headers: getAuthHeaders()
        });
        return response.data; // Επιστρέφει τα δεδομένα του νέου ασθενή
    } catch (error) {
        console.error("Error adding patient:", error.response || error.message);
        throw error; // Ρίχνουμε το σφάλμα για να το χειριστεί το component
    }
};

// Συνάρτηση για ανάκτηση δεδομένων συγκεκριμένου ασθενή
const getPatientById = async (patientId) => {
    try {
        const response = await axios.get(`${API_URL}/patients/${patientId}`, {
            headers: getAuthHeaders()
        });
        return response.data;
    } catch (error) {
        console.error(`Error fetching patient data for ID ${patientId}:`, error.response || error.message);
        throw error;
    }
};

// Συνάρτηση για ανάκτηση συνεδριών συγκεκριμένου ασθενή
const getPatientSessions = async (patientId) => {
    try {
        const response = await axios.get(`${API_URL}/sessions`, { 
            headers: getAuthHeaders(),
            params: { patient_id: patientId } // Περνάμε το ID ως query parameter
        });
        return response.data;
    } catch (error) {
        console.error(`Error fetching sessions for patient ID ${patientId}:`, error.response || error.message);
        throw error;
    }
};

// Συνάρτηση για ανάκτηση λίστας αρχείων συγκεκριμένου ασθενή
const getPatientFilesList = async (patientId) => {
    try {
        const response = await axios.get(`${API_URL}/patients/${patientId}/files/list`, { 
            headers: getAuthHeaders()
        });
        return response.data;
    } catch (error) {
        console.error(`Error fetching file list for patient ID ${patientId}:`, error.response || error.message);
        throw error;
    }
};

// Άλλες συναρτήσεις για ασθενείς (π.χ. getPatientById, addPatient κλπ)
// θα προστεθούν εδώ αργότερα...

const patientService = {
    getMyManagedPatients,
    addPatient,
    getPatientById,
    getPatientSessions,
    getPatientFilesList,
    // ... άλλες συναρτήσεις ...
};

export default patientService; 