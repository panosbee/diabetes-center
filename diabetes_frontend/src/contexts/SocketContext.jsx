// diabetes_frontend/src/contexts/SocketContext.jsx

import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import io from 'socket.io-client';
import { useGetIdentity } from 'react-admin'; // Για τον έλεγχο αυθεντικοποίησης

export const SocketContext = createContext(null); // Πρόσθεσε το export
export const useSocket = () => {
    // Αυτό το hook θα επιστρέφει τώρα το *αντικείμενο* { socket, isConnected }
    return useContext(SocketContext); 
};

// Προσαρμόστε το tokenKey ανάλογα με το ποια εφαρμογή τρέχει (doctor ή patient)
// Μπορεί να γίνει και πιο δυναμικά αν χρειαστεί
export const SocketProvider = ({ children, tokenKey = 'access_token' }) => { 
    const [socket, setSocket] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const { identity, isLoading: identityLoading, error: identityError } = useGetIdentity(); // Παίρνουμε και το error
    
    const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'; // Fallback

    useEffect(() => {
        // Μην κάνεις τίποτα αν φορτώνει η ταυτότητα ή αν υπήρξε σφάλμα στην ανάκτησή της
        if (identityLoading || identityError) {
             console.log('[SocketProvider] Waiting for identity or identity error exists.');
             // Αν υπήρχε παλιό socket, αποσύνδεσέ το
             if(socket) {
                 socket.disconnect();
                 setSocket(null);
                 setIsConnected(false);
             }
             return;
        }

        let newSocket = null;
        
        // Δημιουργία σύνδεσης μόνο αν ο χρήστης ΕΧΕΙ identity (είναι logged in)
        if (identity && identity.id) {
            const token = localStorage.getItem(tokenKey); 
            
            if (token && !socket) { // Συνδέσου μόνο αν υπάρχει token ΚΑΙ δεν υπάρχει ήδη socket
                console.log(`[SocketProvider (${tokenKey})] Attempting to connect with token...`);
                
                newSocket = io(VITE_API_URL, { 
                    query: { token },
                    transports: ['websocket'], 
                    reconnectionAttempts: 3, // Λιγότερες προσπάθειες για να μην κολλάει
                    timeout: 5000, // Timeout σύνδεσης
                });

                newSocket.on('connect', () => {
                    console.log(`[SocketProvider (${tokenKey})] Socket connected: ${newSocket.id}, User: ${identity.id}`);
                    setSocket(newSocket);
                    setIsConnected(true);
                });

                newSocket.on('disconnect', (reason) => {
                    console.log(`[SocketProvider (${tokenKey})] Socket disconnected: ${reason}`);
                    // Μην κάνεις setSocket(null) αμέσως, μπορεί να επανασυνδεθεί
                    setIsConnected(false); 
                    // Αν η αποσύνδεση δεν είναι εσκεμμένη, μπορεί να χρειαστεί έλεγχος
                    if (reason !== 'io client disconnect') {
                        // Προσπάθησε να ξαναπάρεις την ταυτότητα για να δεις αν το token έληξε
                        // authProvider.checkAuth().catch(() => { /* Handle logout if needed */ });
                    }
                });

                newSocket.on('connect_error', (error) => {
                    console.error(`[SocketProvider (${tokenKey})] Connection error:`, error.message || error);
                    // Μην κάνεις setSocket(null) εδώ, το io client μπορεί να προσπαθεί να επανασυνδεθεί
                    setIsConnected(false);
                    // Εδώ ίσως θέλεις να ειδοποιήσεις τον χρήστη
                });

                // Listener για αναγκαστική αποσύνδεση από τον server
                newSocket.on('force_disconnect', (data) => {
                    console.warn(`[SocketProvider (${tokenKey})] Received force_disconnect:`, data.message);
                    if(newSocket) newSocket.disconnect(); // Κλείσε την τρέχουσα σύνδεση
                    setSocket(null);
                    setIsConnected(false);
                    alert(data.message || 'Αποσυνδεθήκατε λόγω σύνδεσης από άλλη τοποθεσία.');
                    // Εδώ θα μπορούσες να κάνεις και logout τον χρήστη από την εφαρμογή React-Admin
                    // authProvider.logout();
                });

            } else if (!token) {
                 console.warn(`[SocketProvider (${tokenKey})] User has identity but token key '${tokenKey}' is missing from localStorage.`);
                 // Αποσύνδεσε αν υπήρχε παλιό socket
                 if(socket) {
                     socket.disconnect();
                     setSocket(null);
                     setIsConnected(false);
                 }
            } else if (socket && !socket.connected) {
                // Αν υπάρχει socket αλλά δεν είναι συνδεδεμένο, προσπάθησε να συνδεθείς
                 console.log(`[SocketProvider (${tokenKey})] Existing socket not connected, attempting to connect...`);
                 socket.connect();
            }

        } else { // Αν ΔΕΝ υπάρχει identity (ο χρήστης δεν είναι logged in)
            if (socket) {
                console.log(`[SocketProvider (${tokenKey})] Disconnecting socket because user is not authenticated.`);
                socket.disconnect();
                setSocket(null);
                setIsConnected(false);
            }
        }

        // Cleanup: Κλείσιμο του socket όταν το component φεύγει ή αλλάζουν οι εξαρτήσεις
        return () => {
            if (newSocket) {
                console.log(`[SocketProvider (${tokenKey})] Disconnecting socket instance on cleanup...`);
                newSocket.off('connect');
                newSocket.off('disconnect');
                newSocket.off('connect_error');
                newSocket.off('force_disconnect');
                newSocket.disconnect();
            } else if (socket && !(identity && !identityLoading)) {
                 // Αποσύνδεση του υπάρχοντος socket αν ο χρήστης αποσυνδέθηκε
                 console.log(`[SocketProvider (${tokenKey})] Disconnecting existing socket on cleanup (auth change).`);
                 socket.disconnect();
                 setSocket(null);
                 setIsConnected(false);
            }
        };
    // Παρακολουθούμε identity, identityLoading
    }, [identity, identityLoading, identityError, tokenKey, VITE_API_URL, socket]); // Πρόσθεσα socket ως dependency για τη συνθήκη επανασύνδεσης

    // Χρησιμοποιούμε useMemo για να μην αλλάζει το value αν δεν αλλάξει το socket ή το isConnected
    const contextValue = useMemo(() => ({ socket, isConnected }), [socket, isConnected]);

    return (
        <SocketContext.Provider value={contextValue}> 
            {children}
        </SocketContext.Provider>
    );
};