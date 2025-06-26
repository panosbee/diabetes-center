import { List, Datagrid, TextField, EditButton, TextInput } from 'react-admin';

// --- ΝΕΟ: Component για τα φίλτρα --- 
const MyPatientFilters = [
    <TextInput label="Αναζήτηση με ΑΜΚΑ" source="amka_filter" alwaysOn />
];
// -----------------------------------

export const MyPatientList = (props) => (
    <List 
        {...props} 
        resource="doctor-portal/patients" 
        title="My Patients"
        filters={MyPatientFilters} // <-- Προσθήκη φίλτρων
    >
        <Datagrid rowClick="edit">
            {/* Το source ταιριάζει με τα κλειδιά που επιστρέφει το API */}
            {/* Για πεδία μέσα σε objects, χρησιμοποιούμε dot notation */}
            <TextField source="personal_details.first_name" label="First Name" />
            <TextField source="personal_details.last_name" label="Last Name" />
            <TextField source="personal_details.amka" label="AMKA" />
            <EditButton />
        </Datagrid>
 
    </List>
); 