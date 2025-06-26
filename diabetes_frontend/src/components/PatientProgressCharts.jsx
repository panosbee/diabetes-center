import React, { useEffect, useState, useMemo } from 'react';
import { useRecordContext, useGetList, Loading, Error as RaError } from 'react-admin'; // Renamed Error to avoid conflict
import { Box, Typography, Paper, Grid, Checkbox, FormControlLabel, Button, Menu, MenuItem, CircularProgress } from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import dayjs from 'dayjs';
import { format } from 'date-fns'; // Using date-fns for formatting
import { el } from 'date-fns/locale'; // Greek locale for date-fns
import {
    VictoryChart, VictoryLine, VictoryAxis, VictoryTheme, VictoryTooltip,
    VictoryVoronoiContainer, VictoryLegend, VictoryGroup, VictoryScatter, VictoryArea,
    VictoryLabel, VictoryPortal, VictoryContainer
} from 'victory';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import DownloadIcon from '@mui/icons-material/Download';
import { useTheme } from '@mui/material/styles'; // Import useTheme

// --- Configuration ---
const CHART_THEME = VictoryTheme.material; // Or VictoryTheme.grayscale, etc.
const DEFAULT_DAYS_RANGE = 90; // Default range to show (e.g., 3 months)

// Define Metrics with MUI Theme Colors (Example - Adjust as needed)
const METRICS_CONFIG = (theme) => [
    { key: 'weight', label: 'Βάρος', color: theme.palette.warning.main, unit: 'kg' },
    { key: 'bmi', label: 'BMI', color: theme.palette.success.dark, unit: '' },
    { key: 'hba1c', label: 'HbA1c', color: theme.palette.error.main, unit: '%' },
    { key: 'glucose', label: 'Γλυκόζη', color: theme.palette.info.main, unit: 'mg/dL' },
    { key: 'insulin_units', label: 'Ινσουλίνη', color: theme.palette.warning.light, unit: 'units' },
    { key: 'systolic', label: 'Συστολική', color: theme.palette.secondary.main, unit: 'mmHg' },
    { key: 'diastolic', label: 'Διαστολική', color: theme.palette.secondary.light, unit: 'mmHg' },
];

// --- Helper Functions ---

// Format date ticks for XAxis using date-fns
const formatDateTick = (tickItem) => {
    try {
        const date = new Date(tickItem);
        if (isNaN(date.getTime())) return 'Invalid Date';
        // Show year only if the range spans more than ~6 months, otherwise day/month
        // This logic might need adjustment based on actual tick values provided by Victory
        return format(date, 'dd/MM/yy', { locale: el });
    } catch (e) {
        console.error("formatDateTick error:", e, "for tickItem:", tickItem);
        return 'Error';
    }
};

const calculateBMI = (weightKg, heightCm) => {
    if (typeof weightKg !== 'number' || typeof heightCm !== 'number' || heightCm <= 0 || weightKg <= 0) {
        return null;
    }
    const heightM = heightCm / 100;
    const bmi = weightKg / (heightM * heightM);
    return Number(bmi.toFixed(1));
};

const parseNumericValue = (value) => {
    if (value === undefined || value === null || value === '') return null;
    const num = Number(value);
    return isNaN(num) ? null : num;
};

// --- Components ---

// Custom Tooltip Component
const CustomVictoryTooltip = ({ datum, x, y, metricsConfig, notesMap, active }) => {
    if (!active || !datum) return null;
    const theme = useTheme();
    const timestamp = datum.timestamp;
    const dateStr = datum.dateLabel ? format(new Date(datum.dateLabel), 'PPPPp', { locale: el }) : 'Άγνωστη Ημερομηνία';
    const notes = notesMap?.[timestamp] || '';

    return (
        <g style={{ pointerEvents: 'none' }}>
            <foreignObject x={x - 75} y={y - 100} width="150" height="120"> // Adjust position/size
                <Paper elevation={5} sx={{ p: 1, bgcolor: 'rgba(40, 40, 40, 0.85)', borderRadius: '4px', color: '#fff' }}>
                    <Typography variant="caption" display="block" sx={{ fontWeight: 'bold', borderBottom: '1px solid #666', pb: 0.5, mb: 0.5 }}>
                        {dateStr}
                    </Typography>
                    {metricsConfig.map((m) => {
                         const val = datum[m.key];
                         // Only display if the value exists for this point
                         if (val !== null && val !== undefined) {
                             return (
                                <Typography key={m.key} sx={{ color: m.color, fontSize: '0.75rem' }}>
                                    {`${m.label}: ${val}${m.unit || ''}`}
                                </Typography>
                            );
                         }
                         return null;
                    })}
                    {notes && (
                        <Typography variant="caption" sx={{ mt: 0.5, display: 'block', color: theme.palette.grey[400], fontStyle: 'italic' }}>
                           Σημ.: {notes.length > 50 ? notes.substring(0, 50) + '...' : notes}
                        </Typography>
                    )}
                </Paper>
            </foreignObject>
        </g>
    );
};


// Main Multi-Line Chart Component
const MultiLineProgressChart = ({ data, notesMap, metricsConfig }) => {
    const theme = useTheme();
    const [visibleLines, setVisibleLines] = useState(metricsConfig.map(m => m.key));
    const [dateRange, setDateRange] = useState(() => {
        // Set initial range: last X days or full range if less than X days
        const lastDate = data.length ? dayjs(new Date(data[data.length - 1].timestamp)) : dayjs();
        const firstDate = data.length ? dayjs(new Date(data[0].timestamp)) : dayjs().subtract(DEFAULT_DAYS_RANGE, 'day');
        const defaultStartDate = dayjs().subtract(DEFAULT_DAYS_RANGE, 'day');

        return {
            from: firstDate.isBefore(defaultStartDate) ? defaultStartDate : firstDate,
            to: lastDate,
        };
    });

    const [exportMenuAnchor, setExportMenuAnchor] = useState(null);

    const handleExportMenuOpen = (event) => setExportMenuAnchor(event.currentTarget);
    const handleExportMenuClose = () => setExportMenuAnchor(null);

    // Filter data based on selected date range and if it has *any* visible metric value
    const filteredData = useMemo(() => data.filter(d => {
        if (!dateRange.from || !dateRange.to) return false; // Require valid range
        const pointDate = dayjs(d.timestamp);
        return pointDate.isBetween(dateRange.from.startOf('day'), dateRange.to.endOf('day'), null, '[]') // Inclusive check
            && visibleLines.some(key => typeof d[key] === 'number' && !isNaN(d[key])); // Ensure at least one visible metric has data
    }), [data, dateRange, visibleLines]);


    const handleToggleLine = (key) => {
        setVisibleLines((prev) => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]);
    };

    const getDomainForVisibleLines = () => {
        let minY = Infinity;
        let maxY = -Infinity;
        let hasData = false;

        filteredData.forEach(d => {
            visibleLines.forEach(key => {
                const value = d[key];
                if (typeof value === 'number' && !isNaN(value)) {
                    hasData = true;
                    minY = Math.min(minY, value);
                    maxY = Math.max(maxY, value);
                }
            });
        });

        if (!hasData) return undefined; // Let Victory decide if no data

        // Add padding to the domain
        const padding = (maxY - minY) * 0.1 || 5; // Add 10% padding or a minimum of 5 units
        return { y: [Math.max(0, minY - padding), maxY + padding] }; // Ensure Y doesn't go below 0
    };

    const yDomain = getDomainForVisibleLines();

    const exportChart = async (formatType) => {
        handleExportMenuClose(); // Close menu first
        const chartNode = document.getElementById('multiline-progress-chart-container'); // Target the container div
        if (!chartNode) return;

        // Temporarily make sure the legend is fully visible for export if needed
        // (This might be complex depending on how overflow is handled)

        try {
            const canvas = await html2canvas(chartNode, {
                scale: 2, // Increase resolution for better quality
                backgroundColor: theme.palette.background.paper, // Match background
                useCORS: true,
                logging: true,
            });
            const imgData = canvas.toDataURL(formatType === 'pdf' ? 'image/jpeg' : 'image/png', 0.9); // Use JPEG for PDF for smaller size

            if (formatType === 'png') {
                const link = document.createElement('a');
                link.download = `multiline_progress_chart_${dayjs().format('YYYYMMDD')}.png`;
                link.href = imgData;
                link.click();
            } else if (formatType === 'pdf') {
                const pdf = new jsPDF({
                    orientation: 'landscape',
                    unit: 'px',
                    format: [canvas.width, canvas.height] // Use canvas dimensions
                });
                // Add title or other info if needed
                pdf.setFontSize(10);
                pdf.text(`Διάγραμμα Προόδου (${format(dateRange.from.toDate(), 'P', { locale: el })} - ${format(dateRange.to.toDate(), 'P', { locale: el })})`, 20, 20);
                pdf.addImage(imgData, 'JPEG', 0, 30, canvas.width, canvas.height);
                pdf.save(`multiline_progress_chart_${dayjs().format('YYYYMMDD')}.pdf`);
            }
        } catch (error) {
            console.error(`Error exporting chart as ${formatType}:`, error);
            alert(`Αποτυχία εξαγωγής γραφήματος ως ${formatType}.`);
        }
    };


    return (
        <Paper elevation={3} sx={{ p: { xs: 1, sm: 2, md: 3 }, mb: 4, borderRadius: 3, overflow: 'hidden' }}>
             <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', mb: 2, gap: 2 }}>
                <Typography variant="h6" component="h3" sx={{ fontWeight: 'bold' }}>
                    Συνολική Πρόοδος
                </Typography>
                 <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, alignItems: 'center' }}>
                    <LocalizationProvider dateAdapter={AdapterDayjs} adapterLocale="el">
                       <DatePicker
                           label="Από"
                           value={dateRange.from}
                           onChange={(newVal) => setDateRange(prev => ({...prev, from: dayjs(newVal)}))}
                           maxDate={dateRange.to}
                           slotProps={{ textField: { size: 'small', sx:{ minWidth: 140 } } }}
                       />
                       <DatePicker
                           label="Έως"
                           value={dateRange.to}
                           onChange={(newVal) => setDateRange(prev => ({...prev, to: dayjs(newVal)}))}
                           minDate={dateRange.from}
                           slotProps={{ textField: { size: 'small', sx:{ minWidth: 140 } } }}
                       />
                    </LocalizationProvider>
                     <Button
                         variant="outlined"
                         size="small"
                         onClick={handleExportMenuOpen}
                         startIcon={<DownloadIcon />}
                         sx={{ height: 40 }} // Match DatePicker height
                     >
                         Εξαγωγή
                     </Button>
                     <Menu
                         anchorEl={exportMenuAnchor}
                         open={Boolean(exportMenuAnchor)}
                         onClose={handleExportMenuClose}
                     >
                         <MenuItem onClick={() => exportChart('png')}>Ως PNG</MenuItem>
                         <MenuItem onClick={() => exportChart('pdf')}>Ως PDF</MenuItem>
                     </Menu>
                </Box>
            </Box>

            {/* Checkboxes for line visibility */}
             <Box sx={{ display: 'flex', justifyContent: 'center', flexWrap: 'wrap', mb: 1, gap: 0.5 }}>
                {metricsConfig.map(m => (
                    <FormControlLabel
                        key={m.key}
                        control={
                            <Checkbox
                                size="small"
                                checked={visibleLines.includes(m.key)}
                                onChange={() => handleToggleLine(m.key)}
                                sx={{
                                    color: m.color,
                                    '&.Mui-checked': { color: m.color },
                                    py: 0 // Reduce vertical padding
                                }}
                            />
                        }
                        label={<Typography variant="caption" sx={{ color: m.color }}>{m.label}</Typography>}
                        sx={{ mr: 1 }} // Reduce margin between checkboxes
                    />
                ))}
            </Box>

            {/* Chart Area */}
            {filteredData.length >= 2 ? (
                <Box id="multiline-progress-chart-container" sx={{ height: 350 }}> {/* Container for export */}
                 <VictoryChart
                    theme={CHART_THEME}
                    height={350}
                    width={800} // Responsive width will be handled by container
                    padding={{ top: 20, bottom: 50, left: 50, right: 30 }}
                    domain={yDomain} // Apply calculated Y domain
                    scale={{ x: "time" }} // Important for date axis
                    containerComponent={
                        <VictoryVoronoiContainer
                            voronoiDimension="x"
                            labelComponent={
                                <CustomVictoryTooltip
                                    metricsConfig={metricsConfig}
                                    notesMap={notesMap}
                                />
                            }
                            labels={() => ""} // Empty function to trigger label component
                        />
                    }
                >
                    {/* X Axis (Time) */}
                    <VictoryAxis
                        // tickValues={/* Optional: provide specific dates if needed */}
                        tickFormat={formatDateTick}
                        style={{
                            axisLabel: { fontSize: 10, padding: 35 },
                            tickLabels: { fontSize: 8, padding: 5, angle: -30, textAnchor: 'end' },
                            grid: { stroke: theme.palette.divider, strokeDasharray: '3, 5' }
                        }}
                    />
                    {/* Y Axis (Value) */}
                    <VictoryAxis
                        dependentAxis
                        // tickFormat={(t) => `${t}`} // Basic number format
                        style={{
                            axisLabel: { fontSize: 10, padding: 35 },
                            tickLabels: { fontSize: 8, padding: 5 },
                            grid: { stroke: theme.palette.divider, strokeDasharray: '3, 5' }
                        }}
                    />

                    {/* Lines and Areas */}
                    <VictoryGroup>
                        {metricsConfig
                            .filter(m => visibleLines.includes(m.key))
                            .map(m => (
                                <VictoryArea
                                    key={`${m.key}-area`}
                                    data={filteredData.filter(d => d[m.key] !== null && d[m.key] !== undefined)} // Filter points with data for this metric
                                    x="timestamp"
                                    y={m.key}
                                    style={{
                                        data: {
                                            fill: m.color,
                                            fillOpacity: 0.1, // Very light fill
                                            stroke: 'none'
                                        }
                                    }}
                                    interpolation="monotoneX"
                                />
                            ))}
                          {metricsConfig
                            .filter(m => visibleLines.includes(m.key))
                            .map(m => (
                                <VictoryLine
                                    key={m.key}
                                    data={filteredData.filter(d => d[m.key] !== null && d[m.key] !== undefined)} // Filter points with data for this metric
                                    x="timestamp"
                                    y={m.key}
                                    style={{ data: { stroke: m.color, strokeWidth: 2 } }}
                                    interpolation="monotoneX"
                                />
                            ))}
                     </VictoryGroup>
                </VictoryChart>
                </Box>
             ) : (
                <Box sx={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography color="textSecondary">Δεν υπάρχουν αρκετά δεδομένα στο επιλεγμένο εύρος για εμφάνιση του γραφήματος.</Typography>
                </Box>
             )}
        </Paper>
    );
};

// Scatter Plot Component (Βελτιωμένο)
const ScatterWeightBMIChart = ({ data, metricsConfig }) => {
    const theme = useTheme();
    const bmiColor = metricsConfig.find(m => m.key === 'bmi')?.color || theme.palette.success.dark;
    const weightColor = metricsConfig.find(m => m.key === 'weight')?.color || theme.palette.warning.main;

    const plotData = data.filter(d => typeof d.weight === 'number' && typeof d.bmi === 'number');

    if (plotData.length < 2) return null; // Don't render if not enough data

    return (
        <Paper elevation={3} sx={{ p: { xs: 1, sm: 2, md: 3 }, mb: 4, borderRadius: 3 }}>
            <Typography variant="h6" component="h3" gutterBottom sx={{ fontWeight: 'bold' }}>Συσχέτιση Βάρους & BMI</Typography>
             <Box sx={{ height: 300 }}>
                <VictoryChart
                    theme={CHART_THEME}
                    height={300}
                    width={800}
                    padding={{ top: 20, bottom: 50, left: 60, right: 30 }}
                    domainPadding={{ x: 15, y: 10 }}
                    containerComponent={<VictoryContainer responsive={true} />}
                >
                    <VictoryAxis
                        label="Βάρος (kg)"
                        style={{ axisLabel: { fontSize: 10, padding: 30 }, tickLabels: { fontSize: 8, padding: 5 } }}
                    />
                    <VictoryAxis
                        dependentAxis
                        label="BMI"
                        style={{ axisLabel: { fontSize: 10, padding: 40 }, tickLabels: { fontSize: 8, padding: 5 } }}
                    />
                    <VictoryScatter
                        data={plotData}
                        x="weight"
                        y="bmi"
                        size={4}
                        style={{ data: { fill: bmiColor } }}
                        labels={({ datum }) => `Βάρος: ${datum.weight}kg\nBMI: ${datum.bmi}\n(${formatDateTick(datum.timestamp)})`}
                        labelComponent={<VictoryTooltip cornerRadius={3} flyoutStyle={{ fill: "rgba(40,40,40,0.85)", stroke: "#fff", strokeWidth: 0.5 }} style={{ fill: "#fff", fontSize: 8 }} constrainToVisibleArea />}
                    />
                </VictoryChart>
             </Box>
        </Paper>
    );
};

// Area Chart for HbA1c (Βελτιωμένο)
const AreaHbA1cChart = ({ data, metricsConfig }) => {
    const theme = useTheme();
    const hba1cColor = metricsConfig.find(m => m.key === 'hba1c')?.color || theme.palette.error.main;

    const plotData = data.filter(d => typeof d.hba1c === 'number' && !isNaN(d.hba1c));

    if (plotData.length < 2) return null; // Don't render if not enough data

    return (
         <Paper elevation={3} sx={{ p: { xs: 1, sm: 2, md: 3 }, mb: 4, borderRadius: 3 }}>
            <Typography variant="h6" component="h3" gutterBottom sx={{ fontWeight: 'bold' }}>Τάση Γλυκοζυλιωμένης Αιμοσφαιρίνης (HbA1c)</Typography>
            <Box sx={{ height: 300 }}>
                <VictoryChart
                    theme={CHART_THEME}
                    height={300}
                    width={800}
                    padding={{ top: 20, bottom: 50, left: 50, right: 30 }}
                    scale={{ x: "time" }}
                    containerComponent={<VictoryContainer responsive={true} />}
                >
                    <VictoryAxis
                        tickFormat={formatDateTick}
                        style={{ axisLabel: { fontSize: 10, padding: 35 }, tickLabels: { fontSize: 8, padding: 5, angle: -30, textAnchor: 'end' } }}
                    />
                    <VictoryAxis
                        dependentAxis
                        label="HbA1c (%)"
                        style={{ axisLabel: { fontSize: 10, padding: 35 }, tickLabels: { fontSize: 8, padding: 5 } }}
                    />
                    <VictoryArea
                        data={plotData}
                        x="timestamp"
                        y="hba1c"
                        style={{ data: { fill: hba1cColor, fillOpacity: 0.2, stroke: hba1cColor, strokeWidth: 2 } }}
                        interpolation="monotoneX"
                    />
                    {/* Add scatter points on top */}
                     <VictoryScatter
                        data={plotData}
                        x="timestamp"
                        y="hba1c"
                        size={3}
                        style={{ data: { fill: hba1cColor } }}
                        labels={({ datum }) => `HbA1c: ${datum.hba1c}%\n(${formatDateTick(datum.timestamp)})`}
                        labelComponent={<VictoryTooltip cornerRadius={3} flyoutStyle={{ fill: "rgba(40,40,40,0.85)", stroke: "#fff", strokeWidth: 0.5 }} style={{ fill: "#fff", fontSize: 8 }} constrainToVisibleArea />}
                    />
                </VictoryChart>
            </Box>
        </Paper>
    );
};

// Area Chart for Glucose (ΝΕΟ)
const AreaGlucoseChart = ({ data, metricsConfig }) => {
    const theme = useTheme();
    const glucoseColor = metricsConfig.find(m => m.key === 'glucose')?.color || theme.palette.info.main;

    const plotData = data.filter(d => typeof d.glucose === 'number' && !isNaN(d.glucose));

    if (plotData.length < 2) return null;

    return (
        <Paper elevation={3} sx={{ p: { xs: 1, sm: 2, md: 3 }, mb: 4, borderRadius: 3 }}>
            <Typography variant="h6" component="h3" gutterBottom sx={{ fontWeight: 'bold' }}>Τάση Γλυκόζης Αίματος</Typography>
            <Box sx={{ height: 300 }}>
                <VictoryChart
                    theme={CHART_THEME}
                    height={300}
                    width={800}
                    padding={{ top: 20, bottom: 50, left: 50, right: 30 }}
                    scale={{ x: "time" }}
                    containerComponent={<VictoryContainer responsive={true} />}
                >
                    <VictoryAxis
                        tickFormat={formatDateTick}
                        style={{ axisLabel: { fontSize: 10, padding: 35 }, tickLabels: { fontSize: 8, padding: 5, angle: -30, textAnchor: 'end' } }}
                    />
                    <VictoryAxis
                        dependentAxis
                        label="Γλυκόζη (mg/dL)"
                        style={{ axisLabel: { fontSize: 10, padding: 35 }, tickLabels: { fontSize: 8, padding: 5 } }}
                    />
                     <VictoryArea
                        data={plotData}
                        x="timestamp"
                        y="glucose"
                        style={{ data: { fill: glucoseColor, fillOpacity: 0.2, stroke: glucoseColor, strokeWidth: 2 } }}
                        interpolation="monotoneX"
                    />
                    <VictoryScatter
                        data={plotData}
                        x="timestamp"
                        y="glucose"
                        size={3}
                        style={{ data: { fill: glucoseColor } }}
                         labels={({ datum }) => `Γλυκόζη: ${datum.glucose} mg/dL\n(${formatDateTick(datum.timestamp)})`}
                        labelComponent={<VictoryTooltip cornerRadius={3} flyoutStyle={{ fill: "rgba(40,40,40,0.85)", stroke: "#fff", strokeWidth: 0.5 }} style={{ fill: "#fff", fontSize: 8 }} constrainToVisibleArea />}
                    />
                </VictoryChart>
            </Box>
        </Paper>
    );
};

// Line Chart for Blood Pressure (ΝΕΟ)
const LineBloodPressureChart = ({ data, metricsConfig }) => {
    const theme = useTheme();
    const systolicColor = metricsConfig.find(m => m.key === 'systolic')?.color || theme.palette.secondary.main;
    const diastolicColor = metricsConfig.find(m => m.key === 'diastolic')?.color || theme.palette.secondary.light;

    const plotData = data.filter(d => (typeof d.systolic === 'number' && !isNaN(d.systolic)) || (typeof d.diastolic === 'number' && !isNaN(d.diastolic)));

    if (plotData.length < 2) return null;

     // Find min/max for Y domain padding
     let minY = Infinity, maxY = -Infinity;
     plotData.forEach(d => {
         if(d.systolic !== null) { minY = Math.min(minY, d.systolic); maxY = Math.max(maxY, d.systolic); }
         if(d.diastolic !== null) { minY = Math.min(minY, d.diastolic); /* maxY already covers systolic */ }
     });
     const yPadding = (maxY - minY) > 0 ? (maxY - minY) * 0.1 : 10; // 10% or 10 units padding
     const yDomain = minY === Infinity ? undefined : { y: [Math.max(0, minY - yPadding), maxY + yPadding] };

    return (
         <Paper elevation={3} sx={{ p: { xs: 1, sm: 2, md: 3 }, mb: 4, borderRadius: 3 }}>
            <Typography variant="h6" component="h3" gutterBottom sx={{ fontWeight: 'bold' }}>Τάση Αρτηριακής Πίεσης</Typography>
             <Box sx={{ height: 300 }}>
                <VictoryChart
                    theme={CHART_THEME}
                    height={300}
                    width={800}
                    padding={{ top: 40, bottom: 50, left: 50, right: 30 }}
                    scale={{ x: "time" }}
                    domain={yDomain}
                    containerComponent={<VictoryContainer responsive={true} />}
                >
                   <VictoryLegend x={50} y={5}
                        title="Πίεση (mmHg)"
                        centerTitle
                        orientation="horizontal"
                        gutter={20}
                        style={{ border: { stroke: "none" }, title: {fontSize: 10 }, labels: { fontSize: 9 } }}
                        data={[
                          { name: "Συστολική", symbol: { fill: systolicColor } },
                          { name: "Διαστολική", symbol: { fill: diastolicColor } }
                        ]}
                      />
                    <VictoryAxis
                        tickFormat={formatDateTick}
                        style={{ axisLabel: { fontSize: 10, padding: 35 }, tickLabels: { fontSize: 8, padding: 5, angle: -30, textAnchor: 'end' } }}
                    />
                    <VictoryAxis
                        dependentAxis
                        label="Πίεση (mmHg)"
                        style={{ axisLabel: { fontSize: 10, padding: 35 }, tickLabels: { fontSize: 8, padding: 5 } }}
                    />
                    {/* Systolic Line */}
                    <VictoryLine
                        data={plotData.filter(d => d.systolic !== null)}
                        x="timestamp"
                        y="systolic"
                        style={{ data: { stroke: systolicColor, strokeWidth: 2 } }}
                         labels={({ datum }) => `Συσ.: ${datum.systolic} mmHg\n(${formatDateTick(datum.timestamp)})`}
                        labelComponent={<VictoryTooltip cornerRadius={3} flyoutStyle={{ fill: "rgba(40,40,40,0.85)", stroke: "#fff", strokeWidth: 0.5 }} style={{ fill: "#fff", fontSize: 8 }} constrainToVisibleArea />}
                        interpolation="monotoneX"
                    />
                    {/* Diastolic Line */}
                    <VictoryLine
                        data={plotData.filter(d => d.diastolic !== null)}
                        x="timestamp"
                        y="diastolic"
                        style={{ data: { stroke: diastolicColor, strokeWidth: 2 } }}
                        labels={({ datum }) => `Διασ.: ${datum.diastolic} mmHg\n(${formatDateTick(datum.timestamp)})`}
                        labelComponent={<VictoryTooltip cornerRadius={3} flyoutStyle={{ fill: "rgba(40,40,40,0.85)", stroke: "#fff", strokeWidth: 0.5 }} style={{ fill: "#fff", fontSize: 8 }} constrainToVisibleArea />}
                        interpolation="monotoneX"
                    />
                </VictoryChart>
             </Box>
        </Paper>
    );
};

// --- ΕΝΙΣΧΥΜΕΝΟ SUMMARY PANEL ---
const SummaryPanel = ({ latest }) => {
  const theme = useTheme(); // Πρόσθεσε αυτό αν δεν υπάρχει ήδη μέσα στο SummaryPanel

  // Επιστροφή null αν δεν υπάρχουν δεδομένα για εμφάνιση
  if (!latest) {
      return (
          <Paper elevation={4} sx={{ /* ... τα styles σου ... */ p: 3, mb: 4, textAlign: 'center' }}>
              <Typography color="textSecondary">Δεν υπάρχουν διαθέσιμα συνοπτικά δεδομένα.</Typography>
          </Paper>
      );
  }

  return (
    <Paper elevation={3} sx={{ // Μείωσα λίγο το elevation για συνέπεια
      p: { xs: 1.5, sm: 2, md: 2.5 }, // Προσαρμογή padding
      mb: 4,
      borderRadius: 3, // Προσαρμογή borderRadius
      // Χρησιμοποιώ ένα απλό background αντί για gradient για ευκολία, μπορείς να το αλλάξεις
      backgroundColor: theme.palette.mode === 'light' ? theme.palette.grey[100] : theme.palette.grey[800],
      boxShadow: '0 2px 10px 0 rgba(0, 0, 0, 0.07)', // Πιο διακριτική σκιά
      maxWidth: '100%', // Να πιάνει όλο το πλάτος αν χρειαστεί
      mx: 'auto',
    }}>
       <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main', mb: 2 }}>
            Τελευταία Καταγραφή
       </Typography>
        <Grid container spacing={{ xs: 1.5, sm: 2 }}> {/* Χρήση Grid για καλύτερο layout */}
          {/* Στήλη 1 */}
          <Grid item xs={12} sm={6} md={4} lg={3}>
              <Typography variant="caption" color="textSecondary" fontWeight={600}>Βάρος:</Typography>
              <Typography variant="body1" fontWeight={500}>{latest.weight ?? '—'} kg</Typography>

              <Typography variant="caption" color="textSecondary" fontWeight={600} sx={{ mt: 1 }}>Ύψος:</Typography>
              <Typography variant="body1" fontWeight={500}>{latest.height_cm ?? '—'} cm</Typography>

              <Typography variant="caption" color="textSecondary" fontWeight={600} sx={{ mt: 1 }}>BMI:</Typography>
              <Typography variant="body1" fontWeight={500}>{latest.bmi ?? '—'}</Typography>
          </Grid>

          {/* Στήλη 2 */}
           <Grid item xs={12} sm={6} md={4} lg={3}>
              <Typography variant="caption" color="textSecondary" fontWeight={600}>HbA1c:</Typography>
              <Typography variant="body1" fontWeight={500}>{latest.hba1c ?? '—'} %</Typography>

               <Typography variant="caption" color="textSecondary" fontWeight={600} sx={{ mt: 1 }}>Γλυκόζη:</Typography>
               <Typography variant="body1" fontWeight={500}>{latest.glucose ?? '—'} mg/dL</Typography>

              <Typography variant="caption" color="textSecondary" fontWeight={600} sx={{ mt: 1 }}>Ινσουλίνη:</Typography>
              <Typography variant="body1" fontWeight={500}>{latest.insulin_units ?? '—'} units</Typography>
          </Grid>

          {/* Στήλη 3 */}
          <Grid item xs={12} sm={6} md={4} lg={3}>
              <Typography variant="caption" color="textSecondary" fontWeight={600}>Συστολική:</Typography>
              <Typography variant="body1" fontWeight={500}>{latest.systolic ?? '—'} mmHg</Typography>

              <Typography variant="caption" color="textSecondary" fontWeight={600} sx={{ mt: 1 }}>Διαστολική:</Typography>
              <Typography variant="body1" fontWeight={500}>{latest.diastolic ?? '—'} mmHg</Typography>

              <Typography variant="caption" color="textSecondary" fontWeight={600} sx={{ mt: 1 }}>Τύπος Μέτρ.:</Typography>
              <Typography variant="body1" fontWeight={500}>{latest.measurement_type ?? '—'}</Typography>
          </Grid>

          {/* Στήλη 4 - Σημειώσεις κλπ (αν υπάρχουν) */}
           <Grid item xs={12} sm={6} md={12} lg={3}> {/* Πιάνει όλο το πλάτος σε md */}
                {latest.notes && (<>
                    <Typography variant="caption" color="textSecondary" fontWeight={600}>Σημ. Ασθενή:</Typography>
                    <Typography variant="body2" sx={{mb: 1}}>{latest.notes}</Typography>
                </>)}
                 {latest.doctor_notes && (<>
                     <Typography variant="caption" color="textSecondary" fontWeight={600}>Σημ. Ιατρού:</Typography>
                     <Typography variant="body2" sx={{mb: 1}}>{latest.doctor_notes}</Typography>
                 </>)}
                  {latest.therapy_adjustments && (<>
                     <Typography variant="caption" color="textSecondary" fontWeight={600}>Πρσ. Θεραπείας:</Typography>
                     <Typography variant="body2" sx={{mb: 1}}>{latest.therapy_adjustments}</Typography>
                 </>)}
                 {latest.patient_report && (<>
                     <Typography variant="caption" color="textSecondary" fontWeight={600}>Αναφ. Ασθενή:</Typography>
                     <Typography variant="body2">{latest.patient_report}</Typography>
                 </>)}
           </Grid>
        </Grid>
    </Paper>
  );
};

// Ακολουθεί ο υπόλοιπος κώδικας...
// const PatientProgressCharts = () => { ...
// Main PatientProgressCharts Component
const PatientProgressCharts = () => {
    const record = useRecordContext();
    const patientId = record?.id;
    const [patientHeight, setPatientHeight] = useState(null);
    const theme = useTheme(); // Get theme here
    const metricsConfig = useMemo(() => METRICS_CONFIG(theme), [theme]); // Pass theme to config

    // Fetch patient height
    useEffect(() => {
        let height = record?.medical_profile?.height_cm;
        if (typeof height === 'number' && height > 0) {
            setPatientHeight(height);
        } else {
            setPatientHeight(null); // Reset if invalid
        }
    }, [record]);

    // Fetch sessions
    const { data: sessions, isLoading, error: sessionsError } = useGetList(
        'sessions',
        {
            filter: { patient_id: patientId },
            sort: { field: 'timestamp', order: 'ASC' },
            pagination: { page: 1, perPage: 1000 }
        },
        { enabled: !!patientId }
    );

    // Process data for charts
    const { chartData, notesMap } = useMemo(() => {
        console.log("[PatientProgressCharts] Processing data. Height:", patientHeight);
        if (!sessions) return { chartData: [], notesMap: {} };

        const processed = sessions.map(session => {
            const vitals = session.vitals_recorded || {};
            const weightNum = parseNumericValue(vitals.weight_kg);
            const sessionHeightNum = parseNumericValue(vitals.height_cm);
            let bmi = parseNumericValue(vitals.bmi); // Prefer stored BMI

            // Calculate BMI if not stored and height is available
            if (bmi === null && weightNum !== null) {
                const heightToUse = patientHeight ?? sessionHeightNum; // Prioritize profile height
                if (heightToUse) {
                    bmi = calculateBMI(weightNum, heightToUse);
                }
            }

            return {
                timestamp: new Date(session.timestamp).getTime(),
                dateLabel: session.timestamp,
                weight: weightNum,
                bmi: bmi,
                hba1c: parseNumericValue(vitals.hba1c),
                systolic: parseNumericValue(vitals.blood_pressure_systolic),
                diastolic: parseNumericValue(vitals.blood_pressure_diastolic),
                glucose: parseNumericValue(vitals.blood_glucose_level),
                insulin_units: parseNumericValue(vitals.insulin_units)
            };
        }).filter(d => !isNaN(d.timestamp)); // Filter out invalid dates

        const notes = sessions.reduce((acc, session) => {
             if (session.notes) { // Only add if notes exist
                 acc[new Date(session.timestamp).getTime()] = session.notes;
             }
             return acc;
         }, {});


        return { chartData: processed, notesMap: notes };
    }, [sessions, patientHeight]);

    // Find latest data point for Summary (slightly different logic)
     const latestSessionData = useMemo(() => {
        if (!sessions || sessions.length === 0) return null;
        const latestSession = sessions[sessions.length - 1];
        const latestChartPoint = chartData.length > 0 ? chartData[chartData.length-1] : {};
        return {
            weight: latestChartPoint.weight,
            bmi: latestChartPoint.bmi,
            hba1c: latestChartPoint.hba1c,
            systolic: latestChartPoint.systolic,
            diastolic: latestChartPoint.diastolic,
            glucose: latestChartPoint.glucose,
            insulin_units: latestChartPoint.insulin_units,
            height_cm: patientHeight, // Show the height used for BMI calculation
            // Get text fields directly from the latest session record
            notes: latestSession.notes,
            doctor_notes: latestSession.doctor_notes,
            therapy_adjustments: latestSession.therapy_adjustments,
            patient_report: latestSession.patient_report,
            measurement_type: latestSession.measurement_type,
        };
    }, [sessions, chartData, patientHeight]);


    if (isLoading && !sessions) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress /></Box>;
    if (sessionsError) return <Paper sx={{ p: 2, m: 2, backgroundColor: 'error.lighter', color: 'error.dark' }}><Typography>Σφάλμα φόρτωσης δεδομένων συνεδριών: {sessionsError.message}</Typography></Paper>;
    if (!sessions && !isLoading) return <Paper sx={{ p: 2, m: 2 }}><Typography>Δεν βρέθηκαν δεδομένα συνεδριών για αυτόν τον ασθενή.</Typography></Paper>;
    if (chartData.length < 2) { // Needs at least 2 valid points for lines/areas
        return (
            <Box sx={{ mt: 3 }}>
                {latestSessionData && <SummaryPanel latest={latestSessionData} />} {/* Show summary even with <2 points */}
                 <Paper sx={{ p: 2, textAlign: 'center', mt: 2 }}>
                     <Typography color="textSecondary">Δεν υπάρχουν αρκετές καταγραφές (τουλάχιστον 2) για την πλήρη δημιουργία γραφημάτων προόδου.</Typography>
                 </Paper>
             </Box>
        );
   }

    return (
        <Box sx={{ mt: 3 }}>
            {/* Εμφάνιση Summary Panel */}
            {latestSessionData && <SummaryPanel latest={latestSessionData} />}

            <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 'bold', color: 'primary.main', textAlign: 'center' }}>
                Διαγράμματα Προόδου
            </Typography>

            {/* Κύριο Γράφημα */}
            <MultiLineProgressChart data={chartData} notesMap={notesMap} metricsConfig={metricsConfig} />

            {/* Επιμέρους Γραφήματα */}
            <Grid container spacing={3}>
                 {/* Blood Pressure Chart */}
                 <Grid item xs={12} lg={6}>
                     <LineBloodPressureChart data={chartData} metricsConfig={metricsConfig} />
                 </Grid>
                 {/* Glucose Chart */}
                  <Grid item xs={12} lg={6}>
                     <AreaGlucoseChart data={chartData} metricsConfig={metricsConfig} />
                 </Grid>
                {/* HbA1c Chart */}
                <Grid item xs={12} lg={6}>
                    <AreaHbA1cChart data={chartData} metricsConfig={metricsConfig} />
                </Grid>
                {/* Weight vs BMI Scatter */}
                <Grid item xs={12} lg={6}>
                    <ScatterWeightBMIChart data={chartData} metricsConfig={metricsConfig} />
                </Grid>
            </Grid>
        </Box>
    );
};

export default PatientProgressCharts;