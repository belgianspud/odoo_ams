# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AMSSubscriptionModification(models.Model):
    """Track subscription modifications (upgrades, downgrades, pauses, etc.)"""
    _name = 'ams.subscription.modification'
    _description = 'AMS Subscription Modification'
    _order = 'modification_date desc'
    _inherit = ['mail.thread']

    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade'
    )
    
    modification_type = fields.Selection([
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('pause', 'Pause'),
        ('resume', 'Resume'),
        ('cancellation', 'Cancellation'),
        ('seat_change', 'Seat Change'),
    ], string='Modification Type', required=True, tracking=True)
    
    modification_date = fields.Date(
        string='Modification Date',
        default=fields.Date.today,
        required=True,
        tracking=True
    )
    
    old_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='Previous Tier'
    )
    
    new_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='New Tier'
    )
    
    reason = fields.Text(
        string='Reason',
        required=True,
        tracking=True
    )
    
    proration_amount = fields.Float(
        string='Proration Amount',
        help='Amount charged/credited for the modification',
        tracking=True
    )
    
    proration_invoice_id = fields.Many2one(
        'account.move',
        string='Proration Invoice'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Modified By',
        default=lambda self: self.env.user,
        tracking=True
    )
    
    # For seat changes
    old_seat_count = fields.Integer(
        string='Previous Seats',
        help='Number of seats before modification'
    )
    
    new_seat_count = fields.Integer(
        string='New Seats',
        help='Number of seats after modification'
    )
    
    # Status tracking
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('applied', 'Applied'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    def action_confirm(self):
        """Confirm the modification"""
        self.ensure_one()
        self.state = 'confirmed'
        self.subscription_id.message_post(
            body=f"Modification confirmed: {self.modification_type} - {self.reason}"
        )

    def action_apply(self):
        """Apply the modification to the subscription"""
        self.ensure_one()
        self.state = 'applied'
        self.subscription_id.message_post(
            body=f"Modification applied: {self.modification_type} completed successfully"
        )

    def action_cancel(self):
        """Cancel the modification"""
        self.ensure_one()
        self.state = 'cancelled'
        self.subscription_id.message_post(
            body=f"Modification cancelled: {self.modification_type} - {self.reason}"
        )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-confirm simple modifications"""
        records = super().create(vals_list)
        
        # Auto-confirm certain types of modifications
        for record in records:
            if record.modification_type in ['pause', 'resume']:
                record.action_confirm()
                record.action_apply()
        
        return records