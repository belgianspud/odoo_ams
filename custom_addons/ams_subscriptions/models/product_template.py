# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Replace the basic ams_product_type with a cleaner approach
    is_subscription_product = fields.Boolean(
        string='Subscription Product',
        default=False,
        help='Check this box to make this product create subscriptions when purchased.'
    )
    
    # Keep the existing ams_product_type but make it dependent on is_subscription_product
    ams_product_type = fields.Selection([
        ('none', 'None'),
        ('individual', 'Membership - Individual'),
        ('enterprise', 'Membership - Enterprise'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
    ], string='Subscription Type', default='none', compute='_compute_ams_product_type', store=True)

    # Enhanced subscription configuration
    subscription_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='Default Subscription Tier',
        help='When this product is purchased, the subscription will be created using this tier.',
        domain="[('subscription_type', '=', ams_product_type)]"
    )

    # Subscription modification capabilities
    allow_mid_cycle_changes = fields.Boolean(
        string='Allow Mid-Cycle Changes',
        default=True,
        help='Allow customers to upgrade/downgrade this subscription mid-cycle'
    )
    
    allow_pausing = fields.Boolean(
        string='Allow Pausing',
        default=True,
        help='Allow customers to pause this subscription'
    )
    
    proration_policy = fields.Selection([
        ('full_period', 'Charge Full Period'),
        ('prorated', 'Prorated Billing'),
        ('credit_next', 'Credit Next Period'),
    ], string='Mid-Cycle Billing Policy', default='prorated',
    help='How to handle billing when subscription changes mid-cycle')

    # Payment failure tracking
    nsf_flag = fields.Boolean(
        string='NSF Flag',
        help='This product has payment failures',
        compute='_compute_payment_flags'
    )
    
    last_payment_failure_date = fields.Datetime(
        string='Last Payment Failure',
        compute='_compute_payment_flags'
    )

    @api.depends('is_subscription_product')
    def _compute_ams_product_type(self):
        for product in self:
            if not product.is_subscription_product:
                product.ams_product_type = 'none'
            elif product.ams_product_type == 'none':
                product.ams_product_type = 'individual'  # Default to individual

    @api.depends('subscription_ids')
    def _compute_payment_flags(self):
        for product in self:
            # Look for payment failures in related subscriptions
            payment_failures = self.env['ams.payment.history'].search([
                ('subscription_id.product_id.product_tmpl_id', '=', product.id),
                ('payment_status', '=', 'failed')
            ], limit=1, order='failure_date desc')
            
            product.nsf_flag = bool(payment_failures)
            product.last_payment_failure_date = payment_failures.failure_date if payment_failures else False

    @api.onchange('is_subscription_product')
    def _onchange_is_subscription_product(self):
        """Smart defaults when subscription product is enabled"""
        if self.is_subscription_product:
            # Set smart defaults
            self.sale_ok = True
            self.website_published = True
            
            # Handle different field names across Odoo versions
            product_type_field = 'detailed_type' if hasattr(self, 'detailed_type') else 'type'
            setattr(self, product_type_field, 'service')  # Subscriptions are typically services
            
            # Set default subscription period if not set
            if not hasattr(self, 'subscription_period') or self.subscription_period == 'none':
                self.subscription_period = 'annual'
                
            # Auto-set category
            self._set_ams_category()
        else:
            # Reset subscription-related fields
            self.ams_product_type = 'none'
            self.subscription_tier_id = False

    @api.onchange('ams_product_type')
    def _onchange_ams_product_type(self):
        """Update tier domain and set smart defaults based on subscription type"""
        if self.ams_product_type != 'none':
            # Clear tier if it doesn't match the new type
            if self.subscription_tier_id and self.subscription_tier_id.subscription_type != self.ams_product_type:
                self.subscription_tier_id = False
            
            # Set type-specific defaults
            if self.ams_product_type == 'publication':
                # Publications might be physical or digital
                if not hasattr(self, 'is_digital'):
                    self.is_digital = True  # Default to digital
            elif self.ams_product_type == 'enterprise':
                # Enterprise memberships typically don't allow pausing
                self.allow_pausing = False

    def _set_ams_category(self):
        """Set appropriate product category for AMS products"""
        if not self.is_subscription_product:
            return
            
        category_obj = self.env['product.category']
        
        category_mapping = {
            'individual': 'Individual Memberships',
            'enterprise': 'Enterprise Memberships', 
            'chapter': 'Chapters',
            'publication': 'Digital Publications' if getattr(self, 'is_digital', True) else 'Print Publications'
        }
        
        if self.ams_product_type in category_mapping:
            category_name = category_mapping[self.ams_product_type]
            category = category_obj.search([('name', '=', category_name)], limit=1)
            if not category:
                category = category_obj.create({'name': category_name})
            self.categ_id = category.id

    def action_configure_subscription_tier(self):
        """Smart action to create or configure subscription tier"""
        self.ensure_one()
        
        if not self.is_subscription_product:
            raise UserError("This is not a subscription product.")
        
        if self.subscription_tier_id:
            # Edit existing tier
            return {
                'type': 'ir.actions.act_window',
                'name': 'Edit Subscription Tier',
                'res_model': 'ams.subscription.tier',
                'res_id': self.subscription_tier_id.id,
                'view_mode': 'form',
                'target': 'new',
            }
        else:
            # Create new tier with smart defaults
            tier_vals = {
                'name': f"{self.name} Tier",
                'description': f"Default tier for {self.name}",
                'subscription_type': self.ams_product_type,
                'period_length': getattr(self, 'subscription_period', 'annual'),
            }
            
            return {
                'type': 'ir.actions.act_window',
                'name': 'Create Subscription Tier',
                'res_model': 'ams.subscription.tier',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_' + k: v for k, v in tier_vals.items()},
            }

    @api.model
    def create_subscription_from_payment(self, invoice_line):
        """Enhanced subscription creation from invoice payment"""
        product = invoice_line.product_id.product_tmpl_id
        
        # Only create subscriptions for subscription products
        if not product.is_subscription_product:
            return False
            
        # Handle Enterprise Seat Add-ons differently
        if product.is_seat_addon:
            return self._handle_seat_addon_payment(invoice_line)
        
        # Check if subscription already exists for this invoice line
        existing_sub = self.env['ams.subscription'].search([
            ('invoice_line_id', '=', invoice_line.id)
        ], limit=1)
        if existing_sub:
            return existing_sub
        
        # Create new subscription with enhanced tracking
        partner = invoice_line.move_id.partner_id
        start_date = fields.Date.today()
        
        subscription_vals = {
            'name': f"{partner.name} - {product.name}",
            'partner_id': partner.id,
            'account_id': partner.parent_id.id if partner.parent_id else partner.id,
            'product_id': invoice_line.product_id.id,
            'subscription_type': product.ams_product_type,
            'tier_id': product.subscription_tier_id.id if product.subscription_tier_id else False,
            'start_date': start_date,
            'paid_through_date': self._calculate_end_date(start_date, getattr(product, 'subscription_period', 'annual')),
            'state': 'active',
            'invoice_id': invoice_line.move_id.id,
            'invoice_line_id': invoice_line.id,
            'base_seats': product.subscription_tier_id.default_seats if product.ams_product_type == 'enterprise' else 0,
            'auto_renew': product.subscription_tier_id.auto_renew if product.subscription_tier_id else True,
            'is_free': product.subscription_tier_id.is_free if product.subscription_tier_id else False,
            'allow_modifications': product.allow_mid_cycle_changes,
            'allow_pausing': product.allow_pausing,
        }
        
        subscription = self.env['ams.subscription'].create(subscription_vals)
        
        # Update partner with active subscription info
        self._update_partner_subscription_status(partner, subscription)
        
        # Create payment history record
        self._create_payment_history(subscription, invoice_line, 'success')
        
        subscription.message_post(body=f"Subscription created from invoice payment: {invoice_line.move_id.name}")
        
        return subscription

    def _update_partner_subscription_status(self, partner, subscription):
        """Update partner record with active subscription information"""
        # Update partner's current subscription info
        if subscription.subscription_type == 'individual':
            partner.current_individual_subscription_id = subscription.id
        elif subscription.subscription_type == 'enterprise':
            partner.current_enterprise_subscription_id = subscription.id
        
        # Update membership status
        partner._compute_membership_status()

    def _create_payment_history(self, subscription, invoice_line, status):
        """Create payment history record for tracking"""
        self.env['ams.payment.history'].create({
            'subscription_id': subscription.id,
            'invoice_id': invoice_line.move_id.id,
            'invoice_line_id': invoice_line.id,
            'payment_date': fields.Datetime.now(),
            'amount': invoice_line.price_subtotal,
            'payment_status': status,
            'payment_method': 'invoice',  # Could be enhanced to track actual payment method
        })

    def _calculate_end_date(self, start_date, period):
        """Calculate end date based on subscription period"""
        from dateutil.relativedelta import relativedelta
        from datetime import timedelta, date
        
        if period == 'monthly':
            return start_date + relativedelta(months=1) - timedelta(days=1)
        elif period == 'quarterly':
            return start_date + relativedelta(months=3) - timedelta(days=1)
        elif period == 'semi_annual':
            return start_date + relativedelta(months=6) - timedelta(days=1)
        elif period == 'annual':
            # Annual subscriptions run calendar year or anniversary year
            return start_date + relativedelta(years=1) - timedelta(days=1)
        else:
            return start_date + relativedelta(years=1) - timedelta(days=1)