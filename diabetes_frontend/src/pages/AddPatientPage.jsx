import React, { useState } from 'react';
import {
    Container, 
    Box, 
    Typography, 
    TextField, 
    Button, 
    CircularProgress, 
    Alert,
    FormControlLabel,
    Checkbox,
    Grid
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import patientService from '../services/patientService'; // <-- Import patientService

function AddPatientPage() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        personal_details: {
            first_name: '',
            last_name: '',
            amka: '',
            // Add other optional fields if needed (date_of_birth, contact.email, contact.phone)
        },
        medical_profile: {
            // Add optional initial fields if needed (medical_history_summary, allergies)
        },
        is_in_common_space: false, 
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const handleChange = (event) => {
        const { name, value, type, checked } = event.target;
        const [section, field] = name.split('.');

        if (type === 'checkbox' && name === 'is_in_common_space') {
            setFormData(prev => ({ ...prev, is_in_common_space: checked }));
        } else if (field) { // Handle nested fields (personal_details.first_name etc)
             setFormData(prev => ({
                ...prev,
                [section]: {
                    ...prev[section],
                    [field]: value
                }
            }));
        } 
        // Add handling for medical_profile fields similarly if needed
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        setLoading(true);
        setError('');
        setSuccess('');

        if (!formData.personal_details.first_name || !formData.personal_details.last_name || !formData.personal_details.amka) {
            setError('First Name, Last Name, and AMKA are required.');
            setLoading(false);
            return;
        }

        console.log("Submitting new patient data:", formData);
        
        try {
            // Καλούμε το service για προσθήκη ασθενή
            const newPatient = await patientService.addPatient(formData);
            console.log("Patient added successfully:", newPatient);
            setSuccess(`Patient ${newPatient.personal_details.first_name || ''} ${newPatient.personal_details.last_name || ''} added successfully!`);
            
            // Καθαρισμός φόρμας και πλοήγηση πίσω στο dashboard μετά από λίγο
            setFormData({ // Reset form
                 personal_details: { first_name: '', last_name: '', amka: '' },
                 medical_profile: {},
                 is_in_common_space: false,
            });
            setTimeout(() => {
                 navigate('/dashboard'); 
            }, 2000); // Navigate after 2 seconds

        } catch (err) {
            console.error("Failed to add patient:", err);
            const errorMessage = err.response?.data?.error || "Failed to add patient.";
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Container component="main" maxWidth="md">
            <Box
                sx={{
                    marginTop: 4,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                }}
            >
                <Typography component="h1" variant="h4" gutterBottom>
                    Add New Patient
                </Typography>
                <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3, width: '100%' }}>
                    <Grid container spacing={2}>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                required
                                fullWidth
                                id="first_name"
                                label="First Name"
                                name="personal_details.first_name"
                                value={formData.personal_details.first_name}
                                onChange={handleChange}
                                autoFocus
                            />
                        </Grid>
                        <Grid item xs={12} sm={6}>
                            <TextField
                                required
                                fullWidth
                                id="last_name"
                                label="Last Name"
                                name="personal_details.last_name"
                                value={formData.personal_details.last_name}
                                onChange={handleChange}
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <TextField
                                required
                                fullWidth
                                id="amka"
                                label="AMKA"
                                name="personal_details.amka"
                                value={formData.personal_details.amka}
                                onChange={handleChange}
                            />
                        </Grid>
                        {/* Add more fields here for date_of_birth, contact, medical_profile as needed */}
                         <Grid item xs={12}>
                            <FormControlLabel
                                control={
                                    <Checkbox 
                                        checked={formData.is_in_common_space}
                                        onChange={handleChange} 
                                        name="is_in_common_space" 
                                    />}
                                label="Add to Common Space (visible to all doctors)"
                            />
                        </Grid>
                    </Grid>
                    
                    {error && <Alert severity="error" sx={{ width: '100%', mt: 3 }}>{error}</Alert>}
                    {success && <Alert severity="success" sx={{ width: '100%', mt: 3 }}>{success}</Alert>}

                    <Button
                        type="submit"
                        fullWidth
                        variant="contained"
                        sx={{ mt: 3, mb: 2 }}
                        disabled={loading}
                    >
                        {loading ? <CircularProgress size={24} /> : 'Add Patient'}
                    </Button>
                     <Button
                        fullWidth
                        variant="outlined"
                        sx={{ mb: 2 }}
                        onClick={() => navigate('/dashboard')} // Go back button
                    >
                        Cancel
                    </Button>
                </Box>
            </Box>
        </Container>
    );
}

export default AddPatientPage; 