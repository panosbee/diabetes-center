import React from 'react';
import { Layout, AppBar, UserMenu, Sidebar } from 'react-admin';
import { Box, Typography, useMediaQuery, Toolbar, Avatar } from '@mui/material';
import FloatingAIChatButton from '../FloatingAIChatButton';
import { alpha, useTheme } from '@mui/material/styles';
import DiabetesLogo from './DiabetesLogo';
import { SocketProvider } from '../contexts/SocketContext';

// Προσαρμοσμένο AppBar
const CustomAppBar = (props) => {
  const theme = useTheme();
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'));
  
  return (
    <AppBar
      {...props}
      elevation={1}
      sx={{
        '& .RaAppBar-toolbar': {
          height: 64,
        },
      }}
    >
      <Toolbar
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          height: 64,
          padding: theme => theme.spacing(0, 2),
        }}
      >
        <Box 
          display="flex" 
          alignItems="center" 
          gap={1}
        >
          <DiabetesLogo size={40} />
          {!isSmall && (
            <Typography 
              variant="h6" 
              sx={{ 
                fontWeight: 700,
                fontSize: '1.2rem',
                letterSpacing: '0.5px',
                color: 'white',
                textShadow: '0 1px 2px rgba(0,0,0,0.1)',
              }}
            >
              Digital Diabetes Center
            </Typography>
          )}
        </Box>
        <Box display="flex" alignItems="center">
          <UserMenu />
        </Box>
      </Toolbar>
    </AppBar>
  );
};

// Προσαρμοσμένο Sidebar
const CustomSidebar = (props) => {
  const theme = useTheme();
  
  return (
    <Sidebar
      {...props}
      sx={{
        '& .RaSidebar-fixed': {
          boxShadow: '2px 0 8px 0 rgba(0,0,0,0.05)',
          borderRight: `1px solid ${alpha(theme.palette.primary.main, 0.08)}`,
          backgroundColor: '#ffffff',
        },
        '& .RaMenuItemLink-active': {
          borderLeft: `3px solid ${theme.palette.primary.main}`,
          backgroundColor: alpha(theme.palette.primary.main, 0.08),
          color: theme.palette.primary.main,
          fontWeight: 600,
          '& .MuiSvgIcon-root': {
            color: theme.palette.primary.main,
          },
        },
        '& .MuiListItemButton-root': {
          borderRadius: '0 8px 8px 0',
          margin: '4px 8px 4px 0',
          padding: '8px 12px',
          transition: 'all 0.2s ease',
          '&:hover': {
            backgroundColor: alpha(theme.palette.primary.main, 0.04),
            '& .MuiSvgIcon-root': {
              color: theme.palette.primary.main,
            },
          },
        },
        '& .MuiListItemIcon-root': {
          minWidth: 40,
        },
        '& .MuiListItemText-root': {
          margin: 0,
          '& .MuiTypography-root': {
            fontSize: '0.95rem',
            fontWeight: 500,
          },
        },
      }}
    />
  );
};

// Προσαρμοσμένο UserMenu
const CustomUserMenu = props => (
  <UserMenu {...props}>
    <UserMenuItem />
  </UserMenu>
);

const UserMenuItem = () => {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: 2,
        minWidth: 220,
      }}
    >
      <Avatar
        sx={{
          width: 64,
          height: 64,
          bgcolor: theme => theme.palette.primary.main,
          mb: 2,
        }}
      />
      <Typography variant="body1" fontWeight={600}>
        Δρ. Κώστας Παπαδόπουλος
      </Typography>
      <Typography variant="body2" color="textSecondary">
        Ενδοκρινολόγος
      </Typography>
    </Box>
  );
};

// Custom Layout συνδυάζει όλα τα προσαρμοσμένα components
const CustomLayout = props => (
  <>
    <SocketProvider>
        <Layout
          {...props}
          appBar={CustomAppBar}
          sidebar={CustomSidebar}
          sx={{
            '& .RaLayout-content': {
              padding: theme => theme.spacing(2),
              backgroundColor: theme => theme.palette.background.default,
            },
          }}
        />
    </SocketProvider>
    <FloatingAIChatButton />
  </>
);

export default CustomLayout;