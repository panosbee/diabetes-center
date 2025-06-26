import React, { useState, useCallback } from 'react';
import { Box, TextField, Button, Paper, Typography, List, ListItem, ListItemText, CircularProgress, IconButton } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import { useDataProvider, useNotify, useGetIdentity } from 'react-admin';
import { format } from 'date-fns';
import { el } from 'date-fns/locale';

const AIChatInterface = () => {
    const [query, setQuery] = useState('');
    const [conversation, setConversation] = useState([]);
    const [loading, setLoading] = useState(false);
    const [contextAmka, setContextAmka] = useState('');
    const dataProvider = useDataProvider();
    const notify = useNotify();
    const { identity } = useGetIdentity(); // Για να ξέρουμε ποιος ρωτάει (ίσως χρειαστεί)

    const formatTimestamp = (dateString) => {
        try {
            return format(new Date(dateString), "HH:mm", { locale: el });
        } catch (e) {
            return '';
        }
    };

    const handleSendQuery = useCallback(async () => {
        if (!query.trim()) return;

        const userMessage = {
            sender: 'user',
            text: query,
            timestamp: new Date().toISOString()
        };

        setConversation(prev => [...prev, userMessage]);
        setQuery('');
        setLoading(true);

        try {
            // Προετοιμασία δεδομένων για το backend
            const payload = { query: query };
            if (contextAmka) {
                payload.amka = contextAmka;
            }

            console.log(`Sending to /api/ai/query:`, payload); // Log το payload

            // Κλήση στο backend API
            const response = await dataProvider.create('ai/query', { data: payload }); 
            
            console.log("Received from /api/ai/query:", response); // Debug Log

            if (response?.data?.response) {
                const aiMessage = {
                    sender: 'ai',
                    text: response.data.response,
                    evidence: response.data.pubmed_evidence || [], // Store PubMed evidence
                    riskAssessment: response.data.risk_assessment || null,
                    recommendations: response.data.recommendations || [],
                    geneticsAnalysis: response.data.genetics_analysis || null,
                    context: response.data.context || {},
                    timestamp: new Date().toISOString()
                };
                setConversation(prev => [...prev, aiMessage]);
            } else {
                 throw new Error("Invalid response structure from AI backend");
            }

        } catch (error) {
            console.error("Error querying AI:", error);
            notify('Σφάλμα κατά την επικοινωνία με την AI.', { type: 'error' });
            const errorMessage = {
                sender: 'ai',
                text: 'Συγγνώμη, παρουσιάστηκε σφάλμα. Προσπαθήστε ξανά.',
                timestamp: new Date().toISOString(),
                isError: true
            };
            setConversation(prev => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    }, [query, dataProvider, notify, contextAmka]);

    const handleKeyPress = (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); // Αποτροπή νέας γραμμής
            handleSendQuery();
        }
    };

    return (
        <Paper elevation={3} sx={{ p: 3, display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)' }}> {/* Προσαρμογή ύψους */}
            <Typography variant="h5" gutterBottom sx={{ mb: 2 }}>
                🤖 AI Assistant με PubMed & Genetics
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Ολοκληρωμένη AI υποστήριξη με πρόσβαση σε δεδομένα ασθενών, PubMed αρθρογραφία και γενετική ανάλυση
            </Typography>
            
            {/* Περιοχή Εμφάνισης Συνομιλίας */}
            <Box sx={{ flexGrow: 1, overflowY: 'auto', mb: 2, border: '1px solid #e0e0e0', borderRadius: 1, p: 2 }}>
                <List>
                    {conversation.map((msg, index) => (
                        <ListItem 
                            key={index} 
                            sx={{ 
                                display: 'flex', 
                                justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                                mb: 1 
                            }}
                        >
                            <Paper 
                                elevation={1} 
                                sx={{ 
                                    p: 1.5, 
                                    bgcolor: msg.sender === 'user' ? 'primary.light' : 'grey.200',
                                    color: msg.sender === 'user' ? 'primary.contrastText' : 'text.primary',
                                    borderRadius: msg.sender === 'user' ? '20px 20px 5px 20px' : '20px 20px 20px 5px',
                                    maxWidth: '75%' 
                                }}
                            >
                                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                                    {msg.text}
                                </Typography>
                                
                                {/* Display PubMed evidence if exists */}
                                {msg.evidence && msg.evidence.length > 0 && (
                                    <Box sx={{ mt: 1, pt: 1, borderTop: '1px dashed rgba(0,0,0,0.1)' }}>
                                        <Typography variant="caption" fontWeight="bold" sx={{ display: 'block', mb: 0.5 }}>
                                            📚 PubMed Αποδεικτικά στοιχεία:
                                        </Typography>
                                        {msg.evidence.map((article, idx) => (
                                            <Typography
                                                key={idx}
                                                variant="caption"
                                                component="div"
                                                sx={{ fontStyle: 'italic', mb: 0.5 }}
                                            >
                                                (PMID: <a
                                                    href={`https://pubmed.ncbi.nlm.nih.gov/${article.pmid}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    style={{ color: 'inherit', textDecoration: 'underline' }}
                                                >
                                                    {article.pmid}
                                                </a>) "{article.title}"
                                                {article.similarity && (
                                                    <span style={{ color: '#666', fontSize: '0.8em' }}>
                                                        {' '}(Σχετικότητα: {Math.round(article.similarity * 100)}%)
                                                    </span>
                                                )}
                                            </Typography>
                                        ))}
                                    </Box>
                                )}
                                
                                {/* Display genetics analysis if exists */}
                                {msg.geneticsAnalysis && (
                                    <Box sx={{ mt: 1, pt: 1, borderTop: '1px dashed rgba(0,0,0,0.1)' }}>
                                        <Typography variant="caption" fontWeight="bold" sx={{ display: 'block', mb: 0.5 }}>
                                            🧬 Γενετική Ανάλυση:
                                        </Typography>
                                        <Typography variant="caption" component="div" sx={{ whiteSpace: 'pre-wrap' }}>
                                            {msg.geneticsAnalysis.answer || msg.geneticsAnalysis.message}
                                        </Typography>
                                    </Box>
                                )}
                                
                                {/* Display risk assessment if exists */}
                                {msg.riskAssessment && (
                                    <Box sx={{ mt: 1, pt: 1, borderTop: '1px dashed rgba(0,0,0,0.1)' }}>
                                        <Typography variant="caption" fontWeight="bold" sx={{ display: 'block', mb: 0.5 }}>
                                            Εκτίμηση Κινδύνου:
                                        </Typography>
                                        <Typography variant="caption" component="div">
                                            {msg.riskAssessment.level} - {msg.riskAssessment.description}
                                        </Typography>
                                    </Box>
                                )}
                                
                                {/* Display recommendations if exists */}
                                {msg.recommendations && msg.recommendations.length > 0 && (
                                    <Box sx={{ mt: 1, pt: 1, borderTop: '1px dashed rgba(0,0,0,0.1)' }}>
                                        <Typography variant="caption" fontWeight="bold" sx={{ display: 'block', mb: 0.5 }}>
                                            Προτάσεις:
                                        </Typography>
                                        <List dense sx={{ py: 0 }}>
                                            {msg.recommendations.map((rec, idx) => (
                                                <ListItem key={idx} sx={{ py: 0, pl: 0 }}>
                                                    <ListItemText
                                                        primary={rec.text}
                                                        primaryTypographyProps={{ variant: 'caption' }}
                                                        secondary={rec.evidence_level ? `Επίπεδο Αποδεικτικών: ${rec.evidence_level}` : null}
                                                        secondaryTypographyProps={{ variant: 'caption', fontStyle: 'italic' }}
                                                    />
                                                </ListItem>
                                            ))}
                                        </List>
                                    </Box>
                                )}
                                <Typography variant="caption" display="block" sx={{ textAlign: 'right', mt: 0.5, opacity: 0.7 }}>
                                    {formatTimestamp(msg.timestamp)}
                                </Typography>
                            </Paper>
                        </ListItem>
                    ))}
                    {loading && (
                         <ListItem sx={{ justifyContent: 'flex-start' }}>
                            <CircularProgress size={24} />
                         </ListItem>
                    )}
                </List>
            </Box>
            
            {/* Περιοχή Εισαγωγής Κειμένου */}
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <TextField
                    variant="outlined"
                    fullWidth
                    multiline // Επιτρέπει πολλαπλές γραμμές
                    maxRows={4} // Όριο για να μη γίνει πολύ μεγάλο
                    placeholder="Ρωτήστε την AI..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={handleKeyPress} // Αποστολή με Enter
                    disabled={loading}
                    sx={{ mr: 1 }}
                />
                <IconButton 
                    color="primary" 
                    onClick={handleSendQuery} 
                    disabled={loading || !query.trim()}
                    size="large"
                >
                    <SendIcon />
                </IconButton>
            </Box>

            {/* --- Πεδίο για AMKA Ασθενή --- */}
            <TextField
                label="AMKA Ασθενή για Context (Προαιρετικό)"
                variant="outlined"
                size="small"
                value={contextAmka}
                onChange={(e) => setContextAmka(e.target.value)}
                sx={{ mb: 1 }}
            />
            {/* -------------------------- */}
        </Paper>
    );
};

export default AIChatInterface; 