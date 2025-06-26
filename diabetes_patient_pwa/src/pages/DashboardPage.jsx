import { authProvider } from '../authProvider'; 
import React, { useState, useEffect, useCallback, useContext } from 'react';
import { Box, Dialog, DialogContent, DialogTitle, DialogActions, Button, Typography, CircularProgress } from '@mui/material'; // Added CircularProgress
import PatientCalendar from '../components/PatientCalendar'; 
import VideoCallManager from '../components/VideoCallManager'; 
import { useSocket } from '../contexts/SocketContext'; 

const PatientDashboardPage = () => {
    const { socket } = useSocket(); 
    const [identity, setIdentity] = useState(null); 
    
    const [isCallModalOpenPWA, setIsCallModalOpenPWA] = useState(false);
    const [callDetailsPWA, setCallDetailsPWA] = useState(null); 
    const [incomingCallPromptDataPWA, setIncomingCallPromptDataPWA] = useState(null); 
    
    useEffect(() => {
      authProvider.getIdentity()
        .then(id => setIdentity(id))
        .catch(() => console.error("PWA: Failed to get identity"));
    }, []);

    const resetCallStatePWA = useCallback(() => {
        console.log('[PWA Dashboard] Resetting call state.');
        setIsCallModalOpenPWA(false);
        setCallDetailsPWA(null);
        setIncomingCallPromptDataPWA(null);
    }, []);

    const handleAcceptIncomingCallPWA = useCallback(() => {
        if (!socket) return alert('Σφάλμα: Δεν υπάρχει σύνδεση.');
        if (!incomingCallPromptDataPWA || !identity?.id) return alert('Σφάλμα: Ελλιπή δεδομένα κλήσης ή ταυτότητας.');
        
        const { caller_identity, caller_sid, suggested_room, caller_name } = incomingCallPromptDataPWA;
        console.log(`[PWA Dashboard] Patient ${identity.id} accepting call from doctor ${caller_identity} in room ${suggested_room}`);

        socket.emit('accept_call', { caller_sid, caller_identity, room_name: suggested_room });
        
        setCallDetailsPWA({
            isActive: false, 
            remoteUserId: caller_identity, 
            roomName: suggested_room,
            isInitiator: false, 
            callStatus: 'active', 
            appointmentTitle: `Κλήση από ${caller_name || caller_identity}`,
            remoteUserSid: caller_sid
        });
        setIsCallModalOpenPWA(true); 
        setIncomingCallPromptDataPWA(null); 
        socket.emit('join_room', { room: suggested_room }); 
        console.log(`[PWA Dashboard] Patient joining room ${suggested_room}`);

    }, [socket, incomingCallPromptDataPWA, identity]);

    const handleRejectIncomingCallPWA = useCallback(() => {
        if (socket && incomingCallPromptDataPWA) {
            console.log(`[PWA Dashboard] Patient rejecting call from ${incomingCallPromptDataPWA.caller_identity}`);
            socket.emit('reject_call', { 
                caller_sid: incomingCallPromptDataPWA.caller_sid, 
                caller_identity: incomingCallPromptDataPWA.caller_identity 
            });
        }
        setIncomingCallPromptDataPWA(null); 
    }, [socket, incomingCallPromptDataPWA]);
    
     const handleEndCallFromManagerPWA = useCallback(() => {
        if (socket && callDetailsPWA?.roomName && identity?.id) {
             console.log(`[PWA Dashboard] Patient ${identity.id} manually ending call in room ${callDetailsPWA.roomName}`);
             // Check if the call was active or if we are ending a call that never fully connected
             if (callDetailsPWA.isActive || callDetailsPWA.callStatus === 'dialing') { // Ensure we only emit end_call if it was established or dialing
                socket.emit('end_call', { room: callDetailsPWA.roomName }); 
             }
        }
        resetCallStatePWA(); 
    }, [socket, callDetailsPWA, identity, resetCallStatePWA]);

    const handleCallActivePWA = useCallback(() => {
        console.log('[PWA Dashboard] Call is now active (peer connected).');
        setCallDetailsPWA(prevDetails => {
            if (prevDetails) {
                return { ...prevDetails, isActive: true, callStatus: 'active' };
            }
            return null;
        });
    }, []);

    useEffect(() => {
        if (!socket || !identity) return;
        console.log('[PWA Dashboard] Setting up Socket listeners...');

        const onIncomingCall = (data) => { 
            console.log('[PWA Dashboard] Received incoming_call:', data);
            if (data.suggested_room?.includes(identity.id) && !callDetailsPWA?.isActive && callDetailsPWA?.callStatus !== 'dialing') {
                 setIncomingCallPromptDataPWA(data);
            } else {
                 console.warn('[PWA Dashboard] Ignoring incoming call:', { callData: data, currentState: callDetailsPWA });
                 if (socket) socket.emit('user_busy', { target_sid: data.caller_sid }); 
            }
        };

        const onCallEnded = (data) => { 
            console.log('[PWA Dashboard] Received call_ended:', data);
            if (callDetailsPWA?.isActive && callDetailsPWA.roomName === data.room) {
                alert('Η τηλεδιάσκεψη τερματίστηκε.');
                resetCallStatePWA();
            } else if (callDetailsPWA?.roomName === data.room) { // Call ended but maybe isActive was false (e.g. connecting)
                console.log('[PWA Dashboard] Received call_ended for current room, but call was not marked active. Resetting.');
                alert('Η τηλεδιάσκεψη τερματίστηκε.');
                resetCallStatePWA();
            }
        };
        
        const onCallRejected = (data) => { 
             console.log('[PWA Dashboard] Received call_rejected (likely I rejected):', data);
             resetCallStatePWA(); 
        };

        socket.on('incoming_call', onIncomingCall); 
        socket.on('call_ended', onCallEnded);
        socket.on('call_rejected', onCallRejected); 

        return () => {
            console.log('[PWA Dashboard] Removing Socket listeners...');
            socket.off('incoming_call', onIncomingCall);
            socket.off('call_ended', onCallEnded);
            socket.off('call_rejected', onCallRejected);
        };
    }, [socket, identity, callDetailsPWA, resetCallStatePWA]); 

    return (
        <Box sx={{ p: 2 }}> 
            <Typography variant="h5" gutterBottom>Πίνακας Ελέγχου Ασθενή</Typography>
            
            {incomingCallPromptDataPWA && (
                <Dialog open={!!incomingCallPromptDataPWA} onClose={handleRejectIncomingCallPWA}>
                    <DialogTitle>Εισερχόμενη Κλήση Τηλεϊατρικής</DialogTitle>
                    <DialogContent>
                        <Typography>
                            Έχετε κλήση από: {incomingCallPromptDataPWA.caller_name || incomingCallPromptDataPWA.caller_identity}
                        </Typography>
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={handleRejectIncomingCallPWA} color="error">Απόρριψη</Button>
                        <Button onClick={handleAcceptIncomingCallPWA} color="primary" autoFocus>Αποδοχή</Button>
                    </DialogActions>
                </Dialog>
            )}

             {isCallModalOpenPWA && callDetailsPWA && identity && (
                <Dialog
                    open={isCallModalOpenPWA}
                    onClose={handleEndCallFromManagerPWA} 
                    fullWidth
                    maxWidth="lg" 
                    disableEscapeKeyDown // Changed from disableEscapeKey
                >
                     <DialogContent sx={{ p: 0, '&:first-of-type': { paddingTop: 0 } }}> {/* Changed :first-child to :first-of-type */}
                        {callDetailsPWA.roomName && (
                            <VideoCallManager
                                localId={identity.id} 
                                remoteId={callDetailsPWA.remoteUserId} 
                                roomName={callDetailsPWA.roomName}
                                isInitiator={callDetailsPWA.isInitiator} 
                                onEndCall={handleEndCallFromManagerPWA}
                                onCallActive={handleCallActivePWA} // Pass the new handler
                                callTitle={callDetailsPWA.appointmentTitle}
                            />
                         )}
                         {!callDetailsPWA.roomName && <CircularProgress sx={{m:4}}/>} 
                     </DialogContent>
                </Dialog>
            )}
            
             <Box sx={{ filter: isCallModalOpenPWA ? 'blur(2px)' : 'none', pointerEvents: isCallModalOpenPWA ? 'none': 'auto', transition: 'filter 0.3s ease-in-out' }}>
                <PatientCalendar />
            </Box>
        </Box>
    );
};

export default PatientDashboardPage;