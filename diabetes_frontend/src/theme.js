import { createTheme } from '@mui/material/styles';

// Παλέτα χρωμάτων για ιατρική εφαρμογή - ξεκούραστη για τα μάτια
// Βασικά χρώματα: μπλε-πράσινο, μπλε, λευκό, απαλό γκρι
export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2e7d8c', // Καθαρό πράσινο-μπλε (teal) - ιατρικό χρώμα
      light: '#5aacb0',
      dark: '#12525e',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#4d79b8', // Ανοιχτό μπλε - ξεκούραστο
      light: '#7da0d8',
      dark: '#285299',
      contrastText: '#ffffff',
    },
    background: {
      default: '#f5f7fa', // Πολύ απαλό γκρι, σχεδόν λευκό
      paper: '#ffffff',
    },
    text: {
      primary: '#334155', // Σκούρο γκρι-μπλε αντί για μαύρο - λιγότερο κουραστικό
      secondary: '#5a6f85', // Μεσαίο γκρι-μπλε
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
    borderRadius: 12, // Πιο στρογγυλεμένες γωνίες για μοντέρνα εμφάνιση
  },
  typography: {
    fontFamily: '"Nunito", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 600,
      fontSize: '2.5rem',
      color: '#2e7d8c',
    },
    h2: {
      fontWeight: 600,
      fontSize: '2rem',
      color: '#2e7d8c',
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.5rem',
    },
    h4: {
      fontWeight: 600,
      fontSize: '1.25rem',
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
      textTransform: 'none', // Buttons χωρίς κεφαλαία για καλύτερη αναγνωσιμότητα
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)', // Πιο απαλές σκιές για τις κάρτες
          borderRadius: 16,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 16px',
          fontWeight: 600,
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)',
          },
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #2e7d8c 0%, #319da8 100%)', // Gradient για τα κουμπιά
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.08)',
          background: 'linear-gradient(90deg, #2e7d8c 0%, #4d79b8 100%)', // Gradient AppBar
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 600,
          backgroundColor: 'rgba(46, 125, 140, 0.05)', // Ελαφριά απόχρωση του primary για τις επικεφαλίδες
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:nth-of-type(even)': {
            backgroundColor: 'rgba(0, 0, 0, 0.02)', // Ελαφρύ γκρι για καλύτερη αναγνωσιμότητα στις σειρές
          },
          '&:hover': {
            backgroundColor: 'rgba(46, 125, 140, 0.08)', // Ελαφρύ hover effect
          },
        },
      },
    },
    MuiInputBase: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: '#2e7d8c',
          },
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: 'rgba(46, 125, 140, 0.08)',
          },
          '&.Mui-selected': {
            backgroundColor: 'rgba(46, 125, 140, 0.12)',
            '&:hover': {
              backgroundColor: 'rgba(46, 125, 140, 0.18)',
            },
          },
        },
      },
    },
    MuiDataGrid: {
      styleOverrides: {
        root: {
          border: 'none',
          '& .MuiDataGrid-cell:focus': {
            outline: 'none',
          },
          '& .MuiDataGrid-columnHeader:focus': {
            outline: 'none',
          },
        },
        columnHeaders: {
          backgroundColor: 'rgba(46, 125, 140, 0.05)',
        },
        row: {
          '&:nth-of-type(even)': {
            backgroundColor: 'rgba(0, 0, 0, 0.02)',
          },
          '&:hover': {
            backgroundColor: 'rgba(46, 125, 140, 0.08)',
          },
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          '&.Mui-selected': {
            color: '#2e7d8c',
          },
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: {
          backgroundColor: '#2e7d8c',
        },
      },
    },
  },
}); 