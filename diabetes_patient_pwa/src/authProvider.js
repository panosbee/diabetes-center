// src/authProvider.js - PWA Patient Portal Auth

// Το URL του backend API (θα χρειαστεί να οριστεί στο .env αργότερα)
const API_BASE_URL = 'http://localhost:5000/api'; // Χρήση του βασικού URL εδώ

export const authProvider = {
    login: ({ username, password }) => {
        // Το PWA θα χρησιμοποιεί email για username
        const email = username; 
        const request = new Request(`${API_BASE_URL}/patient-portal/login`, {
            method: 'POST',
            body: JSON.stringify({ email, password }), // Στέλνουμε email και password
            headers: new Headers({ 'Content-Type': 'application/json' }),
        });
        return fetch(request)
            .then(response => {
                if (response.status < 200 || response.status >= 300) {
                    // Προσπάθεια ανάγνωσης του error message από το backend
                    return response.json().then(err => {
                         throw new Error(err.error || response.statusText);
                    }).catch(() => {
                        throw new Error(response.statusText);
                    });
                }
                return response.json();
            })
            .then(auth => {
                if (!auth.access_token || !auth.patient_info) {
                    throw new Error('Missing access token or patient info in response');
                }
                localStorage.setItem('patient_access_token', auth.access_token);
                localStorage.setItem('patient_info', JSON.stringify(auth.patient_info));
                console.log('Patient logged in successfully', auth.patient_info);
                return Promise.resolve();
            })
            .catch((error) => {
                console.error("Patient login failed:", error);
                throw new Error(error.message || 'Login failed. Please check credentials or network.');
            });
    },

    logout: () => {
        localStorage.removeItem('patient_access_token');
        localStorage.removeItem('patient_info');
        console.log('Patient logged out');
        return Promise.resolve();
    },

    checkError: (error) => {
        const status = error.status;
        if (status === 401 || status === 403) {
            localStorage.removeItem('patient_access_token');
            localStorage.removeItem('patient_info');
            return Promise.reject(); // Προκαλεί ανακατεύθυνση στη σελίδα login
        }
        // Αν δεν είναι 401/403, αφήνουμε την εφαρμογή να χειριστεί το σφάλμα (π.χ. εμφάνιση μηνύματος)
        return Promise.resolve();
    },

    checkAuth: () => {
        return localStorage.getItem('patient_access_token')
            ? Promise.resolve()
            : Promise.reject();
    },

    getPermissions: () => Promise.resolve('patient'), // Όλοι οι χρήστες του PWA είναι ασθενείς

    getIdentity: () => {
        const patientInfo = localStorage.getItem('patient_info');
        if (patientInfo) {
            try {
                const parsedInfo = JSON.parse(patientInfo);
                // Επιστρέφουμε το id και το όνομα για χρήση στο UI
                return Promise.resolve({ 
                    id: parsedInfo.id, 
                    fullName: `${parsedInfo.first_name} ${parsedInfo.last_name}`,
                 });
            } catch (error) {
                return Promise.reject(error);
            }
        }
        return Promise.reject('Patient info not found');
    },
}; 