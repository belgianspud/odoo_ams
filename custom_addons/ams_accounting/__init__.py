print("=== DEBUG: ams_accounting module loading started ===")
try:
    from . import models
    print("=== DEBUG: ams_accounting models imported successfully ===")
except Exception as e:
    print(f"=== DEBUG: Error importing models: {e} ===")