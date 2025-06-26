import React from 'react';
import { 
    List, 
    Datagrid, 
    TextField, 
    DateField, 
    BooleanField, 
    ReferenceField,
    EditButton,
    ShowButton, 
    FunctionField,
    useNotify,
    useRefresh,
    TopToolbar,
    FilterButton,
    TextInput,
    Button,
    useRecordContext
} from 'react-admin';
import { Box, Typography, Chip, Tooltip } from '@mui/material';
import PublicIcon from '@mui/icons-material/Public';
import PersonIcon from '@mui/icons-material/Person';

// Φίλτρα για τη λίστα ασθενών του κοινού χώρου
const CommonSpaceFilters = [
    <TextInput source="q" alwaysOn label="Αναζήτηση" />,
    <TextInput source="personal_details.amka" label="ΑΜΚΑ" />,
];

// Component για τη γρήγορη αφαίρεση από τον κοινό χώρο
const RemoveFromCommonSpaceButton = () => {
    const record = useRecordContext();
    const notify = useNotify();
    const refresh = useRefresh();
    
    if (!record) return null;
    
    const handleRemoveFromCommonSpace = async () => {
        try {
            // Λήψη του JWT token από το localStorage
            const token = localStorage.getItem('token');
            if (!token) {
                throw new Error('Authentication token not found');
            }
            
            // Κλήση στο backend για την αλλαγή του common space
            const response = await fetch(`${import.meta.env.VITE_API_URL}/api/patients/${record.id}/common-space`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ is_in_common_space: false })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Unknown error occurred');
            }
            
            // Ενημέρωση του UI
            notify('Ο ασθενής αφαιρέθηκε από τον κοινό χώρο', { type: 'success' });
            
            // Ανανέωση των δεδομένων
            refresh();
        } catch (error) {
            notify(`Σφάλμα: ${error.message}`, { type: 'error' });
        }
    };
    
    return (
        <Button
            label="Αφαίρεση από Common Space"
            onClick={handleRemoveFromCommonSpace}
            color="warning"
        />
    );
};

// Component για την προβολή των ασθενών στον κοινό χώρο
const CommonSpacePatients = (props) => {
    return (
        <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <PublicIcon color="primary" sx={{ mr: 1, fontSize: '2rem' }} />
                <Typography variant="h5">Ασθενείς στον Κοινό Χώρο</Typography>
            </Box>
            
            <List
                {...props}
                resource="doctor-portal/common-space/patients"
                filters={CommonSpaceFilters}
                sort={{ field: 'personal_details.last_name', order: 'ASC' }}
                actions={
                    <TopToolbar>
                        <FilterButton />
                    </TopToolbar>
                }
                emptyWhileLoading
            >
                <Datagrid bulkActionButtons={false}>
                    <TextField source="personal_details.first_name" label="Όνομα" />
                    <TextField source="personal_details.last_name" label="Επώνυμο" />
                    <TextField source="personal_details.amka" label="ΑΜΚΑ" />
                    <DateField source="personal_details.date_of_birth" label="Ημ. Γέννησης" />
                    <TextField source="medical_history.diabetes_type" label="Τύπος Διαβήτη" />
                    <FunctionField 
                        label="Ανατεθειμένοι Γιατροί" 
                        render={record => 
                            record.assigned_doctors?.length 
                                ? <Chip 
                                    label={record.assigned_doctors.length} 
                                    color="primary" 
                                    icon={<PersonIcon />} 
                                  /> 
                                : <Chip label="Κανένας" variant="outlined" />
                        } 
                    />
                    <BooleanField source="has_access" label="Μπορώ να Επεξεργαστώ" />
                    <ShowButton label="Προβολή" />
                    <EditButton label="Επεξεργασία" />
                    <RemoveFromCommonSpaceButton />
                </Datagrid>
            </List>
        </Box>
    );
};

export default CommonSpacePatients; 