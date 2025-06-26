import React, { useState, useEffect } from 'react';
import { 
    Card, 
    CardContent, 
    Typography, 
    CircularProgress, 
    Alert, 
    Box, 
    Avatar, 
    Button,
    CardActions
} from '@mui/material';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import { getProfile } from '../dataProvider';
import { authProvider } from '../authProvider';
import { Link as RouterLink } from 'react-router-dom';

function ProfileSummary() {
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const loadProfile = async () => {
            setLoading(true);
            setError('');
            try {
                const { data } = await getProfile();
                setProfile(data);
            } catch (err) {
                console.error("Profile Summary loading error:", err);
                authProvider.checkError(err).catch(() => {
                    setError(err.message || 'Failed to load profile summary.');
                });
            } finally {
                setLoading(false);
            }
        };
        loadProfile();
    }, []);

    if (loading) {
        return (
             <Card elevation={3}>
                <CardContent sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100px' }}>
                    <CircularProgress size={30} />
                 </CardContent>
            </Card>
        );
    }

    if (error) {
        return <Alert severity="error" sx={{ mt: 1, mb: 1 }}>{error}</Alert>;
    }

    if (!profile) {
        return <Typography>No profile data.</Typography>;
    }

    return (
        <Card elevation={3}>
            <CardContent sx={{ display: 'flex', alignItems: 'center' }}>
                <Avatar sx={{ bgcolor: 'primary.main', width: 56, height: 56, mr: 2 }}>
                    <AccountCircleIcon sx={{ fontSize: 40 }} />
                </Avatar>
                <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="h6">{`${profile.first_name} ${profile.last_name}`}</Typography>
                    <Typography variant="body2" color="text.secondary">
                        AMKA: {profile.amka || '-'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Email: {profile.email || '-'}
                    </Typography>
                </Box>
            </CardContent>
            <CardActions sx={{ justifyContent: 'flex-end' }}>
                <Button size="small" component={RouterLink} to="/profile">
                    Προβολή & Επεξεργασία Προφίλ
                </Button>
            </CardActions>
        </Card>
    );
}

export default ProfileSummary; 