import {
    List,
    Datagrid,
    TextField,
    DateField,
    ReferenceField,
    EditButton,
    ShowButton,
    CreateButton,
    ExportButton,
    FilterButton,
    TopToolbar,
    DateInput,
    ReferenceInput,
    AutocompleteInput
} from 'react-admin';

const SessionFilters = [
    <DateInput source="timestamp" label="Ημερομηνία" alwaysOn />,
    <ReferenceInput source="patient_id" reference="patients" label="Ασθενής">
        <AutocompleteInput
            optionText={record => record ? `${record.personal_details?.first_name} ${record.personal_details?.last_name}` : ''}
        />
    </ReferenceInput>
];

const SessionListActions = () => (
    <TopToolbar>
        <FilterButton />
        <CreateButton />
        <ExportButton />
    </TopToolbar>
);

export const SessionList = (props) => (
    <List
        {...props}
        title="Συνεδρίες"
        actions={<SessionListActions />}
        filters={SessionFilters}
        sort={{ field: 'timestamp', order: 'DESC' }}
    >
        <Datagrid rowClick="show">
            <DateField source="timestamp" label="Ημερομηνία" showTime />
            <ReferenceField source="patient_id" reference="patients" label="Ασθενής">
                <TextField source="personal_details.last_name" />
            </ReferenceField>
            <TextField source="session_type" label="Τύπος Συνεδρίας" />
            <ShowButton />
            <EditButton />
        </Datagrid>
    </List>
); 