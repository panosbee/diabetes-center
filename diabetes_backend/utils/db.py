from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging
from config.config import MONGO_URI, DATABASE_NAME

# Ρύθμιση logger
logger = logging.getLogger(__name__)

# Μεταβλητή που θα περιέχει το αντικείμενο της βάσης δεδομένων
db = None

def init_db():
    """
    Αρχικοποίηση της σύνδεσης με τη βάση δεδομένων MongoDB.
    
    Returns:
        db: Το αντικείμενο της βάσης δεδομένων ή None σε περίπτωση αποτυχίας.
    """
    global db
    
    try:
        client = MongoClient(MONGO_URI)
        # Έλεγχος σύνδεσης
        client.admin.command('ismaster')
        db = client[DATABASE_NAME]
        logger.info("MongoDB connection successful.")
        
        # Δημιουργία συλλογών εάν δεν υπάρχουν
        _ensure_collections_exist(db)
        
        # Δημιουργία indexes
        _create_indexes(db)
        
        # Δημιουργία unique index για το ΑΜΚΑ των ασθενών
        db.patients.create_index([("personal_details.amka", 1)], unique=True)
        logger.info("Ensured unique index exists for 'personal_details.amka' in 'patients' collection.")
        
        # Ενημέρωση των ασθενών: προσθήκη του πεδίου is_in_common_space αν δεν υπάρχει
        db.patients.update_many(
            {"is_in_common_space": {"$exists": False}},
            {"$set": {"is_in_common_space": False}}
        )
        
        return db
    except ConnectionFailure as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        db = None
        return None
    except Exception as e:
        logger.error(f"Unexpected error initializing database: {e}")
        db = None
        return None

def _ensure_collections_exist(db):
    """
    Δημιουργία των απαραίτητων συλλογών εάν δεν υπάρχουν.
    """
    collections = ['patients', 'doctors', 'sessions', 'calendar_events', 'genetic_data']
    existing_collections = db.list_collection_names()
    
    for collection in collections:
        if collection not in existing_collections:
            db.create_collection(collection)
            logger.info(f"Created '{collection}' collection.")

def _create_indexes(db):
    """
    Δημιουργία των απαραίτητων indexes στη βάση.
    """
    try:
        db.patients.create_index([("personal_details.amka", 1)], unique=True)
        logger.info("Ensured unique index exists for 'personal_details.amka' in 'patients' collection.")
        
        # Create index for genetic data references
        db.genetic_data.create_index([("patient_id", 1)], unique=True)
        logger.info("Ensured index exists for 'patient_id' in 'genetic_data' collection.")
    except Exception as index_err:
        # Αν υπάρχει ήδη, αγνοούμε το λάθος
        if "index already exists" not in str(index_err).lower():
            logger.warning(f"Could not create unique index for AMKA: {index_err}")

def get_db():
    """
    Επιστρέφει το αντικείμενο της βάσης δεδομένων.
    
    Returns:
        db: Το αντικείμενο της βάσης ή None αν δεν έχει αρχικοποιηθεί.
    """
    global db
    if db is None:
        db = init_db()
    return db 