import React, { useState, useEffect, useCallback } from 'react';
import { 
    Box, 
    Typography, 
    List, 
    ListItem, 
    ListItemText, 
    CircularProgress, 
    Alert, 
    Paper,
    Divider,
    Chip,
    ListItemButton,
    ListItemIcon
} from '@mui/material';
import EventNoteIcon from '@mui/icons-material/EventNote';
import { getMySessions } from '../dataProvider';
import { authProvider } from '../authProvider';
import { format } from 'date-fns';
import { Link as RouterLink } from 'react-router-dom';

// Μετατροπή τύπου συνεδρίας σε αναγνώσιμη μορφή
const getSessionTypeLabel = (type) => {
    const typeMap = {
        'telemedicine': 'Τηλεϊατρική',
        'in_person': 'Με φυσική παρουσία',
        'data_review': 'Ανασκόπηση δεδομένων',
        'note': 'Σημείωση',
        'file_upload': 'Ανέβασμα Αρχείου' // Αν υπάρχει τέτοιος τύπος
    };
    return typeMap[type] || type || 'Άγνωστος Τύπος';
};

function SessionsList({ limit, isPreview = false }) {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const loadSessions = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const { data } = await getMySessions();
            setSessions(data || []); // Εξασφάλιση ότι είναι πάντα array
        } catch (err) {
            console.error("Error loading sessions:", err);
            authProvider.checkError(err).catch(() => {
                setError(err.message || 'Failed to load sessions.');
            });
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadSessions();
    }, [loadSessions]);

    if (loading) {
        return <Box sx={{ display: 'flex', justifyContent: 'center', p: isPreview ? 1 : 0 }}><CircularProgress size={isPreview ? 20 : 40} /></Box>;
    }

    if (error) {
        return <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>;
    }

    const displaySessions = limit ? sessions.slice(0, limit) : sessions;

    const content = (
        <>
            {displaySessions.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ p: isPreview ? 1 : 0 }}>Δεν υπάρχουν συνεδρίες.</Typography>
            ) : (
                <List disablePadding={isPreview} dense={true}>
                    {displaySessions.map((session, index) => (
                        <React.Fragment key={session.id}>
                            {isPreview ? (
                                <ListItemButton 
                                    component={RouterLink} 
                                    to={`/session/${session.id}`}
                                    sx={{ pt: 0.5, pb: 0.5 }}
                                >
                                    <ListItemIcon sx={{ minWidth: 'auto', mr: 1.5 }}> 
                                        <EventNoteIcon fontSize="small" />
                                    </ListItemIcon>
                                    <ListItemText 
                                        primary={
                                            <Typography variant="body2" component="span" sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                                                <span>{session.timestamp ? format(new Date(session.timestamp), 'dd/MM/yy HH:mm') : 'N/A'}</span>
                                                <Chip label={getSessionTypeLabel(session.session_type)} size="small" sx={{ ml: 1 }}/>
                                            </Typography>
                                        }
                                    />
                                </ListItemButton>
                            ) : (
                                <ListItemButton 
                                    component={RouterLink} 
                                    to={`/session/${session.id}`}
                                    sx={{ pt: 1, pb: 1 }}
                                >
                                    <ListItemIcon sx={{ minWidth: 'auto', mr: 2 }}> 
                                        <EventNoteIcon />
                                    </ListItemIcon>
                                    <ListItemText 
                                        primary={
                                            <Typography variant="body1" component="div" sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                <span>{session.timestamp ? format(new Date(session.timestamp), 'dd/MM/yyyy HH:mm') : 'N/A'}</span>
                                                <Chip label={getSessionTypeLabel(session.session_type)} size="small" />
                                            </Typography>
                                        }
                                        secondary={
                                            <Typography noWrap variant="body2" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                                                {session.doctor_notes || session.therapy_adjustments || "(Χωρίς σημειώσεις)"}
                                            </Typography>
                                        }
                                    />
                                </ListItemButton>
                            )}
                            {index < displaySessions.length - 1 && !isPreview && <Divider component="li" variant="inset" />}
                        </React.Fragment>
                    ))}
                </List>
            )}
        </>
    );

    if (isPreview) {
        return content;
    }

    return (
        <Paper sx={{ p: 3, mt: 3 }}>
            <Typography variant="h6" gutterBottom>Ιστορικό Συνεδριών</Typography>
            {content}
        </Paper>
    );
}

export default SessionsList; 