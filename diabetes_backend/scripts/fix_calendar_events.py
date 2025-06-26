#!/usr/bin/env python3
"""
Script για να διορθώσει παλιά calendar events που μπορεί να μην έχουν σωστό targeting.

ΠΡΟΒΛΗΜΑ: Παλιά events που δημιουργήθηκαν από γιατρούς χωρίς επιλογή ασθενή
εμφανίζονται σε όλους τους ασθενείς αντί να είναι private του γιατρού.

ΔΙΟΡΘΩΣΗ: Αλλάζει τα events που έχουν:
- creator_id = γιατρός 
- user_id = γιατρός (ίδιος με creator)  
- event_type != 'personal_task' (μόνο personal tasks είναι για τον γιατρό)
- visibility != 'private'

σε:
- visibility = 'private'
- editable_by = 'owner'
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_db
from bson.objectid import ObjectId
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to fix calendar events targeting."""
    logger.info("Starting calendar events cleanup script...")
    
    db = get_db()
    if not db:
        logger.error("Failed to connect to database")
        return
        
    # Find problematic events
    query = {
        "$expr": {
            "$and": [
                {"$eq": ["$creator_id", "$user_id"]},  # creator = user (γιατρός δημιούργησε για τον εαυτό του)
                {"$ne": ["$event_type", "personal_task"]},     # μόνο personal tasks είναι για τον γιατρό
                {"$ne": ["$visibility", "private"]}           # δεν είναι ήδη private
            ]
        }
    }
    
    logger.info(f"Searching for problematic events with query: {query}")
    
    # Get all doctors to validate creator_id
    doctors = list(db.doctors.find({}, {"_id": 1}))
    doctor_ids = [doc["_id"] for doc in doctors]
    
    logger.info(f"Found {len(doctor_ids)} doctors in system")
    
    # Add doctor validation to query
    query["creator_id"] = {"$in": doctor_ids}
    
    # Find events to fix
    events_to_fix = list(db.calendar_events.find(query))
    
    logger.info(f"Found {len(events_to_fix)} events that need fixing")
    
    if len(events_to_fix) == 0:
        logger.info("No events need fixing. Exiting.")
        return
        
    # Show sample events before fixing
    logger.info("Sample events to be fixed:")
    for i, event in enumerate(events_to_fix[:3]):  # Show first 3 as sample
        logger.info(f"  {i+1}. ID: {event['_id']}, Type: {event.get('event_type')}, "
                   f"Title: {event.get('title')}, Visibility: {event.get('visibility')}")
    
    # Ask for confirmation
    if len(events_to_fix) > 0:
        response = input(f"\nProceed to fix {len(events_to_fix)} events? (y/N): ")
        if response.lower() != 'y':
            logger.info("Cancelled by user")
            return
    
    # Fix the events
    fixed_count = 0
    for event in events_to_fix:
        try:
            result = db.calendar_events.update_one(
                {"_id": event["_id"]},
                {
                    "$set": {
                        "visibility": "private",
                        "editable_by": "owner"
                    }
                }
            )
            
            if result.modified_count > 0:
                fixed_count += 1
                logger.info(f"Fixed event {event['_id']}: {event.get('title')}")
            else:
                logger.warning(f"Failed to update event {event['_id']}")
                
        except Exception as e:
            logger.error(f"Error fixing event {event['_id']}: {e}")
    
    logger.info(f"Cleanup completed. Fixed {fixed_count} out of {len(events_to_fix)} events.")
    
    # Verify the fix
    remaining_problematic = db.calendar_events.count_documents(query)
    logger.info(f"Remaining problematic events after fix: {remaining_problematic}")

if __name__ == "__main__":
    main()
