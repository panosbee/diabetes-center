import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import authService from '../services/authService'; // Για έλεγχο token

// Αυτό το component ελέγχει αν ο χρήστης είναι συνδεδεμένος (έχει token).
// Αν ναι, εμφανίζει το περιεχόμενο (children) που του δώσαμε.
// Αν όχι, τον κάνει redirect στη σελίδα login.
function PrivateRoute({ children }) {
    const location = useLocation(); // Για να ξέρουμε πού ήθελε να πάει
    const token = authService.getCurrentToken();

    // Εδώ θα μπορούσαμε να κάνουμε και πιο σύνθετο έλεγχο,
    // π.χ., να δούμε αν το token έχει λήξει ή να το επικυρώσουμε στο backend.
    // Προς το παρόν, απλά ελέγχουμε αν υπάρχει.
    const isAuthenticated = !!token; // Μετατροπή σε boolean (true αν υπάρχει token, false αν όχι)

    if (!isAuthenticated) {
        // Αν δεν είναι συνδεδεμένος, redirect στο login.
        // Το `state={{ from: location }}` βοηθάει ώστε μετά το login
        // να μπορέσουμε να τον στείλουμε πίσω στη σελίδα που ήθελε αρχικά.
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // Αν είναι συνδεδεμένος, απλά δείχνουμε το component που πρέπει (τα children).
    return children;
}

export default PrivateRoute; 