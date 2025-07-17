from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SubscriptionRenewalWizard(models.TransientModel):
    _name = 'ams.subscription.renewal.wizard'
    _description = 'Subscription Renewal Wizard'

    subscription_id = fields.Many2one('ams.subscription', 'Subscription', required=True)
    partner_id = fields.Many2one('res.partner', 'Subscriber', related='subscription_id.partner_id', readonly=True)
    plan_id = fields.Many2one('ams.subscription.plan', 'Plan', related='subscription_id.plan_id', readonly=True)
    
    # Current subscription info
    current_start_date = fields.Date('Current Start Date', related='subscription_id.start_date', readonly=True)
    current_end_date = fields.Date('Current End Date', related='subscription_id.end_date', readonly=True)
    current_price = fields.Float('Current Price', related='subscription_id.price', readonly=True)
    
    # Renewal options
    renewal_type = fields.Selection([
        ('standard', 'Standard Renewal'),
        ('early', 'Early Renewal'),
        ('grace', 'Grace Period Renewal'),
    ], string='Renewal Type', default='standard', required=True)
    
    new_start_date = fields.Date('New Start Date', required=True)
    new_end_date = fields.Date('New End Date', readonly=True, compute='_compute_new_end_date')
    new_price = fields.Float('Renewal Price', required=True)
    
    # Pricing options
    use_proration = fields.Boolean('Apply Proration', default=False)
    discount_percent = fields.Float('Discount %', default=0.0)
    discount_amount = fields.Float('Discount Amount', default=0.0)
    final_price = fields.Float('Final Price', compute='_compute_final_price', store=True)
    
    # Payment options
    create_invoice = fields.Boolean('Create Invoice', default=True)
    auto_confirm_invoice = fields.Boolean('Auto Confirm Invoice', default=False)
    
    # Notes
    notes = fields.Text('Renewal Notes')
    
    @api.model
    def default_get(self, fields_list):
        """Set default values based on context"""
        result = super().default_get(fields_list)
        
        if self.env.context.get('active_model') == 'ams.subscription':
            subscription_id = self.env.context.get('active_id')
            if subscription_id:
                subscription = self.env['ams.subscription'].browse(subscription_id)
                result.update({
                    'subscription_id': subscription_id,
                    'new_start_date': subscription.end_date,
                    'new_price': subscription.price,
                })
        
        return result
    
    @api.depends('new_start_date', 'subscription_id')
    def _compute_new_end_date(self):
        """Calculate new end date based on start date and plan"""
        for wizard in self:
            if wizard.new_start_date and wizard.subscription_id:
                wizard.new_end_date = wizard.subscription_id.plan_id.calculate_next_billing_date(
                    wizard.new_start_date
                )
            else:
                wizard.new_end_date = False
    
    @api.depends('new_price', 'discount_percent', 'discount_amount')
    def _compute_final_price(self):
        """Calculate final price after discounts"""
        for wizard in self:
            final_price = wizard.new_price
            
            # Apply percentage discount
            if wizard.discount_percent > 0:
                final_price = final_price * (1 - wizard.discount_percent / 100)
            
            # Apply amount discount
            if wizard.discount_amount > 0:
                final_price = max(0, final_price - wizard.discount_amount)
            
            wizard.final_price = final_price
    
    @api.onchange('renewal_type')
    def _onchange_renewal_type(self):
        """Update default dates based on renewal type"""
        if self.subscription_id:
            if self.renewal_type == 'standard':
                self.new_start_date = self.subscription_id.end_date
            elif self.renewal_type == 'early':
                self.new_start_date = fields.Date.today()
                self.use_proration = True
            elif self.renewal_type == 'grace':
                self.new_start_date = self.subscription_id.grace_period_end or self.subscription_id.end_date
    
    @api.constrains('new_start_date', 'subscription_id')
    def _check_renewal_dates(self):
        """Validate renewal dates"""
        for wizard in self:
            if wizard.renewal_type == 'early' and wizard.new_start_date >= wizard.subscription_id.end_date:
                raise ValidationError(_('Early renewal start date must be before current end date'))
            
            if wizard.renewal_type == 'standard' and wizard.new_start_date != wizard.subscription_id.end_date:
                raise ValidationError(_('Standard renewal must start on current end date'))
    
    def action_renew_subscription(self):
        """Execute the subscription renewal"""
        self.ensure_one()
        
        subscription = self.subscription_id
        
        # Validate subscription can be renewed
        if subscription.state not in ['active', 'expired']:
            raise UserError(_('Only active or expired subscriptions can be renewed'))
        
        # Calculate proration if needed
        final_price = self.final_price
        if self.use_proration and self.renewal_type == 'early':
            # Calculate prorated amount for overlap period
            overlap_days = (subscription.end_date - self.new_start_date).days
            if overlap_days > 0:
                period_days = (self.new_end_date - self.new_start_date).days
                if period_days > 0:
                    proration_factor = (period_days - overlap_days) / period_days
                    final_price = self.new_price * proration_factor
        
        # Update subscription
        subscription.write({
            'start_date': self.new_start_date,
            'end_date': self.new_end_date,
            'price': final_price,
            'state': 'active',
            'renewal_count': subscription.renewal_count + 1,
            'last_billing_date': fields.Date.today(),
        })
        
        # Create subscription line
        line_vals = {
            'subscription_id': subscription.id,
            'date': fields.Date.today(),
            'line_type': 'renewal',
            'description': f'Subscription renewed - {self.renewal_type} renewal',
            'price': final_price,
            'notes': self.notes,
        }
        
        subscription_line = self.env['ams.subscription.line'].create(line_vals)
        
        # Create invoice if requested
        invoice = None
        if self.create_invoice:
            invoice = self._create_renewal_invoice(subscription, final_price)
            subscription_line.invoice_id = invoice.id
            
            if self.auto_confirm_invoice and invoice:
                invoice.action_post()
        
        # Log renewal activity
        subscription.message_post(
            body=_('Subscription renewed via wizard. New period: %s to %s. Price: %s') % (
                self.new_start_date, self.new_end_date, final_price
            ),
            message_type='comment',
        )
        
        # Return action to view updated subscription
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewed Subscription'),
            'res_model': 'ams.subscription',
            'res_id': subscription.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _create_renewal_invoice(self, subscription, amount):
        """Create invoice for renewal"""
        invoice_vals = {
            'partner_id': subscription.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_origin': f"{subscription.name} - Renewal",
            'ams_subscription_id': subscription.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': subscription.plan_id.product_id.id,
                'name': f"{subscription.plan_id.name} - Renewal ({self.new_start_date} to {self.new_end_date})",
                'quantity': 1,
                'price_unit': amount,
                'account_id': subscription.plan_id.product_id.property_account_income_id.id or
                             subscription.plan_id.product_id.categ_id.property_account_income_categ_id.id,
            })],
        }
        
        # Add discount line if applicable
        if self.discount_amount > 0 or self.discount_percent > 0:
            discount_amount = self.new_price - self.final_price
            if discount_amount > 0:
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'name': f"Renewal Discount ({self.discount_percent}% + {self.discount_amount})",
                    'quantity': 1,
                    'price_unit': -discount_amount,
                    'account_id': subscription.plan_id.product_id.property_account_income_id.id or
                                 subscription.plan_id.product_id.categ_id.property_account_income_categ_id.id,
                }))
        
        return self.env['account.move'].create(invoice_vals)
    
    def action_preview_renewal(self):
        """Preview renewal without executing"""
        self.ensure_one()
        
        message = _('''
        Renewal Preview:
        
        Current Period: %s to %s
        New Period: %s to %s
        
        Original Price: %s
        Discount: %s%% + %s
        Final Price: %s
        
        Renewal Type: %s
        ''') % (
            self.current_start_date, self.current_end_date,
            self.new_start_date, self.new_end_date,
            self.new_price, self.discount_percent, self.discount_amount,
            self.final_price, self.renewal_type
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Renewal Preview'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }