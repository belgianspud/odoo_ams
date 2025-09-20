# -*- coding: utf-8 -*-
# Part of Association Management Software (AMS)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class MembershipType(models.Model):
    _name = 'membership.type'
    _description = 'Membership Type Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    _rec_name = 'name'
    
    # SQL constraints for data integrity
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Membership type code must be unique'),
        ('positive_duration', 'check(duration >= 0)', 'Duration must be positive or zero for lifetime'),
        ('positive_price', 'check(price >= 0)', 'Price must be positive or zero'),
    ]
    
    # Core identification fields
    name = fields.Char(
        string='Membership Type Name',
        required=True,
        size=100,
        help='Display name for membership type',
        tracking=True,
        translate=True
    )
    
    code = fields.Char(
        string='Unique Code',
        required=True,
        size=20,
        help='Internal reference code for integration and reporting',
        tracking=True
    )
    
    sequence = fields.Integer(
        string='Display Order',
        default=10,
        help='Order for displaying in lists and selection menus'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to archive this membership type',
        tracking=True
    )
    
    # Business categorization
    membership_category = fields.Selection([
        ('individual', 'Individual Membership'),
        ('organization', 'Organization Membership'),
        ('chapter', 'Chapter Membership'),
        ('publication', 'Publication Subscription'),
        ('certification', 'Certification'),
        ('other', 'Other')
    ], string='Membership Category',
       required=True,
       default='individual',
       help='Determines business rules and validation logic',
       tracking=True)
    
    description = fields.Html(
        string='Description',
        help='Detailed description of membership type and benefits',
        translate=True
    )
    
    # Pricing configuration
    price = fields.Float(
        string='Membership Fee',
        digits='Product Price',
        default=0.0,
        help='Base membership fee in company currency',
        tracking=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    # Duration and lifecycle management
    duration = fields.Integer(
        string='Duration (Months)',
        required=True,
        default=12,
        help='Membership duration in months. Set to 0 for lifetime membership',
        tracking=True
    )
    
    is_lifetime = fields.Boolean(
        string='Lifetime Membership',
        compute='_compute_is_lifetime',
        store=True,
        help='Automatically calculated based on duration = 0'
    )
    
    auto_renewal = fields.Boolean(
        string='Auto-Renewal Enabled',
        default=False,
        help='Enable automatic renewal for this membership type',
        tracking=True
    )
    
    # Grace period configuration
    grace_period = fields.Integer(
        string='Grace Period (Days)',
        default=30,
        help='Days after expiration before moving to suspended state',
        tracking=True
    )
    
    suspend_period = fields.Integer(
        string='Suspension Period (Days)',
        default=60,
        help='Days in suspended state before automatic termination'
    )
    
    terminate_period = fields.Integer(
        string='Termination Period (Days)',
        default=30,
        help='Days to keep terminated records before archival'
    )
    
    # Product integration
    creates_membership = fields.Boolean(
        string='Creates Membership Record',
        default=True,
        help='Whether purchasing this product creates a membership record'
    )
    
    # Email template configuration
    welcome_template_id = fields.Many2one(
        'mail.template',
        string='Welcome Email Template',
        domain="[('model', '=', 'membership.membership')]",
        help='Email template sent when membership is activated'
    )
    
    renewal_template_id = fields.Many2one(
        'mail.template',
        string='Renewal Reminder Template',
        domain="[('model', '=', 'membership.membership')]",
        help='Email template for renewal reminders'
    )
    
    expiry_template_id = fields.Many2one(
        'mail.template',
        string='Expiry Notice Template',
        domain="[('model', '=', 'membership.membership')]",
        help='Email template sent when membership expires'
    )
    
    cancellation_template_id = fields.Many2one(
        'mail.template',
        string='Cancellation Template',
        domain="[('model', '=', 'membership.membership')]",
        help='Email template sent when membership is cancelled'
    )
    
    # Computed fields for statistics
    membership_count = fields.Integer(
        string='Active Memberships',
        compute='_compute_membership_count',
        help='Number of active memberships of this type'
    )
    
    total_revenue = fields.Float(
        string='Total Revenue',
        compute='_compute_total_revenue',
        digits='Product Price',
        help='Total revenue from this membership type'
    )
    
    # Relationship to memberships
    membership_ids = fields.One2many(
        'membership.membership',
        'membership_type_id',
        string='Memberships',
        help='All memberships of this type'
    )
    
    # Company field
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    # Computed field implementations
    @api.depends('duration')
    def _compute_is_lifetime(self):
        for record in self:
            record.is_lifetime = record.duration == 0
    
    def _compute_membership_count(self):
        for record in self:
            record.membership_count = self.env['membership.membership'].search_count([
                ('membership_type_id', '=', record.id),
                ('state', 'in', ['active', 'grace'])
            ])
    
    def _compute_total_revenue(self):
        for record in self:
            memberships = self.env['membership.membership'].search([
                ('membership_type_id', '=', record.id)
            ])
            record.total_revenue = sum(memberships.mapped('amount_paid'))
    
    # Validation methods
    @api.constrains('grace_period', 'suspend_period', 'terminate_period')
    def _check_periods(self):
        for record in self:
            if record.grace_period < 0 or record.suspend_period < 0 or record.terminate_period < 0:
                raise ValidationError(_("Periods must be positive numbers"))
    
    @api.constrains('code')
    def _check_code_format(self):
        for record in self:
            if record.code and not record.code.replace('_', '').replace('-', '').isalnum():
                raise ValidationError(_("Code can only contain letters, numbers, hyphens and underscores"))
    
    # Business logic methods
    def action_view_memberships(self):
        """Open list of memberships for this type"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Memberships - %s') % self.name,
            'res_model': 'membership.membership',
            'view_mode': 'tree,form',
            'domain': [('membership_type_id', '=', self.id)],
            'context': {'default_membership_type_id': self.id}
        }
    
    def get_renewal_price(self, membership=None):
        """Calculate renewal price for a membership"""
        # Base implementation - can be extended by other modules
        return self.price
    
    def create_default_email_templates(self):
        """Create default email templates for this membership type"""
        # Implementation for creating basic email templates
        template_vals = []
        
        # Welcome template
        if not self.welcome_template_id:
            welcome_template = {
                'name': f'Welcome - {self.name}',
                'subject': f'Welcome to {self.name}',
                'model_id': self.env.ref('membership_core.model_membership_membership').id,
                'body_html': f'''
                    <p>Dear ${{object.partner_id.name}},</p>
                    <p>Welcome to your new {self.name} membership!</p>
                    <p>Your membership number is: ${{object.name}}</p>
                    <p>Thank you for joining us.</p>
                '''
            }
            template_vals.append(welcome_template)
        
        # Renewal template
        if not self.renewal_template_id:
            renewal_template = {
                'name': f'Renewal Reminder - {self.name}',
                'subject': f'Membership Renewal Reminder - {self.name}',
                'model_id': self.env.ref('membership_core.model_membership_membership').id,
                'body_html': f'''
                    <p>Dear ${{object.partner_id.name}},</p>
                    <p>Your {self.name} membership expires on ${{object.end_date}}.</p>
                    <p>Please renew to continue enjoying your membership benefits.</p>
                    <p>Membership Number: ${{object.name}}</p>
                '''
            }
            template_vals.append(renewal_template)
        
        # Expiry template
        if not self.expiry_template_id:
            expiry_template = {
                'name': f'Expiry Notice - {self.name}',
                'subject': f'Membership Expired - {self.name}',
                'model_id': self.env.ref('membership_core.model_membership_membership').id,
                'body_html': f'''
                    <p>Dear ${{object.partner_id.name}},</p>
                    <p>Your {self.name} membership has expired.</p>
                    <p>You are now in a grace period until ${{object.grace_end_date}}.</p>
                    <p>Please renew to maintain your membership benefits.</p>
                '''
            }
            template_vals.append(expiry_template)
        
        # Cancellation template
        if not self.cancellation_template_id:
            cancellation_template = {
                'name': f'Cancellation - {self.name}',
                'subject': f'Membership Cancelled - {self.name}',
                'model_id': self.env.ref('membership_core.model_membership_membership').id,
                'body_html': f'''
                    <p>Dear ${{object.partner_id.name}},</p>
                    <p>Your {self.name} membership has been cancelled as requested.</p>
                    <p>Thank you for being a member.</p>
                    <p>You are welcome to rejoin at any time.</p>
                '''
            }
            template_vals.append(cancellation_template)
        
        if template_vals:
            created_templates = self.env['mail.template'].create(template_vals)
            if len(created_templates) >= 1 and not self.welcome_template_id:
                self.welcome_template_id = created_templates[0].id
            if len(created_templates) >= 2 and not self.renewal_template_id:
                self.renewal_template_id = created_templates[1].id
            if len(created_templates) >= 3 and not self.expiry_template_id:
                self.expiry_template_id = created_templates[2].id
            if len(created_templates) >= 4 and not self.cancellation_template_id:
                self.cancellation_template_id = created_templates[3].id
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Templates Created'),
                    'message': _('%d email templates created successfully') % len(created_templates),
                    'type': 'success',
                }
            }
    
    def get_membership_statistics(self):
        """Get detailed statistics for this membership type"""
        self.ensure_one()
        
        memberships = self.membership_ids
        
        stats = {
            'total_count': len(memberships),
            'active_count': len(memberships.filtered(lambda m: m.state == 'active')),
            'grace_count': len(memberships.filtered(lambda m: m.state == 'grace')),
            'suspended_count': len(memberships.filtered(lambda m: m.state == 'suspended')),
            'terminated_count': len(memberships.filtered(lambda m: m.state == 'terminated')),
            'cancelled_count': len(memberships.filtered(lambda m: m.state == 'cancelled')),
            'total_revenue': sum(memberships.mapped('amount_paid')),
            'average_revenue': sum(memberships.mapped('amount_paid')) / len(memberships) if memberships else 0,
        }
        
        # Calculate expiring soon (next 30 days)
        from datetime import datetime, timedelta
        thirty_days_from_now = datetime.now().date() + timedelta(days=30)
        
        expiring_soon = memberships.filtered(
            lambda m: m.state in ['active', 'grace'] and 
            m.end_date and 
            m.end_date <= thirty_days_from_now
        )
        stats['expiring_soon_count'] = len(expiring_soon)
        
        return stats
    
    @api.model
    def get_membership_type_report(self):
        """Generate membership type summary report"""
        types = self.search([('active', '=', True)])
        report_data = []
        
        for membership_type in types:
            stats = membership_type.get_membership_statistics()
            report_data.append({
                'name': membership_type.name,
                'code': membership_type.code,
                'category': membership_type.membership_category,
                'price': membership_type.price,
                'currency': membership_type.currency_id.symbol,
                'duration': membership_type.duration if not membership_type.is_lifetime else 'Lifetime',
                'stats': stats
            })
        
        return report_data
    
    def copy(self, default=None):
        """Override copy to ensure unique code"""
        if default is None:
            default = {}
        if not default.get('code'):
            default['code'] = f"{self.code}_copy"
        if not default.get('name'):
            default['name'] = f"{self.name} (Copy)"
        return super().copy(default)
    
    @api.model
    def create(self, vals):
        """Override create to auto-generate code if not provided"""
        if not vals.get('code'):
            # Generate code from name
            name = vals.get('name', 'TYPE')
            base_code = name.upper().replace(' ', '_')[:15]
            code = base_code
            counter = 1
            while self.search([('code', '=', code)]):
                code = f"{base_code}_{counter}"
                counter += 1
            vals['code'] = code
        
        return super().create(vals)
    
    def write(self, vals):
        """Override write to track important changes"""
        result = super().write(vals)
        
        # Log important changes
        for record in self:
            if 'price' in vals:
                record.message_post(
                    body=_("Membership price updated to %s %s") % (vals['price'], record.currency_id.symbol),
                    message_type='notification'
                )
            if 'duration' in vals:
                if vals['duration'] == 0:
                    record.message_post(
                        body=_("Membership type converted to lifetime membership"),
                        message_type='notification'
                    )
                else:
                    record.message_post(
                        body=_("Membership duration updated to %s months") % vals['duration'],
                        message_type='notification'
                    )
        
        return result