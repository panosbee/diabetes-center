import React, { useState, useEffect } from 'react';
import { List, ListItem, ListItemText, ListItemAvatar, Avatar, Typography, Box, CircularProgress, Paper } from '@mui/material';
import EventBusyIcon from '@mui/icons-material/EventBusy';
import { useNotify, useGetIdentity } from 'react-admin';
import { format, parseISO, isFuture } from 'date-fns';
import { el } from 'date-fns/locale'; // For Greek date formatting

export const UpcomingBookedAppointmentsList = ({ maxItems = 5 }) => {
    const [appointments, setAppointments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const notify = useNotify();
    const { data: identity, isLoading: identityLoading } = useGetIdentity();

    useEffect(() => {
        if (identityLoading) {
            // Still waiting for identity to load
            return;
        }
        if (!identity?.id) {
            // Identity loaded, but no ID found (e.g., user not fully authenticated or error)
            setLoading(false);
            // setError('User identity not found. Cannot fetch appointments.'); // Optional: set an error
            // notify('User identity not found.', { type: 'warning' });
            return;
        }

        const fetchAppointments = async () => {
            setLoading(true);
            setError(null);
            const token = localStorage.getItem('access_token');
            if (!token) {
                notify('Authentication token not found.', { type: 'error' });
                setLoading(false);
                setError('Authentication required.');
                return;
            }

            // const now = new Date().toISOString(); // Not needed for the new endpoint
            
            // const params = new URLSearchParams({ // Not needed for the new endpoint
            //     creator_id: identity.id, 
            //     event_type: 'booked_appointment',
            //     start_gte: now, 
            //     _sort: 'start', 
            //     _order: 'ASC',
            //     _limit: maxItems.toString(),
            // });

            try {
                // Corrected URL according to instructions
                const response = await fetch(`${import.meta.env.VITE_API_URL}/api/calendar/upcoming_booked_appointments?limit=${maxItems}&days_ahead=30`, {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Accept': 'application/json', // Added Accept header as per instructions
                    },
                });

                if (!response.ok) {
                    const errData = await response.json().catch(() => ({ message: 'Failed to fetch appointments' }));
                    throw new Error(errData.error || errData.message || `HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                
                const mappedAppointments = data
                    .map(event => ({
                        id: event.id || event._id,
                        title: event.title,
                        start: event.start || event.start_time,
                        patientName: event.extendedProps?.patient_name || event.patient_name || 'Άγνωστος Ασθενής',
                    }))
                    .filter(event => event.start && isFuture(parseISO(event.start))); 

                setAppointments(mappedAppointments.slice(0, maxItems));
            } catch (e) {
                console.error("Failed to fetch upcoming appointments:", e);
                setError(e.message);
                notify(`Error fetching appointments: ${e.message}`, { type: 'error' });
            } finally {
                setLoading(false);
            }
        };

        fetchAppointments();

    }, [identity, identityLoading, notify, maxItems]);

    if (loading) {
        return (
            <Paper elevation={2} sx={{ p: 2, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100px' }}>
                <CircularProgress />
            </Paper>
        );
    }

    if (error) {
        return (
            <Paper elevation={2} sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Προσεχή Ραντεβού</Typography>
                <Typography color="error">Σφάλμα φόρτωσης ραντεβού: {error}</Typography>
            </Paper>
        );
    }

    if (appointments.length === 0) {
        return (
            <Paper elevation={2} sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Προσεχή Ραντεβού</Typography>
                <Typography variant="body2">Δεν υπάρχουν προσεχή προγραμματισμένα ραντεβού.</Typography>
            </Paper>
        );
    }

    return (
        <Paper elevation={2} sx={{ p: 1 }}>
             <Typography variant="h6" gutterBottom sx={{pl:1, pt:1}}>Προσεχή Ραντεβού</Typography>
            <List dense>
                {appointments.map((event) => (
                    <ListItem key={event.id} sx={{pt:0, pb:0}}>
                        <ListItemAvatar>
                            <Avatar sx={{ bgcolor: 'secondary.main', width: 32, height: 32 }}> {/* Smaller Avatar */}
                                <EventBusyIcon fontSize="small"/>
                            </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                            primaryTypographyProps={{ variant: 'subtitle2', noWrap: true }}
                            secondaryTypographyProps={{ variant: 'caption' }}
                            primary={event.title || `Ραντεβού με ${event.patientName}`}
                            secondary={
                                <>
                                    <Typography component="span" variant="caption" color="text.primary" sx={{ display: 'block' }}>
                                        {event.patientName}
                                    </Typography>
                                    {event.start ? format(parseISO(event.start), 'Pp', { locale: el }) : ' Άγνωστη ημερομηνία'}
                                </>
                            }
                        />
                    </ListItem>
                ))}
            </List>
        </Paper>
    );
};
