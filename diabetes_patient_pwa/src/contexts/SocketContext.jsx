import React, { createContext, useContext, useState, useEffect } from 'react';
import io from 'socket.io-client';
import { authProvider } from '../authProvider'; // Χρήση του PWA authProvider

const SocketContext = createContext(null);

export const useSocket = () => {
    return useContext(SocketContext);
};

export const SocketProvider = ({ children }) => {
    const [socket, setSocket] = useState(null);
    // Στο PWA, ελέγχουμε απλά αν υπάρχει token στο localStorage
    const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('patient_access_token')); 
    
    // State για να ξέρουμε πότε τελείωσε η αρχική προσπάθεια σύνδεσης
    const [initialAuthCheckDone, setInitialAuthCheckDone] = useState(false);
    
    const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'; // Fallback

    // Έλεγχος αυθεντικοποίησης κατά την έναρξη
    useEffect(() => {
        authProvider.checkAuth()
            .then(() => setIsAuthenticated(true))
            .catch(() => setIsAuthenticated(false))
            .finally(() => setInitialAuthCheckDone(true));
    }, []);
    
    // Effect για δημιουργία/καταστροφή socket βάσει αυθεντικοποίησης
    useEffect(() => {
        // Περιμένουμε να ολοκληρωθεί ο αρχικός έλεγχος
        if (!initialAuthCheckDone) return;
        
        let newSocket = null;
        
        if (isAuthenticated) {
            const token = localStorage.getItem('patient_access_token'); // Για το PWA
            
            if (token) {
                console.log('[SocketProvider PWA] Connecting to Socket.IO server...');
                newSocket = io(VITE_API_URL, { 
                    query: { token },
                    transports: ['websocket'],
                    reconnectionAttempts: 5 // Προσπάθειες επανασύνδεσης
                });

                newSocket.on('connect', () => {
                    console.log('[SocketProvider PWA] Socket connected:', newSocket.id);
                    setSocket(newSocket);
                });

                newSocket.on('disconnect', (reason) => {
                    console.log('[SocketProvider PWA] Socket disconnected:', reason);
                    setSocket(null);
                    // Αν η αποσύνδεση δεν έγινε από logout, ίσως θέλουμε έλεγχο token/auth
                    if (reason !== 'io client disconnect') {
                       authProvider.checkAuth().catch(() => setIsAuthenticated(false));
                    }
                });

                newSocket.on('connect_error', (error) => {
                    console.error('[SocketProvider PWA] Socket connection error:', error);
                    setSocket(null);
                    // Ίσως το token έληξε;
                    authProvider.checkAuth().catch(() => setIsAuthenticated(false));
                });

            } else {
                 console.warn('[SocketProvider PWA] User is authenticated but token is missing?');
                 setIsAuthenticated(false); // Αν λείπει το token, δεν είναι αυθεντικοποιημένος
            }
        } else {
            // Αν ο χρήστης ΔΕΝ είναι αυθεντικοποιημένος
            if (socket) {
                console.log('[SocketProvider PWA] Disconnecting existing socket (user not authenticated).');
                socket.disconnect();
                setSocket(null);
            }
        }

        // Cleanup
        return () => {
            if (newSocket) {
                console.log('[SocketProvider PWA] Disconnecting socket on cleanup...');
                newSocket.disconnect();
            }
        };
    // Παρακολουθούμε το isAuthenticated και το initialAuthCheckDone
    }, [isAuthenticated, initialAuthCheckDone, VITE_API_URL]); 

    // Λειτουργία για να ενημερώνει το isAuthenticated (π.χ. μετά από login/logout)
    // Αυτή θα μπορούσε να καλείται από τα components Login/Register/Layout
    // Προς το παρόν δεν την υλοποιούμε πλήρως, αλλά τη χρειαζόμαστε ίσως αργότερα.
    const updateAuthState = (isAuth) => {
         setIsAuthenticated(isAuth);
    };

    return (
        // Παρέχουμε και το socket και τη λειτουργία ενημέρωσης auth state
        <SocketContext.Provider value={{ socket, updateAuthState }}> 
            {children}
        </SocketContext.Provider>
    );
}; 