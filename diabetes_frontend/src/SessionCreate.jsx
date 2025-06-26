import React, { useEffect } from 'react';
import {
    Create,
    SimpleForm,
    TextInput,
    DateTimeInput,
    SelectInput,
    ReferenceInput,
    AutocompleteInput,
    NumberInput,
    useGetIdentity
} from 'react-admin';
import { useFormContext } from 'react-hook-form';
import { Grid, Typography, Paper, Box } from '@mui/material';

// Το BMI υπολογίζεται αυτόματα από το ύψος και το βάρος
const BMICalculator = () => {
    const { watch, setValue } = useFormContext();
    
    const weight = watch('vitals_recorded.weight_kg', 0);
    const height = watch('vitals_recorded.height_cm', 0);
    
    // Παρακολουθούμε αλλαγές στο ύψος/βάρος και ενημερώνουμε το πεδίο bmi
    useEffect(() => {
        let calculatedBmi = 0;
        if (weight > 0 && height > 0) {
            calculatedBmi = parseFloat((weight / ((height / 100) * (height / 100))).toFixed(2));
        }
        // Ενημέρωση της τιμής του πεδίου vitals_recorded.bmi στη φόρμα
        setValue('vitals_recorded.bmi', calculatedBmi, { shouldValidate: true }); 
    }, [weight, height, setValue]);

    // Παίρνουμε την τρέχουσα τιμή του BMI από τη φόρμα για εμφάνιση
    const bmi = watch('vitals_recorded.bmi', 0); 
    
    return (
        <Paper elevation={1} sx={{ p: 2, bgcolor: 'background.paper', height: '100%' }}>
            <Typography variant="subtitle1" gutterBottom>
                BMI
            </Typography>
            <Typography variant="h5" color={bmi > 0 ? "primary" : "textSecondary"}>
                {bmi > 0 ? bmi : '-'}
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

export const SessionCreate = (props) => {
    const { identity } = useGetIdentity();
    
    return (
        <Create {...props} title="Νέα Συνεδρία">
            <SimpleForm>
                <Grid container spacing={2}>
                    <Grid xs={12}>
                        <Typography variant="h6" gutterBottom>
                            Βασικά Στοιχεία Συνεδρίας
                        </Typography>
                    </Grid>
                    
                    <Grid xs={12} md={6}>
                        <ReferenceInput source="patient_id" reference="patients" fullWidth>
                            <AutocompleteInput 
                                optionText={record => record ? `${record.personal_details?.first_name} ${record.personal_details?.last_name}` : ''} 
                                label="Ασθενής"
                                fullWidth
                            />
                        </ReferenceInput>
                    </Grid>
                    
                    <Grid xs={12} md={6}>
                        <TextInput 
                            source="doctor_id" 
                            defaultValue={identity?.id} 
                            disabled 
                            fullWidth 
                            label="Γιατρός" 
                        />
                    </Grid>
                    
                    <Grid xs={12} md={6}>
                        <DateTimeInput 
                            source="timestamp" 
                            label="Ημερομηνία & Ώρα" 
                            fullWidth 
                        />
                    </Grid>
                    
                    <Grid xs={12} md={6}>
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
                    
                    <Grid xs={12}>
                        <Box mt={3}>
                            <Typography variant="h6" gutterBottom>
                                Ζωτικά Σημεία
                            </Typography>
                        </Box>
                    </Grid>
                    
                    <Grid xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.weight_kg" 
                            label="Βάρος (kg)" 
                            fullWidth 
                            min={0}
                            step={0.1}
                        />
                    </Grid>
                    
                    <Grid xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.height_cm" 
                            label="Ύψος (cm)" 
                            fullWidth 
                            min={0}
                            step={0.1}
                        />
                    </Grid>
                    
                    <Grid xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.bmi" 
                            label="BMI (Υπολογισμένο)" 
                            fullWidth 
                            disabled
                        />
                    </Grid>
                    
                    <Grid xs={12} sm={6} md={3}>
                        <BMICalculator />
                    </Grid>
                    
                    <Grid xs={12} md={6}>
                        <NumberInput 
                            source="vitals_recorded.hba1c" 
                            label="HbA1c (%)" 
                            fullWidth 
                            min={0}
                            step={0.1}
                        />
                    </Grid>
                    
                    <Grid xs={12} md={6}>
                        <NumberInput 
                            source="vitals_recorded.insulin_units" 
                            label="Μονάδες Ινσουλίνης" 
                            fullWidth 
                            min={0}
                            step={0.5}
                        />
                    </Grid>
                    
                    <Grid xs={12}>
                        <Box mt={3}>
                            <Typography variant="h6" gutterBottom>
                                Σημειώσεις
                            </Typography>
                        </Box>
                    </Grid>
                    
                    <Grid xs={12}>
                        <TextInput 
                            source="doctor_notes" 
                            label="Σημειώσεις Γιατρού" 
                            fullWidth 
                            multiline 
                            rows={3}
                        />
                    </Grid>
                    
                    <Grid xs={12}>
                        <TextInput 
                            source="therapy_adjustments" 
                            label="Προσαρμογές Θεραπείας" 
                            fullWidth 
                            multiline 
                            rows={3}
                        />
                    </Grid>
                    
                    <Grid xs={12}>
                        <TextInput 
                            source="patient_reported_outcome" 
                            label="Αναφορά Ασθενή" 
                            fullWidth 
                            multiline 
                            rows={3}
                        />
                    </Grid>
                    
                    {/* --- Νέα πεδία για Αρτηριακή Πίεση --- */}
                    <Grid xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.blood_pressure_systolic"
                            label="Συστολική Πίεση (mmHg)" 
                            fullWidth 
                            min={0}
                            step={1}
                        />
                    </Grid>
                    <Grid xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.blood_pressure_diastolic"
                            label="Διαστολική Πίεση (mmHg)" 
                            fullWidth 
                            min={0}
                            step={1}
                        />
                    </Grid>
                    {/* --- Τέλος πεδίων Αρτηριακής Πίεσης --- */}
                    
                    <Grid xs={12} md={6}>
                        {/* ... existing code for hba1c ... */}
                    </Grid>
                    
                    {/* --- Νέα πεδία για Γλυκόζη Αίματος --- */}
                    <Grid xs={12} sm={6} md={3}>
                        <NumberInput 
                            source="vitals_recorded.blood_glucose_level"
                            label="Γλυκόζη Αίματος (mg/dL)"
                            fullWidth
                            min={0}
                            step={1}
                        />
                    </Grid>
                    <Grid xs={12} sm={6} md={3}>
                        <SelectInput 
                            source="vitals_recorded.blood_glucose_type"
                            label="Τύπος Μέτρησης"
                            fullWidth
                            choices={[
                                { id: 'fasting', name: 'Νηστείας' },
                                { id: 'postprandial', name: 'Μεταγευματική' },
                                { id: 'random', name: 'Τυχαία' },
                                { id: 'pre_meal', name: 'Προ φαγητού' },
                                { id: 'post_meal', name: 'Μετά φαγητού' }, // Πιο συγκεκριμένο από postprandial
                                { id: 'before_sleep', name: 'Προ ύπνου' },
                                { id: 'other', name: 'Άλλο' }
                            ]}
                            emptyText="Επιλέξτε..."
                        />
                    </Grid>
                    {/* --- Τέλος πεδίων Γλυκόζης --- */}
                </Grid>
            </SimpleForm>
        </Create>
    );
}; 