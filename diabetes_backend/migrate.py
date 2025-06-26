#!/usr/bin/env python3
"""
Script για τη μετάβαση στη νέα δομή του backend με Blueprints.
Δημιουργεί αντίγραφα ασφαλείας και μετακινεί τα αρχεία.
"""

import os
import shutil
import sys

def confirm_action(message):
    """Ζητά επιβεβαίωση από το χρήστη."""
    response = input(f"{message} (y/n): ").strip().lower()
    return response == 'y'

def main():
    print("=== Diabetes Backend Μετάβαση σε Blueprints ===")
    
    # Έλεγχος αν τρέχουμε στο σωστό φάκελο
    if not os.path.exists('app.py'):
        print("Σφάλμα: Το script πρέπει να τρέξει στον κύριο φάκελο του diabetes_backend (όπου υπάρχει το app.py)")
        sys.exit(1)
    
    # Έλεγχος αν έχουν δημιουργηθεί τα νέα αρχεία
    required_files = ['app.py.new', 'routes/auth.py', 'routes/doctors.py', 'routes/patients.py', 
                      'routes/sessions.py', 'utils/db.py', 'config/config.py']
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print("Σφάλμα: Τα παρακάτω απαιτούμενα αρχεία λείπουν:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nΠαρακαλώ δημιουργήστε πρώτα όλα τα απαιτούμενα αρχεία.")
        sys.exit(1)
    
    # Ενημέρωση
    print("\nΑυτό το script θα κάνει τα εξής:")
    print("1. Θα δημιουργήσει αντίγραφο ασφαλείας του αρχικού app.py ως app.py.bak")
    print("2. Θα μετονομάσει το app.py.new σε app.py")
    print("3. Θα μεταφέρει τις εξαρτήσεις (.env αρχείο) στο σωστό φάκελο")
    
    if not confirm_action("\nΘέλετε να συνεχίσετε;"):
        print("Η διαδικασία ακυρώθηκε.")
        sys.exit(0)
    
    try:
        # 1. Δημιουργία αντιγράφου ασφαλείας
        print("\nΔημιουργία αντιγράφου ασφαλείας...")
        shutil.copy2('app.py', 'app.py.bak')
        print("✓ Αντίγραφο ασφαλείας δημιουργήθηκε: app.py.bak")
        
        # 2. Μετονομασία του νέου αρχείου
        print("\nΜετονομασία του νέου app.py...")
        if os.path.exists('app.py'):
            os.remove('app.py')
        shutil.copy2('app.py.new', 'app.py')
        print("✓ Το app.py.new μετονομάστηκε σε app.py")
        
        # 3. Έλεγχος και μεταφορά .env αρχείου
        if os.path.exists('.env'):
            if not os.path.exists('.env.bak'):
                shutil.copy2('.env', '.env.bak')
                print("✓ Αντίγραφο του .env δημιουργήθηκε ως .env.bak")
        else:
            print("! Προειδοποίηση: Δεν βρέθηκε .env αρχείο. Παρακαλώ δημιουργήστε ένα.")
        
        print("\nΗ μετάβαση ολοκληρώθηκε επιτυχώς!")
        print("\nΓια να τρέξετε το νέο backend:")
        print("  1. Ενεργοποιήστε το virtual environment: .\\venv\\Scripts\\activate")
        print("  2. Τρέξτε: python app.py")
        
    except Exception as e:
        print(f"\nΣφάλμα κατά τη μετάβαση: {e}")
        print("Η διαδικασία διακόπηκε. Παρακαλώ επιλύστε το πρόβλημα και προσπαθήστε ξανά.")
        sys.exit(1)

if __name__ == "__main__":
    main() 