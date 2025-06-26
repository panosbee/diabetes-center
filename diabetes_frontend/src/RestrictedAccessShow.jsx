import React from 'react';
import { useRecordContext, Show, SimpleShowLayout, TextField } from 'react-admin';
import { Typography, Box, Paper } from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';

// Component που εμφανίζεται όταν ο χρήστης δεν έχει πρόσβαση σε ένα record
export const RestrictedAccessMessage = () => {
    const record = useRecordContext();
    
    // Έλεγχος αν το record έχει μόνο id και message: 'Access Restricted'
    const isRestricted = record && 
                         record.message === 'Access Restricted' && 
                         Object.keys(record).length === 2;
    
    if (!isRestricted) return null;
    
    return (
        <Paper elevation={3} sx={{ p: 3, mt: 2, textAlign: 'center' }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <LockIcon sx={{ fontSize: 60, mb: 2, color: 'warning.main' }} />
                <Typography variant="h5" gutterBottom>
                    Περιορισμένη Πρόσβαση
                </Typography>
                <Typography variant="body1">
                    Δεν έχετε δικαίωμα να δείτε τις πλήρεις λεπτομέρειες αυτής της εγγραφής.
                </Typography>
                <Typography variant="body2" sx={{ mt: 2, color: 'text.secondary' }}>
                    Μπορείτε να δείτε μόνο τις βασικές πληροφορίες. Για πλήρη πρόσβαση, 
                    επικοινωνήστε με τον διαχειριστή του συστήματος.
                </Typography>
            </Box>
        </Paper>
    );
};

// Wrapper για το Show component που εμφανίζει το RestrictedAccessMessage
export const RestrictedAccessShow = ({ children, ...props }) => (
    <Show {...props}>
        <RestrictedAccessMessage />
        {children}
    </Show>
); 