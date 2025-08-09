# -*- coding: utf-8 -*-

# Load revenue recognition models first to avoid circular dependencies
from . import ams_revenue_recognition
from . import ams_revenue_schedule

# Then load extension models
from . import product_template
from . import ams_subscription  
from . import account_move