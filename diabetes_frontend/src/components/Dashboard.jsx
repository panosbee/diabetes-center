// diabetes_frontend/src/components/Dashboard.jsx

import React, { useState, useEffect, useCallback, useContext, useRef } from 'react';
import {
  Card, CardContent, Grid, Typography, Box, Avatar,
  Dialog, DialogContent, DialogTitle, DialogActions, Button,
  CircularProgress, Paper, List, ListItem, ListItemText, ListItemAvatar
} from '@mui/material';
import { useGetList, Title, useGetIdentity, useNotify } from 'react-admin';
import {
  PeopleAltOutlined as PatientsIcon,
  CalendarMonthOutlined as SessionsIcon,
  LocalHospitalOutlined as DoctorsIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';

// --- Imports με ΔΙΟΡΘΩΜΕΝΕΣ ΔΙΑΔΡΟΜΕΣ ---
// Υποθέτουμε ότι όλα αυτά τα αρχεία είναι στον ίδιο φάκελο 'src/components/'
import InteractiveCalendar from './InteractiveCalendar'; 
import { UpcomingBookedAppointmentsList } from './UpcomingBookedAppointmentsList'; 
import AllUpcomingActivitiesList from './AllUpcomingActivitiesList'; // Χωρίς άγκιστρα {}       
import VideoCallManager from './VideoCallManager'; 
// Το Context πιθανόν είναι ένα επίπεδο πάνω, οπότε αυτό μπορεί να είναι σωστό:
import { SocketContext, useSocket } from '../contexts/SocketContext';  
// -----------------------------------------

// StatCard component (το είχαμε ορίσει και πριν)
const StatCard = ({ icon, title, value, color }) => {
  const theme = useTheme();
  const colorName = color || 'primary'; 
  return (
    <Card elevation={0} sx={{ height: '100%', borderRadius: 3, transition: 'transform 0.3s', '&:hover': { transform: 'translateY(-4px)' } }}>
      <CardContent>
        <Box display="flex" alignItems="center" mb={1}>
          <Avatar
            sx={{
              bgcolor: theme.palette[colorName]?.light || theme.palette.grey[200],
              color: theme.palette[colorName]?.main || theme.palette.text.secondary,
              mr: 2
            }}
          >
            {icon}
          </Avatar>
          <Typography variant="h6" color="textSecondary" fontWeight={500} fontSize="1rem">
            {title}
          </Typography>
        </Box>
        <Typography variant="h4" component="div" fontWeight={700} color={theme.palette[colorName]?.main || theme.palette.text.primary}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
};

// Το κύριο Dashboard component
const Dashboard = () => {
    const { socket, isConnected: socketIsConnected } = useSocket(); // Διόρθωση: Destructuring
    const { identity, isLoading: identityLoading } = useGetIdentity();
    const notify = useNotify();
    const theme = useTheme(); 

    // States for WebRTC Call Management
    const [isCallModalOpen, setIsCallModalOpen] = useState(false);
    const [callDetails, setCallDetails] = useState({ 
        isActive: false, remoteUserId: null, roomName: null, 
        isInitiator: false, callStatus: 'idle', 
        appointmentTitle: null, remoteUserSid: null 
    });
    const [incomingCallPromptData, setIncomingCallPromptData] = useState(null); 

    // Data fetching for stats (π.χ., από react-admin)
    const { data: patients, isLoading: patientsLoading } = useGetList('patients');
    const { data: sessions, isLoading: sessionsLoading } = useGetList('sessions'); 
    const { data: doctors, isLoading: doctorsLoading } = useGetList('doctors');

    // --- Callbacks ---
    const resetCallState = useCallback(() => {
        console.log('[Dashboard] Resetting call state.');
        setIsCallModalOpen(false);
        setCallDetails({ isActive: false, remoteUserId: null, roomName: null, isInitiator: false, callStatus: 'idle', appointmentTitle: null, remoteUserSid: null });
        setIncomingCallPromptData(null);
    }, []); // Κενές εξαρτήσεις, απλά θέτει αρχικές τιμές

    const handleInitiateCall = useCallback((targetPatientId, bookedAppointmentTitle) => {
        if (!socket || !socketIsConnected) return notify('Σφάλμα: Δεν υπάρχει ενεργή σύνδεση για τηλεδιάσκεψη.', { type: 'error' });
        if (!identity) return notify('Σφάλμα: Δεν βρέθηκε η ταυτότητα του γιατρού.', { type: 'error' });
        if (!targetPatientId) return notify('Σφάλμα: Δεν προσδιορίστηκε ο ασθενής για κλήση.', { type: 'error' });
        if (callDetails.isActive || callDetails.callStatus === 'dialing') return notify('Είστε ήδη σε διαδικασία κλήσης.', { type: 'warning' });

        console.log(`[Dashboard] Doctor ${identity.id} initiating call to patient ${targetPatientId} for appointment: ${bookedAppointmentTitle}`);
        setCallDetails({
            isActive: false, remoteUserId: targetPatientId, roomName: null, 
            isInitiator: true, callStatus: 'dialing', 
            appointmentTitle: bookedAppointmentTitle, remoteUserSid: null
        });
        setIsCallModalOpen(true); 
        socket.emit('initiate_call', { target_user_identity: targetPatientId });
        console.log(`[Dashboard] 'initiate_call' emitted for ${targetPatientId}`);
    }, [socket, socketIsConnected, identity, notify, callDetails]); // Εξαρτάται από το callDetails για να μην καλέσει διπλά

    const handleEndCallFromManager = useCallback(() => {
        if (socket && callDetails.roomName && identity?.id) {
             console.log(`[Dashboard] Doctor ${identity.id} manually ending call in room ${callDetails.roomName}`);
             socket.emit('end_call', { room: callDetails.roomName }); 
        } else {
             console.log(`[Dashboard] Manually closing call modal (no room or ending dialing). Status: ${callDetails.callStatus}`);
        }
        resetCallState(); 
    }, [socket, callDetails, identity, resetCallState]);

    const handleAcceptIncoming = useCallback(() => {
        if (!socket || !socketIsConnected) return notify('Socket not connected.', { type: 'error' });
        if (!incomingCallPromptData || !identity?.id) return notify('Missing call data or user identity.', { type: 'error' });
        
        const { caller_identity, caller_sid, suggested_room, caller_name } = incomingCallPromptData;
        console.log(`[Dashboard] Doctor ${identity.id} accepting call from ${caller_identity} in room ${suggested_room}`);
        
        socket.emit('accept_call', { caller_sid, caller_identity, room_name: suggested_room });
        setCallDetails({
            isActive: false, remoteUserId: caller_identity, roomName: suggested_room,
            isInitiator: false, callStatus: 'active', 
            appointmentTitle: `Κλήση από ${caller_name || caller_identity}`, remoteUserSid: caller_sid
        });
        setIsCallModalOpen(true);
        setIncomingCallPromptData(null); 
        socket.emit('join_room', { room: suggested_room }); 
        console.log(`[Dashboard] Doctor joining room ${suggested_room} after accepting call.`);

    }, [socket, socketIsConnected, incomingCallPromptData, identity, notify, resetCallState]);

    const handleRejectIncoming = useCallback(() => {
        if (socket && incomingCallPromptData) {
            console.log(`[Dashboard] Doctor rejecting call from ${incomingCallPromptData.caller_identity}`);
            socket.emit('reject_call', { caller_sid: incomingCallPromptData.caller_sid, caller_identity: incomingCallPromptData.caller_identity });
        }
        setIncomingCallPromptData(null);
    }, [socket, incomingCallPromptData]);

    const handleCallActive = useCallback(() => {
        console.log('[Dashboard] Call is now active (VideoCallManager reported peer connection).');
        setCallDetails(prevDetails => {
            // Only update if the call was supposed to be active and details exist
            if (prevDetails && prevDetails.callStatus === 'active') {
                return { ...prevDetails, isActive: true };
            }
            // If onCallActive is called but status isn't 'active' yet, it might be premature
            // or a sign that callStatus should have been 'active'.
            // For now, only affirm isActive if callStatus is already 'active'.
            console.log('[Dashboard] handleCallActive: callStatus was not "active", current details:', prevDetails);
            return prevDetails;
        });
    }, []);

    // --- Socket Event Listeners ---
    useEffect(() => {
        if (!socket || !identity || identityLoading) return;
        console.log('[Dashboard useEffect] Setting up Socket listeners...');

        const onCallAccepted = (data) => { 
            console.log('[Dashboard] Received \'call_accepted\' event. Data:', JSON.stringify(data));
            // Accessing callDetails from state directly here might be stale if not managed carefully with refs or useCallback dependencies.
            // However, callDetails IS in the useEffect dependency array, so this function closure should be recreated with the latest callDetails.
            console.log('[Dashboard] Current callDetails BEFORE processing \'call_accepted\':', JSON.stringify(callDetailsRef.current)); // Using a ref for most up-to-date state in callback

            if (callDetailsRef.current.isInitiator && data && data.callee_identity && callDetailsRef.current.remoteUserId === data.callee_identity) {
                notify(`Ο ασθενής ${data.callee_name || data.callee_identity} αποδέχτηκε την κλήση.`, { type: 'success' });
                setCallDetails(prev => ({
                    ...prev,
                    roomName: data.room_name,
                    callStatus: 'active', // This is key for rendering VideoCallManager
                    remoteUserSid: data.callee_sid,
                    // isActive will be set by onCallActive from VideoCallManager once peer connects
                }));
                setIsCallModalOpen(true); 
                if (socket && data.room_name) {
                    socket.emit('join_room', { room: data.room_name });
                    console.log(`[Dashboard] Doctor emitted 'join_room' for room: ${data.room_name}`);
                } else {
                    console.error('[Dashboard] Socket or room_name missing in onCallAccepted, cannot join room.', {socket_exists: !!socket, room_name: data ? data.room_name : 'data_undefined'});
                }
            } else {
                 console.warn("[Dashboard] Received 'call_accepted' but conditions not met or data missing.", { 
                     isInitiator: callDetailsRef.current.isInitiator, 
                     expectedRemoteUserId: callDetailsRef.current.remoteUserId, 
                     receivedCalleeIdentity: data ? data.callee_identity : 'data_undefined',
                     currentCallDetailsState: callDetailsRef.current, // Use ref for logging
                     eventData: data 
                 });
            }
        };
        
        const onCallRejected = (data) => { 
             console.log('[Dashboard] Received call_rejected:', data);
             if (callDetails.isInitiator && callDetails.remoteUserId === data.callee_identity) {
                notify(`Η κλήση απορρίφθηκε από τον χρήστη ${data.callee_identity}.`, { type: 'warning' });
                resetCallState();
             }
        };

        const onTargetUnavailable = (data) => { 
            console.log('[Dashboard] Received target_unavailable:', data);
            if (callDetails.isInitiator && callDetails.remoteUserId === data.target_identity) {
                notify(`Ο χρήστης ${data.target_identity} δεν είναι διαθέσιμος (${data.status}).`, { type: 'error' });
                resetCallState();
            }
        };
        
        const onCallEnded = (data) => { 
            console.log('[Dashboard] Received call_ended from:', data.ender_identity, 'for room:', data.room);
             if (callDetails.isActive && callDetails.roomName === data.room) {
                 notify('Η τηλεδιάσκεψη τερματίστηκε.', { type: 'info' });
                 resetCallState();
             }
        };
        
        const onCallInitiationFailed = (data) => {
             console.error('[Dashboard] Call initiation failed:', data.error);
             notify(`Σφάλμα έναρξης κλήσης: ${data.error}`, { type: 'error' });
             if (callDetails.isInitiator && callDetails.remoteUserId === data.target_identity) {
                 resetCallState();
             }
         };

        const onIncomingCallToDoctor = (data) => { 
             console.log('[Dashboard] Received INCOMING call from patient:', data.caller_identity);
             if (callDetails.isActive || callDetails.callStatus === 'dialing') {
                 console.warn('[Dashboard] Already in a call, rejecting incoming call from', data.caller_identity);
                 if(socket) socket.emit('user_busy', { target_sid: data.caller_sid });
                 return;
             }
             setIncomingCallPromptData(data);
         };
         
        // Register listeners
        socket.on('call_accepted', onCallAccepted);
        socket.on('call_rejected', onCallRejected);
        socket.on('target_unavailable', onTargetUnavailable);
        socket.on('call_ended', onCallEnded);
        socket.on('call_initiation_failed', onCallInitiationFailed);
        socket.on('incoming_call_to_doctor', onIncomingCallToDoctor); 

        return () => {
            // Cleanup listeners
            console.log('[Dashboard useEffect Cleanup] Removing Socket listeners...');
            socket.off('call_accepted', onCallAccepted);
            socket.off('call_rejected', onCallRejected);
            socket.off('target_unavailable', onTargetUnavailable);
            socket.off('call_ended', onCallEnded);
            socket.off('call_initiation_failed', onCallInitiationFailed);
            socket.off('incoming_call_to_doctor', onIncomingCallToDoctor);
        };
    }, [socket, identity, identityLoading, notify, resetCallState]); 

    // Ref to hold the latest callDetails for use in socket handlers to avoid stale closures
    const callDetailsRef = useRef(callDetails);
    useEffect(() => {
        callDetailsRef.current = callDetails;
    }, [callDetails]);

    // --- Render Logic ---
    if (identityLoading) {
      return <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress /></Box>;
    }

    return (
        <>
            <Title title="Πίνακας Ελέγχου Ιατρού" />
            
            {/* Incoming Call Prompt Dialog */}
            {incomingCallPromptData && (
                <Dialog open={!!incomingCallPromptData} onClose={handleRejectIncoming} >
                    <DialogTitle>Εισερχόμενη Κλήση Τηλεϊατρικής</DialogTitle>
                    <DialogContent>
                        <Typography>
                            Έχετε κλήση από τον ασθενή: {incomingCallPromptData.caller_name || incomingCallPromptData.caller_identity}
                        </Typography>
                        <Typography variant='caption'>Δωμάτιο: {incomingCallPromptData.suggested_room}</Typography>
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={handleRejectIncoming} color="error">Απόρριψη</Button>
                        <Button onClick={handleAcceptIncoming} color="primary" autoFocus>Αποδοχή</Button>
                    </DialogActions>
                </Dialog>
            )}

            {/* Video Call Modal */}
            {isCallModalOpen && callDetails && identity && (
                <Dialog
                    open={isCallModalOpen}
                    onClose={(event, reason) => { 
                       if ((reason === 'backdropClick' || reason === 'escapeKeyDown') && callDetails.callStatus === 'active') return; 
                       handleEndCallFromManager(); 
                    }} 
                    fullWidth
                    maxWidth={callDetails.callStatus === 'active' ? "lg" : "sm"} 
                    disableEscapeKeyDown={callDetails.callStatus === 'active'} // Corrected prop name and direct boolean assignment
                >
                     <DialogTitle sx={{ textAlign:'center', pt: callDetails.callStatus === 'active' ? 1 : 2, pb:1, fontSize: '1rem' }}>
                         {callDetails.callStatus === 'dialing' && `Γίνεται Κλήση...`}
                         {callDetails.callStatus === 'active' && `Σε κλήση με ${callDetails.appointmentTitle || callDetails.remoteUserId}`}
                     </DialogTitle>
                    <DialogContent sx={{ 
                        p: callDetails.callStatus === 'active' ? 0 : 2, 
                        '&:first-of-type': { paddingTop: callDetails.callStatus === 'active' ? 0 : 'auto' } // Changed :first-child to :first-of-type
                    }}>
                        {callDetails.callStatus === 'dialing' && (
                            <Box sx={{textAlign: 'center', p:3}}>
                                <Typography variant="body1" gutterBottom>Προς: {callDetails.appointmentTitle || callDetails.remoteUserId}</Typography>
                                <CircularProgress sx={{my: 3}} />
                                <Button onClick={handleEndCallFromManager} color="error" variant="outlined">Ακύρωση Κλήσης</Button>
                            </Box>
                        )}
                        {callDetails.callStatus === 'active' && callDetails.roomName && identity && (
                            <VideoCallManager
                                localId={identity.id}
                                remoteId={callDetails.remoteUserId}
                                roomName={callDetails.roomName}
                                isInitiator={callDetails.isInitiator}
                                onEndCall={handleEndCallFromManager} 
                                callTitle={callDetails.appointmentTitle}
                                onCallActive={handleCallActive} // Pass the new handler
                            />
                        )}
                    </DialogContent>
                </Dialog>
            )}

            {/* Dimmed background when call modal is open */}
            <Box sx={{ filter: isCallModalOpen ? 'blur(2px)' : 'none', pointerEvents: isCallModalOpen ? 'none': 'auto', transition: 'filter 0.3s ease-in-out' }}>
                <Box mb={4}>
                    <Typography variant="h4" component="h1" gutterBottom fontWeight={700} color="primary">
                        Καλώς ήρθατε, {identity?.fullName || 'Ιατρέ'}!
                    </Typography>
                    <Typography variant="body1" color="textSecondary">
                        Επισκόπηση Κέντρου Διαχείρισης Διαβήτη
                    </Typography>
                </Box>
                
                {/* Stat Cards Grid */}
                 <Grid container spacing={3} mb={4} columns={12}>
                    <Grid item colSpan={{ xs: 12, sm: 6, md: 4 }}>
                    <StatCard 
                        icon={<PatientsIcon />} 
                        title="Σύνολο Ασθενών" 
                        value={patientsLoading ? '...' : patients?.length || 0}
                        color="primary" 
                    />
                    </Grid>
                    <Grid item colSpan={{ xs: 12, sm: 6, md: 4 }}>
                    <StatCard 
                        icon={<SessionsIcon />} 
                        title="Σύνολο Συνεδριών" 
                        value={sessionsLoading ? '...' : sessions?.length || 0} // Needs review
                        color="secondary" 
                    />
                    </Grid>
                    <Grid item colSpan={{ xs: 12, sm: 6, md: 4 }}>
                    <StatCard 
                        icon={<DoctorsIcon />} 
                        title="Σύνολο Ιατρών" 
                        value={doctorsLoading ? '...' : doctors?.length || 0}
                        color="info" 
                    />
                    </Grid>
                </Grid>
                
                {/* Main Content Grid */}
                <Grid container spacing={3} columns={12}>
                    <Grid item colSpan={{ xs: 12, lg: 8 }}> 
                       <InteractiveCalendar 
                           onInitiateCall={handleInitiateCall} // Πέρασμα του callback
                       /> 
                    </Grid>
                    
                    <Grid item colSpan={{ xs: 12, lg: 4 }}> 
                      {/* Upcoming Appointments List */}
                      <Card sx={{ mb: 3, borderRadius: 3 }}>
                        <CardContent>
                          <Typography variant="h6" gutterBottom fontWeight={600} color="text.primary">
                            Επερχόμενα Ραντεβού
                          </Typography>
                          <Box mt={1}>
                            {/* Το component που φέρνει τα πραγματικά δεδομένα */}
                            <UpcomingBookedAppointmentsList />
                          </Box>
                        </CardContent>
                      </Card>
                      
                      {/* Other Activities List */}
                      <Card sx={{ borderRadius: 3 }}>
                        <CardContent>
                          <Typography variant="h6" gutterBottom fontWeight={600} color="text.primary">
                            Λοιπές Δραστηριότητες
                          </Typography>
                          <Box mt={1}>
                            {/* Το component που φέρνει τα πραγματικά δεδομένα */}
                            <AllUpcomingActivitiesList />
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                </Grid>
            </Box>
        </>
    );
};

export default Dashboard;