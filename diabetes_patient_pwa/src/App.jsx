import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
// Εισαγωγές για routing
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
// Εισαγωγή σελίδων
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage'; // Νέα σελίδα Dashboard
import ProfilePage from './pages/ProfilePage'; // Νέα σελίδα Profile
import FilesPage from './pages/FilesPage';
import SessionsPage from './pages/SessionsPage';
import SessionDetailPage from './pages/SessionDetailPage'; // Νέα σελίδα Λεπτομερειών
import FoodSearchPage from './pages/FoodSearchPage'; // Νέα σελίδα Αναζήτησης Τροφής
// Εισαγωγές για MUI Date Picker
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
// Εισαγωγή PrivateRoute
import PrivateRoute from './components/PrivateRoute'; 
// Εισαγωγή Layout & PrivateRoute
import PwaLayout from './components/PwaLayout'; 
// MUI Imports
import { ThemeProvider, CssBaseline } from '@mui/material'; // Προσθήκη ThemeProvider & CssBaseline
import { theme } from './theme'; // Εισαγωγή του θέματος

// --- Import Socket Provider ---
import { SocketProvider } from './contexts/SocketContext'; 
// ----------------------------

function Home() {
  return (
    <div>
      <h1>GGDC Patient Portal (PWA)</h1>
      <nav>
        <ul>
          <li><Link to="/login">Σύνδεση</Link></li>
          <li><Link to="/register">Εγγραφή</Link></li>
          {/* Προσωρινό link για το Dashboard για δοκιμές */} 
          <li><Link to="/dashboard">Dashboard (Protected)</Link></li> 
        </ul>
      </nav>
      {/* Εδώ θα μπει το περιεχόμενο του Dashboard όταν ο χρήστης συνδεθεί */}
    </div>
  );
}

function App() {
  return (
    <ThemeProvider theme={theme}> {/* Εφαρμογή του θέματος */} 
      <CssBaseline /> {/* Εφαρμογή βασικών στυλ για συνέπεια */} 
      <LocalizationProvider dateAdapter={AdapterDayjs}>
        {/* Τυλίγουμε το BrowserRouter με τον SocketProvider */}
        <SocketProvider tokenKey="patient_access_token"> {/* <-- ΣΗΜΑΝΤΙΚΟ: Χρήση του token ασθενή */}
          <BrowserRouter>
            <Routes>
              {/* Δημόσιες Διαδρομές */}
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              
              {/* Προστατευμένες Διαδρομές με Layout */}
              <Route 
                path="/" 
                element={
                  <PrivateRoute>
                    <PwaLayout><DashboardPage /></PwaLayout> 
                  </PrivateRoute>
                }
              />
               <Route 
                path="/dashboard" 
                element={<PrivateRoute><PwaLayout><DashboardPage /></PwaLayout></PrivateRoute>}
              />
              <Route 
                path="/profile" 
                element={<PrivateRoute><PwaLayout><ProfilePage /></PwaLayout></PrivateRoute>}
              />
               <Route 
                path="/files" 
                element={<PrivateRoute><PwaLayout><FilesPage /></PwaLayout></PrivateRoute>}
              />
               <Route 
                path="/sessions" 
                element={<PrivateRoute><PwaLayout><SessionsPage /></PwaLayout></PrivateRoute>}
              />
              {/* Νέα διαδρομή για λεπτομέρειες συνεδρίας */}
              <Route path="/session/:sessionId" element={<PrivateRoute><PwaLayout><SessionDetailPage /></PwaLayout></PrivateRoute>} />
              <Route
                path="/food"
                element={<PrivateRoute><PwaLayout><FoodSearchPage /></PwaLayout></PrivateRoute>}
              />
              
              {/* TODO: Άλλες διαδρομές (π.χ. CGM, Telemedicine) */}
              
              {/* Fallback Route (π.χ., 404) - Προαιρετικό */}
              {/* <Route path="*" element={<NotFoundPage />} /> */}
            </Routes>
          </BrowserRouter>
        </SocketProvider>
      </LocalizationProvider>
    </ThemeProvider>
  )
}

export default App
