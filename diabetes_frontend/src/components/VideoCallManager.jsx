import React, { useRef, useState, useEffect, useCallback } from 'react';
import { useSocket } from '../contexts/SocketContext';
import Peer from 'simple-peer';
import { Box, Button, Typography, IconButton, Grid, CircularProgress } from '@mui/material';
import MicOffIcon from '@mui/icons-material/MicOff';
import MicIcon from '@mui/icons-material/Mic';
import VideocamOffIcon from '@mui/icons-material/VideocamOff';
import VideocamIcon from '@mui/icons-material/Videocam';
import CallEndIcon from '@mui/icons-material/CallEnd';

const VideoCallManager = ({ localId, remoteId, roomName, isInitiator, onEndCall, callTitle, onCallActive }) => {
  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const peerRef = useRef(null);
  const streamRef = useRef(null);

  const [isConnecting, setIsConnecting] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [isAudioMuted, setIsAudioMuted] = useState(false);
  const [isVideoMuted, setIsVideoMuted] = useState(false);
  const [streamReady, setStreamReady] = useState(false); // To signal when media stream is ready
  const [peerInstanceReady, setPeerInstanceReady] = useState(false); // New state

  const { socket } = useSocket();

  // Refs for callbacks to ensure latest versions are used
  const onEndCallRef = useRef(onEndCall);
  useEffect(() => { onEndCallRef.current = onEndCall; }, [onEndCall]);

  const onCallActiveRef = useRef(onCallActive);
  useEffect(() => { onCallActiveRef.current = onCallActive; }, [onCallActive]);

  // 1. Get User Media (Camera/Microphone)
  useEffect(() => {
    console.log('[VideoCallManager FE] Attempting to get media stream...');
    navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      .then(currentStream => {
        console.log('[VideoCallManager FE] Media stream obtained.');
        streamRef.current = currentStream;
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = currentStream;
        }
        setStreamReady(true); // Signal that stream is ready for peer connection
      })
      .catch(err => {
        console.error("[VideoCallManager FE] Error accessing media devices.", err);
        alert("Αποτυχία πρόσβασης σε κάμερα/μικρόφωνο. Βεβαιωθείτε ότι έχετε δώσει τις απαραίτητες άδειες.");
        if (onEndCallRef.current) {
          onEndCallRef.current();
        }
      });
    
    return () => {
      if (streamRef.current) {
        console.log('[VideoCallManager FE] Stopping media stream tracks on cleanup (getUserMedia effect).');
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      setStreamReady(false);
    };
  }, []); // Run once on mount

  // 2. Initialize Peer Connection when ready
  useEffect(() => {
    if (!socket || !streamReady || !streamRef.current || !roomName || !localId || !remoteId) {
      console.log('[VideoCallManager FE] Waiting for socket, stream, room, or IDs...');
      setPeerInstanceReady(false); // Ensure peer is not considered ready
      return;
    }
    
    if (peerRef.current) {
      console.log('[VideoCallManager FE] Peer already exists or is being set up.');
      // If it already exists and is valid, ensure peerInstanceReady reflects this.
      // However, this effect should ideally only set up a new peer.
      // For simplicity, we assume if peerRef.current exists, this effect might be re-running,
      // and peerInstanceReady would have been set by its initial successful run.
      return;
    }

    console.log(`[VideoCallManager FE] Initializing Peer. Initiator: ${isInitiator}, Room: ${roomName}`);
    setIsConnecting(true);
    setIsConnected(false);

    const newPeer = new Peer({ 
      initiator: isInitiator, 
      trickle: false,
      stream: streamRef.current 
    });

    newPeer.on('signal', (data) => {
      console.log(`[VideoCallManager FE] Emitting signal (type: ${data.type || 'candidate'}, to: ${remoteId}, room: ${roomName})`);
      socket.emit('signal', {
        room: roomName,
        // Ensure sender_identity is the localId of this peer (doctor)
        sender_identity: localId, 
        receiver_identity: remoteId, // Explicitly state intended recipient
        type: data.type || 'candidate',
        payload: data,
      });
    });

    newPeer.on('stream', (remoteStream) => {
      console.log('[VideoCallManager FE] Received remote stream! Stream object:', remoteStream);
      if (remoteVideoRef.current) {
        console.log('[VideoCallManager FE] remoteVideoRef.current is available. Assigning srcObject.');
        remoteVideoRef.current.srcObject = remoteStream;
        console.log('[VideoCallManager FE] remoteVideoRef.current.srcObject assigned. Video tracks:', remoteStream.getVideoTracks());
        
        // Attempt to play the video
        const playPromise = remoteVideoRef.current.play();
        if (playPromise !== undefined) {
          playPromise.then(_ => {
            console.log('[VideoCallManager FE] Remote video playback started successfully.');
          }).catch(error => {
            console.error('[VideoCallManager FE] Error attempting to play remote video:', error);
            // alert('Could not play incoming video. Please check browser permissions or try reconnecting.');
          });
        }
      } else {
        console.error('[VideoCallManager FE] remoteVideoRef.current is NULL when \'stream\' event received!');
      }
      // Note: 'connect' event is usually a more reliable indicator for onCallActive
    });

    newPeer.on('connect', () => {
      console.log('[VideoCallManager FE] Peer connection established (CONNECT event).');
      setIsConnecting(false);
      setIsConnected(true);
      if (onCallActiveRef.current) {
        onCallActiveRef.current();
      }
    });

    newPeer.on('close', () => {
      console.log('[VideoCallManager FE] Peer connection closed.');
      if (onEndCallRef.current) {
        onEndCallRef.current(); // Trigger cleanup in parent
      }
    });

    newPeer.on('error', (err) => {
      console.error('[VideoCallManager FE] Peer error:', err);
      // Avoid alert if error is 'ERR_CONNECTION_CLOSED' as 'close' event will handle it
      if (err.code !== 'ERR_CONNECTION_CLOSED') {
        alert(`Προέκυψε σφάλμα σύνδεσης: ${err.message || err}`);
      }
      if (onEndCallRef.current) {
        onEndCallRef.current(); // Trigger cleanup in parent
      }
    });

    peerRef.current = newPeer;
    setPeerInstanceReady(true); // Signal that peer instance is now set

    return () => {
      console.log('[VideoCallManager FE] Cleaning up Peer instance (peer effect).');
      setPeerInstanceReady(false); // Reset peer readiness
      const peerToDestroy = peerRef.current;
      if (peerToDestroy) {
        if (streamRef.current && typeof peerToDestroy.removeStream === 'function' && !peerToDestroy.destroyed) {
          try {
            console.log('[VideoCallManager FE] Removing stream from peer.');
            peerToDestroy.removeStream(streamRef.current);
          } catch (e) {
            console.warn('[VideoCallManager FE] Error removing stream from peer:', e);
          }
        }
        if (!peerToDestroy.destroyed) {
          console.log('[VideoCallManager FE] Destroying peer.');
          peerToDestroy.destroy();
        }
      }
      peerRef.current = null;
      setIsConnected(false);
      setIsConnecting(false); // Reset connection state
    };
  }, [socket, streamReady, roomName, localId, remoteId, isInitiator]); // Removed onEndCall from here, using ref

  // 3. Listener for incoming signals from the other peer
  useEffect(() => {
    console.log(`[VideoCallManager FE] Attempting to set up signal listener. Socket: ${!!socket}, PeerInstanceReady: ${peerInstanceReady}, Peer Exists: ${!!peerRef.current}, Peer Destroyed: ${peerRef.current ? peerRef.current.destroyed : 'N/A'}, localId: ${localId}, remoteId: ${remoteId}`);
    // Depend on peerInstanceReady; also check peerRef.current directly as an additional safeguard.
    if (!socket || !peerInstanceReady || !peerRef.current || peerRef.current.destroyed || !localId || !remoteId) { 
        console.log(`[VideoCallManager FE] Conditions not met for signal listener. Socket: ${!!socket}, PeerInstanceReady: ${peerInstanceReady}, Peer Exists: ${!!peerRef.current}, Peer Destroyed: ${peerRef.current ? peerRef.current.destroyed : 'N/A'}, localId: ${localId}, remoteId: ${remoteId}`);
        return;
    }

    const signalHandler = (data) => { 
      console.log(`[VideoCallManager FE] Raw signal received on socket. Type: ${data.type}, Sender: ${data.sender_identity}, Receiver: ${data.receiver_identity}, Expected Remote: ${remoteId}, My LocalId: ${localId}`);
      // Ensure the signal is intended for this peer (localId) and is from the expected remote peer (remoteId)
      if (data.receiver_identity === localId && data.sender_identity === remoteId) {
        if (peerRef.current && !peerRef.current.destroyed) {
          console.log(`[VideoCallManager FE] Processing signal from remote peer (${data.sender_identity}) for me (${data.receiver_identity}). Type: ${data.type || 'candidate'}. Payload:`, data.payload);
          peerRef.current.signal(data.payload);
        } else {
          console.warn(`[VideoCallManager FE] Peer not ready or destroyed when signal received from ${data.sender_identity} for ${data.receiver_identity}. Peer exists: ${!!peerRef.current}, Peer destroyed: ${peerRef.current ? peerRef.current.destroyed : 'N/A'}`);
        }
      } else {
        // Log if the signal was not for us or not from the expected sender
        console.log(`[VideoCallManager FE] Ignored signal. Destined for: ${data.receiver_identity} (me: ${localId}), From: ${data.sender_identity} (expected: ${remoteId}). Type: ${data.type}`);
      }
    };

    console.log(`[VideoCallManager FE] SUCCESSFULLY Registered socket listener for "signal" (localId: ${localId}, remoteId: ${remoteId}, peerId: ${peerRef.current ? peerRef.current._id : 'N/A'})`);
    socket.on('signal', signalHandler);

    return () => {
      console.log(`[VideoCallManager FE] Removing socket listener for "signal" (localId: ${localId}, remoteId: ${remoteId})`);
      socket.off('signal', signalHandler);
    };
  }, [socket, localId, remoteId, peerInstanceReady]); // Depend on peerInstanceReady instead of peerRef.current directly

  const handleToggleAudio = useCallback(() => {
    if (streamRef.current) {
      const audioTracks = streamRef.current.getAudioTracks();
      if (audioTracks.length > 0) {
        audioTracks[0].enabled = !audioTracks[0].enabled;
        setIsAudioMuted(!audioTracks[0].enabled);
      }
    }
  }, []); // streamRef.current doesn't need to be a dependency for useCallback if its content changes don't redefine the function

  const handleToggleVideo = useCallback(() => {
    if (streamRef.current) {
      const videoTracks = streamRef.current.getVideoTracks();
      if (videoTracks.length > 0) {
        videoTracks[0].enabled = !videoTracks[0].enabled;
        setIsVideoMuted(!videoTracks[0].enabled);
         if (localVideoRef.current) { // Keep this logic as it was
            localVideoRef.current.style.display = videoTracks[0].enabled ? 'block' : 'none';
         }
      }
    }
  }, []); // Same as above for streamRef.current

  // --- Render Logic ---
  // (The existing render logic seems fine, ensure it uses isVideoMuted for local video display)
  // Minor adjustment to local video style for consistency if isVideoMuted is true
  // The existing code already handles this with: style={{ display: isVideoMuted ? 'none' : 'block' }}

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
            muted
            playsInline 
            style={{ 
                width: '100%', 
                borderRadius: 8, 
                backgroundColor: '#333',
                transform: 'scaleX(-1)',
                display: !isVideoMuted ? 'block' : 'none' // Show if not muted
            }} 
          />
          {isVideoMuted && ( // Show placeholder if video is muted
               <Box sx={{ width: '100%', aspectRatio: '16/9', borderRadius: 8, backgroundColor: '#333', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                   <VideocamOffIcon sx={{ color: 'rgba(255,255,255,0.5)', fontSize: 50 }}/>
               </Box>
          )}
          <Typography variant="caption" sx={{ position: 'absolute', bottom: 8, left: 8, color: 'white', bgcolor: 'rgba(0,0,0,0.5)', px: 1, borderRadius: 1 }}>
            Εσείς ({localId}) {isAudioMuted ? '(Σίγαση)' : ''}
          </Typography>
        </Grid>

        {/* Remote Video */}
        <Grid colSpan={{ xs: 12, sm: 6 }}>
            {isConnecting && !isConnected && (
                 <Box sx={{ width: '100%', aspectRatio: '16/9', borderRadius: 8, backgroundColor: '#333', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                    <CircularProgress color="inherit" sx={{color: 'white', mb:1}} size={30} />
                    <Typography variant="caption" color="white">Σύνδεση με {remoteId}...</Typography>
                </Box>
            )}
            {/* Render video element once connection attempt starts or succeeds, hide if not connected */}
            <video 
                ref={remoteVideoRef} 
                autoPlay 
                playsInline 
                style={{ 
                    width: '100%', 
                    borderRadius: 8, 
                    backgroundColor: '#333',
                    display: isConnected ? 'block' : 'none' // Show only when connected
                }} 
            />
             {!isConnected && !isConnecting && ( // Fallback if not connecting and not connected (e.g. initial state before connection attempt)
                 <Box sx={{ width: '100%', aspectRatio: '16/9', borderRadius: 8, backgroundColor: '#444', alignItems: 'center', justifyContent: 'center', display: !isConnected ? 'flex' : 'none' }}>
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
          onClick={onEndCallRef.current} // Use the ref for the callback
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