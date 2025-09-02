# -*- coding: utf-8 -*-

from . import models
from . import wizards

# Optional lifecycle hooks (only add if needed)
def pre_install_hook(env):
    """Pre-installation hook to prepare environment."""
    # Add any pre-installation logic here
    # Example: Check dependencies, prepare data, etc.
    pass

def post_install_hook(env):
    """Post-installation hook to configure module after installation."""
    # Add any post-installation logic here
    # Example: Create default data, configure settings, etc.
    
    # Create default billing periods if they don't exist
    BillingPeriod = env['ams.billing.period']
    if not BillingPeriod.search_count([]):
        # Use the method from the model to create standard periods
        BillingPeriod.create({}).action_create_standard_periods()

def uninstall_hook(env):
    """Uninstallation hook to clean up data."""
    # Add any cleanup logic here
    # Example: Remove custom data, reset configurations, etc.
    pass

def post_load_hook():
    """Post-load hook called after module is loaded."""
    # Add any post-load logic here
    # Example: Register additional functionality, patch methods, etc.
    pass