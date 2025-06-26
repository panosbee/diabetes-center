import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import { 
    Container, 
    Typography, 
    Box, 
    CircularProgress, 
    Alert, 
    Paper, 
    Grid, 
    Divider, 
    Chip,
    Button,
    IconButton
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { getMySessionDetails } from '../dataProvider';
import { authProvider } from '../authProvider';
import { format } from 'date-fns';

// Βοηθητικές συναρτήσεις (παρόμοιες με SessionShow.jsx)
const getSessionTypeLabel = (type) => {
    const typeMap = {
        'telemedicine': 'Τηλεϊατρική',
        'in_person': 'Με φυσική παρουσία',
        'data_review': 'Ανασκόπηση δεδομένων',
        'note': 'Σημείωση',
        'file_upload': 'Ανέβασμα Αρχείου'
    };
    return typeMap[type] || type || 'Άγνωστος Τύπος';
};

const BMIDisplay = ({ vitals }) => {
    if (!vitals) return '-';
    const weight = vitals.weight_kg;
    const height = vitals.height_cm;
    let bmi = vitals.bmi; // Προτιμάμε το αποθηκευμένο αν υπάρχει
    
    if (!bmi && weight > 0 && height > 0) { // Υπολογισμός αν λείπει
        bmi = (weight / ((height / 100) * (height / 100))).toFixed(2);
    }
    
    if (!bmi || bmi <= 0) return '-';

    let bmiCategory = '';
    let color = 'default';
    if (bmi < 18.5) { bmiCategory = 'Λιποβαρής'; color = 'warning'; }
    else if (bmi < 25) { bmiCategory = 'Φυσιολογικός'; color = 'success'; }
    else if (bmi < 30) { bmiCategory = 'Υπέρβαρος'; color = 'warning'; }
    else { bmiCategory = 'Παχύσαρκος'; color = 'error'; }

    return (
        <Box textAlign="center">
            <Typography variant="h5" color="primary">{bmi}</Typography>
            <Chip label={bmiCategory} color={color} size="small" />
        </Box>
    );
};

const GlucoseTypeField = ({ type }) => {
    if (!type) return '-';
     const typeMap = {
        'fasting': 'Νηστείας',
        'postprandial': 'Μεταγευματική',
        'random': 'Τυχαία',
        'pre_meal': 'Προ φαγητού',
        'post_meal': 'Μετά φαγητού',
        'before_sleep': 'Προ ύπνου',
        'other': 'Άλλο'
    };
    return typeMap[type] || type;
};

function SessionDetailPage() {
    const { sessionId } = useParams(); // Παίρνουμε το ID από το URL
    const navigate = useNavigate();
    const [session, setSession] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const loadSession = async () => {
            if (!sessionId) {
                setError("Session ID is missing.");
                setLoading(false);
                return;
            }
            setLoading(true);
            setError('');
            try {
                const { data } = await getMySessionDetails(sessionId);
                setSession(data);
            } catch (err) {
                console.error("Session details loading error:", err);
                authProvider.checkError(err).catch(() => {
                    setError(err.message || 'Failed to load session details.');
                });
            } finally {
                setLoading(false);
            }
        };
        loadSession();
    }, [sessionId]);

    if (loading) {
        return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}><CircularProgress /></Box>;
    }

    if (error) {
        return <Container><Alert severity="error" sx={{ mt: 2 }}>{error}</Alert></Container>;
    }

    if (!session) {
        return <Container><Alert severity="warning" sx={{ mt: 2 }}>Could not load session data.</Alert></Container>;
    }

    const vitals = session.vitals_recorded || {};

    return (
        <Container maxWidth="lg" sx={{ mt: 2, mb: 4 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                 <IconButton onClick={() => navigate(-1)} sx={{ mr: 1 }}> {/* Κουμπί Επιστροφής */}
                     <ArrowBackIcon />
                 </IconButton>
                 <Typography variant="h5" component="h1">
                    Λεπτομέρειες Συνεδρίας
                 </Typography>
             </Box>
            
            <Grid container spacing={3}>
                {/* Κάρτα Βασικών Στοιχείων */}
                <Grid item xs={12} md={6}>
                    <Paper elevation={2} sx={{ p: 2, height: '100%' }}>
                        <Typography variant="h6" gutterBottom>Βασικά Στοιχεία</Typography>
                        <Divider sx={{ mb: 2 }} />
                        <Typography><strong>Ημερομηνία:</strong> {session.timestamp ? format(new Date(session.timestamp), 'dd/MM/yyyy HH:mm') : 'N/A'}</Typography>
                        <Typography><strong>Τύπος:</strong> <Chip label={getSessionTypeLabel(session.session_type)} size="small" /></Typography>
                        {/* TODO: Εμφάνιση ονόματος γιατρού αν χρειάζεται, κάνοντας fetch από /api/doctors/{session.doctor_id} */} 
                        {/* <Typography><strong>Γιατρός:</strong> {session.doctor_id}</Typography> */}
                    </Paper>
                </Grid>

                {/* Κάρτα Ζωτικών Σημείων */}
                <Grid item xs={12} md={6}>
                    <Paper elevation={2} sx={{ p: 2, height: '100%' }}>
                         <Typography variant="h6" gutterBottom>Ζωτικά Σημεία</Typography>
                         <Divider sx={{ mb: 2 }} />
                         <Grid container spacing={2} textAlign="center" alignItems="stretch"> 
                            <Grid item xs={6} sm={3}>
                                <Paper variant="outlined" sx={{ p: 1, height: '100%' }}>
                                    <Typography variant="caption" display="block">Βάρος</Typography>
                                    <Typography variant="body1">{vitals.weight_kg || '-'} kg</Typography>
                                </Paper>
                            </Grid>
                            <Grid item xs={6} sm={3}>
                                <Paper variant="outlined" sx={{ p: 1, height: '100%' }}>
                                    <Typography variant="caption" display="block">Ύψος</Typography>
                                    <Typography variant="body1">{vitals.height_cm || '-'} cm</Typography>
                                </Paper>
                            </Grid>
                            <Grid item xs={6} sm={3}>
                                 <Paper variant="outlined" sx={{ p: 1, height: '100%' }}>
                                     <Typography variant="caption" display="block">BMI</Typography>
                                     <BMIDisplay vitals={vitals} />
                                 </Paper>
                            </Grid>
                            <Grid item xs={6} sm={3}>
                                 <Paper variant="outlined" sx={{ p: 1, height: '100%' }}>
                                     <Typography variant="caption" display="block">Πίεση</Typography>
                                     <Typography variant="body1">{vitals.blood_pressure_systolic && vitals.blood_pressure_diastolic ? `${vitals.blood_pressure_systolic}/${vitals.blood_pressure_diastolic}` : '-'} mmHg</Typography>
                                 </Paper>
                            </Grid>
                            <Grid item xs={6} sm={4}>
                                 <Paper variant="outlined" sx={{ p: 1, height: '100%' }}>
                                     <Typography variant="caption" display="block">HbA1c</Typography>
                                     <Typography variant="body1">{vitals.hba1c || '-'} %</Typography>
                                 </Paper>
                            </Grid>
                            <Grid item xs={6} sm={4}>
                                 <Paper variant="outlined" sx={{ p: 1, height: '100%' }}>
                                     <Typography variant="caption" display="block">Γλυκόζη (<GlucoseTypeField type={vitals.blood_glucose_type} />)</Typography>
                                     <Typography variant="body1">{vitals.blood_glucose_level || '-'} mg/dL</Typography>
                                 </Paper>
                            </Grid>
                            <Grid item xs={6} sm={4}>
                                 <Paper variant="outlined" sx={{ p: 1, height: '100%' }}>
                                     <Typography variant="caption" display="block">Ινσουλίνη</Typography>
                                     <Typography variant="body1">{vitals.insulin_units || '-'} units</Typography>
                                 </Paper>
                            </Grid>
                         </Grid>
                    </Paper>
                </Grid>
                
                 {/* Κάρτα Σημειώσεων */}
                <Grid item xs={12}>
                    <Paper elevation={2} sx={{ p: 2 }}>
                         <Typography variant="h6" gutterBottom>Σημειώσεις Γιατρού</Typography>
                         <Divider sx={{ mb: 2 }} />
                         <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{session.doctor_notes || "Δεν υπάρχουν σημειώσεις."}</Typography>
                         
                         <Typography variant="h6" gutterBottom sx={{mt: 3}}>Προσαρμογές Θεραπείας</Typography>
                         <Divider sx={{ mb: 2 }} />
                         <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{session.therapy_adjustments || "Δεν υπάρχουν προσαρμογές."}</Typography>
                         
                         {/* Το patient_reported_outcome ίσως δεν χρειάζεται να το βλέπει ο ασθενής; Αναλόγως */} 
                         {/* 
                         <Typography variant="h6" gutterBottom sx={{mt: 3}}>Η Αναφορά μου</Typography>
                         <Divider sx={{ mb: 2 }} />
                         <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{session.patient_reported_outcome || "-"}</Typography>
                         */}
                    </Paper>
                </Grid>
            </Grid>
        </Container>
    );
}

export default SessionDetailPage; 