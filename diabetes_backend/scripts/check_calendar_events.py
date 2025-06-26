#!/usr/bin/env python3
"""
Script για έλεγχο των calendar events και εντοπισμό προβλημάτων targeting.

Αυτό το script ΜΟΝΟ ελέγχει και εμφανίζει στατιστικά, δεν κάνει αλλαγές.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_db
from bson.objectid import ObjectId
import logging
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to analyze calendar events."""
    logger.info("Starting calendar events analysis...")
    
    db = get_db()
    if not db:
        logger.error("Failed to connect to database")
        return
        
    # Get basic stats
    total_events = db.calendar_events.count_documents({})
    logger.info(f"Total calendar events: {total_events}")
    
    # Get all doctors and patients for validation
    doctors = list(db.doctors.find({}, {"_id": 1, "personal_details.first_name": 1, "personal_details.last_name": 1}))
    patients = list(db.patients.find({}, {"_id": 1, "personal_details.first_name": 1, "personal_details.last_name": 1}))
    
    doctor_ids = {doc["_id"]: f"{doc.get('personal_details', {}).get('first_name', '')} {doc.get('personal_details', {}).get('last_name', '')}" for doc in doctors}
    patient_ids = {pat["_id"]: f"{pat.get('personal_details', {}).get('first_name', '')} {pat.get('personal_details', {}).get('last_name', '')}" for pat in patients}
    
    logger.info(f"Found {len(doctor_ids)} doctors and {len(patient_ids)} patients")
    
    # Analyze events by type and visibility
    event_stats = defaultdict(lambda: defaultdict(int))
    visibility_stats = defaultdict(int)
    
    all_events = list(db.calendar_events.find({}))
    
    for event in all_events:
        event_type = event.get('event_type', 'unknown')
        visibility = event.get('visibility', 'none')
        creator_id = event.get('creator_id')
        user_id = event.get('user_id')
        
        event_stats[event_type][visibility] += 1
        visibility_stats[visibility] += 1
        
    logger.info("\n=== EVENT STATISTICS BY TYPE AND VISIBILITY ===")
    for event_type, vis_counts in event_stats.items():
        logger.info(f"{event_type}:")
        for visibility, count in vis_counts.items():
            logger.info(f"  {visibility}: {count}")
    
    logger.info(f"\n=== OVERALL VISIBILITY STATS ===")
    for visibility, count in visibility_stats.items():
        logger.info(f"{visibility}: {count}")
    
    # Find problematic events (same logic as fix script)
    problematic_query = {
        "$expr": {
            "$and": [
                {"$eq": ["$creator_id", "$user_id"]},  # creator = user 
                {"$ne": ["$event_type", "appointment_slot"]},  # όχι slots
                {"$ne": ["$event_type", "personal_task"]},     # όχι personal tasks
                {"$ne": ["$visibility", "private"]}           # δεν είναι ήδη private
            ]
        },
        "creator_id": {"$in": list(doctor_ids.keys())}  # created by doctor
    }
    
    problematic_events = list(db.calendar_events.find(problematic_query))
    
    logger.info(f"\n=== PROBLEMATIC EVENTS ANALYSIS ===")
    logger.info(f"Found {len(problematic_events)} potentially problematic events")
    
    if len(problematic_events) > 0:
        logger.info("Sample problematic events:")
        for i, event in enumerate(problematic_events[:5]):
            creator_name = doctor_ids.get(event.get('creator_id'), 'Unknown')
            user_name = doctor_ids.get(event.get('user_id')) or patient_ids.get(event.get('user_id'), 'Unknown')
            
            logger.info(f"  {i+1}. ID: {event['_id']}")
            logger.info(f"     Title: {event.get('title')}")
            logger.info(f"     Type: {event.get('event_type')}")
            logger.info(f"     Visibility: {event.get('visibility')}")
            logger.info(f"     Creator: {creator_name}")
            logger.info(f"     User: {user_name}")
            logger.info(f"     Created: {event.get('created_at')}")
    
    # Check for events where creator != user (targeted events)
    targeted_events = list(db.calendar_events.find({
        "$expr": {"$ne": ["$creator_id", "$user_id"]}
    }))
    
    logger.info(f"\n=== TARGETED EVENTS (creator != user) ===")
    logger.info(f"Found {len(targeted_events)} properly targeted events")
    
    # Check for orphaned events (user_id not in doctors or patients)
    all_user_ids = set()
    for event in all_events:
        if event.get('user_id'):
            all_user_ids.add(event.get('user_id'))
    
    valid_ids = set(doctor_ids.keys()) | set(patient_ids.keys())
    orphaned_user_ids = all_user_ids - valid_ids
    
    if orphaned_user_ids:
        logger.info(f"\n=== ORPHANED EVENTS ===")
        logger.info(f"Found events with user_ids not in doctors/patients: {len(orphaned_user_ids)}")
        for orphaned_id in orphaned_user_ids:
            orphaned_events = db.calendar_events.count_documents({"user_id": orphaned_id})
            logger.info(f"  {orphaned_id}: {orphaned_events} events")
    
    logger.info("\nAnalysis completed.")

if __name__ == "__main__":
    main()
