import React, { useState } from 'react';
import { useRecordContext, useNotify, useRefresh } from 'react-admin';
import { Switch, FormControlLabel, Box, Button, Tooltip } from '@mui/material';
import PublicIcon from '@mui/icons-material/Public';
import LockIcon from '@mui/icons-material/Lock';

/**
 * Component για την ενεργοποίηση/απενεργοποίηση του common space για έναν ασθενή.
 * Χρησιμοποιείται στο PatientShow και PatientEdit.
 */
const CommonSpaceToggle = () => {
    const record = useRecordContext();
    const notify = useNotify();
    const refresh = useRefresh();
    const [loading, setLoading] = useState(false);
    
    if (!record) return null;
    
    const currentState = record.is_in_common_space || false;
    
    // Διαχείριση της αλλαγής του switch
    const handleToggle = async () => {
        setLoading(true);
        
        try {
            // Λήψη του JWT token από το localStorage
            const token = localStorage.getItem('token');
            if (!token) {
                throw new Error('Authentication token not found');
            }
            
            // Κλήση στο backend για την αλλαγή του common space
            const response = await fetch(`${import.meta.env.VITE_API_URL}/api/patients/${record.id}/common-space`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ is_in_common_space: !currentState })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Unknown error occurred');
            }
            
            const data = await response.json();
            
            // Ενημέρωση του UI
            notify(
                currentState 
                    ? 'Ο ασθενής αφαιρέθηκε από τον κοινό χώρο' 
                    : 'Ο ασθενής προστέθηκε στον κοινό χώρο', 
                { type: 'success' }
            );
            
            // Ανανέωση των δεδομένων
            refresh();
        } catch (error) {
            notify(`Σφάλμα: ${error.message}`, { type: 'error' });
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <Box sx={{ display: 'flex', alignItems: 'center', my: 1 }}>
            <Tooltip 
                title={currentState 
                    ? "Ο ασθενής βρίσκεται στον κοινό χώρο και είναι προσβάσιμος από όλους τους γιατρούς" 
                    : "Ο ασθενής δεν βρίσκεται στον κοινό χώρο και είναι προσβάσιμος μόνο από τους assigned γιατρούς"
                }
            >
                <FormControlLabel 
                    control={
                        <Switch 
                            checked={currentState}
                            onChange={handleToggle}
                            color="primary"
                            disabled={loading}
                        />
                    }
                    label={
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {currentState ? <PublicIcon color="primary" sx={{ mr: 1 }} /> : <LockIcon sx={{ mr: 1 }} />}
                            {currentState ? "Κοινός Χώρος Ενεργός" : "Κοινός Χώρος Ανενεργός"}
                        </Box>
                    }
                />
            </Tooltip>
        </Box>
    );
};

export default CommonSpaceToggle; 