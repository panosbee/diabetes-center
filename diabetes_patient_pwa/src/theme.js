// src/theme.js - PWA Patient Portal Theme
import { createTheme } from '@mui/material/styles';

// Παλέτα χρωμάτων παρόμοια με του Doctor Panel
export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2e7d8c', 
      light: '#5aacb0',
      dark: '#12525e',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#4d79b8', 
      light: '#7da0d8',
      dark: '#285299',
      contrastText: '#ffffff',
    },
    background: {
      default: '#f5f7fa', 
      paper: '#ffffff',
    },
    text: {
      primary: '#334155',
      secondary: '#5a6f85',
    },
    info: {
      main: '#2196f3',
    },
    success: {
      main: '#4caf50',
    },
    warning: {
      main: '#ff9800',
    },
    error: {
      main: '#f44336',
    },
  },
  shape: {
    borderRadius: 12, 
  },
  typography: {
    fontFamily: '"Nunito", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 600,
      fontSize: '2.2rem', // Λίγο μικρότερο για mobile
      color: '#2e7d8c',
    },
    h2: {
      fontWeight: 600,
      fontSize: '1.8rem', // Λίγο μικρότερο για mobile
      color: '#2e7d8c',
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.4rem',
    },
    h4: {
      fontWeight: 600,
      fontSize: '1.2rem',
    },
    h5: {
      fontWeight: 600,
      fontSize: '1.1rem',
    },
    h6: {
      fontWeight: 600,
      fontSize: '1rem',
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.6,
    },
    button: {
      fontWeight: 600,
      textTransform: 'none',
    },
  },
  components: {
    // Προσαρμογές για PWA/mobile αν χρειαστούν
    MuiAppBar: {
        styleOverrides: {
          root: {
            // background: 'linear-gradient(90deg, #2e7d8c 0%, #4d79b8 100%)',
            background: '#2e7d8c', // Ίσως απλό χρώμα για PWA
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            padding: '8px 16px',
          }
        }
      }
    // Μπορούμε να προσθέσουμε κι άλλα overrides
  },
}); 