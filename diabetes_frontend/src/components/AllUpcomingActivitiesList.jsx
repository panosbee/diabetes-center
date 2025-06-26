// diabetes_frontend/src/components/AllUpcomingActivitiesList.jsx

import React, { useState, useEffect } from 'react';
import { 
    Typography, 
    List, 
    ListItem, 
    ListItemText, 
    ListItemAvatar, 
    Avatar, 
    CircularProgress, 
    Paper, 
    Box 
} from '@mui/material';
import {
  Assignment as AssignmentIcon,
  Restaurant as RestaurantIcon,
  FitnessCenter as FitnessCenterIcon,
  SpeakerNotes as SpeakerNotesIcon,
  Medication as MedicationIcon,
  MonitorWeight as MonitorWeightIcon,
  EventBusy as EventBusyIcon, // For booked appointments also shown here
  Today as DefaultIcon
} from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';
// import { useNotify } from 'react-admin'; // Uncomment if needed for error notifications

// Helper function to get an appropriate icon based on event type
const getActivityIcon = (eventType) => {
    switch (eventType) {
      case 'personal_task': return <AssignmentIcon fontSize="small" />;
      case 'doctor_instruction': return <AssignmentIcon fontSize="small" />;
      case 'meal_log': return <RestaurantIcon fontSize="small" />;
      case 'exercise_log': return <FitnessCenterIcon fontSize="small" />;
      case 'symptom_log': return <SpeakerNotesIcon fontSize="small" />;
      case 'patient_note': return <SpeakerNotesIcon fontSize="small" />;
      case 'medication_reminder': return <MedicationIcon fontSize="small" />;
      case 'measurement_reminder': return <MonitorWeightIcon fontSize="small" />;
      case 'booked_appointment': return <EventBusyIcon fontSize="small" />; 
      default: return <DefaultIcon fontSize="small" />;
    }
  };

const AllUpcomingActivitiesList = () => {
  const [activities, setActivities] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const theme = useTheme();
  // const notify = useNotify();

  useEffect(() => {
    const fetchActivities = async () => {
      setIsLoading(true);
      setError(null);
      // Assuming this runs in the doctor panel context
      const token = localStorage.getItem('access_token'); 

      if (!token) {
        console.error("[AllActivities] Auth token not found.");
        setError("Δεν βρέθηκε token αυθεντικοποίησης. Απαιτείται σύνδεση.");
        setIsLoading(false);
        return;
      }

      try {
        // Call the specific backend endpoint
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/calendar/all_upcoming_activities?limit=7&days_ahead=7`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json',
          }
        });

        if (!response.ok) {
          let errorMsg = `HTTP error! status: ${response.status}`;
          try {
              const errData = await response.json();
              errorMsg = errData.error || errData.message || errorMsg;
          } catch (e) { /* Ignore if response not JSON */ }
          throw new Error(errorMsg);
        }

        const data = await response.json();
        if (Array.isArray(data)) {
            setActivities(data);
        } else {
            console.error("[AllActivities] Received non-array data:", data);
            throw new Error("Λήφθηκαν μη έγκυρα δεδομένα από τον διακομιστή.");
        }

      } catch (e) {
        console.error("Error fetching all upcoming activities:", e);
        setError(e.message || "Προέκυψε σφάλμα κατά τη φόρτωση των δραστηριοτήτων.");
        // notify(`Σφάλμα: ${e.message || "Failed to load activities"}`, { type: 'error' });
      } finally {
        setIsLoading(false);
      }
    };

    fetchActivities();
    // Optional: Set interval for refetching or use SocketIO later
    // const intervalId = setInterval(fetchActivities, 90000); // e.g., every 90 seconds
    // return () => clearInterval(intervalId);

  }, []); // Run once on mount

  // --- Render Logic ---

  if (isLoading) {
     return (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
             <CircularProgress size={24} />
        </Box>
    );
  }

  if (error) {
    return <Typography color="error" variant="body2" sx={{p: 2}}>Σφάλμα: {error}</Typography>;
  }

  if (activities.length === 0) {
    return (
      <Typography variant="body2" color="textSecondary" sx={{ p: 2, textAlign: 'center' }}>
        Δεν υπάρχουν άλλες επερχόμενες δραστηριότητες.
      </Typography>
    );
  }

  return (
    <List dense sx={{ paddingTop: 0 }}>
      {activities.map(activity => (
        <Paper
          key={activity.id}
          elevation={0}
          sx={{
            mb: 1.5,
            p: 1.5,
            borderRadius: 2,
            borderLeft: `4px solid ${theme.palette.secondary.main}`, // Different color
            transition: 'all 0.2s ease-in-out',
             '&:hover': { 
                boxShadow: theme.shadows[3],
                transform: 'translateX(2px)' 
            }
          }}
        >
          <ListItem disablePadding>
            <ListItemAvatar sx={{ minWidth: 'auto', mr: 1.5 }}>
              <Avatar sx={{ bgcolor: theme.palette.secondary.light, color: theme.palette.secondary.main, width: 36, height: 36 }}>
                {getActivityIcon(activity.event_type)}
              </Avatar>
            </ListItemAvatar>
            <ListItemText
              primaryTypographyProps={{ fontWeight: 500, variant: 'body2', color: 'text.primary' }}
              secondaryTypographyProps={{ variant: 'caption', color: 'text.secondary' }}
              primary={activity.title}
              secondary={
                `${new Date(activity.start).toLocaleDateString('el-GR', { weekday: 'short', day: 'numeric', month: 'short' })}, ${new Date(activity.start).toLocaleTimeString('el-GR', { hour: '2-digit', minute: '2-digit' })}` +
                // Show relevant person only if it exists and is different from the main title maybe
                (activity.relevant_person_name ? ` (${activity.relevant_person_name})` : '')
              }
            />
             {/* Optional: Add an action button */}
             {/* <IconButton edge="end" aria-label="details"> <InfoIcon /> </IconButton> */}
          </ListItem>
        </Paper>
      ))}
    </List>
  );
};

// Make sure to export the component correctly
export default AllUpcomingActivitiesList;