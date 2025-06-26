import React, { useRef, useState, useEffect, useCallback } from 'react';
import { useSocket } from '../contexts/SocketContext'; // Import useSocket hook
import Peer from 'simple-peer';
import { Box, Button, Typography, IconButton, Grid, CircularProgress } from '@mui/material'; // Added Grid, CircularProgress
import MicOffIcon from '@mui/icons-material/MicOff';
import MicIcon from '@mui/icons-material/Mic';
import VideocamOffIcon from '@mui/icons-material/VideocamOff';
import VideocamIcon from '@mui/icons-material/Videocam';
import CallEndIcon from '@mui/icons-material/CallEnd';

const VideoCallManager = ({ localId, remoteId, roomName, isInitiator, onEndCall, callTitle, onCallActive }) => { // Added onCallActive
  console.log('[VideoCallManager PWA PROPS] localId:', localId, 'remoteId:', remoteId, 'roomName:', roomName, 'isInitiator:', isInitiator); // <<< ADD THIS LINE
  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const peerRef = useRef(null); // Changed from useState
  const streamRef = useRef(null); // Changed from useState
  const [isConnecting, setIsConnecting] = useState(true); // State to show connection progress
  const [isConnected, setIsConnected] = useState(false); // State to confirm peer connection
  const [isAudioMuted, setIsAudioMuted] = useState(false);
  const [isVideoMuted, setIsVideoMuted] = useState(false); // <<< ADDED THIS LINE
  const { socket } = useSocket(); // Correctly get socket using the hook

  // Ref to hold the latest onEndCall prop
  const onEndCallRef = useRef(onEndCall);
  useEffect(() => {
    onEndCallRef.current = onEndCall;
  }, [onEndCall]);

  // Ref to hold the latest onCallActive prop
  const onCallActiveRef = useRef(onCallActive);
  useEffect(() => {
    onCallActiveRef.current = onCallActive;
  }, [onCallActive]);

  // 1. Get User Media (Camera/Microphone)
  useEffect(() => {
    console.log('[VideoCallManager PWA] Attempting to get media stream (useEffect runs once)...');
    // let acquiredStream = null; // Not needed if using streamRef directly

    navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      .then(currentStream => {
        console.log('[VideoCallManager PWA] Media stream obtained.');
        streamRef.current = currentStream; // Use ref
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = currentStream;
        }
        // Manually trigger peer setup logic if needed, or rely on streamRef.current being available in the peer effect
        // For simplicity, the peer effect will check streamRef.current.
        // To ensure the peer effect re-evaluates when stream is ready, add a state variable.
        setStreamReady(true);
      })
      .catch(err => {
        console.error("[VideoCallManager] Error accessing media devices.", err);
        alert("Αποτυχία πρόσβασης σε κάμερα/μικρόφωνο. Βεβαιωθείτε ότι έχετε δώσει τις απαραίτητες άδειες.");
        if (onEndCallRef.current) {
          onEndCallRef.current();
        }
      });
  
    return () => {
      console.log('[VideoCallManager PWA] Cleanup: Releasing media stream and video elements.');
      if (streamRef.current) { // Use ref
        streamRef.current.getTracks().forEach(track => track.stop());
        console.log('[VideoCallManager PWA] Media stream tracks stopped.');
        streamRef.current = null; // Clear the ref
      }
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = null;
        console.log('[VideoCallManager] Local video srcObject cleared.');
      }
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = null;
        console.log('[VideoCallManager] Remote video srcObject cleared.');
      }
      // setStream(null); // Clearing stream state might be redundant if component is unmounting
                         // and could trigger peer effect with null stream if not careful.
                         // The peer effect's own cleanup should handle peer destruction.
      setStreamReady(false); // Reset stream ready state
    };
  }, []); // Empty dependency array: runs once on mount, cleans up on unmount.

  // Added state to trigger peer effect once stream is ready
  const [streamReady, setStreamReady] = useState(false);

  // 2. Initialize Peer Connection when ready
  useEffect(() => {
    // Only proceed if we have socket, stream from ref, room, and IDs
    if (!socket || !streamRef.current || !roomName || !localId || !remoteId || !streamReady) {
      console.log('[VideoCallManager PWA] Waiting for socket, stream, room, IDs, or streamReady signal...');
      return;
    }
    
    // Avoid creating multiple peers if one already exists or is being created
    if (peerRef.current) { // Use ref
        console.log('[VideoCallManager PWA] Peer already exists or is being set up.'); 
        return;
    }

    console.log(`[VideoCallManager PWA] Initializing Peer. Initiator: ${isInitiator}, Room: ${roomName}, LocalID: ${localId}, RemoteID: ${remoteId}, Stream Ready: ${streamReady}`); // Enhanced Log
    setIsConnecting(true);
    setIsConnected(false);

    const newPeer = new Peer({ 
        initiator: isInitiator, 
        trickle: false, // Use trickle: false for simplicity initially
        stream: streamRef.current // Use stream from ref
    });

    // --- Peer Event Handlers ---
    // const peerRef = { current: newPeer }; // This was an unused local variable, remove it.

    newPeer.on('signal', (data) => {
      console.log(`[VideoCallManager PWA] Emitting signal (type: ${data.type || 'candidate'}) to room ${roomName}. LocalID: ${localId}, RemoteID: ${remoteId}`);
      socket.emit('signal', {
        room: roomName,
        type: data.type || 'candidate',
        payload: data,
        sender_identity: localId, // PWA's ID
        receiver_identity: remoteId, // Doctor's ID
      });
    });

    newPeer.on('stream', (remoteStream) => {
      console.log('[VideoCallManager PWA] Received remote stream! Stream object:', remoteStream);
      if (remoteVideoRef.current) {
        console.log('[VideoCallManager PWA] remoteVideoRef.current is available. Assigning srcObject.');
        remoteVideoRef.current.srcObject = remoteStream;
        // The explicit style.display = 'block' was here, removing it as isConnected state handles this in JSX.
        console.log('[VideoCallManager PWA] remoteVideoRef.current.srcObject assigned. Video tracks:', remoteStream.getVideoTracks());
        
        // Attempt to play the video
        const playPromise = remoteVideoRef.current.play();
        if (playPromise !== undefined) {
          playPromise.then(_ => {
            console.log('[VideoCallManager PWA] Remote video playback started successfully.');
          }).catch(error => {
            console.error('[VideoCallManager PWA] Error attempting to play remote video:', error);
            // alert('Could not play incoming video. Please check browser permissions or try reconnecting.');
          });
        }

      } else {
        console.error('[VideoCallManager PWA] remoteVideoRef.current is NULL when \'stream\' event received!');
      }
      setIsConnecting(false); // Connected visually
      setIsConnected(true);   // Connected functionally
      if (onCallActiveRef.current) {
        onCallActiveRef.current();
      }
    });

    newPeer.on('connect', () => {
      console.log('[VideoCallManager] Peer connection established (CONNECT event).');
      setIsConnecting(false);
      setIsConnected(true);
      if (onCallActiveRef.current) {
        onCallActiveRef.current();
      }
    });

    // It's often better to handle call termination logic through the onEndCall prop
    // which controls the lifecycle of this component.
    // simple-peer's 'close' event can be used for cleanup if needed, but relying on
    // onEndCall to unmount and trigger the main cleanup effect is usually cleaner.
    // newPeer.on('close', () => {
    //   console.log('[VideoCallManager] Peer connection closed (CLOSE event).');
    //   if (onEndCallRef.current) onEndCallRef.current(); 
    // });

    newPeer.on('error', (err) => {
      console.error('[VideoCallManager PWA] Peer error:', err);
      if (err.message && !err.message.includes('_readableState')) {
        alert(`Προέκυψε σφάλμα σύνδεσης: ${err.message}`);
      }
      // Ensure onEndCallRef is called even with _readableState error to attempt cleanup
      if (onEndCallRef.current) onEndCallRef.current(); 
    });

    peerRef.current = newPeer; // Set the peer ref

    // Cleanup function for this effect
    return () => {
      console.log('[VideoCallManager PWA] Cleaning up Peer instance.');
      const peerToDestroy = peerRef.current; // Use local var for safety in cleanup
      if (peerToDestroy) { 
        if (streamRef.current && typeof peerToDestroy.removeStream === 'function' && !peerToDestroy.destroyed) {
          try {
            console.log('[VideoCallManager PWA] Attempting to remove stream from peer.');
            peerToDestroy.removeStream(streamRef.current); // Use stream from ref
            console.log('[VideoCallManager PWA] Stream removed from peer.');
          } catch (e) {
            console.warn('[VideoCallManager] Error removing stream from peer:', e);
          }
        }

        if (!peerToDestroy.destroyed) {
          try {
            console.log('[VideoCallManager PWA] Attempting to destroy peer.');
            peerToDestroy.destroy();
            console.log('[VideoCallManager PWA] Peer destroyed.');
          } catch (e) {
            // Catching potential errors during destroy, though _readableState might be async / deeper
            console.error('[VideoCallManager] Error during peer.destroy():', e);
            if (e.message && !e.message.includes('_readableState') && onEndCallRef.current) {
              // If destroy fails with a different error, still try to signal end of call
              // onEndCallRef.current(); // This might be too aggressive if already unmounting
            }
          }
        }
      }
      peerRef.current = null; // Clear the ref
      setIsConnected(false);
      setIsConnecting(false);
      // It's also good practice to ensure remote video is cleared if peer is destroyed
      if (remoteVideoRef.current) {
          remoteVideoRef.current.srcObject = null;
      }
    };

  // Dependencies for peer initialization
  }, [socket, roomName, localId, remoteId, isInitiator, streamReady]); // Depend on streamReady


  // 3. Listener for incoming signals from the other peer
  useEffect(() => {
    if (!socket) {
      console.log('[VideoCallManager PWA] Signal listener: Socket not available.');
      return;
    }
    // We need peerRef.current to be set up to process signals, but the effect should still run
    // if only remoteId changes, to update the closure for signalHandler.
    // The actual peerRef.current check happens inside signalHandler.
    if (!remoteId) {
      console.log('[VideoCallManager PWA] Signal listener: remoteId is not available. Cannot effectively process signals.');
      return;
    }

    const currentRemoteId = remoteId; // Capture remoteId for this specific effect closure

    const signalHandler = (data) => { 
      console.log(`[VideoCallManager PWA] signalHandler: Received signal. Type: ${data.type || 'N/A'}, From: ${data.sender_identity || 'N/A'}. Current remoteId in closure: ${currentRemoteId}`);
      if (!peerRef.current) {
        console.log(`[VideoCallManager PWA] signalHandler: Peer not yet available. Cannot process signal from ${data.sender_identity}.`);
        return;
      }
      if (data.sender_identity === currentRemoteId) {
          if (!peerRef.current.destroyed) {
              console.log(`[VideoCallManager PWA] signalHandler: Processing signal from matched remote peer (${currentRemoteId}). Payload:`, data.payload);
              peerRef.current.signal(data.payload);
          } else {
              console.log(`[VideoCallManager PWA] signalHandler: Peer is destroyed. Cannot process signal from ${data.sender_identity}.`);
          }
      } else {
          console.log(`[VideoCallManager PWA] signalHandler: Ignored signal. Reason: data.sender_identity (${data.sender_identity || 'N/A'}) !== currentRemoteIdInClosure (${currentRemoteId}).`);
      }
    };

    console.log(`[VideoCallManager PWA] Registering socket listener for "signal" event (expecting signals from remoteId: ${currentRemoteId})`);
    socket.on('signal', signalHandler);

    return () => {
      console.log(`[VideoCallManager PWA] Removing socket listener for "signal" event (was for remoteId: ${currentRemoteId})`);
      socket.off('signal', signalHandler);
    };
  }, [socket, remoteId, peerRef]); // Rerun if socket, remoteId, or the peerRef itself changes.


  // --- Media Control Handlers ---
  const handleToggleAudio = useCallback(() => {
    if (streamRef.current) { // Use ref
      const audioTracks = streamRef.current.getAudioTracks();
      if (audioTracks.length > 0) {
        audioTracks[0].enabled = !audioTracks[0].enabled;
        setIsAudioMuted(!audioTracks[0].enabled);
      }
    }
  }, []); // streamRef.current change doesn't need to be a dependency

  const handleToggleVideo = useCallback(() => {
    if (streamRef.current) { // Use ref
      const videoTracks = streamRef.current.getVideoTracks();
      if (videoTracks.length > 0) {
        videoTracks[0].enabled = !videoTracks[0].enabled;
        setIsVideoMuted(!videoTracks[0].enabled);
         // You might want to show/hide the local video element or display an avatar
         if (localVideoRef.current) {
            localVideoRef.current.style.visibility = videoTracks[0].enabled ? 'visible' : 'hidden';
         }
      }
    }
  }, []); // streamRef.current change doesn't need to be a dependency

  return (
    <Box sx={{ p: { xs: 1, sm: 2 }, bgcolor: 'background.paper', position: 'relative' }}>
      <Typography variant="h6" align="center" sx={{ mb: 1 }}>
        {callTitle || 'Τηλεδιάσκεψη'}
      </Typography>
       <Typography variant="caption" align="center" display="block" sx={{ mb: 2, color: 'text.secondary' }}>
         (Με {remoteId})
      </Typography>

      <Grid container spacing={2} justifyContent="center" alignItems="center" columns={12}>
        {/* Local Video */}
        <Grid colSpan={{ xs: 12, sm: 6 }} sx={{ position: 'relative' }}> 
          <video 
            ref={localVideoRef} 
            autoPlay 
            muted /* Your own video is always muted locally */
            playsInline 
            style={{ 
                width: '100%', 
                borderRadius: 8, 
                backgroundColor: '#333',
                transform: 'scaleX(-1)', // Mirror view
                display: isVideoMuted ? 'none' : 'block' // Hide if video muted
            }} 
          />
          {isVideoMuted && (
               <Box sx={{ width: '100%', aspectRatio: '16/9', borderRadius: 8, backgroundColor: '#333', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                   <VideocamOffIcon sx={{ color: 'rgba(255,255,255,0.5)', fontSize: 50 }}/>
               </Box>
          )}
          <Typography variant="caption" sx={{ position: 'absolute', bottom: 8, left: 8, color: 'white', bgcolor: 'rgba(0,0,0,0.5)', px: 1, borderRadius: 1 }}>
            Εσείς ({localId}) {isAudioMuted ? '(Σίγαση)' : ''}
          </Typography>
        </Grid>

        {/* Remote Video */}
        <Grid colSpan={{ xs: 12, sm: 6 }} sx={{ position: 'relative', width: '100%', aspectRatio: '16/9', backgroundColor: '#333', borderRadius: '8px' }}> 
            {isConnecting && !isConnected && (
                 <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'absolute', top: 0, left: 0 }}>
                    <CircularProgress color="inherit" sx={{color: 'white', mb:1}} size={30} />
                    <Typography variant="caption" color="white">Σύνδεση με {remoteId}...</Typography>
                </Box>
            )}
            {/* Always render the video tag so ref is available. Control visibility with style. */}
            <video 
                ref={remoteVideoRef} 
                autoPlay 
                playsInline 
                style={{ 
                    width: '100%', 
                    height: '100%',
                    borderRadius: '8px', 
                    objectFit: 'cover', // Ensures video covers the area
                    display: isConnected ? 'block' : 'none' // Show only when connected
                }} 
            />
            {/* Fallback message if connection attempt finished but was not successful (e.g. error, or before connection fully established but no longer connecting) */}
            {!isConnecting && !isConnected && (
                 <Box sx={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'absolute', top: 0, left: 0 }}>
                     <Typography variant="caption" color="white">Αναμονή σύνδεσης...</Typography>
                 </Box>
            )}
        </Grid>
      </Grid>

      {/* Controls */}
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 1.5 }}>
        <IconButton onClick={handleToggleAudio} color={isAudioMuted ? 'default' : 'primary'} title={isAudioMuted ? 'Κατάργηση Σίγασης' : 'Σίγαση Μικροφώνου'}>
          {isAudioMuted ? <MicOffIcon /> : <MicIcon />}
        </IconButton>
        <IconButton onClick={handleToggleVideo} color={isVideoMuted ? 'default' : 'primary'} title={isVideoMuted ? 'Ενεργοποίηση Κάμερας' : 'Απενεργοποίηση Κάμερας'}>
          {isVideoMuted ? <VideocamOffIcon /> : <VideocamIcon />}
        </IconButton>
        <Button 
          variant="contained" 
          color="error" 
          onClick={onEndCall} // Use the callback directly
          startIcon={<CallEndIcon />}
          sx={{ ml: 2 }}
        >
          Τερματισμός
        </Button>
      </Box>
    </Box>
  );
};

export default VideoCallManager;