from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class SubscriptionRejectionWizard(models.TransientModel):
    _name = 'ams.subscription.rejection.wizard'
    _description = 'Subscription Rejection Wizard'

    # Subscription to reject
    subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Subscription',
        required=True,
        readonly=True
    )
    
    # Rejection Details
    rejection_reason = fields.Selection([
        ('incomplete_application', 'Incomplete Application'),
        ('eligibility_requirements', 'Does Not Meet Eligibility Requirements'),
        ('documentation_missing', 'Missing Required Documentation'),
        ('payment_issues', 'Payment Issues'),
        ('duplicate_application', 'Duplicate Application'),
        ('chapter_capacity', 'Chapter at Full Capacity'),
        ('disciplinary_action', 'Previous Disciplinary Action'),
        ('background_check', 'Background Check Issues'),
        ('other', 'Other Reason')
    ], string='Rejection Reason', required=True, default='incomplete_application')
    
    custom_reason = fields.Text(
        string='Custom Reason',
        help="Provide detailed reason for rejection"
    )
    
    # Communication Options
    notify_applicant = fields.Boolean(
        string='Notify Applicant',
        default=True,
        help="Send rejection notification to the applicant"
    )
    
    email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'ams.member.subscription')],
        help="Template to use for rejection notification"
    )
    
    custom_message = fields.Html(
        string='Custom Message',
        help="Additional message to include in the notification"
    )
    
    # Internal Notes
    internal_notes = fields.Html(
        string='Internal Notes',
        help="Internal notes about the rejection (not visible to applicant)"
    )
    
    # Actions
    refund_payment = fields.Boolean(
        string='Refund Payment',
        default=False,
        help="Create refund for any payments made"
    )
    
    blacklist_applicant = fields.Boolean(
        string='Add to Blacklist',
        default=False,
        help="Add applicant to blacklist (prevents future applications)"
    )
    
    blacklist_reason = fields.Text(
        string='Blacklist Reason',
        help="Reason for adding to blacklist"
    )
    
    blacklist_duration = fields.Selection([
        ('permanent', 'Permanent'),
        ('1year', '1 Year'),
        ('2years', '2 Years'),
        ('5years', '5 Years')
    ], string='Blacklist Duration', default='1year')
    
    # Related Information (Read-only for context)
    partner_id = fields.Many2one(
        'res.partner',
        string='Applicant',
        related='subscription_id.partner_id',
        readonly=True
    )
    
    membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Membership Type',
        related='subscription_id.membership_type_id',
        readonly=True
    )
    
    chapter_id = fields.Many2one(
        'ams.chapter',
        string='Chapter',
        related='subscription_id.chapter_id',
        readonly=True
    )
    
    application_date = fields.Date(
        string='Application Date',
        related='subscription_id.application_date',
        readonly=True
    )
    
    total_amount = fields.Float(
        string='Application Amount',
        related='subscription_id.total_amount',
        readonly=True
    )
    
    payment_status = fields.Selection(
        string='Payment Status',
        related='subscription_id.payment_status',
        readonly=True
    )
    
    # Processing Results
    rejection_processed = fields.Boolean(
        string='Rejection Processed',
        default=False,
        readonly=True
    )
    
    processing_log = fields.Html(
        string='Processing Log',
        readonly=True
    )

    @api.model
    def default_get(self, fields_list):
        """Set default values based on context"""
        res = super().default_get(fields_list)
        
        # Get subscription from context
        subscription_id = self.env.context.get('default_subscription_id')
        if subscription_id:
            subscription = self.env['ams.member.subscription'].browse(subscription_id)
            if subscription.exists():
                res['subscription_id'] = subscription_id
                
                # Set default email template
                template = self.env.ref(
                    'ams_subscriptions.email_template_membership_rejected',
                    raise_if_not_found=False
                )
                if template:
                    res['email_template_id'] = template.id
        
        return res

    @api.onchange('rejection_reason')
    def _onchange_rejection_reason(self):
        """Update fields based on rejection reason"""
        if self.rejection_reason == 'payment_issues':
            self.refund_payment = True
        elif self.rejection_reason == 'disciplinary_action':
            self.blacklist_applicant = True
            self.blacklist_duration = 'permanent'
        elif self.rejection_reason == 'background_check':
            self.blacklist_applicant = True
            self.blacklist_duration = '5years'

    @api.onchange('blacklist_applicant')
    def _onchange_blacklist_applicant(self):
        """Clear blacklist fields if not blacklisting"""
        if not self.blacklist_applicant:
            self.blacklist_reason = False
            self.blacklist_duration = '1year'

    @api.constrains('custom_reason')
    def _check_custom_reason(self):
        """Validate custom reason is provided when needed"""
        for wizard in self:
            if wizard.rejection_reason == 'other' and not wizard.custom_reason:
                raise ValidationError(_("Custom reason is required when 'Other Reason' is selected."))

    @api.constrains('blacklist_reason')
    def _check_blacklist_reason(self):
        """Validate blacklist reason is provided when blacklisting"""
        for wizard in self:
            if wizard.blacklist_applicant and not wizard.blacklist_reason:
                raise ValidationError(_("Blacklist reason is required when adding to blacklist."))

    def action_reject_subscription(self):
        """Process the subscription rejection"""
        self.ensure_one()
        
        if not self.subscription_id:
            raise UserError(_("No subscription selected for rejection."))
        
        if self.subscription_id.state not in ['draft', 'pending_approval']:
            raise UserError(_("Only draft or pending approval subscriptions can be rejected."))
        
        processing_log = []
        
        try:
            # Update subscription with rejection information
            rejection_vals = {
                'state': 'cancelled',
                'rejection_reason': self._get_rejection_reason_text(),
                'notes': self._build_rejection_notes(),
            }
            
            self.subscription_id.write(rejection_vals)
            processing_log.append("✓ Subscription marked as rejected")
            
            # Cancel related sale order if exists
            if self.subscription_id.sale_order_id:
                if self.subscription_id.sale_order_id.state in ['draft', 'sent']:
                    self.subscription_id.sale_order_id.action_cancel()
                    processing_log.append("✓ Related sale order cancelled")
            
            # Process refund if requested
            if self.refund_payment:
                refund_result = self._process_refund()
                processing_log.append(refund_result)
            
            # Add to blacklist if requested
            if self.blacklist_applicant:
                blacklist_result = self._add_to_blacklist()
                processing_log.append(blacklist_result)
            
            # Send notification if requested
            if self.notify_applicant:
                notification_result = self._send_rejection_notification()
                processing_log.append(notification_result)
            
            # Log rejection activity
            self.subscription_id.message_post(
                body=_("Subscription rejected: %s") % self._get_rejection_reason_text(),
                message_type='notification'
            )
            processing_log.append("✓ Rejection logged in subscription")
            
            # Update wizard status
            self.rejection_processed = True
            self.processing_log = '<br/>'.join(processing_log)
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'ams.subscription.rejection.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'show_results': True,
                    'result_message': _("Subscription rejection processed successfully.")
                }
            }
            
        except Exception as e:
            error_msg = f"✗ Error processing rejection: {str(e)}"
            processing_log.append(error_msg)
            self.processing_log = '<br/>'.join(processing_log)
            _logger.error(f"Subscription rejection failed for {self.subscription_id.id}: {e}")
            raise UserError(_("Failed to process rejection: %s") % str(e))

    def _get_rejection_reason_text(self):
        """Get human-readable rejection reason"""
        self.ensure_one()
        
        reason_map = {
            'incomplete_application': _('Incomplete Application'),
            'eligibility_requirements': _('Does Not Meet Eligibility Requirements'),
            'documentation_missing': _('Missing Required Documentation'),
            'payment_issues': _('Payment Issues'),
            'duplicate_application': _('Duplicate Application'),
            'chapter_capacity': _('Chapter at Full Capacity'),
            'disciplinary_action': _('Previous Disciplinary Action'),
            'background_check': _('Background Check Issues'),
            'other': _('Other Reason'),
        }
        
        base_reason = reason_map.get(self.rejection_reason, self.rejection_reason)
        
        if self.rejection_reason == 'other' and self.custom_reason:
            return f"{base_reason}: {self.custom_reason}"
        
        return base_reason

    def _build_rejection_notes(self):
        """Build comprehensive rejection notes"""
        self.ensure_one()
        
        notes = []
        
        # Add rejection reason
        notes.append(f"<h4>Rejection Reason:</h4>")
        notes.append(f"<p>{self._get_rejection_reason_text()}</p>")
        
        # Add custom reason if provided
        if self.custom_reason:
            notes.append(f"<h4>Details:</h4>")
            notes.append(f"<p>{self.custom_reason}</p>")
        
        # Add internal notes if provided
        if self.internal_notes:
            notes.append(f"<h4>Internal Notes:</h4>")
            notes.append(self.internal_notes)
        
        # Add processing information
        notes.append(f"<h4>Processing Information:</h4>")
        notes.append(f"<p>Rejected by: {self.env.user.name}</p>")
        notes.append(f"<p>Rejection Date: {fields.Date.today()}</p>")
        
        if self.refund_payment:
            notes.append(f"<p>Refund Requested: Yes</p>")
        
        if self.blacklist_applicant:
            notes.append(f"<p>Added to Blacklist: Yes ({self.blacklist_duration})</p>")
        
        return ''.join(notes)

    def _process_refund(self):
        """Process refund for the subscription"""
        self.ensure_one()
        
        try:
            # Check if there are any invoices to refund
            invoices = self.subscription_id.invoice_ids.filtered(
                lambda inv: inv.state == 'posted' and inv.move_type == 'out_invoice'
            )
            
            if not invoices:
                return "ℹ No invoices found to refund"
            
            refunds_created = 0
            for invoice in invoices:
                # Create credit note
                refund_wizard = self.env['account.move.reversal'].with_context(
                    active_model='account.move',
                    active_ids=[invoice.id]
                ).create({
                    'reason': f"Membership rejection refund - {self._get_rejection_reason_text()}",
                    'refund_method': 'refund',
                })
                
                refund_action = refund_wizard.reverse_moves()
                refunds_created += 1
            
            return f"✓ Created {refunds_created} credit note(s) for refund"
            
        except Exception as e:
            _logger.error(f"Refund processing failed: {e}")
            return f"✗ Refund processing failed: {str(e)}"

    def _add_to_blacklist(self):
        """Add applicant to blacklist"""
        self.ensure_one()
        
        try:
            # Check if blacklist record already exists
            existing_blacklist = self.env['ams.member.blacklist'].search([
                ('partner_id', '=', self.partner_id.id)
            ])
            
            if existing_blacklist:
                # Update existing record
                existing_blacklist.write({
                    'reason': self.blacklist_reason,
                    'duration': self.blacklist_duration,
                    'blacklist_date': fields.Date.today(),
                    'active': True,
                })
                return "✓ Updated existing blacklist record"
            else:
                # Create new blacklist record
                blacklist_vals = {
                    'partner_id': self.partner_id.id,
                    'reason': self.blacklist_reason,
                    'duration': self.blacklist_duration,
                    'blacklist_date': fields.Date.today(),
                    'rejected_subscription_id': self.subscription_id.id,
                    'active': True,
                }
                
                self.env['ams.member.blacklist'].create(blacklist_vals)
                return "✓ Added to blacklist"
                
        except Exception as e:
            _logger.error(f"Blacklist processing failed: {e}")
            return f"✗ Failed to add to blacklist: {str(e)}"

    def _send_rejection_notification(self):
        """Send rejection notification to applicant"""
        self.ensure_one()
        
        try:
            if not self.partner_id.email:
                return "ℹ No email address found for applicant"
            
            template = self.email_template_id
            if not template:
                template = self.env.ref(
                    'ams_subscriptions.email_template_membership_rejected',
                    raise_if_not_found=False
                )
            
            if not template:
                return "✗ No email template found"
            
            # Prepare email values
            email_values = {
                'subject': f"Membership Application - {self.membership_type_id.name if self.membership_type_id else 'Application'}",
            }
            
            if self.custom_message:
                email_values['body_html'] = self.custom_message
            
            # Send email
            template.send_mail(
                self.subscription_id.id,
                force_send=True,
                email_values=email_values
            )
            
            return f"✓ Rejection notification sent to {self.partner_id.email}"
            
        except Exception as e:
            _logger.error(f"Notification sending failed: {e}")
            return f"✗ Failed to send notification: {str(e)}"

    def action_preview_notification(self):
        """Preview the rejection notification"""
        self.ensure_one()
        
        if not self.email_template_id:
            raise UserError(_("Please select an email template first."))
        
        # Generate preview
        return {
            'type': 'ir.actions.act_window',
            'name': _('Email Preview'),
            'res_model': 'mail.template',
            'res_id': self.email_template_id.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_id': self.subscription_id.id,
                'default_model': 'ams.member.subscription',
            }
        }

    def action_cancel(self):
        """Cancel the rejection process"""
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def create_from_subscription(self, subscription_id, reason=None):
        """Create rejection wizard for a specific subscription"""
        subscription = self.env['ams.member.subscription'].browse(subscription_id)
        
        if not subscription.exists():
            raise UserError(_("Subscription not found."))
        
        wizard_vals = {
            'subscription_id': subscription_id,
        }
        
        if reason:
            wizard_vals['rejection_reason'] = reason
        
        wizard = self.create(wizard_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.rejection.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _('Reject Subscription'),
        }


class AMSMemberBlacklist(models.Model):
    """Model to track blacklisted members"""
    _name = 'ams.member.blacklist'
    _description = 'AMS Member Blacklist'
    _order = 'blacklist_date desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        ondelete='cascade'
    )
    
    reason = fields.Text(
        string='Blacklist Reason',
        required=True
    )
    
    duration = fields.Selection([
        ('permanent', 'Permanent'),
        ('1year', '1 Year'),
        ('2years', '2 Years'),
        ('5years', '5 Years')
    ], string='Duration', required=True)
    
    blacklist_date = fields.Date(
        string='Blacklist Date',
        required=True,
        default=fields.Date.context_today
    )
    
    expiry_date = fields.Date(
        string='Expiry Date',
        compute='_compute_expiry_date',
        store=True
    )
    
    rejected_subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Related Subscription'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    notes = fields.Text(string='Additional Notes')

    @api.depends('blacklist_date', 'duration')
    def _compute_expiry_date(self):
        """Compute expiry date based on duration"""
        for record in self:
            if record.duration == 'permanent':
                record.expiry_date = False
            elif record.blacklist_date:
                if record.duration == '1year':
                    record.expiry_date = record.blacklist_date + relativedelta(years=1)
                elif record.duration == '2years':
                    record.expiry_date = record.blacklist_date + relativedelta(years=2)
                elif record.duration == '5years':
                    record.expiry_date = record.blacklist_date + relativedelta(years=5)
            else:
                record.expiry_date = False

    @api.model
    def is_blacklisted(self, partner_id):
        """Check if a partner is currently blacklisted"""
        today = fields.Date.today()
        
        blacklist_record = self.search([
            ('partner_id', '=', partner_id),
            ('active', '=', True),
            '|',
            ('expiry_date', '=', False),  # Permanent
            ('expiry_date', '>', today)   # Not expired
        ], limit=1)
        
        return bool(blacklist_record)

    @api.model
    def cleanup_expired_blacklists(self):
        """Cron job to deactivate expired blacklist records"""
        today = fields.Date.today()
        
        expired_records = self.search([
            ('active', '=', True),
            ('expiry_date', '!=', False),
            ('expiry_date', '<=', today)
        ])
        
        expired_records.write({'active': False})
        
        return len(expired_records)