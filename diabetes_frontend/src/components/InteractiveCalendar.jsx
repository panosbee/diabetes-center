import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, Typography, Box, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Button, TextField, Chip, Select, MenuItem, FormControl, InputLabel, IconButton, Autocomplete, OutlinedInput, Checkbox, ListItemText } from '@mui/material'; // Added Autocomplete, OutlinedInput, Checkbox, ListItemText
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
// --- Εισαγωγή νέων εικονιδίων --- 
import EventAvailableIcon from '@mui/icons-material/EventAvailable'; // Για slots
import EventBusyIcon from '@mui/icons-material/EventBusy'; // Για booked appointments
import MedicationIcon from '@mui/icons-material/Medication'; // Για medication reminder
import RestaurantIcon from '@mui/icons-material/Restaurant'; // Για meal log
import FitnessCenterIcon from '@mui/icons-material/FitnessCenter'; // Για exercise log
import AssignmentIcon from '@mui/icons-material/Assignment'; // Για tasks/instructions
import SpeakerNotesIcon from '@mui/icons-material/SpeakerNotes'; // Για notes
import MonitorWeightIcon from '@mui/icons-material/MonitorWeight'; // Για measurement reminder
// --- Νέο εικονίδιο για Edit ---
import EditIcon from '@mui/icons-material/Edit';
// --- Και για Close ---
import CloseIcon from '@mui/icons-material/Close';
// --- Προσθήκη εικονιδίων για Dialog --- 
import SaveIcon from '@mui/icons-material/Save';
import DeleteIcon from '@mui/icons-material/DeleteOutline'; // Ήδη υπάρχει αλλά το χρησιμοποιούμε κι εδώ
// --- Νέο εικονίδιο --- 
// import AddCommentIcon from '@mui/icons-material/AddComment'; // <-- ΑΦΑΙΡΕΣΗ
// ---------------------------------

// Imports για FullCalendar
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid'; // για month, week, day views (grid)
import timeGridPlugin from '@fullcalendar/timegrid'; // για week, day views (time)
import listPlugin from '@fullcalendar/list'; // για list view
import interactionPlugin from '@fullcalendar/interaction'; // για dateClick, select, eventDrag κλπ

// Import για κλήσεις API (προσαρμόστε ανάλογα με το πώς είναι ο dataProvider σας)
// Προς το παρόν, θα χρησιμοποιήσουμε απευθείας fetch με το token

// --- React Admin hooks ---
import { useGetList, useNotify, useGetIdentity } from 'react-admin';

const eventTypeOptions = [
    { value: 'appointment_slot', label: 'Διαθέσιμο Ραντεβού' },
    { value: 'booked_appointment', label: 'Κλεισμένο Ραντεβού' },
    { value: 'medication_reminder', label: 'Υπενθ. Φαρμάκου' },
    { value: 'measurement_reminder', label: 'Υπενθ. Μέτρησης' },
    { value: 'personal_task', label: 'Προσωπική Εργασία' },
    // { value: 'patient_note', label: 'Σημείωση Ασθενή' },
];

// --- ΝΕΑ ΣΥΝΑΡΤΗΣΗ: Custom rendering για τα events ---
function renderEventContent(eventInfo, patients) {
  const eventType = eventInfo.event.extendedProps.event_type;
  const userId = eventInfo.event.extendedProps.user_id;
  const creatorId = eventInfo.event.extendedProps.creator_id;
  const isForPatient = userId !== creatorId;
  
  let icon = <AssignmentIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />;
  let patientName = null;
  
  if (eventType === 'appointment_slot') icon = <EventAvailableIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />;
  else if (eventType === 'booked_appointment') icon = <EventBusyIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />;
  else if (eventType === 'medication_reminder') icon = <MedicationIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />;
  else if (eventType === 'measurement_reminder') icon = <MonitorWeightIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />;
  else if (eventType === 'meal_log') icon = <RestaurantIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />;
  else if (eventType === 'exercise_log') icon = <FitnessCenterIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />;
  else if (eventType === 'personal_task') icon = <AssignmentIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />;
  else if (eventType === 'patient_note') icon = <SpeakerNotesIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />;
  
  // Εύρεση ονόματος ασθενή αν το event είναι για ασθενή
  if (isForPatient && patients && userId) {
      const patient = patients.find(p => p.id === userId);
      if (patient) {
          patientName = `${patient.personal_details?.last_name || ''} ${patient.personal_details?.first_name?.[0] || ''}.`;
      }
  }
  
  return (
    <Box sx={{ overflow: 'hidden', fontSize: '0.8em', p: '2px', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
             {icon} 
             {/* Η ώρα μπορεί να εμφανίζεται πιο διακριτικά ή καθόλου αν θέλουμε */}
             {/* <Typography variant="caption" component="span" sx={{ fontWeight: 'normal', mr: 0.5, opacity: 0.8 }}> {eventInfo.timeText} </Typography> */}
             {/* <Typography variant="body2" component="span" sx={{ fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                 {eventInfo.timeText}
             </Typography> */}
             <Typography variant="body2" component="span" sx={{ fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                 {eventInfo.timeText}
             </Typography>
             <Typography variant="body2" component="span" sx={{ ml: 0.5, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                 {eventInfo.event.title}
             </Typography>
        </Box>
        {patientName && (
            <Typography variant="caption" sx={{ display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', opacity: 0.8, pl: '22px' }}>
                 {patientName}
             </Typography>
        )}
    </Box>
  )
}
// ---------------------------------------------------

// --- Imports για Date/Time Picker --- 
// import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
// import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
// import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
// import dayjs from 'dayjs'; // Import dayjs
// ------------------------------------

const InteractiveCalendar = ({ onInitiateCall }) => {
  // === DEBUG: Έλεγχος Ημερομηνίας Browser ===
  console.log("Current Browser Date:", new Date());
  // ==========================================
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedDateInfo, setSelectedDateInfo] = useState(null);
  const [eventTitle, setEventTitle] = useState(''); // Αλλαγή σε κενό string
  const [eventType, setEventType] = useState('appointment_slot'); // Default event type
  const calendarRef = useRef(null); // Ref για πρόσβαση στο FullCalendar API

  // --- State για ασθενείς και επιλεγμένο ασθενή ---
  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState('');
  const [isLoadingPatients, setIsLoadingPatients] = useState(false);
  const [filterSelectedPatients, setFilterSelectedPatients] = useState([]); // For multi-select patient filter
  const [selectedEventTypes, setSelectedEventTypes] = useState([]); // For multi-select event type filter
  // --------------------------------------------------

  // --- State για το Dialog Προβολής/Επεξεργασίας Event (παλιό) ---
  // Το μετονομάζουμε σε View Dialog
  const [viewEventDialogOpen, setViewEventDialogOpen] = useState(false);
  const [selectedEventForView, setSelectedEventForView] = useState(null); 
  
  // --- State για το ΝΕΟ Dialog Επεξεργασίας Event ---
  const [editEventDialogOpen, setEditEventDialogOpen] = useState(false);
  const [eventToEdit, setEventToEdit] = useState(null);
  // Επαναφορά του editEventData μόνο για τον τίτλο
  const [editEventData, setEditEventData] = useState({ title: '' }); 
  // ----------------------------------------

  // --- React Admin hooks ---
  const notify = useNotify();
  const { identity, isLoading: identityLoading } = useGetIdentity();
  // ------------------------

  // --- Φόρτωση λίστας ασθενών του γιατρού (αν ο χρήστης είναι γιατρός) ---
  useEffect(() => {
    const fetchDoctorPatients = async () => {
      if (identity && identity.id && !identityLoading) { // Έλεγχος ότι έχουμε identity γιατρού
        // Υποθέτουμε ότι το identity.role ή κάποιο άλλο πεδίο μας λέει αν είναι γιατρός
        // Προς το παρόν, αν υπάρχει identity, φορτώνουμε τους ασθενείς του.
        // Προσαρμόστε το resource ανάλογα με το πώς είναι το API σας
        const token = localStorage.getItem('access_token');
        if (!token) {
            console.error("Auth token not found for fetching patients.");
            return;
        }
        setIsLoadingPatients(true);
        try {
          // Χρησιμοποιούμε το endpoint που φέρνει τους ασθενείς του γιατρού
          // Για React Admin, θα μπορούσε να είναι ένα custom call ή απευθείας fetch
          const response = await fetch(`${import.meta.env.VITE_API_URL}/api/doctor-portal/patients?_sort=personal_details.last_name&_order=ASC`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            }
          });
          if (!response.ok) {
            throw new Error('Failed to fetch patients');
          }
          const data = await response.json();
          setPatients(data || []); 
        } catch (error) {
          console.error("Error fetching patients:", error);
          notify('Error fetching patients', { type: 'error' });
          setPatients([]);
        }
        setIsLoadingPatients(false);
      }
    };

    fetchDoctorPatients();
  }, [identity, identityLoading, notify]);
  // -------------------------------------------------------------------

  // Handler για όταν ο χρήστης επιλέγει ένα χρονικό διάστημα
  const handleSelect = (selectInfo) => {
    console.log('Selected date range:', selectInfo);
    setSelectedDateInfo(selectInfo);
    setEventType('appointment_slot'); // Default σε slot όταν επιλέγουμε
    setEventTitle(''); // Καθαρισμός τίτλου - θα οριστεί μετά την επιλογή ασθενή
    setSelectedPatientId(''); // Καθαρισμός επιλεγμένου ασθενή όταν ανοίγει το dialog
    setDialogOpen(true);
  };

  // Handler για κλείσιμο Dialog Δημιουργίας
  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedDateInfo(null);
    if (calendarRef.current) calendarRef.current.getApi().unselect();
  };

  // Handler για κλείσιμο Dialog Προβολής
  const handleCloseViewDialog = () => {
      setViewEventDialogOpen(false);
      setSelectedEventForView(null);
  };
  
  // --- Handlers για ΝΕΟ Dialog Επεξεργασίας ---
  const handleOpenEditDialog = (event) => {
      setEventToEdit(event); 
      setEditEventData({
          title: event.title || '',
          // Όχι πια ημερομηνίες ή details εδώ
      });
      // setNewComment(''); // Αφαίρεση
      setEditEventDialogOpen(true);
  };
  
  const handleCloseEditDialog = () => {
      setEditEventDialogOpen(false);
      setEventToEdit(null);
      setEditEventData({ title: '' }); // Καθαρισμός state επεξεργασίας
      // setNewComment(''); // Αφαίρεση
  };
  
  const handleEditFormChange = (e) => {
       const { name, value } = e.target;
       // Ενημέρωση μόνο για title
       if (name === 'title') {
            setEditEventData(prev => ({ ...prev, title: value }));
       }
   };
   
   // Αφαίρεση handlers για date pickers
   // const handleStartDateChange = ... 
   // const handleEndDateChange = ... 

  const handleSaveEditedEvent = () => {
       if (!eventToEdit || !editEventData.title) {
           notify('Ο τίτλος είναι υποχρεωτικός', { type: 'warning' });
           return;
       }
       
       const token = localStorage.getItem('access_token');
       if (!token) { notify('Authentication Error', {type: 'error'}); return; }
       
       const url = `${import.meta.env.VITE_API_URL}/api/calendar/events/${eventToEdit.id}`;
       
       // Payload μόνο με τον τίτλο
       const updatePayload = {
           title: editEventData.title,
       };
       
        fetch(url, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(updatePayload)
        })
        .then(response => response.ok ? response.json() : response.json().then(err => { throw new Error(err.error || 'Failed to update event') }))
        .then(updatedEvent => {
            console.log("Event updated:", updatedEvent);
            if (calendarRef.current) calendarRef.current.getApi().refetchEvents();
            notify('Το γεγονός ενημερώθηκε', { type: 'success' });
            handleCloseEditDialog();
        })
        .catch(error => {
            console.error('Error updating event:', error);
            notify(`Σφάλμα ενημέρωσης: ${error.message}`, { type: 'error' });
        });
   };

  // --- ΝΕΑ Συνάρτηση για διαγραφή από το Edit Dialog --- 
  const handleDeleteFromEditDialog = () => {
        if (!eventToEdit) return;
        
        // Έλεγχος δικαιώματος (απλοποιημένος: μόνο ο creator διαγράφει προς το παρόν)
        if (identity?.id !== eventToEdit.extendedProps.creator_id) {
             notify('Δεν έχετε δικαίωμα διαγραφής αυτού του γεγονότος.', { type: 'warning' });
             return;
        }

      if (confirm(`Είστε σίγουροι ότι θέλετε να διαγράψετε το γεγονός "${eventToEdit.title}";\nΑυτή η ενέργεια δεν αναιρείται.`)) {
          const token = localStorage.getItem('access_token');
          if (!token) { notify('Authentication Error', {type: 'error'}); return; }
          
          const url = `${import.meta.env.VITE_API_URL}/api/calendar/events/${eventToEdit.id}`;
          
          fetch(url, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` }})
              .then(response => {
                  if (!response.ok) { return response.json().then(err => { throw new Error(err.error || 'Failed delete') }); }
                  return null;
              })
              .then(() => {
                  notify('Το γεγονός διαγράφηκε', { type: 'info' });
                  if (calendarRef.current) calendarRef.current.getApi().refetchEvents();
                  handleCloseEditDialog(); // Κλείσιμο του edit dialog μετά τη διαγραφή
              })
              .catch(error => {
                  notify(`Σφάλμα διαγραφής: ${error.message}`, { type: 'error' });
                  handleCloseEditDialog(); // Κλείσιμο και σε σφάλμα
              });
       }
   };
   // --------------------------------------------------

  // === ΑΝΤΙΚΑΤΑΣΤΑΣΗ handleCreateEvent ===
  const handleCreateEvent = () => {
    if (!selectedDateInfo) return;

    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error("Auth token not found for creating event.");
      handleCloseDialog();
      return;
    }

    let finalTitle = eventTitle;
    
    // Αυτόματη δημιουργία τίτλου για appointment slots
    if (eventType === 'appointment_slot' && selectedPatientId && (!finalTitle || !finalTitle.trim())) {
      const selectedPatient = patients.find(p => p.id === selectedPatientId);
      if (selectedPatient) {
        finalTitle = `Διαθέσιμο Ραντεβού - ${selectedPatient.personal_details?.last_name} ${selectedPatient.personal_details?.first_name}`;
      } else {
        finalTitle = 'Διαθέσιμο Ραντεβού';
      }
    } else if (eventType === 'appointment_slot' && !finalTitle) {
      finalTitle = 'Διαθέσιμο Ραντεβού';
    }
    
    if (!finalTitle) {
      alert('Please enter a title for the event.');
      return;
    }

    // Έλεγχος ότι έχει επιλεγεί ασθενής για τύπους που το απαιτούν
    if (eventType !== 'personal_task' && !selectedPatientId) {
      notify('Παρακαλώ επιλέξτε ασθενή για αυτόν τον τύπο γεγονότος', { type: 'warning' });
      return;
    }

    let userIdForEvent = null;
    if (selectedPatientId && eventType !== 'personal_task') {
      userIdForEvent = selectedPatientId;
    }

    // === Κύρια αντικατάσταση: Εξασφάλιση σωστών πεδίων για slot ===
    const newEventData = {
      event_type: eventType,
      title: finalTitle,
      start: selectedDateInfo.start.toISOString(),
      end: selectedDateInfo.end.toISOString(),
      allDay: selectedDateInfo.allDay,
      details: {}
    };

    // Ειδικά πεδία για slot
    if (eventType === 'appointment_slot') {
      newEventData.status = 'available';
      newEventData.visibility = 'shared_with_patient';
    }

    if (userIdForEvent) {
      newEventData.user_id = userIdForEvent;
    }

    // Ειδικά details για medication/measurement
    if (eventType === 'medication_reminder') {
      const medName = document.getElementById('med_name')?.value;
      const medDosage = document.getElementById('med_dosage')?.value;
      const medFreq = document.getElementById('med_freq')?.value;
      if (!medName) { notify('Παρακαλώ εισάγετε όνομα φαρμάκου', { type: 'warning' }); return; }
      newEventData.details = { med_name: medName, med_dosage: medDosage, med_freq: medFreq };
      if (!finalTitle || finalTitle === 'Διαθέσιμο Ραντεβού') {
        newEventData.title = `Υπενθύμιση: ${medName}`;
      }
    } else if (eventType === 'measurement_reminder') {
      const measType = document.getElementById('meas-type')?.value;
      const measTarget = document.getElementById('meas_target')?.value;
      newEventData.details = { meas_type: measType, meas_target: measTarget };
      if (!finalTitle || finalTitle === 'Διαθέσιμο Ραντεβού') {
        newEventData.title = `Υπενθύμιση Μέτρησης: ${measType}`;
      }
    }

    const url = `${import.meta.env.VITE_API_URL}/api/calendar/events`;

    fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(newEventData)
    })
      .then(response => {
        if (!response.ok) {
          return response.json().then(err => { throw new Error(err.error || 'Failed to create event') });
        }
        return response.json();
      })
      .then(createdEvent => {
        console.log("Event created successfully:", createdEvent);
        if (calendarRef.current) {
          calendarRef.current.getApi().refetchEvents();
          notify('Calendar events refetched.', { type: 'info', autoHideDuration: 2000 }); // DEBUG
        }
        handleCloseDialog();
      })
      .catch(error => {
        console.error('Error creating event:', error);
        notify(`Σφάλμα δημιουργίας γεγονότος: ${error.message}`, { type: 'error' });
        handleCloseDialog();
      });
  };


  // Handler για κλικ πάνω σε ένα event
  const handleEventClick = (clickInfo) => {
    console.log('Event clicked:', clickInfo.event);
    const event = clickInfo.event;
    const eventType = event.extendedProps.event_type; // Get event_type from extendedProps

    // Μέσα στο handleEventClick στο InteractiveCalendar.jsx

if (eventType === 'booked_appointment') {
    const patientIdForCall = event.extendedProps.user_id; // Το user_id του booked_appointment είναι του ασθενή
    const patientName = event.extendedProps.patient_name || 'τον ασθενή'; // Πάρε το όνομα αν υπάρχει
    const appointmentTitle = event.title || `Ραντεβού με ${patientName}`; // Πάρε τον τίτλο του ραντεβού

    if (identity && identity.id && patientIdForCall && identity.id !== patientIdForCall) { 
        // Βεβαιώσου ότι ο γιατρός καλεί ασθενή, όχι τον εαυτό του
        if (confirm(`Θέλετε να ξεκινήσετε τηλεδιάσκεψη για το ραντεβού "${appointmentTitle}" με ${patientName};`)) {
            // Κάλεσε τη συνάρτηση που ήρθε από το Dashboard
            if (onInitiateCall) {
                console.log(`[InteractiveCalendar] Calling onInitiateCall for patient: ${patientIdForCall}`);
                onInitiateCall(patientIdForCall, appointmentTitle); // Περνάμε το ID του ασθενή και τον τίτλο
            } else {
                notify('Function to initiate call is not available.', { type: 'error' });
            }
        }
    } else {
        notify('Δεν είναι δυνατή η έναρξη κλήσης για αυτό το ραντεβού (μη έγκυρα δεδομένα).', { type: 'warning' });
    }
} else if (event.extendedProps.event_type === 'appointment_slot'){ // Διόρθωση: event.extendedProps.event_type
    // --- Η υπάρχουσα λογική διαγραφής slot ---
    if (identity?.id === event.extendedProps.creator_id) { // Μόνο ο δημιουργός διαγράφει
        if (confirm(`Είστε σίγουροι ότι θέλετε να διαγράψετε αυτό το διαθέσιμο slot;\n'${event.title}'`)) {
            const token = localStorage.getItem('access_token');
            if (!token) {
                notify('Authentication error. Please log in again.', { type: 'error' });
                return;
            }
            const url = `${import.meta.env.VITE_API_URL}/api/calendar/events/${event.id}`;
            fetch(url, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } })
                .then(response => {
                    if (!response.ok) { return response.json().then(err => { throw new Error(err.error || 'Failed delete') }); }
                    return null;
                })
                .then(() => {
                    notify('Το διαθέσιμο slot διαγράφηκε.', { type: 'info' });
                    if (calendarRef.current) calendarRef.current.getApi().refetchEvents();
                })
                .catch(error => notify(`Σφάλμα διαγραφής slot: ${error.message}`, { type: 'error' }));
        }
    } else {
        notify('Δεν μπορείτε να διαγράψετε αυτό το slot.', { type: 'warning' });
    }
    // --- Τέλος λογικής διαγραφής slot ---
} else {
    handleOpenEditDialog(event); // Άνοιγμα dialog επεξεργασίας για άλλους τύπους
}
  };

  // Handler για μετακίνηση event (drag & drop)
  const handleEventDrop = (dropInfo) => {
    console.log('Event dropped:', dropInfo.event);
    const { event } = dropInfo;
    const token = localStorage.getItem('access_token');
    if (!token) { alert('Authentication error'); return; }

    // Προετοιμασία δεδομένων για PATCH
    const updateData = {
        start_time: event.startStr, // Το FullCalendar δίνει τα νέα strings
        end_time: event.endStr,     // (πιθανόν null αν έγινε allDay)
        all_day: event.allDay
    };

    const url = `${import.meta.env.VITE_API_URL}/api/calendar/events/${event.id}`;

    fetch(url, {
        method: 'PATCH',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        body: JSON.stringify(updateData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { 
                throw new Error(err.error || `Failed to update event (drop - status: ${response.status})`)
            }).catch(() => {
                 throw new Error(`Failed to update event (drop - status: ${response.status})`)
            });
        }
        return response.json(); // Παίρνουμε το ενημερωμένο event
    })
    .then(updatedEvent => {
        console.log("Event updated successfully after drop:", updatedEvent);
        // Δεν χρειάζεται refetch, το FullCalendar το έχει ήδη αλλάξει στο UI
        // Μπορούμε όμως να ενημερώσουμε τα extendedProps αν το backend τα άλλαξε
        // event.setExtendedProp('key', updatedEvent.extendedProps.key);
    })
    .catch(error => {
        console.error('Error updating event after drop:', error);
        notify(`Σφάλμα ενημέρωσης γεγονότος: ${error.message}`, { type: 'error' });
        // Αν αποτύχει, κάνουμε revert την αλλαγή στο UI
        dropInfo.revert(); 
    });
  };

  // Handler για αλλαγή μεγέθους event
  const handleEventResize = (resizeInfo) => {
    console.log('Event resized:', resizeInfo.event);
    const { event } = resizeInfo;
    const token = localStorage.getItem('access_token');
    if (!token) { alert('Authentication error'); return; }

    // Προετοιμασία δεδομένων για PATCH (ίδια με το drop)
    const updateData = {
        start_time: event.startStr,
        end_time: event.endStr,
        all_day: event.allDay
    };

    const url = `${import.meta.env.VITE_API_URL}/api/calendar/events/${event.id}`;

     fetch(url, {
        method: 'PATCH',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        body: JSON.stringify(updateData)
    })
    .then(response => {
        if (!response.ok) {
             return response.json().then(err => { 
                throw new Error(err.error || `Failed to update event (resize - status: ${response.status})`)
            }).catch(() => {
                 throw new Error(`Failed to update event (resize - status: ${response.status})`)
            });
        }
        return response.json();
    })
    .then(updatedEvent => {
        console.log("Event updated successfully after resize:", updatedEvent);
    })
    .catch(error => {
        console.error('Error updating event after resize:', error);
        notify(`Σφάλμα ενημέρωσης γεγονότος: ${error.message}`, { type: 'error' });
        // Αν αποτύχει, κάνουμε revert την αλλαγή στο UI
        resizeInfo.revert(); 
    });
  };
  
  // Συνάρτηση για φόρτωση events από το backend API
  const fetchEvents = (fetchInfo, successCallback, failureCallback) => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error("Auth token not found for fetching calendar events.");
      failureCallback('Authentication token not found');
      return;
    }
    let url = `${import.meta.env.VITE_API_URL}/api/calendar/events?start=${fetchInfo.startStr}&end=${fetchInfo.endStr}`; // Changed to let
    
    // Add patient IDs to URL if filterSelectedPatients is not empty
    if (filterSelectedPatients.length > 0) {
        const patientIdsQuery = filterSelectedPatients.map(p => `patient_ids[]=${p.id}`).join('&');
        url += `&${patientIdsQuery}`;
    }
    // Add event types to URL if filterSelectedEventTypes is not empty
    if (selectedEventTypes.length > 0) {
        const eventTypesQuery = selectedEventTypes.map(type => `event_types[]=${type}`).join('&');
        url += `&${eventTypesQuery}`;
    }
    console.log(`Fetching events from: ${url}`); // Log the potentially modified URL

    fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      }
    })
      .then(response => {
        if (!response.ok) {
          console.error("Error fetching events:", response.statusText);
          return response.text().then(text => { throw new Error(text || response.statusText) });
        }
        return response.json();
      })
      .then(data => {
        // === Mapping για FullCalendar ===
        const mapped = data.map(ev => ({
          id: ev.id || ev._id,
          title: ev.title,
          start: ev.start || ev.start_time,
          end: ev.end || ev.end_time,
          allDay: ev.allDay,
          extendedProps: ev.extendedProps || {
            event_type: ev.event_type,
            creator_id: ev.creator_id,
            user_id: ev.user_id,
            status: ev.status,
            visibility: ev.visibility,
            details: ev.details,
            doctor_name: ev.doctor_name,
            patient_name: ev.patient_name,
            ...ev
          },
          ...ev,
        }));
        console.log("Events received:", mapped);
        successCallback(mapped);
      })
      .catch(error => {
        console.error('Error fetching events:', error);
        failureCallback(error);
      });
  };

  return (
    <Card sx={{ height: '100%', borderRadius: 3 }}>
      <CardContent sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
           <CalendarMonthIcon sx={{ mr: 1 }} />
           <Typography variant="h6" fontWeight={600}>
             Ημερολόγιο Ραντεβού & Δραστηριοτήτων
           </Typography>
        </Box>
        {/* Patient Filter Autocomplete */}
        <Box sx={{ mb: 2, display: 'flex', flexWrap: 'wrap', gap: 2 }}> {/* Added flexWrap */}
           <FormControl sx={{minWidth: 300, flexGrow: 1 }}> {/* Added flexGrow */}
               <Autocomplete
                   multiple
                   id="patient-filter-autocomplete"
                   options={patients}
                   value={filterSelectedPatients}
                   onChange={(event, newValue) => {
                       setFilterSelectedPatients(newValue);
                       if (calendarRef.current) {
                           calendarRef.current.getApi().refetchEvents();
                       }
                   }}
                   getOptionLabel={(patient) =>
                       `${patient.personal_details?.last_name || ''} ${patient.personal_details?.first_name || ''} (AMKA: ${patient.personal_details?.amka || 'N/A'})`
                   }
                   renderInput={(params) => (
                       <TextField
                           {...params}
                           variant="standard"
                           label="Φιλτράρισμα ανά Ασθενή"
                           placeholder="Επιλογή Ασθενών"
                       />
                   )}
                   loading={isLoadingPatients}
                   ChipProps={{ size: 'small' }}
                   noOptionsText="Δεν βρέθηκαν ασθενείς"
                   loadingText="Φόρτωση ασθενών..."
               />
           </FormControl>
           {/* Event Type Filter Select */}
           <FormControl sx={{ minWidth: 250, flexGrow: 1 }}> {/* Added flexGrow */}
               <InputLabel id="event-type-filter-label">Φιλτράρισμα ανά Τύπο</InputLabel>
               <Select
                   multiple
                   labelId="event-type-filter-label"
                   id="event-type-filter-select"
                   value={selectedEventTypes}
                   onChange={(event) => {
                       const {
                           target: { value },
                       } = event;
                       setSelectedEventTypes(
                           // On autofill we get a stringified value.
                           typeof value === 'string' ? value.split(',') : value,
                       );
                       if (calendarRef.current) {
                           calendarRef.current.getApi().refetchEvents();
                       }
                   }}
                   input={<OutlinedInput label="Φιλτράρισμα ανά Τύπο" />}
                   renderValue={(selected) => (
                       <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                           {selected.map((value) => {
                               const option = eventTypeOptions.find(opt => opt.value === value);
                               return <Chip key={value} label={option ? option.label : value} size="small" />;
                           })}
                       </Box>
                   )}
                   MenuProps={{ PaperProps: { style: { maxHeight: 224 } } }}
               >
                   {eventTypeOptions.map((option) => (
                       <MenuItem key={option.value} value={option.value}>
                           <Checkbox checked={selectedEventTypes.indexOf(option.value) > -1} />
                           <ListItemText primary={option.label} />
                       </MenuItem>
                   ))}
               </Select>
           </FormControl>
           {/* Event Type Filter Select */}
           <FormControl sx={{ minWidth: 250, flexGrow: 1 }}> {/* Added flexGrow */}
               <InputLabel id="event-type-filter-label">Φιλτράρισμα ανά Τύπο</InputLabel>
               <Select
                   multiple
                   labelId="event-type-filter-label"
                   id="event-type-filter-select"
                   value={selectedEventTypes}
                   onChange={(event) => {
                       const {
                           target: { value },
                       } = event;
                       setSelectedEventTypes(
                           // On autofill we get a stringified value.
                           typeof value === 'string' ? value.split(',') : value,
                       );
                       if (calendarRef.current) {
                           calendarRef.current.getApi().refetchEvents();
                       }
                   }}
                   input={<OutlinedInput label="Φιλτράρισμα ανά Τύπο" />}
                   renderValue={(selected) => (
                       <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                           {selected.map((value) => {
                               const option = eventTypeOptions.find(opt => opt.value === value);
                               return <Chip key={value} label={option ? option.label : value} size="small" />;
                           })}
                       </Box>
                   )}
                   MenuProps={{ PaperProps: { style: { maxHeight: 224 } } }}
               >
                   {eventTypeOptions.map((option) => (
                       <MenuItem key={option.value} value={option.value}>
                           <Checkbox checked={selectedEventTypes.indexOf(option.value) > -1} />
                           <ListItemText primary={option.label} />
                       </MenuItem>
                   ))}
               </Select>
           </FormControl>
       </Box>
        <Box sx={{ flexGrow: 1 }}> {/* Container για το ημερολόγιο */}
          <FullCalendar
            ref={calendarRef}
            plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
            }}
            initialView="timeGridWeek" // Αρχική προβολή
            editable={true}         // Επιτρέπει drag & drop / resize
            selectable={true}       // Επιτρέπει επιλογή ημερομηνιών/ωρών
            selectMirror={true}
            dayMaxEvents={true}
            weekends={true}
            events={fetchEvents} // Use the fetchEvents function
            select={handleSelect}     // Handler για επιλογή διαστήματος
            eventClick={handleEventClick} // Handler για κλικ σε event
            eventDrop={handleEventDrop}   // Handler για μετακίνηση event
            eventResize={handleEventResize} // Handler για αλλαγή μεγέθους event
            // --- Άλλες χρήσιμες ρυθμίσεις ---
            timeZone='Europe/Athens' // <-- ΡΗΤΟΣ ΟΡΙΣΜΟΣ TIMEZONE
            eventContent={(eventArg) => renderEventContent(eventArg, patients)} // <-- Περνάμε τη λίστα patients
            firstDay={1} // <-- Η ΕΒΔΟΜΑΔΑ ΞΕΚΙΝΑ ΔΕΥΤΕΡΑ
            // locale='el' // Για ελληνικά (χρειάζεται import '@fullcalendar/core/locales/el')
            // height="auto" // Προσαρμογή ύψους στο περιεχόμενο
            // businessHours={{ ... }} // Ορισμός ωρών λειτουργίας
            buttonText={{
                today:    'Σήμερα',
                month:    'Μήνας',
                week:     'Εβδομάδα',
                day:      'Ημέρα',
                list:     'Λίστα'
            }}
            allDayText='Ολοήμερο'
            slotDuration='00:15:00' // Default slot duration
            slotLabelInterval='01:00' // Display time labels every hour
            slotLabelFormat={{ // Format for time labels
                hour: '2-digit',
                minute: '2-digit',
                omitZeroMinute: false,
                meridiem: false, // Use 24-hour format
                hour12: false
            }}
            views={{ // Customize views
                timeGridWeek: {
                    slotMinTime: '00:00:00', // ΑΛΛΑΓΗ: Έναρξη από μεσάνυχτα
                    slotMaxTime: '24:00:00', // ΑΛΛΑΓΗ: Λήξη στο τέλος της ημέρας (ή '23:59:59')
                },
                timeGridDay: {
                    slotMinTime: '00:00:00', // ΑΛΛΑΓΗ: Έναρξη από μεσάνυχτα
                    slotMaxTime: '24:00:00', // ΑΛΛΑΓΗ: Λήξη στο τέλος της ημέρας (ή '23:59:59')
                }
            }}
          />
        </Box>
      </CardContent>
      
      {/* Dialog για Δημιουργία Event */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} fullWidth maxWidth="xs">
        <DialogTitle>Δημιουργία Γεγονότος Ημερολογίου</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Επιλεγμένο διάστημα: 
            {selectedDateInfo?.start.toLocaleString()} - 
            {selectedDateInfo?.end.toLocaleString()}
          </DialogContentText>
          
          {/* Επιλογή Τύπου Event */}
          <FormControl fullWidth margin="dense" variant="standard">
            <InputLabel id="event-type-label">Τύπος Γεγονότος</InputLabel>
            <Select
              labelId="event-type-label"
              id="event-type-select"
              value={eventType}
              onChange={(e) => {
                  setEventType(e.target.value);
                  // Καθαρισμός τίτλου όταν αλλάζει ο τύπος
                  setEventTitle('');
              }}
              label="Τύπος Γεγονότος"
            >
              <MenuItem value="appointment_slot">Διαθέσιμο Ραντεβού (Slot)</MenuItem>
              <MenuItem value="personal_task">Προσωπική Εργασία/Σημείωση</MenuItem>
              {/* --- Προσθήκη Νέων Τύπων --- */}
              <MenuItem value="medication_reminder">Υπενθύμιση Φαρμάκου (για Ασθενή)</MenuItem>
              <MenuItem value="measurement_reminder">Υπενθύμιση Μέτρησης (για Ασθενή)</MenuItem>
              {/* ---------------------------- */}
              {/* TODO: Προσθήκη άλλων τύπων */}
            </Select>
          </FormControl>

          {/* --- Επιλογή Ασθενή (εμφανίζεται για όλους τους τύπους εκτός από personal tasks) --- */}
          {eventType !== 'personal_task' && (
            <FormControl fullWidth margin="dense" variant="standard" disabled={isLoadingPatients}>
              <InputLabel id="patient-select-label">Επιλογή Ασθενή *</InputLabel>
              <Select
                labelId="patient-select-label"
                id="patient-select"
                value={selectedPatientId}
                onChange={(e) => setSelectedPatientId(e.target.value)}
                label="Επιλογή Ασθενή"
                required
              >
                <MenuItem value="">
                  <em>-- Επιλέξτε Ασθενή --</em>
                </MenuItem>
                {patients.map((patient) => (
                  <MenuItem key={patient.id} value={patient.id}>
                    {patient.personal_details?.last_name} {patient.personal_details?.first_name} (AMKA: {patient.personal_details?.amka})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          {/* ---------------------------------------------------- */}

          {/* Πεδίο Τίτλου */}
          <TextField
            required={(eventType !== 'appointment_slot') && (eventType !== 'medication_reminder') && (eventType !== 'measurement_reminder')} // Προσαρμογή required
            margin="dense"
            id="event-title"
            label="Τίτλος (προαιρετικός για slots και reminders)"
            type="text"
            fullWidth
            variant="standard"
            value={eventTitle}
            onChange={(e) => setEventTitle(e.target.value)}
            placeholder={eventType === 'appointment_slot' ? 'Θα δημιουργηθεί αυτόματα αν δεν συμπληρώσετε' : ''}
          />
          
          {/* --- Ειδικά Πεδία ανά Τύπο --- */}
          {eventType === 'medication_reminder' && (
             <>
                 <TextField margin="dense" id="med_name" label="Όνομα Φαρμάκου" type="text" fullWidth variant="standard" required />
                 <TextField margin="dense" id="med_dosage" label="Δοσολογία" type="text" fullWidth variant="standard" />
                 <TextField margin="dense" id="med_freq" label="Συχνότητα/Οδηγίες" type="text" fullWidth variant="standard" multiline />
             </>
          )}
          {eventType === 'measurement_reminder' && (
             <>
                 <FormControl fullWidth margin="dense" variant="standard">
                     <InputLabel id="meas-type-label">Τύπος Μέτρησης</InputLabel>
                     <Select labelId="meas-type-label" id="meas-type" defaultValue="blood_glucose" label="Τύπος Μέτρησης">
                         <MenuItem value="blood_glucose">Γλυκόζη Αίματος</MenuItem>
                         <MenuItem value="blood_pressure">Αρτηριακή Πίεση</MenuItem>
                         <MenuItem value="weight">Βάρος</MenuItem>
                     </Select>
                 </FormControl>
                 <TextField margin="dense" id="meas_target" label="Τιμή Στόχος (Προαιρετικά)" type="text" fullWidth variant="standard" />
             </>
          )}
          {/* TODO: Προσθήκη πεδίων για 'details' για άλλους τύπους */}
          
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Άκυρο</Button>
          <Button onClick={handleCreateEvent} variant="contained">Δημιουργία</Button> {/* Αλλαγή κειμένου κουμπιού */}
        </DialogActions>
      </Dialog>
      
      {/* ========= ΝΕΟ: Dialog για Επεξεργασία Event ========= */}
      <Dialog open={editEventDialogOpen} onClose={handleCloseEditDialog} fullWidth maxWidth="sm">
        <DialogTitle>
           Επεξεργασία Γεγονότος
           <IconButton aria-label="close" onClick={handleCloseEditDialog} sx={{ position: 'absolute', right: 8, top: 8 }}>
               <CloseIcon />
           </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {eventToEdit ? (
            <Box component="form" noValidate autoComplete="off">
              <TextField
                required
                autoFocus // Αυτόματη εστίαση στο πεδίο
                margin="dense" name="title" label="Τίτλος"
                type="text" fullWidth variant="standard"
                value={editEventData.title || ''}
                onChange={handleEditFormChange}
              />
              {/* Απλή εμφάνιση ημερομηνιών/ωρών */}
               <Typography variant="body2" color="textSecondary" sx={{mt: 2}}>
                   Έναρξη: {eventToEdit.start?.toLocaleString() || 'N/A'}
               </Typography>
               <Typography variant="body2" color="textSecondary">
                   Λήξη: {eventToEdit.end?.toLocaleString() || (eventToEdit.allDay ? '(Ολοήμερο)' : 'N/A')}
               </Typography>
                {/* Προβολή ασθενή (αν υπάρχει) */}
               {eventToEdit.extendedProps.patient_name && (
                   <Typography variant="body1" sx={{mt: 2}}><b>Ασθενής:</b> {eventToEdit.extendedProps.patient_name}</Typography>
               )}
               {/* Εμφάνιση details (απλή) */}
               {eventToEdit.extendedProps.details && Object.keys(eventToEdit.extendedProps.details).length > 0 && (
                   <Box mt={2}>
                       <Typography variant="subtitle2">Λεπτομέρειες:</Typography>
                       <pre style={{fontSize: '0.8em', background: '#f5f5f5', padding: '5px', borderRadius: '4px', whiteSpace: 'pre-wrap'}}>
                           {JSON.stringify(eventToEdit.extendedProps.details, null, 2)}
                       </pre>
                   </Box>
               )}
               {/* Εμφάνιση σχολίων (απλή) */}
                {eventToEdit.extendedProps?.doctor_comments?.length > 0 && (
                    <Box mt={2}>
                         <Typography variant="subtitle2">Σχόλια:</Typography>
                         <List dense sx={{ maxHeight: 100, overflow: 'auto'}}>
                             {eventToEdit.extendedProps.doctor_comments.map((c, i) => <ListItem key={i}><ListItemText primary={c.comment} secondary={new Date(c.timestamp).toLocaleString()} /></ListItem>)}
                         </List>
                    </Box>
                )}
            </Box>
          ) : ( <Typography>Φόρτωση...</Typography> )}
        </DialogContent>
        <DialogActions>
          {/* --- Προσθήκη Κουμπιού Διαγραφής --- */}
          {eventToEdit && identity?.id === eventToEdit.extendedProps.creator_id && (
                 <Button onClick={handleDeleteFromEditDialog} color="error" startIcon={<DeleteIcon />}>
                    Διαγραφή
                 </Button>
          )}
          {/* ----------------------------------- */}
          <Button onClick={handleCloseEditDialog}>Άκυρο</Button>
          <Button onClick={handleSaveEditedEvent} variant="contained" startIcon={<SaveIcon />} >Αποθήκευση</Button>
        </DialogActions>
      </Dialog>
      {/* ======================================================== */}
    </Card>
  );
};

export default InteractiveCalendar;

/* // Παράδειγμα custom rendering (προαιρετικό)
function renderEventContent(eventInfo) {
  return (
    <>
      <b>{eventInfo.timeText}</b>
      <i>{eventInfo.event.title}</i>
      {eventInfo.event.extendedProps.event_type && 
        <Chip label={eventInfo.event.extendedProps.event_type} size="small" sx={{ml: 1}}/>
      }
    </>
  )
} */
