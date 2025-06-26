import React from 'react';
import { SvgIcon, Box } from '@mui/material';

// Ένα μοντέρνο και επαγγελματικό λογότυπο για την εφαρμογή διαχείρισης διαβήτη
const DiabetesLogo = ({ size = 40 }) => {
  return (
    <Box
      sx={{
        width: size,
        height: size,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <SvgIcon
        viewBox="0 0 24 24"
        sx={{
          width: size,
          height: size,
          filter: 'drop-shadow(0 1px 3px rgba(0,0,0,0.2))',
        }}
      >
        {/* Κύκλος που αντιπροσωπεύει τον αντίκτυπο του διαβήτη */}
        <circle cx="12" cy="12" r="9" fill="#ffffff" />
        
        {/* Το G για το "Gemini Genius" */}
        <path
          d="M12 3.5C7.3 3.5 3.5 7.3 3.5 12C3.5 16.7 7.3 20.5 12 20.5C16.7 20.5 20.5 16.7 20.5 12C20.5 7.3 16.7 3.5 12 3.5ZM12 19C8.13 19 5 15.87 5 12C5 8.13 8.13 5 12 5C15.87 5 19 8.13 19 12C19 15.87 15.87 19 12 19Z"
          fill="#2e7d8c"
        />
        
        {/* Το σύμβολο σταγόνας/γλυκόζης */}
        <path
          d="M12 7.5C11.2 7.5 10.5 8.2 10.5 9C10.5 9.8 11.2 10.5 12 10.5C12.8 10.5 13.5 9.8 13.5 9C13.5 8.2 12.8 7.5 12 7.5Z"
          fill="#4d79b8"
        />
        
        {/* Καμπύλη που αντιπροσωπεύει το διάγραμμα γλυκόζης */}
        <path
          d="M16.5 12.5C16.5 12.5 14 14.5 12 14.5C10 14.5 7.5 12.5 7.5 12.5"
          stroke="#2e7d8c"
          strokeWidth="1.5"
          strokeLinecap="round"
          fill="none"
        />
        
        {/* Δεύτερη καμπύλη διαγράμματος γλυκόζης */}
        <path
          d="M16.5 16C16.5 16 14 14 12 14C10 14 7.5 16 7.5 16"
          stroke="#4d79b8"
          strokeWidth="1.5"
          strokeLinecap="round"
          fill="none"
        />
      </SvgIcon>
    </Box>
  );
};

export default DiabetesLogo; 