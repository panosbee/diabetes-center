import React, { useState, useEffect, useCallback } from 'react';
import { 
    Box, 
    Typography, 
    Button, 
    List, 
    ListItem, 
    ListItemText, 
    IconButton, 
    CircularProgress, 
    Alert, 
    Paper, 
    ListItemIcon
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import DeleteIcon from '@mui/icons-material/Delete';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import DescriptionIcon from '@mui/icons-material/Description';
import { getMyFiles, uploadMyFile, deleteMyFile, getMyFileDownloadUrl } from '../dataProvider';
import { authProvider } from '../authProvider';
import { format } from 'date-fns'; // Για μορφοποίηση ημερομηνίας
import { Link as RouterLink } from 'react-router-dom'; // Για το Link στις λεπτομέρειες

function FilesManagement({ limit, isPreview = false }) {
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [uploading, setUploading] = useState(false);
    const [uploadError, setUploadError] = useState('');
    const [deletingId, setDeletingId] = useState(null); // Για να δείχνουμε loading στο delete button

    // Συνάρτηση για φόρτωση αρχείων
    const loadFiles = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const { data } = await getMyFiles();
            setFiles(data || []); // Εξασφάλιση ότι είναι πάντα array
        } catch (err) {
            console.error("Error loading files:", err);
            authProvider.checkError(err).catch(() => {
                setError(err.message || 'Failed to load files.');
            });
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadFiles();
    }, [loadFiles]);

    // Handler για την επιλογή αρχείου
    const handleFileChange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setUploading(true);
        setUploadError('');

        try {
            await uploadMyFile(file);
            // Ανανέωση λίστας αρχείων μετά το επιτυχές upload
            loadFiles(); 
        } catch (err) {
             console.error("Error uploading file:", err);
             authProvider.checkError(err).catch(() => {
                 setUploadError(err.message || 'File upload failed.');
             });
        } finally {
            setUploading(false);
            // Καθαρισμός του input για να μπορεί να ξαναεπιλεγεί το ίδιο αρχείο
            event.target.value = null; 
        }
    };

    // Handler για διαγραφή αρχείου
    const handleDelete = async (fileId) => {
        if (!window.confirm('Είστε σίγουροι ότι θέλετε να διαγράψετε αυτό το αρχείο;')) {
            return;
        }
        setDeletingId(fileId);
        setError(''); // Καθαρίζουμε τυχόν παλιά γενικά σφάλματα
        try {
            await deleteMyFile(fileId);
            // Ανανέωση λίστας αρχείων
            setFiles(prevFiles => prevFiles.filter(f => f.id !== fileId));
        } catch (err) {
             console.error("Error deleting file:", err);
             authProvider.checkError(err).catch(() => {
                 setError(err.message || 'Failed to delete file.');
             });
        } finally {
            setDeletingId(null);
        }
    };

    // Handler για λήψη αρχείου
    const handleDownload = (fileId) => {
        const url = getMyFileDownloadUrl(fileId);
        // Ανοίγουμε το URL σε νέο tab/παράθυρο για να ξεκινήσει η λήψη
        window.open(url, '_blank');
    };

    // Εφαρμογή του limit αν υπάρχει
    const displayFiles = limit ? files.slice(0, limit) : files;

    const content = (
        <>
            {/* Ανέβασμα Αρχείου (Μόνο αν δεν είναι preview) */} 
            {!isPreview && (
                <Box sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                    <Button
                        variant="contained"
                        component="label"
                        size="small" // Μικρότερο κουμπί
                        startIcon={uploading ? <CircularProgress size={20} color="inherit" /> : <UploadFileIcon />}
                        disabled={uploading}
                    >
                        Ανέβασμα Αρχείου
                        <input 
                            type="file" 
                            hidden 
                            onChange={handleFileChange}
                        />
                    </Button>
                    {uploadError && <Alert severity="error" sx={{ ml: 2, flexGrow: 1 }}>{uploadError}</Alert>}
                </Box>
            )}

            {/* Λίστα Αρχείων */} 
            {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: isPreview ? 1 : 0 }}><CircularProgress size={isPreview ? 20 : 40}/></Box>
            ) : displayFiles.length === 0 ? (
                <Typography variant="body2" color="text.secondary">Δεν υπάρχουν αρχεία.</Typography>
            ) : (
                 <List disablePadding={isPreview} dense={true}>
                    {displayFiles.map((file) => (
                        <ListItem 
                            key={file.id} 
                            divider={!isPreview} 
                            secondaryAction={
                                <>
                                    <IconButton edge="end" size="small" aria-label="download" onClick={() => handleDownload(file.id)}>
                                        <DownloadIcon fontSize="small" />
                                    </IconButton>
                                    {!isPreview && (
                                        <IconButton 
                                            edge="end" 
                                            size="small"
                                            aria-label="delete" 
                                            onClick={() => handleDelete(file.id)}
                                            disabled={deletingId === file.id}
                                            sx={{ ml: 1 }}
                                        >
                                            {deletingId === file.id ? <CircularProgress size={18} /> : <DeleteIcon fontSize="small" />}
                                        </IconButton>
                                    )}
                                </>
                            }
                            sx={{ pt: isPreview ? 0.5 : 1, pb: isPreview ? 0.5 : 1 }}
                        >
                            {/* Προσθήκη εικονιδίου αν είναι preview */} 
                            {isPreview && (
                                <ListItemIcon sx={{ minWidth: 'auto', mr: 1.5 }}> 
                                    <DescriptionIcon fontSize="small" />
                                </ListItemIcon>
                            )}
                            {/* Προσθήκη εικονιδίου και αν ΔΕΝ είναι preview */} 
                            {!isPreview && (
                                <ListItemIcon sx={{ minWidth: 'auto', mr: 2 }}> 
                                    <DescriptionIcon />
                                </ListItemIcon>
                            )}
                            <ListItemText 
                                primary={<Typography variant="body2">{file.original_filename || file.filename}</Typography>}
                                secondary={
                                     <Typography variant="caption" color="text.secondary">
                                        {`Uploaded: ${file.upload_date ? format(new Date(file.upload_date), 'dd/MM/yy HH:mm') : 'N/A'}`}
                                     </Typography>
                                }
                            />
                        </ListItem>
                    ))}
                </List>
            )}
        </>
    );

    if (isPreview) {
        return content;
    }

    return (
        <Paper sx={{ p: 3, mt: 3 }}>
            <Typography variant="h6" gutterBottom>Τα Αρχεία μου</Typography>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            {content}
        </Paper>
    );
}

export default FilesManagement; 