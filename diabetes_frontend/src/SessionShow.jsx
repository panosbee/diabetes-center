import React from 'react';
import {
    Show,
    SimpleShowLayout,
    TextField,
    DateField,
    ReferenceField,
    EditButton,
    TopToolbar,
    useRecordContext,
    useGetIdentity
} from 'react-admin';
import { Grid, Typography, Paper, Box, Divider, Chip } from '@mui/material';
import { RestrictedAccessMessage } from './RestrictedAccessShow';

// Υπολογισμός BMI από τα δεδομένα υγείας
const BMIDisplay = () => {
    const record = useRecordContext();
    
    if (!record || !record.vitals_recorded) return null;
    
    const weight = record.vitals_recorded.weight_kg;
    const height = record.vitals_recorded.height_cm;
    
    // Υπολογισμός BMI μόνο αν υπάρχουν έγκυρες τιμές
    let bmi = 0;
    if (weight > 0 && height > 0) {
        bmi = (weight / ((height / 100) * (height / 100))).toFixed(2);
    }
    
    let bmiCategory = '';
    let color = 'default';
    
    if (bmi > 0) {
        if (bmi < 18.5) {
            bmiCategory = 'Λιποβαρής';
            color = 'warning';
        } else if (bmi < 25) {
            bmiCategory = 'Φυσιολογικός';
            color = 'success';
        } else if (bmi < 30) {
            bmiCategory = 'Υπέρβαρος';
            color = 'warning';
        } else {
            bmiCategory = 'Παχύσαρκος';
            color = 'error';
        }
    }
    
    return (
        <>
            <Typography variant="h5" color="primary">
                {bmi > 0 ? record.vitals_recorded.bmi : 'Μη διαθέσιμο'}
            </Typography>
            {bmi > 0 && (
                <Chip label={bmiCategory} color={color} size="small" />
            )}
        </>
    );
};

// Μετατροπή τύπου συνεδρίας σε αναγνώσιμη μορφή
const SessionTypeField = () => {
    const record = useRecordContext();
    if (!record || !record.session_type) return null;
    
    const typeMap = {
        'telemedicine': 'Τηλεϊατρική',
        'in_person': 'Με φυσική παρουσία',
        'data_review': 'Ανασκόπηση δεδομένων',
        'note': 'Σημείωση'
    };
    
    return <Typography>{typeMap[record.session_type] || record.session_type}</Typography>;
};

// Μετατροπή τύπου μέτρησης γλυκόζης
const GlucoseTypeField = () => {
    const record = useRecordContext();
    if (!record || !record.vitals_recorded?.blood_glucose_type) return null;
    
    const typeMap = {
        'fasting': 'Νηστείας',
        'postprandial': 'Μεταγευματική',
        'random': 'Τυχαία',
        'pre_meal': 'Προ φαγητού',
        'post_meal': 'Μετά φαγητού',
        'before_sleep': 'Προ ύπνου',
        'other': 'Άλλο'
    };
    
    const glucoseType = record.vitals_recorded.blood_glucose_type;
    return <Typography>{typeMap[glucoseType] || glucoseType}</Typography>;
};

// Actions για το Show view
const SessionShowActions = () => {
    const record = useRecordContext();
    const { identity } = useGetIdentity();
    
    if (!record || !identity) return null;
    
    // Έλεγχος αν ο συνδεδεμένος γιατρός είναι ο ίδιος με αυτόν της συνεδρίας
    const isSessionDoctor = record.doctor_id === identity.id;
    
    return (
        <TopToolbar>
            {isSessionDoctor && <EditButton />}
        </TopToolbar>
    );
};

export const SessionShow = (props) => (
    <Show 
        {...props} 
        title="Λεπτομέρειες Συνεδρίας"
        actions={<SessionShowActions />}
    >
        <RestrictedAccessMessage />
        <Grid container spacing={3}>
            <Grid item xs={12}>
                <Paper elevation={3} sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                        Βασικά Στοιχεία Συνεδρίας
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Grid container spacing={2}>
                        <Grid item xs={12} md={6}>
                            <Typography variant="subtitle2" color="textSecondary">Ασθενής</Typography>
                            <ReferenceField source="patient_id" reference="patients">
                                <TextField source="personal_details.first_name" />
                                {' '}
                                <TextField source="personal_details.last_name" />
                            </ReferenceField>
                        </Grid>
                        
                        <Grid item xs={12} md={6}>
                            <Typography variant="subtitle2" color="textSecondary">Γιατρός</Typography>
                            <ReferenceField source="doctor_id" reference="doctors">
                                <TextField source="personal_details.first_name" />
                                {' '}
                                <TextField source="personal_details.last_name" />
                            </ReferenceField>
                        </Grid>
                        
                        <Grid item xs={12} md={6}>
                            <Typography variant="subtitle2" color="textSecondary">Ημερομηνία & Ώρα</Typography>
                            <DateField 
                                source="timestamp" 
                                showTime
                                options={{ 
                                    weekday: 'long', 
                                    year: 'numeric', 
                                    month: 'long', 
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                }}
                            />
                        </Grid>
                        
                        <Grid item xs={12} md={6}>
                            <Typography variant="subtitle2" color="textSecondary">Τύπος Συνεδρίας</Typography>
                            <SessionTypeField />
                        </Grid>
                        
                        <Grid item xs={12} md={6}>
                            <Typography variant="subtitle2" color="textSecondary">Δημιουργήθηκε</Typography>
                            <DateField source="created_at" showTime />
                        </Grid>
                        
                        <Grid item xs={12} md={6}>
                            <Typography variant="subtitle2" color="textSecondary">Τελευταία Ενημέρωση</Typography>
                            <DateField source="last_updated_at" showTime />
                        </Grid>
                    </Grid>
                </Paper>
            </Grid>
            
            <Grid item xs={12}>
                <Paper elevation={3} sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                        Ζωτικά Σημεία
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Grid container spacing={2} alignItems="stretch">
                        <Grid item xs={12} sm={6} md={3}>
                            <Box sx={{ textAlign: 'center', p: 2, borderRadius: 1, bgcolor: 'background.paper' }}>
                                <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                                    Βάρος
                                </Typography>
                                <Typography variant="h5" color="primary">
                                    <TextField source="vitals_recorded.weight_kg" emptyText="Μη διαθέσιμο" /> kg
                                </Typography>
                            </Box>
                        </Grid>
                        
                        <Grid item xs={12} sm={6} md={3}>
                            <Box sx={{ textAlign: 'center', p: 2, borderRadius: 1, bgcolor: 'background.paper' }}>
                                <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                                    Ύψος
                                </Typography>
                                <Typography variant="h5" color="primary">
                                    <TextField source="vitals_recorded.height_cm" emptyText="Μη διαθέσιμο" /> cm
                                </Typography>
                            </Box>
                        </Grid>
                        
                        <Grid item xs={12} sm={6} md={3}>
                            <Box sx={{ textAlign: 'center', p: 2, borderRadius: 1, bgcolor: 'background.paper' }}>
                                <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                                    BMI
                                </Typography>
                                <BMIDisplay />
                            </Box>
                        </Grid>
                        
                        <Grid item xs={12} sm={6} md={3}>
                            <Box sx={{ textAlign: 'center', p: 2, borderRadius: 1, bgcolor: 'background.paper' }}>
                                <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                                    Αρτ. Πίεση
                                </Typography>
                                <Typography variant="h5" color="primary">
                                    <TextField source="vitals_recorded.blood_pressure_systolic" emptyText="-" />
                                    /
                                    <TextField source="vitals_recorded.blood_pressure_diastolic" emptyText="-" />
                                     mmHg
                                </Typography>
                            </Box>
                        </Grid>
                        
                        <Grid item xs={12} sm={6} md={3}>
                            <Box sx={{ textAlign: 'center', p: 2, borderRadius: 1, bgcolor: 'background.paper' }}>
                                <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                                    Γλυκόζη Αίματος
                                </Typography>
                                <Typography variant="h5" color="primary">
                                    <TextField source="vitals_recorded.blood_glucose_level" emptyText="-" /> mg/dL
                                </Typography>
                            </Box>
                        </Grid>
                        
                        <Grid item xs={12} sm={6} md={3}>
                            <Box sx={{ textAlign: 'center', p: 2, borderRadius: 1, bgcolor: 'background.paper' }}>
                                <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                                    Τύπος Μέτρησης
                                </Typography>
                                <GlucoseTypeField />
                            </Box>
                        </Grid>
                        
                        <Grid item xs={12}>
                            <Box sx={{ textAlign: 'center', p: 2, borderRadius: 1, bgcolor: 'background.paper' }}>
                                <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                                    Μονάδες Ινσουλίνης
                                </Typography>
                                <Typography variant="h5" color="primary">
                                    <TextField source="vitals_recorded.insulin_units" emptyText="Μη διαθέσιμο" />
                                </Typography>
                            </Box>
                        </Grid>
                    </Grid>
                </Paper>
            </Grid>
            
            <Grid item xs={12}>
                <Paper elevation={3} sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                        Σημειώσεις
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <Grid container spacing={2}>
                        <Grid item xs={12}>
                            <Typography variant="subtitle2" color="textSecondary">Σημειώσεις Γιατρού</Typography>
                            <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 1, mt: 1 }}>
                                <TextField source="doctor_notes" emptyText="Δεν υπάρχουν σημειώσεις." />
                            </Box>
                        </Grid>
                        
                        <Grid item xs={12}>
                            <Typography variant="subtitle2" color="textSecondary">Προσαρμογές Θεραπείας</Typography>
                            <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 1, mt: 1 }}>
                                <TextField source="therapy_adjustments" emptyText="Δεν υπάρχουν προσαρμογές θεραπείας." />
                            </Box>
                        </Grid>
                        
                        <Grid item xs={12}>
                            <Typography variant="subtitle2" color="textSecondary">Αναφορά Ασθενή</Typography>
                            <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 1, mt: 1 }}>
                                <TextField source="patient_reported_outcome" emptyText="Δεν υπάρχει αναφορά από τον ασθενή." />
                            </Box>
                        </Grid>
                    </Grid>
                </Paper>
            </Grid>
        </Grid>
    </Show>
); 