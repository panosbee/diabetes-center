import React, { useState, useEffect } from 'react';
import {
    Typography, 
    Container, 
    Box, 
    Button, 
    List, 
    ListItem, 
    ListItemText, 
    CircularProgress,
    Alert,
    ListItemButton
} from '@mui/material';
import { useNavigate, Link } from 'react-router-dom';
import authService from '../services/authService';
import patientService from '../services/patientService';

function DashboardPage() {
    const navigate = useNavigate();
    const [patients, setPatients] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchPatients = async () => {
            setLoading(true);
            setError('');
            try {
                console.log("Fetching patients...");
                const data = await patientService.getMyManagedPatients(); 
                console.log("Patients data received:", data);
                setPatients(data);
            } catch (err) {
                console.error("Failed to fetch patients:", err);
                const errorMessage = err.response?.data?.error || "Failed to load patient data.";
                setError(errorMessage);
                if (err.response?.status === 401) {
                    authService.logout();
                    navigate('/login');
                }
            } finally {
                setLoading(false);
            }
        };

        fetchPatients();
    }, [navigate]);

    const handleLogout = () => {
        authService.logout();
        navigate('/login');
    };

    return (
        <Container component="main" maxWidth="lg">
            <Box
                sx={{
                    marginTop: 4,
                    display: 'flex',
                    flexDirection: 'column',
                }}
            >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
                    <Typography component="h1" variant="h4" gutterBottom>
                        Doctor Dashboard
                    </Typography>
                    <Button 
                        variant="outlined"
                        color="secondary" 
                        onClick={handleLogout}
                    >
                        Logout
                    </Button>
                </Box>

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6" gutterBottom component="div">
                        My Patients
                    </Typography>
                    <Button 
                        variant="contained" 
                        component={Link}
                        to="/patients/new"
                    >
                        Add New Patient
                    </Button>
                </Box>

                {loading && (
                    <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
                         <CircularProgress />
                    </Box>
                )}

                {error && (
                    <Alert severity="error" sx={{ width: '100%', mt: 2 }}>
                        {error}
                    </Alert>
                )}

                {!loading && !error && (
                    <List sx={{ width: '100%', bgcolor: 'background.paper' }}>
                        {patients.length === 0 ? (
                            <ListItem>
                                <ListItemText primary="No patients found." />
                            </ListItem>
                        ) : (
                            patients.map((patient) => (
                                <ListItemButton 
                                    key={patient.id}
                                    component={Link}
                                    to={`/patients/${patient.id}`}
                                    sx={{ borderBottom: '1px solid #eee' }}
                                >
                                    <ListItemText 
                                        primary={`${patient.personal_details?.first_name || ''} ${patient.personal_details?.last_name || ''}`}
                                        secondary={`AMKA: ${patient.personal_details?.amka || 'N/A'}`}
                                    />
                                </ListItemButton>
                            ))
                        )}
                    </List>
                )}

            </Box>
        </Container>
    );
}

export default DashboardPage; 