// diabetes_frontend/src/components/UpcomingBookedAppointmentsList.jsx

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
import { Schedule as ScheduleIcon } from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';
// Import useNotify if you want to use React Admin's notification system for errors
// import { useNotify } from 'react-admin';

const UpcomingBookedAppointmentsList = () => {
  const [appointments, setAppointments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const theme = useTheme();
  // const notify = useNotify(); // Uncomment if using useNotify

  useEffect(() => {
    const fetchAppointments = async () => {
      setIsLoading(true);
      setError(null);
      // Assuming this runs in the doctor panel context
      const token = localStorage.getItem('access_token'); 

      if (!token) {
        console.error("[UpcomingAppointments] Auth token not found.");
        setError("Δεν βρέθηκε token αυθεντικοποίησης. Απαιτείται σύνδεση.");
        setIsLoading(false);
        return;
      }

      try {
        // Call the specific backend endpoint
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/calendar/upcoming_booked_appointments?limit=5&days_ahead=30`, {
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
          } catch (e) {
              // Ignore if response is not JSON
          }
          throw new Error(errorMsg);
        }

        const data = await response.json();
        // Ensure data is an array before setting state
        if (Array.isArray(data)) {
            setAppointments(data);
        } else {
            console.error("[UpcomingAppointments] Received non-array data:", data);
            throw new Error("Λήφθηκαν μη έγκυρα δεδομένα από τον διακομιστή.");
        }

      } catch (e) {
        console.error("Error fetching upcoming booked appointments:", e);
        setError(e.message || "Προέκυψε σφάλμα κατά τη φόρτωση των ραντεβού.");
        // notify(`Σφάλμα: ${e.message || "Failed to load appointments"}`, { type: 'error' }); // Uncomment if using useNotify
      } finally {
        setIsLoading(false);
      }
    };

    fetchAppointments();
    // Setup interval for refetching or use SocketIO events in the future if needed
    // const intervalId = setInterval(fetchAppointments, 60000); // Refetch every minute
    // return () => clearInterval(intervalId); // Cleanup interval

  }, []); // Empty dependency array means run once on mount


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

  if (appointments.length === 0) {
    return (
      <Typography variant="body2" color="textSecondary" sx={{ p: 2, textAlign: 'center' }}>
        Δεν υπάρχουν επερχόμενα κλεισμένα ραντεβού.
      </Typography>
    );
  }

  return (
    <List dense sx={{ paddingTop: 0 }}>
      {appointments.map(appt => (
        <Paper
          key={appt.id} // Use the unique ID from the data
          elevation={0}
          sx={{
            mb: 1.5,
            p: 1.5,
            borderRadius: 2,
            borderLeft: `4px solid ${theme.palette.primary.main}`,
            transition: 'all 0.2s ease-in-out',
            '&:hover': { 
                boxShadow: theme.shadows[3],
                transform: 'translateX(2px)' 
            }
          }}
        >
          <ListItem disablePadding>
            <ListItemAvatar sx={{ minWidth: 'auto', mr: 1.5 }}>
              <Avatar sx={{ bgcolor: theme.palette.primary.light, color: theme.palette.primary.main, width: 36, height: 36 }}>
                <ScheduleIcon fontSize="small" />
              </Avatar>
            </ListItemAvatar>
            <ListItemText
              primaryTypographyProps={{ fontWeight: 500, variant: 'body2', color: 'text.primary' }}
              secondaryTypographyProps={{ variant: 'caption', color: 'text.secondary' }}
              // Use patient_name directly from backend data
              primary={appt.patient_name || 'Άγνωστος Ασθενής'} 
              secondary={
                `${new Date(appt.start).toLocaleDateString('el-GR', { weekday: 'short', day: 'numeric', month: 'short' })} @ ${new Date(appt.start).toLocaleTimeString('el-GR', { hour: '2-digit', minute: '2-digit' })}` +
                (appt.title && appt.title !== `Ραντεβού με ${appt.patient_name}` ? ` (${appt.title})` : '') // Show original title if different
               } 
            />
            {/* You could add an action button here if needed, e.g., to view details */}
            {/* <IconButton edge="end" aria-label="details"> <InfoIcon /> </IconButton> */}
          </ListItem>
        </Paper>
      ))}
    </List>
  );
};

// Make sure to export the component
export { UpcomingBookedAppointmentsList }; 
// or export default UpcomingBookedAppointmentsList; depending on your import style in Dashboard.jsx