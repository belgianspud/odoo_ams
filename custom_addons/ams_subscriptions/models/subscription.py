from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta


class Subscription(models.Model):
    _name = 'ams.subscription'
    _description = 'Subscription'
    _order = 'start_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _rec_name = 'display_name'

    def _get_default_start_date(self):
        return fields.Date.today()

    # Basic Information
    name = fields.Char('Subscription Reference', required=True, copy=False, 
                      default=lambda self: _('New'), tracking=True)
    invoice_date = fields.Date(string="Invoice Date")
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    partner_id = fields.Many2one('res.partner', 'Subscriber', required=True, 
                                tracking=True, index=True)
    plan_id = fields.Many2one('ams.subscription.plan', 'Subscription Plan', 
                             required=True, tracking=True)
    
    # Dates
    start_date = fields.Date('Start Date', required=True, default=_get_default_start_date,
                           tracking=True)
    end_date = fields.Date('End Date', compute='_compute_end_date', store=True, 
                          tracking=True)
    next_billing_date = fields.Date('Next Billing Date', compute='_compute_next_billing_date',
                                   store=True, tracking=True)
    last_billing_date = fields.Date('Last Billing Date', tracking=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Billing Information
    price = fields.Float('Price', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                 default=lambda self: self.env.company.currency_id)
    
    # Renewal Configuration
    auto_renew = fields.Boolean('Auto Renew', default=True, tracking=True)
    renewal_count = fields.Integer('Renewal Count', default=0, tracking=True)
    
    # Trial Information
    is_trial = fields.Boolean('Is Trial', default=False, tracking=True)
    trial_end_date = fields.Date('Trial End Date', tracking=True)
    
    # Payment Information
    payment_method = fields.Selection([
        ('manual', 'Manual'),
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
        ('check', 'Check'),
    ], string='Payment Method', default='manual', tracking=True)
    
    # Related Information
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', tracking=True)
    invoice_ids = fields.One2many('account.move', 'ams_subscription_id', 'Invoices')
    invoice_count = fields.Integer('Invoice Count', compute='_compute_invoice_count')
    
    # Subscription Lines
    line_ids = fields.One2many('ams.subscription.line', 'subscription_id', 'Subscription Lines')
    
    # Computed Fields
    is_expired = fields.Boolean('Is Expired', compute='_compute_is_expired')
    days_until_expiry = fields.Integer('Days Until Expiry', compute='_compute_days_until_expiry')
    can_renew = fields.Boolean('Can Renew', compute='_compute_can_renew')
    
    # Grace Period
    grace_period_end = fields.Date('Grace Period End', compute='_compute_grace_period_end',
                                  store=True)
    in_grace_period = fields.Boolean('In Grace Period', compute='_compute_in_grace_period')
    
    @api.depends('partner_id', 'plan_id', 'name')
    def _compute_display_name(self):
        for subscription in self:
            if subscription.partner_id and subscription.plan_id:
                subscription.display_name = f"{subscription.partner_id.name} - {subscription.plan_id.name}"
            else:
                subscription.display_name = subscription.name or _('New Subscription')
    
    @api.depends('start_date', 'plan_id')
    def _compute_end_date(self):
        for subscription in self:
            if subscription.start_date and subscription.plan_id:
                subscription.end_date = subscription.plan_id.calculate_next_billing_date(
                    subscription.start_date
                )
            else:
                subscription.end_date = False
    
    @api.depends('end_date', 'plan_id')
    def _compute_next_billing_date(self):
        for subscription in self:
            if subscription.end_date and subscription.auto_renew and subscription.state == 'active':
                subscription.next_billing_date = subscription.end_date
            else:
                subscription.next_billing_date = False
    
    @api.depends('end_date', 'plan_id')
    def _compute_grace_period_end(self):
        for subscription in self:
            if subscription.end_date and subscription.plan_id.grace_period_days > 0:
                subscription.grace_period_end = subscription.end_date + timedelta(
                    days=subscription.plan_id.grace_period_days
                )
            else:
                subscription.grace_period_end = False
    
    @api.depends('end_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for subscription in self:
            subscription.is_expired = subscription.end_date and subscription.end_date < today
    
    @api.depends('end_date')
    def _compute_days_until_expiry(self):
        today = fields.Date.today()
        for subscription in self:
            if subscription.end_date:
                subscription.days_until_expiry = (subscription.end_date - today).days
            else:
                subscription.days_until_expiry = 0
    
    @api.depends('state', 'end_date')
    def _compute_can_renew(self):
        today = fields.Date.today()
        for subscription in self:
            subscription.can_renew = (
                subscription.state in ['active', 'expired'] and
                subscription.end_date and
                subscription.end_date >= today - timedelta(days=365)  # Can renew within 1 year
            )
    
    @api.depends('grace_period_end')
    def _compute_in_grace_period(self):
        today = fields.Date.today()
        for subscription in self:
            subscription.in_grace_period = (
                subscription.grace_period_end and
                subscription.is_expired and
                subscription.grace_period_end >= today
            )
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for subscription in self:
            subscription.invoice_count = len(subscription.invoice_ids)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('ams.subscription') or _('New')
        
        # Set price from plan if not provided
        if 'price' not in vals and 'plan_id' in vals:
            plan = self.env['ams.subscription.plan'].browse(vals['plan_id'])
            vals['price'] = plan.price
        
        # Handle trial period
        if 'plan_id' in vals:
            plan = self.env['ams.subscription.plan'].browse(vals['plan_id'])
            if plan.trial_period_days > 0:
                vals['is_trial'] = True
                vals['trial_end_date'] = fields.Date.today() + timedelta(days=plan.trial_period_days)
                vals['state'] = 'trial'
        
        return super().create(vals)
    
    def write(self, vals):
        # Track state changes
        if 'state' in vals:
            for subscription in self:
                if subscription.state != vals['state']:
                    subscription.message_post(
                        body=_('Subscription status changed from %s to %s') % (
                            dict(subscription._fields['state'].selection)[subscription.state],
                            dict(subscription._fields['state'].selection)[vals['state']]
                        )
                    )
        
        return super().write(vals)
    
    def action_activate(self):
        """Activate subscription"""
        for subscription in self:
            if subscription.state not in ['draft', 'trial']:
                raise UserError(_('Only draft or trial subscriptions can be activated'))
            
            subscription.write({
                'state': 'active',
                'start_date': fields.Date.today(),
            })
            
            # Create initial subscription line
            self.env['ams.subscription.line'].create({
                'subscription_id': subscription.id,
                'date': subscription.start_date,
                'description': _('Subscription activated'),
                'price': subscription.price,
            })
    
    def action_suspend(self):
        """Suspend subscription"""
        for subscription in self:
            if subscription.state != 'active':
                raise UserError(_('Only active subscriptions can be suspended'))
            
            subscription.state = 'suspended'
    
    def action_cancel(self):
        """Cancel subscription"""
        for subscription in self:
            if subscription.state in ['cancelled', 'expired']:
                raise UserError(_('Subscription is already cancelled or expired'))
            
            subscription.write({
                'state': 'cancelled',
                'auto_renew': False,
            })
    
    def action_renew(self):
        """Renew subscription"""
        for subscription in self:
            if not subscription.can_renew:
                raise UserError(_('Subscription cannot be renewed'))
            
            # Calculate new dates
            new_start_date = subscription.end_date
            new_end_date = subscription.plan_id.calculate_next_billing_date(new_start_date)
            
            subscription.write({
                'start_date': new_start_date,
                'end_date': new_end_date,
                'state': 'active',
                'renewal_count': subscription.renewal_count + 1,
                'last_billing_date': fields.Date.today(),
            })
            
            # Create renewal line
            self.env['ams.subscription.line'].create({
                'subscription_id': subscription.id,
                'date': new_start_date,
                'description': _('Subscription renewed'),
                'price': subscription.price,
            })
            
            # Create invoice if auto-billing is enabled
            if subscription.payment_method != 'manual':
                subscription._create_invoice()
    
    def _create_invoice(self):
        """Create invoice for subscription"""
        for subscription in self:
            invoice_vals = {
                'partner_id': subscription.partner_id.id,
                'move_type': 'out_invoice',
                'invoice_origin': subscription.name,
                'ams_subscription_id': subscription.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': subscription.plan_id.product_id.id,
                    'name': f"{subscription.plan_id.name} - {subscription.name}",
                    'quantity': 1,
                    'price_unit': subscription.price,
                    'account_id': subscription.plan_id.product_id.property_account_income_id.id or
                                 subscription.plan_id.product_id.categ_id.property_account_income_categ_id.id,
                })],
            }
            
            invoice = self.env['account.move'].create(invoice_vals)
            return invoice
    
    def action_create_invoice(self):
        """Manual invoice creation"""
        invoices = self.env['account.move']
        for subscription in self:
            invoice = subscription._create_invoice()
            invoices |= invoice
        
        if len(invoices) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Invoice'),
                'res_model': 'account.move',
                'res_id': invoices.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Invoices'),
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', invoices.ids)],
                'target': 'current',
            }
    
    def action_view_invoices(self):
        """View subscription invoices"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('ams_subscription_id', '=', self.id)],
            'context': {'default_ams_subscription_id': self.id},
        }
    
    @api.model
    def _cron_process_renewals(self):
        """Cron job to process automatic renewals"""
        today = fields.Date.today()
        
        # Find subscriptions that need renewal
        subscriptions = self.search([
            ('state', '=', 'active'),
            ('auto_renew', '=', True),
            ('end_date', '<=', today),
        ])
        
        for subscription in subscriptions:
            try:
                subscription.action_renew()
            except Exception as e:
                subscription.message_post(
                    body=_('Auto-renewal failed: %s') % str(e),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
    
    @api.model
    def _cron_send_renewal_reminders(self):
        """Cron job to send renewal reminders"""
        today = fields.Date.today()
        
        subscriptions = self.search([
            ('state', '=', 'active'),
            ('auto_renew', '=', False),
        ])
        
        for subscription in subscriptions:
            if subscription.plan_id.renewal_reminder_days > 0:
                reminder_date = subscription.end_date - timedelta(
                    days=subscription.plan_id.renewal_reminder_days
                )
                
                if reminder_date == today:
                    subscription._send_renewal_reminder()
    
    def _send_renewal_reminder(self):
        """Send renewal reminder email"""
        template = self.env.ref('ams_subscriptions.email_template_renewal_reminder', 
                               raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
    
    @api.model
    def _cron_expire_subscriptions(self):
        """Cron job to expire subscriptions"""
        today = fields.Date.today()
        
        # Expire subscriptions past grace period
        subscriptions = self.search([
            ('state', 'in', ['active', 'suspended']),
            ('grace_period_end', '<', today),
        ])
        
        subscriptions.write({'state': 'expired'})
        
        # Also expire trial subscriptions
        trial_subscriptions = self.search([
            ('state', '=', 'trial'),
            ('trial_end_date', '<', today),
        ])
        
        trial_subscriptions.write({'state': 'expired'})


# Add field to account.move to link invoices to subscriptions
class AccountMove(models.Model):
    _inherit = 'account.move'
    
    ams_subscription_id = fields.Many2one('ams.subscription', 'Subscription', 
                                         readonly=True, tracking=True)