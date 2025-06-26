import React from 'react';
import { Layout } from 'react-admin';
import FloatingAIChatButton from './FloatingAIChatButton';

// Το MyLayout χρησιμοποιεί το προεπιλεγμένο Layout του React-admin
// και προσθέτει το δικό μας component "από πάνω"
export const MyLayout = (props) => (
    <>
        <Layout {...props} />
        <FloatingAIChatButton />
    </>
); 