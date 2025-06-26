import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
    Container, 
    Typography, 
    Box, 
    CircularProgress, 
    Alert, 
    Paper, 
    Grid,
    Button,
    List,
    ListItem,
    ListItemText,
    ListItemIcon,
    Divider
} from '@mui/material';
import DescriptionIcon from '@mui/icons-material/Description';
import EventNoteIcon from '@mui/icons-material/EventNote';
import patientService from '../services/patientService';
import authService from '../services/authService';
import { useNavigate } from 'react-router-dom';

function PatientDetailPage() {
    const { id } = useParams(); 
    const navigate = useNavigate();
    const [patientData, setPatientData] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchAllData = async () => {
            if (!id) return;
            
            setLoading(true);
            setError('');
            setPatientData(null);
            setSessions([]);
            setFiles([]);
            
            try {
                console.log(`Fetching all data for patient ID: ${id}`);
                const [patientDetails, patientSessions, patientFiles] = await Promise.all([
                    patientService.getPatientById(id),
                    patientService.getPatientSessions(id),
                    patientService.getPatientFilesList(id)
                ]);
                
                console.log("Patient details received:", patientDetails);
                setPatientData(patientDetails);
                
                console.log("Patient sessions received:", patientSessions);
                setSessions(patientSessions);

                console.log("Patient files received:", patientFiles);
                setFiles(patientFiles);

            } catch (err) {
                console.error("Failed to fetch patient page data:", err);
                const errorMessage = err.response?.data?.error || "Failed to load patient page data.";
                setError(errorMessage);
                if (err.response?.status === 401) {
                    authService.logout();
                    navigate('/login');
                } else if (err.response?.status === 403) {
                    setError("You are not authorized to view this patient's data.");
                }
            } finally {
                setLoading(false);
            }
        };

        fetchAllData();
    }, [id, navigate]);

    const formatDate = (isoString) => {
        if (!isoString) return 'N/A';
        try {
            return new Date(isoString).toLocaleString();
        } catch (e) {
            return isoString;
        }
    };

    return (
        <Container component="main" maxWidth="lg">
            <Box sx={{ marginTop: 4 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h4" gutterBottom>
                        Patient Details
                    </Typography>
                     <Button component={Link} to="/dashboard" variant="outlined">
                        Back to Dashboard
                    </Button>
                </Box>

                {loading && (
                    <Box sx={{ display: 'flex', justifyContent: 'center', my: 5 }}>
                        <CircularProgress />
                    </Box>
                )}

                {error && (
                    <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>
                )}

                {!loading && !error && patientData && (
                    <Grid container spacing={3}>
                        <Grid item xs={12} md={6}>
                             <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
                                <Typography variant="h5" gutterBottom sx={{ mb: 2 }}>Patient Information</Typography>
                                <Grid container spacing={1}>
                                    <Grid item xs={12} sm={6}><Typography><strong>Name:</strong> {patientData.personal_details?.first_name} {patientData.personal_details?.last_name}</Typography></Grid>
                                    <Grid item xs={12} sm={6}><Typography><strong>AMKA:</strong> {patientData.personal_details?.amka}</Typography></Grid>
                                    <Grid item xs={12} sm={6}>
                                        <Typography><strong>Date of Birth:</strong> {patientData.personal_details?.date_of_birth || 'N/A'}</Typography>
                                    </Grid>
                                    <Grid item xs={12} sm={6}>
                                        <Typography><strong>Email:</strong> {patientData.personal_details?.contact?.email || 'N/A'}</Typography>
                                    </Grid>
                                    <Grid item xs={12} sm={6}>
                                        <Typography><strong>Phone:</strong> {patientData.personal_details?.contact?.phone || 'N/A'}</Typography>
                                    </Grid>
                                    <Grid item xs={12} sm={6}>
                                        <Typography><strong>Address:</strong> {patientData.personal_details?.address?.street || ''} {patientData.personal_details?.address?.city || ''} {patientData.personal_details?.address?.zip_code || ''}</Typography>
                                    </Grid>
                                    <Grid item xs={12} sm={6}><Typography><strong>Common Space:</strong> {patientData.is_in_common_space ? 'Yes' : 'No'}</Typography></Grid>
                                </Grid>
                             </Paper>
                        </Grid>

                        <Grid item xs={12} md={6}>
                            <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="h5" gutterBottom component="div">Sessions</Typography>
                                </Box>
                                <List dense sx={{ maxHeight: 400, overflow: 'auto' }}>
                                    {sessions.length === 0 ? (
                                        <ListItem><ListItemText primary="No sessions found." /></ListItem>
                                    ) : (
                                        sessions.map((session, index) => (
                                            <React.Fragment key={session._id}>
                                                <ListItem alignItems="flex-start">
                                                     <ListItemIcon><EventNoteIcon /></ListItemIcon>
                                                    <ListItemText
                                                        primary={`${session.session_type} - ${formatDate(session.timestamp)}`}
                                                        secondary={
                                                            <React.Fragment>
                                                                <Typography component="span" variant="body2" color="text.primary">
                                                                     Notes: {session.doctor_notes || '-'}
                                                                 </Typography>
                                                            </React.Fragment>
                                                        }
                                                    />
                                                </ListItem>
                                                {index < sessions.length - 1 && <Divider variant="inset" component="li" />}
                                            </React.Fragment>
                                        ))
                                    )}
                                </List>
                            </Paper>
                        </Grid>

                        <Grid item xs={12}>
                             <Paper elevation={3} sx={{ p: 3, mt: 2 }}>
                                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="h5" gutterBottom component="div">Uploaded Files</Typography>
                                </Box>
                                <List dense>
                                     {files.length === 0 ? (
                                        <ListItem><ListItemText primary="No files found." /></ListItem>
                                    ) : (
                                        files.map((file) => (
                                            <ListItem 
                                                key={file.file_id}
                                                secondaryAction={
                                                    <Button 
                                                        size="small" 
                                                        href={`http://localhost:5000/api/files/${id}/${file.file_id}`}
                                                        target="_blank"
                                                    >
                                                        View/Download
                                                    </Button>
                                                }
                                            >
                                                 <ListItemIcon><DescriptionIcon /></ListItemIcon>
                                                <ListItemText
                                                    primary={file.original_filename || file.filename}
                                                    secondary={`Uploaded: ${formatDate(file.upload_date)} - Size: ${file.size_bytes ? (file.size_bytes / 1024).toFixed(1) : 'N/A'} KB - Type: ${file.mime_type}`}
                                                />
                                            </ListItem>
                                        ))
                                    )}
                                </List>
                            </Paper>
                        </Grid>
                    </Grid>
                )}
            </Box>
        </Container>
    );
}

export default PatientDetailPage; 