import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, Typography, Box, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Button, TextField, Chip, Select, MenuItem, FormControl, InputLabel, IconButton } from '@mui/material';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
// --- Εικονίδια --- 
import EventAvailableIcon from '@mui/icons-material/EventAvailable'; // Για slots
import EventBusyIcon from '@mui/icons-material/EventBusy'; // Για booked appointments
import MedicationIcon from '@mui/icons-material/Medication'; // Για medication reminder
import RestaurantIcon from '@mui/icons-material/Restaurant'; // Για meal log
import FitnessCenterIcon from '@mui/icons-material/FitnessCenter'; // Για exercise log
import AssignmentIcon from '@mui/icons-material/Assignment'; // Για tasks/instructions
import SpeakerNotesIcon from '@mui/icons-material/SpeakerNotes'; // Για notes
import MonitorWeightIcon from '@mui/icons-material/MonitorWeight'; // Για measurement reminder
import EditIcon from '@mui/icons-material/Edit';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleIcon from '@mui/icons-material/CheckCircle'; // Για booking
import TodayIcon from '@mui/icons-material/Today'; // Γενικό εικονίδιο

// Imports για FullCalendar
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid'; 
import timeGridPlugin from '@fullcalendar/timegrid'; 
import listPlugin from '@fullcalendar/list'; 
import interactionPlugin from '@fullcalendar/interaction'; 

// --- React Admin hooks (αν χρησιμοποιούνται στο PWA) ή απλό fetch ---
// Προς το παρόν θα χρησιμοποιήσουμε fetch με token
// import { useNotify, useGetIdentity } from '../hooks/useAuth'; // Παράδειγμα custom hook <-- ΑΦΑΙΡΕΣΗ
import { authProvider } from '../authProvider'; // <-- ΕΙΣΑΓΩΓΗ AUTH PROVIDER

// --- Custom rendering για τα events ---
function renderEventContent(eventInfo, doctorsInfo) { // Το doctorsInfo δεν χρησιμοποιείται εδώ, μπορείτε να το αφαιρέσετε αν δεν προβλέπεται για μελλοντική χρήση
  // === ΠΡΟΣΘΗΚΗ ΓΙΑ DEBUGGING ===
  // Κάνουμε log το eventInfo.event για να δούμε τι ακριβώς λαμβάνει η συνάρτηση για κάθε event
  // Χρησιμοποιούμε JSON.parse(JSON.stringify(...)) για να πάρουμε ένα "καθαρό" αντίγραφο του αντικειμένου για logging, αποφεύγοντας κυκλικές αναφορές ή proxies.
  try {
    console.log('[PatientCalendar] renderEventContent - START PROCESSING EVENT:', JSON.parse(JSON.stringify(eventInfo.event)));
    if (eventInfo.event.extendedProps) {
      console.log('[PatientCalendar] renderEventContent - eventInfo.event.extendedProps:', JSON.parse(JSON.stringify(eventInfo.event.extendedProps)));
      console.log(`[PatientCalendar] renderEventContent - Event Type: ${eventInfo.event.extendedProps.event_type}, Title: ${eventInfo.event.title}`);
    } else {
      console.warn('[PatientCalendar] renderEventContent - eventInfo.event.extendedProps is undefined for event:', eventInfo.event.title, eventInfo.event.id);
    }
  } catch (e) {
    console.error('[PatientCalendar] renderEventContent - Error logging eventInfo.event:', e);
    console.log('[PatientCalendar] renderEventContent - Fallback log eventInfo.event.title:', eventInfo.event.title);
  }
  // === ΤΕΛΟΣ ΠΡΟΣΘΗΚΗΣ ΓΙΑ DEBUGGING ===

  const eventType = eventInfo.event.extendedProps?.event_type; // Προσθήκη optional chaining για ασφάλεια
  const creatorId = eventInfo.event.extendedProps?.creator_id;
  const doctorName = eventInfo.event.extendedProps?.doctor_name;

  let icon = <TodayIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />; // Default
  
  if (eventType === 'appointment_slot') icon = <EventAvailableIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle', color: 'grey.500' }} />;
  else if (eventType === 'booked_appointment') icon = <EventBusyIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle', color: 'primary.main' }} />;
  else if (eventType === 'medication_reminder') icon = <MedicationIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle', color: 'warning.main' }} />;
  else if (eventType === 'measurement_reminder') icon = <MonitorWeightIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle', color: 'secondary.main' }} />;
  else if (eventType === 'meal_log') icon = <RestaurantIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle', color: 'success.main' }} />;
  else if (eventType === 'exercise_log') icon = <FitnessCenterIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle', color: 'info.main' }} />;
  else if (eventType === 'doctor_instruction') icon = <AssignmentIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />
  else if (eventType === 'patient_note') icon = <SpeakerNotesIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />;
  else if (eventType === 'symptom_log') icon = <SpeakerNotesIcon sx={{ fontSize: '0.9em', mr: 0.5, verticalAlign: 'middle' }} />; // Ίδιο εικονίδιο προς το παρόν
  
  return (
    <Box sx={{ overflow: 'hidden', fontSize: '0.8em', p: '2px', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
             {icon} 
             <Typography variant="body2" component="span" sx={{ fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                 {eventInfo.event.title}
             </Typography>
        </Box>
        {/* Εμφάνιση ώρας πιο διακριτικά */}
        <Typography variant="caption" sx={{ display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', opacity: 0.8, pl: '22px' }}>
              {eventInfo.timeText}
        </Typography>
        {/* Εμφάνιση ονόματος γιατρού για booked appointments ΚΑΙ appointment slots */}
        {(eventType === 'booked_appointment' || eventType === 'appointment_slot') && doctorName && (
            <Typography variant="caption" sx={{ display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', opacity: 0.8, pl: '22px' }}>
                {eventType === 'appointment_slot' ? `Διαθέσιμο: ${doctorName}` : doctorName}
            </Typography>
        )}
    </Box>
  )
}
// ---------------------------------------------------

const PatientCalendar = (props) => {
  const [createDialogOpen, setCreateDialogOpen] = useState(false); // Dialog δημιουργίας Log/Note
  const [bookDialogOpen, setBookDialogOpen] = useState(false); // Dialog κλεισίματος ραντεβού
  const [viewDialogOpen, setViewDialogOpen] = useState(false); // Dialog προβολής λεπτομερειών
  
  const [selectedDateInfo, setSelectedDateInfo] = useState(null); // Για δημιουργία
  const [selectedSlotInfo, setSelectedSlotInfo] = useState(null); // Για booking
  const [selectedEvent, setSelectedEvent] = useState(null); // Για προβολή/διαγραφή

  const [eventTitle, setEventTitle] = useState(''); 
  const [eventType, setEventType] = useState('meal_log'); // Default για ασθενή
  const [eventDetails, setEventDetails] = useState(''); // Πεδίο για λεπτομέρειες log/note

  const calendarRef = useRef(null); 
  // const notify = useNotify(); <-- ΑΦΑΙΡΕΣΗ
  const [identity, setIdentity] = useState(null); // <-- ΠΡΟΣΘΗΚΗ STATE ΓΙΑ IDENTITY

  // --- Λήψη identity από authProvider --- 
  useEffect(() => {
      const fetchIdentity = async () => {
          try {
              const id = await authProvider.getIdentity();
              setIdentity(id);
          } catch (error) {
              console.error("Failed to get identity", error);
              // Προαιρετικά: alert('Failed to get user identity');
          }
      };
      fetchIdentity();
  }, []); // Τρέχει μια φορά κατά το mount
  // -------------------------------------

  // Handler για όταν ο χρήστης επιλέγει ένα χρονικό διάστημα (για δημιουργία log/note)
  const handleSelect = (selectInfo) => {
    console.log('Patient selected date range:', selectInfo);
    setSelectedDateInfo(selectInfo);
    setEventType('meal_log'); // Προεπιλογή
    setEventTitle(''); // Καθαρισμός τίτλου
    setEventDetails(''); // Καθαρισμός details
    setCreateDialogOpen(true);
  };

  // Handler για κλικ πάνω σε ένα event
  const handleEventClick = (clickInfo) => {
    console.log('Patient clicked event:', clickInfo.event);
    const event = clickInfo.event;
    
    if (event.extendedProps.event_type === 'appointment_slot') {
        // Αν κάνει κλικ σε διαθέσιμο slot, άνοιξε dialog για booking
        setSelectedSlotInfo(event);
        setBookDialogOpen(true);
    } else {
        // Για όλα τα άλλα events, άνοιξε dialog προβολής
        setSelectedEvent(event);
        setViewDialogOpen(true);
    }
  };

  // --- Handlers για Dialogs ---
  const handleCloseCreateDialog = () => {
    setCreateDialogOpen(false);
    setSelectedDateInfo(null);
    if (calendarRef.current) calendarRef.current.getApi().unselect();
  };
  
  const handleCloseBookDialog = () => {
    setBookDialogOpen(false);
    setSelectedSlotInfo(null);
  };
  
  const handleCloseViewDialog = () => {
    setViewDialogOpen(false);
    setSelectedEvent(null);
  };
  // -----------------------------

  // --- Δημιουργία Log/Note Ασθενή ---
  const handleCreatePatientEvent = () => {
    if (!selectedDateInfo || !eventType) return;

    const token = localStorage.getItem('patient_access_token');
    if (!token) { alert('Authentication Error'); return; }

    let title = eventTitle;
    // Αυτόματος τίτλος για logs αν δεν δόθηκε
    if (!title) {
      if (eventType === 'meal_log') title = 'Καταγραφή Γεύματος';
      else if (eventType === 'exercise_log') title = 'Καταγραφή Άσκησης';
      else if (eventType === 'symptom_log') title = 'Καταγραφή Συμπτώματος';
      else if (eventType === 'patient_note') title = 'Σημείωση Ασθενή';
      else { alert('Παρακαλώ δώστε έναν τίτλο'); return; }
    }

    // === Εξασφάλιση σωστού visibility για logs/notes ασθενή ===
    const newEventData = {
      event_type: eventType,
      title: title,
      start: selectedDateInfo.start.toISOString(),
      end: selectedDateInfo.end.toISOString(),
      allDay: selectedDateInfo.allDay,
      details: { notes: eventDetails },
      visibility: 'shared_with_doctor'
    };

    const url = `${import.meta.env.VITE_API_URL}/api/calendar/events`;

    fetch(url, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(newEventData)
    })
      .then(response => response.ok ? response.json() : response.json().then(err => { throw new Error(err.error || 'Failed to create event') }))
      .then(createdEvent => {
        console.log("Patient event created:", createdEvent);
        if (calendarRef.current) calendarRef.current.getApi().refetchEvents();
        alert('Η καταγραφή δημιουργήθηκε');
        handleCloseCreateDialog();
      })
      .catch(error => {
        console.error('Error creating patient event:', error);
        alert(`Σφάλμα: ${error.message}`);
        handleCloseCreateDialog();
      });
  };

  // --- Κλείσιμο Ραντεβού (Booking) ---
  const handleBookAppointment = () => {
    if (!selectedSlotInfo) return;
    
    const token = localStorage.getItem('patient_access_token');
    if (!token) { alert('Authentication Error'); return; }

    const slotId = selectedSlotInfo.id;
    const url = `${import.meta.env.VITE_API_URL}/api/calendar/events/${slotId}/book`;

    fetch(url, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(response => response.ok ? response.json() : response.json().then(err => { throw new Error(err.error || 'Failed to book appointment') }))
    .then(bookedEvent => {
        console.log("Appointment booked:", bookedEvent);
        if (calendarRef.current) calendarRef.current.getApi().refetchEvents();
        // notify('Το ραντεβού κλείστηκε επιτυχώς!', { type: 'success' });
        alert('Το ραντεβού κλείστηκε επιτυχώς!'); // <-- ΑΛΛΑΓΗ ΣΕ ALERT
        handleCloseBookDialog();
    })
    .catch(error => {
        console.error('Error booking appointment:', error);
        // notify(`Σφάλμα κλεισίματος ραντεβού: ${error.message}`, { type: 'error' });
        alert(`Σφάλμα κλεισίματος ραντεβού: ${error.message}`); // <-- ΑΛΛΑΓΗ ΣΕ ALERT
        handleCloseBookDialog();
    });
  };

  // --- Διαγραφή Γεγονότος Ασθενή (Log/Note) ---
  const handleDeletePatientEvent = () => {
      if (!selectedEvent) return;
      
      // Έλεγχος αν ο ασθενής μπορεί να το διαγράψει (πρέπει να είναι ο owner)
      if (selectedEvent.extendedProps.editable_by !== 'owner' || selectedEvent.extendedProps.user_id !== identity?.id) {
           // notify('Δεν έχετε δικαίωμα διαγραφής αυτού του γεγονότος.', {type: 'warning'});
           alert('Δεν έχετε δικαίωμα διαγραφής αυτού του γεγονότος.'); // <-- ΑΛΛΑΓΗ ΣΕ ALERT
           handleCloseViewDialog();
           return;
      }

      if (confirm(`Είστε σίγουροι ότι θέλετε να διαγράψετε το γεγονός "${selectedEvent.title}";`)) {
          const token = localStorage.getItem('patient_access_token');
          if (!token) { alert('Authentication Error'); return; }
          
          const url = `${import.meta.env.VITE_API_URL}/api/calendar/events/${selectedEvent.id}`;
          fetch(url, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` }})
              .then(response => {
                  if (!response.ok) { return response.json().then(err => { throw new Error(err.error || 'Failed delete') }); }
                  return null;
              })
              .then(() => {
                  // notify('Το γεγονός διαγράφηκε', { type: 'info' });
                  alert('Το γεγονός διαγράφηκε'); // <-- ΑΛΛΑΓΗ ΣΕ ALERT
                  if (calendarRef.current) calendarRef.current.getApi().refetchEvents();
                  handleCloseViewDialog(); // Κλείσιμο του dialog μετά τη διαγραφή
              })
              .catch(error => {
                  // notify(`Σφάλμα διαγραφής: ${error.message}`, { type: 'error' });
                  alert(`Σφάλμα διαγραφής: ${error.message}`); // <-- ΑΛΛΑΓΗ ΣΕ ALERT
                  handleCloseViewDialog(); 
              });
       }
  };

  // --- Fetch Events (Παρόμοιο με του Γιατρού, αλλά το backend φιλτράρει) ---
  // === ΑΝΤΙΚΑΤΑΣΤΑΣΗ fetchEvents με mapping ===
  const fetchEvents = (fetchInfo, successCallback, failureCallback) => {
    const token = localStorage.getItem('patient_access_token');
    if (!token) {
      console.error("[PatientCalendar] Authentication token not found.");
      failureCallback('Authentication token not found');
      return;
    }

    const url = `${import.meta.env.VITE_API_URL}/api/calendar/events?start=${fetchInfo.startStr}&end=${fetchInfo.endStr}`;
    console.log(`[PatientCalendar] Attempting to fetch events from: ${url}`);
    
    fetch(url, { headers: { 'Authorization': `Bearer ${token}`, 'Accept': 'application/json' } })
      .then(response => {
        if (!response.ok) {
          return response.text().then(text => { 
            let errorMsg = `Server error: ${response.status}`;
            try {
              const errJson = JSON.parse(text);
              errorMsg = errJson.error || errJson.message || text;
            } catch (e) {
              // text was not JSON or error field not found
              if (text) errorMsg = text;
            }
            throw new Error(errorMsg);
          });
        }
        return response.json();
      })
      .then(data => {
        if (!Array.isArray(data)) {
          console.error('[PatientCalendar] Data received is not an array:', data);
          throw new Error('Invalid data format from server.');
        }
        // === ΒΕΛΤΙΩΜΕΝΟ Mapping για FullCalendar ===
        const mapped = data.map(ev => {
          // Το backend (με τις προηγούμενες διορθώσεις) θα πρέπει να στέλνει:
          // id, title, start, end, allDay, και ένα αντικείμενο extendedProps.
          
          // Εξασφάλιση ότι το extendedProps είναι αντικείμενο, ακόμα κι αν το backend στείλει null/undefined
          const backendExtendedProps = (typeof ev.extendedProps === 'object' && ev.extendedProps !== null) 
                                       ? ev.extendedProps 
                                       : {};

          return {
            id: ev.id, // Απευθείας χρήση του id από το backend
            title: ev.title,
            start: ev.start, // Απευθείας χρήση του start από το backend
            end: ev.end,     // Απευθείας χρήση του end από το backend
            allDay: ev.allDay || false, // Default σε false αν δεν ορίζεται
            extendedProps: {
              // Προτεραιότητα στις ιδιότητες από το backendExtendedProps
              ...backendExtendedProps,
              // Ρητή ανάθεση κρίσιμων πεδίων για σιγουριά,
              // αντλώντας από το backendExtendedProps ή από το κυρίως αντικείμενο ev αν χρειαστεί
              event_type: backendExtendedProps.event_type || ev.event_type,
              creator_id: backendExtendedProps.creator_id || ev.creator_id,
              user_id: backendExtendedProps.user_id || ev.user_id,
              status: backendExtendedProps.status || ev.status,
              visibility: backendExtendedProps.visibility || ev.visibility,
              details: backendExtendedProps.details || ev.details || {}, // Εξασφάλιση ότι είναι αντικείμενο
              doctor_name: backendExtendedProps.doctor_name || ev.doctor_name,
              patient_name: backendExtendedProps.patient_name || ev.patient_name,
              // Προσθέτουμε το editable_by εδώ, αν το backend το στέλνει στο extendedProps
              editable_by: backendExtendedProps.editable_by || ev.editable_by 
            }
          };
        });
        // console.log('[PatientCalendar] Original data from backend:', data); // Για debugging
        console.log('[PatientCalendar] Mapped events for FullCalendar:', mapped);
        
        // Διόρθωση του φίλτρου για τα appointment slots
        const appointmentSlots = mapped.filter(event => event.extendedProps?.event_type === 'appointment_slot');
        console.log('[PatientCalendar] Filtered Appointment slots:', appointmentSlots);
        
        successCallback(mapped);
      })
      .catch(error => { 
        console.error('[PatientCalendar] Error fetching or processing events:', error);
        alert(`Σφάλμα φόρτωσης ημερολογίου: ${error.message}`);
        failureCallback(error);
      });
  };
  // === ΤΕΛΟΣ ΑΝΤΙΚΑΤΑΣΤΑΣΗΣ ===

  return (
    <Card sx={{ height: 'calc(100vh - 120px)', borderRadius: 3, display: 'flex', flexDirection: 'column' }}> {/* Προσαρμογή ύψους */}
      <CardContent sx={{ display: 'flex', flexDirection: 'column', flexGrow: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
           <CalendarMonthIcon sx={{ mr: 1 }} />
           <Typography variant="h6" fontWeight={600}>
             Το Ημερολόγιό μου
           </Typography>
        </Box>
        <Box sx={{ mb: 2 }}>
          <Chip 
            icon={<EventAvailableIcon />} 
            label="Διαθέσιμα slots ραντεβού - Κάντε κλικ για κράτηση" 
            size="small" 
            color="default"
            sx={{ mr: 1, mb: 1 }}
          />
          <Chip 
            icon={<EventBusyIcon />} 
            label="Επιβεβαιωμένα ραντεβού" 
            size="small" 
            color="primary"
            sx={{ mr: 1, mb: 1 }}
          />
        </Box>
        <Box sx={{ flexGrow: 1, overflow: 'hidden' }}> {/* Container για το ημερολόγιο */}
          <FullCalendar
            ref={calendarRef}
            plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
            }}
            initialView="timeGridWeek" 
            editable={false} // Ο ασθενής δεν κάνει drag/drop events (εκτός ίσως από τα δικά του;)
            selectable={true} // Επιτρέπει επιλογή για δημιουργία log/note
            selectMirror={true}
            dayMaxEvents={true}
            weekends={true}
            events={fetchEvents}      
            select={handleSelect}     
            eventClick={handleEventClick} 
            // eventDrop={handleEventDrop}   // Απενεργοποιημένο για ασθενή
            // eventResize={handleEventResize} // Απενεργοποιημένο για ασθενή
            timeZone='Europe/Athens' 
            eventContent={renderEventContent} 
            firstDay={1} 
            // locale='el' 
            height="100%" // Να πιάνει όλο το διαθέσιμο ύψος
            buttonText={{ // Ελληνικά labels για τα κουμπιά
                 today:    'Σήμερα',
                 month:    'Μήνας',
                 week:     'Εβδομάδα',
                 day:      'Ημέρα',
                 list:     'Λίστα'
            }}
            allDayText='Ολοήμερο'
            slotDuration='00:15:00' // Διάρκεια slot
            slotLabelInterval='01:00' // Εμφάνιση ώρας ανά ώρα
            slotLabelFormat={{ // Μορφή ώρας
                 hour: '2-digit',
                 minute: '2-digit',
                 omitZeroMinute: false,
                 meridiem: false, // 'short' αν θέλουμε πμ/μμ
                 hour12: false
            }}
             views={{ // Προσαρμογή ωρών προβολής
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
      
      {/* Dialog για Δημιουργία Log/Note Ασθενή */}
      <Dialog open={createDialogOpen} onClose={handleCloseCreateDialog} fullWidth maxWidth="xs">
        <DialogTitle>Νέα Καταγραφή</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Επιλεγμένο διάστημα: {selectedDateInfo?.start.toLocaleString()} - {selectedDateInfo?.end.toLocaleString()}
          </DialogContentText>
          
          <FormControl fullWidth margin="dense" variant="standard">
            <InputLabel id="event-type-patient-label">Τύπος Καταγραφής</InputLabel>
            <Select
              labelId="event-type-patient-label"
              id="event-type-patient-select"
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              label="Τύπος Καταγραφής"
            >
              <MenuItem value="meal_log">Καταγραφή Γεύματος</MenuItem>
              <MenuItem value="exercise_log">Καταγραφή Άσκησης</MenuItem>
              <MenuItem value="symptom_log">Καταγραφή Συμπτώματος</MenuItem>
              <MenuItem value="patient_note">Σημείωση</MenuItem>
            </Select>
          </FormControl>

          <TextField
            margin="dense" id="event-title-patient" label="Τίτλος (Προαιρετικά)"
            type="text" fullWidth variant="standard" value={eventTitle}
            onChange={(e) => setEventTitle(e.target.value)}
          />
          <TextField
            margin="dense" id="event-details-patient" label="Λεπτομέρειες / Σημειώσεις"
            type="text" fullWidth variant="standard" multiline rows={3}
            value={eventDetails} onChange={(e) => setEventDetails(e.target.value)}
          />
          
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseCreateDialog}>Άκυρο</Button>
          <Button onClick={handleCreatePatientEvent} variant="contained">Δημιουργία</Button>
        </DialogActions>
      </Dialog>

       {/* Dialog για Επιβεβαίωση Booking */}
      <Dialog open={bookDialogOpen} onClose={handleCloseBookDialog} fullWidth maxWidth="xs">
        <DialogTitle>Κλείσιμο Ραντεβού</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Θέλετε να κλείσετε το διαθέσιμο ραντεβού;
          </DialogContentText>
           {selectedSlotInfo && (
               <Box sx={{mt: 2, p: 1, border: '1px dashed grey', borderRadius: 1}}>
                   <Typography variant="body1"><b>Γιατρός:</b> {selectedSlotInfo.extendedProps.doctor_name || 'Μη διαθέσιμο όνομα'}</Typography>
                   <Typography variant="body1"><b>Έναρξη:</b> {selectedSlotInfo.start?.toLocaleString()}</Typography>
                   <Typography variant="body1"><b>Λήξη:</b> {selectedSlotInfo.end?.toLocaleString()}</Typography>
               </Box>
           )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseBookDialog}>Άκυρο</Button>
          <Button onClick={handleBookAppointment} variant="contained" startIcon={<CheckCircleIcon />}>Επιβεβαίωση</Button>
        </DialogActions>
      </Dialog>

      {/* Dialog για Προβολή Λεπτομερειών Γεγονότος */}
      <Dialog open={viewDialogOpen} onClose={handleCloseViewDialog} fullWidth maxWidth="sm">
         <DialogTitle>
           Λεπτομέρειες Γεγονότος
            <IconButton aria-label="close" onClick={handleCloseViewDialog} sx={{ position: 'absolute', right: 8, top: 8 }}>
                <CloseIcon />
            </IconButton>
         </DialogTitle>
         <DialogContent dividers>
           {selectedEvent ? (
             <Box>
               <Typography variant="h6" gutterBottom>{selectedEvent.title}</Typography>
               <Chip 
                 icon={renderEventContent({ event: selectedEvent }, {}).props.children[0].props.children[0]} 
                 label={selectedEvent.extendedProps.event_type || 'Γεγονός'}
                 size="small" sx={{ mb: 2 }}
                 color={selectedEvent.extendedProps.event_type === 'booked_appointment' ? 'primary' : 
                        selectedEvent.extendedProps.event_type === 'medication_reminder' ? 'warning' :
                        selectedEvent.extendedProps.event_type === 'measurement_reminder' ? 'secondary' :
                        selectedEvent.extendedProps.event_type.includes('_log') ? 'success' : 'default'
                       }
               />
               <Typography variant="body1" gutterBottom>
                 <b>Έναρξη:</b> {selectedEvent.start?.toLocaleString() || 'N/A'}
               </Typography>
               <Typography variant="body1" gutterBottom>
                 <b>Λήξη:</b> {selectedEvent.end?.toLocaleString() || (selectedEvent.allDay ? '(Ολοήμερο)' : 'N/A')}
               </Typography>
               
               {/* Όνομα Γιατρού για booked appointments */}
               {selectedEvent.extendedProps.event_type === 'booked_appointment' && selectedEvent.extendedProps.doctor_name && (
                  <Typography variant="body1" gutterBottom>
                     <b>Γιατρός:</b> {selectedEvent.extendedProps.doctor_name}
                   </Typography>
               )}

               {/* Details */}
               {selectedEvent.extendedProps.details && Object.keys(selectedEvent.extendedProps.details).length > 0 && (
                   <Box mt={2} mb={1}>
                       <Typography variant="subtitle2" gutterBottom>Λεπτομέρειες:</Typography>
                       {Object.entries(selectedEvent.extendedProps.details).map(([key, value]) => (
                           <Typography key={key} variant="body2" sx={{whiteSpace: 'pre-wrap'}}>- {key}: {value || '-'}</Typography>
                       ))}
                   </Box>
               )}
               
             </Box>
           ) : ( <Typography>Φόρτωση...</Typography> )}
         </DialogContent>
         <DialogActions>
            {/* Κουμπί Διαγραφής (αν επιτρέπεται) */}
            {selectedEvent && selectedEvent.extendedProps.editable_by === 'owner' && selectedEvent.extendedProps.user_id === identity?.id && (
                 <Button onClick={handleDeletePatientEvent} color="error">Διαγραφή Καταγραφής</Button>
            )}
           <Button onClick={handleCloseViewDialog}>Κλείσιμο</Button>
         </DialogActions>
       </Dialog>
    </Card>
  );
};

export default PatientCalendar;
