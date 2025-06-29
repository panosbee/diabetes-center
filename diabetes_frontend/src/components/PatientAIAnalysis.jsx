import React, { useState, useEffect, useCallback } from 'react';
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
  Autocomplete,
  Badge,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  Rating,
  Stack
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
  AccountTree, // <--- ADD THIS LINE
  Security as SecurityIcon,
  Speed as SpeedIcon,
  Insights as InsightsIcon,
  Lightbulb as LightbulbIcon,
  Star as StarIcon,
  Biotech as BiotechIcon,
  AutoFixHigh as AutoFixHighIcon,
  Refresh as RefreshIcon,
  Save as SaveIcon,
  Share as ShareIcon,
  Download as DownloadIcon,
  Science as ScienceIcon,
  Verified as VerifiedIcon
} from '@mui/icons-material';
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
  Cell,
  ScatterChart,
  Scatter,
  Area,
  AreaChart,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from 'recharts';

/**
 * ΒΕΛΤΙΩΜΕΝΟ Component για την ανάλυση με Enhanced Digital Twin Engine - FIXED VERSION
 */
const PatientAIAnalysis = () => {
  const record = useRecordContext();
  const notify = useNotify();
  
  // Analysis state
  const [loading, setLoading] = useState(false);
  const [analysisData, setAnalysisData] = useState(null);
  
  // Enhanced What-If state
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
  
  // Enhanced UI state
  const [tabValue, setTabValue] = useState(0);
  const [validationWarnings, setValidationWarnings] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [presets, setPresets] = useState([]);
  const [realTimeValidation, setRealTimeValidation] = useState(true);
  const [advancedMode, setAdvancedMode] = useState(false);
  const [simulationProgress, setSimulationProgress] = useState(0);
  const [scenarioHistory, setScenarioHistory] = useState([]);

  // FIXED: Error boundary state
  const [hasError, setHasError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // FIXED: Safe data access helpers
  const safeGet = (obj, path, defaultValue = null) => {
    try {
      return path.split('.').reduce((current, key) => {
        return current && current[key] !== undefined ? current[key] : defaultValue;
      }, obj);
    } catch {
      return defaultValue;
    }
  };

  const safeNumber = (value, defaultValue = 0) => {
    const num = parseFloat(value);
    return isNaN(num) ? defaultValue : num;
  };

  const safeArray = (value, defaultValue = []) => {
    return Array.isArray(value) ? value : defaultValue;
  };

  // Load enhanced presets on component mount
  useEffect(() => {
    try {
      loadEnhancedPresets();
    } catch (error) {
      console.error('Error in component mount:', error);
      setHasError(true);
      setErrorMessage(error.message);
    }
  }, []);

  const loadEnhancedPresets = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/scenarios/presets`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        const presetArray = Object.entries(safeGet(data, 'presets', {})).map(([key, preset]) => ({
          id: key,
          ...preset
        }));
        setPresets(presetArray);
      }
    } catch (error) {
      console.error('Error loading enhanced presets:', error);
    }
  };

  // Enhanced parameter change handler με real-time validation
  const handleParamChange = useCallback(async (param, value) => {
    try {
      const newParams = { ...scenarioParams, [param]: value };
      setScenarioParams(newParams);
      
      if (realTimeValidation && record?.id) {
        try {
          const token = localStorage.getItem('access_token');
          if (!token) return;
          
          const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/scenarios/validate`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
              patient_id: record.id,
              scenario_params: newParams
            }),
          });
          
          if (response.ok) {
            const validation = await response.json();
            setValidationWarnings(safeArray(validation.warnings));
          }
        } catch (error) {
          console.error('Validation error:', error);
        }
      }
    } catch (error) {
      console.error('Parameter change error:', error);
    }
  }, [scenarioParams, realTimeValidation, record?.id]);

  // Enhanced scenario execution με detailed progress
  const handleRunEnhancedScenario = async () => {
    try {
      if (!record || !record.id) {
        notify('Δεν βρέθηκε αναγνωριστικό ασθενή', { type: 'error' });
        return;
      }

      setWhatIfLoading(true);
      setSimulationProgress(0);
      setHasError(false);
      
      // Enhanced progress simulation
      const progressInterval = setInterval(() => {
        setSimulationProgress(prev => {
          if (prev < 20) return prev + 2;
          if (prev < 50) return prev + 3;
          if (prev < 80) return prev + 2;
          return Math.min(prev + 1, 95);
        });
      }, 300);

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
      
      clearInterval(progressInterval);
      setSimulationProgress(100);
      
      setTimeout(() => setSimulationProgress(0), 1000);
      
      setScenarioResults(resultData);
      
      // Enhanced history tracking - FIXED: Safe data access
      const historyEntry = {
        id: Date.now(),
        timestamp: new Date(),
        params: { ...scenarioParams },
        results: {
          tir: safeNumber(safeGet(resultData, 'simulation_results.glucose_metrics.tir_70_180')),
          cv: safeNumber(safeGet(resultData, 'simulation_results.glucose_metrics.glucose_cv')),
          risk: safeNumber(safeGet(resultData, 'simulation_results.risk_scores.overall_risk')),
          safety: safeGet(resultData, 'ai_validation.safety_assessment', 'UNKNOWN')
        },
        confidence: safeNumber(safeGet(resultData, 'advanced_analytics.model_confidence'))
      };
      setScenarioHistory(prev => [historyEntry, ...prev.slice(0, 4)]);
      
      notify('🚀 Enhanced Digital Twin simulation completed successfully!', { type: 'success' });
      
    } catch (error) {
      console.error('Enhanced simulation error:', error);
      setHasError(true);
      setErrorMessage(error.message);
      notify(`Σφάλμα στην προηγμένη προσομοίωση: ${error.message}`, { type: 'error' });
    } finally {
      setWhatIfLoading(false);
    }
  };

  // Enhanced analysis handler
  const handleAnalyzeData = async () => {
    try {
      if (!record?.id) {
        notify('Δεν βρέθηκε αναγνωριστικό ασθενή', { type: 'error' });
        return;
      }

      setLoading(true);
      setHasError(false);

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
        recommendations: safeArray(resultData.recommendations),
        riskAssessment: safeGet(resultData, 'risk_assessment', {})
      });
    } catch (error) {
      console.error('Error analyzing patient data:', error);
      setHasError(true);
      setErrorMessage(error.message);
      notify(`Σφάλμα κατά την ανάλυση: ${error.message}`, { type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  // FIXED: Enhanced formatting functions με safe data access
  const formatEnhancedSimulationData = useCallback(() => {
    try {
      const timePoints = safeArray(safeGet(scenarioResults, 'simulation.time_points'));
      const glucoseLevels = safeArray(safeGet(scenarioResults, 'simulation.glucose_levels'));
      const insulinLevels = safeArray(safeGet(scenarioResults, 'simulation.insulin_levels'));
      
      if (!timePoints.length || !glucoseLevels.length) return [];
      
      return timePoints.map((hour, index) => ({
        hour: safeNumber(hour).toFixed(1),
        glucose: Math.round(safeNumber(glucoseLevels[index]) * 10) / 10,
        target_low: 70,
        target_high: 180,
        target_ideal_low: 80,
        target_ideal_high: 140,
        insulin: insulinLevels[index] ? Math.round(safeNumber(insulinLevels[index]) * 100) / 100 : 0
      }));
    } catch (error) {
      console.error('Error formatting simulation data:', error);
      return [];
    }
  }, [scenarioResults]);

  const formatHighResSimulationData = useCallback(() => {
    try {
      const timePoints = safeArray(safeGet(scenarioResults, 'simulation.high_res_time_points'));
      const glucoseLevels = safeArray(safeGet(scenarioResults, 'simulation.high_res_glucose_levels'));

      if (!timePoints.length || !glucoseLevels.length) return [];

      return timePoints.map((hour, index) => ({
        hour: safeNumber(hour).toFixed(2),
        glucose: Math.round(safeNumber(glucoseLevels[index]) * 10) / 10,
      }));
    } catch (error) {
      console.error('Error formatting high-res simulation data:', error);
      return [];
    }
  }, [scenarioResults]);

  const formatHighResInsulinData = useCallback(() => {
    try {
      const timePoints = safeArray(safeGet(scenarioResults, 'simulation.high_res_time_points'));
      const insulinLevels = safeArray(safeGet(scenarioResults, 'simulation.high_res_insulin_levels'));

      if (!timePoints.length || !insulinLevels.length) return [];

      return timePoints.map((hour, index) => ({
        hour: safeNumber(hour).toFixed(2),
        insulin: Math.round(safeNumber(insulinLevels[index]) * 100) / 100,
      }));
    } catch (error) {
      console.error('Error formatting high-res insulin data:', error);
      return [];
    }
  }, [scenarioResults]);

  const formatAdvancedMetricsData = () => {
    try {
      const metrics = safeGet(scenarioResults, 'simulation_results.glucose_metrics', {});
      
      return [
        {
          name: 'TIR 70-180',
          value: Math.round(safeNumber(metrics.tir_70_180) * 10) / 10,
          target: 70,
          optimal: 85,
          unit: '%',
          status: safeNumber(metrics.tir_70_180) >= 85 ? 'excellent' : safeNumber(metrics.tir_70_180) >= 70 ? 'good' : 'needs_improvement'
        },
        {
          name: 'TIR 70-140',
          value: Math.round(safeNumber(metrics.tir_70_140) * 10) / 10,
          target: 50,
          optimal: 70,
          unit: '%',
          status: safeNumber(metrics.tir_70_140) >= 70 ? 'excellent' : safeNumber(metrics.tir_70_140) >= 50 ? 'good' : 'needs_improvement'
        },
        {
          name: 'Time <70',
          value: Math.round(safeNumber(metrics.time_below_70) * 10) / 10,
          target: 4,
          optimal: 1,
          unit: '%',
          status: safeNumber(metrics.time_below_70) <= 1 ? 'excellent' : safeNumber(metrics.time_below_70) <= 4 ? 'good' : 'concerning'
        },
        {
          name: 'Time <54',
          value: Math.round(safeNumber(metrics.time_below_54) * 10) / 10,
          target: 1,
          optimal: 0.5,
          unit: '%',
          status: safeNumber(metrics.time_below_54) <= 0.5 ? 'excellent' : safeNumber(metrics.time_below_54) <= 1 ? 'good' : 'concerning'
        },
        {
          name: 'Time >180',
          value: Math.round(safeNumber(metrics.time_above_180) * 10) / 10,
          target: 25,
          optimal: 15,
          unit: '%',
          status: safeNumber(metrics.time_above_180) <= 15 ? 'excellent' : safeNumber(metrics.time_above_180) <= 25 ? 'good' : 'needs_improvement'
        },
        {
          name: 'Glucose CV',
          value: Math.round(safeNumber(metrics.glucose_cv) * 10) / 10,
          target: 36,
          optimal: 25,
          unit: '%',
          status: safeNumber(metrics.glucose_cv) <= 25 ? 'excellent' : safeNumber(metrics.glucose_cv) <= 36 ? 'good' : 'needs_improvement'
        }
      ];
    } catch (error) {
      console.error('Error formatting advanced metrics:', error);
      return [];
    }
  };

  const formatRiskRadarData = () => {
    try {
      const risks = safeGet(scenarioResults, 'simulation.risk_scores', {});

      return [
        { risk: 'Hypo Risk', value: Math.round(safeNumber(risks.hypoglycemia_risk)), fullMark: 100 },
        { risk: 'Severe Hypo', value: Math.round(safeNumber(risks.severe_hypoglycemia_risk)), fullMark: 100 },
        { risk: 'Hyper Risk', value: Math.round(safeNumber(risks.hyperglycemia_risk)), fullMark: 100 },
        { risk: 'Variability', value: Math.round(safeNumber(risks.variability_risk)), fullMark: 100 },
        { risk: 'Overall Risk', value: Math.round(safeNumber(risks.overall_risk)), fullMark: 100 }
      ];
    } catch (error) {
      console.error('Error formatting risk radar data:', error);
      return [];
    }
  };

  // FIXED: format comparison πριν το return του component
const formatEnhancedComparisonData = useCallback(() => {
  try {
    const comp = safeGet(scenarioResults, 'comparison_data', {});

    /* map κλειδιών → label & μονάδες */
    const metrics = [
      { key: 'tir_70_180',   label: 'TIR 70-180',  unit: '%'      },
      { key: 'tir_70_140',   label: 'TIR 70-140',  unit: '%'      },
      { key: 'glucose_cv',   label: 'Glucose CV',  unit: '%'      },
      { key: 'mean_glucose', label: 'Mean Glucose',unit: 'mg/dL'  },
      { key: 'overall_risk', label: 'Overall Risk',unit: '%'      },
    ];

    return metrics.map(m => {
      const baseline = safeNumber(safeGet(comp, `baseline.${m.key}`));
      const scenario = safeNumber(safeGet(comp, `scenario.${m.key}`));
      return {
        metric: m.label,
        baseline,
        scenario,
        improvement: scenario - baseline, // + θετικό = χειροτερεύει; άλλαξε αν θες το πρόσημο
        unit: m.unit,
      };
    });
  } catch (err) {
    console.error('Error formatting comparison data', err);
    return [];
  }
}, [scenarioResults]);

  // FIXED: Enhanced Mindmap Component με safe rendering
  const EnhancedMindmapVisualization = ({ data }) => {
    const svgRef = React.useRef();
    
    React.useEffect(() => {
      try {
        if (!data || !svgRef.current) return;
        
        const svg = svgRef.current;
        const width = 600;
        const height = 450;
        svg.innerHTML = '';
        
        const createEnhancedNode = (node, x, y, level = 0) => {
          if (!node || !node.label) return; // FIXED: Safe node check
          
          const radius = level === 0 ? 55 : level === 1 ? 40 : 28;
          const colors = {
            root: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            category: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', 
            parameter: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
            outcome: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
            risk: 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)',
            recommendation: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)'
          };
          
          // Create enhanced circle with SVG gradient
          const defs = svg.querySelector('defs') || document.createElementNS('http://www.w3.org/2000/svg', 'defs');
          if (!svg.querySelector('defs')) svg.appendChild(defs);
          
          const gradientId = `gradient-${node.id}-${level}`;
          const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'radialGradient');
          gradient.setAttribute('id', gradientId);
          
          const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
          stop1.setAttribute('offset', '0%');
          stop1.setAttribute('stop-color', colors[node.type]?.split(' ')[2] || '#4facfe');
          
          const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
          stop2.setAttribute('offset', '100%');
          stop2.setAttribute('stop-color', colors[node.type]?.split(' ')[5] || '#00f2fe');
          
          gradient.appendChild(stop1);
          gradient.appendChild(stop2);
          defs.appendChild(gradient);
          
          // Enhanced circle με shadow
          const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
          circle.setAttribute('cx', x);
          circle.setAttribute('cy', y);
          circle.setAttribute('r', radius);
          circle.setAttribute('fill', `url(#${gradientId})`);
          circle.setAttribute('stroke', 'rgba(255,255,255,0.8)');
          circle.setAttribute('stroke-width', '3');
          circle.setAttribute('filter', 'drop-shadow(3px 3px 6px rgba(0,0,0,0.3))');
          circle.setAttribute('opacity', '0.95');
          svg.appendChild(circle);
          
          // Enhanced text με καλύτερη τυπογραφία
          const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          text.setAttribute('x', x);
          text.setAttribute('y', y);
          text.setAttribute('text-anchor', 'middle');
          text.setAttribute('dominant-baseline', 'middle');
          text.setAttribute('fill', 'white');
          text.setAttribute('font-size', level === 0 ? '14' : level === 1 ? '11' : '9');
          text.setAttribute('font-weight', 'bold');
          text.setAttribute('font-family', 'Roboto, Arial, sans-serif');
          text.setAttribute('text-shadow', '1px 1px 2px rgba(0,0,0,0.5)');
          
          const maxLength = level === 0 ? 25 : level === 1 ? 18 : 14;
          let displayText = String(node.label || ''); // FIXED: Safe string conversion
          if (displayText.length > maxLength) {
            displayText = displayText.substring(0, maxLength - 3) + '...';
          }
          text.textContent = displayText;
          svg.appendChild(text);
          
          // Value display για outcomes και metrics - FIXED: Safe value access
          const nodeValue = safeGet(node, 'data.value');
          if (nodeValue !== null && nodeValue !== undefined && level > 0) {
            const valueText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            valueText.setAttribute('x', x);
            valueText.setAttribute('y', y + 12);
            valueText.setAttribute('text-anchor', 'middle');
            valueText.setAttribute('fill', 'rgba(255,255,255,0.9)');
            valueText.setAttribute('font-size', '8');
            valueText.setAttribute('font-weight', 'normal');
            valueText.textContent = typeof nodeValue === 'number' ? 
              `${nodeValue.toFixed(1)}${safeGet(node, 'data.unit', '')}` : String(nodeValue);
            svg.appendChild(valueText);
          }
          
          // Enhanced children rendering με καλύτερες γραμμές - FIXED: Safe children access
          const children = safeArray(node.children);
          if (children.length > 0) {
            const angleStep = (2 * Math.PI) / children.length;
            const distance = level === 0 ? 160 : level === 1 ? 120 : 80;
            
            children.forEach((child, index) => {
              if (!child) return; // FIXED: Safe child check
              
              const angle = index * angleStep - Math.PI / 2; // Start from top
              const childX = x + distance * Math.cos(angle);
              const childY = y + distance * Math.sin(angle);
              
              // Enhanced connection line με gradient
              const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
              line.setAttribute('x1', x + radius * Math.cos(angle));
              line.setAttribute('y1', y + radius * Math.sin(angle));
              line.setAttribute('x2', childX - (level === 1 ? 40 : 28) * Math.cos(angle));
              line.setAttribute('y2', childY - (level === 1 ? 40 : 28) * Math.sin(angle));
              line.setAttribute('stroke', 'rgba(255,255,255,0.6)');
              line.setAttribute('stroke-width', level === 0 ? '3' : level === 1 ? '2' : '1');
              line.setAttribute('stroke-dasharray', level > 0 ? '5,3' : 'none');
              line.setAttribute('opacity', '0.8');
              svg.appendChild(line);
              
              createEnhancedNode(child, childX, childY, level + 1);
            });
          }
        };
        
        createEnhancedNode(data, width / 2, height / 2);
      } catch (error) {
        console.error('Error creating mindmap:', error);
      }
    }, [data]);
    
    return (
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox="0 0 600 450"
        style={{ 
          background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
          borderRadius: '8px'
        }}
      />
    );
  };

  // FIXED: Enhanced Safety Status Component με safe data access
  const EnhancedSafetyStatusCard = ({ validation = {}, simulation = {} }) => {
    const safetyLevel = safeGet(validation, 'safety_assessment', 'UNKNOWN');
    const riskLevel = safeGet(validation, 'risk_level', 'UNKNOWN');
    const overallRisk = safeNumber(safeGet(simulation, 'risk_scores.overall_risk'));
    const confidence = safeGet(validation, 'confidence_level', 'MEDIUM');
    
    const getSafetyColor = (level) => {
      switch(level) {
        case 'SAFE': return { color: 'success', bg: '#e8f5e9' };
        case 'CAUTION': return { color: 'warning', bg: '#fff3e0' };
        case 'UNSAFE': return { color: 'error', bg: '#ffebee' };
        default: return { color: 'info', bg: '#e3f2fd' };
      }
    };
    
    const getRiskColor = (level) => {
      switch(level) {
        case 'LOW': return 'success';
        case 'MODERATE': return 'warning'; 
        case 'HIGH': return 'error';
        default: return 'info';
      }
    };
    
    const safetyConfig = getSafetyColor(safetyLevel);
    
    return (
      <Paper 
        elevation={4} 
        sx={{ 
          p: 3, 
          borderRadius: 3, 
          background: `linear-gradient(135deg, ${safetyConfig.bg} 0%, rgba(255,255,255,0.8) 100%)`,
          border: `2px solid ${safetyConfig.color === 'success' ? '#4caf50' : safetyConfig.color === 'warning' ? '#ff9800' : '#f44336'}`
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <SecurityIcon sx={{ mr: 1, fontSize: 32, color: 'primary.main' }} />
          <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
            Enhanced Safety Assessment
          </Typography>
          <Chip 
            label={confidence} 
            size="small" 
            color="primary" 
            sx={{ ml: 'auto' }}
          />
        </Box>
        
        <Grid container spacing={3}>
          <Grid item xs={4}>
            <Box sx={{ textAlign: 'center' }}>
              <Chip
                label={safetyLevel}
                color={safetyConfig.color}
                size="large"
                sx={{ fontWeight: 'bold', mb: 1, minWidth: '80px' }}
              />
              <Typography variant="caption" display="block" sx={{ fontWeight: 'bold' }}>
                Safety Level
              </Typography>
            </Box>
          </Grid>
          
          <Grid item xs={4}>
            <Box sx={{ textAlign: 'center' }}>
              <Chip
                label={riskLevel}
                color={getRiskColor(riskLevel)}
                size="large"
                sx={{ fontWeight: 'bold', mb: 1, minWidth: '80px' }}
              />
              <Typography variant="caption" display="block" sx={{ fontWeight: 'bold' }}>
                Risk Level
              </Typography>
            </Box>
          </Grid>
          
          <Grid item xs={4}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" sx={{ 
                fontWeight: 'bold', 
                mb: 1,
                color: overallRisk > 50 ? 'error.main' : overallRisk > 25 ? 'warning.main' : 'success.main'
              }}>
                {overallRisk.toFixed(0)}%
              </Typography>
              <Typography variant="caption" display="block" sx={{ fontWeight: 'bold' }}>
                Overall Risk
              </Typography>
            </Box>
          </Grid>
        </Grid>
        
        {/* Model Confidence Indicator - FIXED: Safe data access */}
        {safeGet(scenarioResults, 'advanced_analytics.model_confidence') && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" gutterBottom>
              Model Confidence: {safeNumber(safeGet(scenarioResults, 'advanced_analytics.model_confidence'))}%
            </Typography>
            <LinearProgress
              variant="determinate"
              value={safeNumber(safeGet(scenarioResults, 'advanced_analytics.model_confidence'))}
              sx={{ height: 6, borderRadius: 3 }}
            />
          </Box>
        )}
        
        {/* FIXED: Safe warnings access */}
        {safeArray(validation.clinical_warnings).length > 0 && (
          <Alert severity="warning" sx={{ mt: 2, bgcolor: 'rgba(255,255,255,0.8)' }}>
            <AlertTitle>Clinical Warnings</AlertTitle>
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {safeArray(validation.clinical_warnings).slice(0, 3).map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          </Alert>
        )}
      </Paper>
    );
  };

  // Error boundary fallback UI
  if (hasError) {
    return (
      <Box mt={3}>
        <Alert severity="error" sx={{ mb: 2 }}>
          <AlertTitle>Component Error</AlertTitle>
          {errorMessage || 'Παρουσιάστηκε σφάλμα στο component. Παρακαλώ δοκιμάστε ξανά.'}
        </Alert>
        <Button
          variant="contained"
          color="primary"
          onClick={() => {
            setHasError(false);
            setErrorMessage('');
            window.location.reload();
          }}
          sx={{ mt: 2 }}
        >
          Ανανέωση Σελίδας
        </Button>
      </Box>
    );
  }

  if (!record) return null;

  return (
    <Box mt={3}>
      <Paper elevation={4} sx={{ 
        p: 3, 
        mb: 2, 
        borderRadius: 3, 
        overflow: 'hidden', 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white'
      }}>
        <Box display="flex" alignItems="center" mb={2}>
          <ScienceIcon sx={{ mr: 1, fontSize: 36 }} />
          <Typography variant="h4" sx={{ fontWeight: 'bold', flexGrow: 1 }}>
            Enhanced Digital Twin Analysis
          </Typography>
          <Stack direction="row" spacing={1}>
            <Chip 
              icon={<VerifiedIcon />}
              label="ENHANCED" 
              color="warning" 
              size="medium" 
              sx={{ fontWeight: 'bold' }}
            />
            <Chip 
              icon={<BiotechIcon />}
              label="v2.0" 
              color="success" 
              size="medium"
            />
          </Stack>
        </Box>

        <Typography variant="h6" sx={{ opacity: 0.9, mb: 2 }}>
          Προηγμένη ανάλυση με τεχνητή νοημοσύνη και ψηφιακό δίδυμο για ακριβή προσομοίωση 
          διαχείρισης διαβήτη με realistic φαρμακοκινητικά μοντέλα.
        </Typography>

        {/* Enhanced Feature Indicators */}
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={3}>
            <Box sx={{ textAlign: 'center' }}>
              <BiotechIcon sx={{ fontSize: 24, mb: 0.5 }} />
              <Typography variant="caption" display="block">
                6-Compartment Model
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={3}>
            <Box sx={{ textAlign: 'center' }}>
              <TimelineIcon sx={{ fontSize: 24, mb: 0.5 }} />
              <Typography variant="caption" display="block">
                5-Min Resolution
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={3}>
            <Box sx={{ textAlign: 'center' }}>
              <PsychologyIcon sx={{ fontSize: 24, mb: 0.5 }} />
              <Typography variant="caption" display="block">
                AI Validation
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={3}>
            <Box sx={{ textAlign: 'center' }}>
              <SpeedIcon sx={{ fontSize: 24, mb: 0.5 }} />
              <Typography variant="caption" display="block">
                Real-time Analysis
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Enhanced Controls */}
      <Paper elevation={2} sx={{ p: 2, mb: 2, borderRadius: 2 }}>
        <Box sx={{ display: 'flex', gap: 3, alignItems: 'center', flexWrap: 'wrap' }}>
          <FormControlLabel
            control={
              <Switch
                checked={realTimeValidation}
                onChange={(e) => setRealTimeValidation(e.target.checked)}
                color="primary"
              />
            }
            label="Real-time Validation"
          />
          <FormControlLabel
            control={
              <Switch
                checked={advancedMode}
                onChange={(e) => setAdvancedMode(e.target.checked)}
                color="secondary"
              />
            }
            label="Advanced Mode"
          />
          <Button
            startIcon={<RefreshIcon />}
            onClick={loadEnhancedPresets}
            size="small"
            variant="outlined"
          >
            Refresh Presets
          </Button>
          
          {/* Scenario History Quick View - FIXED: Safe history access */}
          {scenarioHistory.length > 0 && (
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Typography variant="caption" color="text.secondary">
                Recent:
              </Typography>
              {scenarioHistory.slice(0, 3).map((entry, index) => (
                <Tooltip 
                  key={entry.id}
                  title={`TIR: ${safeNumber(entry.results?.tir).toFixed(0)}% | Risk: ${safeNumber(entry.results?.risk).toFixed(0)}% | ${entry.results?.safety || 'UNKNOWN'}`}
                >
                  <Chip
                    label={`${safeNumber(entry.results?.tir).toFixed(0)}%`}
                    size="small"
                    color={entry.results?.safety === 'SAFE' ? 'success' : entry.results?.safety === 'CAUTION' ? 'warning' : 'error'}
                    sx={{ fontSize: '10px' }}
                  />
                </Tooltip>
              ))}
            </Box>
          )}
        </Box>
      </Paper>

      <Tabs 
        value={tabValue} 
        onChange={(e, v) => setTabValue(v)} 
        sx={{ mb: 2 }}
        variant="fullWidth"
      >
        <Tab label="AI Analysis" icon={<AssessmentIcon />} />
        <Tab label="Enhanced Digital Twin" icon={<ScienceIcon />} />
        <Tab label="Advanced Metrics" icon={<InsightsIcon />} />
        <Tab label="AI Optimization" icon={<AutoFixHighIcon />} />
      </Tabs>

      {/* Tab 0: AI Analysis */}
      {tabValue === 0 && (
        <Box>
          {analysisData?.analysis ? (
            <Card variant="outlined" sx={{ mb: 2, borderRadius: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <PsychologyIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">AI Analysis Results</Typography>
                </Box>
                {/* formatted AI analysis */}
<Box sx={{ lineHeight: 1.8 }}>
  {analysisData.analysis
    // σπάμε σε μπλοκ με βάση κενές γραμμές
    .split(/\n{2,}/)
    .map((block, idx) => {
      const txt = block.trim();

      // --- Markdown-like τίτλοι ---
      if (txt.startsWith('###')) {
        return (
          <Typography key={idx} variant="subtitle1" sx={{ fontWeight: 'bold', mt: idx ? 2 : 0 }}>
            {txt.replace(/^###\s*/, '')}
          </Typography>
        );
      }
      if (txt.startsWith('##')) {
        return (
          <Typography key={idx} variant="h6" sx={{ fontWeight: 'bold', mt: idx ? 2 : 0 }}>
            {txt.replace(/^##\s*/, '')}
          </Typography>
        );
      }
      if (txt.startsWith('#')) {
        return (
          <Typography key={idx} variant="h5" sx={{ fontWeight: 'bold', mt: idx ? 2 : 0 }}>
            {txt.replace(/^#\s*/, '')}
          </Typography>
        );
      }

      // --- bullets (γραμμές που ξεκινούν με “- ” ή “• ”) ---
      if (txt.startsWith('- ') || txt.startsWith('• ')) {
        return (
          <Box key={idx} component="ul" sx={{ pl: 3, mb: 1 }}>
            {txt
              .split('\n')
              .filter(Boolean)
              .map((li, i) => (
                <Typography component="li" variant="body2" key={i}>
                  {li.replace(/^[-•]\s*/, '')}
                </Typography>
              ))}
          </Box>
        );
      }

      // --- απλή παράγραφος ---
      return (
        <Typography key={idx} variant="body2" paragraph>
          {txt.replace(/\n/g, ' ')}
        </Typography>
      );
    })}
</Box>

              </CardContent>
            </Card>
          ) : (
            <Box textAlign="center" p={6}>
              <PsychologyIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                AI Analysis Ready
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Run comprehensive AI analysis on patient data to get intelligent insights
              </Typography>
              <Button
                variant="contained"
                size="large"
                startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <AnalyticsIcon />}
                onClick={handleAnalyzeData}
                disabled={loading}
                sx={{ 
                  px: 4, 
                  py: 1.5, 
                  borderRadius: 3,
                  background: 'linear-gradient(45deg, #2196f3 30%, #21cbf3 90%)'
                }}
              >
                {loading ? 'Analyzing Patient Data...' : 'Run AI Analysis'}
              </Button>
            </Box>
          )}
        </Box>
      )}

      {/* Tab 1: Enhanced Digital Twin */}
      {tabValue === 1 && (
        <Grid container spacing={3}>
          {/* Left Panel - Enhanced Controls */}
          <Grid item xs={12} md={6}>
            <Paper elevation={3} sx={{ p: 3, borderRadius: 2, height: 'fit-content' }}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                <SettingsIcon sx={{ mr: 1 }} />
                Enhanced Scenario Parameters
              </Typography>

              {/* Progress indicator during simulation */}
              {whatIfLoading && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="body2" gutterBottom sx={{ fontWeight: 'bold' }}>
                    Running Enhanced Digital Twin Simulation...
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={simulationProgress} 
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                    {simulationProgress}% - Processing enhanced physiological models
                  </Typography>
                </Box>
              )}

              {/* Enhanced Preset Selection - FIXED: Safe preset handling */}
              <Box sx={{ mb: 3 }}>
                <FormLabel component="legend" sx={{ mb: 1, fontWeight: 'bold' }}>
                  🎯 Clinical Evidence-Based Presets
                </FormLabel>
                <Autocomplete
                  value={selectedPreset}
                  onChange={(event, newValue) => {
                    setSelectedPreset(newValue);
                    if (newValue && newValue.params) {
                      setScenarioParams(prev => ({
                        ...prev,
                        ...newValue.params
                      }));
                    }
                  }}
                  options={presets}
                  getOptionLabel={(option) => option?.name || ''}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      placeholder="Select evidence-based scenario..."
                      variant="outlined"
                      size="small"
                    />
                  )}
                  renderOption={(props, option) => {
                    const { key, ...otherProps } = props;
                    return (
                      <Box component="li" key={option?.id || key} {...otherProps}>
                        <Box sx={{ width: '100%' }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                            <Typography variant="body2" fontWeight="bold" sx={{ flexGrow: 1 }}>
                              {option?.name || 'Unknown Preset'}
                            </Typography>
                            <Chip 
                              label={safeGet(option, 'safety_profile', 'STANDARD').replace('_', ' ')} 
                              size="small"
                              color={
                                safeGet(option, 'safety_profile') === 'HIGH_SAFETY' ? 'success' :
                                safeGet(option, 'safety_profile') === 'MODERATE_SAFETY' ? 'warning' : 'default'
                              }
                            />
                          </Box>
                          <Typography variant="caption" color="text.secondary" display="block">
                            {option?.description || 'No description available'}
                          </Typography>
                          {option?.clinical_evidence && (
                            <Typography variant="caption" sx={{ 
                              color: 'primary.main', 
                              fontStyle: 'italic',
                              display: 'block',
                              mt: 0.5
                            }}>
                              📚 {option.clinical_evidence}
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    );
                  }}
                />
              </Box>

              {/* Enhanced Parameter Controls */}
              {/* Insulin Parameters */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold', color: 'primary.main' }}>
                  💉 Enhanced Insulin Therapy Adjustments
                </Typography>
                
                {/* Basal Insulin */}
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <FormLabel component="legend" sx={{ flexGrow: 1 }}>
                      Basal Insulin: {scenarioParams.basal_change > 0 ? '+' : ''}{scenarioParams.basal_change}%
                    </FormLabel>
                    {Math.abs(scenarioParams.basal_change) > 30 && (
                      <Chip label="HIGH CHANGE" color="warning" size="small" />
                    )}
                  </Box>
                  <Slider
                    value={scenarioParams.basal_change}
                    onChange={(e, value) => handleParamChange('basal_change', value)}
                    min={-50}
                    max={50}
                    step={5}
                    marks={[
                      { value: -50, label: '-50%' },
                      { value: -25, label: '-25%' },
                      { value: 0, label: '0%' },
                      { value: 25, label: '+25%' },
                      { value: 50, label: '+50%' }
                    ]}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(value) => `${value > 0 ? '+' : ''}${value}%`}
                    color={Math.abs(scenarioParams.basal_change) > 30 ? 'error' : 'primary'}
                    sx={{ 
                      '& .MuiSlider-thumb': {
                        boxShadow: Math.abs(scenarioParams.basal_change) > 30 ? '0 0 10px rgba(244, 67, 54, 0.5)' : 'none'
                      }
                    }}
                  />
                </Box>

                {/* Bolus Insulin */}
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <FormLabel component="legend" sx={{ flexGrow: 1 }}>
                      Bolus Insulin: {scenarioParams.bolus_change > 0 ? '+' : ''}{scenarioParams.bolus_change}%
                    </FormLabel>
                    {Math.abs(scenarioParams.bolus_change) > 30 && (
                      <Chip label="HIGH CHANGE" color="warning" size="small" />
                    )}
                  </Box>
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

                {advancedMode && (
                  <>
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
                        valueLabelDisplay="auto"
                        valueLabelFormat={(value) => `${value > 0 ? '+' : ''}${value}%`}
                      />
                    </Box>

                    <Box sx={{ mb: 2 }}>
                      <FormLabel component="legend" sx={{ mb: 1 }}>
                        Correction Factor: {scenarioParams.correction_factor_change > 0 ? '+' : ''}{scenarioParams.correction_factor_change}%
                      </FormLabel>
                      <Slider
                        value={scenarioParams.correction_factor_change}
                        onChange={(e, value) => handleParamChange('correction_factor_change', value)}
                        min={-30}
                        max={30}
                        step={5}
                        valueLabelDisplay="auto"
                        valueLabelFormat={(value) => `${value > 0 ? '+' : ''}${value}%`}
                      />
                    </Box>
                  </>
                )}
              </Box>

              {/* Meal Scenario */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold', color: 'warning.main' }}>
                  🍽️ Enhanced Meal Scenario
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <TextField
                      label="Carbohydrates (g)"
                      type="number"
                      value={scenarioParams.meal_carbs}
                      onChange={(e) => handleParamChange('meal_carbs', parseFloat(e.target.value) || 0)}
                      variant="outlined"
                      size="small"
                      fullWidth
                      inputProps={{ min: 0, max: 150, step: 5 }}
                      helperText={
                        scenarioParams.meal_carbs > 100 ? "Very large meal - consider split bolus" :
                        scenarioParams.meal_carbs > 80 ? "Large meal - monitor closely" : ""
                      }
                      color={scenarioParams.meal_carbs > 100 ? 'error' : scenarioParams.meal_carbs > 80 ? 'warning' : 'primary'}
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      label="Meal Timing (min)"
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
                  🏃‍♂️ Enhanced Exercise Scenario
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <FormLabel component="legend" sx={{ mb: 1 }}>
                    Exercise Intensity: {scenarioParams.exercise_intensity}%
                  </FormLabel>
                  <Slider
                    value={scenarioParams.exercise_intensity}
                    onChange={(e, value) => handleParamChange('exercise_intensity', value)}
                    min={0}
                    max={100}
                    step={10}
                    marks={[
                      { value: 0, label: 'None' },
                      { value: 30, label: 'Light' },
                      { value: 60, label: 'Moderate' },
                      { value: 90, label: 'Intense' }
                    ]}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(value) => `${value}%`}
                    color={scenarioParams.exercise_intensity > 70 ? 'warning' : 'success'}
                  />
                  {scenarioParams.exercise_intensity > 70 && (
                    <Typography variant="caption" color="warning.main" sx={{ mt: 1, display: 'block' }}>
                      ⚠️ High intensity exercise - consider carb snack and insulin reduction
                    </Typography>
                  )}
                </Box>
                <TextField
                  label="Exercise Duration (minutes)"
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

              {/* Advanced Simulation Settings */}
              {advancedMode && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold' }}>
                    ⚙️ Advanced Simulation Settings
                  </Typography>
                  <FormControl fullWidth>
                    <FormLabel component="legend" sx={{ mb: 1 }}>
                      Simulation Duration: {scenarioParams.simulation_hours} hours
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
              )}

              {/* Validation Warnings */}
              {validationWarnings.length > 0 && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                  <AlertTitle>Real-time Parameter Validation</AlertTitle>
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {validationWarnings.map((warning, index) => (
                      <li key={index}>{warning}</li>
                    ))}
                  </ul>
                </Alert>
              )}

              {/* Enhanced Run Button */}
              <Box sx={{ textAlign: 'center', mt: 4 }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={handleRunEnhancedScenario}
                  disabled={whatIfLoading}
                  startIcon={whatIfLoading ? 
                    <CircularProgress size={24} color="inherit" /> : 
                    <ScienceIcon />
                  }
                  sx={{
                    px: 5,
                    py: 2,
                    borderRadius: 4,
                    background: 'linear-gradient(45deg, #667eea 30%, #764ba2 90%)',
                    boxShadow: '0 4px 15px rgba(102, 126, 234, .4)',
                    fontSize: '1.1rem',
                    fontWeight: 'bold',
                    '&:hover': {
                      background: 'linear-gradient(45deg, #5a6fd8 30%, #6a4190 90%)',
                      boxShadow: '0 6px 20px rgba(102, 126, 234, .6)',
                    },
                    '&:disabled': {
                      background: 'linear-gradient(45deg, #bbb 30%, #999 90%)',
                    }
                  }}
                >
                  {whatIfLoading ? 'Running Enhanced Simulation...' : 'Run Enhanced Digital Twin'}
                </Button>
                <Typography variant="caption" display="block" sx={{ mt: 1, color: 'text.secondary' }}>
                  Enhanced 6-compartment model με 5-minute resolution
                </Typography>
              </Box>
            </Paper>
          </Grid>

          {/* Right Panel - Enhanced Results */}
          <Grid item xs={12} md={6}>
            {scenarioResults ? (
              <Box>
                {/* Enhanced Safety Assessment */}
                <EnhancedSafetyStatusCard 
                  validation={safeGet(scenarioResults, 'ai_validation', {})}
                  simulation={safeGet(scenarioResults, 'simulation', {})}
                />

                {/* Enhanced Glucose Chart */}
                <Paper elevation={3} sx={{ p: 3, mt: 2, borderRadius: 2 }}>
                  <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                    <ShowChartIcon sx={{ mr: 1 }} />
                    Enhanced Glucose Prediction (High Resolution)
                  </Typography>
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={formatEnhancedSimulationData()}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis 
                        dataKey="hour"
                        label={{ value: 'Hours', position: 'insideBottom', offset: -5 }}
                        tick={{ fontSize: 12 }}
                      />
                      <YAxis
  domain={[50, 300]}
  label={{ value: 'Glucose (mg/dL)', angle: -90, position: 'insideLeft' }}
  tick={{ fontSize: 12 }}
/>
{advancedMode && (
  <YAxis
    yAxisId="right"
    orientation="right"
    label={{ value: 'Insulin (mU/L)', angle: 90, position: 'insideRight' }}
    tick={{ fontSize: 12 }}
    domain={[0, 50]}
  />
)}



                      <RechartsTooltip 
                        formatter={(value, name) => [
                          `${typeof value === 'number' ? value.toFixed(1) : value} ${
                            name === 'glucose' ? 'mg/dL' : 
                            name === 'insulin' ? 'mU/L' : ''
                          }`, 
                          name === 'glucose' ? 'Glucose' : 
                          name === 'insulin' ? 'Insulin' : 
                          name.replace('target_', '').replace('_', ' ')
                        ]}
                        labelFormatter={(hour) => `Time: ${hour} hours`}
                        contentStyle={{ 
                          backgroundColor: 'rgba(255,255,255,0.95)', 
                          border: '1px solid #ddd',
                          borderRadius: '8px'
                        }}
                      />
                      <Legend />
                      
                      {/* Target zones με enhanced styling */}
                      <Area 
                        dataKey="target_ideal_high" 
                        fill="rgba(76, 175, 80, 0.1)" 
                        stroke="none"
                        fillOpacity={0.3} 
                      />
                      <Area 
                        dataKey="target_ideal_low" 
                        fill="rgba(255, 255, 255, 1)" 
                        stroke="none"
                      />
                      
                      {/* Main glucose line με enhanced styling */}
                      <Line 
                        dataKey="glucose" 
                        stroke="#1976d2" 
                        strokeWidth={4}
                        name="Predicted Glucose"
                        dot={{ fill: '#1976d2', strokeWidth: 2, r: 4 }}
                        activeDot={{ r: 6, stroke: '#1976d2', strokeWidth: 2 }}
                      />
                      
                      {/* Target lines */}
                      <Line dataKey="target_low" stroke="#4caf50" strokeDasharray="8 4" strokeWidth={2} name="Target Low (70)" dot={false} />
                      <Line dataKey="target_high" stroke="#4caf50" strokeDasharray="8 4" strokeWidth={2} name="Target High (180)" dot={false} />
                      <Line dataKey="target_ideal_low" stroke="#2e7d32" strokeDasharray="4 2" strokeWidth={1} name="Ideal Low (80)" dot={false} />
                      <Line dataKey="target_ideal_high" stroke="#2e7d32" strokeDasharray="4 2" strokeWidth={1} name="Ideal High (140)" dot={false} />
                      
                      {/* Enhanced insulin overlay για advanced mode */}
                      {advancedMode && (
                        <Line 
                          dataKey="insulin" 
                          stroke="#ff9800" 
                          strokeWidth={2}
                          name="Insulin (mU/L)"
                          yAxisId="right"
                          dot={{ fill: '#ff9800', r: 2 }}
                        />
                      )}
                    </LineChart>
                  </ResponsiveContainer>
                  
                  {/* Chart insights - FIXED: Safe data access */}
                  <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      📊 <strong>Chart Insights:</strong> Peak glucose: {formatEnhancedSimulationData().length > 0 ? Math.max(...formatEnhancedSimulationData().map(d => d.glucose)).toFixed(0) : 'N/A'} mg/dL, 
                      Minimum: {formatEnhancedSimulationData().length > 0 ? Math.min(...formatEnhancedSimulationData().map(d => d.glucose)).toFixed(0) : 'N/A'} mg/dL, 
                      Data points: {formatEnhancedSimulationData().length} (5-min resolution)
                    </Typography>
                  </Box>
                </Paper>

                {/* Enhanced Mindmap */}
                <Paper elevation={3} sx={{ p: 3, mt: 2, borderRadius: 2 }}>
                  <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                    <AccountTree sx={{ mr: 1 }} />
                    Enhanced Scenario Mindmap
                  </Typography>
                  <Box sx={{ height: 450, border: '1px solid #e0e0e0', borderRadius: 2 }}>
                    <EnhancedMindmapVisualization data={safeGet(scenarioResults, 'mindmap_data')} />
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    Interactive visualization of scenario parameters, outcomes, and relationships
                  </Typography>
                </Paper>

                {/* Enhanced Key Metrics - FIXED: Safe data access με Rating fix */}
                <Paper elevation={3} sx={{ p: 3, mt: 2, borderRadius: 2 }}>
                  <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                    <InsightsIcon sx={{ mr: 1 }} />
                    Enhanced Clinical Metrics
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'primary.light', borderRadius: 2, color: 'white' }}>
                        <Typography variant="h3" sx={{ fontWeight: 'bold' }}>
                          {safeNumber(safeGet(scenarioResults, 'simulation.glucose_metrics.tir_70_180')).toFixed(1)}%
                        </Typography>
                        <Typography variant="body2">Time in Range</Typography>
                        <Rating 
                          value={Math.min(5, Math.max(0, safeNumber(safeGet(scenarioResults, 'simulation.glucose_metrics.tir_70_180')) / 20))} 
                          precision={0.1} 
                          readOnly 
                          sx={{ mt: 1 }}
                        />
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'success.light', borderRadius: 2, color: 'white' }}>
                        <Typography variant="h3" sx={{ fontWeight: 'bold' }}>
                          {safeNumber(safeGet(scenarioResults, 'simulation.glucose_metrics.mean_glucose')).toFixed(0)}
                        </Typography>
                        <Typography variant="body2">Mean Glucose (mg/dL)</Typography>
                        <Typography variant="caption" sx={{ opacity: 0.9 }}>
                          Target: 80-140 mg/dL
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'warning.light', borderRadius: 2, color: 'white' }}>
                        <Typography variant="h3" sx={{ fontWeight: 'bold' }}>
                          {safeNumber(safeGet(scenarioResults, 'simulation.glucose_metrics.glucose_cv')).toFixed(1)}%
                        </Typography>
                        <Typography variant="body2">Glucose Variability</Typography>
                        <Typography variant="caption" sx={{ opacity: 0.9 }}>
                          Target: &lt;36%
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box sx={{ 
                        textAlign: 'center', 
                        p: 2, 
                        bgcolor: safeNumber(safeGet(scenarioResults, 'simulation.risk_scores.overall_risk')) > 50 ? 'error.light' : 
                                 safeNumber(safeGet(scenarioResults, 'simulation.risk_scores.overall_risk')) > 25 ? 'warning.light' : 'success.light', 
                        borderRadius: 2, 
                        color: 'white' 
                      }}>
                        <Typography variant="h3" sx={{ fontWeight: 'bold' }}>
                          {safeNumber(safeGet(scenarioResults, 'simulation.risk_scores.overall_risk')).toFixed(0)}%
                        </Typography>
                        <Typography variant="body2">Overall Risk Score</Typography>
                        <Typography variant="caption" sx={{ opacity: 0.9 }}>
                          Lower is better
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </Paper>

                {/* Enhanced Before/After Comparison */}
                {safeGet(scenarioResults, 'comparison_data') && (
                  <Paper elevation={3} sx={{ p: 3, mt: 2, borderRadius: 2 }}>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                      <CompareIcon sx={{ mr: 1 }} />
                      Enhanced Before/After Analysis
                    </Typography>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={formatEnhancedComparisonData()}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="metric" tick={{ fontSize: 11 }} />
                        <YAxis />
                        {advancedMode && (
                          <YAxis
  domain={[50, 300]}
  label={{ value: 'Glucose (mg/dL)', angle: -90, position: 'insideLeft' }}
  tick={{ fontSize: 12 }}
/>

                        )}
                        {advancedMode && (
  <YAxis
    yAxisId="right"
    orientation="right"
    label={{ value: 'Insulin (mU/L)', angle: 90, position: 'insideRight' }}
    tick={{ fontSize: 12 }}
    domain={[0, 50]}
  />
)}


                        <RechartsTooltip 
                          formatter={(value, name) => [
                            `${value}${formatEnhancedComparisonData().find(d => d.baseline === value || d.scenario === value)?.unit || ''}`,
                            name === 'baseline' ? 'Current State' : 'With Scenario'
                          ]}
                        />
                        <Legend />
                        <Bar dataKey="baseline" name="Current State" fill="#ff9800" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="scenario" name="With Scenario" fill="#2196f3" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                    
                    {/* Improvement summary */}
                    <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        📈 Improvement Summary:
                      </Typography>
                      {formatEnhancedComparisonData().map((item, index) => (
                        <Typography key={index} variant="caption" display="block">
                          • {item.metric}: {item.improvement > 0 ? '+' : ''}{item.improvement.toFixed(1)}{item.unit}
                          {item.improvement > 0 ? ' 📈' : item.improvement < 0 ? ' 📉' : ' ➡️'}
                        </Typography>
                      ))}
                    </Box>
                  </Paper>
                )}

                {/* Enhanced AI Recommendations - FIXED: Safe recommendations access */}
                {safeArray(safeGet(scenarioResults, 'simulation.recommendations')).length > 0 && (
                  <Paper elevation={3} sx={{ p: 3, mt: 2, borderRadius: 2 }}>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                      <LightbulbIcon sx={{ mr: 1 }} />
                      Enhanced AI Recommendations
                    </Typography>
                    {safeArray(safeGet(scenarioResults, 'simulation.recommendations')).map((rec, index) => (
                      <Alert 
                        key={index} 
                        severity={
                          rec.includes('🚨') || rec.includes('ΚΡΙΤΙΚΟ') ? 'error' :
                          rec.includes('⚠️') || rec.includes('ΠΡΟΣΟΧΗ') ? 'warning' :
                          rec.includes('✅') || rec.includes('ΕΞΑΙΡΕΤΙΚ') ? 'success' : 'info'
                        } 
                        sx={{ mb: 1, borderRadius: 2 }}
                      >
                        {rec}
                      </Alert>
                    ))}
                  </Paper>
                )}
              </Box>
            ) : (
              <Paper elevation={3} sx={{ p: 6, textAlign: 'center', borderRadius: 2, height: 'fit-content' }}>
                <ScienceIcon sx={{ fontSize: 80, color: 'text.secondary', mb: 3 }} />
                <Typography variant="h5" color="text.secondary" gutterBottom sx={{ fontWeight: 'bold' }}>
                  Enhanced Digital Twin Ready
                </Typography>
                <Typography variant="body1" color="text.secondary" paragraph>
                  Configure scenario parameters and run the enhanced simulation
                  to see realistic glucose predictions with 5-minute resolution.
                </Typography>
                <Box sx={{ mt: 3, p: 2, bgcolor: 'primary.light', borderRadius: 2, color: 'white' }}>
                  <Typography variant="subtitle2" gutterBottom>
                    🧬 Enhanced Features:
                  </Typography>
                  <Typography variant="body2">
                    • 6-compartment physiological model<br/>
                    • Stochastic noise for realism<br/>
                    • Circadian rhythm modeling<br/>
                    • Enhanced meal absorption (gamma distribution)<br/>
                    • Real-time safety validation
                  </Typography>
                </Box>
              </Paper>
            )}
          </Grid>
        </Grid>
      )}

      {/* Tab 2: Advanced Metrics */}
      {tabValue === 2 && (
        <Box>
          {scenarioResults ? (
            <Grid container spacing={3}>
              {/* Advanced Metrics Table */}
              <Grid item xs={12} md={6}>
                <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    📊 Advanced Glucose Metrics
                  </Typography>
                  <Box sx={{ mt: 2 }}>
                    {formatAdvancedMetricsData().map((metric, index) => (
                      <Box key={index} sx={{ mb: 2, p: 2, border: '1px solid #e0e0e0', borderRadius: 1 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                            {metric.name}
                          </Typography>
                          <Chip 
                            label={metric.status?.replace('_', ' ').toUpperCase()}
                            color={
                              metric.status === 'excellent' ? 'success' :
                              metric.status === 'good' ? 'primary' :
                              metric.status === 'concerning' ? 'error' : 'warning'
                            }
                            size="small"
                          />
                        </Box>
                        <Typography variant="h6" sx={{ mb: 1 }}>
                          {metric.value}{metric.unit}
                        </Typography>
                        <LinearProgress 
                          variant="determinate" 
                          value={metric.name.includes('<') ? 
                            Math.max(0, 100 - (metric.value / metric.target) * 100) :
                            Math.min(100, (metric.value / metric.optimal) * 100)
                          }
                          color={
                            metric.status === 'excellent' ? 'success' :
                            metric.status === 'good' ? 'primary' : 'warning'
                          }
                          sx={{ height: 6, borderRadius: 3 }}
                        />
                        <Typography variant="caption" color="text.secondary">
                          Target: {metric.name.includes('<') ? '< ' : '> '}{metric.target}{metric.unit}, 
                          Optimal: {metric.name.includes('<') ? '< ' : '> '}{metric.optimal}{metric.unit}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Paper>
              </Grid>

              {/* Risk Radar Chart */}
              <Grid item xs={12} md={6}>
                <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    🎯 Risk Assessment Radar
                  </Typography>
                  <ResponsiveContainer width="100%" height={350}>
                    <RadarChart data={formatRiskRadarData()}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="risk" tick={{ fontSize: 12 }} />
                      <PolarRadiusAxis 
                        domain={[0, 100]} 
                        tick={{ fontSize: 10 }}
                        tickFormatter={(value) => `${value}%`}
                      />
                      <Radar
                        name="Risk Level"
                        dataKey="value"
                        stroke="#ff4444"
                        fill="rgba(255, 68, 68, 0.3)"
                        strokeWidth={2}
                      />
                      <RechartsTooltip 
                        formatter={(value) => [`${value}%`, 'Risk Level']}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>

              {/* Enhanced Patient Factors - FIXED: Safe data access */}
              <Grid item xs={12}>
                <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    👤 Patient-Specific Factors
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={3}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="primary.main">
                          {safeNumber(safeGet(scenarioResults, 'advanced_analytics.patient_factors.insulin_resistance')).toFixed(2)}
                        </Typography>
                        <Typography variant="body2">Insulin Resistance Factor</Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={3}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="success.main">
                          {safeNumber(safeGet(scenarioResults, 'advanced_analytics.patient_factors.exercise_sensitivity')).toFixed(2)}
                        </Typography>
                        <Typography variant="body2">Exercise Sensitivity</Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={3}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="warning.main">
                          {safeNumber(safeGet(scenarioResults, 'advanced_analytics.patient_factors.stress_sensitivity')).toFixed(2)}
                        </Typography>
                        <Typography variant="body2">Stress Sensitivity</Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={3}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="info.main">
                          {safeNumber(safeGet(scenarioResults, 'advanced_analytics.model_confidence'))}%
                        </Typography>
                        <Typography variant="body2">Model Confidence</Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>
            </Grid>
          ) : (
            <Box textAlign="center" p={6}>
              <InsightsIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Advanced Metrics Available After Simulation
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Run an enhanced digital twin simulation to see detailed glucose metrics,
                risk assessment, and patient-specific factors.
              </Typography>
            </Box>
          )}
        </Box>
      )}

      {/* Tab 3: AI Optimization */}
      {tabValue === 3 && (
        <Box>
          {safeGet(scenarioResults, 'optimization') ? (
            <Grid container spacing={3}>
              {/* Optimization Recommendations */}
              <Grid item xs={12} md={8}>
                <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }}>
                  <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                    <AutoFixHighIcon sx={{ mr: 1 }} />
                    AI-Powered Optimization Recommendations
                  </Typography>
                  
                  {/* Priority Actions - FIXED: Safe data access */}
                  {safeArray(safeGet(scenarioResults, 'optimization.priority_actions')).length > 0 && (
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 1 }}>
                        🎯 Priority Actions
                      </Typography>
                      {safeArray(safeGet(scenarioResults, 'optimization.priority_actions')).map((action, index) => (
                        <Alert key={index} severity="info" sx={{ mb: 1 }}>
                          {action}
                        </Alert>
                      ))}
                    </Box>
                  )}

                  {/* Monitoring Recommendations */}
                  {safeArray(safeGet(scenarioResults, 'optimization.monitoring_recommendations')).length > 0 && (
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 1 }}>
                        📋 Monitoring Protocol
                      </Typography>
                      {safeArray(safeGet(scenarioResults, 'optimization.monitoring_recommendations')).map((rec, index) => (
                        <Alert key={index} severity="warning" sx={{ mb: 1 }}>
                          {rec}
                        </Alert>
                      ))}
                    </Box>
                  )}

                  {/* Technology Suggestions */}
                  {safeArray(safeGet(scenarioResults, 'optimization.technology_suggestions')).length > 0 && (
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 1 }}>
                        📱 Technology Recommendations
                      </Typography>
                      {safeArray(safeGet(scenarioResults, 'optimization.technology_suggestions')).map((tech, index) => (
                        <Alert key={index} severity="success" sx={{ mb: 1 }}>
                          {tech}
                        </Alert>
                      ))}
                    </Box>
                  )}

                  {/* Clinical Rationale */}
                  {safeGet(scenarioResults, 'optimization.clinical_rationale') && (
                    <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                        📚 Clinical Rationale
                      </Typography>
                      <Typography variant="body2">
                        {safeGet(scenarioResults, 'optimization.clinical_rationale')}
                      </Typography>
                    </Box>
                  )}
                </Paper>
              </Grid>

              {/* Optimization Summary */}
              <Grid item xs={12} md={4}>
                <Paper elevation={3} sx={{ p: 3, borderRadius: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    📈 Expected Improvements
                  </Typography>
                  
                  {/* Optimization Confidence */}
                  <Box sx={{ mb: 3, textAlign: 'center' }}>
                    <Typography variant="h3" color="primary.main">
                      {safeGet(scenarioResults, 'optimization.confidence', 'MEDIUM')}
                    </Typography>
                    <Typography variant="body2">AI Confidence Level</Typography>
                  </Box>

                  {/* Expected Improvements */}
                  {safeArray(safeGet(scenarioResults, 'optimization.expected_improvements')).length > 0 && (
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                        Predicted Outcomes:
                      </Typography>
                      {safeArray(safeGet(scenarioResults, 'optimization.expected_improvements')).map((improvement, index) => (
                        <Chip
                          key={index}
                          label={improvement}
                          color="success"
                          size="small"
                          sx={{ mr: 1, mb: 1 }}
                        />
                      ))}
                    </Box>
                  )}

                  {/* Follow-up Timeline */}
                  {safeGet(scenarioResults, 'optimization.follow_up_timeline') && (
                    <Box sx={{ p: 2, bgcolor: 'info.light', borderRadius: 1, color: 'white' }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                        📅 Follow-up Schedule
                      </Typography>
                      <Typography variant="body2">
                        {safeGet(scenarioResults, 'optimization.follow_up_timeline')}
                      </Typography>
                    </Box>
                  )}
                </Paper>
              </Grid>
            </Grid>
          ) : (
            <Box textAlign="center" p={6}>
              <AutoFixHighIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                AI Optimization Available After Simulation
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Run an enhanced digital twin simulation to receive
                personalized AI-powered optimization recommendations.
              </Typography>
            </Box>
          )}
        </Box>
      )}

      {/* Clear Results Button */}
      {(analysisData?.analysis || scenarioResults) && !loading && !whatIfLoading && (
        <Box display="flex" justifyContent="center" mt={3}>
          <Button
            variant="outlined"
            onClick={() => {
              setAnalysisData(null);
              setScenarioResults(null);
              setScenarioHistory([]);
            }}
            startIcon={<RefreshIcon />}
            sx={{ borderRadius: 2 }}
          >
            Clear Results & Start Fresh
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default PatientAIAnalysis;
