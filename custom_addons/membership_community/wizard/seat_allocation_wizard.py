# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class SeatAllocationWizard(models.TransientModel):
    """
    Wizard to allocate seats to employees for organizational subscriptions
    """
    _name = 'seat.allocation.wizard'
    _description = 'Seat Allocation Wizard'

    subscription_id = fields.Many2one(
        'subscription.subscription',
        string='Organization Subscription',
        required=True,
        readonly=True,
        help='The organizational subscription to allocate seats from'
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
    
    max_seats = fields.Integer(
        string='Maximum Seats',
        related='subscription_id.max_seats',
        readonly=True
    )
    
    allocated_seat_count = fields.Integer(
        string='Allocated Seats',
        related='subscription_id.allocated_seat_count',
        readonly=True
    )
    
    available_seat_count = fields.Integer(
        string='Available Seats',
        related='subscription_id.available_seat_count',
        readonly=True
    )
    
    # Allocation method
    allocation_method = fields.Selection([
        ('single', 'Allocate Single Seat'),
        ('multiple', 'Allocate Multiple Seats'),
    ], string='Allocation Method',
       default='single',
       required=True)
    
    # Single seat allocation
    employee_id = fields.Many2one(
        'res.partner',
        string='Employee',
        domain=[('is_company', '=', False)],
        help='Employee to assign the seat to'
    )
    
    employee_email = fields.Char(
        string='Email',
        related='employee_id.email',
        readonly=True
    )
    
    employee_phone = fields.Char(
        string='Phone',
        related='employee_id.phone',
        readonly=True
    )
    
    # Multiple seat allocation
    employee_ids = fields.Many2many(
        'res.partner',
        'seat_allocation_partner_rel',
        'wizard_id',
        'partner_id',
        string='Employees',
        domain=[('is_company', '=', False)],
        help='Multiple employees to assign seats to'
    )
    
    seats_to_allocate = fields.Integer(
        string='Seats to Allocate',
        compute='_compute_seats_to_allocate',
        store=True
    )
    
    # Options
    send_notification_email = fields.Boolean(
        string='Send Notification Email',
        default=True,
        help='Send email to employees notifying them of their seat assignment'
    )
    
    organizational_role = fields.Selection([
        ('primary_contact', 'Primary Contact'),
        ('billing_contact', 'Billing Contact'),
        ('seat_user', 'Seat User'),
        ('admin', 'Administrator'),
    ], string='Organizational Role',
       default='seat_user',
       help='Role of the employee in the organization')
    
    # Summary
    allocation_summary = fields.Html(
        string='Allocation Summary',
        compute='_compute_allocation_summary'
    )

    @api.depends('allocation_method', 'employee_id', 'employee_ids')
    def _compute_seats_to_allocate(self):
        """Calculate how many seats will be allocated"""
        for wizard in self:
            if wizard.allocation_method == 'single':
                wizard.seats_to_allocate = 1 if wizard.employee_id else 0
            else:
                wizard.seats_to_allocate = len(wizard.employee_ids)
    
    @api.depends('seats_to_allocate', 'available_seat_count', 'employee_id', 'employee_ids')
    def _compute_allocation_summary(self):
        """Generate allocation summary"""
        for wizard in self:
            summary = '<div class="alert alert-info">'
            summary += '<h5><i class="fa fa-info-circle"/> Allocation Summary</h5>'
            summary += '<ul>'
            summary += f'<li><strong>Organization:</strong> {wizard.partner_id.name}</li>'
            summary += f'<li><strong>Plan:</strong> {wizard.plan_id.name}</li>'
            summary += f'<li><strong>Total Seats:</strong> {wizard.max_seats}</li>'
            summary += f'<li><strong>Currently Allocated:</strong> {wizard.allocated_seat_count}</li>'
            summary += f'<li><strong>Available:</strong> {wizard.available_seat_count}</li>'
            summary += f'<li><strong>Seats to Allocate:</strong> <span class="text-primary">{wizard.seats_to_allocate}</span></li>'
            
            if wizard.seats_to_allocate > wizard.available_seat_count:
                summary += f'<li class="text-danger"><strong>⚠️ Warning:</strong> Not enough seats available!</li>'
            
            summary += '</ul>'
            
            if wizard.allocation_method == 'single' and wizard.employee_id:
                summary += f'<p class="mb-0"><strong>Employee:</strong> {wizard.employee_id.name}'
                if wizard.employee_email:
                    summary += f' ({wizard.employee_email})'
                summary += '</p>'
            elif wizard.allocation_method == 'multiple' and wizard.employee_ids:
                summary += f'<p class="mb-0"><strong>Employees ({len(wizard.employee_ids)}):</strong></p>'
                summary += '<ul class="mb-0">'
                for emp in wizard.employee_ids[:5]:  # Show first 5
                    summary += f'<li>{emp.name}'
                    if emp.email:
                        summary += f' ({emp.email})'
                    summary += '</li>'
                if len(wizard.employee_ids) > 5:
                    summary += f'<li><em>...and {len(wizard.employee_ids) - 5} more</em></li>'
                summary += '</ul>'
            
            summary += '</div>'
            wizard.allocation_summary = summary

    @api.onchange('allocation_method')
    def _onchange_allocation_method(self):
        """Clear fields when switching method"""
        if self.allocation_method == 'single':
            self.employee_ids = [(5, 0, 0)]
        else:
            self.employee_id = False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Validate single employee selection"""
        if self.employee_id:
            # Check if employee already has a seat
            if self.employee_id.seat_subscription_id:
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _(
                            '%s already has a seat subscription (%s). '
                            'You may want to choose a different employee.'
                        ) % (self.employee_id.name, self.employee_id.seat_subscription_id.name)
                    }
                }

    def action_allocate_seats(self):
        """Allocate seats to selected employees"""
        self.ensure_one()
        
        # Validate
        self._validate_allocation()
        
        # Get employees to allocate
        employees = self._get_employees_to_allocate()
        
        if not employees:
            raise UserError(_('No employees selected for seat allocation.'))
        
        # Check availability
        if len(employees) > self.available_seat_count:
            raise UserError(_(
                'Cannot allocate %s seats. Only %s seats available.'
            ) % (len(employees), self.available_seat_count))
        
        # Allocate seats
        allocated_subscriptions = []
        failed_allocations = []
        
        for employee in employees:
            try:
                seat_sub = self.subscription_id.action_allocate_seat(employee.id)
                
                # Set organizational role
                if seat_sub:
                    employee.write({
                        'organizational_role': self.organizational_role,
                    })
                    allocated_subscriptions.append(seat_sub)
                    
                    # Send notification email
                    if self.send_notification_email:
                        self._send_seat_notification_email(employee, seat_sub)
                        
            except Exception as e:
                failed_allocations.append((employee.name, str(e)))
        
        # Prepare result message
        return self._show_allocation_result(allocated_subscriptions, failed_allocations)
    
    def _get_employees_to_allocate(self):
        """Get list of employees to allocate seats to"""
        if self.allocation_method == 'single':
            return self.employee_id if self.employee_id else self.env['res.partner']
        else:
            return self.employee_ids
    
    def _validate_allocation(self):
        """Validate allocation before processing"""
        # Check subscription state
        if self.subscription_id.state not in ('active', 'trial'):
            raise UserError(_(
                'Cannot allocate seats. Subscription must be active or in trial. '
                'Current state: %s'
            ) % self.subscription_id.state)
        
        # Check if plan supports seats
        if not self.subscription_id.plan_id.supports_seats:
            raise UserError(_(
                'This subscription plan does not support multiple seats.'
            ))
        
        # Check employees
        employees = self._get_employees_to_allocate()
        
        if not employees:
            raise UserError(_('Please select at least one employee.'))
        
        # Check for duplicates in selection
        if self.allocation_method == 'multiple':
            if len(employees) != len(set(employees.ids)):
                raise UserError(_('You have selected the same employee multiple times.'))
        
        # Check for existing seat subscriptions
        existing_seats = []
        for employee in employees:
            if employee.seat_subscription_id:
                existing_seats.append(employee.name)
        
        if existing_seats:
            raise UserError(_(
                'The following employees already have seat subscriptions:\n%s\n\n'
                'Please remove them from the selection or deallocate their existing seats first.'
            ) % '\n'.join(existing_seats))
    
    def _send_seat_notification_email(self, employee, seat_subscription):
        """Send notification email to employee"""
        template = self.env.ref(
            'membership_community.email_template_seat_allocated',
            raise_if_not_found=False
        )
        
        if template and employee.email:
            try:
                # Temporarily set context with employee
                template.with_context(
                    employee_id=employee.id,
                    seat_subscription_id=seat_subscription.id,
                    organization_id=self.partner_id.id
                ).send_mail(seat_subscription.id, force_send=False)
            except Exception as e:
                # Don't fail allocation if email fails
                self.subscription_id.message_post(
                    body=_('Warning: Could not send notification email to %s: %s') % (employee.name, str(e)),
                    message_type='comment'
                )
    
    def _show_allocation_result(self, allocated_subscriptions, failed_allocations):
        """Show allocation result to user"""
        message = ''
        
        if allocated_subscriptions:
            message += f'✅ Successfully allocated {len(allocated_subscriptions)} seat(s)!\n\n'
            message += 'Allocated to:\n'
            for sub in allocated_subscriptions:
                message += f'• {sub.seat_holder_id.name} ({sub.name})\n'
        
        if failed_allocations:
            message += f'\n❌ Failed to allocate {len(failed_allocations)} seat(s):\n'
            for emp_name, error in failed_allocations:
                message += f'• {emp_name}: {error}\n'
        
        message_type = 'success' if not failed_allocations else 'warning'
        title = _('Seat Allocation Complete') if not failed_allocations else _('Seat Allocation Partial')
        
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
    
    def action_create_new_employee(self):
        """Open form to create new employee partner"""
        self.ensure_one()
        
        return {
            'name': _('Create Employee'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_is_company': False,
                'default_parent_id': self.partner_id.id,
            }
        }