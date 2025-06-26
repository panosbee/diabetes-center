import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Container, 
    TextField, 
    Button, 
    Typography, 
    Box, 
    Select, 
    MenuItem, 
    InputLabel, 
    FormControl, 
    Grid, 
    Alert
} from '@mui/material';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs from 'dayjs'; // Για το DatePicker

// URL του Backend (Ίσως να μπει σε .env αργότερα)
const API_BASE_URL = 'http://localhost:5000/api';

function RegisterPage() {
    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        amka: '',
        date_of_birth: null, // Αρχική τιμή για DatePicker
        email: '',
        phone: '',
        password: '',
        confirmPassword: '',
        doctor_id: '', // ID του επιλεγμένου γιατρού
        address: '', // Προαιρετικό
        gender: '' // Προαιρετικό
    });
    const [doctors, setDoctors] = useState([]);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    // Φόρτωση λίστας διαθέσιμων γιατρών κατά την έναρξη
    useEffect(() => {
        const fetchDoctors = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/doctors/available`);
                if (!response.ok) {
                    throw new Error('Failed to fetch doctors');
                }
                const data = await response.json();
                setDoctors(data);
            } catch (err) {
                setError(err.message || 'Could not load available doctors.');
            }
        };
        fetchDoctors();
    }, []);

    const handleChange = (event) => {
        const { name, value } = event.target;
        setFormData(prevState => ({
            ...prevState,
            [name]: value
        }));
    };

    // Ειδικό handleChange για το DatePicker
    const handleDateChange = (newValue) => {
        setFormData(prevState => ({
            ...prevState,
            date_of_birth: newValue 
        }));
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError('');
        setSuccess('');

        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match.');
            return;
        }
        if (formData.password.length < 8) {
            setError('Password must be at least 8 characters long.');
            return;
        }
        if (!formData.doctor_id) {
            setError('Please select a doctor.');
            return;
        }

        setLoading(true);

        // Προετοιμασία δεδομένων για αποστολή
        const dataToSend = {
            first_name: formData.first_name,
            last_name: formData.last_name,
            amka: formData.amka,
            // Μετατροπή ημερομηνίας σε ISO string (μόνο το date part)
            date_of_birth: formData.date_of_birth ? dayjs(formData.date_of_birth).format('YYYY-MM-DD') : null,
            email: formData.email,
            phone: formData.phone,
            password: formData.password,
            doctor_id: formData.doctor_id,
            gender: formData.gender || null, // Στέλνουμε null αν είναι κενό
            address: formData.address || null
        };

        try {
            const response = await fetch(`${API_BASE_URL}/patient-portal/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(dataToSend),
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `HTTP error! status: ${response.status}`);
            }

            setSuccess('Registration successful! Redirecting to login...');
            // Προαιρετικά: Καθάρισμα φόρμας
            // setFormData({... αρχικές τιμές ...});
            setTimeout(() => {
                navigate('/login');
            }, 2000); // Ανακατεύθυνση μετά από 2 δευτερόλεπτα

        } catch (err) {
            setError(err.message || 'Registration failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <LocalizationProvider dateAdapter={AdapterDayjs}>
            <Container maxWidth="sm">
                <Box sx={{ marginTop: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <Typography component="h1" variant="h5">
                        Εγγραφή Νέου Ασθενή
                    </Typography>
                    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
                        <Grid container spacing={2}>
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    required
                                    fullWidth
                                    id="first_name"
                                    label="Όνομα"
                                    name="first_name"
                                    autoComplete="given-name"
                                    value={formData.first_name}
                                    onChange={handleChange}
                                    disabled={loading}
                                />
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField
                                    required
                                    fullWidth
                                    id="last_name"
                                    label="Επώνυμο"
                                    name="last_name"
                                    autoComplete="family-name"
                                    value={formData.last_name}
                                    onChange={handleChange}
                                    disabled={loading}
                                />
                            </Grid>
                            <Grid item xs={12}>
                                <TextField
                                    required
                                    fullWidth
                                    id="amka"
                                    label="ΑΜΚΑ"
                                    name="amka"
                                    value={formData.amka}
                                    onChange={handleChange}
                                    disabled={loading}
                                />
                            </Grid>
                            <Grid item xs={12}>
                                <DatePicker
                                    label="Ημερομηνία Γέννησης *"
                                    value={formData.date_of_birth}
                                    onChange={handleDateChange}
                                    renderInput={(params) => <TextField {...params} required fullWidth disabled={loading} />}
                                    disableFuture // Δεν επιτρέπουμε μελλοντικές ημερομηνίες
                                    inputFormat="DD/MM/YYYY" // Μορφή εμφάνισης
                                />
                            </Grid>
                            <Grid item xs={12}>
                                <TextField
                                    required
                                    fullWidth
                                    id="email"
                                    label="Διεύθυνση Email"
                                    name="email"
                                    type="email"
                                    autoComplete="email"
                                    value={formData.email}
                                    onChange={handleChange}
                                    disabled={loading}
                                />
                            </Grid>
                            <Grid item xs={12}>
                                <TextField
                                    required
                                    fullWidth
                                    id="phone"
                                    label="Τηλέφωνο"
                                    name="phone"
                                    type="tel"
                                    autoComplete="tel"
                                    value={formData.phone}
                                    onChange={handleChange}
                                    disabled={loading}
                                />
                            </Grid>
                             <Grid item xs={12}>
                                <TextField
                                    fullWidth
                                    id="address"
                                    label="Διεύθυνση (Προαιρετικό)"
                                    name="address"
                                    value={formData.address}
                                    onChange={handleChange}
                                    disabled={loading}
                                />
                            </Grid>
                            <Grid item xs={12}>
                                <FormControl fullWidth>
                                    <InputLabel id="gender-label">Φύλο (Προαιρετικό)</InputLabel>
                                    <Select
                                        labelId="gender-label"
                                        id="gender"
                                        name="gender"
                                        value={formData.gender}
                                        label="Φύλο (Προαιρετικό)"
                                        onChange={handleChange}
                                        disabled={loading}
                                    >
                                        <MenuItem value={''}>-- Επιλέξτε --</MenuItem>
                                        <MenuItem value={'male'}>Άνδρας</MenuItem>
                                        <MenuItem value={'female'}>Γυναίκα</MenuItem>
                                        <MenuItem value={'other'}>Άλλο</MenuItem>
                                    </Select>
                                </FormControl>
                            </Grid>
                            <Grid item xs={12}>
                                <TextField
                                    required
                                    fullWidth
                                    name="password"
                                    label="Κωδικός Πρόσβασης"
                                    type="password"
                                    id="password"
                                    autoComplete="new-password"
                                    value={formData.password}
                                    onChange={handleChange}
                                    disabled={loading}
                                />
                            </Grid>
                            <Grid item xs={12}>
                                <TextField
                                    required
                                    fullWidth
                                    name="confirmPassword"
                                    label="Επιβεβαίωση Κωδικού"
                                    type="password"
                                    id="confirmPassword"
                                    autoComplete="new-password"
                                    value={formData.confirmPassword}
                                    onChange={handleChange}
                                    disabled={loading}
                                    error={formData.password !== formData.confirmPassword}
                                    helperText={formData.password !== formData.confirmPassword ? "Οι κωδικοί δεν ταιριάζουν" : ""}
                                />
                            </Grid>
                             <Grid item xs={12}>
                                <FormControl fullWidth required error={!formData.doctor_id && error.includes('doctor')}>
                                    <InputLabel id="doctor-select-label">Επιλογή Γιατρού</InputLabel>
                                    <Select
                                        labelId="doctor-select-label"
                                        id="doctor_id"
                                        name="doctor_id"
                                        value={formData.doctor_id}
                                        label="Επιλογή Γιατρού *"
                                        onChange={handleChange}
                                        disabled={loading || doctors.length === 0}
                                    >
                                        <MenuItem value="" disabled>-- Επιλέξτε Διαθέσιμο Γιατρό --</MenuItem>
                                        {doctors.map((doctor) => (
                                            <MenuItem key={doctor.id} value={doctor.id}>
                                                {`${doctor.personal_details?.first_name} ${doctor.personal_details?.last_name} (${doctor.personal_details?.specialty || 'N/A'})`}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                        </Grid>
                        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
                        {success && <Alert severity="success" sx={{ mt: 2 }}>{success}</Alert>}
                        <Button
                            type="submit"
                            fullWidth
                            variant="contained"
                            sx={{ mt: 3, mb: 2 }}
                            disabled={loading}
                        >
                            {loading ? 'Γίνεται Εγγραφή...' : 'Εγγραφή'}
                        </Button>
                    </Box>
                </Box>
            </Container>
        </LocalizationProvider>
    );
}

export default RegisterPage; 