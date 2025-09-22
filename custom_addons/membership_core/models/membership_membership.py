# -*- coding: utf-8 -*-
# Part of Association Management Software (AMS)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class MembershipMembership(models.Model):
    _name = 'membership.membership'
    _description = 'Membership Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, name'
    _rec_name = 'display_name'
    
    # SQL constraints for business rules
    _sql_constraints = [
        ('unique_membership_number', 'unique(name)', 'Membership number must be unique'),
        ('valid_date_range', 'check(end_date IS NULL OR end_date >= start_date)', 
         'End date must be after start date'),
        ('positive_amount_paid', 'check(amount_paid >= 0)', 'Amount paid must be positive')
    ]
    
    # Core identification
    name = fields.Char(
        string='Membership Number',
        required=True,
        copy=False,
        default='New',
        help='Unique membership identification number',
        tracking=True
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    # Partner relationship
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        ondelete='cascade',
        help='Partner who holds this membership',
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    # Membership type and category
    membership_type_id = fields.Many2one(
        'membership.type',
        string='Membership Type',
        required=True,
        ondelete='restrict',
        tracking=True
    )
    
    membership_category = fields.Selection(
        related='membership_type_id.membership_category',
        store=True,
        string='Category'
    )
    
    # Related fields from membership type
    membership_type_description = fields.Html(
        related='membership_type_id.description',
        string='Membership Type Description',
        readonly=True
    )
    
    # State management with full lifecycle
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('cancelled', 'Cancelled')
    ], string='Status',
       default='draft',
       required=True,
       tracking=True,
       help='Current membership status')
    
    # Date management
    start_date = fields.Date(
        string='Start Date',
        help='Membership activation date',
        tracking=True
    )
    
    end_date = fields.Date(
        string='End Date',
        help='Membership expiration date. Empty for lifetime memberships',
        tracking=True
    )
    
    grace_end_date = fields.Date(
        string='Grace Period End',
        help='Date when grace period expires and membership moves to suspended'
    )
    
    suspension_end_date = fields.Date(
        string='Suspension End',
        help='Date when suspension period expires and membership terminates'
    )
    
    termination_date = fields.Date(
        string='Termination Date',
        help='Date when membership was terminated'
    )
    
    # Financial information
    amount_paid = fields.Float(
        string='Amount Paid',
        digits='Product Price',
        default=0.0,
        help='Total amount paid for this membership',
        tracking=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='membership_type_id.currency_id',
        store=True
    )
    
    # Renewal information
    renewal_date = fields.Date(
        string='Next Renewal Date',
        compute='_compute_renewal_date',
        store=True
    )
    
    auto_renewal = fields.Boolean(
        related='membership_type_id.auto_renewal',
        string='Auto-Renewal'
    )
    
    renewal_reminder_sent = fields.Boolean(
        string='Renewal Reminder Sent',
        default=False
    )
    
    # Additional computed fields for views
    days_until_expiry = fields.Integer(
        string='Days Until Expiry',
        compute='_compute_expiry_info',
        help='Number of days until membership expires'
    )
    
    is_expiring_soon = fields.Boolean(
        string='Expiring Soon',
        compute='_compute_expiry_info',
        help='True if membership expires within 30 days'
    )
    
    # Additional information
    notes = fields.Text(
        string='Internal Notes',
        help='Internal notes about this membership'
    )
    
    # Reference fields for integration
    invoice_ids = fields.Many2many(
        'account.move',
        string='Invoices',
        help='Invoices related to this membership'
    )
    
    # Computed field implementations
    @api.depends('name', 'partner_id.name', 'membership_type_id.name')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.name != 'New':
                record.display_name = f"{record.name} - {record.partner_id.name}"
            else:
                record.display_name = f"{record.membership_type_id.name} - {record.partner_id.name}"
    
    @api.depends('end_date', 'membership_type_id.duration')
    def _compute_renewal_date(self):
        for record in self:
            if record.end_date and not record.membership_type_id.is_lifetime:
                # Renewal typically 30 days before expiry
                record.renewal_date = record.end_date - timedelta(days=30)
            else:
                record.renewal_date = False
    
    @api.depends('end_date', 'state')
    def _compute_expiry_info(self):
        for record in self:
            if record.end_date and record.state in ['active', 'grace']:
                today = fields.Date.today()
                delta = (record.end_date - today).days
                record.days_until_expiry = max(0, delta)
                record.is_expiring_soon = 0 <= delta <= 30
            else:
                record.days_until_expiry = 0
                record.is_expiring_soon = False
    
    # Business rule constraints
    @api.constrains('partner_id', 'membership_type_id', 'state')
    def _check_parent_membership_exclusivity(self):
        """Enforce single parent membership rule"""
        for record in self:
            if record.membership_type_id.membership_category in ['individual', 'organization']:
                if record.state in ['active', 'grace']:
                    existing = self.search([
                        ('partner_id', '=', record.partner_id.id),
                        ('id', '!=', record.id),
                        ('state', 'in', ['active', 'grace']),
                        ('membership_type_id.membership_category', 'in', ['individual', 'organization'])
                    ])
                    if existing:
                        raise ValidationError(
                            _("Partner %s already has an active parent membership (%s). "
                              "Only one parent membership allowed.") % 
                            (record.partner_id.name, existing[0].membership_type_id.name)
                        )
    
    # Lifecycle management methods
    @api.model
    def create(self, vals):
        """Override create to generate membership number"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('membership.membership') or 'New'
        
        # Set company from partner if not provided
        if not vals.get('company_id') and vals.get('partner_id'):
            partner = self.env['res.partner'].browse(vals['partner_id'])
            vals['company_id'] = partner.company_id.id or self.env.company.id
        
        return super().create(vals)
    
    def action_activate(self):
        """Activate membership with business rule validation"""
        for record in self:
            # Run validation checks
            record._check_parent_membership_exclusivity()
            
            # Set activation date and end date
            record.start_date = fields.Date.today()
            if record.membership_type_id.duration > 0:
                record.end_date = fields.Date.today() + relativedelta(months=record.membership_type_id.duration)
            else:
                record.end_date = False  # Lifetime membership
            
            record.state = 'active'
            
            # Send welcome email
            if record.membership_type_id.welcome_template_id:
                record.membership_type_id.welcome_template_id.send_mail(record.id)
            
            # Log activation
            record.message_post(
                body=_("Membership activated on %s") % record.start_date,
                message_type='notification'
            )
    
    def action_renew(self, new_end_date=None, amount_paid=0.0):
        """Renew membership"""
        for record in self:
            if not new_end_date:
                if record.membership_type_id.duration > 0:
                    new_end_date = (record.end_date or fields.Date.today()) + relativedelta(months=record.membership_type_id.duration)
                else:
                    new_end_date = False  # Lifetime
            
            record.write({
                'end_date': new_end_date,
                'state': 'active',
                'grace_end_date': False,
                'suspension_end_date': False,
                'renewal_reminder_sent': False,
                'amount_paid': record.amount_paid + amount_paid
            })
            
            # Log renewal
            record.message_post(
                body=_("Membership renewed until %s") % (new_end_date or "lifetime"),
                message_type='notification'
            )
    
    def action_suspend(self, reason=None):
        """Suspend membership"""
        for record in self:
            record.write({
                'state': 'suspended',
                'suspension_end_date': fields.Date.today() + timedelta(days=record.membership_type_id.suspend_period)
            })
            
            # Log suspension
            record.message_post(
                body=_("Membership suspended. Reason: %s") % (reason or "No reason provided"),
                message_type='notification'
            )
    
    def action_terminate(self, reason=None):
        """Terminate membership"""
        for record in self:
            record.write({
                'state': 'terminated',
                'termination_date': fields.Date.today()
            })
            
            # Log termination
            record.message_post(
                body=_("Membership terminated. Reason: %s") % (reason or "No reason provided"),
                message_type='notification'
            )
    
    def action_cancel(self, reason=None):
        """Cancel membership"""
        for record in self:
            record.write({
                'state': 'cancelled'
            })
            
            # Send cancellation email
            if record.membership_type_id.cancellation_template_id:
                record.membership_type_id.cancellation_template_id.send_mail(record.id)
            
            # Log cancellation
            record.message_post(
                body=_("Membership cancelled. Reason: %s") % (reason or "No reason provided"),
                message_type='notification'
            )
    
    def action_view_invoices(self):
        """View invoices related to this membership"""
        self.ensure_one()
        if not self.invoice_ids:
            raise UserError(_("No invoices found for this membership."))
        
        if len(self.invoice_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Membership Invoice'),
                'res_model': 'account.move',
                'res_id': self.invoice_ids[0].id,
                'view_mode': 'form',
                'target': 'current'
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Membership Invoices'),
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.invoice_ids.ids)],
                'target': 'current'
            }
    
    # Automated state transition (called by cron)
    @api.model
    def _cron_update_membership_states(self):
        """Automated membership state transitions"""
        today = fields.Date.today()
        
        # Move expired active memberships to grace period
        expired_active = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
            ('end_date', '!=', False)  # Exclude lifetime memberships
        ])
        
        for membership in expired_active:
            membership.write({
                'state': 'grace',
                'grace_end_date': today + timedelta(days=membership.membership_type_id.grace_period)
            })
            
            # Send expiry notice
            if membership.membership_type_id.expiry_template_id:
                membership.membership_type_id.expiry_template_id.send_mail(membership.id)
        
        # Move grace period memberships to suspended
        grace_expired = self.search([
            ('state', '=', 'grace'),
            ('grace_end_date', '<', today)
        ])
        
        for membership in grace_expired:
            membership.action_suspend(reason="Grace period expired")
        
        # Move suspended memberships to terminated
        suspension_expired = self.search([
            ('state', '=', 'suspended'),
            ('suspension_end_date', '<', today)
        ])
        
        for membership in suspension_expired:
            membership.action_terminate(reason="Suspension period expired")
    
    @api.model
    def _cron_send_renewal_reminders(self):
        """Send renewal reminders"""
        # Get memberships expiring in 30 days that haven't received reminder
        reminder_date = fields.Date.today() + timedelta(days=30)
        
        expiring_memberships = self.search([
            ('state', '=', 'active'),
            ('end_date', '=', reminder_date),
            ('renewal_reminder_sent', '=', False),
            ('membership_type_id.renewal_template_id', '!=', False)
        ])
        
        for membership in expiring_memberships:
            membership.membership_type_id.renewal_template_id.send_mail(membership.id)
            membership.renewal_reminder_sent = True
    
    # Utility methods
    def get_days_until_expiry(self):
        """Get number of days until membership expires"""
        self.ensure_one()
        if not self.end_date:
            return None  # Lifetime membership
        
        today = fields.Date.today()
        if self.end_date < today:
            return 0  # Already expired
        
        return (self.end_date - today).days
    
    def is_expiring_soon(self, days=30):
        """Check if membership is expiring within specified days"""
        days_until_expiry = self.get_days_until_expiry()
        return days_until_expiry is not None and days_until_expiry <= days