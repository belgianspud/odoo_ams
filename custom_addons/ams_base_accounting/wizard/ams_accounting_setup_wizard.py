# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AMSAccountingSetupWizard(models.TransientModel):
    """Wizard to set up AMS accounting"""
    _name = 'ams.accounting.setup.wizard'
    _description = 'AMS Accounting Setup Wizard'
    
    # Setup options
    create_ams_accounts = fields.Boolean(
        string='Create AMS Chart of Accounts',
        default=True,
        help='Create association-specific GL accounts'
    )
    
    configure_existing_products = fields.Boolean(
        string='Configure Existing Products',
        default=True,
        help='Auto-configure GL accounts for existing AMS products'
    )
    
    setup_default_journals = fields.Boolean(
        string='Setup AMS Journals',
        default=True,
        help='Create AMS-specific journals if needed'
    )
    
    # Information fields
    unconfigured_product_count = fields.Integer(
        string='Unconfigured Products',
        compute='_compute_product_stats',
        help='Number of AMS products needing configuration'
    )
    
    existing_ams_accounts = fields.Integer(
        string='Existing AMS Accounts', 
        compute='_compute_account_stats',
        help='Number of existing AMS accounts'
    )
    
    @api.depends()
    def _compute_product_stats(self):
        """Compute product statistics"""
        for wizard in self:
            wizard.unconfigured_product_count = self.env['product.template'].search_count([
                ('is_subscription_product', '=', True),
                ('use_ams_accounting', '=', True),
                ('ams_accounts_configured', '=', False)
            ])
    
    @api.depends()
    def _compute_account_stats(self):
        """Compute account statistics"""
        for wizard in self:
            wizard.existing_ams_accounts = self.env['account.account'].search_count([
                ('is_ams_account', '=', True)
            ])
    
    def action_run_setup(self):
        """Execute the AMS accounting setup"""
        self.ensure_one()
        
        messages = []
        
        # Create AMS accounts
        if self.create_ams_accounts:
            created_accounts = self.env['account.account'].create_ams_account_structure()
            if created_accounts:
                messages.append(f"Created {len(created_accounts)} AMS accounts")
            else:
                messages.append("AMS accounts already exist")
        
        # Configure existing products
        if self.configure_existing_products:
            unconfigured = self.env['product.template'].search([
                ('is_subscription_product', '=', True),
                ('use_ams_accounting', '=', True),
                ('ams_accounts_configured', '=', False)
            ])
            
            for product in unconfigured:
                product._set_default_ams_accounts()
            
            if unconfigured:
                messages.append(f"Configured {len(unconfigured)} AMS products")
            else:
                messages.append("All AMS products already configured")
        
        # Setup journals
        if self.setup_default_journals:
            journal_created = self._setup_ams_journals()
            if journal_created:
                messages.append("Created AMS journals")
            else:
                messages.append("AMS journals already exist")
        
        # Show completion message
        message_text = "AMS Accounting Setup Complete:\n" + "\n".join(f"• {msg}" for msg in messages)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message_text,
                'type': 'success',
                'sticky': True,
            }
        }
    
    def _setup_ams_journals(self):
        """Create AMS-specific journals if needed"""
        company = self.env.company
        
        # Check if AMS sales journal exists
        ams_journal = self.env['account.journal'].search([
            ('code', '=', 'AMS'),
            ('company_id', '=', company.id)
        ], limit=1)
        
        if not ams_journal:
            # Create AMS sales journal
            ams_journal = self.env['account.journal'].create({
                'name': 'AMS Sales',
                'code': 'AMS',
                'type': 'sale',
                'company_id': company.id,
            })
            return True
        
        return False