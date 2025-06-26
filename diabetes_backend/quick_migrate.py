#!/usr/bin/env python3
"""
Απλό script για τη μετάβαση στη νέα δομή του backend χωρίς επιβεβαίωση.
"""

import os
import shutil
import sys

def main():
    print("=== Γρήγορη Μετάβαση σε Blueprints ===")
    
    # Έλεγχος αν τρέχουμε στο σωστό φάκελο
    if not os.path.exists('app.py'):
        print("Σφάλμα: Το script πρέπει να τρέξει στον κύριο φάκελο του diabetes_backend")
        sys.exit(1)
    
    try:
        # 1. Δημιουργία αντιγράφου ασφαλείας
        print("Δημιουργία αντιγράφου ασφαλείας...")
        shutil.copy2('app.py', 'app.py.bak')
        print("✓ Αντίγραφο ασφαλείας δημιουργήθηκε: app.py.bak")
        
        # 2. Μετονομασία του νέου αρχείου
        print("Μετονομασία του νέου app.py...")
        if os.path.exists('app.py'):
            os.remove('app.py')
        shutil.copy2('app.py.new', 'app.py')
        print("✓ Το app.py.new μετονομάστηκε σε app.py")
        
        print("Η μετάβαση ολοκληρώθηκε επιτυχώς!")
        
    except Exception as e:
        print(f"Σφάλμα κατά τη μετάβαση: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 