import React from 'react';
import {
    Edit,
    TextInput,
    DateInput,
    BooleanInput,
    NumberInput,
    TabbedForm,
    FormTab,
    ArrayInput,
    SimpleFormIterator,
    Toolbar,
    SaveButton,
    DeleteButton,
    useGetIdentity,
    useRecordContext
} from 'react-admin';

// Εισαγωγή των components για τα αρχεία
import FileUpload from './components/FileUpload';
import FileList from './components/FileList';
import CommonSpaceToggle from './components/CommonSpaceToggle';

const PatientEditToolbar = () => {
    const { identity, isLoading: identityLoading } = useGetIdentity();
    const record = useRecordContext();

    if (identityLoading || !record || !identity) return null;

    const isAssigned = record.assigned_doctors?.includes(identity.id);
    const isInCommonSpace = record.is_in_common_space;
    const canEdit = isAssigned || isInCommonSpace;

    console.log(`[PatientEditToolbar] Checking permissions for patient ${record.id}: Can Edit = ${canEdit}`);

    return (
        <Toolbar>
            {canEdit && <SaveButton />}
            {canEdit && <DeleteButton mutationMode="pessimistic"/>}
        </Toolbar>
    );
};

const PatientEditFormContent = () => {
    const record = useRecordContext();
    const patientId = record?.id;
    
    const [refreshFileList, setRefreshFileList] = React.useState(0);

    const handleUploadSuccess = () => {
        console.log(">>> handleUploadSuccess triggered!");
        setRefreshFileList(prev => prev + 1);
    };
    
    if (!record) return null;

    return (
        <TabbedForm toolbar={<PatientEditToolbar />}>
            <FormTab label="Personal Details">
                <TextInput source="personal_details.first_name" label="First Name" required />
                <TextInput source="personal_details.last_name" label="Last Name" required />
                <TextInput source="personal_details.amka" label="AMKA" required />
                <DateInput source="personal_details.date_of_birth" label="Date of Birth" />
                <TextInput source="personal_details.contact.phone" label="Phone" />
                <TextInput source="personal_details.contact.email" label="Email" type="email" />
                <TextInput source="personal_details.contact.address" label="Address" fullWidth multiline />
            </FormTab>

            <FormTab label="Medical Profile">
                <NumberInput source="medical_profile.height_cm" label="Height (cm)" />
                <ArrayInput source="medical_profile.allergies" label="Allergies">
                    <SimpleFormIterator inline>
                        <TextInput source="" label="Allergy" />
                    </SimpleFormIterator>
                </ArrayInput>
                <ArrayInput source="medical_profile.conditions" label="Conditions">
                     <SimpleFormIterator>
                         <TextInput source="condition_name" label="Condition Name" />
                         <DateInput source="diagnosis_date" label="Diagnosis Date" />
                     </SimpleFormIterator>
                </ArrayInput>
                <TextInput source="medical_profile.medical_history_summary" label="History Summary" fullWidth multiline/>
            </FormTab>

            <FormTab label="Management">
                <CommonSpaceToggle />
            </FormTab>
            
            <FormTab label="Files">
                 {patientId && (
                     <>
                         <FileUpload patientId={patientId} onUploadSuccess={handleUploadSuccess} />
                         <FileList patientId={patientId} refreshTrigger={refreshFileList} />
                     </>
                 )}
             </FormTab>
        </TabbedForm>
    );
};

export const PatientEdit = (props) => {
    return (
        <Edit {...props} title="Edit Patient">
            <PatientEditFormContent />
        </Edit>
    );
}; 