# Diabetes Center Platform

## 🚀 Overview

**Diabetes Center** is a groundbreaking, AI-powered digital health platform for diabetes management, designed for both clinicians and patients. It combines advanced clinical decision support, digital twin simulation, real-time analytics, and personalized medicine, all within a secure, modular, and extensible architecture.

---

## 🏗️ Architecture

### Backend

- **Python 3.x / Flask** modular API with Blueprints for scalability.
- **MongoDB** (encrypted, document-based) for flexible, secure storage.
- **Role-Based Access Control (RBAC)** and JWT authentication for secure, granular permissions.
- **AI & Decision Support**: DeepSeek Medical, PubMed RAG, genetics, polygenic scores, PharmGKB, and digital twin engine.
- **File Management & OCR**: Automated extraction and structuring of medical data from uploaded documents.
- **WebRTC & SocketIO**: Real-time video calls, chat, and notifications.
- **Audit Logging**: Immutable logs and anomaly detection for compliance.

### Frontend

#### Doctor/Admin Portal (`diabetes_frontend`)
- **React + Vite** SPA.
- AI chat interface for clinical support and PubMed RAG.
- Patient management, session history, file management, analytics dashboards.
- **Interactive Diary**: Shared, editable timeline for doctor-patient communication, medication, and events.
- **WebRTC Video Calls**: Secure, browser-based video communication with patients.
- **Interactive Mindmaps**: Visualize patient data, scenarios, and outcomes with D3.js.

#### Patient PWA (`diabetes_patient_pwa`)
- **React + Vite PWA** (mobile-first, offline support).
- Full Greek localization (1700+ foods in Greek.json for macronutrient tracking).
- File upload with OCR, session management, secure messaging, and video calls.
- **Interactive Diary**: Patients can log symptoms, meals, exercise, and communicate with their doctor in real time.

---

## 🤖 Key Innovations

- **Digital Twin Engine**: Patient-specific, 6-compartment glucose-insulin simulation with stochastic and circadian modeling, supporting “what-if” scenario analysis.
- **AI Clinical Decision Support**: DeepSeek Medical engine provides context-aware, evidence-based recommendations.
- **PubMed RAG Integration**: Real-time retrieval and summarization of medical literature for clinical queries.
- **PGS Catalog & SNP Database**: Polygenic risk scoring, SNP validation, and evidence-based risk stratification.
- **PharmGKB Pharmacogenomics**: Personalized drug-gene interaction analysis and dosing recommendations.
- **OCR Engine**: Automated extraction of structured data from PDFs/images (labs, prescriptions, etc.).
- **Interactive Doctor-Patient Diary**: Shared, editable timeline for tracking symptoms, medications, and lifestyle events.
- **WebRTC Video Calls**: Secure, encrypted video communication between doctor and patient, with audit trails.
- **Real-time Dashboards**: Live monitoring, predictive analytics, and early warning systems.
- **Food Database**: 1700+ Greek foods with macronutrient data for precise dietary tracking.
- **PWA Patient Portal**: Mobile-friendly, offline-capable, empowering patients to manage their data and communicate with clinicians.

---

## 🔒 Security & Compliance

- **TLS 1.3, AES-256**: End-to-end encryption for data in transit and at rest.
- **JWT Authentication**: Short-lived tokens, session monitoring, and rotation.
- **Role-Based Access Control (RBAC)**: Doctors can only access their own patients and sessions.
- **Audit Logs & Anomaly Detection**: Immutable logging, ML-based analysis for suspicious activity.
- **GDPR & HIPAA Compliance**: Data minimization, right to be forgotten, data portability.
- **File Security**: Per-patient access, signed URLs, and encrypted storage.
- **WebRTC Security**: Encrypted peer-to-peer video streams, no third-party relay.
- **Vulnerability Management**: Automated dependency scanning and regular security audits.

---

## 🧬 Scientific Foundation

- **PGS Catalog Integration**: Polygenic risk scores for diabetes and comorbidities.
- **SNP Database**: Curated, validated SNPs with PubMed citations and clinical annotations.
- **PharmGKB**: Drug-gene interactions for personalized pharmacotherapy.
- **PubMed RAG**: Real-time literature retrieval and AI-powered summarization.
- **Digital Twin Simulation**: Advanced PK/PD models for individualized therapy simulation.
- **Clinical Validation**: Benchmarked against ADA, AACE, and international guidelines.

---

## 🩺 Core Features

- **Doctor Portal**: Add/manage patients, review sessions, upload files, run AI analysis, access PubMed evidence, video calls, and diary.
- **Patient PWA**: Upload lab/device data, view history, receive AI analysis, communicate securely, video calls, and diary.
- **File Management**: Drag-and-drop upload, OCR extraction, tagging, preview, and secure download.
- **AI Analysis**: Visual and textual insights, risk assessment, and actionable recommendations.
- **Digital Twin Simulation**: Run and visualize “what-if” scenarios for therapy optimization.
- **Interactive Mindmaps**: Visualize relationships between parameters, outcomes, and recommendations.
- **Interactive Diary**: Real-time, bidirectional timeline for symptoms, medications, and lifestyle events.
- **WebRTC Video Calls**: Secure, browser-based video communication with audit trails.
- **Food & Nutrition**: Greek food database for meal tracking and macronutrient analysis.
- **Real-time Dashboards**: Live monitoring, predictive analytics, and early warning systems.

---

## 📊 Impact & Clinical Value

- **Personalized Care**: AI-driven, evidence-based recommendations tailored to each patient.
- **Efficiency**: Automated data extraction, analysis, and reporting reduce clinician workload.
- **Patient Empowerment**: Patients actively manage their data and participate in care decisions.
- **Research-Ready**: Modular architecture supports integration with new AI models, devices, and clinical studies.

---

## 🛡️ How to Run

1. **Backend**:  
   - Python 3.x, Flask, MongoDB  
   - `pip install -r requirements.txt`  
   - `python app.py`

2. **Frontend (Doctor Portal & Patient PWA)**:  
   - Node.js, Vite  
   - `npm install`  
   - `npm run dev`

3. **Environment**:  
   - Configure `.env` with MongoDB URI, PubMed API key, and encryption keys.

---

## 📚 References

- Nathan, D. M., et al. (2008). "The Diabetes Control and Complications Trial/Epidemiology of Diabetes Interventions and Complications Study at 30 years: Overview." *Diabetes Care*.
- American Diabetes Association. (2020). "Standards of Medical Care in Diabetes—2020." *Diabetes Care*.
- Riddle, M. C., et al. (2019). "Insulin Therapy in Type 2 Diabetes: A Position Statement of the American Diabetes Association." *Diabetes Care*.
- PubMed, PGS Catalog, PharmGKB official documentation.

---

## 🏆 Acknowledgements

This platform integrates the latest advances in AI, genomics, and clinical informatics to set a new standard for diabetes care.  
**For more details, see the [Technical Report](docs/Diabetes_Platform_Technical_Report.md) and [Digital Twin Paper](docs/digital-twin-paper/README.md).**

---

**Contact:**  
For clinical pilots, research collaboration, or technical support, please contact the project maintainers.
