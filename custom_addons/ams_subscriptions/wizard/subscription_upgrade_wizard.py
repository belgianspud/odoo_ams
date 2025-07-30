from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class SubscriptionUpgradeWizard(models.TransientModel):
    _name = 'ams.subscription.upgrade.wizard'
    _description = 'Subscription Upgrade/Downgrade Wizard'

    # Source Subscription
    subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Current Subscription',
        required=True,
        domain=[('state', 'in', ['active', 'pending_renewal'])]
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        related='subscription_id.partner_id',
        readonly=True
    )
    
    current_membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Current Membership Type',
        related='subscription_id.membership_type_id',
        readonly=True
    )
    
    current_chapter_id = fields.Many2one(
        'ams.chapter',
        string='Current Chapter',
        related='subscription_id.chapter_id',
        readonly=True
    )
    
    current_price = fields.Float(
        string='Current Price',
        related='subscription_id.unit_price',
        readonly=True
    )
    
    current_end_date = fields.Date(
        string='Current End Date',
        related='subscription_id.end_date',
        readonly=True
    )

    # Target Information
    target_membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='New Membership Type',
        required=True,
        help="Membership type to upgrade/downgrade to"
    )
    
    target_price = fields.Float(
        string='New Price',
        related='target_membership_type_id.price',
        readonly=True
    )

    # Upgrade/Downgrade Type
    change_type = fields.Selection([
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('lateral', 'Lateral Change')
    ], string='Change Type', compute='_compute_change_type', store=True)

    # Timing Options
    timing_option = fields.Selection([
        ('immediate', 'Immediate'),
        ('next_renewal', 'At Next Renewal'),
        ('custom_date', 'Custom Date')
    ], string='When to Apply', default='immediate', required=True)
    
    effective_date = fields.Date(
        string='Effective Date',
        default=fields.Date.context_today,
        help="Date when the change becomes effective"
    )
    
    extend_subscription = fields.Boolean(
        string='Extend Subscription Period',
        default=False,
        help="Extend subscription period based on new membership type duration"
    )
    
    new_end_date = fields.Date(
        string='New End Date',
        compute='_compute_new_end_date',
        store=True
    )

    # Financial Calculations
    price_difference = fields.Float(
        string='Price Difference',
        compute='_compute_financial_impact',
        store=True,
        help="Difference between current and new price"
    )
    
    prorate_charges = fields.Boolean(
        string='Prorate Charges',
        default=True,
        help="Calculate prorated charges for the change"
    )
    
    remaining_days = fields.Integer(
        string='Remaining Days',
        compute='_compute_financial_impact',
        store=True
    )
    
    prorated_amount = fields.Float(
        string='Prorated Amount',
        compute='_compute_financial_impact',
        store=True,
        help="Prorated amount to charge or refund"
    )
    
    upgrade_fee = fields.Float(
        string='Upgrade/Change Fee',
        digits='Product Price',
        help="Additional administrative fee for the change"
    )
    
    total_adjustment = fields.Float(
        string='Total Amount',
        compute='_compute_financial_impact',
        store=True,
        help="Total amount to charge or credit"
    )

    # Payment Options
    payment_option = fields.Selection([
        ('immediate', 'Charge Immediately'),
        ('next_invoice', 'Add to Next Invoice'),
        ('refund', 'Issue Refund'),
        ('credit', 'Apply as Credit')
    ], string='Payment Option', default='immediate')
    
    payment_method = fields.Selection([
        ('auto', 'Automatic Payment'),
        ('manual', 'Manual Payment'),
        ('invoice', 'Send Invoice')
    ], string='Payment Method', default='auto')

    # Benefits Comparison
    current_benefits = fields.Html(
        string='Current Benefits',
        compute='_compute_benefits_comparison'
    )
    
    new_benefits = fields.Html(
        string='New Benefits',
        compute='_compute_benefits_comparison'
    )
    
    benefits_gained = fields.Html(
        string='Benefits Gained',
        compute='_compute_benefits_comparison'
    )
    
    benefits_lost = fields.Html(
        string='Benefits Lost',
        compute='_compute_benefits_comparison'
    )

    # Approval and Notifications
    requires_approval = fields.Boolean(
        string='Requires Approval',
        compute='_compute_requires_approval'
    )
    
    approval_reason = fields.Text(
        string='Approval Reason',
        help="Reason why approval is required"
    )
    
    send_confirmation = fields.Boolean(
        string='Send Confirmation Email',
        default=True
    )
    
    confirmation_template_id = fields.Many2one(
        'mail.template',
        string='Confirmation Template',
        domain=[('model', '=', 'ams.member.subscription')]
    )

    # Member Communication
    member_message = fields.Html(
        string='Message to Member',
        help="Optional message to include in confirmation"
    )
    
    internal_notes = fields.Html(
        string='Internal Notes',
        help="Internal notes about the change"
    )

    # Change Reason
    change_reason = fields.Selection([
        ('member_request', 'Member Request'),
        ('eligibility_change', 'Eligibility Change'),
        ('promotion', 'Promotional Upgrade'),
        ('correction', 'Administrative Correction'),
        ('policy_change', 'Policy Change'),
        ('other', 'Other')
    ], string='Reason for Change', required=True, default='member_request')
    
    custom_reason = fields.Text(
        string='Custom Reason',
        help="Detailed reason for the change"
    )

    # Processing Options
    create_backup = fields.Boolean(
        string='Create Backup Record',
        default=True,
        help="Keep a record of the original subscription"
    )
    
    auto_confirm_order = fields.Boolean(
        string='Auto-Confirm Order',
        default=True
    )
    
    auto_create_invoice = fields.Boolean(
        string='Auto-Create Invoice',
        default=False
    )

    # Validation and Preview
    validation_messages = fields.Html(
        string='Validation Messages',
        compute='_compute_validation_messages'
    )
    
    change_preview = fields.Html(
        string='Change Preview',
        compute='_compute_change_preview'
    )

    @api.depends('current_price', 'target_price')
    def _compute_change_type(self):
        """Determine if this is an upgrade, downgrade, or lateral change"""
        for wizard in self:
            if wizard.target_price > wizard.current_price: