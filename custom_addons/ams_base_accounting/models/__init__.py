# -*- coding: utf-8 -*-

# Import in very careful order to avoid circular dependencies
# Start with models that have no internal dependencies

# Company extensions first (no deps on AMS models)
from . import res_company

# Basic models with minimal cross-references
from . import account_account

# Journal model (depends on account_account for default account)
from . import account_journal

# Move line model (depends on account_account and account_journal)
from . import account_move_line

# Move model (depends on account_journal and account_move_line)
from . import account_move

# Revenue recognition models (depend on account_move)
from . import revenue_recognition

# Check if subscription model already exists before loading stub
try:
    import odoo
    if 'ams.subscription' not in odoo.registry().get('ams.subscription', {}):
        # Only load stub if real subscription model doesn't exist
        from . import ams_subscription_stub
except:
    # Load stub as fallback
    from . import ams_subscription_stub

# Integration models (depend on subscription and accounting models)
from . import ams_subscription_accounting

# Product extensions (depend on account models)
from . import product_template