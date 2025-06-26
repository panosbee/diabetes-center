import React, { useState, useEffect } from 'react';
import { 
    Container, 
    Typography, 
    Box, 
    CircularProgress, 
    Alert, 
    Card, 
    CardContent, 
    CardActions, 
    Button, 
    Grid, 
    TextField
} from '@mui/material';
import { getProfile, updateProfile } from '../dataProvider'; // Εισαγωγή των συναρτήσεων API
import { authProvider } from '../authProvider'; // Για έλεγχο σφαλμάτων αυθεντικοποίησης
import { useNavigate } from 'react-router-dom';

function ProfilePage() {
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [editMode, setEditMode] = useState(false);
    const [editData, setEditData] = useState({ email: '', phone: '', address: '' });
    const [updateLoading, setUpdateLoading] = useState(false);
    const [updateError, setUpdateError] = useState('');
    const [updateSuccess, setUpdateSuccess] = useState('');
    const navigate = useNavigate();

    // Φόρτωση προφίλ
    useEffect(() => {
        const loadProfile = async () => {
            setLoading(true);
            setError('');
            try {
                const { data } = await getProfile();
                setProfile(data);
                // Αρχικοποίηση φόρμας επεξεργασίας
                setEditData({
                    email: data.email || '',
                    phone: data.phone || '',
                    address: data.address || ''
                });
            } catch (err) {
                console.error("Profile loading error:", err);
                // Έλεγχος αν είναι σφάλμα αυθεντικοποίησης
                authProvider.checkError(err).catch(() => {
                    // Αν το checkError κάνει reject (π.χ. 401), ο authProvider θα ανακατευθύνει
                    // Αλλιώς, δείχνουμε το σφάλμα
                    setError(err.message || 'Failed to load profile.');
                });
            } finally {
                setLoading(false);
            }
        };

        loadProfile();
    }, []); // Κενό dependency array για να τρέξει μόνο μια φορά

    const handleEditChange = (event) => {
        const { name, value } = event.target;
        setEditData(prevState => ({
            ...prevState,
            [name]: value
        }));
    };

    const handleUpdateSubmit = async (event) => {
        event.preventDefault();
        setUpdateLoading(true);
        setUpdateError('');
        setUpdateSuccess('');

        try {
            // Φιλτράρουμε για να στείλουμε μόνο τα πεδία που έχουν αλλάξει
            const changedData = {};
            if (editData.email !== profile.email) changedData.email = editData.email;
            if (editData.phone !== profile.phone) changedData.phone = editData.phone;
            if (editData.address !== profile.address) changedData.address = editData.address;

            if (Object.keys(changedData).length === 0) {
                setUpdateSuccess("No changes detected.");
                setEditMode(false);
                setUpdateLoading(false);
                return;
            }

            await updateProfile(changedData);
            setUpdateSuccess('Profile updated successfully!');
            // Ενημέρωση της τοπικής κατάστασης του προφίλ
            setProfile(prev => ({...prev, ...changedData})); 
            setEditMode(false);
        } catch (err) {
            console.error("Profile update error:", err);
             authProvider.checkError(err).catch(() => {
                 setUpdateError(err.message || 'Failed to update profile.');
             });
        } finally {
            setUpdateLoading(false);
        }
    };

    if (loading) {
        return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}><CircularProgress /></Box>;
    }

    if (error) {
        return <Container><Alert severity="error" sx={{ mt: 2 }}>{error}</Alert></Container>;
    }

    if (!profile) {
        return <Container><Alert severity="warning" sx={{ mt: 2 }}>Could not load profile data.</Alert></Container>;
    }

    return (
        <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
            <Typography variant="h4" component="h1" gutterBottom>
                Το Προφίλ μου
            </Typography>
            
            {updateError && <Alert severity="error" sx={{ mb: 2 }}>{updateError}</Alert>}
            {updateSuccess && <Alert severity="success" sx={{ mb: 2 }}>{updateSuccess}</Alert>}

            <Card>
                <CardContent>
                    {!editMode ? (
                        // --- Προβολή Στοιχείων --- 
                        <Grid container spacing={2}>
                            <Grid item xs={12} sm={6}><Typography><strong>Όνομα:</strong> {profile.first_name}</Typography></Grid>
                            <Grid item xs={12} sm={6}><Typography><strong>Επώνυμο:</strong> {profile.last_name}</Typography></Grid>
                            <Grid item xs={12} sm={6}><Typography><strong>ΑΜΚΑ:</strong> {profile.amka}</Typography></Grid>
                            <Grid item xs={12} sm={6}><Typography><strong>Ημ/νία Γέννησης:</strong> {profile.date_of_birth}</Typography></Grid>
                            <Grid item xs={12} sm={6}><Typography><strong>Φύλο:</strong> {profile.gender || '-'}</Typography></Grid>
                            <Grid item xs={12} sm={6}><Typography><strong>Email:</strong> {profile.email || '-'}</Typography></Grid>
                            <Grid item xs={12} sm={6}><Typography><strong>Τηλέφωνο:</strong> {profile.phone || '-'}</Typography></Grid>
                            <Grid item xs={12} sm={6}><Typography><strong>Διεύθυνση:</strong> {profile.address || '-'}</Typography></Grid>
                        </Grid>
                    ) : (
                        // --- Φόρμα Επεξεργασίας --- 
                        <Box component="form" onSubmit={handleUpdateSubmit}>
                            <Grid container spacing={2}>
                                <Grid item xs={12}><Typography variant="h6">Επεξεργασία Στοιχείων Επικοινωνίας</Typography></Grid>
                                <Grid item xs={12}>
                                    <TextField
                                        fullWidth
                                        margin="normal"
                                        id="email"
                                        label="Διεύθυνση Email"
                                        name="email"
                                        type="email"
                                        value={editData.email}
                                        onChange={handleEditChange}
                                        disabled={updateLoading}
                                    />
                                </Grid>
                                <Grid item xs={12}>
                                     <TextField
                                        fullWidth
                                        margin="normal"
                                        id="phone"
                                        label="Τηλέφωνο"
                                        name="phone"
                                        type="tel"
                                        value={editData.phone}
                                        onChange={handleEditChange}
                                        disabled={updateLoading}
                                    />
                                </Grid>
                                <Grid item xs={12}>
                                     <TextField
                                        fullWidth
                                        margin="normal"
                                        id="address"
                                        label="Διεύθυνση"
                                        name="address"
                                        value={editData.address}
                                        onChange={handleEditChange}
                                        disabled={updateLoading}
                                    />
                                </Grid>
                                <Grid item xs={12} sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                                    <Button onClick={() => setEditMode(false)} sx={{ mr: 1 }} disabled={updateLoading}>
                                        Άκυρο
                                    </Button>
                                    <Button type="submit" variant="contained" disabled={updateLoading}>
                                        {updateLoading ? 'Αποθήκευση...' : 'Αποθήκευση'}
                                    </Button>
                                </Grid>
                            </Grid>
                        </Box>
                    )}
                </CardContent>
                {!editMode && (
                    <CardActions sx={{ justifyContent: 'flex-end' }}>
                        <Button size="small" onClick={() => setEditMode(true)}>Επεξεργασία Στοιχείων Επικοινωνίας</Button>
                    </CardActions>
                )}
            </Card>
        </Container>
    );
}

export default ProfilePage; 