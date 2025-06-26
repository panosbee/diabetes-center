import React, { useState } from 'react';
import { 
    AppBar, 
    Toolbar, 
    IconButton, 
    Typography, 
    Drawer, 
    List, 
    ListItem, 
    ListItemButton,
    ListItemIcon, 
    ListItemText, 
    Box, 
    Divider 
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import FolderIcon from '@mui/icons-material/Folder';
import EventNoteIcon from '@mui/icons-material/EventNote';
import RestaurantIcon from '@mui/icons-material/Restaurant';
import LogoutIcon from '@mui/icons-material/Logout';
import { Link as RouterLink, useNavigate } from 'react-router-dom'; // Link για πλοήγηση
import { authProvider } from '../authProvider';

const drawerWidth = 240;

function PwaLayout({ children }) {
    const [mobileOpen, setMobileOpen] = useState(false);
    const navigate = useNavigate();

    const handleDrawerToggle = () => {
        setMobileOpen(!mobileOpen);
    };
    
    const handleLogout = () => {
        authProvider.logout();
        navigate('/login'); 
    };

    const drawer = (
        <div>
            <Toolbar /> {/* Spacer για να είναι κάτω από το AppBar */} 
            <Divider />
            <List>
                <ListItemButton component={RouterLink} to="/dashboard">
                    <ListItemIcon><DashboardIcon /></ListItemIcon>
                    <ListItemText primary="Dashboard" />
                </ListItemButton>
                <ListItemButton component={RouterLink} to="/profile">
                    <ListItemIcon><AccountCircleIcon /></ListItemIcon>
                    <ListItemText primary="Προφίλ" />
                </ListItemButton>
                 <ListItemButton component={RouterLink} to="/files">
                    <ListItemIcon><FolderIcon /></ListItemIcon>
                    <ListItemText primary="Αρχεία" />
                </ListItemButton>
                <ListItemButton component={RouterLink} to="/sessions">
                    <ListItemIcon><EventNoteIcon /></ListItemIcon>
                    <ListItemText primary="Συνεδρίες" />
                </ListItemButton>
                <ListItemButton component={RouterLink} to="/food">
                    <ListItemIcon><RestaurantIcon /></ListItemIcon>
                    <ListItemText primary="Αναζήτηση Τροφής" />
                </ListItemButton>
                {/* TODO: Προσθήκη links για CGM, Telemedicine */}
            </List>
            <Divider />
            <List>
                <ListItemButton onClick={handleLogout}>
                    <ListItemIcon><LogoutIcon /></ListItemIcon>
                    <ListItemText primary="Αποσύνδεση" />
                </ListItemButton>
            </List>
        </div>
    );

    return (
        <Box sx={{ display: 'flex' }}>
            <AppBar 
                position="fixed"
                sx={{ 
                    zIndex: (theme) => theme.zIndex.drawer + 1 // Πάνω από το drawer
                }}
            >
                <Toolbar>
                    <IconButton
                        color="inherit"
                        aria-label="open drawer"
                        edge="start"
                        onClick={handleDrawerToggle}
                        sx={{ mr: 2 }}
                    >
                        <MenuIcon />
                    </IconButton>
                    <Typography variant="h6" noWrap component="div">
                        GGDC Patient Portal
                    </Typography>
                </Toolbar>
            </AppBar>
            <Drawer
                variant="temporary"
                open={mobileOpen}
                onClose={handleDrawerToggle}
                ModalProps={{
                    keepMounted: true, // Better open performance on mobile.
                }}
                sx={{
                    '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
                }}
            >
                {drawer}
            </Drawer>
            {/* Κύριο Περιεχόμενο */}
            <Box 
                component="main"
                sx={{ flexGrow: 1, p: 3, width: { sm: `calc(100% - ${drawerWidth}px)` } }}
            >
                <Toolbar /> {/* Spacer για να είναι κάτω από το AppBar */}
                {children} {/* Εδώ θα μπει η εκάστοτε σελίδα */}
            </Box>
        </Box>
    );
}

export default PwaLayout; 