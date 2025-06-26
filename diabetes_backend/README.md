# Diabetes Management Backend

## Επισκόπηση Αρχιτεκτονικής

Το backend αναδιοργανώθηκε χρησιμοποιώντας Flask Blueprints για καλύτερη δομή και διαχειρισιμότητα:

- **config/**: Περιέχει τις ρυθμίσεις της εφαρμογής
- **models/**: Θα περιέχει μοντέλα δεδομένων
- **routes/**: Περιέχει τα Flask Blueprints για κάθε τμήμα του API
- **utils/**: Βοηθητικές λειτουργίες (βάση δεδομένων, διαχείριση αρχείων)

## Εγκατάσταση & Εκκίνηση

### Προϋποθέσεις
- Python 3.11 ή νεότερο
- MongoDB
- Tesseract OCR εγκατεστημένο (για την επεξεργασία PDF)

### Εγκατάσταση

1. Ενεργοποιήστε το virtual environment:
   ```
   cd diabetes_backend
   .\venv\Scripts\activate
   ```

2. Εγκαταστήστε τις εξαρτήσεις:
   ```
   pip install -r requirements.txt
   ```

3. Δημιουργήστε αρχείο `.env` με τις παρακάτω μεταβλητές:
   ```
   JWT_SECRET_KEY=your-secret-key
   MONGO_URI=mongodb://localhost:27017/
   DEEPSEEK_API_KEY=your-api-key (αν χρειάζεται)
   DEEPSEEK_API_URL=your-api-url (αν χρειάζεται)
   ```

### Εκκίνηση

Για να χρησιμοποιήσετε το νέο, αναδομημένο backend:

```
python app.py.new
```

Αν επιθυμείτε να μετονομάσετε το αρχείο στο αρχικό όνομα:

```
ren app.py app.py.old
ren app.py.new app.py
python app.py
```

Ο server θα εκκινήσει στη διεύθυνση http://localhost:5000.

## API Endpoints

### Authentication

- **POST /api/auth/login** - Είσοδος χρήστη
- **POST /api/auth/change-password** - Αλλαγή κωδικού πρόσβασης

### Doctors (Γιατροί)

- **GET /api/doctors** - Λίστα γιατρών
- **GET /api/doctors/:id** - Λεπτομέρειες γιατρού
- **POST /api/doctors** - Δημιουργία γιατρού
- **PATCH /api/doctors/:id** - Ενημέρωση γιατρού
- **DELETE /api/doctors/:id** - Διαγραφή γιατρού

### Patients (Ασθενείς)

- **GET /api/patients** - Λίστα ασθενών (μόνο για τον συνδεδεμένο γιατρό)
- **GET /api/patients/:id** - Λεπτομέρειες ασθενή
- **POST /api/patients** - Προσθήκη ασθενή
- **PATCH /api/patients/:id** - Ενημέρωση ασθενή
- **DELETE /api/patients/:id** - Διαγραφή ασθενή

### Sessions (Συνεδρίες)

- **GET /api/sessions** - Λίστα συνεδριών
- **GET /api/sessions/:id** - Λεπτομέρειες συνεδρίας
- **POST /api/sessions** - Προσθήκη συνεδρίας
  - Δέχεται JSON data για κανονικές συνεδρίες
  - Δέχεται multipart/form-data για ανέβασμα αρχείων
- **PATCH /api/sessions/:id** - Ενημέρωση συνεδρίας
- **DELETE /api/sessions/:id** - Διαγραφή συνεδρίας

### Βοηθητικά

- **GET /api/health** - Έλεγχος λειτουργίας του server
- **GET /uploads/:patient_id/:filename** - Πρόσβαση σε ανεβασμένα αρχεία

## Ασφάλεια

- Όλα τα endpoints (εκτός από login) απαιτούν JWT token για πρόσβαση
- Κάθε γιατρός έχει πρόσβαση μόνο στους δικούς του ασθενείς και τις δικές του συνεδρίες
- Οι κωδικοί πρόσβασης αποθηκεύονται με bcrypt hashing 