import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom'; // Για redirect μετά το login
import { 
    Container, 
    Box, 
    TextField, 
    Button, 
    Typography, 
    Alert 
} from '@mui/material';
import authService from '../services/authService'; // <--- ΕΙΣΑΓΩΓΗ AUTH SERVICE

function LoginPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(''); // Για εμφάνιση σφαλμάτων login
    const [loading, setLoading] = useState(false); // State για ένδειξη φόρτωσης
    const navigate = useNavigate(); // Hook για πλοήγηση

    const handleLogin = async (event) => {
        event.preventDefault(); // Αποτροπή default συμπεριφοράς φόρμας
        setError(''); // Καθαρισμός προηγούμενου σφάλματος
        setLoading(true); // Ξεκινάμε τη φόρτωση

        if (!username || !password) {
            setError('Please enter both username and password.');
            setLoading(false);
            return;
        }

        console.log('Attempting login with:', { username, password });

        try {
            // Καλούμε το authService για login γιατρού
            const data = await authService.loginDoctor(username, password);
            
            console.log('Login successful:', data);
            // Το token αποθηκεύτηκε ήδη στο localStorage από το authService
            
            // Κάνουμε redirect στο dashboard
            navigate('/dashboard'); 

        } catch (err) {
             console.error('Login failed:', err);
             // Εμφάνιση μηνύματος λάθους από το backend ή γενικό μήνυμα
             const errorMessage = err.response?.data?.error || 'Login failed. Please check your credentials.';
             setError(errorMessage);
        } finally {
            setLoading(false); // Σταματάμε τη φόρτωση σε κάθε περίπτωση
        }
    };

    return (
        <Container component="main" maxWidth="xs">
            <Box
                sx={{
                    marginTop: 8,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                }}
            >
                <Typography component="h1" variant="h5">
                    Gemini Genius - Doctor Login
                </Typography>
                <Box component="form" onSubmit={handleLogin} noValidate sx={{ mt: 1 }}>
                    <TextField
                        margin="normal"
                        required
                        fullWidth
                        id="username"
                        label="Username"
                        name="username"
                        autoComplete="username"
                        autoFocus
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        disabled={loading} // Απενεργοποίηση κατά τη φόρτωση
                    />
                    <TextField
                        margin="normal"
                        required
                        fullWidth
                        name="password"
                        label="Password"
                        type="password"
                        id="password"
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        disabled={loading} // Απενεργοποίηση κατά τη φόρτωση
                    />
                    {error && (
                        <Alert severity="error" sx={{ width: '100%', mt: 2 }}>
                            {error}
                        </Alert>
                    )}
                    <Button
                        type="submit"
                        fullWidth
                        variant="contained"
                        sx={{ mt: 3, mb: 2 }}
                        disabled={loading} // Απενεργοποίηση κουμπιού κατά τη φόρτωση
                    >
                        {loading ? 'Logging in...' : 'Login'} {/* Αλλαγή κειμένου κουμπιού */}
                    </Button>
                    {/* Μπορούμε να προσθέσουμε Link για εγγραφή ή ξεχασμένο κωδικό αργότερα */}
                </Box>
            </Box>
        </Container>
    );
}

export default LoginPage; 