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

        #Custom Modules
        'ams_member_data',      # AMS base module for member data structures - Layer 1
        'ams_communication',    # AMS base module to track comms preferences - Layer 1
        'ams_system_config',    # AMS base module for managing and configuring ams configurations - Layer 1
        'ams_participation',    # AMS base module for tracking participations(membership/chapter subscription records) - Layer 2

        """
        #commenting out this section to provide clean list of modules to use for ams. 
        #uncomment modules as needed for missing functionality.
        # Original Custom Modules
        'ams_subscriptions',    # AMS Subscriptions
        'ams_base_accounting',  # AMS Accounting
        'ams_revenue_recognition', # AMS Revenue Recognition
        'ams_subscription_billing', # AMS Subscription Billing
        'association_business_automation', # initial automation GUI module for business rules management

        #External Modules
        'base_accounting_kit',
        'base_account_budget',
        'master_search',
        'auto_database_backup',
        'custom_receipts_for_pos',
        'dynamic_accounts_report',
        'inventory_barcode_scanning',
        'inventory_stock_dashboard_odoo',
        'invoice_format_editor',
        'invoice_merging',
        'login_user_detail',
        'low_stocks_product_alert',
        'odoo_accounting_dashboard',
        'pos_product_stock',
        'pos_restrict_product_stock',
        'product_management_app',
        'purchase_product_history',
        'rest_api_odoo',
        'sale_discount_total',
        'sale_report_advanced',
        'subscription_package',
        'user_audit',
        'website_hide_button',"""
    ]
    
    def _is_apps_menu_context(self, domain=None):
        """Check if this is specifically the Apps menu context"""
        context = self.env.context
        
        # Check for Apps menu specific contexts
        if context.get('search_default_app'):
            return True
            
        # Check if domain contains Apps menu specific filters
        if domain:
            for condition in domain:
                if isinstance(condition, (list, tuple)) and len(condition) >= 3:
                    field, operator, value = condition[0], condition[1], condition[2]
                    # Apps menu typically searches for application=True and installable=True
                    if field == 'application' and value is True:
                        return True
                    if field == 'installable' and value is True and \
                       any('application' in str(c) for c in domain):
                        return True
        
        return False
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        """Override search - only filter for Apps menu, not main dashboard"""
        # Only apply filtering if this is specifically the Apps menu
        if self._is_apps_menu_context():
            _logger.info("AMS Module Manager: Filtering for Apps menu only")
            # Add filter to show only allowed modules
            module_filter = ('name', 'in', self.ALLOWED_MODULES)
            args = args + [module_filter]
        
        return super().search(args, offset=offset, limit=limit, order=order)
    
    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None, count_limit=None):
        """Override web_search_read - only filter for Apps menu"""
        # Check if this is the Apps menu context
        if self._is_apps_menu_context(domain):
            _logger.info("AMS Module Manager: Filtering web_search_read for Apps menu")
            
            # Get the results first
            result = super().web_search_read(domain=domain, specification=specification, 
                                           offset=offset, limit=limit, order=order, count_limit=count_limit)
            
            if result and 'records' in result:
                # Keep ONLY allowed modules
                filtered_records = []
                for record in result['records']:
                    module_name = record.get('name', '')
                    if module_name in self.ALLOWED_MODULES:
                        filtered_records.append(record)
                
                result['records'] = filtered_records
                result['length'] = len(filtered_records)
            
            return result
        else:
            # For main dashboard and other contexts, don't filter
            _logger.info("AMS Module Manager: Not filtering - allowing all modules for dashboard")
            return super().web_search_read(domain=domain, specification=specification, 
                                         offset=offset, limit=limit, order=order, count_limit=count_limit)