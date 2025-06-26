# User Operation Manuals

## Doctor Portal
### Patient Analysis Workflow
1. **Select Patient**: From `MyPatientList.jsx`
2. **Upload Files**: Using `FileUpload.jsx`
3. **Initiate AI Analysis**: Click "Analyze" in `PatientAIAnalysis.jsx`
4. **Review Results**: Interactive charts in `PatientProgressCharts.jsx`

![Doctor Portal Workflow](workflow.png)

## Patient PWA
### Key Features:
- **Appointment Management**: `UpcomingBookedAppointmentsList.jsx`
- **File Sharing**: `FilesManagement.jsx`
- **Video Consultations**: `VideoCallManager.jsx`

```javascript
// Example: Booking appointment
// src/pages/SessionsPage.jsx
function handleBookAppointment(sessionId) {
  dataProvider.create('sessions', { id: sessionId, status: 'booked' });
}
```

## AI Analysis Interface
### Usage Patterns:
1. **Quick Questions**: Floating chat button (`FloatingAIChatButton.jsx`)
2. **Deep Analysis**: Full-page interface (`AIChatInterface.jsx`)
3. **Context Sources**:
   - Patient medical history
   - Uploaded documents
   - PubMed research

## File Management
### Supported Formats:
- PDF reports
- CSV data exports
- Medical imaging (DICOM conversion)