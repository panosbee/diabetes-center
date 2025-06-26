
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from bson.errors import InvalidId
import datetime
import logging
from utils.db import get_db

# Ρύθμιση logger
logger = logging.getLogger(__name__)

# Δημιουργία blueprint
calendar_bp = Blueprint('calendar', __name__, url_prefix='/api/calendar')

# Η σύνδεση στη βάση δεδομένων
db = get_db()

def format_event_for_fullcalendar(event):
    """Μορφοποιεί ένα event από τη βάση για το FullCalendar."""
    event_id = str(event.get('_id'))
    start_time = event.get('start_time')
    end_time = event.get('end_time')
    
    formatted = {
        "id": event_id,
        "title": event.get('title', 'Untitled Event'),
        "start": start_time.isoformat() if isinstance(start_time, datetime.datetime) else None,
        "end": end_time.isoformat() if isinstance(end_time, datetime.datetime) else None,
        "allDay": event.get('all_day', False),
        "extendedProps": { # Βάζουμε τα υπόλοιπα custom πεδία εδώ
            "event_type": event.get('event_type'),
            "status": event.get('status'),
            "user_id": str(event.get('user_id')) if event.get('user_id') else None,
            "creator_id": str(event.get('creator_id')) if event.get('creator_id') else None,
            "visibility": event.get('visibility'),
            "editable_by": event.get('editable_by'),
            "details": event.get('details'),
            "patient_input": event.get('patient_input'),
            "doctor_comments": event.get('doctor_comments', []),
            "doctor_name": event.get('doctor_name', None),
            "patient_name": event.get('patient_name', None),
            "isSlot": event.get('event_type') == 'appointment_slot'
        }
    }
    
    event_type = event.get('event_type')
    if event_type == 'appointment_slot':
        formatted['color'] = '#cccccc' 
        formatted['display'] = 'block'
    elif event_type == 'booked_appointment':
        formatted['color'] = '#3788d8' 
        
    return formatted

@calendar_bp.route('/events', methods=['GET'])
@jwt_required()
def get_calendar_events():
    user_id_str = get_jwt_identity()
    start_str = request.args.get('start') 
    end_str = request.args.get('end')   
    
    if db is None: return jsonify({"error": "Database connection failed"}), 500
    
    if not start_str or not end_str:
        return jsonify({"error": "Missing start or end query parameters"}), 400
    
    logger.info(f"Received start_str: '{start_str}'")
    logger.info(f"Received end_str: '{end_str}'")
    
    try:
        start_dt = datetime.datetime.fromisoformat(start_str)
        end_dt = datetime.datetime.fromisoformat(end_str)
        start_dt_utc = start_dt.astimezone(datetime.timezone.utc)
        end_dt_utc = end_dt.astimezone(datetime.timezone.utc)
    except ValueError as e:
        logger.error(f"ValueError parsing dates: start='{start_str}', end='{end_str}'. Error: {e}")
        return jsonify({"error": "Invalid start or end date format. Use ISO 8601."}), 400

    logger.info(f"[DEBUG] get_calendar_events: user_id_str={user_id_str}")
    try:
        user_object_id = ObjectId(user_id_str)
    except InvalidId:
        logger.error(f"[DEBUG] Invalid user ID in token: {user_id_str}")
        return jsonify({"error": "Invalid user ID in token"}), 400

    user_role = None
    mongo_query_or_conditions = []
    
    # Get patient_ids from query parameters for filtering
    patient_ids_filter_str = request.args.getlist('patient_ids[]')
    selected_patient_object_ids_filter = []
    if patient_ids_filter_str:
        try:
            selected_patient_object_ids_filter = [ObjectId(pid) for pid in patient_ids_filter_str]
        except InvalidId:
            logger.warning(f"Invalid ObjectId in patient_ids_filter: {patient_ids_filter_str}")
            return jsonify({"error": "Invalid patient ID format in filter"}), 400

    doctor = db.doctors.find_one({"_id": user_object_id}, {"managed_patients": 1, "personal_details.first_name": 1, "personal_details.last_name": 1})
    
    # Get event_types from query parameters for filtering
    event_types_filter = request.args.getlist('event_types[]')
    # Initialize managed_patient_ids and assigned_doctor_ids to prevent unbound errors later
    managed_patient_ids = []
    assigned_doctor_ids = []


    if doctor:
        user_role = 'doctor'
        managed_patient_ids = doctor.get('managed_patients', [])

        base_doctor_conditions = []
        if selected_patient_object_ids_filter: # Patient filter is active
            valid_filter_ids = [pid for pid in selected_patient_object_ids_filter if pid in managed_patient_ids]
            if valid_filter_ids:
                condition = {"user_id": {"$in": valid_filter_ids}}
                if event_types_filter: # Both patient and type filters
                    condition["event_type"] = {"$in": event_types_filter}
                base_doctor_conditions.append(condition)
            # If no valid_filter_ids, patient-specific part of query will be empty.
            # Consider if doctor's own events of selected types should show.
            # For now, if patient filter is active, only events for those patients are shown.

        elif event_types_filter:
            # Only event_type filter is active (no specific patient filter)
            base_doctor_conditions.append({"user_id": user_object_id, "event_type": {"$in": event_types_filter}})
            base_doctor_conditions.append({"creator_id": user_object_id, "event_type": {"$in": event_types_filter}})
            if managed_patient_ids:
                base_doctor_conditions.append({
                    "user_id": {"$in": managed_patient_ids},
                    "visibility": {"$in": ["shared_with_doctor", "public"]},
                    "event_type": {"$in": event_types_filter}
                })
                base_doctor_conditions.append({ # Patient created, shared with doctor
                    "creator_id": {"$in": managed_patient_ids},
                    "visibility": "shared_with_doctor",
                    "event_type": {"$in": event_types_filter}
                })
        else:
            # No filters active for doctor, original broad logic
            base_doctor_conditions.append({"user_id": user_object_id})
            base_doctor_conditions.append({"creator_id": user_object_id})
            if managed_patient_ids:
                base_doctor_conditions.append({
                    "user_id": {"$in": managed_patient_ids},
                    "visibility": {"$in": ["shared_with_doctor", "public"]}
                })
                base_doctor_conditions.append({
                    "creator_id": {"$in": managed_patient_ids},
                    "visibility": "shared_with_doctor"
                })
        
        # Add conditions to the main $or list, ensuring no duplicates
        for cond in base_doctor_conditions:
            if cond not in mongo_query_or_conditions:
                 mongo_query_or_conditions.append(cond)
    else:
        patient_data_for_role_check = db.patients.find_one({"_id": user_object_id}, {"assigned_doctors": 1, "personal_details.first_name": 1, "personal_details.last_name": 1})
        if patient_data_for_role_check:
            user_role = 'patient'
            assigned_doctor_ids = patient_data_for_role_check.get('assigned_doctors', [])
            # Patient logic for mongo_query_or_conditions will be handled after main query construction
        else:
            logger.warning(f"[DEBUG] User ID {user_id_str} not found in doctors or patients.")
            return jsonify({"error": "User not found"}), 404

    # Construct the final query
    mongo_query_main_conditions = {
        "start_time": {"$lt": end_dt_utc},
        "end_time": {"$gt": start_dt_utc}
    }
    
    mongo_query = {} # Initialize mongo_query

    if user_role == 'doctor':
        if not mongo_query_or_conditions:
            return jsonify([]) # Doctor with filters that yield no conditions
        
        unique_or_conditions = []
        for item in mongo_query_or_conditions:
            if item not in unique_or_conditions:
                unique_or_conditions.append(item)
        
        if not unique_or_conditions:
             return jsonify([])

        mongo_query = {
            "$and": [
                mongo_query_main_conditions,
                {"$or": unique_or_conditions}
            ]
        }

    elif user_role == 'patient':
        mongo_query_or_conditions = [] # Reset for patient specific $or clauses
        # assigned_doctor_ids is already defined if user_role is 'patient'
        
        patient_owned_condition = {"user_id": user_object_id}
        if event_types_filter: # Apply event type filter to patient's own events
            patient_owned_condition["event_type"] = {"$in": event_types_filter}
        mongo_query_or_conditions.append(patient_owned_condition)
        
        if assigned_doctor_ids: # Check if list is not empty
            slot_condition = {
                "creator_id": {"$in": assigned_doctor_ids},
                "event_type": "appointment_slot",
                "status": "available",
                "visibility": "shared_with_patient"
            }
            # Only add slots if 'appointment_slot' is in the event_types_filter or if no event_type filter is active
            if not event_types_filter or 'appointment_slot' in event_types_filter:
                 mongo_query_or_conditions.append(slot_condition)

        if not mongo_query_or_conditions: # Patient, but filters (event_type) resulted in no OR conditions
            return jsonify([])
        
        mongo_query = {
            "$and": [
                mongo_query_main_conditions,
                {"$or": mongo_query_or_conditions}
            ]
        }
    else:
        logger.error(f"User role not determined for {user_id_str} before query construction.")
        return jsonify({"error": "User role undetermined"}), 500
    
    # Ensure managed_patient_ids and assigned_doctor_ids are defined for the name fetching part,
    # even if they were empty or not set due to filter paths.
    # This was already handled by initializing them to [] at the start of the function for doctor,
    # and assigned_doctor_ids is fetched if user_role is patient.
    # The Pylance warnings about them being unbound later should be resolved by this structure.
                # Booked appointments by this patient with their assigned doctors (already covered by user_id: patient_object_id if status is booked)
                # but to be explicit for clarity if needed, though the first condition (user_id: patient_object_id) covers patient-owned events
                # including those they booked.
    # Stray else block removed

    # Construct the final query
    mongo_query_main_conditions = {
        "start_time": {"$lt": end_dt_utc},
        "end_time": {"$gt": start_dt_utc}
    }

    if mongo_query_or_conditions:
        # Remove duplicate conditions if any (e.g. if user_id and creator_id are the same for some events)
        # This can be complex; for now, allow potential duplicates in $or, MongoDB handles it.
        # A more robust way would be to build a set of unique query dicts.
        unique_or_conditions = []
        for item in mongo_query_or_conditions:
            if item not in unique_or_conditions:
                unique_or_conditions.append(item)
        
        if unique_or_conditions: # Ensure $or is not empty if we intend to use it
            mongo_query = {
                "$and": [
                    mongo_query_main_conditions,
                    {"$or": unique_or_conditions}
                ]
            }
        else: # Filters resulted in no valid OR conditions for the doctor
            if user_role == 'doctor':
                return jsonify([]) # No events match doctor's specific filter combination
            else: # Patient context, will be handled below
                 mongo_query = mongo_query_main_conditions # Fallback for patient if their OR conditions become empty
    
    elif user_role == 'doctor': # Doctor, but no filters led to any OR conditions (e.g. initial load without filters, but this case is handled by the 'else' in the main if/elif/else block)
        # This path should ideally not be hit if the main if/elif/else for doctor filters is exhaustive.
        # If it is, it means no filters applied, and the original broad fetch for doctor was intended.
        # The original logic for a doctor with no filters is now in the final 'else' of the patient/event_type filter block.
        # If mongo_query_or_conditions is empty here for a doctor, it implies an issue with filter logic not adding default views.
        # For safety, if a doctor has no OR conditions (e.g. due to very specific filters yielding nothing), return empty.
        return jsonify([])
    # If not a doctor and no OR conditions yet, it's a patient; their OR conditions are built below.
    # So, mongo_query would just be mongo_query_main_conditions at this point for a patient.
    # This will be overwritten by patient-specific logic.


    # --- PATIENT LOGIC (ensure event_type filter can apply) ---
    if user_role == 'patient':
        patient = db.patients.find_one({"_id": user_object_id}) # Fetch patient details if not already done
        if not patient: # Should not happen if role was determined
            return jsonify({"error": "Patient not found"}), 404

        mongo_query_or_conditions = [] # Reset for patient
        assigned_doctor_ids = patient.get('assigned_doctors', [])
        
        # Events owned by the patient (e.g., booked appointments, personal notes, reminders set for them)
        patient_owned_condition = {"user_id": user_object_id}
        if event_types_filter:
            patient_owned_condition["event_type"] = {"$in": event_types_filter}
        mongo_query_or_conditions.append(patient_owned_condition)
        
        # Available slots from assigned doctors
        if assigned_doctor_ids:
            slot_condition = {
                "creator_id": {"$in": assigned_doctor_ids},
                "event_type": "appointment_slot",
                "status": "available",
                "visibility": "shared_with_patient"
            }
            # Only add slots if 'appointment_slot' is in the event_types_filter or if no event_type filter is active
            if not event_types_filter or 'appointment_slot' in event_types_filter:
                 mongo_query_or_conditions.append(slot_condition)

        if mongo_query_or_conditions: # If there are conditions for the patient
             mongo_query = {
                "$and": [
                    mongo_query_main_conditions,
                    {"$or": mongo_query_or_conditions}
                ]
            }
        else: # Patient, but filters (event_type) resulted in no OR conditions
            return jsonify([])
    logger.info(f"[DEBUG] {user_role.capitalize()} mongo_query for /events: {mongo_query}")

    try:
        events_cursor = db.calendar_events.find(mongo_query)
        events_list = list(events_cursor)
        logger.info(f"[DEBUG] Events found for /events: {len(events_list)}")
        
        # --- Fetch patient/doctor names for formatting ---
        # For doctor viewing events of their patients
        patient_names_map = {}
        if user_role == 'doctor' and managed_patient_ids:
            patients_data = db.patients.find(
                {"_id": {"$in": managed_patient_ids}},
                {"_id": 1, "personal_details.first_name": 1, "personal_details.last_name": 1}
            )
            for p in patients_data:
                patient_names_map[str(p['_id'])] = f"{p.get('personal_details', {}).get('last_name', '?')} {p.get('personal_details', {}).get('first_name', '?')}"

        # For patient viewing slots from their doctors
        doctor_names_map = {}
        if user_role == 'patient' and assigned_doctor_ids:
            doctors_data = db.doctors.find(
                {"_id": {"$in": assigned_doctor_ids}},
                {"_id": 1, "personal_details.first_name": 1, "personal_details.last_name": 1}
            )
            for d in doctors_data:
                doctor_names_map[str(d['_id'])] = f"Dr. {d.get('personal_details', {}).get('last_name', '?')}"
        # --- End fetching names ---
        
        formatted_events = []
        for event in events_list:
            formatted = format_event_for_fullcalendar(event)
            # Add patient name if doctor is viewing patient's event
            if user_role == 'doctor':
                event_user_id_str = formatted['extendedProps'].get('user_id')
                if event_user_id_str != user_id_str and event_user_id_str in patient_names_map:
                    formatted['extendedProps']['patient_name'] = patient_names_map[event_user_id_str]
            # Add doctor name to slots/booked appointments for patient
            elif user_role == 'patient':
                creator_id_str = formatted['extendedProps'].get('creator_id')
                if formatted['extendedProps'].get('event_type') == 'appointment_slot' and creator_id_str in doctor_names_map:
                    formatted['extendedProps']['doctor_name'] = doctor_names_map[creator_id_str]
                    # Update title for available slots for patient
                    if formatted['extendedProps'].get('status') == 'available':
                         formatted['title'] = f"Διαθέσιμο με {doctor_names_map[creator_id_str]}"
                elif formatted['extendedProps'].get('event_type') == 'booked_appointment' and creator_id_str in doctor_names_map:
                    # For booked appointments, creator_id is the doctor who created the slot.
                    # user_id is the patient who booked.
                    formatted['extendedProps']['doctor_name'] = doctor_names_map[creator_id_str]


            formatted_events.append(formatted)

        if user_role == 'patient':
            slot_events = [e for e in formatted_events if e['extendedProps'].get('event_type') == 'appointment_slot' and e['extendedProps'].get('status') == 'available']
            if slot_events:
                logger.info(f"Returning {len(slot_events)} available appointment slots to patient {user_id_str}")
            else:
                logger.warning(f"No available appointment slots found for patient {user_id_str} in the given time range.")
        
        return jsonify(formatted_events)
        
    except Exception as db_err:
        logger.error(f"Database error fetching calendar events: {db_err}")
        return jsonify({"error": "Error fetching calendar events"}), 500
    

@calendar_bp.route('/events', methods=['POST'])
@jwt_required()
def create_calendar_event():
    creator_id_str = get_jwt_identity()
    data = request.get_json()
    
    if db is None: return jsonify({"error": "Database connection failed"}), 500
    if not data: return jsonify({"error": "Request body must be JSON"}), 400

    try:
        creator_object_id = ObjectId(creator_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid creator ID in token"}), 400

    event_type = data.get('event_type')
    title = data.get('title')
    start_str = data.get('start') 
    end_str = data.get('end')     
    all_day = data.get('allDay', False)
    client_details = data.get('details', {})

    if not event_type or not start_str or (not title and event_type not in ['medication_reminder', 'measurement_reminder', 'appointment_slot']):
         return jsonify({"error": "Missing required fields: event_type, start, and sometimes title"}), 400
        
    try:
        start_dt = datetime.datetime.fromisoformat(start_str)
        end_dt = datetime.datetime.fromisoformat(end_str) if end_str else start_dt
        start_dt_utc = start_dt.astimezone(datetime.timezone.utc)
        end_dt_utc = end_dt.astimezone(datetime.timezone.utc)
        if end_dt_utc < start_dt_utc:
            return jsonify({"error": "End time cannot be before start time"}), 400
    except ValueError:
        return jsonify({"error": "Invalid start or end date format. Use ISO 8601."}), 400
        
    target_user_id = None 
    user_id_for_event_str = data.get('user_id', creator_id_str) 

    if user_id_for_event_str == creator_id_str:
        target_user_id = creator_object_id
    else:
        try:
            target_user_id = ObjectId(user_id_for_event_str)
            creator_doctor = db.doctors.find_one({"_id": creator_object_id}, {"managed_patients": 1})
            if not creator_doctor:
                return jsonify({"error": "Only doctors can create events for other users (patients)"}), 403
            target_patient = db.patients.find_one({"_id": target_user_id}, {"_id": 1})
            if not target_patient:
                 return jsonify({"error": "Target user is not a patient"}), 400
            managed_patients = creator_doctor.get('managed_patients', [])
            if target_user_id not in managed_patients:
                 logger.warning(f"Doctor {creator_id_str} attempted to create event for unmanaged patient {user_id_for_event_str}")
                 return jsonify({"error": f"Unauthorized to create events for patient {user_id_for_event_str}"}), 403
        except InvalidId:
            return jsonify({"error": "Invalid user_id provided for the event target"}), 400
        except Exception as auth_err:
             logger.error(f"Error during authorization check for event creation: {auth_err}")
             return jsonify({"error": "Authorization check failed"}), 500

    final_user_id = creator_object_id 
    visibility = 'private' 
    editable_by = 'owner'  
    status = 'active' 

    is_creator_doctor = db.doctors.count_documents({"_id": creator_object_id}) > 0

    if target_user_id != creator_object_id: 
        final_user_id = target_user_id 
        if event_type in ['medication_reminder', 'measurement_reminder', 'doctor_instruction', 'booked_appointment']:
            visibility = 'shared_with_doctor' 
            editable_by = 'doctor' 
            if event_type == 'booked_appointment': status = 'booked'
        elif event_type == 'appointment_slot':
            # Appointment slot για συγκεκριμένο ασθενή
            visibility = 'shared_with_patient' 
            editable_by = 'doctor'
            status = 'available'
            if not title: title = "Διαθέσιμο Ραντεβού"
        else:
            visibility = 'shared_with_doctor' 
            editable_by = 'doctor'           
    else:
        if is_creator_doctor:
            if event_type == 'appointment_slot': 
                visibility = 'shared_with_patient'
                editable_by = 'doctor'
                status = 'available'
                if not title: title = "Διαθέσιμο Ραντεβού" 
            elif event_type == 'personal_task':
                 visibility = 'private'
                 editable_by = 'owner'
            else: 
                 visibility = 'private'
                 editable_by = 'owner'
        else:
            if event_type in ['meal_log', 'exercise_log', 'symptom_log', 'patient_note']:
                visibility = 'shared_with_doctor' 
                editable_by = 'owner' 
            else: 
                 visibility = 'shared_with_doctor' 
                 editable_by = 'owner'
    
    event_details = {}
    if event_type == 'medication_reminder':
        event_details['medication_name'] = client_details.get('med_name') or data.get('med_name')
        event_details['dosage'] = client_details.get('med_dosage') or data.get('med_dosage')
        event_details['frequency'] = client_details.get('med_freq') or data.get('med_freq')
        if not event_details['medication_name']: 
            return jsonify({"error": "Missing medication name for reminder"}), 400
        if not title: title = f"Υπενθύμιση: {event_details['medication_name']}"
    elif event_type == 'measurement_reminder':
        event_details['measurement_type'] = client_details.get('meas_type') or data.get('meas_type', 'blood_glucose')
        event_details['target_value'] = client_details.get('meas_target') or data.get('meas_target')
        if not title: title = f"Υπενθύμιση Μέτρησης: {event_details['measurement_type']}"
    elif event_type in ['meal_log', 'exercise_log', 'symptom_log', 'patient_note']:
        event_details['notes'] = client_details.get('notes', '')

    now = datetime.datetime.now(datetime.timezone.utc)
    new_event_doc = {
        "user_id": final_user_id, 
        "creator_id": creator_object_id, 
        "event_type": event_type, "visibility": visibility, "editable_by": editable_by,
        "title": title, "start_time": start_dt_utc, "end_time": end_dt_utc,
        "all_day": all_day, "status": status, "details": event_details, 
        "patient_input": None, "doctor_comments": [],
        "created_at": now, "updated_at": now
    }
    
    logger.info(f"Attempting to insert new event: {new_event_doc}")

    try:
        result = db.calendar_events.insert_one(new_event_doc)
        inserted_id = result.inserted_id
        logger.info(f"Created calendar event {inserted_id} (type: {event_type}, user_id: {final_user_id}, creator_id: {creator_object_id}, visibility: {visibility}, status: {status}) by user {creator_id_str}")
        created_event = db.calendar_events.find_one({"_id": inserted_id})
        if created_event:
            return jsonify(format_event_for_fullcalendar(created_event)), 201
        else:
            logger.error(f"Failed to retrieve newly created event with id {inserted_id}")
            return jsonify({"message": "Event created but failed to retrieve it", "id": str(inserted_id)}), 201
    except Exception as db_err:
        logger.error(f"Database error creating calendar event: {db_err}")
        logger.error(f"Failed event document was: {new_event_doc}") 
        return jsonify({"error": "Error creating calendar event"}), 500

@calendar_bp.route('/events/<string:event_id>', methods=['PATCH'])
@jwt_required()
def update_calendar_event(event_id):
    user_id_str = get_jwt_identity()
    data = request.get_json()
    
    if db is None: return jsonify({"error": "Database connection failed"}), 500
    if not data: return jsonify({"error": "Request body cannot be empty for update"}), 400
    
    try:
        event_object_id = ObjectId(event_id)
        user_object_id = ObjectId(user_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400
        
    try:
        event_to_update = db.calendar_events.find_one({"_id": event_object_id})
        if not event_to_update:
            return jsonify({"error": "Event not found"}), 404
            
        requesting_user_doc = db.doctors.find_one({"_id": user_object_id}, {"role": 1}) 
        is_admin = requesting_user_doc and requesting_user_doc.get('role') == 'admin'
        
        editable_by_policy = event_to_update.get('editable_by', 'owner')
        owner_id = event_to_update.get('user_id')
        creator_id = event_to_update.get('creator_id')
        is_owner = owner_id == user_object_id 
        is_creator = creator_id == user_object_id

        can_edit = False
        if is_admin:
            can_edit = True
        else:
            is_requesting_user_doctor = bool(requesting_user_doc) 
            if editable_by_policy == 'owner' and is_owner:
                can_edit = True
            elif editable_by_policy == 'doctor':
                if is_requesting_user_doctor:
                     if is_creator or is_owner: 
                         can_edit = True
                     else:
                         if db.patients.count_documents({"_id": owner_id}) > 0: # Check if owner is a patient
                            owner_patient = db.patients.find_one({"_id": owner_id}, {"assigned_doctors": 1})
                            if owner_patient and user_object_id in owner_patient.get('assigned_doctors', []):
                                can_edit = True
            elif editable_by_policy == 'both': 
                if is_owner:
                    can_edit = True
                elif is_requesting_user_doctor:
                     if db.patients.count_documents({"_id": owner_id}) > 0:
                        owner_patient = db.patients.find_one({"_id": owner_id}, {"assigned_doctors": 1})
                        if owner_patient and user_object_id in owner_patient.get('assigned_doctors', []):
                            can_edit = True
                         
        if not can_edit:
            logger.warning(f"User {user_id_str} unauthorized to edit event {event_id} (editable_by: {editable_by_policy}, owner: {owner_id}, creator: {creator_id})")
            return jsonify({"error": "Unauthorized to edit this event"}), 403
        
        update_fields = {}
        allowed_fields_to_update = ['title', 'start_time', 'end_time', 'all_day', 'status', 'details', 'patient_input'] 
        
        for field in allowed_fields_to_update:
            if field in data:
                 if field in ['start_time', 'end_time']:
                     try:
                         dt_str = data[field]
                         if isinstance(dt_str, str):
                            dt = datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00')) # Ensure Z is handled
                            update_fields[field] = dt.astimezone(datetime.timezone.utc)
                         elif isinstance(dt_str, dict) and 'dateTime' in dt_str : 
                             dt = datetime.datetime.fromisoformat(dt_str['dateTime'].replace('Z', '+00:00'))
                             update_fields[field] = dt.astimezone(datetime.timezone.utc)
                         else:
                             logger.warning(f"Skipping date update for field '{field}' due to unexpected format: {dt_str}")
                     except Exception as date_err:
                          logger.error(f"Error parsing date for field '{field}': {data[field]}, Error: {date_err}")
                          return jsonify({"error": f"Invalid date format for {field}. Use ISO 8601."}), 400
                 else:
                    update_fields[field] = data[field]

        update_payload = {}
        if update_fields:
            update_payload["$set"] = update_fields

        if 'add_doctor_comment' in data and isinstance(data['add_doctor_comment'], dict) and 'comment' in data['add_doctor_comment']:
            doctor_check = db.doctors.find_one({"_id": user_object_id}) 
            if doctor_check:
                new_comment = {
                    "_id": ObjectId(), "doctor_id": user_object_id,
                    "comment": data['add_doctor_comment']['comment'],
                    "timestamp": datetime.datetime.now(datetime.timezone.utc)
                }
                update_payload.setdefault("$push", {})["doctor_comments"] = new_comment
            else:
                logger.warning(f"Non-doctor user {user_id_str} attempted to add a doctor comment.")

        if not update_payload: 
             return jsonify({"message": "No valid fields provided for update or no changes detected"}), 400
             
        update_payload["$currentDate"] = { "updated_at": True }
        logger.info(f"Updating event {event_id} with payload: {update_payload}")

        result = db.calendar_events.update_one({"_id": event_object_id}, update_payload)

        if result.modified_count >= 1:
            logger.info(f"Successfully updated calendar event {event_id} by user {user_id_str}. Modified: {result.modified_count}")
            updated_event = db.calendar_events.find_one({"_id": event_object_id})
            if updated_event: return jsonify(format_event_for_fullcalendar(updated_event)), 200
            else:
                 logger.error(f"Failed to retrieve event {event_id} after update, though modification was reported.")
                 return jsonify({"message": "Event updated but failed to retrieve"}), 200
        elif result.matched_count >= 1 and not update_fields and "$push" in update_payload: 
            logger.info(f"Event {event_id} matched. Only comments pushed. Matched: {result.matched_count}")
            updated_event = db.calendar_events.find_one({"_id": event_object_id})
            if updated_event: return jsonify(format_event_for_fullcalendar(updated_event)), 200
            return jsonify({"message": "Event found but no standard fields modified, only comments pushed"}), 200
        elif result.matched_count == 0:
             logger.error(f"Failed to find event {event_id} during update operation (matched_count=0).")
             return jsonify({"error": "Event not found during update"}), 404
        else: 
             logger.info(f"Event {event_id} found, but data sent resulted in no modification. Matched: {result.matched_count}, Modified: {result.modified_count}")
             return jsonify({"message": "Event data submitted did not result in any changes"}), 200
             
    except Exception as e:
        logger.error(f"Error updating calendar event {event_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@calendar_bp.route('/events/<string:event_id>', methods=['DELETE'])
@jwt_required()
def delete_calendar_event(event_id):
    user_id_str = get_jwt_identity()
    if db is None: return jsonify({"error": "Database connection failed"}), 500
    try:
        event_object_id = ObjectId(event_id)
        user_object_id = ObjectId(user_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid ID format"}), 400

    try:
        event_to_delete = db.calendar_events.find_one({"_id": event_object_id})
        if not event_to_delete:
            return jsonify({"error": "Event not found"}), 404
        
        is_creator = event_to_delete.get('creator_id') == user_object_id
        # Add admin check if needed:
        # admin_check = db.doctors.find_one({"_id": user_object_id, "role": "admin"})
        # is_admin = bool(admin_check)
        # if not is_creator and not is_admin:
        if not is_creator:
             logger.warning(f"User {user_id_str} (not creator {event_to_delete.get('creator_id')}) attempted to delete event {event_id}")
             return jsonify({"error": "Unauthorized to delete this event"}), 403

        result = db.calendar_events.delete_one({"_id": event_object_id})
        if result.deleted_count == 1:
            logger.info(f"Deleted calendar event {event_id} by user {user_id_str}")
            return jsonify({"message": "Event deleted successfully"}), 200 
        else:
            logger.error(f"Failed to delete event {event_id} (deleted_count: {result.deleted_count}) even though it was found initially.")
            return jsonify({"error": "Failed to delete event after finding it"}), 500
    except Exception as e:
        logger.error(f"Error deleting calendar event {event_id}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@calendar_bp.route('/events/<string:event_id>/book', methods=['POST'])
@jwt_required()
def book_appointment_slot(event_id):
    patient_id_str = get_jwt_identity() 
    if db is None: return jsonify({"error": "Database connection failed"}), 500
    try:
        event_object_id = ObjectId(event_id)
        patient_object_id = ObjectId(patient_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid ID format for event or patient"}), 400
        
    try:
        patient = db.patients.find_one({"_id": patient_object_id}, {"assigned_doctors": 1, "personal_details.first_name": 1, "personal_details.last_name": 1})
        if not patient:
            return jsonify({"error": "Unauthorized: Only patients can book appointments."}), 403
            
        slot_event = db.calendar_events.find_one({"_id": event_object_id})
        if not slot_event:
            return jsonify({"error": "Appointment slot not found."}), 404
            
        if slot_event.get('event_type') != 'appointment_slot' or slot_event.get('status') != 'available':
             return jsonify({"error": "This slot is not available for booking."}), 409 
             
        creator_doctor_id = slot_event.get('creator_id')
        assigned_doctors = patient.get('assigned_doctors', [])
        if not creator_doctor_id or creator_doctor_id not in assigned_doctors:
            logger.warning(f"Patient {patient_id_str} tried to book slot {event_id} from unassigned doctor {creator_doctor_id}")
            return jsonify({"error": "Cannot book appointment with this doctor."}), 403
            
        now = datetime.datetime.now(datetime.timezone.utc)
        update_payload = {
            "$set": {
                "event_type": "booked_appointment", "status": "booked",
                "user_id": patient_object_id, "visibility": "shared_with_doctor", 
                "editable_by": "doctor", 
            },
            "$currentDate": { "updated_at": True }
        }
        
        query_for_update = {"_id": event_object_id, "event_type": "appointment_slot", "status": "available"}
        result = db.calendar_events.update_one(query_for_update, update_payload)
        
        if result.modified_count == 1:
            logger.info(f"Patient {patient_id_str} successfully booked slot {event_id}")
            booked_event = db.calendar_events.find_one({"_id": event_object_id})
            if booked_event:
                 formatted_booked_event = format_event_for_fullcalendar(booked_event)
                 doctor_doc = db.doctors.find_one({"_id": creator_doctor_id}, {"personal_details.last_name": 1, "personal_details.first_name": 1})
                 if doctor_doc:
                     formatted_booked_event['extendedProps']['doctor_name'] = f"Dr. {doctor_doc.get('personal_details', {}).get('last_name', '?')}"
                 
                 patient_full_name = f"{patient.get('personal_details',{}).get('first_name','')} {patient.get('personal_details',{}).get('last_name','')}".strip()
                 formatted_booked_event['extendedProps']['patient_name'] = patient_full_name
                 # Potentially update title of the booked event for clarity
                 if doctor_doc:
                     formatted_booked_event['title'] = f"Ραντεβού: {patient_full_name} / Dr. {doctor_doc.get('personal_details', {}).get('last_name', '?')}"
                 else:
                     formatted_booked_event['title'] = f"Ραντεβού: {patient_full_name}"

                 return jsonify(formatted_booked_event), 200
            else:
                 logger.error(f"Failed to retrieve event {event_id} after booking.")
                 return jsonify({"message": "Appointment booked successfully but failed to retrieve updated data."}), 200 
        elif result.matched_count == 0 : 
            logger.warning(f"Failed to book slot {event_id} for patient {patient_id_str}. Slot might have been booked or changed. Matched: {result.matched_count}, Modified: {result.modified_count}")
            current_slot_state = db.calendar_events.find_one({"_id": event_object_id})
            if current_slot_state and (current_slot_state.get('status') != 'available' or current_slot_state.get('event_type') != 'appointment_slot'):
                return jsonify({"error": "Failed to book the appointment slot. It is no longer available."}), 409
            else: 
                return jsonify({"error": "Failed to book the appointment slot. Please try again."}), 409
    except Exception as e:
        logger.error(f"Error booking appointment slot {event_id}: {e}")
        return jsonify({"error": "An internal server error occurred during booking."}), 500


# --- NEW ENDPOINTS FOR SIDEBAR ---

@calendar_bp.route('/upcoming_booked_appointments', methods=['GET'])
@jwt_required()
def get_upcoming_booked_appointments():
    """Επιστρέφει τα επερχόμενα κλεισμένα ραντεβού για τον γιατρό."""
    user_id_str = get_jwt_identity()
    limit = request.args.get('limit', default=5, type=int)
    days_ahead = request.args.get('days_ahead', default=30, type=int)

    if db is None: return jsonify({"error": "Database connection failed"}), 500
    try:
        doctor_object_id = ObjectId(user_id_str)
    except InvalidId:
        return jsonify({"error": "Invalid user ID in token (not ObjectId)"}), 400

    doctor_doc = db.doctors.find_one({"_id": doctor_object_id}, {"managed_patients": 1})
    if not doctor_doc:
        return jsonify({"error": "User is not a doctor or not found"}), 403

    managed_patient_ids = doctor_doc.get('managed_patients', [])
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    future_end_date_utc = now_utc + datetime.timedelta(days=days_ahead)

    # Query for appointments where:
    # 1. The event is a 'booked_appointment'.
    # 2. The status is 'booked'.
    # 3. The creator_id of the event (which was the doctor who made the slot) is the current doctor.
    # 4. The user_id of the event (who owns the booked appointment) is one of the doctor's managed patients.
    # 5. The start_time is in the future and within the days_ahead window.
    query = {
        "event_type": "booked_appointment",
        "status": "booked",
        "creator_id": doctor_object_id, 
        "user_id": {"$in": managed_patient_ids} if managed_patient_ids else [], # Handle if no managed patients
        "start_time": {"$gte": now_utc, "$lt": future_end_date_utc}
    }
    logger.info(f"Upcoming booked_appointments query for doctor {user_id_str}: {query}")

    try:
        appointments_cursor = db.calendar_events.find(query).sort("start_time", 1).limit(limit)
        
        results = []
        patient_ids_for_names = {appt.get("user_id") for appt in appointments_cursor} # Collect unique patient IDs
        appointments_cursor.rewind() # Reset cursor to iterate again for formatting

        patients_info = {}
        if patient_ids_for_names:
            patients_docs = db.patients.find(
                {"_id": {"$in": list(patient_ids_for_names)}},
                {"_id": 1, "personal_details.first_name": 1, "personal_details.last_name": 1}
            )
            for p_doc in patients_docs:
                patients_info[str(p_doc["_id"])] = f"{p_doc.get('personal_details',{}).get('first_name','').strip()} {p_doc.get('personal_details',{}).get('last_name','').strip()}".strip()
        
        for appt in appointments_cursor:
            patient_name = patients_info.get(str(appt.get("user_id")), "Άγνωστος Ασθενής")
            results.append({
                "id": str(appt["_id"]),
                "title": appt.get("title", f"Ραντεβού με {patient_name}"), # More descriptive title
                "start": appt["start_time"].isoformat(),
                "patient_name": patient_name,
                "event_type": appt.get("event_type")
            })
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error fetching upcoming booked appointments: {e}")
        return jsonify({"error": "Error fetching upcoming booked appointments"}), 500


@calendar_bp.route('/all_upcoming_activities', methods=['GET'])
@jwt_required()
def get_all_upcoming_activities():
    user_id_str = get_jwt_identity()
    limit = request.args.get('limit', default=10, type=int)
    days_ahead = request.args.get('days_ahead', default=7, type=int)

    if db is None: return jsonify({"error": "Database connection failed"}), 500
    try:
        user_object_id = ObjectId(user_id_str)
    except InvalidId: return jsonify({"error": "Invalid user ID in token"}), 400

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    future_end_date_utc = now_utc + datetime.timedelta(days=days_ahead)

    or_conditions = []
    user_role = None

    doctor_doc = db.doctors.find_one({"_id": user_object_id}, {"managed_patients": 1})
    if doctor_doc:
        user_role = 'doctor'
        managed_patient_ids = doctor_doc.get('managed_patients', [])
        # 1. Doctor's own personal tasks, or instructions/reminders they created for themselves (not typical but possible)
        or_conditions.append({"user_id": user_object_id, "creator_id": user_object_id, "event_type": {"$nin": ["appointment_slot"]}})
        # 2. Events doctor created FOR patients (med_reminder, measurement_reminder, doctor_instruction)
        if managed_patient_ids:
            or_conditions.append({"creator_id": user_object_id, "user_id": {"$in": managed_patient_ids}, "event_type": {"$nin": ["appointment_slot", "booked_appointment"]}})
        # 3. Events CREATED BY managed patients (logs, notes)
        if managed_patient_ids:
            or_conditions.append({"creator_id": {"$in": managed_patient_ids}, "user_id": {"$in": managed_patient_ids}, "visibility": "shared_with_doctor"})
        # 4. Booked appointments where the doctor is the creator of the original slot (covered by /upcoming_booked_appointments, but can be included here for a combined view if desired, or excluded)
        #    For this "all activities" endpoint, let's include them as well if they are not "available" slots
        if managed_patient_ids:
             or_conditions.append({"creator_id": user_object_id, "user_id": {"$in": managed_patient_ids}, "event_type": "booked_appointment"})


    else:
        patient_doc = db.patients.find_one({"_id": user_object_id}, {"assigned_doctors": 1})
        if patient_doc:
            user_role = 'patient'
            assigned_doctor_ids = patient_doc.get('assigned_doctors', [])
            # 1. Patient's own created events (logs, notes)
            or_conditions.append({"user_id": user_object_id, "creator_id": user_object_id})
            # 2. Events created BY a doctor FOR this patient (reminders, instructions, booked appointments)
            if assigned_doctor_ids:
                 or_conditions.append({"user_id": user_object_id, "creator_id": {"$in": assigned_doctor_ids}, "event_type": {"$ne": "appointment_slot"}})
        else:
            return jsonify({"error": "User not found as doctor or patient"}), 404

    query = {
        "$or": or_conditions,
        "start_time": {"$gte": now_utc, "$lt": future_end_date_utc},
        "status": {"$nin": ["cancelled", "available"]} # Exclude cancelled and purely available slots
    }
    
    # If it's a doctor and an event is 'appointment_slot', it must not be 'available' to show here.
    # Booked appointments are fine.
    if user_role == 'doctor':
        query["$nor"] = [{"event_type": "appointment_slot", "status": "available"}]


    logger.info(f"All upcoming activities query for {user_role} {user_id_str}: {query}")

    try:
        activities_cursor = db.calendar_events.find(query).sort("start_time", 1).limit(limit)
        results = []

        # Collect all relevant user IDs (patients and doctors) to fetch names efficiently
        all_user_ids_for_names = set()
        temp_activities_list = list(activities_cursor) # Consume cursor once
        activities_cursor.rewind() # Reset for next iteration

        for activity in temp_activities_list:
            all_user_ids_for_names.add(activity.get("user_id"))
            all_user_ids_for_names.add(activity.get("creator_id"))
        
        names_map = {}
        if all_user_ids_for_names:
            # Fetch patient names
            patients_docs = db.patients.find(
                {"_id": {"$in": list(all_user_ids_for_names)}},
                {"_id": 1, "personal_details.first_name": 1, "personal_details.last_name": 1}
            )
            for p_doc in patients_docs:
                names_map[str(p_doc["_id"])] = f"{p_doc.get('personal_details',{}).get('first_name','').strip()} {p_doc.get('personal_details',{}).get('last_name','').strip()}".strip()
            
            # Fetch doctor names
            doctors_docs = db.doctors.find(
                {"_id": {"$in": list(all_user_ids_for_names)}},
                 {"_id": 1, "personal_details.first_name": 1, "personal_details.last_name": 1}
            )
            for d_doc in doctors_docs:
                 names_map[str(d_doc["_id"])] = f"Dr. {d_doc.get('personal_details', {}).get('last_name', '?')}"


        for activity in temp_activities_list:
            formatted_activity = {
                "id": str(activity["_id"]),
                "title": activity.get("title", "Δραστηριότητα"),
                "start": activity["start_time"].isoformat(),
                "event_type": activity.get("event_type"),
                "status": activity.get("status"),
            }
            
            activity_user_id_str = str(activity.get("user_id"))
            activity_creator_id_str = str(activity.get("creator_id"))

            if user_role == 'doctor':
                # If the event's user_id is different from the doctor, it's a patient's event or for a patient
                if activity_user_id_str != user_id_str:
                    formatted_activity["relevant_person_name"] = names_map.get(activity_user_id_str, "Ασθενής")
                # If creator is different from doctor (e.g. patient created a log), show patient name
                elif activity_creator_id_str != user_id_str and activity_creator_id_str in names_map:
                     formatted_activity["relevant_person_name"] = names_map.get(activity_creator_id_str, "Ασθενής")
            
            elif user_role == 'patient':
                # If the event's creator_id is different from the patient, it's likely from a doctor
                if activity_creator_id_str != user_id_str:
                    formatted_activity["relevant_person_name"] = names_map.get(activity_creator_id_str, "Γιατρός")
            
            results.append(formatted_activity)
            
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error fetching all upcoming activities: {e}, Query: {query}")
        return jsonify({"error": "Error fetching all upcoming activities"}), 500