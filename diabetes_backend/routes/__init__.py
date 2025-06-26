""" 
Routes package περιέχει όλα τα Flask Blueprints της εφαρμογής. 
"""

from .auth import auth_bp
from .doctors import doctors_bp
from .patients import patients_bp
from .sessions import sessions_bp
from .files import files_bp
from .doctor_portal import doctor_portal_bp
from .ai import ai_bp
from .patient_portal import patient_portal_bp
from .calendar import calendar_bp

# === SAFE IMPORT για scenarios blueprint ===
scenarios_bp = None
scenarios_import_error = None

try:
    from .scenarios import scenarios_bp
    print("✅ Successfully imported scenarios blueprint")
except ImportError as e:
    print(f"⚠️ Could not import scenarios blueprint: {e}")
    print("This is normal if digital_twin_engine.py doesn't exist yet")
    scenarios_import_error = str(e)
except Exception as e:
    print(f"❌ Unexpected error importing scenarios blueprint: {e}")
    scenarios_import_error = str(e)

# === DYNAMIC BLUEPRINTS LIST ===
# Βασικά blueprints που υπάρχουν πάντα
base_blueprints = [
    auth_bp,
    doctors_bp,
    patients_bp,
    sessions_bp,
    files_bp,
    doctor_portal_bp,
    ai_bp,
    patient_portal_bp,
    calendar_bp,
]

# Προσθήκη scenarios blueprint αν είναι διαθέσιμο
all_blueprints = base_blueprints.copy()

if scenarios_bp is not None:
    all_blueprints.append(scenarios_bp)
    print(f"📋 Added scenarios blueprint to all_blueprints. Total: {len(all_blueprints)}")
else:
    print(f"📋 Scenarios blueprint not available. Total blueprints: {len(all_blueprints)}")

# Debug information
blueprint_names = []
for bp in all_blueprints:
    if bp is not None:
        blueprint_names.append(bp.name)
    else:
        blueprint_names.append("None")

print(f"🔍 Available blueprint names: {blueprint_names}")

# === EXPORTS ===
__all__ = [
    'auth_bp', 
    'doctors_bp', 
    'patients_bp', 
    'sessions_bp', 
    'files_bp', 
    'doctor_portal_bp', 
    'ai_bp', 
    'patient_portal_bp', 
    'calendar_bp', 
    'scenarios_bp',  # May be None
    'all_blueprints',
    'scenarios_import_error'
]

# === ΔΙΑΓΝΩΣΤΙΚΗ ΛΕΙΤΟΥΡΓΙΑ ===
def get_blueprint_status():
    """Returns current blueprint registration status"""
    return {
        "base_blueprints_count": len(base_blueprints),
        "total_blueprints_count": len(all_blueprints),
        "scenarios_available": scenarios_bp is not None,
        "scenarios_import_error": scenarios_import_error,
        "blueprint_names": blueprint_names,
        "scenarios_blueprint_name": scenarios_bp.name if scenarios_bp else None
    }

# Print status on import
status = get_blueprint_status()
print(f"📊 Routes package status: {status['total_blueprints_count']} blueprints ready")
if not status['scenarios_available']:
    print(f"⚠️ Scenarios feature unavailable: {status['scenarios_import_error']}")
else:
    print(f"✅ What-If Scenarios feature available as: {status['scenarios_blueprint_name']}")