# Copyright 2016 LasLabs Inc.
# Copyright 2018-2020 Onestein (<http://www.onestein.eu>)
# Copyright 2023 Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    @api.model
    def get_views(self, views, options=None):
        ret_val = super().get_views(views, options)

        form_view = self.env["ir.ui.view"].browse(ret_val["views"]["form"]["id"])
        if not form_view.xml_id == "base.res_config_settings_view_form":
            return ret_val

        doc = etree.XML(ret_val["views"]["form"]["arch"])

        # Dynamic enterprise widget detection patterns
        enterprise_patterns = [
            "//setting[field[@widget='upgrade_boolean']]",        # Settings with upgrade widgets
            "//field[@widget='upgrade_boolean']",                 # Direct upgrade boolean fields
            "//widget[@name='iap_buy_more_credits']",             # IAP credit purchase widgets
        ]

        # Build dynamic patterns for enterprise module fields based on naming patterns
        enterprise_module_patterns = [
            '_enterprise',      # Modules ending with _enterprise
            'studio',           # Studio modules
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

        # Add dynamic XPath patterns for module fields
        for pattern in enterprise_module_patterns:
            # Handle different naming conventions
            enterprise_patterns.extend([
                f"//field[@name='module_{pattern}']",
                f"//field[contains(@name, '{pattern}')]",
            ])

        elements_hidden = 0
        for pattern in enterprise_patterns:
            for item in doc.xpath(pattern):
                # For widgets, hide the parent setting if possible
                if item.tag == 'widget':
                    parent_setting = item.xpath("ancestor::setting")
                    if parent_setting:
                        parent_setting[0].attrib["class"] = "d-none"
                        elements_hidden += 1
                    else:
                        item.attrib["class"] = "d-none"
                        elements_hidden += 1
                else:
                    item.attrib["class"] = "d-none"
                    elements_hidden += 1

        # Clean up empty blocks (existing logic)
        for block in doc.xpath("//block"):
            if (
                len(
                    block.xpath(
                        """setting[
                            not(contains(@class, 'd-none'))
                            and not(@invisible='1')]
                        """
                    )
                )
                == 0
            ):
                # Removing title and tip so that no empty h2 or h3 are displayed
                block.attrib.pop("title", None)
                block.attrib.pop("tip", None)
                block.attrib["class"] = "d-none"

        if elements_hidden > 0:
            _logger.info(f"remove_odoo_enterprise: Hidden {elements_hidden} enterprise elements")

        ret_val["views"]["form"]["arch"] = etree.tostring(doc)
        return ret_val

    @api.model
    def _get_classified_fields(self, fnames=None):
        """Override to filter enterprise modules from classification"""
        result = super()._get_classified_fields(fnames)

        # Dynamic filtering of enterprise modules from classification
        if 'module' in result:
            def is_enterprise_module(module):
                """Dynamic detection of enterprise modules for classification filtering"""

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

                # 3. In-App Purchase modules
                if hasattr(module, 'has_iap') and module.has_iap:
                    return True

                # 4. Dynamic name pattern detection
                enterprise_patterns = [
                    '_enterprise', 'studio', 'helpdesk', 'planning', 'documents',
                    'sign', 'voip', 'quality', 'mrp_plm', 'timesheet_grid',
                    'social', 'marketing_automation', 'hr_appraisal',
                    'sale_subscription', 'stock_barcode', 'web_mobile',
                    'accountant', 'knowledge', 'mrp_workorder', 'sale_amazon',
                    'account_inter_company', 'partner_autocomplete', 'iap'
                ]

                module_name = module.name.lower()
                if any(pattern in module_name for pattern in enterprise_patterns):
                    return True

                return False

            # Apply dynamic filtering
            original_count = len(result['module'])
            result['module'] = result['module'].filtered(lambda m: not is_enterprise_module(m))
            filtered_count = original_count - len(result['module'])

            if filtered_count > 0:
                _logger.info(f"remove_odoo_enterprise: Filtered {filtered_count} enterprise modules from settings classification")

        return result
