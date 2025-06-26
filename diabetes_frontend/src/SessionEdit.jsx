import React from 'react';
import {
    Edit,
    SimpleForm,
    TextInput,
    DateTimeInput,
    SelectInput,
    ReferenceInput,
    AutocompleteInput,
    NumberInput,
    ReferenceField,
    TextField,
    useGetIdentity,
    useRecordContext,
    Toolbar,
    SaveButton,
    DeleteButton
} from 'react-admin';
import { useFormContext } from 'react-hook-form';
import { Grid, Typography, Paper, Box } from '@mui/material';

// Το BMI υπολογίζεται αυτόματα από το ύψος και το βάρος
const BMICalculator = () => {
    const { watch } = useFormContext();
    
    const weight = watch('vitals_recorded.weight_kg', 0);
    const height = watch('vitals_recorded.height_cm', 0);
    
    // Υπολογισμός BMI μόνο αν υπάρχουν έγκυρες τιμές
    let bmi = 0;
    if (weight > 0 && height > 0) {
        bmi = (weight / ((height / 100) * (height / 100))).toFixed(2);
    }
    
    return (
        <Paper elevation={1} sx={{ p: 2, bgcolor: 'background.paper' }}>
            <Typography variant="subtitle1" gutterBottom>
                Υπολογισμός BMI
            </Typography>
            <Typography variant="h5" color="primary">
                {bmi > 0 ? bmi : 'Απαιτούνται ύψος και βάρος'}
            </Typography>
            {bmi > 0 && (
                <Typography variant="body2" color="textSecondary">
                    {bmi < 18.5 ? 'Λιποβαρής' : 
                     bmi < 25 ? 'Φυσιολογικός' : 
                     bmi < 30 ? 'Υπέρβαρος' : 'Παχύσαρκος'}
                </Typography>
            )}
        </Paper>
    );
};

// Custom toolbar που ελέγχει αν ο γιατρός έχει δικαίωμα επεξεργασίας της συνεδρίας
const SessionEditToolbar = (props) => {
    const { identity } = useGetIdentity();
    const record = useRecordContext();
    
    if (!record || !identity) return null;
    
    // Έλεγχος αν ο συνδεδεμένος γιατρός είναι ο ίδιος με αυτόν της συνεδρίας
    const isSessionDoctor = record.doctor_id === identity.id;
    
    console.log(`[SessionEditToolbar] Checking permissions: Session Doctor = ${record.doctor_id}, Current Doctor = ${identity.id}, Can Edit = ${isSessionDoctor}`);
    
    return (
        <Toolbar {...props}>
            {isSessionDoctor && <SaveButton />}
            {isSessionDoctor && <DeleteButton mutationMode="pessimistic" />}
        </Toolbar>
    );
};

export const SessionEdit = (props) => {
    return (
        <Edit 
            {...props} 
            title="Επεξεργασία Συνεδρίας"
        >
            <SimpleForm toolbar={<SessionEditToolbar />}>
                <Grid container spacing={2}>
                    <Grid item xs={12}>
                        <Typography variant="h6" gutterBottom>
                            Βασικά Στοιχεία Συνεδρίας
                        </Typography>
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                        <ReferenceField source="patient_id" reference="patients" label="Ασθενής">
                            <TextField source="personal_details.last_name" />
                        </ReferenceField>
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                        <ReferenceField source="doctor_id" reference="doctors" label="Γιατρός">
                            <TextField source="personal_details.last_name" />
                        </ReferenceField>
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                        <DateTimeInput 
                            source="timestamp" 
                            label="Ημερομηνία & Ώρα" 
                            fullWidth 
                            disabled
                        />
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                        <SelectInput 
                            source="session_type" 
                            label="Τύπος Συνεδρίας" 
                            fullWidth
                            choices={[
                                { id: 'telemedicine', name: 'Τηλεϊατρική' },
                                { id: 'in_person', name: 'Με φυσική παρουσία' },
                                { id: 'data_review', name: 'Ανασκόπηση δεδομένων' },
                                { id: 'note', name: 'Σημείωση' }
                            ]}
                        />
                    </Grid>
                    
                    <Grid item xs={12}>
                        <Box mt={3}>
                            <Typography variant="h6" gutterBottom>
                                Ζωτικά Σημεία
                            </Typography>
                        </Box>
                    </Grid>
                    
                    <Grid item xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.weight_kg" 
                            label="Βάρος (kg)" 
                            fullWidth 
                            min={0}
                            step={0.1}
                        />
                    </Grid>
                    
                    <Grid item xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.height_cm" 
                            label="Ύψος (cm)" 
                            fullWidth 
                            min={0}
                            step={0.1}
                        />
                    </Grid>
                    
                    <Grid item xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.bmi" 
                            label="BMI (Αποθηκευμένο)"
                            fullWidth 
                            disabled 
                        />
                    </Grid>
                    
                    <Grid item xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.hba1c" 
                            label="HbA1c (%)" 
                            fullWidth 
                            min={0}
                            step={0.1}
                        />
                    </Grid>
                    
                    <Grid item xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.blood_pressure_systolic"
                            label="Συστολική Πίεση (mmHg)" 
                            fullWidth 
                            min={0}
                            step={1}
                        />
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.blood_pressure_diastolic"
                            label="Διαστολική Πίεση (mmHg)" 
                            fullWidth 
                            min={0}
                            step={1}
                        />
                    </Grid>
                    
                    <Grid item xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.blood_glucose_level"
                            label="Γλυκόζη Αίματος (mg/dL)"
                            fullWidth
                            min={0}
                            step={1}
                        />
                    </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <SelectInput 
                            source="vitals_recorded.blood_glucose_type"
                            label="Τύπος Μέτρησης"
                            fullWidth
                            choices={[
                                { id: 'fasting', name: 'Νηστείας' },
                                { id: 'postprandial', name: 'Μεταγευματική' },
                                { id: 'random', name: 'Τυχαία' },
                                { id: 'pre_meal', name: 'Προ φαγητού' },
                                { id: 'post_meal', name: 'Μετά φαγητού' },
                                { id: 'before_sleep', name: 'Προ ύπνου' },
                                { id: 'other', name: 'Άλλο' }
                            ]}
                            emptyText="Επιλέξτε..."
                        />
                    </Grid>
                    
                    <Grid item xs={12} md={6}>
                        <NumberInput 
                            source="vitals_recorded.insulin_units" 
                            label="Μονάδες Ινσουλίνης" 
                            fullWidth 
                            min={0}
                            step={0.5}
                        />
                    </Grid>
                    
                    <Grid item xs={12}>
                        <Box mt={3}>
                            <Typography variant="h6" gutterBottom>
                                Σημειώσεις
                            </Typography>
                        </Box>
                    </Grid>
                    
                    <Grid item xs={12}>
                        <TextInput 
                            source="doctor_notes" 
                            label="Σημειώσεις Γιατρού" 
                            fullWidth 
                            multiline 
                            rows={3}
                        />
                    </Grid>
                    
                    <Grid item xs={12}>
                        <TextInput 
                            source="therapy_adjustments" 
                            label="Προσαρμογές Θεραπείας" 
                            fullWidth 
                            multiline 
                            rows={3}
                        />
                    </Grid>
                    
                    <Grid item xs={12}>
                        <TextInput 
                            source="patient_reported_outcome" 
                            label="Αναφορά Ασθενή" 
                            fullWidth 
                            multiline 
                            rows={3}
                        />
                    </Grid>
                </Grid>
            </SimpleForm>
        </Edit>
    );
}; 