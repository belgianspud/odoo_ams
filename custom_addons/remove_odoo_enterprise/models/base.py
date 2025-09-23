# Copyright 2019-2020 Onestein (<https://www.onestein.eu>)
# Copyright 2023 Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        res = super().search_fetch(domain, field_names, offset, limit, order)

        # Dynamic filtering of enterprise modules based on module characteristics
        if self._name == "ir.module.module":
            original_count = len(res)

            # Filter modules based on enterprise characteristics
            def is_enterprise_module(module):
                """Dynamic detection of enterprise modules based on module characteristics"""

                # 0. Exception: Never hide OCA server-brand modules (debranding tools)
                oca_debranding_modules = [
                    'remove_odoo_enterprise',
                    'portal_odoo_debranding',
                    'disable_odoo_online'
                ]
                if module.name in oca_debranding_modules:
                    return False

                # 1. Direct enterprise flag
                if hasattr(module, 'to_buy') and module.to_buy:
                    return True

                # 2. Enterprise licenses
                if hasattr(module, 'license') and module.license in ['OEEL-1', 'OPL-1']:
                    return True

                # 3. In-App Purchase modules (IAP)
                if hasattr(module, 'has_iap') and module.has_iap:
                    return True

                # 4. Module name patterns that indicate enterprise
                enterprise_name_patterns = [
                    '_enterprise',      # Modules ending with _enterprise
                    'studio_',          # Studio customization modules
                    'helpdesk',         # Helpdesk enterprise
                    'planning',         # Planning enterprise
                    'documents',        # Documents enterprise
                    'sign',             # Digital signature
                    'voip',             # VoIP enterprise
                    'quality',          # Quality control
                    'mrp_plm',          # PLM
                    'timesheet_grid',   # Grid timesheet
                    'social',           # Social marketing
                    'marketing_automation', # Marketing automation
                    'hr_appraisal',     # HR appraisal
                    'sale_subscription', # Subscriptions
                    'stock_barcode',    # Barcode
                    'web_mobile',       # Mobile web
                    'accountant',       # Accounting enterprise
                    'knowledge',        # Knowledge management
                    'mrp_workorder',    # MRP workorder
                    'sale_amazon',      # Amazon integration
                ]

                # Check if module name contains enterprise patterns
                module_name_lower = module.name.lower()
                if any(pattern in module_name_lower for pattern in enterprise_name_patterns):
                    return True

                # 5. Category-based detection
                if hasattr(module, 'category_id') and module.category_id:
                    category_name = module.category_id.name.lower()
                    enterprise_category_patterns = [
                        'enterprise',
                        'studio',
                        'industry',
                        'iot',
                        'appointment'
                    ]
                    if any(pattern in category_name for pattern in enterprise_category_patterns):
                        return True

                return False

            # Apply enterprise filtering
            res = res.filtered(lambda m: not is_enterprise_module(m))

            filtered_count = original_count - len(res)
            if filtered_count > 0:
                _logger.info(f"remove_odoo_enterprise: Hidden {filtered_count} enterprise modules from Apps menu")

        elif self._name == "payment.provider":
            original_count = len(res)
            res = res.filtered(lambda a: not a.module_to_buy)
            filtered_count = original_count - len(res)
            if filtered_count > 0:
                _logger.info(f"remove_odoo_enterprise: Filtered {filtered_count} enterprise payment providers")

        return res
