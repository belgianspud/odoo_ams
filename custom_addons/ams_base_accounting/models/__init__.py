# -*- coding: utf-8 -*-

# Import in strict dependency order to avoid circular imports
# Base models with no internal dependencies first
from . import res_company

# Core accounting models with minimal cross-references
from . import account_account
from . import account_journal

# Transaction models - import lines before moves
from . import account_move_line
from . import account_move

# Revenue recognition models
from . import revenue_recognition

# Integration models (depend on others)
from . import ams_subscription_accounting

# Product extensions (depend on account models)
from . import product_template