import {
    Edit,
    SimpleForm,
    TextInput,
    SelectInput, 
    Toolbar, 
    SaveButton, 
    DeleteButton,
    useGetIdentity,
    useRecordContext
} from 'react-admin';

// Custom Toolbar για τη φόρμα Edit Γιατρού
const DoctorEditToolbar = () => {
    const { identity, isLoading: identityLoading } = useGetIdentity();
    const record = useRecordContext();

    if (identityLoading || !record || !identity) return null;

    // Έλεγχος αν ο συνδεδεμένος χρήστης επεξεργάζεται το δικό του προφίλ
    const canEdit = record.id === identity.id;

    console.log(`[DoctorEditToolbar] Checking permissions for doctor ${record.id}: Can Edit = ${canEdit}`);

    return (
        <Toolbar>
            {/* Εμφανίζουμε τα κουμπιά ΜΟΝΟ αν ο χρήστης επεξεργάζεται τον εαυτό του */}
            {canEdit && <SaveButton />}
            {canEdit && <DeleteButton mutationMode="pessimistic" />}
        </Toolbar>
    );
};

export const DoctorEdit = (props) => (
    // Χρησιμοποιούμε το Edit χωρίς το actions prop
    <Edit {...props} title="Edit Doctor Profile">
        <SimpleForm toolbar={<DoctorEditToolbar />}>
            {/* Δεν επιτρέπουμε αλλαγή ID */}
            <TextInput source="id" disabled /> 
            
            {/* Προσωπικά Στοιχεία */}
            <TextInput source="personal_details.first_name" label="First Name" required />
            <TextInput source="personal_details.last_name" label="Last Name" required />
            <TextInput source="personal_details.specialty" label="Specialty" required />
            
            {/* Στοιχεία Επικοινωνίας */}
            <TextInput source="personal_details.contact.phone" label="Phone" />
            <TextInput source="personal_details.contact.email" label="Email" type="email" required />
            <TextInput source="personal_details.contact.address" label="Address" fullWidth multiline />

            {/* Κατάσταση Διαθεσιμότητας */}
            <SelectInput source="availability_status" label="Availability" choices={[
                { id: 'available', name: 'Available' },
                { id: 'busy', name: 'Busy' },
                { id: 'unavailable', name: 'Unavailable' },
            ]} required />

            {/* ΣΗΜΕΙΩΣΗ: Δεν βάζουμε εδώ πεδία για account_details (username/password) 
                 ή managed_patients. Αυτά θα διαχειρίζονται αλλού (αν χρειαστεί). */}
        </SimpleForm>
    </Edit>
); 