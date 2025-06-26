// src/authProvider.js

// Το URL του backend API
const apiUrl = 'http://localhost:5000/api';

export const authProvider = {
    // Καλείται όταν ο χρήστης προσπαθεί να συνδεθεί
    login: ({ username, password }) => {
        const request = new Request(`${apiUrl}/auth/login`, {
            method: 'POST',
            body: JSON.stringify({ username, password }),
            headers: new Headers({ 'Content-Type': 'application/json' }),
        });
        return fetch(request)
            .then(response => {
                if (response.status < 200 || response.status >= 300) {
                    throw new Error(response.statusText);
                }
                return response.json();
            })
            .then(auth => {
                if (!auth.access_token) {
                    throw new Error('Missing access token in response');
                }
                localStorage.setItem('access_token', auth.access_token);
                
                // Προσθέτουμε LOG για να δούμε την απάντηση του backend
                console.log("[AuthProvider] Login Response Received:", auth);
                
                // Προαιρετικά: Αποθηκεύουμε και τα στοιχεία χρήστη αν επιστρέφονται
                if (auth.doctor_info) { 
                  console.log("[AuthProvider] Storing user_info:", auth.doctor_info);
                  localStorage.setItem('user_info', JSON.stringify(auth.doctor_info));
                } else {
                  console.warn("[AuthProvider] doctor_info key NOT FOUND in login response!");
                }
                return Promise.resolve();
            })
            .catch((error) => {
                console.error("Login failed:", error);
                // Επιστρέφουμε ένα πιο φιλικό μήνυμα λάθους
                throw new Error('Network error or invalid credentials');
            });
    },
    // Καλείται όταν ο χρήστης κάνει logout
    logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
        return Promise.resolve();
    },
    // Καλείται όταν η εφαρμογή ελέγχει για σφάλματα API (π.χ. 401 Unauthorized)
    checkError: (error) => {
        const status = error.status;
        if (status === 401) { // Μόνο σε 401 κάνουμε logout
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_info');
            console.log("[AuthProvider] Received 401, logging out."); // Debug Log
            return Promise.reject(); // Προκαλεί ανακατεύθυνση στη σελίδα login
        }
        
        // Για 403 Forbidden, ανακατευθύνουμε στο show view αντί του edit
        if (status === 403) {
            console.log(`[AuthProvider] Received status ${status}, redirecting to show view.`);
            
            // Ελέγχουμε αν βρισκόμαστε σε edit σελίδα και βρίσκουμε το resource και το id
            const currentUrl = window.location.href;
            const editRegex = /\/([\w-]+)\/(\w+)$/;  // Matches /resource/id at the end of URL
            const match = currentUrl.match(editRegex);
            
            if (match && match.length === 3) {
                const resource = match[1];
                const id = match[2];
                
                // Ανακατεύθυνση στο show view για το συγκεκριμένο resource και id
                window.location.href = `#/${resource}/${id}/show`;
                
                // Επιστρέφουμε resolve για να μη διακοπεί η ροή
                return Promise.resolve();
            }
            
            // Αν δεν μπορούμε να αναγνωρίσουμε το URL, απλά επιστρέφουμε στη λίστα
            window.location.href = '#/';
            return Promise.resolve();
        }
        
        // Για άλλα σφάλματα, απλά απορρίπτουμε το Promise
        console.log(`[AuthProvider] Received status ${status}, NOT logging out.`); // Debug Log
        return Promise.reject(error); 
    },
    // Καλείται όταν η εφαρμογή ελέγχει αν ο χρήστης είναι συνδεδεμένος
    checkAuth: () => {
        return localStorage.getItem('access_token')
            ? Promise.resolve()
            : Promise.reject();
    },
    // Καλείται όταν η εφαρμογή χρειάζεται τα δικαιώματα/ρόλο του χρήστη
    getPermissions: () => {
        // Προς το παρόν, επιστρέφουμε κενό string. 
        // Θα μπορούσαμε να αποκωδικοποιήσουμε το token ή να πάρουμε ρόλο από το localStorage
        return Promise.resolve(''); 
    },
    // Επαναφέρουμε την παλιά υλοποίηση που διαβάζει από localStorage
    getIdentity: () => {
        const userInfo = localStorage.getItem('user_info');
        console.log("[AuthProvider getIdentity] Raw user_info from localStorage:", userInfo);
        if (userInfo) {
            try {
                const parsedInfo = JSON.parse(userInfo);
                console.log("[AuthProvider getIdentity] Parsed user_info:", parsedInfo);
                // Επιστρέφουμε ένα object με τα στοιχεία που θέλουμε να εμφανίζονται
                // ΣΙΓΟΥΡΕΥΤΕΙΤΕ ότι το parsedInfo όντως περιέχει 'id', 'first_name', 'last_name'
                return Promise.resolve({ 
                    id: parsedInfo.id, // Χρειαζόμαστε το id!
                    fullName: `${parsedInfo.first_name} ${parsedInfo.last_name}`,
                    // avatar: parsedInfo.avatar_url // Αν υπάρχει
                 });
            } catch (error) {
                console.error("Error parsing user info from localStorage", error);
                return Promise.reject(error);
            }
        }
        // Αν δεν βρεθεί user_info στο localStorage, αποτυγχάνει
        console.error("[AuthProvider getIdentity] User info not found in localStorage");
        return Promise.reject('User info not found'); 
    },
    /*
    // Απλοποιημένη (λανθασμένη) υλοποίηση (σε σχόλιο)
    getIdentity: () => {
        return Promise.resolve({ id: null }); 
    },
    */
}; 