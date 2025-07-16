from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'
    
    # List of Enterprise modules to hide from Apps menu
    ENTERPRISE_MODULES = [
        'studio', 'quality', 'helpdesk', 'planning', 'sign', 'appointment',
        'hr_recruitment', 'hr_skills', 'hr_attendance', 'hr_timesheet', 
        'hr_expense', 'lunch', 'social', 'repair', 'stock_barcode',
        'marketing_automation', 'voip', 'sms', 'documents', 'website_studio',
        'plm', 'whatsapp', 'iot', 'pos_restaurant_adyen', 'pos_adyen',
        'enterprise_theme', 'web_enterprise', 'mail_enterprise', 'hr_appraisal'
    ]
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """Override search to hide Enterprise promotional cards from Apps menu"""
        # Log when this method is called
        _logger.info("AMS Module Manager: Filtering module search")
        _logger.info(f"Search args: {args}")
        _logger.info(f"Context: {self.env.context}")
        
        # Apply enterprise filtering for any Apps-related search
        if any('application' in str(arg) for arg in args):
            _logger.info("Applying Enterprise module filter")
            # Filter out Enterprise modules
            enterprise_filter = ('name', 'not in', self.ENTERPRISE_MODULES)
            args = args + [enterprise_filter]
            _logger.info(f"Updated args: {args}")
        
        return super().search(args, offset=offset, limit=limit, order=order, count=count)