import React, { useState } from 'react';
import { Fab, Modal, Box, IconButton, Typography } from '@mui/material';
import ChatIcon from '@mui/icons-material/Chat';
import CloseIcon from '@mui/icons-material/Close';
import AIChatInterface from './AIChatInterface'; // Η διεπαφή που ήδη φτιάξαμε

const fabStyle = {
    position: 'fixed',
    bottom: 32,
    right: 32,
    zIndex: 1300, // Πρέπει να είναι πάνω από άλλα στοιχεία (π.χ., το AppBar του react-admin είναι ~1100)
};

const modalStyle = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: '80%', // Ή ένα σταθερό πλάτος π.χ. 600
    maxWidth: 600, 
    maxHeight: '85vh', // Μέγιστο ύψος
    bgcolor: 'background.paper',
    border: '1px solid #ccc',
    borderRadius: 2,
    boxShadow: 24,
    p: 3, // Padding
    display: 'flex',
    flexDirection: 'column',
};

const modalHeaderStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 2, // Κενό πριν το chat interface
};

const modalContentStyle = {
    flexGrow: 1, // Να παίρνει τον υπόλοιπο χώρο
    overflowY: 'auto', // Scroll αν το περιεχόμενο ξεχειλίσει
};

const FloatingAIChatButton = () => {
    const [modalOpen, setModalOpen] = useState(false);

    const handleOpen = () => setModalOpen(true);
    const handleClose = () => setModalOpen(false);

    return (
        <>
            <Fab color="primary" aria-label="chat with ai" onClick={handleOpen} sx={fabStyle}>
                <ChatIcon />
            </Fab>
            <Modal
                open={modalOpen}
                onClose={handleClose} // Κλείνει και με κλικ έξω από το modal
                aria-labelledby="ai-chat-modal-title"
                aria-describedby="ai-chat-modal-description"
            >
                <Box sx={modalStyle}>
                    <Box sx={modalHeaderStyle}>
                        <Typography id="ai-chat-modal-title" variant="h6" component="h2">
                            🤖 AI Assistant με PubMed & Genetics
                        </Typography>
                        <IconButton onClick={handleClose} aria-label="close ai chat">
                            <CloseIcon />
                        </IconButton>
                    </Box>
                    <Box sx={modalContentStyle} id="ai-chat-modal-description">
                        <AIChatInterface /> 
                    </Box>
                </Box>
            </Modal>
        </>
    );
};

export default FloatingAIChatButton; 