import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Container, 
    TextField, 
    Button, 
    Typography, 
    Box, 
    Grid, 
    Alert, 
    Link as MuiLink // Μετονομασία για αποφυγή σύγκρουσης με Link του router
} from '@mui/material';
import { Link } from 'react-router-dom'; // Link για πλοήγηση
// Ξεσχολιάζουμε την εισαγωγή του authProvider
import { authProvider } from '../authProvider'; 

function LoginPage() {
    const [formData, setFormData] = useState({
        email: '',
        password: ''
    });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleChange = (event) => {
        const { name, value } = event.target;
        setFormData(prevState => ({
            ...prevState,
            [name]: value
        }));
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError('');
        setLoading(true);

        try {
            // Χρήση του authProvider για τη σύνδεση
            // Το username για τον authProvider είναι το email εδώ
            await authProvider.login({ username: formData.email, password: formData.password });
            
            // Επιτυχής σύνδεση - Ανακατεύθυνση στο Dashboard
            navigate('/dashboard'); 

        } catch (err) {
            setError(err.message || 'Login failed. Please check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Container maxWidth="xs"> {/* Μικρότερο container για login */} 
            <Box sx={{ marginTop: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography component="h1" variant="h5">
                    Σύνδεση Ασθενή
                </Typography>
                <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
                    <TextField
                        margin="normal"
                        required
                        fullWidth
                        id="email"
                        label="Διεύθυνση Email"
                        name="email"
                        type="email"
                        autoComplete="email"
                        autoFocus
                        value={formData.email}
                        onChange={handleChange}
                        disabled={loading}
                    />
                    <TextField
                        margin="normal"
                        required
                        fullWidth
                        name="password"
                        label="Κωδικός Πρόσβασης"
                        type="password"
                        id="password"
                        autoComplete="current-password"
                        value={formData.password}
                        onChange={handleChange}
                        disabled={loading}
                    />
                    {/* Κάποια στιγμή ίσως προσθέσουμε "Remember me" Checkbox */} 
                    {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
                    <Button
                        type="submit"
                        fullWidth
                        variant="contained"
                        sx={{ mt: 3, mb: 2 }}
                        disabled={loading}
                    >
                        {loading ? 'Γίνεται Σύνδεση...' : 'Σύνδεση'}
                    </Button>
                    <Grid container justifyContent="flex-end">
                        <Grid item>
                            {/* Link προς τη σελίδα εγγραφής */}
                            <MuiLink component={Link} to="/register" variant="body2">
                                {"Δεν έχετε λογαριασμό; Εγγραφή"}
                            </MuiLink>
                        </Grid>
                        {/* Κάποια στιγμή ίσως προσθέσουμε Link για "Forgot password?" */}
                    </Grid>
                </Box>
            </Box>
        </Container>
    );
}

export default LoginPage; 