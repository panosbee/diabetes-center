import React, { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { authProvider } from '../authProvider'; // Εισάγουμε τον auth provider μας

function PrivateRoute({ children }) {
    const [isAuthenticated, setIsAuthenticated] = useState(null); // null = loading, true = auth, false = not auth

    useEffect(() => {
        let isMounted = true;
        authProvider.checkAuth()
            .then(() => {
                if (isMounted) {
                    setIsAuthenticated(true);
                }
            })
            .catch(() => {
                if (isMounted) {
                    setIsAuthenticated(false);
                }
            });
        
        // Cleanup function για αποφυγή memory leaks αν το component γίνει unmount πριν ολοκληρωθεί το checkAuth
        return () => { isMounted = false; };
    }, []);

    // Αν ακόμα φορτώνει η κατάσταση αυθεντικοποίησης, δείχνουμε ένα μήνυμα φόρτωσης
    if (isAuthenticated === null) {
        return <div>Loading authentication status...</div>; 
    }

    // Αν είναι αυθεντικοποιημένος, δείχνουμε το παιδί (το component της διαδρομής)
    // Αν δεν είναι, ανακατευθύνουμε στο /login
    return isAuthenticated ? children : <Navigate to="/login" replace />;
}

export default PrivateRoute; 