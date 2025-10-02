# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MembershipQuickSetupWizard(models.TransientModel):
    """
    One-click setup wizard for membership products
    Creates: Category → Product → Subscription Plan → Links everything
    
    This simplifies membership setup dramatically - users just fill one form
    and get a complete, ready-to-use membership configuration.
    """
    _name = 'membership.quick.setup.wizard'
    _description = 'Quick Membership Setup'

    # ==========================================
    # STEP 1: MEMBERSHIP TYPE
    # ==========================================
    
    membership_type = fields.Selection([
        ('individual', 'Individual Membership'),
        ('organizational', 'Organization Membership'),
        ('chapter', 'Chapter Membership'),
        ('seat', 'Organization Seat Add-on'),
    ], string='Membership Type', required=True, default='individual',
       help='What type of membership are you creating?')
    
    # ==========================================
    # STEP 2: BASIC INFO
    # ==========================================
    
    name = fields.Char(
        string='Membership Name', 
        required=True,
        help='E.g., "Standard Individual Member", "Premium Organization"'
    )
    
    code = fields.Char(
        string='Code', 
        required=True,
        help='Short unique code, e.g., "IND_STD", "ORG_PREM"'
    )
    
    description = fields.Text(
        string='Description',
        help='Describe what this membership includes'
    )
    
    # ==========================================
    # STEP 3: PRICING
    # ==========================================
    
    price = fields.Float(
        string='Price', 
        required=True, 
        default=100.0,
        help='Membership price'
    )
    
    billing_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Billing Period', default='yearly', required=True)
    
    billing_type = fields.Selection([
        ('anniversary', 'Anniversary-based'),
        ('calendar', 'Calendar-based'),
    ], string='Billing Type', default='anniversary', required=True,
       help='Anniversary: bills from signup date. Calendar: aligns to calendar periods.')
    
    # ==========================================
    # STEP 4: TRIAL
    # ==========================================
    
    has_trial = fields.Boolean(
        string='Offer Trial Period', 
        default=False
    )
    
    trial_days = fields.Integer(
        string='Trial Days', 
        default=14,
        help='Number of days for free trial'
    )
    
    # ==========================================
    # STEP 5: ORGANIZATION-SPECIFIC
    # ==========================================
    
    includes_seats = fields.Integer(
        string='Included Seats', 
        default=5,
        help='Number of user seats included (for organization memberships)'
    )
    
    max_seats = fields.Integer(
        string='Maximum Seats',
        compute='_compute_max_seats',
        readonly=False,
        store=True,
        help='Maximum total seats allowed (0 = unlimited)'
    )
    
    create_seat_addon = fields.Boolean(
        string='Create Additional Seat Product',
        default=True,
        help='Create a separate product for purchasing additional seats'
    )
    
    seat_price = fields.Float(
        string='Price per Additional Seat',
        compute='_compute_seat_price',
        readonly=False,
        store=True,
        help='Price for each additional seat beyond included seats'
    )
    
    @api.depends('includes_seats')
    def _compute_max_seats(self):
        """Set default max seats to match included seats"""
        for wizard in self:
            if wizard.includes_seats > 0:
                wizard.max_seats = wizard.includes_seats
            else:
                wizard.max_seats = 0
    
    @api.depends('price', 'includes_seats')
    def _compute_seat_price(self):
        """Calculate per-seat price based on total price"""
        for wizard in self:
            if wizard.includes_seats > 0:
                # Add 20% premium over pro-rated base price
                base_per_seat = wizard.price / wizard.includes_seats
                wizard.seat_price = base_per_seat * 1.2
            else:
                wizard.seat_price = wizard.price / 5  # Default to 5 seats
    
    # ==========================================
    # STEP 6: FEATURES (Simple Checkboxes)
    # ==========================================
    
    has_portal_access = fields.Boolean(
        string='Portal Access', 
        default=True,
        help='Members can access online portal'
    )
    
    has_directory = fields.Boolean(
        string='Directory Listing', 
        default=True,
        help='Members appear in member directory'
    )
    
    has_events = fields.Boolean(
        string='Event Access', 
        default=True,
        help='Members can register for events'
    )
    
    has_publications = fields.Boolean(
        string='Publication Access', 
        default=True,
        help='Members get access to publications'
    )
    
    has_networking = fields.Boolean(
        string='Networking Tools',
        default=True,
        help='Members can use networking features'
    )
    
    # ==========================================
    # STEP 7: CLASSIFICATION
    # ==========================================
    
    is_voting_member = fields.Boolean(
        string='Voting Rights',
        default=True,
        help='Members in this category can vote'
    )
    
    is_full_member = fields.Boolean(
        string='Full Membership',
        default=True,
        help='This is a full membership (vs associate/affiliate)'
    )
    
    # ==========================================
    # MAIN ACTION
    # ==========================================

    def action_create_membership(self):
        """Create everything in one go"""
        self.ensure_one()
        
        # Validate
        self._validate_setup()
        
        # 1. Create Category
        category = self._create_category()
        
        # 2. Create Product
        product = self._create_product(category)
        
        # 3. Create Subscription Plan
        plan = self._create_subscription_plan(product)
        
        # 4. Link category to product
        category.default_product_id = product.id
        
        # 5. Create seat add-on if organization membership
        seat_product = False
        if self.membership_type == 'organizational' and self.create_seat_addon:
            seat_product = self._create_seat_addon(product, plan)
        
        # 6. Show success message and open product
        return self._show_success_action(product, seat_product)
    
    def _validate_setup(self):
        """Validate wizard inputs"""
        # Check for duplicate code
        existing_category = self.env['membership.category'].search([
            ('code', '=', self.code)
        ], limit=1)
        
        if existing_category:
            raise ValidationError(
                _('A membership category with code "%s" already exists. Please use a different code.') 
                % self.code
            )
        
        # Validate prices
        if self.price <= 0:
            raise ValidationError(_('Price must be greater than zero.'))
        
        if self.membership_type == 'organizational':
            if self.includes_seats <= 0:
                raise ValidationError(_('Organization memberships must include at least 1 seat.'))
            
            if self.max_seats > 0 and self.max_seats < self.includes_seats:
                raise ValidationError(_(
                    'Maximum seats (%s) cannot be less than included seats (%s).'
                ) % (self.max_seats, self.includes_seats))
    
    def _create_category(self):
        """Create membership category"""
        return self.env['membership.category'].create({
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'category_type': self.membership_type,
            'is_voting_member': self.is_voting_member,
            'is_full_member': self.is_full_member,
            'sequence': 10,
        })
    
    def _create_product(self, category):
        """Create product template with features"""
        
        # Collect feature IDs based on checkboxes
        feature_ids = []
        if self.has_portal_access:
            feature = self.env.ref('membership_community.feature_portal_access', raise_if_not_found=False)
            if feature:
                feature_ids.append(feature.id)
        
        if self.has_directory:
            feature = self.env.ref('membership_community.feature_directory', raise_if_not_found=False)
            if feature:
                feature_ids.append(feature.id)
        
        if self.has_events:
            feature = self.env.ref('membership_community.feature_event_registration', raise_if_not_found=False)
            if feature:
                feature_ids.append(feature.id)
        
        if self.has_publications:
            feature = self.env.ref('membership_community.feature_publications', raise_if_not_found=False)
            if feature:
                feature_ids.append(feature.id)
        
        if self.has_networking:
            feature = self.env.ref('membership_community.feature_networking', raise_if_not_found=False)
            if feature:
                feature_ids.append(feature.id)
        
        # Collect benefit IDs (use default benefits)
        benefit_ids = []
        for benefit_ref in ['benefit_member_support', 'benefit_networking_events', 
                           'benefit_publication_access', 'benefit_directory_listing']:
            benefit = self.env.ref(f'membership_community.{benefit_ref}', raise_if_not_found=False)
            if benefit:
                benefit_ids.append(benefit.id)
        
        # Determine subscription product type
        if self.membership_type == 'organizational':
            sub_type = 'organizational_membership'
        elif self.membership_type == 'seat':
            sub_type = 'membership'  # Seats use base membership type
        else:
            sub_type = self.membership_type
        
        return self.env['product.template'].create({
            'name': self.name,
            'type': 'service',
            'list_price': self.price,
            'description': self.description,
            'is_membership_product': True,
            'is_subscription': True,
            'subscription_product_type': sub_type,
            'default_member_category_id': category.id,
            'portal_access_level': 'standard',
            'feature_ids': [(6, 0, feature_ids)],
            'benefit_ids': [(6, 0, benefit_ids)],
        })
    
    def _create_subscription_plan(self, product):
        """Create subscription plan"""
        
        plan_name = f"{self.name}"
        if self.billing_period != 'yearly':
            plan_name += f" - {self.billing_period.title()}"
        
        plan_vals = {
            'name': plan_name,
            'code': self.code,
            'product_template_id': product.id,
            'price': self.price,
            'billing_period': self.billing_period,
            'billing_interval': 1,
            'billing_type': self.billing_type,
            'auto_renew': True,
            'sequence': 10,
        }
        
        # Add trial configuration
        if self.has_trial:
            plan_vals.update({
                'trial_period': self.trial_days,
                'trial_price': 0.0,
            })
        
        # Add seat configuration for organizational memberships
        if self.membership_type == 'organizational':
            plan_vals.update({
                'supports_seats': True,
                'included_seats': self.includes_seats,
                'max_seats': self.max_seats,
                'additional_seat_price': self.seat_price,
            })
        
        return self.env['subscription.plan'].create(plan_vals)
    
    def _create_seat_addon(self, parent_product, parent_plan):
        """Create additional seat product for organizations"""
        
        # Create seat category
        seat_category = self.env['membership.category'].create({
            'name': f"{self.name} - Additional Seat",
            'code': f"{self.code}_SEAT",
            'category_type': 'seat',
            'is_voting_member': False,
            'is_full_member': False,
        })
        
        # Create seat product
        seat_product = self.env['product.template'].create({
            'name': f"{self.name} - Additional Seat",
            'type': 'service',
            'list_price': self.seat_price,
            'description': f"Additional user seat for {self.name}",
            'is_membership_product': True,
            'is_subscription': True,
            'subscription_product_type': 'membership',
            'default_member_category_id': seat_category.id,
            'portal_access_level': 'standard',
        })
        
        # Link to category
        seat_category.default_product_id = seat_product.id
        
        # Create plan for seats
        seat_plan = self.env['subscription.plan'].create({
            'name': f"{self.name} - Additional Seat",
            'code': f"{self.code}_SEAT",
            'product_template_id': seat_product.id,
            'price': self.seat_price,
            'billing_period': self.billing_period,
            'billing_interval': 1,
            'billing_type': self.billing_type,
        })
        
        # Link seat product to parent plan
        parent_plan.seat_product_id = seat_product.id
        
        return seat_product
    
    def _show_success_action(self, product, seat_product=False):
        """Show success message and open product"""
        
        message = f'✅ Membership "{self.name}" created successfully!\n\n'
        message += f'📦 Product: {product.name}\n'
        message += f'💰 Price: {self.price} / {self.billing_period}\n'
        
        if self.membership_type == 'organizational':
            message += f'\n👥 Included Seats: {self.includes_seats}\n'
            message += f'📊 Maximum Seats: {self.max_seats if self.max_seats > 0 else "Unlimited"}\n'
        
        if seat_product:
            message += f'\n👤 Additional Seat Product: {seat_product.name}\n'
            message += f'💰 Seat Price: {self.seat_price} / {self.billing_period}\n'
        
        message += f'\n✨ You can now start selling this membership!'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success!'),
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'product.template',
                    'res_id': product.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            }
        }