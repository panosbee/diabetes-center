import React, { useState, useEffect, useRef } from 'react';
import { 
    Paper, 
    Typography, 
    List, 
    ListItem, 
    ListItemIcon, 
    ListItemText, 
    ListItemSecondaryAction,
    IconButton, 
    Chip,
    Tooltip,
    Dialog,
    DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    Button,
    Box,
    TextField,
    InputAdornment,
    Collapse,
    Divider,
    CircularProgress,
    Avatar
} from '@mui/material';
import { 
    InsertDriveFile as FileIcon, 
    Description as PdfIcon,
    Image as ImageIcon,
    NoteAlt as TextIcon,
    DeleteOutline as DeleteIcon,
    GetApp as DownloadIcon,
    Visibility as ViewIcon,
    Search as SearchIcon,
    FilterList as FilterIcon,
    Label as LabelIcon,
    Close as CloseIcon
} from '@mui/icons-material';
import { useDataProvider, useNotify, useGetIdentity } from 'react-admin';
import { format } from 'date-fns';
import { el } from 'date-fns/locale';
import { useTheme } from '@mui/material/styles';

// Component για λίστα αρχείων
const FileList = ({ patientId, refreshTrigger }) => {
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [fileToDelete, setFileToDelete] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedTags, setSelectedTags] = useState([]);
    const [availableTags, setAvailableTags] = useState([]);
    const [filterExpanded, setFilterExpanded] = useState(false);
    const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
    const [previewFile, setPreviewFile] = useState(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [previewObjectUrl, setPreviewObjectUrl] = useState(null);
    const objectUrlRef = useRef(null);
    
    const dataProvider = useDataProvider();
    const notify = useNotify();
    const { identity } = useGetIdentity();
    const theme = useTheme();
    
    // Φόρτωση της λίστας αρχείων
    useEffect(() => {
        console.log(">>> FileList useEffect triggered! RefreshTrigger:", refreshTrigger);
        const fetchFiles = async () => {
            setLoading(true);
            try {
                const response = await dataProvider.getList(`patients/${patientId}/files`, {
                    pagination: { page: 1, perPage: 100 },
                    sort: { field: 'upload_date', order: 'DESC' },
                    filter: {}
                });
                
                setFiles(response.data || []);
                
                // Συλλογή μοναδικών tags
                const tags = new Set();
                response.data.forEach(file => {
                    if (file.tag) tags.add(file.tag);
                });
                setAvailableTags(Array.from(tags));
                
            } catch (error) {
                console.error('Error fetching files:', error);
                notify('Σφάλμα κατά τη φόρτωση της λίστας αρχείων', { type: 'error' });
            } finally {
                setLoading(false);
            }
        };
        
        fetchFiles();
    }, [patientId, dataProvider, notify, refreshTrigger]);
    
    // --- ΝΕΑ Συνάρτηση για λήψη blob με fetch --- 
    const fetchFileBlob = async (file) => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            notify('Authentication token not found.', { type: 'error' });
            return null;
        }
        const fileUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/files/${patientId}/${file.file_id}`;
        try {
            const response = await fetch(fileUrl, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: response.statusText }));
                throw new Error(errorData.error || `HTTP error ${response.status}`);
            }
            return await response.blob();
        } catch (error) {
            console.error('Error fetching file blob:', error);
            notify(`Σφάλμα λήψης δεδομένων αρχείου: ${error.message}`, { type: 'error' });
            return null;
        }
    };

    // Χειρισμός προβολής αρχείου
    const handleViewFile = async (file) => {
        setPreviewFile(file);
        setPreviewDialogOpen(true);
        setPreviewLoading(true);
        setPreviewObjectUrl(null);
        if (objectUrlRef.current) {
             URL.revokeObjectURL(objectUrlRef.current);
        }
        
        const blob = await fetchFileBlob(file);
        
        if (blob) {
            objectUrlRef.current = URL.createObjectURL(blob);
            setPreviewObjectUrl(objectUrlRef.current);
        }
        setPreviewLoading(false);
    };
    
    // Χειρισμός λήψης αρχείου
    const handleDownloadFile = async (file) => {
        const blob = await fetchFileBlob(file);
        if (blob) {
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.setAttribute('download', file.original_filename || file.filename);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);
        }
    };
    
    // Χειρισμός διαγραφής αρχείου
    const handleDeleteFile = async () => {
        if (!fileToDelete) return;
        
        const token = localStorage.getItem('access_token');
        if (!token) {
            notify('Authentication token not found.', { type: 'error' });
            closeDeleteDialog();
            return;
        }

        const deleteUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/files/${patientId}/${fileToDelete.file_id}`;

        try {
            const response = await fetch(deleteUrl, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: response.statusText }));
                throw new Error(errorData.error || `HTTP error ${response.status}`);
            }

            // Αφαίρεση του αρχείου από την τοπική λίστα
            setFiles(prevFiles => prevFiles.filter(file => file.file_id !== fileToDelete.file_id));
            notify('Το αρχείο διαγράφηκε επιτυχώς', { type: 'success' });
            
        } catch (error) {
            console.error('Error deleting file:', error);
            notify(`Σφάλμα κατά τη διαγραφή του αρχείου: ${error.message}`, { type: 'error' });
        } finally {
            closeDeleteDialog();
        }
    };
    
    // Άνοιγμα διαλόγου διαγραφής
    const openDeleteDialog = (file) => {
        setFileToDelete(file);
        setDeleteDialogOpen(true);
    };
    
    // Κλείσιμο διαλόγου διαγραφής
    const closeDeleteDialog = () => {
        setDeleteDialogOpen(false);
        setFileToDelete(null);
    };
    
    // Χειρισμός επιλογής ετικέτας για φιλτράρισμα
    const handleTagToggle = (tag) => {
        setSelectedTags(prevTags => 
            prevTags.includes(tag)
                ? prevTags.filter(t => t !== tag)
                : [...prevTags, tag]
        );
    };
    
    // Φιλτράρισμα αρχείων βάσει αναζήτησης και επιλεγμένων ετικετών
    const filteredFiles = files.filter(file => {
        const matchesSearch = searchTerm === '' || 
            (file.filename && file.filename.toLowerCase().includes(searchTerm.toLowerCase())) ||
            (file.original_filename && file.original_filename.toLowerCase().includes(searchTerm.toLowerCase())) ||
            (file.tag && file.tag.toLowerCase().includes(searchTerm.toLowerCase()));
            
        const matchesTags = selectedTags.length === 0 || 
            (file.tag && selectedTags.includes(file.tag));
            
        return matchesSearch && matchesTags;
    });
    
    // Εμφάνιση κατάλληλου εικονιδίου βάσει τύπου αρχείου
    const getFileIcon = (mimeType) => {
        if (mimeType?.startsWith('image/')) {
            return <ImageIcon />;
        } else if (mimeType === 'application/pdf') {
            return <PdfIcon />;
        } else if (mimeType === 'text/plain' || mimeType === 'text/csv') {
            return <TextIcon />;
        }
        return <FileIcon />;
    };
    
    // Μορφοποίηση ημερομηνίας
    const formatDate = (dateString) => {
        try {
            const date = new Date(dateString);
            return format(date, "d MMMM yyyy, HH:mm", { locale: el });
        } catch (e) {
            return 'Μη έγκυρη ημερομηνία';
        }
    };
    
    // Συνάρτηση για τη μορφοποίηση του μεγέθους αρχείου
    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };
    
    const FileItem = ({ file, onViewFile, onDeleteFile }) => {
        const theme = useTheme();
        const fileIcon = getFileIcon(file.filename);
        
        return (
            <Box
                sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    p: 2,
                    mb: 1.5,
                    borderRadius: 2,
                    border: '1px solid',
                    borderColor: 'rgba(0, 0, 0, 0.05)',
                    backgroundColor: 'white',
                    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                        boxShadow: '0 3px 8px rgba(0, 0, 0, 0.08)',
                        borderColor: theme.palette.primary.light,
                        transform: 'translateY(-2px)',
                    },
                }}
            >
                <Box display="flex" alignItems="center" gap={2}>
                    <Avatar 
                        variant="rounded"
                        sx={{ 
                            bgcolor: `${theme.palette.primary.light}20`, 
                            color: theme.palette.primary.main,
                            width: 42,
                            height: 42
                        }}
                    >
                        {fileIcon}
                    </Avatar>
                    <Box>
                        <Typography variant="body1" fontWeight={600}>
                            {file.filename}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            {formatDate(file.upload_date)} - {formatFileSize(file.file_size || 0)}
                        </Typography>
                    </Box>
                </Box>
                <Box>
                    <Tooltip title="Περισσότερες λεπτομέρειες">
                        <IconButton
                            onClick={() => onViewFile(file)}
                            sx={{ 
                                color: theme.palette.info.main,
                                '&:hover': { 
                                    backgroundColor: `${theme.palette.info.light}20` 
                                }
                            }}
                        >
                            <ViewIcon />
                        </IconButton>
                    </Tooltip>
                    <Tooltip title="Διαγραφή αρχείου">
                        <IconButton
                            onClick={() => onDeleteFile(file.file_id)}
                            sx={{ 
                                color: theme.palette.error.main,
                                '&:hover': { 
                                    backgroundColor: `${theme.palette.error.light}20` 
                                }
                            }}
                        >
                            <DeleteIcon />
                        </IconButton>
                    </Tooltip>
                </Box>
            </Box>
        );
    };
    
    return (
        <Paper
            elevation={0}
            sx={{
                padding: 2,
                borderRadius: 3,
                overflow: 'hidden',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
                backgroundColor: 'white',
                border: '1px solid rgba(0, 0, 0, 0.05)',
            }}
        >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Αρχεία Ασθενή</Typography>
                
                <Button 
                    variant="outlined" 
                    startIcon={<FilterIcon />}
                    onClick={() => setFilterExpanded(!filterExpanded)}
                    size="small"
                >
                    Φίλτρα
                </Button>
            </Box>
            
            <Collapse in={filterExpanded}>
                <Box sx={{ mb: 2 }}>
                    <TextField
                        fullWidth
                        variant="outlined"
                        placeholder="Αναζήτηση αρχείων..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">
                                    <SearchIcon />
                                </InputAdornment>
                            ),
                        }}
                        sx={{ mb: 2 }}
                        size="small"
                    />
                    
                    {availableTags.length > 0 && (
                        <Box>
                            <Typography variant="subtitle2" gutterBottom>
                                Φιλτράρισμα με Ετικέτες:
                            </Typography>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                                {availableTags.map((tag, index) => (
                                    <Chip
                                        key={index}
                                        label={tag}
                                        clickable
                                        color={selectedTags.includes(tag) ? "primary" : "default"}
                                        onClick={() => handleTagToggle(tag)}
                                        icon={<LabelIcon />}
                                    />
                                ))}
                            </Box>
                        </Box>
                    )}
                </Box>
                <Divider sx={{ mb: 2 }} />
            </Collapse>
            
            {loading ? (
                <Typography>Φόρτωση αρχείων...</Typography>
            ) : filteredFiles.length === 0 ? (
                <Typography color="textSecondary">
                    {files.length === 0 
                        ? 'Δεν υπάρχουν αρχεία για αυτόν τον ασθενή.' 
                        : 'Δεν βρέθηκαν αρχεία που να ταιριάζουν με τα κριτήρια αναζήτησης.'}
                </Typography>
            ) : (
                <List>
                    {filteredFiles.map((file, index) => (
                        <FileItem
                            key={file.file_id}
                            file={file}
                            onViewFile={handleViewFile}
                            onDeleteFile={openDeleteDialog}
                        />
                    ))}
                </List>
            )}
            
            {/* Διάλογος Διαγραφής */}
            <Dialog
                open={deleteDialogOpen}
                onClose={closeDeleteDialog}
            >
                <DialogTitle>Διαγραφή Αρχείου</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Είστε βέβαιοι ότι θέλετε να διαγράψετε το αρχείο
                        {fileToDelete && ` "${fileToDelete.original_filename || fileToDelete.filename}"`};
                        Αυτή η ενέργεια δεν μπορεί να αναιρεθεί.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeDeleteDialog}>Ακύρωση</Button>
                    <Button onClick={handleDeleteFile} color="error" variant="contained">
                        Διαγραφή
                    </Button>
                </DialogActions>
            </Dialog>
            
            {/* Διάλογος Προβολής */}
            <Dialog
                open={previewDialogOpen}
                onClose={() => {
                    setPreviewDialogOpen(false);
                    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
                }}
                maxWidth="lg"
                fullWidth
            >
                <DialogTitle>
                    {previewFile?.original_filename || previewFile?.filename}
                    <IconButton
                        aria-label="close"
                        onClick={() => {
                             setPreviewDialogOpen(false);
                             if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
                         }}
                        sx={{ position: 'absolute', right: 8, top: 8 }}
                    >
                        <CloseIcon />
                    </IconButton>
                </DialogTitle>
                <DialogContent>
                     {previewLoading ? (
                         <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '70vh' }}>
                             <CircularProgress />
                         </Box>
                     ) : !previewObjectUrl ? (
                         <Typography color="error">Αποτυχία φόρτωσης προεπισκόπησης.</Typography>
                     ) : previewFile && previewFile.mime_type?.startsWith('image/') ? (
                        <Box sx={{ textAlign: 'center' }}>
                            <img 
                                src={previewObjectUrl}
                                alt={previewFile.filename}
                                style={{ maxWidth: '100%', maxHeight: '70vh' }}
                            />
                        </Box>
                    ) : previewFile && previewFile.mime_type === 'application/pdf' ? (
                        <Box sx={{ height: '70vh' }}>
                            <iframe
                                src={previewObjectUrl}
                                width="100%"
                                height="100%"
                                title={previewFile.filename}
                                frameBorder="0"
                            />
                        </Box>
                    ) : (
                        <Typography>Η προεπισκόπηση δεν είναι διαθέσιμη για αυτόν τον τύπο αρχείου.</Typography>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button 
                        onClick={() => handleDownloadFile(previewFile)} 
                        startIcon={<DownloadIcon />} 
                        disabled={previewLoading || !previewObjectUrl}
                    >
                        Λήψη
                    </Button>
                    <Button 
                        onClick={() => {
                             setPreviewDialogOpen(false);
                             if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
                         }}
                    >
                        Κλείσιμο
                    </Button>
                </DialogActions>
            </Dialog>
        </Paper>
    );
};

export default FileList;