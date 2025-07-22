from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'
    
    # List of modules to KEEP visible in Apps menu for AMS focus
    ALLOWED_MODULES = [
        'sale_management',      # Sales
        'account',              # Invoicing
        'crm',                  # CRM
        'website',              # Website
        'stock',                # Inventory
        'purchase',             # Purchase
        'point_of_sale',        # Point of Sale
        'project',              # Project
        'website_sale',         # eCommerce
        'mass_mailing',         # Email Marketing
        'ams_module_manager',   # AMS Module Manager
        'data_recycle',         # Data Recycle
        'marketing_card',       # Marketing Card
        'website_slides',       # eLearning
        'website_event',        # Events
        'mail',                 # Discuss
        'contacts',             # Contacts
        'calendar',             # Calendar
        'im_livechat',          # Live Chat
        'survey',               # Surveys
        'mass_mailing_sms',     # SMS Marketing
        'ams_subscriptions',    # AMS Subscriptions
        'ams_accounting_kit',   # AMS Accounting Kit
        'base_account_budget',  # AMS Base Accounting Budget 
    ]
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        """Override search to show only allowed modules in Apps menu"""
        # Log when this method is called
        _logger.info("AMS Module Manager: search() called")
        _logger.info(f"Search args: {args}")
        _logger.info(f"Context: {self.env.context}")
        
        # Apply filtering for Apps menu searches - show ONLY allowed modules
        if any('category_id' in str(arg) for arg in args if isinstance(arg, (list, tuple))):
            _logger.info("Applying AMS module filter - showing only allowed modules")
            # Show ONLY allowed modules
            module_filter = ('name', 'in', self.ALLOWED_MODULES)
            args = args + [module_filter]
            _logger.info(f"Updated args to show only allowed modules")
        
        return super().search(args, offset=offset, limit=limit, order=order)
    
    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None, count_limit=None):
        """Override web_search_read to show only allowed modules in Apps menu"""
        _logger.info("AMS Module Manager: web_search_read() called")
        _logger.info(f"Domain: {domain}")
        _logger.info(f"Context: {self.env.context}")
        
        # Get the results first
        result = super().web_search_read(domain=domain, specification=specification, offset=offset, limit=limit, order=order, count_limit=count_limit)
        
        # Filter to show ONLY allowed modules
        if result and 'records' in result:
            module_names = [record.get('name') for record in result['records'] if record.get('name')]
            _logger.info(f"Found modules: {module_names}")
            
            # Keep ONLY allowed modules
            filtered_records = []
            for record in result['records']:
                module_name = record.get('name', '')
                if module_name in self.ALLOWED_MODULES:
                    filtered_records.append(record)
                    _logger.info(f"Keeping allowed module: {module_name}")
                else:
                    _logger.info(f"Hiding module: {module_name}")
            
            result['records'] = filtered_records
            result['length'] = len(filtered_records)
        
        return result