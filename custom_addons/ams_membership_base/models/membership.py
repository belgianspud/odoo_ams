from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class Membership(models.Model):
    _name = 'membership.membership'
    _description = 'Membership Record'
    _order = 'start_date desc'
    _rec_name = 'display_name'

    # Basic Information
    partner_id = fields.Many2one(
        'res.partner', 
        string='Member', 
        required=True,
        ondelete='cascade',
        help="The contact this membership belongs to"
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    # Dates
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        help="Date when membership becomes active"
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        help="Date when membership expires"
    )
    paid_through_date = fields.Date(
        string='Paid Through Date',
        help="Date through which dues have been paid"
    )
    
    # Status
    state = fields.Selection([
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('lapsed', 'Lapsed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='active', required=True, tracking=True)
    
    # Financial
    invoice_ids = fields.One2many(
        'account.move',
        'membership_id',
        string='Related Invoices',
        domain=[('move_type', '=', 'out_invoice')]
    )
    total_invoiced = fields.Monetary(
        string='Total Invoiced',
        compute='_compute_financial_totals',
        currency_field='currency_id'
    )
    total_paid = fields.Monetary(
        string='Total Paid',
        compute='_compute_financial_totals',
        currency_field='currency_id'
    )
    balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_financial_totals',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # Computed fields
    days_until_expiry = fields.Integer(
        string='Days Until Expiry',
        compute='_compute_days_until_expiry'
    )
    is_current = fields.Boolean(
        string='Is Current',
        compute='_compute_is_current',
        help="True if membership is currently active and not expired"
    )

    @api.depends('partner_id.name')
    def _compute_display_name(self):
        for record in self:
            if record.partner_id:
                record.display_name = f"{record.partner_id.name} Membership"
            else:
                record.display_name = "New Membership"

    @api.depends('end_date')
    def _compute_days_until_expiry(self):
        today = fields.Date.today()
        for record in self:
            if record.end_date:
                delta = record.end_date - today
                record.days_until_expiry = delta.days
            else:
                record.days_until_expiry = 0

    @api.depends('state', 'end_date')
    def _compute_is_current(self):
        today = fields.Date.today()
        for record in self:
            record.is_current = (
                record.state in ['active', 'grace'] and 
                record.end_date and 
                record.end_date >= today
            )

    @api.depends('invoice_ids.amount_total', 'invoice_ids.amount_residual', 'invoice_ids.state')
    def _compute_financial_totals(self):
        for record in self:
            invoices = record.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            record.total_invoiced = sum(invoices.mapped('amount_total'))
            record.balance_due = sum(invoices.mapped('amount_residual'))
            record.total_paid = record.total_invoiced - record.balance_due

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date > record.end_date:
                    raise ValidationError(_("Start date cannot be after end date."))

    @api.model
    def update_membership_statuses(self):
        """Cron job method to update membership statuses based on dates"""
        today = fields.Date.today()
        grace_period_days = 30  # Configurable grace period
        
        # Find memberships that should be in grace period
        grace_memberships = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
            ('end_date', '>=', today - timedelta(days=grace_period_days))
        ])
        grace_memberships.write({'state': 'grace'})
        
        # Find memberships that should be lapsed
        lapsed_memberships = self.search([
            ('state', 'in', ['active', 'grace']),
            ('end_date', '<', today - timedelta(days=grace_period_days))
        ])
        lapsed_memberships.write({'state': 'lapsed'})
        
        _logger.info(f"Updated {len(grace_memberships)} memberships to grace period")
        _logger.info(f"Updated {len(lapsed_memberships)} memberships to lapsed")

    def action_activate(self):
        """Activate membership"""
        self.write({'state': 'active'})

    def action_cancel(self):
        """Cancel membership"""
        self.write({'state': 'cancelled'})

    def action_renew(self):
        """Renew membership for another period"""
        for record in self:
            # Extend end date by one year
            new_end_date = record.end_date + timedelta(days=365)
            record.write({
                'end_date': new_end_date,
                'state': 'active'
            })


class ResPartner(models.Model):
    _inherit = 'res.partner'

    membership_ids = fields.One2many(
        'membership.membership',
        'partner_id',
        string='Memberships'
    )
    current_membership_id = fields.Many2one(
        'membership.membership',
        string='Current Membership',
        compute='_compute_current_membership'
    )
    is_member = fields.Boolean(
        string='Is Member',
        compute='_compute_current_membership'
    )

    @api.depends('membership_ids.is_current')
    def _compute_current_membership(self):
        for partner in self:
            current_membership = partner.membership_ids.filtered('is_current')
            if current_membership:
                partner.current_membership_id = current_membership[0]
                partner.is_member = True
            else:
                partner.current_membership_id = False
                partner.is_member = False


class AccountMove(models.Model):
    _inherit = 'account.move'

    membership_id = fields.Many2one(
        'membership.membership',
        string='Related Membership',
        help="Membership this invoice is related to"
    )