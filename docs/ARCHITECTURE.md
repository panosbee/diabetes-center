# System Architecture Documentation

## Overview
```mermaid
graph TD
    A[Doctor Portal] --> B[Backend API]
    C[Patient PWA] --> B
    D[AI Services] --> B
    B --> E[MongoDB]
    B --> F[VectorDB]
    D --> G[DeepSeek API]
    D --> H[PubMed RAG]
```

## Backend Architecture (Flask)
### Core Components:
- **`app.py`**: Main application entry point
- **JWT Authentication**: Role-based access control
- **Endpoint Structure**:
  ```python
  @app.route('/ai/query', methods=['POST'])
  @jwt_required()
  def ai_query():
      # Handles AI analysis requests
  ```

## Frontend Architecture (React)
### Component Structure:
- **Doctor Portal**: 
  - `src/components/PatientAIAnalysis.jsx`
  - `src/components/InteractiveCalendar.jsx`
- **Patient PWA**:
  - `src/components/FilesManagement.jsx`
  - `src/components/VideoCallManager.jsx`

## AI Integration
```mermaid
sequenceDiagram
    Frontend->>Backend: POST /ai/query
    Backend->>DecisionEngine: Process query
    DecisionEngine->>VectorDB: Retrieve context
    VectorDB->>PubMedRAG: Get medical literature
    PubMedRAG->>DeepSeek: Generate response
    DeepSeek-->>Frontend: Formatted analysis
```

## Data Flow
1. Patient data uploaded via PWA (`FileUpload.jsx`)
2. Stored in encrypted uploads directory
3. Processed by decision engine (`decision_engine.py`)
4. Context sent to DeepSeek via `ai.py`
5. Responses cached in MongoDB