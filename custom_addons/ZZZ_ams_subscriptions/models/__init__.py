# Import order is important! Base models first, then dependent models
from . import ams_subscription_tier       # No dependencies
from . import ams_subscription           # Depends on tier
from . import ams_subscription_seat      # Depends on subscription
from . import ams_subscription_modification  # Depends on subscription
from . import ams_payment_history        # Depends on subscription
from . import ams_lifecycle_settings     # Depends on tier
from . import product_template           # Enhances existing model
from . import sale_order                 # Enhances existing model  
from . import res_partner                # Enhances existing model