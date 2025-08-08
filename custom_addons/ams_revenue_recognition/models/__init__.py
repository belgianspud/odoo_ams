# -*- coding: utf-8 -*-

# Import models in dependency order
from . import ams_revenue_schedule          # Core model - no dependencies
from . import ams_revenue_recognition       # Depends on schedule
from . import ams_contract_modification     # Depends on schedule and recognition
from . import product_template              # Enhances existing model
from . import ams_subscription              # Enhances existing model
from . import account_move                  # Enhances existing model
from . import ams_revenue_dashboard         # Dashboard/reporting model