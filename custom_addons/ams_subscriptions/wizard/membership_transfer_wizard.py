from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class MembershipTransferWizard(models.TransientModel):
    _name = 'ams.membership.transfer.wizard'
    _description = 'Membership Transfer Wizard'

    # Transfer Type
    transfer_type = fields.Selection([
        ('chapter', 'Chapter Transfer'),
        ('membership_type', 'Membership Type Change'),
        ('member', 'Transfer to Different Member'),
        ('merge', 'Merge Memberships')
    ], string='Transfer Type', required=True, default='chapter')

    # Source Information
    source_subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Source Subscription',
        required=True,
        domain=[('state', 'in', ['active', 'pending_renewal'])]
    )
    
    source_partner_id = fields.Many2one(
        'res.partner',
        string='Current Member',
        related='source_subscription_id.partner_id',
        readonly=True
    )
    
    source_membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Current Membership Type',
        related='source_subscription_id.membership_type_id',
        readonly=True
    )
    
    source_chapter_id = fields.Many2one(
        'ams.chapter',
        string='Current Chapter',
        related='source_subscription_id.chapter_id',
        readonly=True
    )
    
    source_end_date = fields.Date(
        string='Current End Date',
        related='source_subscription_id.end_date',
        readonly=True
    )
    
    source_amount_paid = fields.Float(
        string='Amount Paid',
        related='source_subscription_id.total_amount',
        readonly=True
    )

    # Target Information
    target_chapter_id = fields.Many2one(
        'ams.chapter',
        string='Target Chapter',
        help="Chapter to transfer membership to"
    )
    
    target_membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Target Membership Type',
        help="Membership type to change to"
    )
    
    target_partner_id = fields.Many2one(
        'res.partner',
        string='Target Member',
        domain=[('is_company', '=', False)],
        help="Member to transfer subscription to"
    )
    
    merge_subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Subscription to Merge With',
        domain=[('state', 'in', ['active', 'pending_renewal'])],
        help="Existing subscription to merge with"
    )

    # Transfer Options
    effective_date = fields.Date(
        string='Effective Date',
        default=fields.Date.context_today,
        required=True,
        help="Date when the transfer becomes effective"
    )
    
    preserve_end_date = fields.Boolean(
        string='Preserve End Date',
        default=True,
        help="Keep the same expiration date after transfer"
    )
    
    new_end_date = fields.Date(
        string='New End Date',
        help="New expiration date if not preserving original"
    )
    
    prorate_fees = fields.Boolean(
        string='Prorate Fees',
        default=True,
        help="Calculate prorated fees for the transfer"
    )

    # Financial Handling
    fee_handling = fields.Selection([
        ('no_charge', 'No Additional Charge'),
        ('charge_difference', 'Charge Difference'),
        ('refund_difference', 'Refund Difference'),
        ('full_charge', 'Charge Full New Fee')
    ], string='Fee Handling', default='charge_difference', required=True)
    
    transfer_fee = fields.Float(
        string='Transfer Fee',
        digits='Product Price',
        help="Administrative fee for the transfer"
    )
    
    price_difference = fields.Float(
        string='Price Difference',
        digits='Product Price',
        compute='_compute_price_difference',
        help="Price difference between old and new membership"
    )
    
    prorated_amount = fields.Float(
        string='Prorated Amount',
        digits='Product Price',
        compute='_compute_prorated_amount',
        help="Prorated amount based on remaining period"
    )
    
    total_adjustment = fields.Float(
        string='Total Adjustment',
        digits='Product Price',
        compute='_compute_total_adjustment',
        help="Total amount to charge or refund"
    )

    # Approval and Notifications
    requires_approval = fields.Boolean(
        string='Requires Approval',
        compute='_compute_requires_approval',
        help="Transfer requires management approval"
    )
    
    approval_notes = fields.Text(
        string='Approval Notes',
        help="Notes for approval process"
    )
    
    send_notifications = fields.Boolean(
        string='Send Notifications',
        default=True,
        help="Send notification emails to affected parties"
    )
    
    notify_source_member = fields.Boolean(
        string='Notify Original Member',
        default=True
    )
    
    notify_target_member = fields.Boolean(
        string='Notify Target Member',
        default=True
    )
    
    notify_chapters = fields.Boolean(
        string='Notify Chapters',
        default=True,
        help="Notify chapter administrators"
    )

    # Transfer Reason and Notes
    transfer_reason = fields.Selection([
        ('member_request', 'Member Request'),
        ('relocation', 'Member Relocation'),
        ('career_change', 'Career Change'),
        ('administrative', 'Administrative Correction'),
        ('merger', 'Organization Merger'),
        ('other', 'Other')
    ], string='Transfer Reason', required=True, default='member_request')
    
    custom_reason = fields.Text(
        string='Custom Reason',
        help="Detailed reason for transfer"
    )
    
    internal_notes = fields.Html(
        string='Internal Notes',
        help="Internal notes not visible to members"
    )
    
    member_message = fields.Html(
        string='Message to Member',
        help="Message to include in member notification"
    )

    # Processing Options
    create_new_subscription = fields.Boolean(
        string='Create New Subscription',
        default=True,
        help="Create new subscription record (recommended)"
    )
    
    cancel_source_subscription = fields.Boolean(
        string='Cancel Source Subscription',
        default=True,
        help="Cancel the original subscription"
    )
    
    auto_confirm_orders = fields.Boolean(
        string='Auto-Confirm Orders',
        default=True
    )
    
    auto_create_invoices = fields.Boolean(
        string='Auto-Create Invoices',
        default=False
    )

    # Validation and Preview
    validation_errors = fields.Html(
        string='Validation Errors',
        compute='_compute_validation_errors'
    )
    
    transfer_preview = fields.Html(
        string='Transfer Preview',
        compute='_compute_transfer_preview'
    )

    @api.onchange('transfer_type')
    def _onchange_transfer_type(self):
        """Clear fields when transfer type changes"""
        self.target_chapter_id = False
        self.target_membership_type_id = False
        self.target_partner_id = False
        self.merge_subscription_id = False

    @api.onchange('target_membership_type_id', 'source_subscription_id')
    def _onchange_target_membership_type(self):
        """Update price difference when target membership type changes"""
        if self.target_membership_type_id and self.source_subscription_id:
            # Trigger recomputation
            self._compute_price_difference()

    @api.depends('source_subscription_id', 'target_membership_type_id', 'target_chapter_id')
    def _compute_price_difference(self):
        """Compute price difference between source and target"""
        for wizard in self:
            if not wizard.source_subscription_id:
                wizard.price_difference = 0.0
                continue
            
            source_price = wizard.source_subscription_id.unit_price
            target_price = source_price
            
            if wizard.transfer_type == 'membership_type' and wizard.target_membership_type_id:
                target_price = wizard.target_membership_type_id.price
            elif wizard.transfer_type == 'chapter' and wizard.target_chapter_id:
                # Check if target chapter has different pricing
                if wizard.target_chapter_id.membership_fee_override > 0:
                    target_price = wizard.target_chapter_id.membership_fee_override
            
            wizard.price_difference = target_price - source_price

    @api.depends('price_difference', 'source_subscription_id', 'effective_date', 'prorate_fees')
    def _compute_prorated_amount(self):
        """Compute prorated amount based on remaining period"""
        for wizard in self:
            if not wizard.prorate_fees or not wizard.source_subscription_id:
                wizard.prorated_amount = wizard.price_difference
                continue
            
            # Calculate remaining days
            today = fields.Date.today()
            end_date = wizard.source_subscription_id.end_date
            
            if not end_date:
                wizard.prorated_amount = wizard.price_difference
                continue
            
            total_days = (end_date - wizard.source_subscription_id.start_date).days
            remaining_days = (end_date - max(today, wizard.effective_date)).days
            
            if total_days <= 0 or remaining_days <= 0:
                wizard.prorated_amount = 0.0
            else:
                proration_factor = remaining_days / total_days
                wizard.prorated_amount = wizard.price_difference * proration_factor

    @api.depends('prorated_amount', 'transfer_fee', 'fee_handling')
    def _compute_total_adjustment(self):
        """Compute total adjustment amount"""
        for wizard in self:
            if wizard.fee_handling == 'no_charge':
                wizard.total_adjustment = wizard.transfer_fee
            elif wizard.fee_handling == 'charge_difference':
                wizard.total_adjustment = max(0, wizard.prorated_amount) + wizard.transfer_fee
            elif wizard.fee_handling == 'refund_difference':
                wizard.total_adjustment = wizard.prorated_amount + wizard.transfer_fee
            elif wizard.fee_handling == 'full_charge':
                target_price = 0.0
                if wizard.target_membership_type_id:
                    target_price = wizard.target_membership_type_id.price
                wizard.total_adjustment = target_price + wizard.transfer_fee
            else:
                wizard.total_adjustment = wizard.transfer_fee

    @api.depends('transfer_type', 'target_membership_type_id', 'target_chapter_id', 'total_adjustment')
    def _compute_requires_approval(self):
        """Determine if transfer requires approval"""
        for wizard in self:
            requires_approval = False
            
            # Transfers involving membership type changes require approval
            if wizard.transfer_type == 'membership_type':
                requires_approval = True
            
            # Large financial adjustments require approval
            if abs(wizard.total_adjustment) > 100:  # Configurable threshold
                requires_approval = True
            
            # Transfers to different members require approval
            if wizard.transfer_type == 'member':
                requires_approval = True
            
            wizard.requires_approval = requires_approval

    @api.depends('source_subscription_id', 'transfer_type', 'target_chapter_id', 
                 'target_membership_type_id', 'target_partner_id')
    def _compute_validation_errors(self):
        """Compute validation errors"""
        for wizard in self:
            errors = []
            
            if not wizard.source_subscription_id:
                errors.append("Source subscription is required")
                wizard.validation_errors = '<br/>'.join(errors)
                continue
            
            if wizard.transfer_type == 'chapter':
                if not wizard.target_chapter_id:
                    errors.append("Target chapter is required for chapter transfer")
                elif wizard.target_chapter_id == wizard.source_chapter_id:
                    errors.append("Target chapter must be different from current chapter")
                
                # Check if membership type is available in target chapter
                if (wizard.target_chapter_id and wizard.source_membership_type_id and
                    not wizard.source_membership_type_id.is_available_for_chapter(wizard.target_chapter_id.id)):
                    errors.append("Current membership type is not available in target chapter")
            
            elif wizard.transfer_type == 'membership_type':
                if not wizard.target_membership_type_id:
                    errors.append("Target membership type is required")
                elif wizard.target_membership_type_id == wizard.source_membership_type_id:
                    errors.append("Target membership type must be different from current type")
            
            elif wizard.transfer_type == 'member':
                if not wizard.target_partner_id:
                    errors.append("Target member is required for member transfer")
                elif wizard.target_partner_id == wizard.source_partner_id:
                    errors.append("Target member must be different from current member")
                
                # Check if target member already has active subscription
                existing_subscription = wizard.env['ams.member.subscription'].search([
                    ('partner_id', '=', wizard.target_partner_id.id),
                    ('state', 'in', ['active', 'pending_renewal']),
                    ('id', '!=', wizard.source_subscription_id.id)
                ])
                if existing_subscription:
                    errors.append("Target member already has an active subscription")
            
            elif wizard.transfer_type == 'merge':
                if not wizard.merge_subscription_id:
                    errors.append("Subscription to merge with is required")
                elif wizard.merge_subscription_id == wizard.source_subscription_id:
                    errors.append("Cannot merge subscription with itself")
            
            # Check effective date
            if wizard.effective_date < fields.Date.today():
                errors.append("Effective date cannot be in the past")
            
            if wizard.validation_errors:
                wizard.validation_errors = '<ul><li>' + '</li><li>'.join(errors) + '</li></ul>'
            else:
                wizard.validation_errors = ''

    @api.depends('source_subscription_id', 'transfer_type', 'target_chapter_id',
                 'target_membership_type_id', 'target_partner_id', 'total_adjustment')
    def _compute_transfer_preview(self):
        """Compute transfer preview"""
        for wizard in self:
            if not wizard.source_subscription_id:
                wizard.transfer_preview = "<p>Please select a source subscription first.</p>"
                continue
            
            preview_html = "<table class='table table-sm'>"
            preview_html += "<tr><th>Item</th><th>From</th><th>To</th></tr>"
            
            if wizard.transfer_type == 'chapter':
                current_chapter = wizard.source_chapter_id.name if wizard.source_chapter_id else 'None'
                target_chapter = wizard.target_chapter_id.name if wizard.target_chapter_id else 'Not Set'
                preview_html += f"<tr><td>Chapter</td><td>{current_chapter}</td><td>{target_chapter}</td></tr>"
            
            elif wizard.transfer_type == 'membership_type':
                current_type = wizard.source_membership_type_id.name
                target_type = wizard.target_membership_type_id.name if wizard.target_membership_type_id else 'Not Set'
                preview_html += f"<tr><td>Membership Type</td><td>{current_type}</td><td>{target_type}</td></tr>"
            
            elif wizard.transfer_type == 'member':
                current_member = wizard.source_partner_id.name
                target_member = wizard.target_partner_id.name if wizard.target_partner_id else 'Not Set'
                preview_html += f"<tr><td>Member</td><td>{current_member}</td><td>{target_member}</td></tr>"
            
            # Financial impact
            if wizard.total_adjustment != 0:
                adjustment_type = "Charge" if wizard.total_adjustment > 0 else "Refund"
                preview_html += f"<tr><td>Financial Impact</td><td>-</td><td>{adjustment_type}: ${abs(wizard.total_adjustment):.2f}</td></tr>"
            
            preview_html += "</table>"
            
            if wizard.requires_approval:
                preview_html += "<div class='alert alert-warning'>⚠️ This transfer requires management approval.</div>"
            
            wizard.transfer_preview = preview_html

    def action_preview_transfer(self):
        """Preview the transfer"""
        self.ensure_one()
        
        # Force recompute validations and preview
        self._compute_validation_errors()
        self._compute_transfer_preview()
        
        if self.validation_errors:
            raise UserError(_("Please fix validation errors before proceeding."))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership.transfer.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_preview': True}
        }

    def action_process_transfer(self):
        """Process the membership transfer"""
        self.ensure_one()
        
        # Validate transfer
        self._compute_validation_errors()
        if self.validation_errors:
            raise UserError(_("Cannot process transfer due to validation errors."))
        
        # Check approval requirements
        if self.requires_approval and not self.env.user.has_group('ams_subscriptions.group_ams_manager'):
            raise UserError(_("This transfer requires management approval."))
        
        try:
            # Process the transfer based on type
            if self.transfer_type == 'chapter':
                result = self._process_chapter_transfer()
            elif self.transfer_type == 'membership_type':
                result = self._process_membership_type_transfer()
            elif self.transfer_type == 'member':
                result = self._process_member_transfer()
            elif self.transfer_type == 'merge':
                result = self._process_merge_transfer()
            
            # Send notifications if requested
            if self.send_notifications:
                self._send_transfer_notifications()
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'ams.membership.transfer.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'show_results': True,
                    'result_message': _("Transfer processed successfully.")
                }
            }
            
        except Exception as e:
            _logger.error(f"Transfer processing failed: {e}")
            raise UserError(_("Transfer failed: %s") % str(e))

    def _process_chapter_transfer(self):
        """Process chapter transfer"""
        self.ensure_one()
        
        # Update subscription
        self.source_subscription_id.write({
            'chapter_id': self.target_chapter_id.id,
            'notes': self._build_transfer_notes()
        })
        
        # Handle financial adjustment
        if self.total_adjustment != 0:
            self._create_financial_adjustment()
        
        # Log transfer
        self.source_subscription_id.message_post(
            body=_("Chapter transferred from %s to %s") % (
                self.source_chapter_id.name if self.source_chapter_id else 'None',
                self.target_chapter_id.name
            )
        )
        
        return True

    def _process_membership_type_transfer(self):
        """Process membership type change"""
        self.ensure_one()
        
        # Update subscription
        update_vals = {
            'membership_type_id': self.target_membership_type_id.id,
            'unit_price': self.target_membership_type_id.price,
            'notes': self._build_transfer_notes()
        }
        
        if not self.preserve_end_date:
            update_vals['end_date'] = self.new_end_date
        
        self.source_subscription_id.write(update_vals)
        
        # Handle financial adjustment
        if self.total_adjustment != 0:
            self._create_financial_adjustment()
        
        # Log transfer
        self.source_subscription_id.message_post(
            body=_("Membership type changed from %s to %s") % (
                self.source_membership_type_id.name,
                self.target_membership_type_id.name
            )
        )
        
        return True

    def _process_member_transfer(self):
        """Process member transfer"""
        self.ensure_one()
        
        if self.create_new_subscription:
            # Create new subscription for target member
            new_subscription_vals = {
                'partner_id': self.target_partner_id.id,
                'membership_type_id': self.source_subscription_id.membership_type_id.id,
                'chapter_id': self.source_subscription_id.chapter_id.id if self.source_subscription_id.chapter_id else False,
                'start_date': self.effective_date,
                'end_date': self.source_subscription_id.end_date if self.preserve_end_date else self.new_end_date,
                'unit_price': self.source_subscription_id.unit_price,
                'parent_subscription_id': self.source_subscription_id.id,
                'notes': self._build_transfer_notes(),
                'state': 'active'
            }
            
            new_subscription = self.env['ams.member.subscription'].create(new_subscription_vals)
            
            # Cancel source subscription if requested
            if self.cancel_source_subscription:
                self.source_subscription_id.write({
                    'state': 'cancelled',
                    'notes': self._build_transfer_notes()
                })
        else:
            # Direct transfer
            self.source_subscription_id.write({
                'partner_id': self.target_partner_id.id,
                'notes': self._build_transfer_notes()
            })
        
        return True

    def _process_merge_transfer(self):
        """Process subscription merge"""
        self.ensure_one()
        
        # Extend the end date of target subscription
        target_subscription = self.merge_subscription_id
        source_end_date = self.source_subscription_id.end_date
        target_end_date = target_subscription.end_date
        
        if source_end_date and target_end_date:
            new_end_date = max(source_end_date, target_end_date)
        else:
            new_end_date = source_end_date or target_end_date
        
        target_subscription.write({
            'end_date': new_end_date,
            'notes': self._build_transfer_notes()
        })
        
        # Cancel source subscription
        self.source_subscription_id.write({
            'state': 'cancelled',
            'notes': self._build_transfer_notes()
        })
        
        return True

    def _create_financial_adjustment(self):
        """Create financial adjustment for transfer"""
        self.ensure_one()
        
        if self.total_adjustment == 0:
            return
        
        # This would create appropriate invoices or credit notes
        # Implementation depends on specific financial handling requirements
        pass

    def _build_transfer_notes(self):
        """Build comprehensive transfer notes"""
        self.ensure_one()
        
        notes = []
        notes.append(f"<h4>Membership Transfer</h4>")
        notes.append(f"<p>Transfer Type: {dict(self._fields['transfer_type'].selection)[self.transfer_type]}</p>")
        notes.append(f"<p>Effective Date: {self.effective_date}</p>")
        notes.append(f"<p>Reason: {dict(self._fields['transfer_reason'].selection)[self.transfer_reason]}</p>")
        
        if self.custom_reason:
            notes.append(f"<p>Details: {self.custom_reason}</p>")
        
        if self.total_adjustment != 0:
            adjustment_type = "Charge" if self.total_adjustment > 0 else "Refund"
            notes.append(f"<p>Financial Impact: {adjustment_type} ${abs(self.total_adjustment):.2f}</p>")
        
        notes.append(f"<p>Processed by: {self.env.user.name} on {fields.Date.today()}</p>")
        
        if self.internal_notes:
            notes.append(f"<h4>Internal Notes:</h4>")
            notes.append(self.internal_notes)
        
        return ''.join(notes)

    def _send_transfer_notifications(self):
        """Send transfer notifications"""
        self.ensure_one()
        
        # Implementation would send appropriate emails to affected parties
        pass

    def action_cancel(self):
        """Cancel the transfer"""
        return {'type': 'ir.actions.act_window_close'}