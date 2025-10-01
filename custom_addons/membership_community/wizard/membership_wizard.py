# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class MembershipWizard(models.TransientModel):
    _name = 'membership.wizard'
    _description = 'Membership Creation and Management Wizard'

    # ==========================================
    # ACTION TYPE
    # ==========================================
    
    action_type = fields.Selection([
        ('create', 'Create New Membership'),
        ('renew', 'Renew Membership'),
        ('upgrade', 'Upgrade Membership'),
        ('downgrade', 'Downgrade Membership'),
        ('add_chapter', 'Add Chapter Membership'),
    ], string='Action', required=True, default='create')

    # ==========================================
    # PARTNER INFORMATION
    # ==========================================
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        domain=[('is_company', '=', False)],
        help='Individual or organization to create membership for'
    )
    
    is_organizational = fields.Boolean(
        string='Organizational Membership',
        help='Check if this is for an organization with multiple seats'
    )
    
    organization_id = fields.Many2one(
        'res.partner',
        string='Organization',
        domain=[('is_company', '=', True)],
        help='Parent organization for organizational memberships'
    )

    # ==========================================
    # MEMBERSHIP CATEGORY
    # ==========================================
    
    membership_category_id = fields.Many2one(
        'membership.category',
        string='Member Category',
        required=True,
        help='Type of membership (Individual, Student, Corporate, etc.)'
    )
    
    available_categories = fields.Many2many(
        'membership.category',
        compute='_compute_available_categories',
        string='Available Categories'
    )

    # ==========================================
    # PRODUCT SELECTION
    # ==========================================
    
    product_id = fields.Many2one(
        'product.template',
        string='Membership Product',
        required=True,
        domain=[('is_membership_product', '=', True)],
        help='Membership product/plan to subscribe to'
    )
    
    available_products = fields.Many2many(
        'product.template',
        compute='_compute_available_products',
        string='Available Products'
    )
    
    subscription_product_type = fields.Selection(
        related='product_id.subscription_product_type',
        string='Product Type',
        readonly=True
    )

    # ==========================================
    # CURRENT MEMBERSHIP (for upgrades/renewals)
    # ==========================================
    
    current_subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Current Membership',
        help='Existing membership subscription'
    )
    
    current_category_id = fields.Many2one(
        'membership.category',
        string='Current Category',
        help='Current member category'
    )

    # ==========================================
    # SUBSCRIPTION SETTINGS
    # ==========================================
    
    start_date = fields.Date(
        string='Start Date',
        default=fields.Date.today,
        required=True
    )
    
    use_trial = fields.Boolean(
        string='Start with Trial Period',
        compute='_compute_trial_settings',
        store=True
    )
    
    trial_period = fields.Integer(
        string='Trial Period (days)',
        compute='_compute_trial_settings',
        store=True
    )

    # ==========================================
    # ORGANIZATIONAL SETTINGS
    # ==========================================
    
    number_of_seats = fields.Integer(
        string='Number of Seats',
        default=1,
        help='Number of individual memberships included'
    )
    
    seat_members_ids = fields.Many2many(
        'res.partner',
        'membership_wizard_seat_member_rel',
        'wizard_id',
        'partner_id',
        string='Seat Members',
        domain=[('is_company', '=', False)],
        help='Individual members to assign to organizational seats'
    )

    # ==========================================
    # CHAPTER MEMBERSHIP
    # ==========================================
    
    is_chapter_membership = fields.Boolean(
        related='product_id.is_chapter_membership',
        string='Is Chapter Membership',
        readonly=True
    )
    
    requires_primary_membership = fields.Boolean(
        related='product_id.requires_primary_membership',
        string='Requires Primary',
        readonly=True
    )
    
    primary_membership_valid = fields.Boolean(
        string='Has Valid Primary',
        compute='_compute_primary_membership_valid'
    )

    # ==========================================
    # PRICING
    # ==========================================
    
    list_price = fields.Float(
        string='Standard Price',
        related='product_id.list_price',
        readonly=True
    )
    
    discount_percent = fields.Float(
        string='Discount %',
        compute='_compute_discount',
        store=True
    )
    
    discounted_price = fields.Float(
        string='Price After Discount',
        compute='_compute_discounted_price',
        store=True
    )
    
    override_price = fields.Boolean(
        string='Override Price',
        default=False
    )
    
    custom_price = fields.Float(
        string='Custom Price'
    )

    # ==========================================
    # ELIGIBILITY & VERIFICATION
    # ==========================================
    
    requires_verification = fields.Boolean(
        string='Requires Verification',
        related='membership_category_id.requires_verification',
        readonly=True
    )
    
    eligibility_verified = fields.Boolean(
        string='Eligibility Verified',
        default=False
    )
    
    verification_notes = fields.Text(
        string='Verification Notes'
    )

    # ==========================================
    # OPTIONS
    # ==========================================
    
    create_invoice = fields.Boolean(
        string='Create Invoice Immediately',
        default=True
    )
    
    send_welcome_email = fields.Boolean(
        string='Send Welcome Email',
        default=True
    )
    
    auto_activate = fields.Boolean(
        string='Auto-Activate',
        default=True,
        help='Automatically activate membership after creation'
    )

    # ==========================================
    # RESULT
    # ==========================================
    
    result_subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Created Subscription',
        readonly=True
    )
    
    result_invoice_id = fields.Many2one(
        'account.move',
        string='Created Invoice',
        readonly=True
    )

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.depends('partner_id', 'membership_category_id')
    def _compute_available_categories(self):
        """Get categories available to this partner"""
        for wizard in self:
            if wizard.partner_id:
                # Check eligibility for each category
                all_categories = self.env['membership.category'].search([
                    ('active', '=', True)
                ])
                
                available = self.env['membership.category']
                for category in all_categories:
                    is_eligible, reasons = category.check_eligibility(wizard.partner_id)
                    if is_eligible:
                        available |= category
                
                wizard.available_categories = available
            else:
                wizard.available_categories = False

    @api.depends('membership_category_id', 'action_type')
    def _compute_available_products(self):
        """Get products available for selected category"""
        for wizard in self:
            if wizard.membership_category_id:
                products = wizard.membership_category_id.get_available_products()
                
                # Filter by action type
                if wizard.action_type == 'add_chapter':
                    products = products.filtered(
                        lambda p: p.subscription_product_type == 'chapter'
                    )
                elif wizard.action_type in ['create', 'renew']:
                    products = products.filtered(
                        lambda p: p.subscription_product_type in ['membership', 'organizational_membership']
                    )
                
                wizard.available_products = products
            else:
                wizard.available_products = False

    @api.depends('product_id')
    def _compute_trial_settings(self):
        """Get trial settings from product's subscription plan"""
        for wizard in self:
            if wizard.product_id and wizard.product_id.subscription_plan_ids:
                plan = wizard.product_id.subscription_plan_ids[0]
                wizard.use_trial = plan.trial_period > 0
                wizard.trial_period = plan.trial_period
            else:
                wizard.use_trial = False
                wizard.trial_period = 0

    @api.depends('partner_id', 'product_id')
    def _compute_primary_membership_valid(self):
        """Check if partner has valid primary membership for chapter"""
        for wizard in self:
            if wizard.requires_primary_membership and wizard.partner_id:
                # Check if partner has active primary membership
                primary_products = wizard.product_id.primary_membership_product_ids
                
                has_primary = bool(
                    wizard.partner_id.membership_subscription_ids.filtered(
                        lambda s: s.state in ['open', 'active'] and
                                 s.product_id in primary_products.mapped('product_variant_ids')
                    )
                )
                wizard.primary_membership_valid = has_primary
            else:
                wizard.primary_membership_valid = True

    @api.depends('membership_category_id')
    def _compute_discount(self):
        """Calculate discount based on category"""
        for wizard in self:
            if wizard.membership_category_id:
                wizard.discount_percent = wizard.membership_category_id.typical_discount_percent
            else:
                wizard.discount_percent = 0.0

    @api.depends('list_price', 'discount_percent', 'override_price', 'custom_price')
    def _compute_discounted_price(self):
        """Calculate final price after discount"""
        for wizard in self:
            if wizard.override_price:
                wizard.discounted_price = wizard.custom_price
            elif wizard.discount_percent > 0:
                discount_amount = wizard.list_price * (wizard.discount_percent / 100)
                wizard.discounted_price = wizard.list_price - discount_amount
            else:
                wizard.discounted_price = wizard.list_price

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================

    @api.onchange('action_type')
    def _onchange_action_type(self):
        """Update fields based on action type"""
        if self.action_type in ['renew', 'upgrade', 'downgrade']:
            # Get current subscription from context or partner
            subscription_id = self.env.context.get('active_id')
            if subscription_id:
                subscription = self.env['subscription.subscription'].browse(subscription_id)
                self.current_subscription_id = subscription
                self.partner_id = subscription.partner_id
                self.current_category_id = subscription.membership_category_id
        
        if self.action_type == 'add_chapter':
            # For chapter, keep current category
            if self.partner_id and self.partner_id.membership_category_id:
                self.membership_category_id = self.partner_id.membership_category_id

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Update organization flag and category suggestions"""
        if self.partner_id:
            self.is_organizational = self.partner_id.is_company
            
            # Suggest current category if partner is already a member
            if self.partner_id.membership_category_id:
                self.membership_category_id = self.partner_id.membership_category_id

    @api.onchange('membership_category_id')
    def _onchange_membership_category_id(self):
        """Update product suggestions based on category"""
        if self.membership_category_id:
            # Suggest default product for category
            if self.membership_category_id.default_product_id:
                self.product_id = self.membership_category_id.default_product_id

    @api.onchange('is_organizational')
    def _onchange_is_organizational(self):
        """Update seat settings for organizational memberships"""
        if not self.is_organizational:
            self.number_of_seats = 1
            self.seat_members_ids = False

    # ==========================================
    # CONSTRAINT METHODS
    # ==========================================

    @api.constrains('number_of_seats', 'seat_members_ids')
    def _check_seat_members(self):
        """Validate seat members don't exceed number of seats"""
        for wizard in self:
            if wizard.is_organizational:
                if len(wizard.seat_members_ids) > wizard.number_of_seats:
                    raise ValidationError(_(
                        'Number of seat members (%s) cannot exceed number of seats (%s).'
                    ) % (len(wizard.seat_members_ids), wizard.number_of_seats))

    @api.constrains('partner_id', 'membership_category_id')
    def _check_eligibility(self):
        """Validate partner is eligible for selected category"""
        for wizard in self:
            if wizard.partner_id and wizard.membership_category_id:
                is_eligible, reasons = wizard.membership_category_id.check_eligibility(
                    wizard.partner_id
                )
                
                if not is_eligible and not wizard.eligibility_verified:
                    raise ValidationError(_(
                        'Partner is not eligible for category "%s":\n%s\n\n'
                        'Please verify eligibility or choose another category.'
                    ) % (wizard.membership_category_id.name, '\n'.join(reasons)))

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_create_membership(self):
        """Main action to create or manage membership"""
        self.ensure_one()
        
        if self.action_type == 'create':
            return self._action_create()
        elif self.action_type == 'renew':
            return self._action_renew()
        elif self.action_type == 'upgrade':
            return self._action_upgrade()
        elif self.action_type == 'downgrade':
            return self._action_downgrade()
        elif self.action_type == 'add_chapter':
            return self._action_add_chapter()

    def _action_create(self):
        """Create new membership subscription"""
        self.ensure_one()
        
        # Validate
        self._validate_creation()
        
        # Check for existing active membership
        existing = self.env['subscription.subscription'].search([
            ('partner_id', '=', self.partner_id.id),
            ('product_id', 'in', self.product_id.product_variant_ids.ids),
            ('state', 'in', ['active', 'trial', 'open'])
        ])
        
        if existing:
            raise UserError(_(
                'Partner already has an active membership subscription (%s) for this product. '
                'Please use Renew or Upgrade actions instead.'
            ) % existing[0].name)
        
        # Create subscription
        subscription = self._create_subscription()
        
        # Create invoice if requested
        if self.create_invoice:
            invoice = subscription._create_initial_invoice()
            self.result_invoice_id = invoice
        
        # Activate if requested
        if self.auto_activate:
            if self.use_trial:
                subscription.action_start_trial()
            else:
                subscription.action_activate()
        
        # Send welcome email
        if self.send_welcome_email:
            self._send_welcome_email(subscription)
        
        self.result_subscription_id = subscription
        
        return self._return_success_action()

    def _action_renew(self):
        """Renew existing membership"""
        self.ensure_one()
        
        if not self.current_subscription_id:
            raise UserError(_('No current subscription to renew.'))
        
        # Use subscription's renew method
        self.current_subscription_id.action_renew()
        
        # Send renewal confirmation
        if self.send_welcome_email:
            template = self.env.ref(
                'subscription_management.email_template_subscription_reactivated',
                raise_if_not_found=False
            )
            if template:
                template.send_mail(self.current_subscription_id.id, force_send=False)
        
        self.result_subscription_id = self.current_subscription_id
        
        return self._return_success_action()

    def _action_upgrade(self):
        """Upgrade membership to higher tier"""
        self.ensure_one()
        
        if not self.current_subscription_id:
            raise UserError(_('No current subscription to upgrade.'))
        
        # Create new subscription with upgraded product
        new_subscription = self._create_subscription()
        
        # Cancel old subscription
        self.current_subscription_id.write({
            'date_end': fields.Date.today(),
        })
        self.current_subscription_id.action_cancel()
        
        # Link in chatter
        new_subscription.message_post(
            body=_('Upgraded from subscription %s') % self.current_subscription_id.name,
            message_type='notification'
        )
        
        self.current_subscription_id.message_post(
            body=_('Upgraded to subscription %s') % new_subscription.name,
            message_type='notification'
        )
        
        # Activate new subscription
        if self.auto_activate:
            new_subscription.action_activate()
        
        self.result_subscription_id = new_subscription
        
        return self._return_success_action()

    def _action_downgrade(self):
        """Downgrade membership to lower tier"""
        self.ensure_one()
        
        if not self.current_subscription_id:
            raise UserError(_('No current subscription to downgrade.'))
        
        # Similar to upgrade but different messaging
        new_subscription = self._create_subscription()
        
        # Mark old subscription to end at current period
        self.current_subscription_id.write({
            'date_end': self.current_subscription_id.date_end or fields.Date.today(),
        })
        
        # Link in chatter
        new_subscription.message_post(
            body=_('Downgraded from subscription %s') % self.current_subscription_id.name,
            message_type='notification'
        )
        
        self.result_subscription_id = new_subscription
        
        return self._return_success_action()

    def _action_add_chapter(self):
        """Add chapter membership to existing member"""
        self.ensure_one()
        
        # Validate primary membership
        if self.requires_primary_membership and not self.primary_membership_valid:
            raise UserError(_(
                'Partner must have an active primary membership to join this chapter.'
            ))
        
        # Create chapter subscription
        subscription = self._create_subscription()
        
        # Activate immediately
        if self.auto_activate:
            subscription.action_activate()
        
        self.result_subscription_id = subscription
        
        return self._return_success_action()

    # ==========================================
    # HELPER METHODS
    # ==========================================

    def _create_subscription(self):
        """Create subscription record"""
        self.ensure_one()
        
        # Get subscription plan
        plan = self.product_id.subscription_plan_ids[:1]
        if not plan:
            raise UserError(_(
                'Product %s does not have a subscription plan configured.'
            ) % self.product_id.name)
        
        # Prepare subscription values
        subscription_vals = {
            'partner_id': self.partner_id.id,
            'partner_invoice_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'plan_id': plan.id,
            'date_start': self.start_date,
            'state': 'draft',
            'membership_category_id': self.membership_category_id.id,
            'eligibility_verified': self.eligibility_verified,
            'eligibility_verified_by': self.env.user.id if self.eligibility_verified else False,
            'eligibility_verified_date': fields.Date.today() if self.eligibility_verified else False,
            'source_type': self._get_source_type(),
        }
        
        # Create subscription
        subscription = self.env['subscription.subscription'].create(subscription_vals)
        
        # Create subscription lines
        self._create_subscription_lines(subscription)
        
        # Handle organizational seats
        if self.is_organizational and self.number_of_seats > 1:
            self._create_seat_memberships(subscription)
        
        return subscription

    def _create_subscription_lines(self, subscription):
        """Create subscription line items"""
        self.ensure_one()
        
        # Main product line
        line_vals = {
            'subscription_id': subscription.id,
            'product_id': self.product_id.product_variant_ids[:1].id,
            'name': self.product_id.name,
            'quantity': 1,
            'price_unit': self.discounted_price,
        }
        
        self.env['subscription.line'].create(line_vals)

    def _create_seat_memberships(self, parent_subscription):
        """Create individual seat memberships for organizational membership"""
        self.ensure_one()
        
        # This would create additional subscription records for each seat member
        # Linking them to the parent organizational subscription
        
        for seat_member in self.seat_members_ids:
            seat_vals = {
                'partner_id': seat_member.id,
                'plan_id': parent_subscription.plan_id.id,
                'date_start': parent_subscription.date_start,
                'date_end': parent_subscription.date_end,
                'state': 'draft',
                'membership_category_id': self.membership_category_id.id,
                'parent_membership_id': parent_subscription.id,
                'is_seat_member': True,
            }
            
            seat_subscription = self.env['subscription.subscription'].create(seat_vals)
            
            # Activate seat subscription with parent
            if parent_subscription.state in ['active', 'trial']:
                seat_subscription.action_activate()

    def _get_source_type(self):
        """Get source type for subscription"""
        if self.action_type == 'create':
            return 'direct'
        elif self.action_type == 'renew':
            return 'renewal'
        elif self.action_type == 'upgrade':
            return 'upgrade'
        elif self.action_type == 'downgrade':
            return 'downgrade'
        elif self.action_type == 'add_chapter':
            return 'chapter'
        return 'admin'

    def _validate_creation(self):
        """Validate wizard data before creation"""
        self.ensure_one()
        
        if not self.partner_id:
            raise UserError(_('Please select a member.'))
        
        if not self.membership_category_id:
            raise UserError(_('Please select a member category.'))
        
        if not self.product_id:
            raise UserError(_('Please select a membership product.'))
        
        if self.requires_verification and not self.eligibility_verified:
            raise UserError(_(
                'This membership category requires eligibility verification. '
                'Please verify eligibility before creating the membership.'
            ))
        
        if self.is_chapter_membership and not self.primary_membership_valid:
            raise UserError(_(
                'Partner must have a valid primary membership to join this chapter.'
            ))

    def _send_welcome_email(self, subscription):
        """Send welcome email to new member"""
        template = self.env.ref(
            'subscription_management.email_template_subscription_welcome',
            raise_if_not_found=False
        )
        
        if template:
            try:
                template.send_mail(subscription.id, force_send=False)
                _logger.info(f'Sent welcome email for membership {subscription.name}')
            except Exception as e:
                _logger.error(f'Failed to send welcome email: {e}')

    def _return_success_action(self):
        """Return action to view created subscription"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Created'),
            'res_model': 'subscription.subscription',
            'res_id': self.result_subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }