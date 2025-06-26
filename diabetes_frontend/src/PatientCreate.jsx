import React from 'react';
import {
    Create,
    SimpleForm,
    TextInput,
    DateInput,
    BooleanInput,
    NumberInput,
    ArrayInput,
    SimpleFormIterator,
    TabbedForm,
    FormTab,
    ReferenceInput,
    AutocompleteInput,
    useGetIdentity
} from 'react-admin';

export const PatientCreate = (props) => {
    const { identity } = useGetIdentity();
    
    return (
        <Create {...props} title="Δημιουργία Νέου Ασθενή">
            <TabbedForm>
                <FormTab label="Προσωπικά Στοιχεία">
                    <TextInput source="personal_details.first_name" label="Όνομα" required fullWidth />
                    <TextInput source="personal_details.last_name" label="Επώνυμο" required fullWidth />
                    <TextInput source="personal_details.amka" label="ΑΜΚΑ" required fullWidth />
                    <DateInput source="personal_details.date_of_birth" label="Ημ. Γέννησης" fullWidth />
                    <TextInput source="personal_details.contact.phone" label="Τηλέφωνο" fullWidth />
                    <TextInput source="personal_details.contact.email" label="Email" type="email" fullWidth />
                    <TextInput source="personal_details.contact.address" label="Διεύθυνση" fullWidth multiline />
                </FormTab>

                <FormTab label="Ιατρικό Προφίλ">
                    <NumberInput source="medical_profile.height_cm" label="Ύψος (cm)" fullWidth />
                    <ArrayInput source="medical_profile.allergies" label="Αλλεργίες">
                        <SimpleFormIterator inline>
                            <TextInput source="" label="Αλλεργία" />
                        </SimpleFormIterator>
                    </ArrayInput>
                    <ArrayInput source="medical_profile.conditions" label="Παθήσεις">
                        <SimpleFormIterator>
                            <TextInput source="condition_name" label="Όνομα Πάθησης" fullWidth />
                            <DateInput source="diagnosis_date" label="Ημ. Διάγνωσης" fullWidth />
                        </SimpleFormIterator>
                    </ArrayInput>
                    <TextInput 
                        source="medical_profile.medical_history_summary" 
                        label="Περίληψη Ιατρικού Ιστορικού" 
                        fullWidth 
                        multiline
                        rows={4}
                    />
                </FormTab>

                <FormTab label="Διαχείριση">
                    {/* Αυτόματη συμπλήρωση του τρέχοντος γιατρού */}
                    <TextInput
                        source="assigned_doctors"
                        label="ID Θεράποντος Ιατρού"
                        initialValue={identity?.id ? [identity.id] : []}
                        disabled
                        fullWidth
                        helperText="Ο ασθενής θα ανατεθεί αυτόματα σε εσάς"
                    />
                    <BooleanInput 
                        source="is_in_common_space" 
                        label="Σε κοινό χώρο;" 
                        helperText="Εάν επιλεγεί, ο ασθενής θα είναι προσβάσιμος από όλους τους γιατρούς" 
                        fullWidth
                    />
                    
                    <TextInput 
                        source="account_details.username" 
                        label="Όνομα Χρήστη για τον Ασθενή" 
                        helperText="Προτείνεται η χρήση του ΑΜΚΑ" 
                        fullWidth 
                    />
                    <TextInput 
                        source="account_details.password" 
                        label="Προσωρινός Κωδικός Πρόσβασης" 
                        type="password" 
                        fullWidth 
                        required
                    />
                </FormTab>
            </TabbedForm>
        </Create>
    );
}; 