# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class SeatDeallocationWizard(models.TransientModel):
    """
    Wizard to deallocate seats from employees for organizational subscriptions
    """
    _name = 'seat.deallocation.wizard'
    _description = 'Seat Deallocation Wizard'

    subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Organization Subscription',
        required=True,
        readonly=True,
        help='The organizational subscription to deallocate seats from'
    )
    
    seat_subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Seat Subscription',
        help='Specific seat subscription to deallocate'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Organization',
        related='subscription_id.partner_id',
        readonly=True
    )
    
    plan_id = fields.Many2one(
        'subscription.plan',
        string='Plan',
        related='subscription_id.plan_id',
        readonly=True
    )
    
    # Deallocation method
    deallocation_method = fields.Selection([
        ('single', 'Remove Single Seat'),
        ('multiple', 'Remove Multiple Seats'),
    ], string='Deallocation Method',
       default='single',
       required=True)
    
    # Single seat deallocation
    seat_holder_id = fields.Many2one(
        'res.partner',
        string='Seat Holder',
        compute='_compute_seat_holder_id',
        store=True,
        readonly=True,
        help='Employee currently using this seat'
    )
    
    seat_holder_email = fields.Char(
        string='Email',
        related='seat_holder_id.email',
        readonly=True
    )
    
    # Multiple seat deallocation
    seat_subscription_ids = fields.Many2many(
        'subscription.subscription',
        'seat_deallocation_subscription_rel',
        'wizard_id',
        'subscription_id',
        string='Seat Subscriptions',
        domain="[('parent_subscription_id', '=', subscription_id), ('is_seat_subscription', '=', True)]",
        help='Multiple seat subscriptions to remove'
    )
    
    seats_to_deallocate = fields.Integer(
        string='Seats to Deallocate',
        compute='_compute_seats_to_deallocate',
        store=True
    )
    
    # Current seat status
    max_seats = fields.Integer(
        string='Maximum Seats',
        related='subscription_id.max_seats',
        readonly=True
    )
    
    allocated_seat_count = fields.Integer(
        string='Currently Allocated',
        related='subscription_id.allocated_seat_count',
        readonly=True
    )
    
    available_seat_count = fields.Integer(
        string='Available After Deallocation',
        compute='_compute_available_after',
        help='Number of seats that will be available after deallocation'
    )
    
    # Options
    send_notification_email = fields.Boolean(
        string='Send Notification Email',
        default=True,
        help='Send email to employees notifying them of seat removal'
    )
    
    reason = fields.Selection([
        ('employee_left', 'Employee Left Organization'),
        ('role_changed', 'Role Changed - No Longer Needs Access'),
        ('reassignment', 'Reassigning to Another Employee'),
        ('subscription_downgrade', 'Subscription Downgrade'),
        ('other', 'Other Reason'),
    ], string='Deallocation Reason',
       default='other',
       help='Reason for removing seat allocation')
    
    reason_notes = fields.Text(
        string='Additional Notes',
        help='Optional notes about the deallocation'
    )
    
    # Action on seat subscription
    seat_action = fields.Selection([
        ('cancel', 'Cancel Seat Subscription'),
        ('expire', 'Mark as Expired'),
    ], string='Seat Subscription Action',
       default='cancel',
       required=True,
       help='What to do with the seat subscription after deallocation')
    
    # Summary
    deallocation_summary = fields.Html(
        string='Deallocation Summary',
        compute='_compute_deallocation_summary'
    )

    @api.depends('seat_subscription_id')
    def _compute_seat_holder_id(self):
        """Get seat holder from seat subscription"""
        for wizard in self:
            if wizard.seat_subscription_id:
                wizard.seat_holder_id = wizard.seat_subscription_id.seat_holder_id
            else:
                wizard.seat_holder_id = False

    @api.depends('deallocation_method', 'seat_subscription_id', 'seat_subscription_ids')
    def _compute_seats_to_deallocate(self):
        """Calculate how many seats will be deallocated"""
        for wizard in self:
            if wizard.deallocation_method == 'single':
                wizard.seats_to_deallocate = 1 if wizard.seat_subscription_id else 0
            else:
                wizard.seats_to_deallocate = len(wizard.seat_subscription_ids)
    
    @api.depends('allocated_seat_count', 'seats_to_deallocate')
    def _compute_available_after(self):
        """Calculate seats available after deallocation"""
        for wizard in self:
            wizard.available_seat_count = wizard.subscription_id.available_seat_count + wizard.seats_to_deallocate
    
    @api.depends('seats_to_deallocate', 'seat_holder_id', 'seat_subscription_ids', 'reason', 'seat_action')
    def _compute_deallocation_summary(self):
        """Generate deallocation summary"""
        for wizard in self:
            summary = '<div class="alert alert-warning">'
            summary += '<h5><i class="fa fa-exclamation-triangle"/> Deallocation Summary</h5>'
            summary += '<ul>'
            summary += f'<li><strong>Organization:</strong> {wizard.partner_id.name}</li>'
            summary += f'<li><strong>Plan:</strong> {wizard.plan_id.name}</li>'
            summary += f'<li><strong>Current Allocated Seats:</strong> {wizard.allocated_seat_count}</li>'
            summary += f'<li><strong>Seats to Deallocate:</strong> <span class="text-danger">{wizard.seats_to_deallocate}</span></li>'
            summary += f'<li><strong>Available After:</strong> <span class="text-success">{wizard.available_seat_count}</span></li>'
            
            if wizard.reason:
                reason_display = dict(wizard._fields['reason'].selection).get(wizard.reason)
                summary += f'<li><strong>Reason:</strong> {reason_display}</li>'
            
            action_display = dict(wizard._fields['seat_action'].selection).get(wizard.seat_action)
            summary += f'<li><strong>Action:</strong> {action_display}</li>'
            summary += '</ul>'
            
            if wizard.deallocation_method == 'single' and wizard.seat_holder_id:
                summary += f'<p class="mb-0"><strong>Affected Employee:</strong> {wizard.seat_holder_id.name}'
                if wizard.seat_holder_email:
                    summary += f' ({wizard.seat_holder_email})'
                summary += '</p>'
                if wizard.seat_subscription_id:
                    summary += f'<p class="mb-0"><strong>Seat Subscription:</strong> {wizard.seat_subscription_id.name}</p>'
            elif wizard.deallocation_method == 'multiple' and wizard.seat_subscription_ids:
                summary += f'<p class="mb-0"><strong>Affected Employees ({len(wizard.seat_subscription_ids)}):</strong></p>'
                summary += '<ul class="mb-0">'
                for seat_sub in wizard.seat_subscription_ids[:5]:  # Show first 5
                    holder_name = seat_sub.seat_holder_id.name if seat_sub.seat_holder_id else 'Unknown'
                    summary += f'<li>{holder_name} ({seat_sub.name})</li>'
                if len(wizard.seat_subscription_ids) > 5:
                    summary += f'<li><em>...and {len(wizard.seat_subscription_ids) - 5} more</em></li>'
                summary += '</ul>'
            
            summary += '</div>'
            wizard.deallocation_summary = summary

    @api.onchange('deallocation_method')
    def _onchange_deallocation_method(self):
        """Clear fields when switching method"""
        if self.deallocation_method == 'single':
            self.seat_subscription_ids = [(5, 0, 0)]
        else:
            self.seat_subscription_id = False

    def action_deallocate_seats(self):
        """Deallocate selected seats"""
        self.ensure_one()
        
        # Validate
        self._validate_deallocation()
        
        # Get seat subscriptions to deallocate
        seat_subscriptions = self._get_seat_subscriptions_to_deallocate()
        
        if not seat_subscriptions:
            raise UserError(_('No seat subscriptions selected for deallocation.'))
        
        # Deallocate seats
        deallocated_count = 0
        failed_deallocations = []
        
        for seat_sub in seat_subscriptions:
            try:
                seat_holder_name = seat_sub.seat_holder_id.name if seat_sub.seat_holder_id else 'Unknown'
                
                # Send notification email before deallocation
                if self.send_notification_email and seat_sub.seat_holder_id:
                    self._send_seat_deallocation_email(seat_sub.seat_holder_id, seat_sub)
                
                # Deallocate
                self.subscription_id.action_deallocate_seat(seat_sub.id)
                
                # Log deallocation reason
                if self.reason_notes:
                    self.subscription_id.message_post(
                        body=_('Seat deallocated from %s. Reason: %s') % (seat_holder_name, self.reason_notes),
                        message_type='comment'
                    )
                
                deallocated_count += 1
                    
            except Exception as e:
                failed_deallocations.append((seat_holder_name, str(e)))
        
        # Prepare result message
        return self._show_deallocation_result(deallocated_count, failed_deallocations)
    
    def _get_seat_subscriptions_to_deallocate(self):
        """Get list of seat subscriptions to deallocate"""
        if self.deallocation_method == 'single':
            return self.seat_subscription_id if self.seat_subscription_id else self.env['subscription.subscription']
        else:
            return self.seat_subscription_ids
    
    def _validate_deallocation(self):
        """Validate deallocation before processing"""
        # Check subscription state
        if self.subscription_id.state not in ('active', 'trial', 'suspended'):
            raise UserError(_(
                'Cannot deallocate seats from subscription in state: %s'
            ) % self.subscription_id.state)
        
        # Check seat subscriptions
        seat_subs = self._get_seat_subscriptions_to_deallocate()
        
        if not seat_subs:
            raise UserError(_('Please select at least one seat subscription to remove.'))
        
        # Verify all seat subscriptions belong to parent
        for seat_sub in seat_subs:
            if seat_sub.parent_subscription_id != self.subscription_id:
                raise UserError(_(
                    'Seat subscription %s does not belong to organization subscription %s'
                ) % (seat_sub.name, self.subscription_id.name))
    
    def _send_seat_deallocation_email(self, employee, seat_subscription):
        """Send notification email to employee"""
        template = self.env.ref(
            'membership_community.email_template_seat_deallocated',
            raise_if_not_found=False
        )
        
        if template and employee.email:
            try:
                # Temporarily set context with employee
                template.with_context(
                    employee_id=employee.id,
                    seat_subscription_id=seat_subscription.id,
                    organization_id=self.partner_id.id,
                    reason=dict(self._fields['reason'].selection).get(self.reason, 'Other'),
                    reason_notes=self.reason_notes or ''
                ).send_mail(seat_subscription.id, force_send=False)
            except Exception as e:
                # Don't fail deallocation if email fails
                self.subscription_id.message_post(
                    body=_('Warning: Could not send notification email to %s: %s') % (employee.name, str(e)),
                    message_type='comment'
                )
    
    def _show_deallocation_result(self, deallocated_count, failed_deallocations):
        """Show deallocation result to user"""
        message = ''
        
        if deallocated_count > 0:
            message += f'✅ Successfully deallocated {deallocated_count} seat(s)!\n\n'
            message += f'Available seats increased from {self.allocated_seat_count} to {self.subscription_id.allocated_seat_count}\n'
        
        if failed_deallocations:
            message += f'\n❌ Failed to deallocate {len(failed_deallocations)} seat(s):\n'
            for emp_name, error in failed_deallocations:
                message += f'• {emp_name}: {error}\n'
        
        message_type = 'success' if not failed_deallocations else 'warning'
        title = _('Seat Deallocation Complete') if not failed_deallocations else _('Seat Deallocation Partial')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': message_type,
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_window_close',
                }
            }
        }
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super().default_get(fields_list)
        
        # Get seat subscription from context if provided
        if self._context.get('default_seat_subscription_id'):
            res['seat_subscription_id'] = self._context.get('default_seat_subscription_id')
            res['deallocation_method'] = 'single'
        
        return res