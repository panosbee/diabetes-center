"""
Module για τη διαχείριση δικαιωμάτων και εξουσιοδοτήσεων με χρήση της Flask-Principal.
Περιλαμβάνει ορισμούς ρόλων, αντικείμενα δικαιωμάτων και βοηθητικές συναρτήσεις.
"""

from flask import g, current_app, jsonify
from flask_principal import Identity, Permission, RoleNeed, UserNeed, ActionNeed
from bson.objectid import ObjectId
import logging

# Ρύθμιση του logger
logger = logging.getLogger(__name__)

# Ορισμός βασικών ρόλων/αναγκών
admin_role = RoleNeed('admin')
doctor_role = RoleNeed('doctor')
primary_doctor_role = RoleNeed('primary_doctor')
assistant_doctor_role = RoleNeed('assistant_doctor')
patient_role = RoleNeed('patient')

# Ορισμός βασικών ενεργειών
view_action = ActionNeed('view')
edit_action = ActionNeed('edit')
delete_action = ActionNeed('delete')
add_action = ActionNeed('add')

# Κλάσεις Δικαιωμάτων
class ViewAllPermission(Permission):
    """Δικαίωμα προβολής όλων των πόρων"""
    def __init__(self):
        needs = [admin_role, primary_doctor_role]
        super(ViewAllPermission, self).__init__(*needs)

class ViewPatientPermission(Permission):
    """Δικαίωμα προβολής συγκεκριμένου ασθενή"""
    def __init__(self, patient_id=None):
        # Βασικά δικαιώματα: admin
        needs = [admin_role]
        super(ViewPatientPermission, self).__init__(*needs)
        self.patient_id = patient_id
        
    def can(self):
        """Έλεγχος αν ο χρήστης έχει δικαίωμα προβολής του συγκεκριμένου ασθενή"""
        # Admin έχει πάντα δικαίωμα
        if super(ViewPatientPermission, self).can():
            return True
            
        # Αν δεν έχουμε ID ασθενή, επιτρέπουμε προβολή (για λίστες)
        if not self.patient_id:
            return True
            
        # Αν δεν υπάρχει identity στο request context, δεν έχουμε δικαίωμα
        if not hasattr(g, 'identity'):
            return False
            
        try:
            # Λήψη του ασθενή από τη βάση
            from utils.db import get_db
            db = get_db()
            patient = db.patients.find_one({"_id": ObjectId(self.patient_id)})
            
            if not patient:
                return False
                
            # Έλεγχος αν ο γιατρός είναι ανατεθειμένος στον ασθενή
            doctor_id = g.identity.id
            if 'assigned_doctors' in patient:
                assigned_doctors = [str(doc_id) for doc_id in patient['assigned_doctors']]
                if str(doctor_id) in assigned_doctors:
                    return True
                    
            # Έλεγχος αν είναι στον common space (μπορούν να βλέπουν όλοι)
            if patient.get('is_in_common_space', False):
                return True
                    
            return False
        except Exception as e:
            logger.error(f"Error checking ViewPatientPermission: {e}")
            return False

class EditPatientPermission(Permission):
    """Δικαίωμα επεξεργασίας συγκεκριμένου ασθενή"""
    def __init__(self, patient_id=None):
        # Βασικά δικαιώματα: admin
        needs = [admin_role]
        super(EditPatientPermission, self).__init__(*needs)
        self.patient_id = patient_id
        
    def can(self):
        """Έλεγχος αν ο χρήστης έχει δικαίωμα επεξεργασίας του συγκεκριμένου ασθενή"""
        # Admin έχει πάντα δικαίωμα
        if super(EditPatientPermission, self).can():
            return True
            
        # Αν δεν έχουμε ID ασθενή, δεν μπορούμε να κάνουμε έλεγχο
        if not self.patient_id:
            return False
            
        # Αν δεν υπάρχει identity στο request context, δεν έχουμε δικαίωμα
        if not hasattr(g, 'identity'):
            return False
            
        try:
            # Λήψη του ασθενή από τη βάση
            from utils.db import get_db
            db = get_db()
            patient = db.patients.find_one({"_id": ObjectId(self.patient_id)})
            
            if not patient:
                return False
                
            # Έλεγχος αν είναι στον common space
            if patient.get('is_in_common_space', False):
                return True
                
            # Έλεγχος αν ο γιατρός είναι ανατεθειμένος στον ασθενή
            doctor_id = g.identity.id
            if 'assigned_doctors' in patient:
                assigned_doctors = [str(doc_id) for doc_id in patient['assigned_doctors']]
                if str(doctor_id) in assigned_doctors:
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Error checking EditPatientPermission: {e}")
            return False

class DeletePatientPermission(Permission):
    """Δικαίωμα διαγραφής συγκεκριμένου ασθενή"""
    def __init__(self, patient_id=None):
        # Μόνο admin και ο κύριος γιατρός μπορεί να διαγράψει
        needs = [admin_role, primary_doctor_role]
        super(DeletePatientPermission, self).__init__(*needs)
        self.patient_id = patient_id
        
    def can(self):
        """Έλεγχος αν ο χρήστης έχει δικαίωμα διαγραφής του συγκεκριμένου ασθενή"""
        # Admin έχει πάντα δικαίωμα
        if super(DeletePatientPermission, self).can():
            return True
            
        # Αν δεν έχουμε ID ασθενή, δεν μπορούμε να κάνουμε έλεγχο
        if not self.patient_id:
            return False
            
        # Αν δεν υπάρχει identity στο request context, δεν έχουμε δικαίωμα
        if not hasattr(g, 'identity'):
            return False
            
        try:
            # Λήψη του ασθενή από τη βάση
            from utils.db import get_db
            db = get_db()
            patient = db.patients.find_one({"_id": ObjectId(self.patient_id)})
            
            if not patient:
                return False
                
            # Έλεγχος αν ο γιατρός είναι ανατεθειμένος στον ασθενή
            doctor_id = g.identity.id
            if 'assigned_doctors' in patient:
                assigned_doctors = [str(doc_id) for doc_id in patient['assigned_doctors']]
                if str(doctor_id) in assigned_doctors:
                    # Αν ο γιατρός έχει ρόλο primary_doctor
                    return primary_doctor_role in g.identity.provides
                    
            return False
        except Exception as e:
            logger.error(f"Error checking DeletePatientPermission: {e}")
            return False

class EditDoctorPermission(Permission):
    """Δικαίωμα επεξεργασίας συγκεκριμένου γιατρού"""
    def __init__(self, doctor_id=None):
        # Μόνο admin μπορεί να επεξεργαστεί άλλους γιατρούς
        needs = [admin_role]
        super(EditDoctorPermission, self).__init__(*needs)
        self.doctor_id = doctor_id
        
    def can(self):
        """Έλεγχος αν ο χρήστης έχει δικαίωμα επεξεργασίας του συγκεκριμένου γιατρού"""
        # Admin έχει πάντα δικαίωμα
        if super(EditDoctorPermission, self).can():
            return True
            
        # Αν δεν έχουμε ID γιατρού, δεν μπορούμε να κάνουμε έλεγχο
        if not self.doctor_id:
            return False
            
        # Αν δεν υπάρχει identity στο request context, δεν έχουμε δικαίωμα
        if not hasattr(g, 'identity'):
            return False
            
        # Ένας γιατρός μπορεί πάντα να επεξεργαστεί τον εαυτό του
        return str(g.identity.id) == str(self.doctor_id)

class EditSessionPermission(Permission):
    """Δικαίωμα επεξεργασίας συγκεκριμένης συνεδρίας"""
    def __init__(self, session_id=None):
        # Βασικά δικαιώματα: admin
        needs = [admin_role]
        super(EditSessionPermission, self).__init__(*needs)
        self.session_id = session_id
        
    def can(self):
        """Έλεγχος αν ο χρήστης έχει δικαίωμα επεξεργασίας της συγκεκριμένης συνεδρίας"""
        # Admin έχει πάντα δικαίωμα
        if super(EditSessionPermission, self).can():
            return True
            
        # Αν δεν έχουμε ID συνεδρίας, δεν μπορούμε να κάνουμε έλεγχο
        if not self.session_id:
            return False
            
        # Αν δεν υπάρχει identity στο request context, δεν έχουμε δικαίωμα
        if not hasattr(g, 'identity'):
            return False
            
        try:
            # Λήψη της συνεδρίας από τη βάση
            from utils.db import get_db
            db = get_db()
            session = db.sessions.find_one({"_id": ObjectId(self.session_id)})
            
            if not session:
                return False
                
            # Έλεγχος αν ο γιατρός δημιούργησε τη συνεδρία
            doctor_id = g.identity.id
            if 'doctor_id' in session:
                if str(doctor_id) == str(session['doctor_id']):
                    return True
                    
            # Έλεγχος αν ο γιατρός είναι ανατεθειμένος στον ασθενή της συνεδρίας
            if 'patient_id' in session:
                patient = db.patients.find_one({"_id": ObjectId(session['patient_id'])})
                if patient and 'assigned_doctors' in patient:
                    assigned_doctors = [str(doc_id) for doc_id in patient['assigned_doctors']]
                    if str(doctor_id) in assigned_doctors:
                        return True
                    
            return False
        except Exception as e:
            logger.error(f"Error checking EditSessionPermission: {e}")
            return False

class EditFilePermission(Permission):
    """Δικαίωμα επεξεργασίας/διαγραφής συγκεκριμένου αρχείου"""
    def __init__(self, patient_id=None, file_id=None):
        # Βασικά δικαιώματα: admin
        needs = [admin_role]
        super(EditFilePermission, self).__init__(*needs)
        self.patient_id = patient_id
        self.file_id = file_id
        
    def can(self):
        """Έλεγχος αν ο χρήστης έχει δικαίωμα επεξεργασίας του συγκεκριμένου αρχείου"""
        # Admin έχει πάντα δικαίωμα
        if super(EditFilePermission, self).can():
            return True
            
        # Έλεγχος δικαιωμάτων για τον ασθενή στον οποίο ανήκει το αρχείο
        # Χρησιμοποιούμε το EditPatientPermission για να επαναχρησιμοποιήσουμε τη λογική
        edit_patient_perm = EditPatientPermission(self.patient_id)
        return edit_patient_perm.can()

# Βοηθητικές συναρτήσεις
def on_identity_loaded(identity):
    """
    Φορτώνει τα δικαιώματα ενός χρήστη/γιατρού στο identity του.
    Καλείται όταν δημιουργείται ή φορτώνεται ένα identity.
    """
    from utils.db import get_db
    db = get_db()
    
    # Αποθήκευση του ID του χρήστη
    identity.provides.add(UserNeed(str(identity.id)))
    
    try:
        # Έλεγχος αν είναι γιατρός
        doctor = db.doctors.find_one({"_id": ObjectId(identity.id)})
        if doctor:
            # Προσθήκη του βασικού ρόλου γιατρού
            identity.provides.add(doctor_role)
            
            # Προσθήκη του ειδικού ρόλου βάσει του role του γιατρού
            doctor_type = doctor.get('role', 'assistant')  # Default: assistant
            if doctor_type == 'admin':
                identity.provides.add(admin_role)
            elif doctor_type == 'primary':
                identity.provides.add(primary_doctor_role)
            else:  # assistant
                identity.provides.add(assistant_doctor_role)
                
            # Προσθήκη δικαιωμάτων για τους ασθενείς του
            for patient_id in doctor.get('managed_patients', []):
                identity.provides.add(UserNeed(str(patient_id)))
                
        # Έλεγχος αν είναι ασθενής
        else:
            patient = db.patients.find_one({"_id": ObjectId(identity.id)})
            if patient:
                identity.provides.add(patient_role)
                
    except Exception as e:
        logger.error(f"Error loading identity permissions: {e}")
        
def permission_denied(message="Δεν έχετε δικαίωμα πρόσβασης σε αυτόν τον πόρο"):
    """Επιστρέφει τυποποιημένη απάντηση για άρνηση πρόσβασης"""
    return jsonify({"error": message}), 403

def initialize_permissions(app, jwt):
    """
    Αρχικοποιεί το σύστημα δικαιωμάτων και συνδέει το με το JWT.
    
    Args:
        app: Το Flask app instance
        jwt: Το Flask-JWT-Extended instance
    """
    from flask_principal import Principal, identity_loaded
    
    # Αρχικοποίηση του Principal
    principal = Principal(app)
    
    # Σύνδεση με το identity_loaded event
    @identity_loaded.connect_via(app)
    def on_identity_loaded_callback(sender, identity):
        on_identity_loaded(identity)
        
    # Σύνδεση με το JWT για αυτόματο φόρτωμα του Identity μετά από επιτυχή αυθεντικοποίηση
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        from utils.db import get_db
        db = get_db()
        
        # Έλεγχος αν είναι γιατρός
        doctor = db.doctors.find_one({"_id": ObjectId(identity)})
        if doctor:
            return doctor
            
        # Έλεγχος αν είναι ασθενής
        patient = db.patients.find_one({"_id": ObjectId(identity)})
        if patient:
            return patient
            
        return None
        
    @app.before_request
    def before_request():
        # Δημιουργία identity για τον τρέχοντα χρήστη αν υπάρχει JWT
        from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
        from flask import request
        
        # Εξαίρεση για options requests και δημόσια endpoints
        if request.method == 'OPTIONS':
            return None
            
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            
            if current_user_id:
                # Δημιουργία identity
                identity = Identity(current_user_id)
                on_identity_loaded(identity)
                g.identity = identity
        except Exception as e:
            # Σε περίπτωση σφάλματος, απλά συνεχίζουμε χωρίς identity
            logger.debug(f"No valid JWT found: {e}")
            pass
            
    return principal 