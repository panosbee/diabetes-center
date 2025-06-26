"""
Script για την προσθήκη ρόλων στους γιατρούς στη βάση δεδομένων.
"""
import sys
import os
import logging
from pymongo import MongoClient
from bson.objectid import ObjectId

# Προσθήκη του parent directory στο path για να μπορούμε να εισάγουμε τα modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MONGO_URI

# Ρύθμιση logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s : %(message)s'
)
logger = logging.getLogger(__name__)

def connect_to_db():
    """Συνδέεται στη βάση δεδομένων MongoDB."""
    try:
        client = MongoClient(MONGO_URI)
        # Έλεγχος σύνδεσης με ένα ping
        client.admin.command('ping')
        db = client.diabetes_db
        logger.info("MongoDB connection successful.")
        return db
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None

def add_roles_to_doctors(db):
    """Προσθέτει ρόλους στους γιατρούς στη βάση δεδομένων."""
    try:
        doctors = list(db.doctors.find({}))
        logger.info(f"Found {len(doctors)} doctors.")
        
        # Ορισμός ρόλων
        roles = ["admin", "primary", "assistant"]
        
        # Αρχικοποίηση counters
        update_count = 0
        admin_count = 0
        primary_count = 0
        assistant_count = 0
        
        # Ο πρώτος γιατρός γίνεται admin
        if doctors:
            db.doctors.update_one(
                {"_id": doctors[0]["_id"]},
                {"$set": {"role": "admin"}}
            )
            admin_count += 1
            update_count += 1
            logger.info(f"Set doctor {doctors[0].get('username', str(doctors[0]['_id']))} as admin.")
        
        # Για τους υπόλοιπους γιατρούς
        for i, doctor in enumerate(doctors[1:], 1):
            # Αν ο γιατρός έχει ήδη ρόλο, παραλείπουμε
            if "role" in doctor:
                logger.info(f"Doctor {doctor.get('username', str(doctor['_id']))} already has role: {doctor['role']}")
                continue
                
            # Ορισμός ρόλου: κάθε τρίτος primary, οι υπόλοιποι assistant
            role = "primary" if i % 3 == 0 else "assistant"
            
            # Ενημέρωση του γιατρού
            db.doctors.update_one(
                {"_id": doctor["_id"]},
                {"$set": {"role": role}}
            )
            update_count += 1
            
            # Ενημέρωση counters
            if role == "primary":
                primary_count += 1
            elif role == "assistant":
                assistant_count += 1
                
            logger.info(f"Set doctor {doctor.get('username', str(doctor['_id']))} as {role}.")
            
        logger.info(f"Updated {update_count} doctors with roles.")
        logger.info(f"Roles distribution: admin={admin_count}, primary={primary_count}, assistant={assistant_count}")
        
        return update_count
            
    except Exception as e:
        logger.error(f"Error updating doctors with roles: {e}")
        return 0

def main():
    """Κύρια συνάρτηση του script."""
    db = connect_to_db()
    if db is None:
        logger.error("Failed to connect to database.")
        sys.exit(1)
    
    update_count = add_roles_to_doctors(db)
    logger.info(f"Script completed. Updated {update_count} doctors.")

if __name__ == "__main__":
    main() 