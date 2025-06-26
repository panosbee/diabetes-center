import logging
import datetime # <--- Η ΠΡΟΣΘΗΚΗ ΕΙΝΑΙ ΕΔΩ
from flask import request, session
from flask_socketio import emit, join_room, leave_room, disconnect, rooms
from flask_jwt_extended import decode_token 
from bson.objectid import ObjectId
from bson.errors import InvalidId
from utils.db import get_db 

logger = logging.getLogger(__name__)

online_users = {} 

def get_user_id_from_sid(sid):
    for user_id, info in online_users.items():
        if info.get("sid") == sid:
            return user_id
    return None

def get_sid_from_user_id(user_id):
    user_info = online_users.get(user_id)
    return user_info.get("sid") if user_info else None

def register_socketio_handlers(socketio):
    db = get_db() 

    @socketio.on('connect')
    def handle_connect():
        sid = request.sid
        logger.info(f"SocketIO connection attempt from SID: {sid}")
        auth_token = request.args.get('token') 

        if not auth_token:
            logger.warning(f"SocketIO connection rejected for {sid}: No token provided.")
            emit('connect_error', {'message': 'Authentication token missing.'}, to=sid) 
            disconnect(sid=sid) 
            return False 

        try:
            decoded_token = decode_token(auth_token)
            user_identity = decoded_token['sub']
            user_object_id = ObjectId(user_identity) 
            
            user_role = None
            user_doc = db.doctors.find_one({"_id": user_object_id}, {"_id": 1})
            if user_doc:
                user_role = "doctor"
            else:
                user_doc = db.patients.find_one({"_id": user_object_id}, {"_id": 1})
                if user_doc:
                    user_role = "patient"

            if not user_role:
                logger.warning(f"SocketIO connection rejected for {sid}: Invalid user identity '{user_identity}' not found in DB.")
                emit('connect_error', {'message': 'Invalid user identity.'}, to=sid)
                disconnect(sid=sid)
                return False

            if user_identity in online_users:
                old_sid = online_users[user_identity].get('sid')
                logger.warning(f"User {user_identity} reconnected with new SID {sid}. Disconnecting old SID {old_sid}.")
                socketio.emit('force_disconnect', {'message': 'Connected from a new location.'}, to=old_sid)
                socketio.disconnect(old_sid, silent=True)

            online_users[user_identity] = {"sid": sid, "status": "online", "role": user_role, "current_room": None}
            session['user_identity'] = user_identity 
            session['user_role'] = user_role       

            logger.info(f'Client connected: {sid}, User: {user_identity}, Role: {user_role}. Total online: {len(online_users)}')
            emit('connection_success', {'message': 'Connected successfully!', 'userId': user_identity}, to=sid)
            
        except InvalidId:
             logger.warning(f"SocketIO connection rejected for {sid}: Invalid user ID format in token.")
             emit('connect_error', {'message': 'Invalid token format.'}, to=sid)
             disconnect(sid=sid)
             return False
        except Exception as e: 
             logger.warning(f"SocketIO connection rejected for {sid}: Invalid token or other error ({type(e).__name__}: {e})")
             emit('connect_error', {'message': f'Authentication failed: {type(e).__name__}'}, to=sid)
             disconnect(sid=sid)
             return False

    @socketio.on('disconnect')
    def handle_disconnect():
        sid = request.sid
        user_identity = get_user_id_from_sid(sid) 
        
        if user_identity and user_identity in online_users:
            current_room = online_users[user_identity].get('current_room')
            if current_room:
                 logger.info(f"User {user_identity} disconnected while in room {current_room}.")
                 emit('call_ended', {'ender_identity': user_identity, 'reason': 'disconnect'}, to=current_room, include_self=False)
                 room_clients_sids = socketio.server.manager.rooms.get('/', {}).get(current_room, set())
                 for client_sid in room_clients_sids:
                     if client_sid != sid:
                         other_user_id = get_user_id_from_sid(client_sid)
                         if other_user_id and other_user_id in online_users:
                             online_users[other_user_id]['status'] = 'online'
                             online_users[other_user_id].pop('current_room', None)
                         leave_room(current_room, sid=client_sid)

            del online_users[user_identity]
            logger.info(f'Client disconnected: {sid}, User: {user_identity}. Total online: {len(online_users)}')
        else:
            logger.info(f'Client disconnected: {sid} (User identity not found in online list or already removed)')

    @socketio.on('join_room')
    def handle_join_room(data):
        room = data.get('room')
        user_sid = request.sid
        user_identity = session.get('user_identity') 
        user_role = session.get('user_role')

        if not user_identity or not user_role:
            logger.warning(f"Rejecting join_room for {user_sid}: User not authenticated properly (no identity/role in session).")
            emit('call_error', {'message': 'Authentication missing.'}, to=user_sid)
            return
        
        if not room or not room.startswith('call_'):
             logger.warning(f"Rejecting join_room for {user_sid}: Invalid or missing room name '{room}'.")
             emit('call_error', {'message': 'Invalid room name for call.'}, to=user_sid)
             return

        is_authorized = False
        try:
            parts = room.split('_')
            if len(parts) >= 3: 
                room_user1_id = parts[1] 
                room_user2_id = parts[2] 
                
                if user_identity == room_user1_id or user_identity == room_user2_id:
                    user_status = online_users.get(user_identity, {}).get('status')
                    if user_status in ['online', 'in_call']: 
                        is_authorized = True
                    else:
                         logger.warning(f"User {user_identity} tried to join room {room} with invalid status: {user_status}")
                else:
                     logger.warning(f"User {user_identity} is not part of room {room} ({room_user1_id}, {room_user2_id}).")
            else:
                 logger.warning(f"Invalid room name format for authorization check: {room}")
        except Exception as e:
            logger.error(f"Error parsing room name '{room}' for authorization: {e}")

        if is_authorized:
            join_room(room)
            if online_users.get(user_identity, {}).get('status') != 'in_call':
                online_users[user_identity]['status'] = 'in_call' 
                online_users[user_identity]['current_room'] = room 
                logger.info(f"User {user_identity} status set to 'in_call' for room {room}.")
            
            logger.info(f'Client {user_sid} (User: {user_identity}) joined room: {room}')
            emit('peer_joined', {'sid': user_sid, 'userIdentity': user_identity, 'role': user_role}, to=room, include_self=False)
        else:
            logger.warning(f"Rejecting join_room for {user_sid} (User: {user_identity}) to room {room}: Not authorized or invalid state.")
            emit('call_error', {'message': f'Not authorized to join room {room}.'}, to=user_sid)

    @socketio.on('leave_room')
    def handle_leave_room(data):
        room = data.get('room')
        user_identity = session.get('user_identity')
        user_sid = request.sid

        if not user_identity or not room:
            logger.warning(f"Ignoring leave_room from {user_sid}: Missing identity or room.")
            return
            
        logger.info(f'Client {user_sid} (User: {user_identity}) attempting to leave room: {room}')
        leave_room(room) 
        
        if user_identity in online_users:
            if online_users[user_identity].get('current_room') == room:
                 online_users[user_identity]['status'] = 'online'
                 online_users[user_identity].pop('current_room', None) 
                 logger.info(f"User {user_identity} status set to 'online' after leaving room {room}.")
            else:
                logger.info(f"User {user_identity} left room {room}, but was not marked as being in it (current_room was {online_users[user_identity].get('current_room')}).")
        else:
            logger.warning(f"User {user_identity} (SID: {user_sid}) left room {room}, but was not found in online_users list.")
            
        emit('peer_left', {'sid': user_sid, 'userIdentity': user_identity}, to=room, include_self=False)

    @socketio.on('signal')
    def handle_signal(data):
        room = data.get('room')
        signal_type = data.get('type') 
        payload = data.get('payload') 
        sender_identity = session.get('user_identity')
        sender_sid = request.sid
        receiver_identity = data.get('receiver_identity')  # Get receiver_identity from incoming data

        if not sender_identity:
             logger.warning(f"Received signal from unauthenticated SID {sender_sid}.")
             return
        if not room or not payload:
            logger.warning(f"Received signal from {sender_identity} ({sender_sid}) with missing room or payload.")
            return

        room_clients_sids = socketio.server.manager.rooms.get('/', {}).get(room, set())
        target_sid = None
        for sid_in_room in room_clients_sids: # Renamed sid to sid_in_room to avoid conflict
            if sid_in_room != sender_sid:
                target_sid = sid_in_room
                break 
                
        if target_sid:
            logger.info(f"Relaying signal '{signal_type}' from {sender_identity} ({sender_sid}) to target SID {target_sid} in room {room}, receiver_identity: {receiver_identity}")
            emit('signal', {
                'type': signal_type, 
                'payload': payload, 
                'sender_sid': sender_sid, 
                'sender_identity': sender_identity,
                'receiver_identity': receiver_identity  # Forward receiver_identity in the signal
            }, to=target_sid)
        else:
             logger.warning(f"Could not find target peer in room {room} for signal from {sender_identity} ({sender_sid}).")

    # --- Call Flow Handlers ---

    @socketio.on('initiate_call')
    def handle_initiate_call(data):
        caller_identity = session.get('user_identity')
        caller_sid = request.sid
        caller_role = session.get('user_role')
        target_identity = data.get('target_user_identity') 

        if not caller_identity or not target_identity or caller_role != 'doctor':
            logger.warning(f"Invalid initiate_call from {caller_sid}: Missing data or invalid role.")
            emit('call_initiation_failed', {'error': 'Invalid request or unauthorized.'}, to=caller_sid)
            return

        logger.info(f"Doctor {caller_identity} ({caller_sid}) initiating call to patient {target_identity}")

        target_user_info = online_users.get(target_identity)
        if target_user_info and target_user_info['status'] == 'online' and target_user_info['role'] == 'patient':
            target_sid = target_user_info['sid']
            
            user_ids = sorted([caller_identity, target_identity])
            # ΧΡΗΣΗ ΤΟΥ ΔΙΟΡΘΩΜΕΝΟΥ DATETIME IMPORT
            timestamp_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000) 
            room_name = f"call_{user_ids[0]}_{user_ids[1]}_{timestamp_ms}" 

            doctor_name = "Γιατρός"
            try: # Προσθήκη try-except για το ObjectId
                caller_doc = db.doctors.find_one({"_id": ObjectId(caller_identity)}, {"personal_details.last_name": 1})
                if caller_doc: doctor_name = f"Dr. {caller_doc.get('personal_details', {}).get('last_name', '?')}"
            except InvalidId:
                 logger.error(f"Invalid ObjectId format for caller_identity: {caller_identity}")
                 doctor_name = "Γιατρός (Άγνωστο ID)" # Fallback
            except Exception as db_err:
                 logger.error(f"Database error fetching doctor name for {caller_identity}: {db_err}")
                 doctor_name = "Γιατρός (Σφάλμα Βάσης)" # Fallback
            
            logger.info(f"Target patient {target_identity} is online at SID {target_sid}. Sending incoming_call...")
            emit('incoming_call', { 
                'caller_identity': caller_identity, 
                'caller_sid': caller_sid,          
                'caller_name': doctor_name,        
                'suggested_room': room_name         
            }, to=target_sid)
            # Ενημέρωση κατάστασης του γιατρού σε 'dialing' (προαιρετικό αλλά χρήσιμο)
            if caller_identity in online_users:
                online_users[caller_identity]['status'] = 'dialing' 
                online_users[caller_identity]['current_room'] = room_name # Αποθήκευση προτεινόμενου δωματίου
                logger.info(f"Doctor {caller_identity} status set to 'dialing' for room {room_name}.")

        else:
            status = target_user_info.get('status', 'offline') if target_user_info else 'offline'
            logger.warning(f"Target patient {target_identity} is not available (Status: {status}).")
            emit('target_unavailable', {'target_identity': target_identity, 'status': status}, to=caller_sid)

    @socketio.on('accept_call')
    def handle_accept_call(data):
        callee_identity = session.get('user_identity') 
        callee_sid = request.sid
        caller_sid = data.get('caller_sid')        
        caller_identity = data.get('caller_identity') 
        room_name = data.get('room_name')          

        if not all([callee_identity, caller_sid, caller_identity, room_name]):
             logger.warning(f"Accept call failed: Missing data from {callee_sid}.")
             if caller_sid: emit('call_error', {'message': 'Call acceptance failed (missing data).'}, to=caller_sid)
             # Ενημέρωσε και τον καλούμενο ότι απέτυχε
             emit('call_error', {'message': 'Call acceptance failed (missing data).'}, to=callee_sid)
             return
             
        caller_info = online_users.get(caller_identity)
        # Έλεγχος αν ο καλών είναι ακόμα συνδεδεμένος ΚΑΙ περιμένει κλήση (dialing)
        if not caller_info or caller_info.get('sid') != caller_sid or caller_info.get('status') != 'dialing':
             logger.warning(f"Cannot accept call: Caller {caller_identity} (SID: {caller_sid}) is no longer available or not dialing.")
             emit('call_error', {'message': 'Ο καλέσας δεν είναι πλέον διαθέσιμος.'}, to=callee_sid)
             # Ενημέρωση του καλούντα αν είναι ακόμα συνδεδεμένος αλλά όχι dialing
             if caller_info and caller_info.get('sid') == caller_sid:
                  emit('call_error', {'message': 'Η κλήση ακυρώθηκε ή απαντήθηκε ήδη.'}, to=caller_sid)
             return

        logger.info(f"Patient {callee_identity} ({callee_sid}) accepted call from doctor {caller_identity} ({caller_sid}) for room {room_name}")

        # --- BEGIN MODIFICATION ---
        # Update caller's (doctor's) status to 'online' so they can join the room.
        # Their status will be set to 'in_call' by handle_join_room when they actually join.
        if caller_identity in online_users:
            online_users[caller_identity]['status'] = 'online'
            # 'current_room' for the caller was already set to room_name during 'initiate_call'
            # and should remain as is, as it's the room they are intended to join.
            logger.info(f"Caller {caller_identity} (Doctor) status updated to 'online' in preparation for joining room {room_name}.")
        else:
            # This case should ideally not happen if the preceding checks for caller_info passed.
            # If it does, it indicates a critical inconsistency.
            logger.error(f"CRITICAL: Caller {caller_identity} was not found in online_users during call acceptance processing, despite earlier checks. This may prevent the call from proceeding correctly.")
            emit('call_error', {'message': 'Internal server error: Your session data seems inconsistent. Please try again.'}, to=callee_sid) # For patient
            if caller_sid: # Check if caller_sid is valid before emitting
                 # It's important to ensure caller_sid is still valid and refers to an active connection.
                 # The previous checks (caller_info.get('sid') == caller_sid) should ensure this.
                emit('call_error', {'message': 'Internal server error: Your call session data is inconsistent. Please try initiating the call again.'}, to=caller_sid) # For doctor
            return # Prevent further processing if this critical error occurs.
        # --- END MODIFICATION ---

        # Ενημέρωση του γιατρού (καλούντα)
        emit('call_accepted', { 
            'callee_identity': callee_identity, 
            'callee_sid': callee_sid,           
            'room_name': room_name              
        }, to=caller_sid)
        
        # Ο ασθενής (callee) μπαίνει στο δωμάτιο
        handle_join_room({'room': room_name}) 

    @socketio.on('reject_call')
    def handle_reject_call(data):
        callee_identity = session.get('user_identity', 'Unknown')
        callee_sid = request.sid
        caller_sid = data.get('caller_sid') 
        caller_identity = data.get('caller_identity') 

        if not caller_sid or not caller_identity:
            logger.warning(f"Reject call from {callee_sid}: Missing caller info.")
            return

        logger.info(f"Patient {callee_identity} ({callee_sid}) rejected call from doctor {caller_identity} ({caller_sid})")
        # Ενημέρωση του γιατρού (καλούντα)
        emit('call_rejected', {'callee_identity': callee_identity}, to=caller_sid)
        # Ο καλών θα πρέπει να αλλάξει το status του από dialing σε online όταν λάβει αυτό

    @socketio.on('end_call')
    def handle_end_call(data):
        ender_identity = session.get('user_identity')
        ender_sid = request.sid
        room = data.get('room') 
        
        if not ender_identity or not room:
            logger.warning(f"Ignoring end_call from {ender_sid}: Missing identity or room.")
            return

        logger.info(f"User {ender_identity} ({ender_sid}) requested to end call in room {room}")
        
        emit('call_ended', {'ender_identity': ender_identity, 'reason': 'hangup'}, to=room) # Include self as well
        
        # Κάνουμε leave όλους από το δωμάτιο και αλλάζουμε το status τους
        room_clients_sids = socketio.server.manager.rooms.get('/', {}).get(room, set())
        logger.info(f"Clients in room {room} to process for call end: {room_clients_sids}")
        for client_sid in list(room_clients_sids): 
            client_user_id = get_user_id_from_sid(client_sid)
            logger.info(f"Processing SID {client_sid} (User ID: {client_user_id}) for leaving room {room}")
            
            leave_room(room, sid=client_sid) 
            
            if client_user_id and client_user_id in online_users:
                online_users[client_user_id]['status'] = 'online'
                online_users[client_user_id].pop('current_room', None)
                logger.info(f"User {client_user_id} status set to 'online'.")
            else:
                logger.warning(f"Could not find user identity for SID {client_sid} to update status after call end.")

    # --- ΝΕΟ Event για απασχολημένο χρήστη ---
    @socketio.on('user_busy')
    def handle_user_busy(data):
        """Ενημερώνει τον καλούντα ότι ο καλούμενος είναι απασχολημένος."""
        target_sid = data.get('target_sid') # Ο SID του αρχικού καλούντα
        busy_user_identity = session.get('user_identity') # Ποιος είναι απασχολημένος
        if target_sid:
            logger.info(f"Informing SID {target_sid} that user {busy_user_identity} is busy.")
            emit('target_unavailable', {'target_identity': busy_user_identity, 'status': 'in_call'}, to=target_sid)


    logger.info("SocketIO event handlers registered.")