import { Admin, Resource } from 'react-admin';
import { dataProvider } from './dataProvider';
import { authProvider } from './authProvider';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { theme } from './theme';
import { MyPatientList } from './MyPatientList';
import { PatientList } from './PatientList';
import { PatientEdit } from './PatientEdit';
import { PatientShow } from './PatientShow';
import { PatientCreate } from './PatientCreate';
import { DoctorList } from './DoctorList';
import { DoctorEdit } from './DoctorEdit';
import { DoctorShow } from './DoctorShow';
import { DoctorCreate } from './DoctorCreate';
import { SessionList } from './SessionList';
import { SessionEdit } from './SessionEdit';
import { SessionShow } from './SessionShow';
import { SessionCreate } from './SessionCreate';
import CustomLayout from './components/CustomLayout';
import CommonSpacePatients from './components/CommonSpacePatients';
import Dashboard from './components/Dashboard';

// Εικονίδια για τα resources
import PeopleAltIcon from '@mui/icons-material/PeopleAlt';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import EventNoteIcon from '@mui/icons-material/EventNote';
import PersonIcon from '@mui/icons-material/Person';
import PublicIcon from '@mui/icons-material/Public';

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        {/* ΔΕΝ τυλίγουμε εδώ με SocketProvider */}
        {/* <SocketProvider> */}
            <Admin 
              dataProvider={dataProvider}
              authProvider={authProvider}
              dashboard={Dashboard}
              layout={CustomLayout}
              disableTelemetry
              title="Gemini Genius Diabetes Center"
            >
              {/* Ορίζουμε τους πόρους που θα διαχειρίζεται το React-admin */}
              <Resource 
                name="patients" 
                list={PatientList} 
                edit={PatientEdit}
                show={PatientShow}
                create={PatientCreate}
                icon={PeopleAltIcon}
                options={{ label: 'Ασθενείς' }}
              />
              <Resource 
                name="doctors" 
                list={DoctorList} 
                edit={DoctorEdit}
                show={DoctorShow}
                create={DoctorCreate}
                icon={LocalHospitalIcon}
                options={{ label: 'Γιατροί' }}
              />
              <Resource 
                name="sessions" 
                list={SessionList} 
                edit={SessionEdit}
                show={SessionShow}
                create={SessionCreate}
                icon={EventNoteIcon}
                options={{ label: 'Συνεδρίες' }}
              />
              {/* Ειδικός πόρος για τους ασθενείς του γιατρού */}
              <Resource 
                name="doctor-portal/patients" 
                list={MyPatientList}
                edit={PatientEdit}
                show={PatientShow}
                icon={PersonIcon}
                options={{ label: 'Οι Ασθενείς μου' }}
              />
              
              {/* Πόρος για τους ασθενείς στον κοινό χώρο */}
              <Resource 
                name="doctor-portal/common-space/patients" 
                list={CommonSpacePatients}
                edit={PatientEdit}
                show={PatientShow}
                icon={PublicIcon}
                options={{ label: 'Κοινός Χώρος' }}
              />
            </Admin>
         {/* </SocketProvider> */}
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
