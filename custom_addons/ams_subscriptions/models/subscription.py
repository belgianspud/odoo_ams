from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class AMSSubscription(models.Model):
    _name = 'ams.subscription'
    _description = 'AMS Subscription'
    _order = 'create_date desc'
    
    name = fields.Char(string='Subscription Name', required=True)
    partner_id = fields.Many2one('res.partner', string='Member', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending_renewal', 'Pending Renewal')
    ], string='Status', default='draft')
    
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.today)
    end_date = fields.Date(string='End Date', required=False)
    
    # Recurring and renewal fields
    is_recurring = fields.Boolean('Is Recurring', default=False)
    recurring_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),        
        ('yearly', 'Yearly')
    ], string='Recurring Period', default='yearly')
    
    auto_renewal = fields.Boolean('Auto Renewal', default=True)
    next_renewal_date = fields.Date('Next Renewal Date')
    renewal_reminder_sent = fields.Boolean('Renewal Reminder Sent', default=False)
    renewal_invoice_id = fields.Many2one('account.move', 'Renewal Invoice')
    
    # Updated subscription_type to maintain backward compatibility
    subscription_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),        
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime')
    ], string='Billing Cycle', default='yearly')
    
    # Subscription Type (membership, chapter, publication)
    subscription_type_id = fields.Many2one('ams.subscription.type', 'Subscription Type', required=True)
    subscription_code = fields.Selection(related='subscription_type_id.code', store=True, string='Type Code')
    
    # Financial fields
    amount = fields.Float(string='Amount', required=True, default=0.0)
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 default=lambda self: self.env.company.currency_id, required=True)
    
    notes = fields.Text(string='Notes')
    
    # Product Integration
    product_id = fields.Many2one('product.product', 'Related Product')
    sale_order_line_id = fields.Many2one('sale.order.line', 'Source Sale Line')
    
    # Invoice Integration
    invoice_ids = fields.One2many('account.move', 'subscription_id', 'Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoice Count', store=True)
    
    # Hierarchy for chapters
    parent_subscription_id = fields.Many2one('ams.subscription', 'Parent Subscription',
                                           domain="[('subscription_code', '=', 'membership'), ('partner_id', '=', partner_id)]")
    child_subscription_ids = fields.One2many('ams.subscription', 'parent_subscription_id', 'Child Subscriptions')
    
    # Chapter-specific fields
    chapter_id = fields.Many2one('ams.chapter', 'Chapter', 
                                domain="[('active', '=', True)]",
                                help="Select the chapter for this subscription")
    chapter_region = fields.Char(related='chapter_id.region', store=True, readonly=True, string='Chapter Region')
    
    # Publication-specific fields
    publication_format = fields.Selection([
        ('print', 'Print'),
        ('digital', 'Digital'),
        ('both', 'Print + Digital')
    ], 'Publication Format')
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids) if record.invoice_ids else 0
    
    @api.model_create_multi
    def create(self, vals_list):
        # Auto-generate subscription name if not provided
        for vals in vals_list:
            if not vals.get('name'):
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                subscription_type = self.env['ams.subscription.type'].browse(vals.get('subscription_type_id'))
                vals['name'] = f"{subscription_type.name} - {partner.name}"
            
            # Ensure amount has a proper default
            if 'amount' not in vals or not vals['amount']:
                vals['amount'] = 0.0
                
            # Set next renewal date if recurring
            if vals.get('is_recurring') and vals.get('end_date') and not vals.get('next_renewal_date'):
                vals['next_renewal_date'] = vals['end_date']
        
        subscriptions = super().create(vals_list)
        
        # Handle subscription type-specific creation logic
        for subscription in subscriptions:
            subscription._handle_subscription_creation()
        
        return subscriptions
    
    def _create_chapter_subscriptions(self, chapter_ids):
        """Create chapter subscriptions for a membership"""
        if self.subscription_code != 'membership':
            return
            
        chapter_type = self.env['ams.subscription.type'].search([('code', '=', 'chapter')], limit=1)
        if not chapter_type:
            _logger.warning("No chapter subscription type found")
            return
            
        for chapter in chapter_ids:
            chapter_vals = {
                'partner_id': self.partner_id.id,
                'subscription_type_id': chapter_type.id,
                'parent_subscription_id': self.id,
                'chapter_id': chapter.id,
                'name': f"Chapter {chapter.name} - {self.partner_id.name}",
                'start_date': self.start_date,
                'end_date': self.end_date,
                'amount': chapter.chapter_fee if chapter.chapter_fee else 0.0,
                'is_recurring': self.is_recurring,
                'recurring_period': self.recurring_period,
                'auto_renewal': self.auto_renewal,
                'next_renewal_date': self.next_renewal_date,
                'state': 'active',
            }
            
            chapter_subscription = self.env['ams.subscription'].create(chapter_vals)
            
            # Add chapter fee to the same invoice if exists
            if self.sale_order_line_id and self.sale_order_line_id.order_id.invoice_ids:
                draft_invoice = self.sale_order_line_id.order_id.invoice_ids.filtered(lambda i: i.state == 'draft')
                if draft_invoice and chapter.chapter_fee > 0:
                    chapter_subscription._add_to_existing_invoice(draft_invoice[0])
    
    def _handle_subscription_creation(self):
        """Handle subscription type-specific creation logic"""
        if self.subscription_code == 'membership':
            self._handle_membership_creation()
        elif self.subscription_code == 'chapter':
            self._handle_chapter_creation()
        elif self.subscription_code == 'publication':
            self._handle_publication_creation()
    
    def _handle_membership_creation(self):
        """Handle membership-specific logic"""
        if self.subscription_type_id.creates_invoice and not self.sale_order_line_id:
            self._create_subscription_invoice()
    
    def _handle_chapter_creation(self):
        """Handle chapter-specific logic"""
        if not self.parent_subscription_id:
            raise UserError("Chapter subscriptions must have a parent membership.")
        
        # Validate parent subscription is active
        if self.parent_subscription_id.state not in ['active']:
            raise UserError("Parent membership must be active to add a chapter.")
        
        # Auto-set chapter fee if chapter is selected and no amount is set
        if self.chapter_id and (not self.amount or self.amount == 0.0):
            chapter = self.chapter_id
            if hasattr(chapter, 'chapter_fee') and chapter.chapter_fee and chapter.chapter_fee > 0:
                self.amount = float(chapter.chapter_fee)
        
        # Try to add to existing draft invoice of parent
        parent_invoice = self.parent_subscription_id._get_active_draft_invoice()
        if parent_invoice:
            self._add_to_existing_invoice(parent_invoice)
        elif self.subscription_type_id.creates_invoice:
            self._create_subscription_invoice()
    
    def _handle_publication_creation(self):
        """Handle publication-specific logic"""
        if self.subscription_type_id.creates_invoice and not self.sale_order_line_id:
            self._create_subscription_invoice()
    
    @api.model
    def _cron_check_renewals(self):
        """Cron job to check for upcoming renewals and create renewal invoices"""
        today = fields.Date.today()
        
        # Find subscriptions due for renewal
        subscriptions_to_renew = self.search([
            ('state', '=', 'active'),
            ('is_recurring', '=', True),
            ('auto_renewal', '=', True),
            ('next_renewal_date', '<=', today),
            ('renewal_invoice_id', '=', False)
        ])
        
        for subscription in subscriptions_to_renew:
            subscription._create_renewal_invoice()
        
        # Send renewal reminders
        reminder_date = today + relativedelta(days=30)  # 30 days before expiry
        subscriptions_for_reminder = self.search([
            ('state', '=', 'active'),
            ('is_recurring', '=', True),
            ('next_renewal_date', '=', reminder_date),
            ('renewal_reminder_sent', '=', False)
        ])
        
        for subscription in subscriptions_for_reminder:
            subscription._send_renewal_reminder()
    
    def _create_renewal_invoice(self):
        """Create renewal invoice for subscription"""
        if not self.product_id:
            _logger.warning(f"No product found for subscription {self.name}")
            return
            
        # Calculate new renewal period
        if self.recurring_period == 'monthly':
            new_end_date = self.next_renewal_date + relativedelta(months=1)
        elif self.recurring_period == 'quarterly':
            new_end_date = self.next_renewal_date + relativedelta(months=3)
        else:  # yearly
            new_end_date = self.next_renewal_date + relativedelta(years=1)
        
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'subscription_id': self.id,
            'is_renewal_invoice': True,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'quantity': 1,
                'price_unit': self.amount,
                'name': f"Renewal: {self.name} ({self.next_renewal_date.strftime('%Y-%m-%d')} - {new_end_date.strftime('%Y-%m-%d')})",
            })]
        }
        
        renewal_invoice = self.env['account.move'].create(invoice_vals)
        
        # Update subscription
        self.write({
            'renewal_invoice_id': renewal_invoice.id,
            'state': 'pending_renewal',
            'next_renewal_date': new_end_date,
        })
        
        # Also create renewal invoices for child subscriptions (chapters)
        for child in self.child_subscription_ids.filtered(lambda c: c.is_recurring and c.auto_renewal):
            child._create_renewal_invoice()
        
        return renewal_invoice
    
    def _send_renewal_reminder(self):
        """Send renewal reminder email"""
        # This would integrate with Odoo's email system
        self.renewal_reminder_sent = True
        # TODO: Implement email template and sending logic
        _logger.info(f"Renewal reminder sent for subscription {self.name}")
    
    def action_confirm_renewal(self):
        """Confirm renewal and extend subscription"""
        if self.renewal_invoice_id and self.renewal_invoice_id.state == 'posted':
            # Extend subscription period
            if self.recurring_period == 'monthly':
                self.end_date = self.end_date + relativedelta(months=1)
            elif self.recurring_period == 'quarterly':
                self.end_date = self.end_date + relativedelta(months=3)
            else:  # yearly
                self.end_date = self.end_date + relativedelta(years=1)
                
            self.state = 'active'
            self.renewal_invoice_id = False
            self.renewal_reminder_sent = False
            
            # Also renew child subscriptions
            for child in self.child_subscription_ids:
                if child.state == 'pending_renewal':
                    child.action_confirm_renewal()
    
    def _create_subscription_invoice(self):
        """Create invoice for subscription"""
        if not self.product_id:
            # Try to get product from subscription type or chapter
            if self.subscription_code == 'chapter' and self.chapter_id:
                chapter = self.chapter_id
                if hasattr(chapter, 'product_template_id') and chapter.product_template_id:
                    self.product_id = chapter.product_template_id.product_variant_id
            elif hasattr(self.subscription_type_id, 'product_template_id') and self.subscription_type_id.product_template_id:
                self.product_id = self.subscription_type_id.product_template_id.product_variant_id
            
            if not self.product_id:
                return
        
        # Prepare invoice description
        description = f"{self.subscription_type_id.name}: {self.name}"
        if self.subscription_code == 'chapter' and self.chapter_id:
            description += f" ({self.chapter_id.name})"
        
        # Ensure we have a valid amount
        amount = self.amount if self.amount and self.amount > 0 else (self.product_id.list_price if self.product_id else 0.0)
        
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'subscription_id': self.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'quantity': 1,
                'price_unit': amount,
                'name': description,
            })]
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        return invoice
    
    def _get_active_draft_invoice(self):
        """Get active draft invoice for this subscription"""
        return self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
    
    def _add_to_existing_invoice(self, invoice):
        """Add this subscription to an existing draft invoice"""
        if not self.product_id:
            return
            
        # Prepare line description
        description = f"{self.subscription_type_id.name}: {self.name}"
        if self.subscription_code == 'chapter' and self.chapter_id:
            description += f" ({self.chapter_id.name})"
        
        # Ensure we have a valid amount
        amount = self.amount if self.amount and self.amount > 0 else (self.product_id.list_price if self.product_id else 0.0)
            
        invoice.write({
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'quantity': 1,
                'price_unit': amount,
                'name': description,
            })]
        })
    
    def action_view_invoices(self):
        """Action to view related invoices"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'context': {'default_partner_id': self.partner_id.id}
        }
    
    def action_view_renewal_invoice(self):
        """Action to view renewal invoice"""
        if self.renewal_invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Renewal Invoice',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.renewal_invoice_id.id,
                'context': {'default_partner_id': self.partner_id.id}
            }
    
    # Keep existing methods and constraints
    @api.constrains('parent_subscription_id', 'subscription_code')
    def _check_parent_subscription(self):
        """Validate parent subscription requirements"""
        for record in self:
            if hasattr(record.subscription_type_id, 'requires_parent') and record.subscription_type_id.requires_parent and not record.parent_subscription_id:
                raise ValidationError(f"{record.subscription_type_id.name} subscriptions require a parent membership.")
            
            if record.parent_subscription_id and record.parent_subscription_id.subscription_code != 'membership':
                raise ValidationError("Parent subscription must be a membership type.")
    
    @api.constrains('chapter_id', 'subscription_code')
    def _check_chapter_requirements(self):
        """Validate chapter requirements for chapter subscriptions"""
        for record in self:
            if record.subscription_code == 'chapter' and not record.chapter_id:
                raise ValidationError("Chapter subscriptions must have a chapter selected.")
    
    @api.onchange('chapter_id')
    def _onchange_chapter_id(self):
        """Auto-populate amount and product when chapter is selected"""
        if self.chapter_id and self.subscription_code == 'chapter':
            chapter = self.chapter_id
            # Only update amount if current amount is 0 or not set
            if hasattr(chapter, 'chapter_fee') and chapter.chapter_fee and (not self.amount or self.amount == 0.0):
                self.amount = float(chapter.chapter_fee)
            if hasattr(chapter, 'product_template_id') and chapter.product_template_id:
                self.product_id = chapter.product_template_id.product_variant_id
    
    @api.onchange('subscription_type_id')
    def _onchange_subscription_type_id(self):
        """Clear fields that don't apply to the selected subscription type"""
        if self.subscription_type_id:
            if self.subscription_type_id.code != 'chapter':
                self.chapter_id = False
                self.parent_subscription_id = False
            if self.subscription_type_id.code != 'publication':
                self.publication_format = False
    
    # Keep existing methods
    def action_activate(self):
        self.state = 'active'
    
    def action_cancel(self):
        self.state = 'cancelled'
    
    def action_renew(self):
        """Manual renewal action"""
        if self.is_recurring:
            self._create_renewal_invoice()
        else:
            self.state = 'active'
            # Extend end date based on subscription type
            if self.subscription_type == 'monthly':
                self.end_date = fields.Date.add(self.end_date or fields.Date.today(), months=1)
            elif self.subscription_type == 'yearly':
                self.end_date = fields.Date.add(self.end_date or fields.Date.today(), years=1)