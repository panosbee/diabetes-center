import { 
    List, 
    Datagrid, 
    TextField, 
    EmailField, // Αν έχουμε email γιατρού
    EditButton,
    ShowButton,
    useGetIdentity, // <-- Επαναφέρουμε τα hooks
    useRecordContext // <-- Επαναφέρουμε τα hooks
} from 'react-admin';

// Custom component για τα κουμπιά που εμφανίζονται υπό συνθήκη
const DoctorListActions = () => {
    const { identity, isLoading } = useGetIdentity(); 
    const record = useRecordContext(); 
    
    if (isLoading || !record || !identity) { 
        return <ShowButton />;
    }

    // Έλεγχος αν ο γιατρός βλέπει τον εαυτό του
    const isSelf = record.id === identity.id;
    
    // Εμφάνιση EditButton μόνο αν είναι ο ίδιος γιατρός, αλλιώς ShowButton
    return isSelf ? (
        <>
            <ShowButton />
            <EditButton />
        </>
    ) : (
        <ShowButton />
    );
};

export const DoctorList = (props) => (
    <List {...props} title="All Doctors">
        <Datagrid rowClick="show">
            <TextField source="personal_details.first_name" label="First Name" />
            <TextField source="personal_details.last_name" label="Last Name" />
            <TextField source="personal_details.specialty" label="Specialty" />
            {/* Αν θέλουμε να δείχνουμε το email από personal_details.contact */}
            {/* <EmailField source="personal_details.contact.email" label="Email" /> */}
            <TextField source="availability_status" label="Availability" />
            <DoctorListActions />
        </Datagrid>
    </List>
); 