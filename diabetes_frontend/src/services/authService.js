import axios from 'axios';

// Ορίζουμε το βασικό URL του backend API μας
// Στην παραγωγή, αυτό θα πρέπει να είναι μεταβλητή περιβάλλοντος
const API_URL = 'http://localhost:5000/api'; // Το backend τρέχει στην πόρτα 5000

// Συνάρτηση για login γιατρού
const loginDoctor = async (username, password) => {
    try {
        const response = await axios.post(`${API_URL}/auth/login`, {
            username,
            password,
        });
        // Αν το login πετύχει, αποθηκεύουμε το token και επιστρέφουμε τα δεδομένα
        if (response.data.access_token) {
            localStorage.setItem('authToken', response.data.access_token);
            // Μπορούμε να αποθηκεύσουμε και άλλα στοιχεία χρήστη αν χρειάζεται
            // localStorage.setItem('userType', 'doctor'); 
        }
        return response.data; // Επιστρέφει { access_token: "..." }
    } catch (error) {
        console.error("Error during doctor login API call:", error.response || error.message);
        // Πετάμε το σφάλμα παραπάνω για να το χειριστεί το component
        throw error; 
    }
};

// Συνάρτηση για login ασθενή
const loginPatient = async (amka, password) => {
    try {
        const response = await axios.post(`${API_URL}/auth/patient/login`, {
            amka,
            password,
        });
        if (response.data.access_token) {
            localStorage.setItem('authToken', response.data.access_token);
            localStorage.setItem('userInfo', JSON.stringify(response.data.patient_info)); // Αποθηκεύουμε και τα στοιχεία του ασθενή
            // localStorage.setItem('userType', 'patient'); 
        }
        return response.data; // Επιστρέφει { access_token: "...", patient_info: {...} }
    } catch (error) {
        console.error("Error during patient login API call:", error.response || error.message);
        throw error;
    }
};

// Συνάρτηση για logout (απλά καθαρίζει το token)
const logout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userInfo');
    // localStorage.removeItem('userType');
};

// Συνάρτηση για να πάρουμε το τρέχον token (αν υπάρχει)
const getCurrentToken = () => {
    return localStorage.getItem('authToken');
};

// Εξάγουμε τις συναρτήσεις για να χρησιμοποιηθούν αλλού
const authService = {
    loginDoctor,
    loginPatient,
    logout,
    getCurrentToken,
};

export default authService; 