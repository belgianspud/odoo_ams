# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AMSSubscriptionSeat(models.Model):
    _name = 'ams.subscription.seat'
    _description = 'AMS Subscription Seat'
    _inherit = ['mail.thread']

    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade'
    )

    contact_id = fields.Many2one(
        'res.partner',
        string='Assigned Contact',
        required=True
    )

    assigned_date = fields.Date(
        string='Assigned Date',
        default=fields.Date.context_today
    )

    active = fields.Boolean(
        string='Active Seat',
        default=True,
        help='When unchecked, the seat is freed for reassignment.'
    )

    @api.model
    def create(self, vals):
        seat = super().create(vals)
        seat._activate_contact_membership()
        return seat

    def unlink(self):
        for seat in self:
            seat._deactivate_contact_membership()
        return super().unlink()

    # ------------------------
    # Internal helper methods
    # ------------------------
    def _activate_contact_membership(self):
        """Optional: Automatically mark contact as 'member' or assign benefits."""
        for seat in self:
            contact = seat.contact_id
            # Example: flag the contact as an active member
            if hasattr(contact, 'is_member'):
                contact.is_member = True

    def _deactivate_contact_membership(self):
        """Optional: Remove membership status if seat is removed."""
        for seat in self:
            contact = seat.contact_id
            if hasattr(contact, 'is_member'):
                contact.is_member = False
