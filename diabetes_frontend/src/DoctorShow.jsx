import {
    Show,
    SimpleShowLayout,
    TextField,
    EmailField,
    Tab,
    TabbedShowLayout
} from 'react-admin';

import { RestrictedAccessMessage } from './RestrictedAccessShow';

export const DoctorShow = (props) => (
    <Show {...props} title="Doctor Profile">
        <RestrictedAccessMessage />
        <TabbedShowLayout>
            <Tab label="Personal Info">
                <TextField source="personal_details.first_name" label="First Name" />
                <TextField source="personal_details.last_name" label="Last Name" />
                <TextField source="personal_details.specialty" label="Specialty" />
                <TextField source="personal_details.contact.phone" label="Phone" />
                <EmailField source="personal_details.contact.email" label="Email" />
                <TextField source="personal_details.contact.address" label="Address" />
                <TextField source="availability_status" label="Availability" />
            </Tab>
        </TabbedShowLayout>
    </Show>
); 