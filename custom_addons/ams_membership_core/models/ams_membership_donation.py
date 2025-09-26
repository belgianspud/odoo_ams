# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AMSMembershipDonation(models.Model):
    _name = 'ams.membership.donation'
    _description = 'Recurring Donation Programs'
    _inherit = 'ams.membership.base'
    _rec_name = 'name'

    # Donation Classification
    donation_type = fields.Selection([
        ('general', 'General Fund'),
        ('scholarship', 'Scholarship Fund'),
        ('research', 'Research Fund'),
        ('building', 'Building Fund'),
        ('endowment', 'Endowment'),
        ('emergency', 'Emergency Relief'),
        ('education', 'Education Programs'),
        ('community', 'Community Outreach'),
        ('advocacy', 'Advocacy & Policy'),
        ('technology', 'Technology Development'),
        ('awards', 'Awards & Recognition'),
        ('events', 'Events & Conferences'),
        ('memorial', 'Memorial Fund'),
        ('special_project', 'Special Project')
    ], string='Donation Type', default='general', required=True)
    
    # Donation Amount and Frequency
    donation_amount = fields.Float('Donation Amount', required=True)
    total_donated = fields.Float('Total Donated', readonly=True, default=0.0)
    payments_made = fields.Integer('Payments Made', readonly=True, default=0)
    
    # Recognition and Acknowledgment
    donor_recognition_level = fields.Selection([
        ('anonymous', 'Anonymous'),
        ('name_only', 'Name Only'),
        ('full_recognition', 'Full Recognition'),
        ('major_donor', 'Major Donor'),
        ('legacy_circle', 'Legacy Circle'),
        ('founders_circle', 'Founders Circle')
    ], string='Recognition Level', default='full_recognition')
    
    public_recognition = fields.Boolean('Public Recognition', default=True,
                                      help="Allow public acknowledgment of donation")
    recognition_name = fields.Char('Recognition Name',
                                 help="Name to use for recognition (if different from donor name)")
    
    # Donation Preferences
    donation_designation = fields.Text('Donation Designation',
                                     help="Specific purpose or restrictions for the donation")
    tax_deductible = fields.Boolean('Tax Deductible', default=True)
    receipt_required = fields.Boolean('Receipt Required', default=True)
    receipt_delivery = fields.Selection([
        ('email', 'Email'),
        ('mail', 'Physical Mail'),
        ('both', 'Email and Mail')
    ], string='Receipt Delivery', default='email')
    
    # Gift Information
    gift_type = fields.Selection([
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('securities', 'Securities'),
        ('property', 'Property'),
        ('in_kind', 'In-Kind'),
        ('pledge', 'Pledge'),
        ('bequest', 'Bequest')
    ], string='Gift Type', default='credit_card')
    
    # Memorial and Tribute Donations
    is_memorial_gift = fields.Boolean('Memorial Gift')
    is_tribute_gift = fields.Boolean('Tribute Gift')
    memorial_honoree = fields.Char('In Memory Of')
    tribute_honoree = fields.Char('In Honor Of')
    notification_contact = fields.Many2one('res.partner', 'Notification Contact',
                                         help="Person to notify about memorial/tribute gift")
    
    # Matching Gifts
    employer_matching = fields.Boolean('Employer Matching Available')
    matching_gift_employer = fields.Many2one('res.partner', 'Matching Gift Employer',
                                           domain=[('is_company', '=', True)])
    matching_gift_submitted = fields.Boolean('Matching Gift Submitted')
    expected_matching_amount = fields.Float('Expected Matching Amount')
    
    # Donor Communication
    communication_preferences = fields.Selection([
        ('minimal', 'Minimal Contact'),
        ('updates_only', 'Program Updates Only'),
        ('regular', 'Regular Communications'),
        ('newsletter', 'Newsletter and Updates'),
        ('all', 'All Communications')
    ], string='Communication Preferences', default='regular')
    
    thank_you_sent = fields.Boolean('Thank You Sent', readonly=True)
    thank_you_date = fields.Date('Thank You Date', readonly=True)
    impact_report_sent = fields.Boolean('Impact Report Sent', readonly=True)
    
    # Stewardship and Relationship
    donor_relations_contact = fields.Many2one('res.users', 'Donor Relations Contact')
    stewardship_level = fields.Selection([
        ('standard', 'Standard'),
        ('enhanced', 'Enhanced'),
        ('premium', 'Premium'),
        ('vip', 'VIP')
    ], string='Stewardship Level', default='standard')
    
    # Special Programs and Benefits
    giving_circle_member = fields.Boolean('Giving Circle Member')
    board_invited = fields.Boolean('Board Meeting Invited')
    special_events_invited = fields.Boolean('Special Events Invited')
    behind_scenes_access = fields.Boolean('Behind the Scenes Access')
    
    # Pledge Information
    pledge_amount = fields.Float('Pledge Amount')
    pledge_fulfilled = fields.Float('Pledge Fulfilled', readonly=True)
    pledge_balance = fields.Float('Pledge Balance', compute='_compute_pledge_balance', store=True)
    pledge_end_date = fields.Date('Pledge End Date')
    
    # Campaign Information
    campaign_id = fields.Many2one('ams.donation.campaign', 'Campaign')
    solicitation_method = fields.Selection([
        ('direct_mail', 'Direct Mail'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('in_person', 'In Person'),
        ('event', 'Event'),
        ('online', 'Online'),
        ('peer_to_peer', 'Peer to Peer'),
        ('social_media', 'Social Media')
    ], string='Solicitation Method')
    
    # Impact and Reporting
    impact_category = fields.Selection([
        ('students_served', 'Students Served'),
        ('research_funded', 'Research Funded'),
        ('programs_supported', 'Programs Supported'),
        ('facilities_improved', 'Facilities Improved'),
        ('scholarships_awarded', 'Scholarships Awarded'),
        ('equipment_purchased', 'Equipment Purchased'),
        ('community_impact', 'Community Impact')
    ], string='Impact Category')
    
    impact_metrics = fields.Text('Impact Metrics')
    success_stories = fields.Text('Success Stories')

    @api.depends('pledge_amount', 'pledge_fulfilled')
    def _compute_pledge_balance(self):
        """Compute remaining pledge balance"""
        for donation in self:
            donation.pledge_balance = donation.pledge_amount - donation.pledge_fulfilled

    @api.onchange('donation_type')
    def _onchange_donation_type(self):
        """Set defaults based on donation type"""
        if self.donation_type == 'scholarship':
            self.impact_category = 'scholarships_awarded'
            self.stewardship_level = 'enhanced'
        elif self.donation_type == 'endowment':
            self.stewardship_level = 'premium'
            self.donor_recognition_level = 'major_donor'
        elif self.donation_type == 'memorial':
            self.is_memorial_gift = True
            self.communication_preferences = 'minimal'
        elif self.donation_type == 'research':
            self.impact_category = 'research_funded'

    @api.onchange('donor_recognition_level')
    def _onchange_recognition_level(self):
        """Set stewardship level based on recognition level"""
        if self.donor_recognition_level in ['major_donor', 'legacy_circle', 'founders_circle']:
            self.stewardship_level = 'vip'
            self.special_events_invited = True
            self.behind_scenes_access = True
        elif self.donor_recognition_level == 'full_recognition':
            self.stewardship_level = 'enhanced'

    @api.onchange('is_memorial_gift', 'is_tribute_gift')
    def _onchange_memorial_tribute(self):
        """Clear conflicting memorial/tribute settings"""
        if self.is_memorial_gift:
            self.is_tribute_gift = False
        elif self.is_tribute_gift:
            self.is_memorial_gift = False

    # Action Methods
    def action_send_thank_you(self):
        """Send thank you acknowledgment"""
        self.ensure_one()
        
        if self.thank_you_sent:
            raise UserError(_("Thank you has already been sent."))
        
        # This would integrate with email/mail system
        self.write({
            'thank_you_sent': True,
            'thank_you_date': fields.Date.today()
        })
        
        self.message_post(
            body=_("Thank you acknowledgment sent to %s") % self.partner_id.name,
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thank You Sent'),
                'message': _('Thank you acknowledgment has been sent to the donor.'),
                'type': 'success'
            }
        }

    def action_generate_receipt(self):
        """Generate donation receipt"""
        self.ensure_one()
        
        if not self.tax_deductible:
            raise UserError(_("Receipts are only available for tax-deductible donations."))
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'ams_membership_core.donation_receipt_report',
            'report_type': 'qweb-pdf',
            'data': {'donation_id': self.id},
            'context': {'active_id': self.id},
        }

    def action_send_impact_report(self):
        """Send impact report to donor"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Impact Report'),
            'res_model': 'ams.donation.impact.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_donation_id': self.id,
            }
        }

    def action_record_pledge_payment(self):
        """Record a pledge payment"""
        self.ensure_one()
        
        if self.pledge_amount <= 0:
            raise UserError(_("No pledge amount set for this donation."))
        
        if self.pledge_balance <= 0:
            raise UserError(_("Pledge has been fully paid."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Record Pledge Payment'),
            'res_model': 'ams.pledge.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_donation_id': self.id,
                'default_remaining_balance': self.pledge_balance,
            }
        }

    def action_update_stewardship(self):
        """Update donor stewardship information"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Stewardship'),
            'res_model': 'ams.donor.stewardship.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_donation_id': self.id,
            }
        }

    def action_submit_matching_gift(self):
        """Submit matching gift request"""
        self.ensure_one()
        
        if not self.employer_matching:
            raise UserError(_("Employer matching is not available for this donation."))
        
        if self.matching_gift_submitted:
            raise UserError(_("Matching gift has already been submitted."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Submit Matching Gift'),
            'res_model': 'ams.matching.gift.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_donation_id': self.id,
            }
        }

    def action_donor_profile(self):
        """View comprehensive donor profile"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Donor Profile: %s') % self.partner_id.name,
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
            'context': {
                'show_donor_info': True,
            }
        }

    def action_donation_history(self):
        """View donation history for this donor"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Donation History: %s') % self.partner_id.name,
            'res_model': 'ams.membership.donation',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {'search_default_group_by_year': 1},
        }

    # Donation Management Methods
    def record_payment(self, amount, payment_date=None):
        """Record a donation payment"""
        self.ensure_one()
        
        if amount <= 0:
            raise UserError(_("Payment amount must be positive."))
        
        if not payment_date:
            payment_date = fields.Date.today()
        
        # Update totals
        self.write({
            'total_donated': self.total_donated + amount,
            'payments_made': self.payments_made + 1
        })
        
        # Update pledge if applicable
        if self.pledge_amount > 0:
            self.pledge_fulfilled += amount
        
        # Log payment
        self.message_post(
            body=_("Payment recorded: $%.2f on %s") % (amount, payment_date),
            message_type='notification'
        )
        
        # Send automatic thank you if configured
        if not self.thank_you_sent and self.receipt_required:
            self.action_send_thank_you()

    def update_recognition_level(self):
        """Update recognition level based on total donations"""
        self.ensure_one()
        
        # Define recognition thresholds (these would be configurable)
        if self.total_donated >= 100000:
            new_level = 'founders_circle'
        elif self.total_donated >= 50000:
            new_level = 'legacy_circle'
        elif self.total_donated >= 10000:
            new_level = 'major_donor'
        elif self.total_donated >= 1000:
            new_level = 'full_recognition'
        else:
            new_level = 'name_only'
        
        if new_level != self.donor_recognition_level:
            old_level = self.donor_recognition_level
            self.donor_recognition_level = new_level
            
            # Log recognition level change
            self.message_post(
                body=_("Recognition level updated from %s to %s") % (
                    dict(self._fields['donor_recognition_level'].selection)[old_level],
                    dict(self._fields['donor_recognition_level'].selection)[new_level]
                ),
                message_type='notification'
            )

    def calculate_annual_giving(self, year=None):
        """Calculate total giving for a specific year"""
        self.ensure_one()
        
        if not year:
            year = fields.Date.today().year
        
        # This is a simplified calculation - in practice would sum invoice amounts
        return self.donation_amount * self.payments_made

    def get_donor_benefits(self):
        """Get list of donor benefits"""
        self.ensure_one()
        benefits = []
        
        if self.tax_deductible:
            benefits.append(_("Tax Deductible"))
        
        if self.receipt_required:
            benefits.append(_("Tax Receipt Provided"))
        
        if self.public_recognition:
            level_name = dict(self._fields['donor_recognition_level'].selection)[self.donor_recognition_level]
            benefits.append(_("Public Recognition: %s") % level_name)
        
        if self.giving_circle_member:
            benefits.append(_("Giving Circle Membership"))
        
        if self.special_events_invited:
            benefits.append(_("Special Events Invitation"))
        
        if self.behind_scenes_access:
            benefits.append(_("Behind the Scenes Access"))
        
        if self.board_invited:
            benefits.append(_("Board Meeting Invitation"))
        
        # Stewardship level benefits
        if self.stewardship_level == 'vip':
            benefits.extend([
                _("VIP Stewardship Level"),
                _("Personal Donor Relations Contact"),
                _("Exclusive Updates and Reports")
            ])
        
        return benefits

    def get_impact_summary(self):
        """Get impact summary for this donation"""
        self.ensure_one()
        
        impact = {
            'type': dict(self._fields['donation_type'].selection)[self.donation_type],
            'total_donated': self.total_donated,
            'payments_made': self.payments_made,
            'recognition_level': dict(self._fields['donor_recognition_level'].selection)[self.donor_recognition_level],
        }
        
        if self.impact_category:
            impact['category'] = dict(self._fields['impact_category'].selection)[self.impact_category]
        
        if self.impact_metrics:
            impact['metrics'] = self.impact_metrics
        
        return impact

    # Automated Processing
    @api.model
    def process_pledge_reminders(self):
        """Send reminders for outstanding pledges"""
        _logger.info("Starting pledge reminder processing...")
        
        try:
            # Find pledges with outstanding balances
            outstanding_pledges = self.search([
                ('pledge_amount', '>', 0),
                ('pledge_balance', '>', 0),
                ('state', 'in', ['active', 'grace'])
            ])
            
            reminder_count = 0
            for pledge in outstanding_pledges:
                # Check if reminder is due (simplified logic)
                if pledge.pledge_end_date:
                    days_until_due = (pledge.pledge_end_date - fields.Date.today()).days
                    if days_until_due in [30, 14, 7]:  # Send reminders at these intervals
                        # Send reminder (would integrate with email system)
                        pledge.message_post(
                            body=_("Pledge reminder sent - %d days until due date") % days_until_due,
                            message_type='notification'
                        )
                        reminder_count += 1
            
            _logger.info(f"Sent {reminder_count} pledge reminders")
            
        except Exception as e:
            _logger.error(f"Error in pledge reminder processing: {str(e)}")

    @api.model
    def update_donor_recognition_levels(self):
        """Update all donor recognition levels based on giving totals"""
        _logger.info("Starting donor recognition level updates...")
        
        try:
            active_donations = self.search([('state', 'in', ['active', 'grace'])])
            
            updated_count = 0
            for donation in active_donations:
                old_level = donation.donor_recognition_level
                donation.update_recognition_level()
                if donation.donor_recognition_level != old_level:
                    updated_count += 1
            
            _logger.info(f"Updated {updated_count} donor recognition levels")
            
        except Exception as e:
            _logger.error(f"Error in recognition level updates: {str(e)}")

    # Constraints
    @api.constrains('product_id')
    def _check_product_class(self):
        """Ensure product is a donation product"""
        for donation in self:
            if donation.product_id.product_tmpl_id.product_class != 'donations':
                raise ValidationError(_("Product must be a donations product class."))

    @api.constrains('donation_amount')
    def _check_donation_amount(self):
        """Validate donation amount"""
        for donation in self:
            if donation.donation_amount <= 0:
                raise ValidationError(_("Donation amount must be positive."))

    @api.constrains('pledge_amount', 'pledge_fulfilled')
    def _check_pledge_amounts(self):
        """Validate pledge amounts"""
        for donation in self:
            if donation.pledge_amount < 0:
                raise ValidationError(_("Pledge amount cannot be negative."))
            if donation.pledge_fulfilled < 0:
                raise ValidationError(_("Pledge fulfilled cannot be negative."))
            if donation.pledge_fulfilled > donation.pledge_amount:
                raise ValidationError(_("Pledge fulfilled cannot exceed pledge amount."))

    @api.constrains('total_donated', 'payments_made')
    def _check_totals(self):
        """Validate totals"""
        for donation in self:
            if donation.total_donated < 0:
                raise ValidationError(_("Total donated cannot be negative."))
            if donation.payments_made < 0:
                raise ValidationError(_("Payments made cannot be negative."))

    @api.constrains('expected_matching_amount')
    def _check_matching_amount(self):
        """Validate matching amount"""
        for donation in self:
            if donation.expected_matching_amount < 0:
                raise ValidationError(_("Expected matching amount cannot be negative."))

    @api.constrains('is_memorial_gift', 'is_tribute_gift')
    def _check_memorial_tribute_exclusive(self):
        """Ensure memorial and tribute are mutually exclusive"""
        for donation in self:
            if donation.is_memorial_gift and donation.is_tribute_gift:
                raise ValidationError(_("Donation cannot be both memorial and tribute gift."))

    @api.constrains('pledge_end_date')
    def _check_pledge_end_date(self):
        """Validate pledge end date"""
        for donation in self:
            if donation.pledge_amount > 0 and donation.pledge_end_date:
                if donation.pledge_end_date <= fields.Date.today():
                    raise ValidationError(_("Pledge end date must be in the future."))

    def copy(self, default=None):
        """Override copy to handle unique fields"""
        if default is None:
            default = {}
        default.update({
            'total_donated': 0.0,
            'payments_made': 0,
            'pledge_fulfilled': 0.0,
            'thank_you_sent': False,
            'thank_you_date': False,
            'impact_report_sent': False,
            'matching_gift_submitted': False,
        })
        return super().copy(default)