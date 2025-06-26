# Diabetes Center: Επαναστατική Ψηφιακή Πλατφόρμα Διαχείρισης Διαβήτη με Τεχνητή Νοημοσύνη & Εξατομικευμένη Ιατρική

![Diabetes Center Logo](https://img.shields.io/badge/AI-Ready-success)  
*Ανοικτή, καινοτόμος πλατφόρμα για τον σακχαρώδη διαβήτη – Για κλινικούς, ερευνητές και ασθενείς.*

---

## 🔬 Vision: Το Μέλλον της Εξατομικευμένης Διαχείρισης Διαβήτη

Ο σακχαρώδης διαβήτης αποτελεί μια από τις μεγαλύτερες προκλήσεις της σύγχρονης ιατρικής, με εκατοντάδες εκατομμύρια ασθενείς παγκοσμίως. Το **Diabetes Center** φιλοδοξεί να μεταμορφώσει τη φροντίδα σε μια ολιστική, προσωποποιημένη, τεκμηριωμένη και data-driven εμπειρία, συνδυάζοντας:

- **Τεχνητή Νοημοσύνη (ΑΙ)**
- **Γενετική ανάλυση & φαρμακογονιδιωματική**
- **Real-time επιστημονική τεκμηρίωση**
- **Εργαλεία αυτοδιαχείρισης για τον ασθενή**
- **Συμμόρφωση με τα πιο αυστηρά διεθνή standards ασφάλειας & προστασίας δεδομένων**

---

## 🏗️ Αρχιτεκτονική Συστήματος

### 1. Backend: Flask Modular API

- **Python 3.x / Flask** με Blueprints και πλήρως modular σχεδίαση.
- **MongoDB** ως NoSQL βάση (document-based, encrypted), κατάλληλη για ετερογενή ιατρικά δεδομένα.
- **Granular permissions** & role-based access με JWT (stateless, end-to-end encryption).

#### Κύρια modules:
- **Authentication & Permissions**: Πολυεπίπεδη ασφάλεια, granular δικαιώματα (π.χ. ViewPatientPermission).
- **Patients, Doctors, Sessions**: CRUD RESTful endpoints, real-time audit trail.
- **File Management & OCR**: Αυτόματη επεξεργασία και εξαγωγή δομημένων δεδομένων από ιατρικά έγγραφα με ML-based OCR.
- **AI & Decision Support**: DeepSeek Medical, PubMed RAG, genetics, polygenic scores, PharmGKB integration.
- **Real-time Communication**: SocketIO, WebRTC για τηλεϊατρική και ειδοποιήσεις.

### 2. Frontend: Δύο Πλήρως Διαχωρισμένες Εφαρμογές

#### α) Doctor/Admin Portal (`diabetes_frontend`)
- **React + Vite** (SPA)
- Advanced AI Chat Interface (ιατρική υποστήριξη, PubMed RAG)
- Πλήρης διαχείριση ασθενών, ραντεβού, εγγράφων, συνεδριών
- Real-time dashboards, analytics, workflow/calendar management
- Role-based UI, granular permissions
- Υποστήριξη dark mode & theme customization

#### β) Patient Progressive Web App (`diabetes_patient_pwa`)
- **React + Vite PWA** (mobile-first, native-like εμπειρία, offline support)
- Πλήρης ελληνική τοπικοποίηση (1700+ τρόφιμα, Greek.json)
- Αυτόματη OCR ανάλυση εργαστηριακών αποτελεσμάτων
- Διαδραστικά γραφήματα διατροφής, γλυκόζης, trends υγείας
- Εργαλεία αυτοδιαχείρισης (φαγητό, φάρμακα, δραστηριότητες, αρχεία)
- Seamless επικοινωνία με γιατρό/κέντρο

---

## 🤖 Καινοτομίες & Τεχνολογική Αριστεία

### Τεχνητή Νοημοσύνη & Γενετική Ανάλυση
- **DeepSeek Medical**: AI-driven recommendations, context-aware decision support
- **PubMed RAG**: Αυτόματη αναζήτηση και σύνθεση επιστημονικής βιβλιογραφίας με NLP
- **Genetics Analyzer & Polygenic Scores**: Υπολογισμός γενετικού κινδύνου & εξατομίκευση θεραπείας
- **PharmGKB Integration**: Φαρμακογονιδιωματική ανάλυση, personalized drug selection & dosage

### Real-time, Data-driven Healthcare
- **WebRTC / SocketIO**: Peer-to-peer βιντεοκλήσεις, άμεσες ειδοποιήσεις, real-time collaboration
- **Advanced Dashboards**: Real-time monitoring, predictive analytics, early warning systems

### Διαλειτουργικότητα & Επεκτασιμότητα
- **API-first approach**: Εύκολη διασύνδεση με τρίτα συστήματα, wearables, health apps
- **Microservices-ready**: Modular αρχιτεκτονική, έτοιμη για scaling & future-proofing

---

## 🔒 Ασφάλεια, Συμμόρφωση & Privacy by Design

- **TLS 1.3, AES-256**: End-to-end κρυπτογράφηση στη μετάδοση & αποθήκευση
- **JWT με exp, rotation, session monitoring**
- **Audit logs & anomaly detection**: Πλήρης καταγραφή, ML-based ανάλυση για ύποπτες ενέργειες
- **GDPR compliance**: Data minimization, right to be forgotten, data portability
- **Key Management Excellence**: Περιστροφή, hardware secure modules

---

## 🧬 Επιστημονική Τεκμηρίωση & Evidence-based Medicine

- **Κάθε απόφαση βασίζεται σε πραγματικό, πρόσφατο evidence** (PubMed RAG, deep learning syntheses)
- **Κλινική αξία**: Συνδυασμός δεδομένων EHR, γενετικής, διατροφής, lifestyle για πλήρως προσωποποιημένες συστάσεις
- **Συνεχής ανανέωση γνώσης**: Αλγόριθμοι που ενσωματώνουν νέα ερευνητικά δεδομένα αυτόματα

---

## 🚀 Flows & User Journeys

### Για τον Ιατρό
1. Προφίλ ασθενή: Ιστορικό, γενετική, διατροφή, συνεδρίες, trends
2. Διαδραστικό ημερολόγιο, διαχείριση ραντεβού, ειδοποιήσεις
3. AI chat: Πληροφορίες, ιατρικά ερωτήματα, PubMed evidence, personalized recommendations
4. Advanced analytics: Dashboards, predictive trends, alerts
5. Διαχείριση εγγράφων με OCR & αυτόματη κατηγοριοποίηση

### Για τον Ασθενή
1. Mobile PWA: Καταγραφή γευμάτων, φαρμάκων, δραστηριοτήτων
2. Αυτόματη ανάλυση εργαστηριακών αποτελεσμάτων (OCR)
3. Real-time feedback, διαδραστικά γραφήματα, nutrition insights
4. Εύκολη επικοινωνία με ιατρό, διαμοιρασμός αρχείων, ασφάλεια δεδομένων
5. Προσωποποιημένες συστάσεις & empowerment

---

## 📊 Επιστημονική & Κοινωνική Επίδραση

- **Patient empowerment**: Ο ασθενής γίνεται ενεργό μέλος στην υγεία του
- **Clinical decision support**: Ο γιατρός εξοπλίζεται με AI, genetics, evidence – όχι αντικατάσταση, αλλά ενίσχυση
- **Research & RWE**: Ανώνυμα δεδομένα για επιστημονική έρευνα, population health, public health policies
- **Διεύρυνση του οικοσυστήματος**: Εύκολη διασύνδεση με άλλες πλατφόρμες, συστήματα, ακαδημαϊκούς φορείς

---

## 🛠️ Τεχνικές Οδηγίες (Setup)

### Backend
```bash
cd diabetes_backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Συμπληρώστε τα απαραίτητα keys
python app.py

