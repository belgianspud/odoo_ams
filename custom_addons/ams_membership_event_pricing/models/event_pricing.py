from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class Event(models.Model):
    _inherit = 'event.event'

    # Member Pricing
    use_member_pricing = fields.Boolean(
        string='Use Member Pricing',
        default=False,
        help="Enable different pricing for members vs non-members"
    )
    member_price = fields.Float(
        string='Member Price',
        default=0.0,
        help="Price for members"
    )
    non_member_price = fields.Float(
        string='Non-Member Price',
        default=0.0,
        help="Price for non-members"
    )
    member_discount_percent = fields.Float(
        string='Member Discount (%)',
        compute='_compute_member_discount',
        help="Percentage discount for members"
    )
    
    # Early Bird Pricing
    use_early_bird = fields.Boolean(
        string='Early Bird Pricing',
        default=False,
        help="Enable early bird pricing"
    )
    early_bird_deadline = fields.Datetime(
        string='Early Bird Deadline',
        help="Deadline for early bird pricing"
    )
    early_bird_member_price = fields.Float(
        string='Early Bird Member Price',
        default=0.0,
        help="Early bird price for members"
    )
    early_bird_non_member_price = fields.Float(
        string='Early Bird Non-Member Price',
        default=0.0,
        help="Early bird price for non-members"
    )
    
    # Statistics
    member_registrations = fields.Integer(
        string='Member Registrations',
        compute='_compute_registration_statistics',
        help="Number of member registrations"
    )
    non_member_registrations = fields.Integer(
        string='Non-Member Registrations',
        compute='_compute_registration_statistics',
        help="Number of non-member registrations"
    )
    total_member_revenue = fields.Monetary(
        string='Member Revenue',
        compute='_compute_revenue_statistics',
        currency_field='currency_id',
        help="Total revenue from member registrations"
    )
    total_non_member_revenue = fields.Monetary(
        string='Non-Member Revenue',
        compute='_compute_revenue_statistics',
        currency_field='currency_id',
        help="Total revenue from non-member registrations"
    )

    @api.depends('member_price', 'non_member_price')
    def _compute_member_discount(self):
        for event in self:
            if event.non_member_price > 0:
                discount = ((event.non_member_price - event.member_price) / event.non_member_price) * 100
                event.member_discount_percent = max(0, discount)
            else:
                event.member_discount_percent = 0

    @api.depends('registration_ids.is_member')
    def _compute_registration_statistics(self):
        for event in self:
            registrations = event.registration_ids.filtered(lambda r: r.state != 'cancel')
            event.member_registrations = len(registrations.filtered('is_member'))
            event.non_member_registrations = len(registrations.filtered(lambda r: not r.is_member))

    @api.depends('registration_ids.final_price', 'registration_ids.is_member', 'registration_ids.state')
    def _compute_revenue_statistics(self):
        for event in self:
            paid_registrations = event.registration_ids.filtered(lambda r: r.state in ['open', 'done'])
            member_regs = paid_registrations.filtered('is_member')
            non_member_regs = paid_registrations.filtered(lambda r: not r.is_member)
            
            event.total_member_revenue = sum(member_regs.mapped('final_price'))
            event.total_non_member_revenue = sum(non_member_regs.mapped('final_price'))

    @api.constrains('member_price', 'non_member_price')
    def _check_prices(self):
        for event in self:
            if event.use_member_pricing:
                if event.member_price < 0 or event.non_member_price < 0:
                    raise ValidationError(_("Prices cannot be negative."))

    @api.constrains('early_bird_deadline')
    def _check_early_bird_deadline(self):
        for event in self:
            if event.use_early_bird and event.early_bird_deadline:
                if event.early_bird_deadline >= event.date_begin:
                    raise ValidationError(_("Early bird deadline must be before event start date."))

    def get_price_for_partner(self, partner_id=None):
        """Get the appropriate price for a specific partner"""
        self.ensure_one()
        
        if not self.use_member_pricing:
            return self.standard_price if hasattr(self, 'standard_price') else 0.0
        
        # Check if it's early bird period
        is_early_bird = (
            self.use_early_bird and 
            self.early_bird_deadline and 
            fields.Datetime.now() <= self.early_bird_deadline
        )
        
        # Determine if partner is a member
        is_member = False
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            is_member = partner.is_member
        
        # Return appropriate price
        if is_early_bird:
            return self.early_bird_member_price if is_member else self.early_bird_non_member_price
        else:
            return self.member_price if is_member else self.non_member_price

    def action_view_member_registrations(self):
        """View member registrations"""
        self.ensure_one()
        return {
            'name': f"Member Registrations - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'event.registration',
            'view_mode': 'tree,form',
            'domain': [('event_id', '=', self.id), ('is_member', '=', True)],
            'context': {'default_event_id': self.id},
        }

    def action_view_non_member_registrations(self):
        """View non-member registrations"""
        self.ensure_one()
        return {
            'name': f"Non-Member Registrations - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'event.registration',
            'view_mode': 'tree,form',
            'domain': [('event_id', '=', self.id), ('is_member', '=', False)],
            'context': {'default_event_id': self.id},
        }


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    # Membership Information
    is_member = fields.Boolean(
        string='Is Member',
        compute='_compute_membership_info',
        store=True,
        help="True if the attendee is a current member"
    )
    membership_level_id = fields.Many2one(
        'membership.level',
        string='Membership Level',
        compute='_compute_membership_info',
        store=True,
        help="Current membership level of the attendee"
    )
    chapter_id = fields.Many2one(
        'membership.chapter',
        string='Chapter',
        compute='_compute_membership_info',
        store=True,
        help="Chapter of the attendee"
    )
    
    # Pricing Information
    base_price = fields.Float(
        string='Base Price',
        help="Base price before any discounts"
    )
    member_discount = fields.Float(
        string='Member Discount',
        help="Discount amount for being a member"
    )
    level_discount = fields.Float(
        string='Level Discount',
        help="Additional discount based on membership level"
    )
    final_price = fields.Float(
        string='Final Price',
        compute='_compute_final_price',
        store=True,
        help="Final price after all discounts"
    )
    
    # Early Bird
    is_early_bird = fields.Boolean(
        string='Early Bird',
        compute='_compute_early_bird',
        store=True,
        help="True if registered during early bird period"
    )

    @api.depends('partner_id.is_member', 'partner_id.current_membership_id', 'partner_id.chapter_id')
    def _compute_membership_info(self):
        for registration in self:
            if registration.partner_id:
                registration.is_member = registration.partner_id.is_member
                if registration.partner_id.current_membership_id:
                    registration.membership_level_id = registration.partner_id.current_membership_id.level_id
                    registration.chapter_id = registration.partner_id.current_membership_id.chapter_id
                else:
                    registration.membership_level_id = False
                    registration.chapter_id = registration.partner_id.chapter_id
            else:
                registration.is_member = False
                registration.membership_level_id = False
                registration.chapter_id = False

    @api.depends('event_id.use_early_bird', 'event_id.early_bird_deadline', 'create_date')
    def _compute_early_bird(self):
        for registration in self:
            if (registration.event_id.use_early_bird and 
                registration.event_id.early_bird_deadline and 
                registration.create_date):
                registration.is_early_bird = registration.create_date <= registration.event_id.early_bird_deadline
            else:
                registration.is_early_bird = False

    @api.depends('base_price', 'member_discount', 'level_discount')
    def _compute_final_price(self):
        for registration in self:
            registration.final_price = registration.base_price - registration.member_discount - registration.level_discount

    @api.model_create_multi
    def create(self, vals_list):
        registrations = super().create(vals_list)
        for registration in registrations:
            registration._update_pricing()
        return registrations

    def write(self, vals):
        result = super().write(vals)
        if 'partner_id' in vals:
            self._update_pricing()
        return result

    def _update_pricing(self):
        """Update pricing based on membership status and event settings"""
        for registration in self:
            if not registration.event_id.use_member_pricing:
                continue
                
            # Get base price
            if registration.is_early_bird:
                base_price = (registration.event_id.early_bird_member_price if registration.is_member 
                             else registration.event_id.early_bird_non_member_price)
            else:
                base_price = (registration.event_id.member_price if registration.is_member 
                             else registration.event_id.non_member_price)
            
            # Calculate member discount
            member_discount = 0
            if registration.is_member:
                if registration.is_early_bird:
                    member_discount = registration.event_id.early_bird_non_member_price - registration.event_id.early_bird_member_price
                else:
                    member_discount = registration.event_id.non_member_price - registration.event_id.member_price
                member_discount = max(0, member_discount)
            
            # Calculate level discount
            level_discount = 0
            if registration.membership_level_id and registration.membership_level_id.event_discount_percent > 0:
                level_discount = base_price * (registration.membership_level_id.event_discount_percent / 100)
            
            # Update pricing fields
            registration.write({
                'base_price': base_price,
                'member_discount': member_discount,
                'level_discount': level_discount,
            })

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Update pricing when partner changes"""
        super()._onchange_partner_id()
        if self.partner_id and self.event_id:
            self._update_pricing()


class EventTicket(models.Model):
    _inherit = 'event.event.ticket'

    # Member Pricing for Tickets
    use_member_pricing = fields.Boolean(
        string='Use Member Pricing',
        default=False,
        help="Enable different pricing for members vs non-members for this ticket"
    )
    member_price = fields.Float(
        string='Member Price',
        default=0.0,
        help="Price for members"
    )
    
    def get_ticket_price_for_partner(self, partner_id=None):
        """Get the appropriate ticket price for a specific partner"""
        self.ensure_one()
        
        if not self.use_member_pricing:
            return self.price
        
        # Determine if partner is a member
        is_member = False
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            is_member = partner.is_member
        
        return self.member_price if is_member else self.price


class ResPartner(models.Model):
    _inherit = 'res.partner'

    event_registration_ids = fields.One2many(
        'event.registration',
        'partner_id',
        string='Event Registrations'
    )
    events_attended_count = fields.Integer(
        string='Events Attended',
        compute='_compute_event_statistics',
        help="Number of events attended"
    )
    total_event_spending = fields.Monetary(
        string='Total Event Spending',
        compute='_compute_event_statistics',
        currency_field='currency_id',
        help="Total amount spent on events"
    )

    @api.depends('event_registration_ids.state', 'event_registration_ids.final_price')
    def _compute_event_statistics(self):
        for partner in self:
            attended_registrations = partner.event_registration_ids.filtered(
                lambda r: r.state in ['open', 'done']
            )
            partner.events_attended_count = len(attended_registrations)
            partner.total_event_spending = sum(attended_registrations.mapped('final_price'))