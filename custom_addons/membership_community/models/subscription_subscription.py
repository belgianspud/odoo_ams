# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SubscriptionSubscription(models.Model):
    _inherit = 'subscription.subscription'

    # ==========================================
    # MEMBERSHIP CATEGORY
    # Store category on subscription for reporting
    # ==========================================
    
    membership_category_id = fields.Many2one(
        'membership.category',
        string='Member Category',
        help='Category assigned when subscription created',
        tracking=True
    )
    
    # ==========================================
    # PRODUCT HELPER FIELDS
    # Quick access to product fields
    # ==========================================
    
    product_id = fields.Many2one(
        'product.template',
        string='Product',
        related='plan_id.product_template_id',
        store=True,
        help='Product template from subscription plan'
    )
    
    subscription_product_type = fields.Selection(
        related='plan_id.product_template_id.subscription_product_type',
        string='Subscription Type',
        store=True,
        help='Type of subscription/membership'
    )
    
    # ==========================================
    # ELIGIBILITY TRACKING
    # ==========================================
    
    eligibility_verified = fields.Boolean(
        string='Eligibility Verified',
        default=False,
        help='Membership eligibility has been verified',
        tracking=True
    )
    
    eligibility_verified_by = fields.Many2one(
        'res.users',
        string='Verified By',
        help='User who verified eligibility'
    )
    
    eligibility_verified_date = fields.Date(
        string='Verification Date',
        help='Date when eligibility was verified'
    )
    
    requires_verification = fields.Boolean(
        string='Requires Verification',
        related='plan_id.product_template_id.requires_eligibility_verification',
        store=True,
        help='This membership requires eligibility verification'
    )
    
    # ==========================================
    # CHAPTER-SPECIFIC FIELDS
    # ==========================================
    
    requires_primary_membership = fields.Boolean(
        string='Requires Primary Membership',
        related='plan_id.product_template_id.requires_primary_membership',
        store=True,
        help='This chapter membership requires an active primary membership'
    )
    
    primary_membership_valid = fields.Boolean(
        string='Primary Membership Valid',
        compute='_compute_primary_membership_valid',
        store=True,
        help='Partner has valid primary membership (for chapters)'
    )
    
    primary_membership_ids = fields.Many2many(
        'subscription.subscription',
        compute='_compute_primary_memberships',
        string='Primary Memberships',
        help='Partner\'s primary memberships'
    )

    # ==========================================
    # APPROVAL WORKFLOW
    # ==========================================
    
    requires_approval = fields.Boolean(
        string='Requires Approval',
        related='plan_id.product_template_id.requires_approval',
        store=True,
        help='This membership requires staff approval'
    )
    
    approval_status = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Approval Status',
       default='approved',
       tracking=True,
       help='Approval status for memberships requiring approval')
    
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        help='User who approved this membership'
    )
    
    approval_date = fields.Date(
        string='Approval Date',
        help='Date when membership was approved'
    )
    
    rejection_reason = fields.Text(
        string='Rejection Reason',
        help='Reason for rejection'
    )

    # ==========================================
    # MEMBERSHIP-SPECIFIC DATA
    # ==========================================
    
    join_date = fields.Date(
        string='Original Join Date',
        help='Date when member first joined (for historical tracking)',
        tracking=True
    )
    
    membership_notes = fields.Text(
        string='Membership Notes',
        help='Internal notes about this membership'
    )
    
    source_type = fields.Selection([
        ('direct', 'Direct Signup'),
        ('renewal', 'Renewal'),
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('transfer', 'Transfer'),
        ('chapter', 'Chapter'),
        ('import', 'Data Import'),
        ('admin', 'Admin Created')
    ], string='Source Type',
       default='direct',
       tracking=True,
       help='How this membership was created')

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.depends('partner_id', 'plan_id.product_template_id.primary_membership_product_ids', 'state')
    def _compute_primary_membership_valid(self):
        """Check if partner has valid primary membership (for chapters)"""
        for subscription in self:
            if not subscription.requires_primary_membership:
                subscription.primary_membership_valid = True
            else:
                # Get primary membership products
                primary_products = subscription.plan_id.product_template_id.primary_membership_product_ids
                
                if not primary_products:
                    subscription.primary_membership_valid = False
                    continue
                
                # Check if partner has active primary membership
                valid = bool(
                    subscription.partner_id.membership_subscription_ids.filtered(
                        lambda s: s.state in ['trial', 'active'] and
                                 s.plan_id.product_template_id in primary_products and
                                 s.id != subscription.id  # Don't count self
                    )
                )
                subscription.primary_membership_valid = valid

    @api.depends('partner_id')
    def _compute_primary_memberships(self):
        """Get partner's primary memberships"""
        for subscription in self:
            if subscription.subscription_product_type == 'chapter':
                # Get primary memberships for this partner
                primaries = subscription.partner_id.membership_subscription_ids.filtered(
                    lambda s: s.state in ['trial', 'active'] and
                             s.subscription_product_type == 'membership'
                )
                subscription.primary_membership_ids = primaries
            else:
                subscription.primary_membership_ids = False

    # ==========================================
    # CRUD OVERRIDES
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set membership-specific defaults"""
        
        for vals in vals_list:
            # Get plan to check if it's a membership product
            plan_id = vals.get('plan_id')
            if plan_id:
                plan = self.env['subscription.plan'].browse(plan_id)
                product = plan.product_template_id
                
                if product.is_membership_product:
                    # Set join_date if not provided
                    if 'join_date' not in vals:
                        vals['join_date'] = vals.get('date_start', fields.Date.today())
                    
                    # Set default category from product if not provided
                    if 'membership_category_id' not in vals and product.default_member_category_id:
                        vals['membership_category_id'] = product.default_member_category_id.id
                    
                    # Set approval status for memberships requiring approval
                    if product.requires_approval and 'approval_status' not in vals:
                        vals['approval_status'] = 'pending'
                        # Set state to draft if requires approval
                        if 'state' not in vals:
                            vals['state'] = 'draft'
        
        subscriptions = super(SubscriptionSubscription, self).create(vals_list)
        
        # Auto-verify eligibility if not required
        for subscription in subscriptions:
            if subscription.plan_id.product_template_id.is_membership_product:
                if not subscription.requires_verification:
                    subscription.write({
                        'eligibility_verified': True,
                        'eligibility_verified_date': fields.Date.today(),
                    })
        
        return subscriptions

    def write(self, vals):
        """Override write to handle approval status changes"""
        
        # Handle approval
        if vals.get('approval_status') == 'approved':
            vals['approved_by'] = self.env.user.id
            vals['approval_date'] = fields.Date.today()
            # Activate subscription if it was pending
            if 'state' not in vals:
                for subscription in self:
                    if subscription.state == 'draft':
                        vals['state'] = 'trial' if subscription.plan_id.trial_period > 0 else 'active'
        
        return super(SubscriptionSubscription, self).write(vals)

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def action_approve_membership(self):
        """Approve pending membership"""
        for subscription in self:
            if subscription.approval_status != 'pending':
                raise ValidationError(_("Only pending memberships can be approved."))
            
            subscription.write({
                'approval_status': 'approved',
                'approved_by': self.env.user.id,
                'approval_date': fields.Date.today(),
                'state': 'trial' if subscription.plan_id.trial_period > 0 else 'active'
            })
            
            # Send approval notification
            subscription._send_approval_notification()
        
        return True

    def action_reject_membership(self):
        """Reject pending membership"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Membership'),
            'res_model': 'membership.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_ids': [(6, 0, self.ids)]}
        }

    def action_verify_eligibility(self):
        """Mark eligibility as verified"""
        for subscription in self:
            subscription.write({
                'eligibility_verified': True,
                'eligibility_verified_by': self.env.user.id,
                'eligibility_verified_date': fields.Date.today(),
            })
        
        return True

    def action_check_primary_membership(self):
        """Check primary membership requirements"""
        self.ensure_one()
        
        if not self.requires_primary_membership:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Primary Required'),
                    'message': _('This membership does not require a primary membership.'),
                    'type': 'info'
                }
            }
        
        if self.primary_membership_valid:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Valid'),
                    'message': _('Primary membership requirements are met.'),
                    'type': 'success'
                }
            }
        else:
            primary_products = self.plan_id.product_template_id.primary_membership_product_ids
            product_names = ', '.join(primary_products.mapped('name'))
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Invalid'),
                    'message': _('Primary membership requirements are NOT met. '
                               'Member needs an active primary membership from: %s') % product_names,
                    'type': 'warning',
                    'sticky': True
                }
            }

    def _send_approval_notification(self):
        """Send notification when membership is approved"""
        self.ensure_one()
        
        if not self.partner_id.email:
            return
        
        # This would send an email notification
        # Implementation depends on your email template setup
        template = self.env.ref(
            'membership_community.email_template_membership_approved',
            raise_if_not_found=False
        )
        
        if template:
            try:
                template.send_mail(self.id, force_send=True)
            except Exception as e:
                # Log error but don't fail
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error(f"Failed to send approval email for {self.name}: {e}")

    def get_available_benefits(self):
        """
        Get available benefits for this subscription
        
        Returns:
            recordset: membership.benefit records
        """
        self.ensure_one()
        return self.plan_id.product_template_id.benefit_ids

    def get_available_features(self):
        """
        Get available features for this subscription
        
        Returns:
            recordset: membership.feature records
        """
        self.ensure_one()
        return self.plan_id.product_template_id.feature_ids

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('state', 'requires_primary_membership', 'primary_membership_valid')
    def _check_primary_membership(self):
        """Validate primary membership requirements"""
        for subscription in self:
            if subscription.state in ['trial', 'active']:
                if subscription.requires_primary_membership:
                    if not subscription.primary_membership_valid:
                        primary_products = subscription.plan_id.product_template_id.primary_membership_product_ids
                        product_names = ', '.join(primary_products.mapped('name'))
                        
                        raise ValidationError(
                            _("Cannot activate chapter membership '%s'. "
                              "Partner must have an active primary membership from: %s") % (
                                subscription.plan_id.name,
                                product_names
                            )
                        )

    @api.constrains('state', 'approval_status', 'requires_approval')
    def _check_approval_status(self):
        """Validate approval requirements"""
        for subscription in self:
            if subscription.state in ['trial', 'active']:
                if subscription.requires_approval:
                    if subscription.approval_status != 'approved':
                        raise ValidationError(
                            _("Cannot activate membership '%s'. "
                              "Membership requires approval.") % subscription.plan_id.name
                        )

    @api.constrains('state', 'eligibility_verified', 'requires_verification')
    def _check_eligibility_verification(self):
        """Validate eligibility verification"""
        for subscription in self:
            if subscription.state in ['trial', 'active']:
                if subscription.requires_verification:
                    if not subscription.eligibility_verified:
                        raise ValidationError(
                            _("Cannot activate membership '%s'. "
                              "Eligibility must be verified first.") % subscription.plan_id.name
                        )

    @api.constrains('membership_category_id', 'plan_id')
    def _check_category_allowed(self):
        """Validate category is allowed for product"""
        for subscription in self:
            if subscription.membership_category_id and subscription.plan_id:
                product = subscription.plan_id.product_template_id
                allowed = product.allowed_member_categories
                
                if allowed and subscription.membership_category_id not in allowed:
                    raise ValidationError(
                        _("Member category '%s' is not allowed for product '%s'.") % (
                            subscription.membership_category_id.name,
                            product.name
                        )
                    )