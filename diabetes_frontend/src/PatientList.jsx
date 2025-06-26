import { 
    List, 
    Datagrid, 
    TextField, 
    EmailField,
    DateField, 
    BooleanField, 
    ReferenceArrayField,
    SingleFieldList, 
    ChipField, 
    EditButton,
    ShowButton,
    useGetIdentity,
    useRecordContext,
    TextInput
} from 'react-admin';

// Custom Actions για Ασθενείς
const PatientListActions = () => {
    const { identity, isLoading } = useGetIdentity();
    const record = useRecordContext();

    if (isLoading || !record || !identity) return <ShowButton />;

    // Έλεγχος αν ο γιατρός έχει πρόσβαση στον ασθενή
    const isAssigned = record.assigned_doctors?.includes(identity.id);
    const isInCommonSpace = record.is_in_common_space;
    const hasAccess = isAssigned || isInCommonSpace;

    // Εμφάνιση EditButton μόνο αν ο γιατρός έχει πρόσβαση, αλλιώς ShowButton
    return hasAccess ? (
        <>
            <ShowButton />
            <EditButton />
        </>
    ) : (
        <ShowButton />
    );
};

// --- ΝΕΟ: Component για τα φίλτρα --- 
const PatientFilters = [
    <TextInput label="Αναζήτηση με ΑΜΚΑ" source="amka_filter" alwaysOn />
];
// -----------------------------------

export const PatientList = (props) => (
    <List {...props} title="All Patients" filters={PatientFilters}>
        <Datagrid rowClick="show">
            <TextField source="personal_details.first_name" label="First Name" />
            <TextField source="personal_details.last_name" label="Last Name" />
            <TextField source="personal_details.amka" label="AMKA" />
            <DateField source="created_at" label="Registration Date" />
            <BooleanField source="is_in_common_space" label="Common Space?" />
            <ReferenceArrayField label="Assigned Doctors" reference="doctors" source="assigned_doctors">
                 <SingleFieldList linkType={false}>
                     <ChipField source="personal_details.last_name" />
                 </SingleFieldList>
            </ReferenceArrayField>
            <PatientListActions />
        </Datagrid>
    </List>
); 