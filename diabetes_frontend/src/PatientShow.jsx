import {
    Show,
    SimpleShowLayout,
    TextField,
    EmailField,
    DateField,
    BooleanField,
    ReferenceArrayField,
    SingleFieldList,
    ChipField,
    Tab,
    TabbedShowLayout,
    ArrayField,
    Datagrid,
    useRecordContext,
    useResourceContext,
    TopToolbar,
    EditButton
} from 'react-admin';
import { Grid, Typography, Paper, Box, Divider, Chip, Alert } from '@mui/material';
import { useLocation } from 'react-router-dom';
import { RestrictedAccessMessage } from './RestrictedAccessShow';
import FileList from './components/FileList';
import PatientProgressCharts from './components/PatientProgressCharts';
import PatientAIAnalysis from './components/PatientAIAnalysis';

// --- Helper component για την καρτέλα Files --- 
const FileShowContent = () => {
    const record = useRecordContext();
    if (!record) return null;
    return <FileList patientId={record.id} />;
};
// -------------------------------------------

// Custom Actions component που εμφανίζει το EditButton μόνο για συνδεδεμένους ασθενείς
const PatientShowActions = () => {
    const resource = useResourceContext();
    const record = useRecordContext();
    
    // Έλεγχος αν είμαστε στο "Ασθενείς" panel (μη συνδεδεμένοι)
    const isUnconnectedPatientsView = resource === 'patients';
    
    // Εμφάνιση edit button μόνο για συνδεδεμένους ασθενείς
    if (isUnconnectedPatientsView) {
        return null; // Κρύβει όλα τα action buttons
    }
    
    // Για συνδεδεμένους ασθενείς, εμφάνιση edit button
    // Επίσης έλεγχος αν ο ασθενής έχει can_edit: true από το backend
    if (record && record.can_edit === false) {
        return null; // Κρύβει το edit button αν δεν έχει δικαίωμα
    }
    
    return (
        <TopToolbar>
            <EditButton />
        </TopToolbar>
    );
};

export const PatientShow = (props) => {
    const resource = useResourceContext();
    const location = useLocation();
    
    // Debug logging
    console.log('PatientShow - Current resource:', resource);
    console.log('PatientShow - Current location:', location.pathname);
    
    // Έλεγχος του URL path για να καθορίσουμε την περιοχή
    const isMyPatientsView = location.pathname.includes('/doctor-portal/patients/');
    const isCommonSpaceView = location.pathname.includes('/doctor-portal/common-space/patients/');
    const isUnconnectedPatientsView = location.pathname.includes('/patients/') && !location.pathname.includes('/doctor-portal/');
    
    // Για συνδεδεμένους ασθενείς (Οι Ασθενείς μου ή Κοινός Χώρος), δείχνουμε όλα τα tabs
    // Για μη συνδεδεμένους ασθενείς (Ασθενείς), δείχνουμε μόνο Personal Details και Files
    const showAdvancedTabs = isMyPatientsView || isCommonSpaceView;
    
    console.log('PatientShow - isMyPatientsView:', isMyPatientsView);
    console.log('PatientShow - isCommonSpaceView:', isCommonSpaceView);
    console.log('PatientShow - isUnconnectedPatientsView:', isUnconnectedPatientsView);
    console.log('PatientShow - showAdvancedTabs:', showAdvancedTabs);
    
    return (
        <Show 
            {...props} 
            title="Patient Details"
            actions={<PatientShowActions />}  // Custom actions component
        >
            <RestrictedAccessMessage />
            
            {/* Ειδοποίηση για περιορισμένη πρόσβαση στους μη συνδεδεμένους ασθενείς */}
            {isUnconnectedPatientsView && (
                <Alert severity="info" sx={{ mb: 2 }}>
                    <Typography variant="body2">
                        <strong>Περιορισμένη προβολή:</strong> Βλέπετε έναν μη συνδεδεμένο ασθενή. 
                        Για πλήρη πρόσβαση στο ιατρικό προφίλ και τα εργαλεία ανάλυσης, 
                        ο ασθενής πρέπει να είναι στους "Ασθενείς σας" ή στον "Κοινό Χώρο".
                    </Typography>
                </Alert>
            )}
            
            <TabbedShowLayout>
                <Tab label="Personal Details">
                    <TextField source="personal_details.first_name" label="First Name" />
                    <TextField source="personal_details.last_name" label="Last Name" />
                    <TextField source="personal_details.amka" label="AMKA" />
                    <DateField source="personal_details.date_of_birth" label="Date of Birth" />
                    <TextField source="personal_details.contact.phone" label="Phone" />
                    <EmailField source="personal_details.contact.email" label="Email" />
                    <TextField source="personal_details.contact.address" label="Address" />
                </Tab>
                
                {showAdvancedTabs && (
                    <Tab label="Medical Profile">
                        <TextField source="medical_profile.height_cm" label="Height (cm)" />
                        <ArrayField source="medical_profile.allergies" label="Allergies">
                            <SingleFieldList>
                                <ChipField source="" />
                            </SingleFieldList>
                        </ArrayField>
                        
                        <ArrayField source="medical_profile.conditions" label="Conditions">
                            <Datagrid bulkActionButtons={false}>
                                <TextField source="condition_name" label="Condition" />
                                <DateField source="diagnosis_date" label="Diagnosis Date" />
                            </Datagrid>
                        </ArrayField>
                        
                        <TextField source="medical_profile.medical_history_summary" label="History Summary" />
                    </Tab>
                )}
                
                <Tab label="Files">
                    <FileShowContent />
                </Tab>
                
                {showAdvancedTabs && (
                    <Tab label="Progress Charts">
                        <PatientProgressCharts />
                    </Tab>
                )}
                
                {showAdvancedTabs && (
                    <Tab label="AI Analysis">
                        <PatientAIAnalysis />
                    </Tab>
                )}
            </TabbedShowLayout>
        </Show>
    );
};

// Helper component για την καρτέλα Files για να έχουμε πρόσβαση στο record
// ... FileShowContent code ... 