from odoo import models, fields, api, _
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Member Information
    is_member = fields.Boolean(
        string='Is Member',
        compute='_compute_member_status',
        store=True,
        help="Check if this contact is currently a member"
    )
    
    member_since = fields.Date(
        string='Member Since',
        compute='_compute_member_since',
        store=True,
        help="Date when this person first became a member"
    )
    
    membership_number = fields.Char(
        string='Membership Number',
        copy=False,
        help="Unique membership identification number"
    )
    
    member_status = fields.Selection([
        ('not_member', 'Not a Member'),
        ('active', 'Active Member'),
        ('pending_approval', 'Pending Approval'),
        ('pending_renewal', 'Pending Renewal'),
        ('expired', 'Expired'),
        ('lapsed', 'Lapsed'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended')
    ], string='Membership Status', compute='_compute_member_status', store=True)
    
    # Current Membership Information
    current_subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Current Subscription',
        compute='_compute_current_subscription',
        store=True,
        help="Current active subscription"
    )
    
    current_membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Current Membership Type',
        related='current_subscription_id.membership_type_id',
        store=True
    )
    
    current_chapter_id = fields.Many2one(
        'ams.chapter',
        string='Current Chapter',
        related='current_subscription_id.chapter_id',
        store=True
    )
    
    membership_expiry_date = fields.Date(
        string='Membership Expiry',
        related='current_subscription_id.end_date',
        store=True
    )
    
    # All Subscriptions
    subscription_ids = fields.One2many(
        'ams.member.subscription',
        'partner_id',
        string='Subscriptions',
        help="All subscriptions for this member"
    )
    
    subscription_count = fields.Integer(
        string='Subscription Count',
        compute='_compute_subscription_count'
    )
    
    # Member Categories and Classifications
    member_type = fields.Selection([
        ('individual', 'Individual'),
        ('student', 'Student'),
        ('corporate', 'Corporate'),
        ('honorary', 'Honorary'),
        ('emeritus', 'Emeritus'),
        ('affiliate', 'Affiliate')
    ], string='Member Type', help="Primary member classification")
    
    member_category_ids = fields.Many2many(
        'ams.member.category',
        string='Member Categories',
        help="Additional member categories"
    )
    
    # Professional Information
    professional_title = fields.Char(
        string='Professional Title',
        help="Professional title or designation"
    )
    
    license_number = fields.Char(
        string='License Number',
        help="Professional license number if applicable"
    )
    
    license_state = fields.Char(
        string='License State/Province',
        help="State or province where license is issued"
    )
    
    license_expiry_date = fields.Date(
        string='License Expiry Date'
    )
    
    specialty_areas = fields.Text(
        string='Specialty Areas',
        help="Areas of professional specialty or expertise"
    )
    
    # Education Information
    education_level = fields.Selection([
        ('high_school', 'High School'),
        ('associate', 'Associate Degree'),
        ('bachelor', 'Bachelor Degree'),
        ('master', 'Master Degree'),
        ('doctorate', 'Doctorate'),
        ('other', 'Other')
    ], string='Education Level')
    
    alma_mater = fields.Char(
        string='Alma Mater',
        help="Primary educational institution"
    )
    
    graduation_year = fields.Integer(
        string='Graduation Year'
    )
    
    # Employment Information
    employer = fields.Char(
        string='Employer',
        help="Current employer"
    )
    
    job_title = fields.Char(
        string='Job Title',
        help="Current job title"
    )
    
    work_address = fields.Text(
        string='Work Address'
    )
    
    work_phone = fields.Char(
        string='Work Phone'
    )
    
    work_email = fields.Char(
        string='Work Email'
    )
    
    # Communication Preferences
    newsletter_subscription = fields.Boolean(
        string='Newsletter Subscription',
        default=True,
        help="Subscribe to association newsletter"
    )
    
    event_notifications = fields.Boolean(
        string='Event Notifications',
        default=True,
        help="Receive notifications about upcoming events"
    )
    
    communication_preference = fields.Selection([
        ('email', 'Email'),
        ('mail', 'Regular Mail'),
        ('phone', 'Phone'),
        ('sms', 'SMS'),
        ('none', 'No Communication')
    ], string='Preferred Communication', default='email')
    
    # Emergency Contact
    emergency_contact_name = fields.Char(
        string='Emergency Contact Name'
    )
    
    emergency_contact_phone = fields.Char(
        string='Emergency Contact Phone'
    )
    
    emergency_contact_relationship = fields.Char(
        string='Relationship to Emergency Contact'
    )
    
    # Financial Information
    total_membership_revenue = fields.Float(
        string='Total Membership Revenue',
        compute='_compute_financial_totals',
        store=True,
        help="Total revenue from all memberships"
    )
    
    outstanding_balance = fields.Float(
        string='Outstanding Balance',
        compute='_compute_financial_totals',
        store=True,
        help="Outstanding membership fees"
    )
    
    # Member Portal Access
    portal_access_granted = fields.Boolean(
        string='Portal Access Granted',
        default=False,
        help="Grant access to member portal"
    )
    
    last_portal_login = fields.Datetime(
        string='Last Portal Login',
        help="Last time member logged into portal"
    )
    
    # Notes and Comments
    membership_notes = fields.Html(
        string='Membership Notes',
        help="Internal notes about this member"
    )
    
    public_notes = fields.Html(
        string='Public Notes',
        help="Notes visible to the member"
    )

    @api.depends('subscription_ids.state')
    def _compute_member_status(self):
        for partner in self:
            active_subscription = partner.subscription_ids.filtered(
                lambda s: s.state in ['active', 'pending_renewal']
            )
            
            if active_subscription:
                partner.is_member = True
                # Get the most recent active subscription's state
                partner.member_status = active_subscription.sorted('start_date', reverse=True)[0].state
            else:
                partner.is_member = False
                # Check if there are any other subscriptions
                recent_subscription = partner.subscription_ids.sorted('start_date', reverse=True)[:1]
                if recent_subscription:
                    partner.member_status = recent_subscription.state
                else:
                    partner.member_status = 'not_member'

    @api.depends('subscription_ids.start_date')
    def _compute_member_since(self):
        for partner in self:
            first_subscription = partner.subscription_ids.filtered(
                lambda s: s.state != 'cancelled'
            ).sorted('start_date')
            
            if first_subscription:
                partner.member_since = first_subscription[0].start_date
            else:
                partner.member_since = False

    @api.depends('subscription_ids.state', 'subscription_ids.end_date')
    def _compute_current_subscription(self):
        for partner in self:
            # Find active subscription with latest start date
            active_subscriptions = partner.subscription_ids.filtered(
                lambda s: s.state in ['active', 'pending_renewal']
            ).sorted('start_date', reverse=True)
            
            if active_subscriptions:
                partner.current_subscription_id = active_subscriptions[0]
            else:
                partner.current_subscription_id = False

    @api.depends('subscription_ids')
    def _compute_subscription_count(self):
        for partner in self:
            partner.subscription_count = len(partner.subscription_ids)

    @api.depends('subscription_ids.total_amount', 'subscription_ids.payment_status')
    def _compute_financial_totals(self):
        for partner in self:
            total_revenue = sum(partner.subscription_ids.mapped('total_amount'))
            partner.total_membership_revenue = total_revenue
            
            # Calculate outstanding balance (unpaid and partially paid subscriptions)
            outstanding = sum(
                partner.subscription_ids.filtered(
                    lambda s: s.payment_status in ['unpaid', 'partial']
                ).mapped('total_amount')
            )
            partner.outstanding_balance = outstanding

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        
        for partner in partners:
            # Auto-generate membership number if this becomes a member
            if partner.is_member and not partner.membership_number:
                partner._generate_membership_number()
        
        return partners

    def write(self, vals):
        result = super().write(vals)
        
        # Auto-generate membership number when someone becomes a member
        for partner in self:
            if partner.is_member and not partner.membership_number:
                partner._generate_membership_number()
        
        return result

    def _generate_membership_number(self):
        """Generate a unique membership number"""
        self.ensure_one()
        
        if self.membership_number:
            return
        
        # Try to get sequence, create if it doesn't exist
        sequence = self.env['ir.sequence'].search([
            ('code', '=', 'ams.membership.number')
        ], limit=1)
        
        if not sequence:
            sequence = self.env['ir.sequence'].create({
                'name': 'Membership Number',
                'code': 'ams.membership.number',
                'prefix': 'MEM-',
                'padding': 6,
                'number_increment': 1,
            })
        
        self.membership_number = sequence.next_by_id()

    def action_view_subscriptions(self):
        """View all subscriptions for this member"""
        self.ensure_one()
        
        action = self.env["ir.actions.actions"]._for_xml_id("ams_subscriptions.action_member_subscription")
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {
            'default_partner_id': self.id,
            'search_default_partner_id': self.id,
        }
        
        return action

    def action_create_subscription(self):
        """Create a new subscription for this member"""
        self.ensure_one()
        
        return {
            'name': _('New Subscription'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.member.subscription',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_partner_id': self.id,
            }
        }

    def action_renew_membership(self):
        """Renew current membership"""
        self.ensure_one()
        
        if not self.current_subscription_id:
            raise UserError(_("No active subscription found to renew."))
        
        return self.current_subscription_id.action_renew()

    def action_grant_portal_access(self):
        """Grant portal access to this member"""
        self.ensure_one()
        
        if not self.user_ids:
            # Create portal user
            user_vals = {
                'name': self.name,
                'login': self.email,
                'email': self.email,
                'partner_id': self.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
            }
            
            user = self.env['res.users'].create(user_vals)
            
        self.portal_access_granted = True
        
        # Send portal access email
        template = self.env.ref('ams_subscriptions.email_template_portal_access', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def action_revoke_portal_access(self):
        """Revoke portal access for this member"""
        self.ensure_one()
        
        if self.user_ids:
            self.user_ids.write({'active': False})
        
        self.portal_access_granted = False

    @api.model
    def search_members(self, search_term, limit=10):
        """Search members by name, membership number, or email"""
        domain = [
            ('is_member', '=', True),
            '|', '|', 
            ('name', 'ilike', search_term),
            ('membership_number', 'ilike', search_term),
            ('email', 'ilike', search_term)
        ]
        
        return self.search(domain, limit=limit)

    def get_membership_history(self):
        """Get membership history for this partner"""
        self.ensure_one()
        
        return self.subscription_ids.sorted('start_date', reverse=True)

    def check_membership_eligibility(self, membership_type_id):
        """Check if member is eligible for a specific membership type"""
        self.ensure_one()
        
        membership_type = self.env['ams.membership.type'].browse(membership_type_id)
        
        # Basic checks - can be extended
        if membership_type.member_category == 'student' and self.education_level not in ['high_school', 'associate', 'bachelor']:
            return False, _("Student membership requires appropriate education level")
        
        if membership_type.max_members > 0:
            current_count = membership_type.current_member_count
            if current_count >= membership_type.max_members:
                return False, _("Membership type has reached maximum capacity")
        
        return True, _("Eligible for membership")

    def get_chapter_eligibility(self):
        """Get list of chapters this member is eligible for"""
        self.ensure_one()
        
        # Basic implementation - can be extended based on location, etc.
        return self.env['ams.chapter'].search([('active', '=', True)])

    @api.model
    def get_member_statistics(self):
        """Get member statistics for dashboard"""
        total_members = self.search_count([('is_member', '=', True)])
        active_members = self.search_count([('member_status', '=', 'active')])
        new_this_month = self.search_count([
            ('member_since', '>=', date.today().replace(day=1)),
            ('is_member', '=', True)
        ])
        
        return {
            'total_members': total_members,
            'active_members': active_members,
            'new_this_month': new_this_month,
            'renewal_rate': (active_members / total_members * 100) if total_members > 0 else 0
        }


class AMSMemberCategory(models.Model):
    _name = 'ams.member.category'
    _description = 'Member Category'
    _order = 'sequence, name'

    name = fields.Char(
        string='Category Name',
        required=True
    )
    
    code = fields.Char(
        string='Code',
        required=True
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    description = fields.Text(
        string='Description'
    )
    
    color = fields.Integer(
        string='Color Index',
        help="Color for display in kanban and other views"
    )

    @api.constrains('code')
    def _check_unique_code(self):
        for record in self:
            if self.search_count([
                ('code', '=', record.code),
                ('id', '!=', record.id)
            ]) > 0:
                raise ValidationError(_("Member category code must be unique!"))
                
class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    def get_portal_dashboard_data(self):
        """Get member portal dashboard data"""
        self.ensure_one()
        
        current_subscription = self.current_subscription_id
        
        # Upcoming renewals
        renewal_date = None
        days_until_renewal = None
        if current_subscription and current_subscription.end_date:
            renewal_date = current_subscription.end_date
            days_until_renewal = (renewal_date - fields.Date.today()).days
        
        # Recent activity
        recent_invoices = self.env['account.move'].search([
            ('partner_id', '=', self.id),
            ('is_membership_invoice', '=', True),
            ('state', '=', 'posted')
        ], order='invoice_date desc', limit=3)
        
        # Benefit usage this month
        month_start = fields.Date.today().replace(day=1)
        monthly_usage = self.env['ams.benefit.usage'].search_count([
            ('member_id', '=', self.id),
            ('usage_date', '>=', month_start)
        ])
        
        return {
            'membership_status': self.member_status,
            'membership_type': current_subscription.membership_type_id.name if current_subscription else None,
            'chapter': current_subscription.chapter_id.name if current_subscription and current_subscription.chapter_id else None,
            'renewal_date': renewal_date,
            'days_until_renewal': days_until_renewal,
            'recent_invoices': recent_invoices,
            'monthly_benefit_usage': monthly_usage,
            'auto_renew_enabled': current_subscription.auto_renew if current_subscription else False,
            'outstanding_balance': self.outstanding_balance
        }