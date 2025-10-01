# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class CategoryChangeWizard(models.TransientModel):
    _name = 'category.change.wizard'
    _description = 'Member Category Change Wizard'

    # ==========================================
    # BASIC INFORMATION
    # ==========================================
    
    subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Membership',
        required=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        related='subscription_id.partner_id',
        readonly=True
    )
    
    current_category_id = fields.Many2one(
        'membership.category',
        string='Current Category',
        related='subscription_id.membership_category_id',
        readonly=True
    )
    
    current_product_id = fields.Many2one(
        'product.template',
        string='Current Product',
        related='subscription_id.product_id.product_tmpl_id',
        readonly=True
    )

    # ==========================================
    # NEW CATEGORY SELECTION
    # ==========================================
    
    change_type = fields.Selection([
        ('upgrade', 'Upgrade Category'),
        ('downgrade', 'Downgrade Category'),
        ('transition', 'Category Transition'),
    ], string='Change Type', required=True, default='transition')
    
    new_category_id = fields.Many2one(
        'membership.category',
        string='New Category',
        required=True,
        help='Category to change to'
    )
    
    available_categories = fields.Many2many(
        'membership.category',
        compute='_compute_available_categories',
        string='Available Categories'
    )
    
    is_allowed_transition = fields.Boolean(
        string='Allowed Transition',
        compute='_compute_transition_validation',
        store=True
    )
    
    transition_warnings = fields.Text(
        string='Warnings',
        compute='_compute_transition_validation',
        store=True
    )

    # ==========================================
    # NEW PRODUCT SELECTION
    # ==========================================
    
    change_product = fields.Boolean(
        string='Change Product',
        default=True,
        help='Also change to a different product for the new category'
    )
    
    new_product_id = fields.Many2one(
        'product.template',
        string='New Product',
        domain=[('is_membership_product', '=', True)],
        help='Membership product for the new category'
    )
    
    available_products = fields.Many2many(
        'product.template',
        compute='_compute_available_products',
        string='Available Products'
    )

    # ==========================================
    # PRICING & BILLING
    # ==========================================
    
    current_price = fields.Float(
        string='Current Price',
        related='subscription_id.price',
        readonly=True
    )
    
    new_price = fields.Float(
        string='New Price',
        compute='_compute_new_price',
        store=True
    )
    
    price_difference = fields.Float(
        string='Price Difference',
        compute='_compute_price_difference',
        store=True
    )
    
    discount_percent = fields.Float(
        string='Category Discount %',
        compute='_compute_discount',
        store=True
    )
    
    prorate_billing = fields.Boolean(
        string='Prorate Billing',
        default=True,
        help='Create prorated invoice/credit for price difference'
    )
    
    prorated_amount = fields.Float(
        string='Prorated Amount',
        compute='_compute_prorated_amount',
        store=True
    )

    # ==========================================
    # TIMING
    # ==========================================
    
    effective_date = fields.Date(
        string='Effective Date',
        default=fields.Date.today,
        required=True,
        help='Date when the category change takes effect'
    )
    
    apply_immediately = fields.Boolean(
        string='Apply Immediately',
        default=True,
        help='Apply change now or at next renewal'
    )

    # ==========================================
    # ELIGIBILITY
    # ==========================================
    
    requires_verification = fields.Boolean(
        string='Requires Verification',
        compute='_compute_eligibility_requirements',
        store=True
    )
    
    eligibility_verified = fields.Boolean(
        string='Eligibility Verified',
        default=False
    )
    
    verification_notes = fields.Text(
        string='Verification Notes'
    )
    
    eligibility_requirements = fields.Html(
        string='Requirements',
        related='new_category_id.eligibility_requirements',
        readonly=True
    )

    # ==========================================
    # DOCUMENTATION
    # ==========================================
    
    reason = fields.Text(
        string='Reason for Change',
        required=True,
        help='Explain why the category is being changed'
    )
    
    internal_notes = fields.Text(
        string='Internal Notes',
        help='Additional notes for internal use'
    )

    # ==========================================
    # OPTIONS
    # ==========================================
    
    send_notification = fields.Boolean(
        string='Send Notification Email',
        default=True
    )
    
    create_invoice = fields.Boolean(
        string='Create Invoice/Credit Note',
        default=True,
        help='Create invoice or credit note for price difference'
    )

    # ==========================================
    # COMPUTE METHODS
    # ==========================================

    @api.depends('current_category_id', 'change_type')
    def _compute_available_categories(self):
        """Get categories that can be transitioned to"""
        for wizard in self:
            if not wizard.current_category_id:
                wizard.available_categories = False
                continue
            
            available = self.env['membership.category']
            
            if wizard.change_type == 'upgrade':
                # Get upgrade paths
                available = wizard.current_category_id.allows_upgrade_to
            elif wizard.change_type == 'downgrade':
                # Get downgrade paths
                available = wizard.current_category_id.allows_downgrade_to
            else:
                # All active categories for general transition
                available = self.env['membership.category'].search([
                    ('active', '=', True),
                    ('id', '!=', wizard.current_category_id.id)
                ])
            
            wizard.available_categories = available

    @api.depends('new_category_id', 'partner_id')
    def _compute_transition_validation(self):
        """Validate if transition is allowed"""
        for wizard in self:
            if not wizard.new_category_id or not wizard.partner_id:
                wizard.is_allowed_transition = False
                wizard.transition_warnings = False
                continue
            
            warnings = []
            
            # Check if transition path exists
            if wizard.change_type == 'upgrade':
                if wizard.new_category_id not in wizard.current_category_id.allows_upgrade_to:
                    warnings.append(
                        f"⚠️ Upgrade path from '{wizard.current_category_id.name}' to "
                        f"'{wizard.new_category_id.name}' is not configured."
                    )
            elif wizard.change_type == 'downgrade':
                if wizard.new_category_id not in wizard.current_category_id.allows_downgrade_to:
                    warnings.append(
                        f"⚠️ Downgrade path from '{wizard.current_category_id.name}' to "
                        f"'{wizard.new_category_id.name}' is not configured."
                    )
            
            # Check eligibility
            is_eligible, reasons = wizard.new_category_id.check_eligibility(wizard.partner_id)
            
            if not is_eligible:
                for reason in reasons:
                    warnings.append(f"❌ {reason}")
            
            # Check age restrictions
            if wizard.new_category_id.min_age > 0 or wizard.new_category_id.max_age > 0:
                if hasattr(wizard.partner_id, 'birthdate') and wizard.partner_id.birthdate:
                    age = (fields.Date.today() - wizard.partner_id.birthdate).days // 365
                    
                    if wizard.new_category_id.min_age > 0 and age < wizard.new_category_id.min_age:
                        warnings.append(
                            f"❌ Member age ({age}) below minimum required age "
                            f"({wizard.new_category_id.min_age})"
                        )
                    
                    if wizard.new_category_id.max_age > 0 and age > wizard.new_category_id.max_age:
                        warnings.append(
                            f"❌ Member age ({age}) exceeds maximum allowed age "
                            f"({wizard.new_category_id.max_age})"
                        )
            
            # Check organizational requirements
            if wizard.new_category_id.is_organizational and not wizard.partner_id.is_company:
                warnings.append("❌ New category is for organizations only")
            
            if not wizard.new_category_id.is_organizational and wizard.partner_id.is_company:
                warnings.append("❌ New category is for individuals only")
            
            wizard.is_allowed_transition = len(warnings) == 0 or wizard.eligibility_verified
            wizard.transition_warnings = '\n'.join(warnings) if warnings else False

    @api.depends('new_category_id')
    def _compute_available_products(self):
        """Get products available for new category"""
        for wizard in self:
            if wizard.new_category_id:
                wizard.available_products = wizard.new_category_id.get_available_products()
            else:
                wizard.available_products = False

    @api.depends('new_category_id')
    def _compute_eligibility_requirements(self):
        """Check if new category requires verification"""
        for wizard in self:
            wizard.requires_verification = wizard.new_category_id.requires_verification

    @api.depends('new_category_id')
    def _compute_discount(self):
        """Get discount for new category"""
        for wizard in self:
            if wizard.new_category_id:
                wizard.discount_percent = wizard.new_category_id.typical_discount_percent
            else:
                wizard.discount_percent = 0.0

    @api.depends('new_product_id', 'discount_percent')
    def _compute_new_price(self):
        """Calculate new price with category discount"""
        for wizard in self:
            if wizard.new_product_id:
                base_price = wizard.new_product_id.list_price
                
                if wizard.discount_percent > 0:
                    discount_amount = base_price * (wizard.discount_percent / 100)
                    wizard.new_price = base_price - discount_amount
                else:
                    wizard.new_price = base_price
            else:
                wizard.new_price = 0.0

    @api.depends('current_price', 'new_price')
    def _compute_price_difference(self):
        """Calculate price difference"""
        for wizard in self:
            wizard.price_difference = wizard.new_price - wizard.current_price

    @api.depends('price_difference', 'prorate_billing', 'subscription_id', 'effective_date')
    def _compute_prorated_amount(self):
        """Calculate prorated amount for billing"""
        for wizard in self:
            if not wizard.prorate_billing or wizard.price_difference == 0:
                wizard.prorated_amount = 0.0
                continue
            
            if not wizard.subscription_id or not wizard.subscription_id.date_end:
                wizard.prorated_amount = wizard.price_difference
                continue
            
            # Calculate remaining days in period
            today = wizard.effective_date or fields.Date.today()
            end_date = wizard.subscription_id.date_end
            
            if end_date <= today:
                wizard.prorated_amount = 0.0
                continue
            
            remaining_days = (end_date - today).days
            
            # Calculate total days in period based on billing period
            billing_period = wizard.subscription_id.plan_id.billing_period
            
            if billing_period == 'monthly':
                total_days = 30
            elif billing_period == 'quarterly':
                total_days = 90
            elif billing_period == 'yearly':
                total_days = 365
            else:
                total_days = 30  # Default
            
            # Prorate
            proration_factor = remaining_days / total_days
            wizard.prorated_amount = wizard.price_difference * proration_factor

    # ==========================================
    # ONCHANGE METHODS
    # ==========================================

    @api.onchange('new_category_id')
    def _onchange_new_category_id(self):
        """Update product selection when category changes"""
        if self.new_category_id:
            # Suggest default product for new category
            if self.new_category_id.default_product_id:
                self.new_product_id = self.new_category_id.default_product_id
            else:
                # Clear product selection
                self.new_product_id = False

    @api.onchange('change_product')
    def _onchange_change_product(self):
        """Clear product when change_product is unchecked"""
        if not self.change_product:
            self.new_product_id = False

    @api.onchange('apply_immediately')
    def _onchange_apply_immediately(self):
        """Update effective date"""
        if self.apply_immediately:
            self.effective_date = fields.Date.today()
        else:
            # Set to next renewal date
            if self.subscription_id and self.subscription_id.date_end:
                self.effective_date = self.subscription_id.date_end

    # ==========================================
    # CONSTRAINT METHODS
    # ==========================================

    @api.constrains('new_category_id', 'current_category_id')
    def _check_category_change(self):
        """Validate category change"""
        for wizard in self:
            if wizard.new_category_id == wizard.current_category_id:
                raise ValidationError(_('New category must be different from current category.'))

    @api.constrains('effective_date', 'subscription_id')
    def _check_effective_date(self):
        """Validate effective date"""
        for wizard in self:
            if wizard.effective_date < wizard.subscription_id.date_start:
                raise ValidationError(_(
                    'Effective date cannot be before subscription start date.'
                ))

    @api.constrains('eligibility_verified', 'requires_verification')
    def _check_verification(self):
        """Validate verification requirement"""
        for wizard in self:
            if wizard.requires_verification and not wizard.eligibility_verified:
                if not wizard.is_allowed_transition:
                    raise ValidationError(_(
                        'This category requires eligibility verification. '
                        'Please verify eligibility before proceeding.'
                    ))

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_change_category(self):
        """Execute category change"""
        self.ensure_one()
        
        # Validate
        if not self.is_allowed_transition and not self.eligibility_verified:
            raise UserError(_(
                'Category change cannot be completed:\n\n%s\n\n'
                'Please verify eligibility or choose a different category.'
            ) % self.transition_warnings)
        
        if not self.reason:
            raise UserError(_('Please provide a reason for the category change.'))
        
        # Update subscription
        self._update_subscription()
        
        # Create prorated invoice if needed
        if self.create_invoice and self.prorated_amount != 0:
            self._create_proration_invoice()
        
        # Log change in chatter
        self._log_category_change()
        
        # Send notification
        if self.send_notification:
            self._send_notification_email()
        
        return self._return_success_action()

    def _update_subscription(self):
        """Update subscription with new category and product"""
        self.ensure_one()
        
        vals = {
            'membership_category_id': self.new_category_id.id,
        }
        
        # Update product if requested
        if self.change_product and self.new_product_id:
            # Get new plan
            new_plan = self.new_product_id.subscription_plan_ids[:1]
            if new_plan:
                vals['plan_id'] = new_plan.id
                vals['price'] = self.new_price
        else:
            # Just update price with discount
            vals['price'] = self.new_price
        
        # Update verification fields
        if self.eligibility_verified:
            vals.update({
                'eligibility_verified': True,
                'eligibility_verified_by': self.env.user.id,
                'eligibility_verified_date': fields.Date.today(),
            })
        
        self.subscription_id.write(vals)

    def _create_proration_invoice(self):
        """Create prorated invoice or credit note"""
        self.ensure_one()
        
        # Determine if invoice or credit note
        move_type = 'out_invoice' if self.prorated_amount > 0 else 'out_refund'
        
        invoice_vals = {
            'move_type': move_type,
            'partner_id': self.partner_id.id,
            'subscription_id': self.subscription_id.id,
            'invoice_origin': f"Category change - {self.subscription_id.name}",
            'invoice_date': self.effective_date,
            'invoice_line_ids': [(0, 0, {
                'name': (
                    f"Category change proration\n"
                    f"From: {self.current_category_id.name}\n"
                    f"To: {self.new_category_id.name}\n"
                    f"Effective: {self.effective_date}"
                ),
                'quantity': 1,
                'price_unit': abs(self.prorated_amount),
            })],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Post invoice if positive amount
        if self.prorated_amount > 0:
            try:
                invoice.action_post()
            except Exception as e:
                _logger.warning(f"Could not auto-post proration invoice: {e}")
        
        return invoice

    def _log_category_change(self):
        """Log category change in subscription chatter"""
        self.ensure_one()
        
        message_body = f"""
        <p><strong>Category Changed</strong></p>
        <ul>
            <li><strong>From:</strong> {self.current_category_id.name}</li>
            <li><strong>To:</strong> {self.new_category_id.name}</li>
            <li><strong>Effective Date:</strong> {self.effective_date}</li>
            <li><strong>Change Type:</strong> {dict(self._fields['change_type'].selection).get(self.change_type)}</li>
            <li><strong>Price Change:</strong> {self.current_price} → {self.new_price} 
                ({'+' if self.price_difference > 0 else ''}{self.price_difference})</li>
        </ul>
        <p><strong>Reason:</strong> {self.reason}</p>
        """
        
        if self.internal_notes:
            message_body += f"<p><strong>Internal Notes:</strong> {self.internal_notes}</p>"
        
        self.subscription_id.message_post(
            body=message_body,
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )

    def _send_notification_email(self):
        """Send notification email to member"""
        self.ensure_one()
        
        # You would create a custom email template for category changes
        # For now, just log
        _logger.info(
            f"Category change notification for {self.partner_id.name}: "
            f"{self.current_category_id.name} → {self.new_category_id.name}"
        )
        
        # Create activity for staff follow-up if verification was required
        if self.requires_verification:
            self.subscription_id.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Follow up on category change for {self.partner_id.name}',
                note=f'Category changed to {self.new_category_id.name}. Verify all requirements are met.',
                user_id=self.env.user.id
            )

    def _return_success_action(self):
        """Return action to view updated subscription"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(
                    'Category changed from %s to %s successfully.'
                ) % (self.current_category_id.name, self.new_category_id.name),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'subscription.subscription',
                    'res_id': self.subscription_id.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            }
        }

    # ==========================================
    # DEFAULT GET
    # ==========================================

    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super(CategoryChangeWizard, self).default_get(fields_list)
        
        subscription_id = self.env.context.get('active_id')
        if subscription_id:
            subscription = self.env['subscription.subscription'].browse(subscription_id)
            res['subscription_id'] = subscription_id
            
            # Set effective date to next renewal if not applying immediately
            if not res.get('apply_immediately', True):
                if subscription.date_end:
                    res['effective_date'] = subscription.date_end
        
        return res