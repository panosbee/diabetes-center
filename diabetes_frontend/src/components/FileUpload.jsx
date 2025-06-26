import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
    Button, 
    Box, 
    Typography, 
    Paper, 
    CircularProgress, 
    LinearProgress,
    List, 
    ListItem, 
    ListItemText, 
    ListItemSecondaryAction,
    IconButton,
    Chip,
    TextField,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Grid
} from '@mui/material';
import { 
    CloudUpload as CloudUploadIcon,
    AttachFile as AttachFileIcon,
    Delete as DeleteIcon,
    Label as LabelIcon,
    Add as AddIcon
} from '@mui/icons-material';
import { useNotify, useGetIdentity, useDataProvider } from 'react-admin';

// Component για ανέβασμα αρχείων
const FileUpload = ({ patientId, onUploadSuccess }) => {
    const [files, setFiles] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState({});
    const [tagDialogOpen, setTagDialogOpen] = useState(false);
    const [currentFileIndex, setCurrentFileIndex] = useState(null);
    const [tag, setTag] = useState('');
    const [availableTags, setAvailableTags] = useState([
        'Εξετάσεις Αίματος', 
        'Εξετάσεις Νεφρών', 
        'Γλυκοζυλιωμένη', 
        'Καρδιολογικά',
        'Οφθαλμολογικά',
        'Ινσουλίνη'
    ]);
    
    const notify = useNotify();
    const { identity } = useGetIdentity();
    const dataProvider = useDataProvider();
    
    const onDrop = useCallback(acceptedFiles => {
        setFiles(prevFiles => [...prevFiles, ...acceptedFiles.map(file => ({ 
            file,
            tag: '',
            progress: 0
        }))]);
    }, []);
    
    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png'],
            'application/pdf': ['.pdf'],
            'text/plain': ['.txt'],
            'text/csv': ['.csv']
        },
        maxSize: 15728640 // 15MB
    });
    
    const handleRemoveFile = (index) => {
        setFiles(prevFiles => prevFiles.filter((_, i) => i !== index));
    };
    
    const openTagDialog = (index) => {
        setCurrentFileIndex(index);
        setTag(files[index].tag || '');
        setTagDialogOpen(true);
    };
    
    const handleTagDialogClose = () => {
        setTagDialogOpen(false);
        setCurrentFileIndex(null);
        setTag('');
    };
    
    const handleTagSubmit = () => {
        if (currentFileIndex !== null) {
            setFiles(prevFiles => prevFiles.map((fileItem, index) => 
                index === currentFileIndex ? { ...fileItem, tag } : fileItem
            ));
            
            if (tag && !availableTags.includes(tag)) {
                setAvailableTags(prev => [...prev, tag]);
            }
            
            handleTagDialogClose();
        }
    };
    
    const handleTagSelect = (selectedTag) => {
        setTag(selectedTag);
    };
    
    const handleUpload = async () => {
        if (files.length === 0) return;

        setUploading(true);
        let successful = 0;
        const token = localStorage.getItem('access_token'); // <-- ΔΙΟΡΘΩΣΗ ΚΛΕΙΔΙΟΥ

        if (!token) {
            notify('Authentication token not found. Please log in again.', { type: 'error' });
            setUploading(false);
            // Προαιρετικά: Κατεύθυνση στη σελίδα login
            // logout(); 
            return;
        }

        // --- Χρήση απευθείας fetch αντί για dataProvider.create ---
        for (let i = 0; i < files.length; i++) {
            const fileItem = files[i];
            const formData = new FormData();
            formData.append('file', fileItem.file);
            
            // if (fileItem.tag) { // Το tag δεν το στέλνουμε πια με το upload αρχικά
            //     formData.append('tag', fileItem.tag);
            // }

            // --- Χρήση import.meta.env --- 
            const apiUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/patients/${patientId}/files`;

            try {
                const response = await fetch(apiUrl, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        // 'Content-Type': 'multipart/form-data' // Το fetch το βάζει αυτόματα για FormData
                    },
                    // Δεν υπάρχει απλός τρόπος για progress με το fetch, το αφαιρούμε προς το παρόν
                    // onUploadProgress: ... 
                });

                const responseData = await response.json(); // Διαβάζουμε την απάντηση

                if (!response.ok) {
                    // Αν η απάντηση δεν είναι 2xx, θεωρείται σφάλμα
                    throw new Error(responseData.error || `HTTP error! status: ${response.status}`);
                }

                console.log('Upload response:', responseData);
                successful++;
                
                // --- Ενημέρωση Tag (ΞΕΧΩΡΙΣΤΗ ΚΛΗΣΗ PATCH) --- 
                if (fileItem.tag && responseData.file_info?.file_id) {
                    const fileId = responseData.file_info.file_id;
                    // --- Χρήση import.meta.env --- 
                    const tagUpdateUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/files/${patientId}/${fileId}/tag`;
                    try {
                        const tagResponse = await fetch(tagUpdateUrl, {
                            method: 'PATCH',
                            headers: {
                                'Authorization': `Bearer ${token}`,
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ tag: fileItem.tag })
                        });
                        if (!tagResponse.ok) {
                            const tagErrorData = await tagResponse.json();
                            throw new Error(tagErrorData.error || `Failed to update tag: ${tagResponse.status}`);
                        }
                        console.log(`Tag updated successfully for file ${fileId}`);
                    } catch (tagError) {
                        console.error('Error updating tag:', tagError);
                        notify(`Σφάλμα κατά την ενημέρωση ετικέτας για το αρχείο ${fileItem.file.name}: ${tagError.message}`, { type: 'warning' });
                        // Συνεχίζουμε ακόμα κι αν το tag απέτυχε
                    }
                }
                // ------------------------------------------------
                
            } catch (error) {
                console.error('Error uploading file:', error);
                notify(`Σφάλμα κατά το ανέβασμα του αρχείου ${fileItem.file.name}: ${error.message}`, { type: 'error' });
            } finally {
                 // Αφαιρούμε την πρόοδο αφού δεν την υποστηρίζει εύκολα το fetch
                // setUploadProgress(prev => ({ ...prev, [i]: 100 })); 
            }
        }
        // ----------------------------------------------------

        setUploading(false);

        if (successful > 0) {
            notify(
                successful === 1 
                    ? 'Το αρχείο ανέβηκε επιτυχώς' 
                    : `${successful} αρχεία ανέβηκαν επιτυχώς`, 
                { type: 'success' }
            );
            setFiles([]);
            setUploadProgress({});
            
            // Καλούμε το callback για ανανέωση της λίστας αρχείων
            if (onUploadSuccess) {
                onUploadSuccess();
            }
        }
    };
    
    return (
        <Box sx={{ mb: 3 }}>
            <Paper 
                elevation={3} 
                sx={{ 
                    p: 2, 
                    mb: 2,
                    border: isDragActive ? '2px dashed #1976d2' : '2px dashed #ccc',
                    borderRadius: 2,
                    backgroundColor: isDragActive ? 'rgba(25, 118, 210, 0.04)' : 'transparent',
                    transition: 'all 0.2s'
                }}
            >
                <Box 
                    {...getRootProps()} 
                    sx={{ 
                        p: 3, 
                        textAlign: 'center',
                        cursor: 'pointer'
                    }}
                >
                    <input {...getInputProps()} />
                    <CloudUploadIcon sx={{ fontSize: 48, color: '#1976d2', mb: 2 }} />
                    
                    {isDragActive ? (
                        <Typography variant="h6" color="primary">
                            Αφήστε τα αρχεία εδώ...
                        </Typography>
                    ) : (
                        <>
                            <Typography variant="h6" gutterBottom>
                                Σύρετε και αφήστε τα αρχεία εδώ
                            </Typography>
                            <Typography variant="body2" color="textSecondary">
                                ή κάντε κλικ για επιλογή αρχείων
                            </Typography>
                            <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 1 }}>
                                Υποστηριζόμενοι τύποι: PDF, JPG, PNG, TXT, CSV (έως 15MB)
                            </Typography>
                        </>
                    )}
                </Box>
            </Paper>
            
            {files.length > 0 && (
                <Paper elevation={2} sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                        Αρχεία προς ανέβασμα ({files.length})
                    </Typography>
                    
                    <List dense>
                        {files.map((fileItem, index) => (
                            <ListItem key={index} divider={index < files.length - 1}>
                                <AttachFileIcon sx={{ mr: 1 }} />
                                <ListItemText 
                                    primary={fileItem.file.name} 
                                    secondary={`${(fileItem.file.size / 1024).toFixed(1)} KB${fileItem.tag ? ` • Ετικέτα: ${fileItem.tag}` : ''}`}
                                />
                                
                                {/*!uploading &&*/ (
                                     <ListItemSecondaryAction>
                                        <IconButton 
                                            edge="end" 
                                            aria-label="προσθήκη ετικέτας"
                                            onClick={() => openTagDialog(index)}
                                            sx={{ mr: 1 }}
                                        >
                                            <LabelIcon />
                                        </IconButton>
                                        <IconButton 
                                            edge="end" 
                                            aria-label="διαγραφή"
                                            onClick={() => handleRemoveFile(index)}
                                        >
                                            <DeleteIcon />
                                        </IconButton>
                                    </ListItemSecondaryAction>
                                )}
                            </ListItem>
                        ))}
                    </List>
                    
                    <Box sx={{ mt: 2, textAlign: 'right' }}>
                        <Button 
                            variant="contained" 
                            color="primary" 
                            onClick={handleUpload}
                            disabled={uploading || files.length === 0}
                            startIcon={uploading ? <CircularProgress size={20} /> : null}
                        >
                            {uploading ? 'Ανέβασμα...' : 'Ανέβασμα Αρχείων'}
                        </Button>
                    </Box>
                </Paper>
            )}
            
            {/* Διάλογος για προσθήκη ετικέτας */}
            <Dialog open={tagDialogOpen} onClose={handleTagDialogClose}>
                <DialogTitle>Προσθήκη Ετικέτας</DialogTitle>
                <DialogContent>
                    <TextField
                        autoFocus
                        margin="dense"
                        label="Ετικέτα"
                        fullWidth
                        variant="outlined"
                        value={tag}
                        onChange={(e) => setTag(e.target.value)}
                        placeholder="π.χ. Εξετάσεις Αίματος"
                    />
                    
                    <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                        Διαθέσιμες Ετικέτες:
                    </Typography>
                    
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {availableTags.map((availTag, index) => (
                            <Chip 
                                key={index} 
                                label={availTag} 
                                onClick={() => handleTagSelect(availTag)}
                                clickable
                                color={tag === availTag ? "primary" : "default"}
                            />
                        ))}
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleTagDialogClose}>Ακύρωση</Button>
                    <Button onClick={handleTagSubmit} variant="contained" color="primary">
                        Προσθήκη
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default FileUpload; 