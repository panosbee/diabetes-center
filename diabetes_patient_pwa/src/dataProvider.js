// src/dataProvider.js - PWA Patient Portal Data Provider

// Το URL του backend API (θα χρειαστεί να οριστεί στο .env αργότερα)
const API_BASE_URL = 'http://localhost:5000/api'; 

/**
 * Βοηθητική συνάρτηση για κλήσεις fetch με αυτόματη προσθήκη του JWT token.
 */
export const fetchWithAuth = async (url, options = {}) => {
    const token = localStorage.getItem('patient_access_token');
    
    const headers = new Headers(options.headers || {});
    headers.set('Accept', 'application/json');
    if (token) {
        headers.set('Authorization', `Bearer ${token}`);
    }
    if (options.body && !(options.body instanceof FormData)) { // Μην θέτεις Content-Type για FormData
         headers.set('Content-Type', 'application/json');
    }

    const finalOptions = {
        ...options,
        headers,
    };

    console.log(`[PWA Fetch] Fetching: ${url}`, finalOptions);

    try {
        const response = await fetch(url, finalOptions);

        // Check for no content response (e.g., DELETE)
        if (response.status === 204) {
            return Promise.resolve({ status: 204, data: null }); 
        }

        const responseData = await response.json();

        if (!response.ok) {
            // Προσπάθεια εξαγωγής του μηνύματος σφάλματος από την απάντηση
            const errorMessage = responseData.error || responseData.message || `HTTP error! status: ${response.status}`;
            console.error('[PWA Fetch] Error:', errorMessage, 'Status:', response.status);
            // Δημιουργούμε ένα σφάλμα με status για τον authProvider
            const error = new Error(errorMessage);
            error.status = response.status; 
            throw error;
        }

        console.log('[PWA Fetch] Success:', responseData);
        return Promise.resolve({ status: response.status, data: responseData });
        
    } catch (error) {
        console.error('[PWA Fetch] Network or parsing error:', error);
        // Εξασφαλίζουμε ότι το σφάλμα έχει status για τον authProvider
        if (!error.status) {
           error.status = 500; // Default to internal server error if status is missing
        }
        throw error; // Throw the error again so it can be caught by calling components
    }
};

// Μπορούμε να προσθέσουμε συγκεκριμένες data provider functions εδώ αν χρειαστεί
// π.χ., για getProfile, updateProfile, getSessions, getFiles κ.λπ.

export const getProfile = () => fetchWithAuth(`${API_BASE_URL}/patient-portal/profile`);

export const updateProfile = (profileData) => fetchWithAuth(`${API_BASE_URL}/patient-portal/profile`, {
    method: 'PATCH',
    body: JSON.stringify(profileData),
});

// --- Files Functions ---
export const getMyFiles = () => fetchWithAuth(`${API_BASE_URL}/patient-portal/files`);

export const uploadMyFile = (file) => {
    const formData = new FormData();
    formData.append('file', file); // Το κλειδί πρέπει να είναι 'file' όπως στο backend
    
    // ΣΗΜΑΝΤΙΚΟ: Μην βάζουμε Content-Type header όταν στέλνουμε FormData
    // Ο browser θα το κάνει αυτόματα με το σωστό boundary.
    return fetchWithAuth(`${API_BASE_URL}/patient-portal/files`, {
        method: 'POST',
        body: formData,
        // headers: {} // Αφήνουμε το fetchWithAuth να ΜΗΝ βάλει Content-Type: application/json
    });
};

export const deleteMyFile = (fileId) => fetchWithAuth(`${API_BASE_URL}/patient-portal/files/${fileId}`, {
    method: 'DELETE',
});

// Για το download, συνήθως δεν χρησιμοποιούμε fetch, αλλά ανοίγουμε το URL σε νέο παράθυρο
// ή δημιουργούμε ένα προσωρινό link. Παρέχουμε το URL εδώ.
export const getMyFileDownloadUrl = (fileId) => {
    const token = localStorage.getItem('patient_access_token');
    // ΠΡΟΣΟΧΗ: Η απλή προσθήκη token στο URL ΔΕΝ είναι ασφαλής πρακτική για παραγωγή.
    // Ιδανικά, το backend endpoint θα πρέπει να δέχεται το token στο header.
    // Εναλλακτικά, θα μπορούσε να δημιουργεί ένα προσωρινό, signed URL.
    // Για απλότητα προς το παρόν, ΔΕΝ προσθέτουμε token στο URL εδώ.
    // Ο χρήστης ΠΡΕΠΕΙ να είναι ήδη συνδεδεμένος στο browser για να δουλέψει το @jwt_required.
    return `${API_BASE_URL}/patient-portal/files/${fileId}/download`;
};

// --- Sessions Functions ---
export const getMySessions = () => fetchWithAuth(`${API_BASE_URL}/patient-portal/sessions`);

export const getMySessionDetails = (sessionId) => fetchWithAuth(`${API_BASE_URL}/patient-portal/sessions/${sessionId}`);

// Προσθέστε κι άλλες συναρτήσεις εδώ... 