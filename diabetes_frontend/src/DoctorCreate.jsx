import React from 'react';
import {
    Create,
    SimpleForm,
    TextInput,
    SelectInput,
    required,
    email
} from 'react-admin';

export const DoctorCreate = (props) => (
    <Create {...props} title="Εγγραφή Νέου Γιατρού">
        <SimpleForm>
            {/* Προσωπικά Στοιχεία */}
            <TextInput 
                source="personal_details.first_name" 
                label="Όνομα" 
                validate={required()} 
                fullWidth 
            />
            <TextInput 
                source="personal_details.last_name" 
                label="Επώνυμο" 
                validate={required()} 
                fullWidth 
            />
            <TextInput 
                source="personal_details.specialty" 
                label="Ειδικότητα" 
                validate={required()} 
                fullWidth 
            />
            <SelectInput 
                source="personal_details.gender" 
                label="Φύλο" 
                choices={[
                    { id: 'male', name: 'Άνδρας' },
                    { id: 'female', name: 'Γυναίκα' },
                    { id: 'other', name: 'Άλλο' }
                ]}
                fullWidth
            />
            
            {/* Στοιχεία Επικοινωνίας */}
            <TextInput 
                source="personal_details.contact.phone" 
                label="Τηλέφωνο" 
                fullWidth 
            />
            <TextInput 
                source="personal_details.contact.email" 
                label="Email" 
                type="email" 
                validate={[required(), email()]} 
                fullWidth 
            />
            <TextInput 
                source="personal_details.contact.address" 
                label="Διεύθυνση" 
                fullWidth 
                multiline 
            />

            {/* Κατάσταση Διαθεσιμότητας */}
            <SelectInput 
                source="availability_status" 
                label="Διαθεσιμότητα" 
                choices={[
                    { id: 'available', name: 'Διαθέσιμος' },
                    { id: 'busy', name: 'Απασχολημένος' },
                    { id: 'unavailable', name: 'Μη Διαθέσιμος' },
                ]} 
                validate={required()} 
                fullWidth 
                defaultValue="available"
            />

            {/* Στοιχεία Λογαριασμού */}
            <TextInput 
                source="account_details.username" 
                label="Όνομα Χρήστη" 
                validate={required()} 
                fullWidth 
            />
            <TextInput 
                source="account_details.password" 
                label="Κωδικός Πρόσβασης" 
                type="password" 
                validate={required()} 
                fullWidth 
            />
        </SimpleForm>
    </Create>
); 