import React, { useState } from 'react';
import {
  useRecordContext,
  useNotify,
  Loading
} from 'react-admin';
import {
  Box,
  Button,
  Typography,
  Paper,
  CircularProgress,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  Tabs,
  Tab,
  Slider,
  FormControl,
  FormLabel,
  TextField,
  Grid,
  Alert,
  AlertTitle,
  Chip,
  
  IconButton,
  Switch,
  FormControlLabel,
  Autocomplete
} from '@mui/material';
import {
  Analytics as AnalyticsIcon,
  ExpandMore as ExpandMoreIcon,
  Psychology as PsychologyIcon,
  ShowChart as ShowChartIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
  PlayArrow as PlayArrowIcon,
  Settings as SettingsIcon,
  TrendingUp as TrendingUpIcon,
  LocalDining as MealIcon,
  FitnessCenter as ExerciseIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Compare as CompareIcon,
  AccountTree as MindmapIcon
} from '@mui/icons-material';
import { Tooltip } from '@mui/material'; // ΔΙΟΡΘΩΣΗ: σωστό import Tooltip
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts';

/**
 * Component για την ανάλυση των ιστορικών μετρήσεων του ασθενή με AI
 */
const PatientAIAnalysis = () => {
  const record = useRecordContext();
  const notify = useNotify();
  const [loading, setLoading] = useState(false);
  const [analysisData, setAnalysisData] = useState(null);

  // Χειρισμός του κουμπιού ανάλυσης δεδομένων
  const handleAnalyzeData = async () => {
    if (!record?.id) {
      notify('Δεν βρέθηκε αναγνωριστικό ασθενή', { type: 'error' });
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Δεν βρέθηκε token αυθεντικοποίησης');
      }

      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/ai/analysis`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          patient_id: record.id,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error ${response.status}`);
      }

      const resultData = await response.json();
      setAnalysisData({
        analysis: resultData.analysis,
        recommendations: resultData.recommendations || [],
        riskAssessment: resultData.risk_assessment || {}
      });
    } catch (error) {
      console.error('Error analyzing patient data:', error);
      notify(`Σφάλμα κατά την ανάλυση: ${error.message}`, { type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  if (!record) return null;

  // Μορφοποίηση της ανάλυσης
  const formatAnalysis = (text) => {
    if (!text) return null;

    // Αφαιρούμε το section "Limitations:" και ό,τι ακολουθεί
    const limitationsIndex = text.indexOf('Limitations:');
    let mainText = limitationsIndex !== -1 ? text.substring(0, limitationsIndex).trim() : text;

    // Χειρισμός τίτλων και παραγράφων
    let formattedText = mainText
      .replace(/\n\n/g, '<br/><br/>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Χειρισμός λιστών αν υπάρχουν
    if (mainText.includes('\n-')) {
      formattedText = formattedText.replace(/\n- (.*)/g, '<li>$1</li>');
      formattedText = formattedText.replace(/<li>(.*?)<\/li>(\s*)<li>/g, '<li>$1</li><li>');
      formattedText = formattedText.replace(/(<li>.*<\/li>)+/g, '<ul>$&</ul>');
    }

    return <div dangerouslySetInnerHTML={{ __html: formattedText }} />;
  };

  // Format risk data for visualization
  const formatRiskData = () => {
    if (!analysisData?.riskAssessment) return [];
    
    // Handle both object and array formats from backend
    if (Array.isArray(analysisData.riskAssessment)) {
      return analysisData.riskAssessment.map(risk => ({
        name: risk.name,
        risk: Math.min(100, Math.round(risk.value * 100)) // Cap at 100%
      }));
    } else {
      return Object.entries(analysisData.riskAssessment).map(([riskName, riskValue]) => ({
        name: riskName,
        risk: Math.min(100, Math.round(riskValue * 100)) // Cap at 100%
      }));
    }
  };

  // === What-If Scenarios State ===
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [scenarioResults, setScenarioResults] = useState(null);
  const [scenarioParams, setScenarioParams] = useState({
    basal_change: 0,
    bolus_change: 0,
    carb_ratio_change: 0,
    correction_factor_change: 0,
    meal_carbs: 60,
    meal_timing: 60,
    exercise_intensity: 0,
    exercise_duration: 0,
    simulation_hours: 24
  });
  const [validationWarnings, setValidationWarnings] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(null);

  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (event, newValue) => {
      setTabValue(newValue);
  };

  // Enhanced visualization data
  const generateRecommendationChartData = () => {
    if (!analysisData.recommendations || analysisData.recommendations.length === 0) return [];
    
    return analysisData.recommendations.map((rec, index) => ({
      name: `Σύσταση ${index + 1}`,
      priority: rec.priority || 1,
      impact: Number(rec.clinicalImpact) || 0,
      urgency: Number(rec.urgency) || 0,
      evidence_strength: Number(rec.evidenceStrength) || 0,
      category: rec.type || 'general'
    }));
  };

  const generateRiskTrendData = () => {
    // Simulate risk progression over time
    const dates = [];
    const now = new Date();
    for (let i = 6; i >= 0; i--) {
      const date = new Date(now);
      date.setMonth(date.getMonth() - i);
      dates.push(date.toISOString().slice(0, 7)); // YYYY-MM format
    }
    
    return dates.map((date, index) => ({
      date,
      hypoglycemia: Math.max(10, 30 - index * 2 + Math.random() * 10),
      hyperglycemia: Math.max(15, 40 - index * 3 + Math.random() * 15),
      cardiovascular: Math.max(20, 50 - index * 2 + Math.random() * 10),
      overall_risk: Math.max(25, 60 - index * 4 + Math.random() * 15)
    }));
  };

  const getRecommendationPriorityColor = (priority) => {
    switch(priority) {
      case 1: return '#ff4444'; // High priority - Red
      case 2: return '#ff9800'; // Medium priority - Orange  
      case 3: return '#4caf50'; // Low priority - Green
      default: return '#2196f3'; // Default - Blue
    }
  };

  const RISK_COLORS = ['#ff4444', '#ff9800', '#ffeb3b', '#4caf50'];
  const PRIORITY_COLORS = ['#f44336', '#ff9800', '#4caf50', '#2196f3'];

  // === Mapping functions for backend data ===
  const mapRecommendation = (rec) => ({
    ...rec,
    clinicalImpact: rec.clinical_impact ?? rec.clinicalImpact ?? 0,
    urgency: rec.urgency ?? 0,
    evidenceStrength: rec.evidence?.evidence_quality === 'high' ? 100 : rec.evidence?.evidence_quality === 'moderate' ? 70 : 40,
    type: rec.type?.toLowerCase?.() ?? rec.type ?? 'general',
    priority: rec.priority ?? 3,
    action: rec.action ?? '',
    evidence: rec.evidence?.pmids?.length ? rec.evidence.pmids.join(', ') : (rec.evidence?.source || ''),
  });

  const mapRiskAssessment = (riskAssessment) => {
    // Accepts both new and legacy formats
    if (!riskAssessment) return [];
    // If array of risk factors
    if (Array.isArray(riskAssessment)) {
      return riskAssessment.filter(risk =>
        typeof risk.value === 'number' && risk.name && risk.value > 0
      ).map(risk => ({
        name: risk.name,
        risk: Math.min(100, Math.round(risk.value))
      }));
    } else if (riskAssessment.risk_factors) {
      return riskAssessment.risk_factors.filter(rf =>
        typeof rf.value === 'number' && rf.name && rf.value > 0
      ).map(rf => ({
        name: rf.name,
        risk: Math.min(100, Math.round(rf.value))
      }));
    } else {
      // Filter out non-numeric and meta fields
      const ignoreKeys = ['level', 'assessment_date', 'total_score', 'predictions', 'risk_distribution', 'evidence_summary'];
      return Object.entries(riskAssessment)
        .filter(([riskName, riskValue]) =>
          !ignoreKeys.includes(riskName) && typeof riskValue === 'number' && riskValue > 0
        )
        .map(([riskName, riskValue]) => ({
          name: riskName,
          risk: Math.min(100, Math.round(riskValue))
        }));
    }
  };

  // === Use mapping for recommendations and risk assessment ===
  const mappedRecommendations = (analysisData?.recommendations || []).map(mapRecommendation);
  const mappedRiskData = mapRiskAssessment(analysisData?.riskAssessment);

  // ΑΝΤΙΚΑΤΑΣΤΑΣΗ του scenarioPresets array με ID fields:
  const scenarioPresets = [
    {
      id: 'mild_adjustment', // ΠΡΟΣΘΗΚΗ ID για React key
      name: "Ήπια Προσαρμογή",
      description: "Μικρές αλλαγές για βελτίωση",
      params: {
        basal_change: 10,
        bolus_change: 5,
        meal_carbs: 45,
        simulation_hours: 12
      }
    },
    {
      id: 'exercise_scenario', // ΠΡΟΣΘΗΚΗ ID
      name: "Σενάριο Άσκησης",
      description: "Προσαρμογή για άσκηση",
      params: {
        basal_change: -20,
        exercise_intensity: 60,
        exercise_duration: 45,
        meal_carbs: 30,
        simulation_hours: 8
      }
    },
    {
      id: 'large_meal', // ΠΡΟΣΘΗΚΗ ID
      name: "Μεγάλο Γεύμα",
      description: "Διαχείριση πολλών υδατανθράκων",
      params: {
        meal_carbs: 80,
        bolus_change: 15,
        carb_ratio_change: -10,
        simulation_hours: 6
      }
    }
  ];

  // ΔΙΟΡΘΩΣΗ handleParamChange function:
  const handleParamChange = async (param, value) => {
    const newParams = { ...scenarioParams, [param]: value };
    setScenarioParams(newParams);
    
    // Real-time validation - ΔΙΟΡΘΩΣΗ: check for record
    if (!record?.id) return; // Skip validation if no patient
    
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return; // Skip validation if no token
      
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/scenarios/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          scenario_params: newParams
        }),
      });
      
      if (response.ok) {
        const validation = await response.json();
        setValidationWarnings(validation.warnings || []);
      }
    } catch (error) {
      console.error('Validation error:', error);
      // Don't show error to user for validation - it's not critical
    }
  };

  // ΔΙΟΡΘΩΣΗ handleRunScenario function:
  const handleRunScenario = async () => {
    // ΔΙΟΡΘΩΣΗ: Έλεγχος ότι υπάρχει record
    if (!record || !record.id) {
      notify('Δεν βρέθηκε αναγνωριστικό ασθενή', { type: 'error' });
      return;
    }

    setWhatIfLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Δεν βρέθηκε token αυθεντικοποίησης');
      }

      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/scenarios/simulate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          patient_id: record.id,
          scenario_params: scenarioParams
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error ${response.status}`);
      }

      const resultData = await response.json();
      setScenarioResults(resultData);
      notify('Προσομοίωση ολοκληρώθηκε επιτυχώς!', { type: 'success' });
    } catch (error) {
      console.error('Error running scenario:', error);
      notify(`Σφάλμα κατά την προσομοίωση: ${error.message}`, { type: 'error' });
    } finally {
      setWhatIfLoading(false);
    }
  };

  // ΜΕΤΑΚΙΝΗΣΗ των helper functions ΜΕΣΑ στο component:
  const formatSimulationData = () => {
    if (!scenarioResults?.simulation?.time_points) return [];
    return scenarioResults.simulation.time_points.map((hour, index) => ({
      hour: hour.toFixed(1),
      glucose: scenarioResults.simulation.glucose_levels[index],
      target_low: 70,
      target_high: 180
    }));
  };

  const formatComparisonData = () => {
    if (!scenarioResults?.comparison_data) return [];
    const { baseline, scenario } = scenarioResults.comparison_data;
    return [
      {
        metric: 'Μέση Γλυκόζη',
        baseline: baseline.glucose,
        scenario: scenario.glucose
      },
      {
        metric: 'HbA1c (%)',
        baseline: baseline.hba1c,
        scenario: scenario.hba1c
      },
      {
        metric: 'Time in Range (%)',
        baseline: baseline.tir_70_180,
        scenario: scenario.tir_70_180
      },
      {
        metric: 'Μεταβλητότητα (%)',
        baseline: baseline.glucose_cv,
        scenario: scenario.glucose_cv
      }
    ];
  };

  const MindmapVisualization = ({ data }) => {
    const svgRef = React.useRef();
    React.useEffect(() => {
      if (!data || !svgRef.current) return;
      const svg = svgRef.current;
      const width = 400;
      const height = 400;
      svg.innerHTML = '';
      const createNode = (node, x, y, level = 0) => {
        const radius = level === 0 ? 40 : 30;
        const color = level === 0 ? '#2196f3' : 
                     node.type === 'category' ? '#4caf50' :
                     node.type === 'risk' ? '#f44336' : '#ff9800';
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', x);
        circle.setAttribute('cy', y);
        circle.setAttribute('r', radius);
        circle.setAttribute('fill', color);
        circle.setAttribute('stroke', 'white');
        circle.setAttribute('stroke-width', '2');
        svg.appendChild(circle);
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', x);
        text.setAttribute('y', y);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('dominant-baseline', 'middle');
        text.setAttribute('fill', 'white');
        text.setAttribute('font-size', level === 0 ? '12' : '10');
        text.setAttribute('font-weight', 'bold');
        text.textContent = node.label.length > 15 ? node.label.substring(0, 15) + '...' : node.label;
        svg.appendChild(text);
        if (node.children && node.children.length > 0) {
          const angleStep = (2 * Math.PI) / node.children.length;
          const distance = level === 0 ? 120 : 80;
          node.children.forEach((child, index) => {
            const angle = index * angleStep;
            const childX = x + distance * Math.cos(angle);
            const childY = y + distance * Math.sin(angle);
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', x);
            line.setAttribute('y1', y);
            line.setAttribute('x2', childX);
            line.setAttribute('y2', childY);
            line.setAttribute('stroke', '#ccc');
            line.setAttribute('stroke-width', '2');
            svg.appendChild(line);
            createNode(child, childX, childY, level + 1);
          });
        }
      };
      createNode(data, width / 2, height / 2);
    }, [data]);
    return (
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox="0 0 400 400"
        style={{ background: '#f5f5f5' }}
      />
    );
  };

  return (
      <Box mt={3}>
          <Paper elevation={3} sx={{ p: 3, mb: 2, borderRadius: 2, overflow: 'hidden' }}>
              <Box display="flex" alignItems="center" mb={2}>
                  <PsychologyIcon color="primary" sx={{ mr: 1, fontSize: 28 }} />
                  <Typography variant="h6">Ανάλυση Δεδομένων Ασθενή με AI</Typography>
              </Box>

              <Typography variant="body2" color="text.secondary" paragraph>
                  Η λειτουργία αυτή χρησιμοποιεί τεχνητή νοημοσύνη για να αναλύσει όλες τις ιστορικές
                  μετρήσεις του ασθενή, αναδεικνύοντας τάσεις και παρέχοντας προτάσεις βελτίωσης της θεραπείας.
              </Typography>

              {loading && (
                  <Box display="flex" flexDirection="column" alignItems="center" my={4}>
                      <CircularProgress size={40} />
                      <Typography variant="body2" color="text.secondary" mt={2}>
                          Γίνεται ανάλυση των δεδομένων...
                      </Typography>
                  </Box>
              )}

              <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 2, mt: 2 }}>
                <Tab label="Ανάλυση" icon={<AssessmentIcon />} />
                <Tab label="Συστάσεις" icon={<PsychologyIcon />} />
                <Tab label="Εκτίμηση Κινδύνων" icon={<ShowChartIcon />} />
                <Tab label="What-If Scenarios" icon={<TrendingUpIcon />} />
              </Tabs>

              {tabValue === 0 && (
                <Box>
                  {analysisData?.analysis ? (
                    <Accordion
                      defaultExpanded
                      elevation={0}
                      sx={{
                        '&:before': { display: 'none' },
                        border: '1px solid',
                        borderColor: 'divider',
                        borderRadius: '8px !important',
                        overflow: 'hidden'
                      }}
                    >
                      <AccordionSummary
                        expandIcon={<ExpandMoreIcon />}
                        sx={{
                          backgroundColor: 'rgba(0, 0, 0, 0.02)',
                          '&.Mui-expanded': { minHeight: 48 }
                        }}
                      >
                        <Typography fontWeight={500}>Αποτελέσματα Ανάλυσης</Typography>
                      </AccordionSummary>
                      <AccordionDetails sx={{ pt: 2 }}>
                        <Card variant="outlined" sx={{ mb: 2 }}>
                          <CardContent>
                            <Typography component="div" style={{ lineHeight: 1.7 }}>
                              {formatAnalysis(analysisData.analysis)}
                            </Typography>
                          </CardContent>
                        </Card>
                      </AccordionDetails>
                    </Accordion>
                  ) : (
                    <Box textAlign="center" p={4}>
                      <Typography variant="body1" color="textSecondary">
                        {loading
                          ? 'Γίνεται ανάλυση των δεδομένων...'
                          : 'Παρακαλώ τρέξτε την ανάλυση για να δείτε τα αποτελέσματα'}
                      </Typography>
                      {!loading && (
                        <Button
                          variant="contained"
                          startIcon={<AnalyticsIcon />}
                          onClick={handleAnalyzeData}
                          sx={{ mt: 2 }}
                        >
                          Ανάλυση Δεδομένων
                        </Button>
                      )}
                    </Box>
                  )}
                </Box>
              )}

              {tabValue === 1 && (
                <Box>
                  {mappedRecommendations.length > 0 ? (
                    <Box mt={2}>
                      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                        <PsychologyIcon sx={{ mr: 1, color: 'primary.main' }} />
                        AI-Driven Clinical Recommendations
                      </Typography>
                      <Box sx={{ mb: 3 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          📊 Προτεραιότητα & Αντίκτυπος Συστάσεων
                        </Typography>
                        <ResponsiveContainer width="100%" height={300}>
                          <BarChart data={mappedRecommendations.map((rec, index) => ({
                            name: `Σύσταση ${index + 1}`,
                            priority: rec.priority,
                            impact: rec.clinicalImpact,
                            urgency: rec.urgency,
                            evidence_strength: rec.evidenceStrength,
                            category: rec.type
                          }))}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" />
                            <YAxis domain={[0, 100]} />
                            <RechartsTooltip
                              formatter={(value, name) => [
                                `${value}%`,
                                name === 'priority' ? 'Προτεραιότητα' :
                                name === 'impact' ? 'Κλινικός Αντίκτυπος' :
                                name === 'urgency' ? 'Επείγον' : 'Ισχύς Αποδείξεων'
                              ]}
                            />
                            <Legend />
                            <Bar dataKey="impact" name="Κλινικός Αντίκτυπος" fill="#2196f3" />
                            <Bar dataKey="urgency" name="Επείγον" fill="#ff9800" />
                            <Bar dataKey="evidence_strength" name="Ισχύς Αποδείξεων" fill="#4caf50" />
                          </BarChart>
                        </ResponsiveContainer>
                        <Box sx={{ mt: 2, p: 1.5, backgroundColor: '#f9f9f9', borderRadius: 1, border: '1px solid #e0e0e0' }}>
                          <Typography variant="body2" component="div" sx={{ fontWeight: 'bold', mb: 1 }}>
                            Εξήγηση Μετρικών:
                          </Typography>
                          <Typography variant="body2" component="div">
                            <ul style={{ marginTop: 0, paddingLeft: 20 }}>
                              <li><strong>Κλινικός Αντίκτυπος</strong>: Πόσο σημαντική είναι η σύσταση για την υγεία του ασθενούς (0-100%)</li>
                              <li><strong>Επείγον</strong>: Πόσο γρήγορα πρέπει να εφαρμοστεί η σύσταση (0-100%)</li>
                              <li><strong>Ισχύς Αποδείξεων</strong>: Πόσο ισχυρές είναι οι επιστημονικές αποδείξεις (0-100%)</li>
                            </ul>
                          </Typography>
                        </Box>
                      </Box>
                      {mappedRecommendations.map((rec, index) => (
                        <Accordion key={index} sx={{ mb: 2, border: '1px solid #e0e0e0' }}>
                          <AccordionSummary 
                            expandIcon={<ExpandMoreIcon />}
                            sx={{ 
                              bgcolor: rec.priority === 1 ? '#ffebee' : rec.priority === 2 ? '#fff3e0' : '#e8f5e8',
                              borderLeft: `4px solid ${getRecommendationPriorityColor(rec.priority)}` 
                            }}
                          >
                            <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                              <Typography sx={{ fontWeight: 'bold', flexGrow: 1 }}>
                                {rec.priority === 1 ? '🔴' : rec.priority === 2 ? '🟡' : '🟢'} 
                                {' '}Σύσταση {index + 1}: {rec.action}
                              </Typography>
                              <Typography variant="caption" sx={{ 
                                bgcolor: getRecommendationPriorityColor(rec.priority),
                                color: 'white',
                                px: 1,
                                py: 0.5,
                                borderRadius: 1,
                                mr: 2
                              }}>
                                {rec.type?.toUpperCase() || 'GENERAL'}
                              </Typography>
                            </Box>
                          </AccordionSummary>
                          <AccordionDetails>
                            <Box>
                              <Typography variant="body1" sx={{ fontWeight: 'bold', mb: 2 }}>
                                {rec.action}
                              </Typography>
                              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 2 }}>
                                <Typography variant="body2">
                                  <strong>Τύπος:</strong> {rec.type || 'Γενική'}
                                </Typography>
                                <Typography variant="body2">
                                  <strong>Προτεραιότητα:</strong> {
                                    rec.priority === 1 ? 'Υψηλή' : 
                                    rec.priority === 2 ? 'Μέτρια' : 'Χαμηλή'
                                  }
                                </Typography>
                              </Box>
                              {rec.evidence && (
                                <Typography variant="body2" sx={{ 
                                  mt: 1, 
                                  fontStyle: 'italic',
                                  bgcolor: '#f5f5f5',
                                  p: 1,
                                  borderRadius: 1
                                }}>
                                  📚 <strong>Αιτιολογία:</strong> {rec.evidence}
                                </Typography>
                              )}
                            </Box>
                          </AccordionDetails>
                        </Accordion>
                      ))}
                    </Box>
                  ) : (
                    <Box textAlign="center" p={4}>
                      <Typography variant="body1" color="textSecondary">
                        {loading
                          ? 'Γίνεται ανάλυση των δεδομένων...'
                          : 'Παρακαλώ τρέξτε την ανάλυση για να δείτε τις συστάσεις'}
                      </Typography>
                      {!loading && (
                        <Button
                          variant="contained"
                          startIcon={<AnalyticsIcon />}
                          onClick={handleAnalyzeData}
                          sx={{ mt: 2 }}
                        >
                          Ανάλυση Δεδομένων
                        </Button>
                      )}
                    </Box>
                  )}
                </Box>
              )}

              {tabValue === 2 && (
                <Box>
                  {mappedRiskData.length > 0 ? (
                    <Box mt={2}>
                      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                        <ShowChartIcon sx={{ mr: 1, color: 'error.main' }} />
                        AI-Driven Risk Assessment & Prediction
                      </Typography>
                      <Box sx={{ mb: 4 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          ⚠️ Τρέχουσα Εκτίμηση Κινδύνων
                        </Typography>
                        <ResponsiveContainer width="100%" height={400}>
                          <BarChart
                            data={mappedRiskData}
                            layout="vertical"
                            margin={{ top: 20, right: 30, left: 100, bottom: 50 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                              type="number"
                              domain={[0, 100]}
                              tickFormatter={(value) => `${value}%`}
                              label={{ value: 'Πιθανότητα Κινδύνου (%)', position: 'insideBottom', offset: -5 }}
                            />
                            <YAxis
                              type="category"
                              dataKey="name"
                              width={120}
                              tick={{ fontSize: 12 }}
                            />
                            <RechartsTooltip
                              formatter={(value) => [`${value}%`, 'Κίνδυνος']}
                              labelFormatter={(value) => `Παράγοντας: ${value}`}
                            />
                            <Legend />
                            <Bar
                              dataKey="risk"
                              name="Επίπεδο Κινδύνου"
                              fill="#8884d8"
                              animationDuration={1500}
                            >
                              {mappedRiskData.map((entry, index) => (
                                <Cell
                                  key={`cell-${index}`}
                                  fill={
                                    entry.risk >= 70 ? '#ff4d4d' :
                                    entry.risk >= 50 ? '#ff9800' :
                                    entry.risk >= 30 ? '#ffeb3b' : '#66bb6a'
                                  }
                                />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </Box>
                    </Box>
                  ) : (
                    <Box textAlign="center" p={4}>
                      <Typography variant="body1" color="textSecondary">
                        {loading
                          ? 'Γίνεται ανάλυση των δεδομένων...'
                          : 'Παρακαλώ τρέξτε την ανάλυση για να δείτε την εκτίμηση κινδύνων'}
                      </Typography>
                      {!loading && (
                        <Button
                          variant="contained"
                          startIcon={<AnalyticsIcon />}
                          onClick={handleAnalyzeData}
                          sx={{ mt: 2 }}
                        >
                          Ανάλυση Δεδομένων
                        </Button>
                      )}
                    </Box>
                  )}
                </Box>
              )}

              {tabValue === 3 && (
                <Box>
                  <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                    <TrendingUpIcon sx={{ mr: 1, color: 'primary.main' }} />
                    Digital Twin - What-If Scenarios
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    Προσομοιώστε διαφορετικά σενάρια διαχείρισης διαβήτη και δείτε τα αναμενόμενα αποτελέσματα
                    στη γλυκόζη, τον κίνδυνο υπογλυκαιμίας και τη συνολική κατάσταση του ασθενή.
                  </Typography>
                  {/* Validation Warnings */}
                  {validationWarnings.length > 0 && (
                    <Alert severity="warning" sx={{ mb: 2 }}>
                      <AlertTitle>Προσοχή στις Παραμέτρους</AlertTitle>
                      <ul style={{ margin: 0, paddingLeft: 20 }}>
                        {validationWarnings.map((warning, index) => (
                          <li key={index}>{warning}</li>
                        ))}
                      </ul>
                    </Alert>
                  )}
                  <Grid container spacing={3}>
                    {/* Left Panel - Controls */}
                    <Grid item xs={12} md={6}>
                      <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
                        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                          <SettingsIcon sx={{ mr: 1 }} />
                          Παράμετροι Σεναρίου
                        </Typography>
                        {/* Preset Selection */}
                        <Box sx={{ mb: 3 }}>
                          <FormLabel component="legend" sx={{ mb: 1, fontWeight: 'bold' }}>
                            Προκαθορισμένα Σενάρια
                          </FormLabel>
                          {/* ΔΙΟΡΘΩΣΗ Autocomplete: */}
                          <Autocomplete
                            value={selectedPreset}
                            onChange={(event, newValue) => {
                              setSelectedPreset(newValue);
                              if (newValue) {
                                setScenarioParams(prev => ({
                                  ...prev,
                                  ...newValue.params
                                }));
                              }
                            }}
                            options={scenarioPresets}
                            getOptionLabel={(option) => option.name}
                            renderInput={(params) => (
                              <TextField
                                {...params}
                                placeholder="Επιλέξτε προκαθορισμένο σενάριο..."
                                variant="outlined"
                                size="small"
                              />
                            )}
                            renderOption={(props, option) => {
                              // ΔΙΟΡΘΩΣΗ: Extract key separately
                              const { key, ...otherProps } = props;
                              return (
                                <Box component="li" key={option.id} {...otherProps}>
                                  <Box>
                                    <Typography variant="body2" fontWeight="bold">
                                      {option.name}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                      {option.description}
                                    </Typography>
                                  </Box>
                                </Box>
                              );
                            }}
                          />
                        </Box>
                        {/* Insulin Adjustments */}
                        <Box sx={{ mb: 3 }}>
                          <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold', color: 'primary.main' }}>
                            🩸 Προσαρμογές Ινσουλίνης
                          </Typography>
                          <Box sx={{ mb: 2 }}>
                            <FormLabel component="legend" sx={{ mb: 1 }}>
                              Βασική Ινσουλίνη: {scenarioParams.basal_change > 0 ? '+' : ''}{scenarioParams.basal_change}%
                            </FormLabel>
                            <Slider
                              value={scenarioParams.basal_change}
                              onChange={(e, value) => handleParamChange('basal_change', value)}
                              min={-50}
                              max={50}
                              step={5}
                              marks={[
                                { value: -50, label: '-50%' },
                                { value: 0, label: '0%' },
                                { value: 50, label: '+50%' }
                              ]}
                              valueLabelDisplay="auto"
                              valueLabelFormat={(value) => `${value > 0 ? '+' : ''}${value}%`}
                              color={Math.abs(scenarioParams.basal_change) > 30 ? 'error' : 'primary'}
                            />
                          </Box>
                          <Box sx={{ mb: 2 }}>
                            <FormLabel component="legend" sx={{ mb: 1 }}>
                              Bolus Ινσουλίνη: {scenarioParams.bolus_change > 0 ? '+' : ''}{scenarioParams.bolus_change}%
                            </FormLabel>
                            <Slider
                              value={scenarioParams.bolus_change}
                              onChange={(e, value) => handleParamChange('bolus_change', value)}
                              min={-50}
                              max={50}
                              step={5}
                              marks={[
                                { value: -50, label: '-50%' },
                                { value: 0, label: '0%' },
                                { value: 50, label: '+50%' }
                              ]}
                              valueLabelDisplay="auto"
                              valueLabelFormat={(value) => `${value > 0 ? '+' : ''}${value}%`}
                              color={Math.abs(scenarioParams.bolus_change) > 30 ? 'error' : 'primary'}
                            />
                          </Box>
                          <Box sx={{ mb: 2 }}>
                            <FormLabel component="legend" sx={{ mb: 1 }}>
                              Carb Ratio: {scenarioParams.carb_ratio_change > 0 ? '+' : ''}{scenarioParams.carb_ratio_change}%
                            </FormLabel>
                            <Slider
                              value={scenarioParams.carb_ratio_change}
                              onChange={(e, value) => handleParamChange('carb_ratio_change', value)}
                              min={-30}
                              max={30}
                              step={5}
                              marks={[
                                { value: -30, label: '-30%' },
                                { value: 0, label: '0%' },
                                { value: 30, label: '+30%' }
                              ]}
                              valueLabelDisplay="auto"
                              valueLabelFormat={(value) => `${value > 0 ? '+' : ''}${value}%`}
                            />
                          </Box>
                        </Box>
                        {/* Meal Scenario */}
                        <Box sx={{ mb: 3 }}>
                          <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold', color: 'warning.main' }}>
                            🍽️ Σενάριο Γεύματος
                          </Typography>
                          <Grid container spacing={2}>
                            <Grid item xs={6}>
                              <TextField
                                label="Υδατάνθρακες (g)"
                                type="number"
                                value={scenarioParams.meal_carbs}
                                onChange={(e) => handleParamChange('meal_carbs', parseFloat(e.target.value) || 0)}
                                variant="outlined"
                                size="small"
                                fullWidth
                                inputProps={{ min: 0, max: 150, step: 5 }}
                              />
                            </Grid>
                            <Grid item xs={6}>
                              <TextField
                                label="Χρόνος γεύματος (min)"
                                type="number"
                                value={scenarioParams.meal_timing}
                                onChange={(e) => handleParamChange('meal_timing', parseInt(e.target.value) || 60)}
                                variant="outlined"
                                size="small"
                                fullWidth
                                inputProps={{ min: 0, max: 360, step: 15 }}
                              />
                            </Grid>
                          </Grid>
                        </Box>
                        {/* Exercise Scenario */}
                        <Box sx={{ mb: 3 }}>
                          <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold', color: 'success.main' }}>
                            🏃‍♂️ Σενάριο Άσκησης
                          </Typography>
                          <Box sx={{ mb: 2 }}>
                            <FormLabel component="legend" sx={{ mb: 1 }}>
                              Ένταση Άσκησης: {scenarioParams.exercise_intensity}%
                            </FormLabel>
                            <Slider
                              value={scenarioParams.exercise_intensity}
                              onChange={(e, value) => handleParamChange('exercise_intensity', value)}
                              min={0}
                              max={100}
                              step={10}
                              marks={[
                                { value: 0, label: 'Όχι' },
                                { value: 30, label: 'Ήπια' },
                                { value: 60, label: 'Μέτρια' },
                                { value: 90, label: 'Έντονη' }
                              ]}
                              valueLabelDisplay="auto"
                              valueLabelFormat={(value) => `${value}%`}
                            />
                          </Box>
                          <TextField
                            label="Διάρκεια Άσκησης (λεπτά)"
                            type="number"
                            value={scenarioParams.exercise_duration}
                            onChange={(e) => handleParamChange('exercise_duration', parseInt(e.target.value) || 0)}
                            variant="outlined"
                            size="small"
                            fullWidth
                            inputProps={{ min: 0, max: 180, step: 15 }}
                            disabled={scenarioParams.exercise_intensity === 0}
                          />
                        </Box>
                        {/* Simulation Settings */}
                        <Box sx={{ mb: 3 }}>
                          <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold' }}>
                            ⏱️ Ρυθμίσεις Προσομοίωσης
                          </Typography>
                          <FormControl fullWidth>
                            <FormLabel component="legend" sx={{ mb: 1 }}>
                              Διάρκεια Προσομοίωσης: {scenarioParams.simulation_hours} ώρες
                            </FormLabel>
                            <Slider
                              value={scenarioParams.simulation_hours}
                              onChange={(e, value) => handleParamChange('simulation_hours', value)}
                              min={6}
                              max={48}
                              step={6}
                              marks={[
                                { value: 6, label: '6h' },
                                { value: 12, label: '12h' },
                                { value: 24, label: '24h' },
                                { value: 48, label: '48h' }
                              ]}
                              valueLabelDisplay="auto"
                              valueLabelFormat={(value) => `${value}h`}
                            />
                          </FormControl>
                        </Box>
                        {/* Run Simulation Button */}
                        <Box sx={{ textAlign: 'center', mt: 3 }}>
                          <Button
                            variant="contained"
                            size="large"
                            onClick={handleRunScenario}
                            disabled={whatIfLoading}
                            startIcon={whatIfLoading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                            sx={{
                              px: 4,
                              py: 1.5,
                              borderRadius: 3,
                              background: 'linear-gradient(45deg, #2196f3 30%, #21cbf3 90%)',
                              '&:hover': {
                                background: 'linear-gradient(45deg, #1976d2 30%, #1e88e5 90%)',
                              }
                            }}
                          >
                            {whatIfLoading ? 'Γίνεται Προσομοίωση...' : 'Εκτέλεση Σεναρίου'}
                          </Button>
                        </Box>
                      </Paper>
                    </Grid>
                    {/* Right Panel - Results */}
                    <Grid item xs={12} md={6}>
                      {scenarioResults ? (
                        <Box>
                          {/* Safety Status */}
                          <Paper elevation={2} sx={{ p: 2, mb: 2, borderRadius: 2 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                              {scenarioResults.ai_validation?.safety_assessment === 'SAFE' ? (
                                <CheckCircleIcon sx={{ color: 'success.main', mr: 1 }} />
                              ) : (
                                <WarningIcon sx={{ color: 'warning.main', mr: 1 }} />
                              )}
                              <Typography variant="h6">
                                Αξιολόγηση Ασφάλειας: {scenarioResults.ai_validation?.safety_assessment || 'UNKNOWN'}
                              </Typography>
                            </Box>
                            <Chip
                              label={`Επίπεδο Κινδύνου: ${scenarioResults.ai_validation?.risk_level || 'UNKNOWN'}`}
                              color={
                                scenarioResults.ai_validation?.risk_level === 'LOW' ? 'success' :
                                scenarioResults.ai_validation?.risk_level === 'MODERATE' ? 'warning' : 'error'
                              }
                              sx={{ mr: 1 }}
                            />
                          </Paper>
                          {/* Glucose Simulation Chart */}
                          <Paper elevation={2} sx={{ p: 3, mb: 2, borderRadius: 2 }}>
                            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                              <ShowChartIcon sx={{ mr: 1 }} />
                              Προβλεπόμενη Γλυκόζη (24ωρο)
                            </Typography>
                            <ResponsiveContainer width="100%" height={300}>
                              <LineChart data={formatSimulationData()}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis 
                                  dataKey="hour" 
                                  label={{ value: 'Ώρες', position: 'insideBottom', offset: -5 }}
                                />
                                <YAxis 
                                  domain={[50, 300]}
                                  label={{ value: 'Γλυκόζη (mg/dL)', angle: -90, position: 'insideLeft' }}
                                />
                                <RechartsTooltip 
                                  formatter={(value, name) => [
                                    `${value} mg/dL`, 
                                    name === 'glucose' ? 'Γλυκόζη' : 'Ινσουλίνη'
                                  ]}
                                  labelFormatter={(hour) => `Ώρα: ${hour}`}
                                />
                                <Legend />
                                {/* Target Range Bands */}
                                <defs>
                                  <pattern id="targetRange" patternUnits="userSpaceOnUse" width="4" height="4">
                                    <rect width="4" height="4" fill="#e8f5e9"/>
                                    <path d="M 0,4 l 4,-4 M -1,1 l 2,-2 M 3,5 l 2,-2" stroke="#4caf50" strokeWidth="0.5"/>
                                  </pattern>
                                </defs>
                                <Line 
                                  dataKey="glucose" 
                                  stroke="#2196f3" 
                                  strokeWidth={3}
                                  name="Προβλεπόμενη Γλυκόζη"
                                  dot={{ fill: '#2196f3', strokeWidth: 2, r: 4 }}
                                />
                                {/* Target Range Lines */}
                                <Line dataKey="target_low" stroke="#4caf50" strokeDasharray="5 5" strokeWidth={1} name="Στόχος (70 mg/dL)" />
                                <Line dataKey="target_high" stroke="#4caf50" strokeDasharray="5 5" strokeWidth={1} name="Στόχος (180 mg/dL)" />
                              </LineChart>
                            </ResponsiveContainer>
                          </Paper>
                          {/* Mindmap Visualization */}
                          <Paper elevation={2} sx={{ p: 3, mb: 2, borderRadius: 2 }}>
                            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                              <MindmapIcon sx={{ mr: 1 }} />
                              Mindmap Αποτελεσμάτων
                            </Typography>
                            <Box sx={{ height: 400, border: '1px solid #e0e0e0', borderRadius: 1 }}>
                              <MindmapVisualization data={scenarioResults.mindmap_data} />
                            </Box>
                          </Paper>
                          {/* Key Metrics */}
                          <Paper elevation={2} sx={{ p: 3, mb: 2, borderRadius: 2 }}>
                            <Typography variant="h6" gutterBottom>
                              📊 Κλειδικές Μετρικές
                            </Typography>
                            <Grid container spacing={2}>
                              <Grid item xs={6}>
                                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'primary.light', borderRadius: 1 }}>
                                  <Typography variant="h4" color="white">
                                    {scenarioResults.simulation?.glucose_metrics?.tir_70_180?.toFixed(1) || '0'}%
                                  </Typography>
                                  <Typography variant="body2" color="white">
                                    Time in Range
                                  </Typography>
                                </Box>
                              </Grid>
                              <Grid item xs={6}>
                                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'success.light', borderRadius: 1 }}>
                                  <Typography variant="h4" color="white">
                                    {scenarioResults.simulation?.glucose_metrics?.mean_glucose?.toFixed(0) || '0'}
                                  </Typography>
                                  <Typography variant="body2" color="white">
                                    Μέση Γλυκόζη (mg/dL)
                                  </Typography>
                                </Box>
                              </Grid>
                              <Grid item xs={6}>
                                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'warning.light', borderRadius: 1 }}>
                                  <Typography variant="h4" color="white">
                                    {scenarioResults.simulation?.glucose_metrics?.glucose_cv?.toFixed(1) || '0'}%
                                  </Typography>
                                  <Typography variant="body2" color="white">
                                    Μεταβλητότητα
                                  </Typography>
                                </Box>
                              </Grid>
                              <Grid item xs={6}>
                                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'error.light', borderRadius: 1 }}>
                                  <Typography variant="h4" color="white">
                                    {scenarioResults.simulation?.risk_scores?.overall_risk?.toFixed(0) || '0'}%
                                  </Typography>
                                  <Typography variant="body2" color="white">
                                    Συνολικός Κίνδυνος
                                  </Typography>
                                </Box>
                              </Grid>
                            </Grid>
                          </Paper>
                          {/* Before/After Comparison */}
                          {scenarioResults.comparison_data && (
                            <Paper elevation={2} sx={{ p: 3, mb: 2, borderRadius: 2 }}>
                              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                                <CompareIcon sx={{ mr: 1 }} />
                                Σύγκριση Πριν/Μετά
                              </Typography>
                              <ResponsiveContainer width="100%" height={250}>
                                <BarChart data={formatComparisonData()}>
                                  <CartesianGrid strokeDasharray="3 3" />
                                  <XAxis dataKey="metric" />
                                  <YAxis />
                                  <RechartsTooltip />
                                  <Legend />
                                  <Bar dataKey="baseline" name="Τρέχουσα Κατάσταση" fill="#ff9800" />
                                  <Bar dataKey="scenario" name="Με Σενάριο" fill="#2196f3" />
                                </BarChart>
                              </ResponsiveContainer>
                            </Paper>
                          )}
                          {/* Recommendations */}
                          {scenarioResults.simulation?.recommendations && scenarioResults.simulation.recommendations.length > 0 && (
                            <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
                              <Typography variant="h6" gutterBottom>
                                💡 AI Συστάσεις
                              </Typography>
                              {scenarioResults.simulation.recommendations.map((rec, index) => (
                                <Alert key={index} severity="info" sx={{ mb: 1 }}>
                                  {rec}
                                </Alert>
                              ))}
                            </Paper>
                          )}
                        </Box>
                      ) : (
                        <Paper elevation={2} sx={{ p: 4, textAlign: 'center', borderRadius: 2, height: 'fit-content' }}>
                          <TrendingUpIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                          <Typography variant="h6" color="text.secondary" gutterBottom>
                            Προσομοίωση Digital Twin
                          </Typography>
                          <Typography variant="body2" color="text.secondary" paragraph>
                            Προσαρμόστε τις παραμέτρους αριστερά και εκτελέστε το σενάριο
                            για να δείτε τα προβλεπόμενα αποτελέσματα.
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            💡 Δοκιμάστε τα προκαθορισμένα σενάρια για γρήγορη αρχή
                          </Typography>
                        </Paper>
                      )}
                    </Grid>
                  </Grid>
                </Box>
              )}

              {analysisData?.analysis && !loading && (
                <Box display="flex" justifyContent="flex-end" mt={2}>
                  <Button
                    size="small"
                    onClick={() => setAnalysisData({ analysis: '', recommendations: [], riskAssessment: {} })}
                    color="primary"
                  >
                    Νέα Ανάλυση
                  </Button>
                </Box>
              )}

          </Paper>
      </Box>
  );
};

export default PatientAIAnalysis;