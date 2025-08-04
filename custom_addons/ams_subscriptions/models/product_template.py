# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import timedelta, date


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Main subscription field - this is what users interact with
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

    # Subscription period configuration
    subscription_period = fields.Selection([
        ('none', 'Not Applicable'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Subscription Period', default='annual',
       help='How often customers will be billed for this subscription')

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

    # Enterprise seat configuration
    is_seat_addon = fields.Boolean(
        string='Enterprise Seat Add-On',
        help='This product adds seats to existing enterprise subscriptions'
    )

    # Publication-specific fields
    is_digital = fields.Boolean(
        string='Digital Publication',
        help='This is a digital publication (not physical)'
    )
    
    publication_type = fields.Selection([
        ('journal', 'Journal'),
        ('magazine', 'Magazine'),
        ('newsletter', 'Newsletter'),
        ('report', 'Report'),
        ('book', 'Book'),
        ('other', 'Other'),
    ], string='Publication Type')

    # Lifecycle settings (can override tier defaults)
    grace_days = fields.Integer(
        string='Grace Period (Days)',
        default=30,
        help='Grace period for this product (overrides tier setting if set)'
    )
    
    suspend_days = fields.Integer(
        string='Suspension Period (Days)',
        default=60,
        help='Suspension period for this product (overrides tier setting if set)'
    )
    
    terminate_days = fields.Integer(
        string='Termination Period (Days)',
        default=30,
        help='Termination period for this product (overrides tier setting if set)'
    )

    # Statistics fields
    active_subscriptions_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_subscription_stats',
        help='Number of active subscriptions for this product'
    )
    
    total_revenue_ytd = fields.Float(
        string='Revenue YTD',
        compute='_compute_subscription_stats',
        help='Total revenue year-to-date from this product'
    )

    # Payment failure tracking - compute every time they're accessed
    nsf_flag = fields.Boolean(
        string='NSF Flag',
        help='This product has payment failures',
        compute='_compute_payment_flags',
        store=False  # Don't store, compute fresh each time
    )
    
    last_payment_failure_date = fields.Datetime(
        string='Last Payment Failure',
        compute='_compute_payment_flags',
        store=False  # Don't store, compute fresh each time
    )

    @api.depends('is_subscription_product')
    def _compute_ams_product_type(self):
        for product in self:
            if not product.is_subscription_product:
                product.ams_product_type = 'none'
            elif product.ams_product_type == 'none':
                product.ams_product_type = 'individual'  # Default to individual

    @api.depends('ams_product_type')
    def _compute_subscription_stats(self):
        """Compute subscription statistics for this product"""
        for product in self:
            if product.ams_product_type == 'none':
                product.active_subscriptions_count = 0
                product.total_revenue_ytd = 0.0
            else:
                # Count active subscriptions
                active_subs = self.env['ams.subscription'].search_count([
                    ('product_id.product_tmpl_id', '=', product.id),
                    ('state', '=', 'active')
                ])
                product.active_subscriptions_count = active_subs
                
                # Calculate YTD revenue (simplified)
                product.total_revenue_ytd = active_subs * product.list_price

    # No @api.depends decorator since we're searching records directly
    def _compute_payment_flags(self):
        """Compute payment failure flags by searching payment history"""
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
            if self.subscription_period == 'none':
                self.subscription_period = 'annual'
                
            # Auto-set category
            self._set_ams_category()
            
            # Show a helpful message
            return {
                'warning': {
                    'title': 'Subscription Product Enabled',
                    'message': 'This product will now create subscriptions when purchased. Configure the subscription type and tier below.'
                }
            }
        else:
            # Reset subscription-related fields
            self.ams_product_type = 'none'
            self.subscription_tier_id = False
            self.subscription_period = 'none'

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
                self.is_digital = True  # Default to digital
                self.subscription_period = 'monthly' if not self.subscription_period or self.subscription_period == 'none' else self.subscription_period
            elif self.ams_product_type == 'enterprise':
                # Enterprise memberships typically don't allow pausing
                self.allow_pausing = False
                self.subscription_period = 'annual' if not self.subscription_period or self.subscription_period == 'none' else self.subscription_period
            elif self.ams_product_type == 'chapter':
                # Chapters are typically annual
                self.subscription_period = 'annual' if not self.subscription_period or self.subscription_period == 'none' else self.subscription_period
            
            # Update category
            self._set_ams_category()

    def _set_ams_category(self):
        """Set appropriate product category for AMS products"""
        if not self.is_subscription_product:
            return
            
        category_obj = self.env['product.category']
        
        category_mapping = {
            'individual': 'Individual Memberships',
            'enterprise': 'Enterprise Memberships', 
            'chapter': 'Chapters',
            'publication': 'Digital Publications' if self.is_digital else 'Print Publications'
        }
        
        if self.ams_product_type in category_mapping:
            category_name = category_mapping[self.ams_product_type]
            category = category_obj.search([('name', '=', category_name)], limit=1)
            if not category:
                category = category_obj.create({'name': category_name})
            self.categ_id = category.id

    def action_view_subscriptions(self):
        """Action to view subscriptions for this product"""
        self.ensure_one()
        
        return {
            'name': f'Subscriptions for {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription',
            'view_mode': 'list,form',
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
            'context': {
                'default_product_id': self.product_variant_id.id if self.product_variant_id else False,
                'search_default_active': 1,
            }
        }

    def action_configure_subscription_tier(self):
        """Smart action to create or configure subscription tier"""
        self.ensure_one()
        
        if not self.is_subscription_product:
            raise UserError("This is not a subscription product. Please check 'Subscription Product' first.")
        
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
                'period_length': self.subscription_period if self.subscription_period != 'none' else 'annual',
            }
            
            return {
                'type': 'ir.actions.act_window',
                'name': 'Create Subscription Tier',
                'res_model': 'ams.subscription.tier',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_' + k: v for k, v in tier_vals.items()},
            }

    def action_quick_setup_subscription(self):
        """Quick setup wizard for subscription products"""
        self.ensure_one()
        
        if not self.is_subscription_product:
            raise UserError("This is not a subscription product.")
        
        # This could open a wizard for quick setup
        # For now, just redirect to tier configuration
        return self.action_configure_subscription_tier()

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
            'paid_through_date': self._calculate_end_date(start_date, product.subscription_period or 'annual'),
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

    def _handle_seat_addon_payment(self, invoice_line):
        """Add seats to existing enterprise subscription"""
        partner = invoice_line.move_id.partner_id
        
        # Find active enterprise subscription for this partner
        enterprise_sub = self.env['ams.subscription'].search([
            ('partner_id', '=', partner.id),
            ('subscription_type', '=', 'enterprise'),
            ('state', '=', 'active'),
        ], limit=1)
        
        if enterprise_sub:
            seats_to_add = int(invoice_line.quantity)
            enterprise_sub.extra_seats += seats_to_add
            enterprise_sub.message_post(
                body=f"{seats_to_add} seats added via invoice payment: {invoice_line.move_id.name}"
            )
            return enterprise_sub
        else:
            # No active enterprise subscription found - log warning
            invoice_line.move_id.message_post(
                body="Warning: Seat add-on purchased but no active enterprise subscription found."
            )
            return False

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
    def action_publish_ams_product(self):
        """Publish/unpublish AMS product on website"""
        self.ensure_one()
    
        if not self.is_subscription_product:
            raise UserError("Only subscription products can be published to AMS.")
    
        # Toggle the website published status
        self.website_published = not self.website_published
    
        action_type = "published" if self.website_published else "unpublished"
    
        # Log the action
        self.message_post(
            body=f"Product {action_type} on website by {self.env.user.name}"
        )
    
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Product successfully {action_type}!',
                'type': 'success',
            }
        }