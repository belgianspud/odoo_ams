from odoo import models, fields, api

class AMSMembershipBenefit(models.Model):
    _name = 'ams.membership.benefit'
    _description = 'AMS Membership Benefit'
    _order = 'sequence, name'

    name = fields.Char('Benefit Name', required=True)
    description = fields.Html('Description')
    sequence = fields.Integer('Sequence', default=10)
    
    benefit_type = fields.Selection([
        ('discount_event', 'Event Discount'),
        ('discount_product', 'Product Discount'),
        ('publication_access', 'Publication Access'),
        ('certification_credit', 'Certification Credit'),
        ('portal_feature', 'Portal Feature'),
        ('networking', 'Networking Access'),
        ('directory', 'Member Directory'),
        ('support_priority', 'Priority Support'),
        ('webinar_access', 'Webinar Access'),
        ('resource_library', 'Resource Library'),
        ('other', 'Other')
    ], string='Benefit Type', required=True)
    
    # Benefit value/configuration
    discount_percentage = fields.Float(
        'Discount Percentage',
        help='For discount benefits, percentage off regular price'
    )
    
    discount_amount = fields.Float(
        'Discount Amount',
        help='For discount benefits, fixed amount off'
    )
    
    credit_hours = fields.Float(
        'Credit Hours',
        help='For certification benefits, number of CE hours'
    )
    
    # Availability settings
    active = fields.Boolean('Active', default=True)
    start_date = fields.Date('Available From')
    end_date = fields.Date('Available Until')
    
    # Usage tracking
    usage_count = fields.Integer(
        'Times Used',
        compute='_compute_usage_stats',
        help='How many times this benefit has been used'
    )
    
    eligible_member_count = fields.Integer(
        'Eligible Members',
        compute='_compute_usage_stats',
        help='How many members are eligible for this benefit'
    )
    
    # Which tiers get this benefit
    tier_ids = fields.Many2many(
        'ams.subscription.tier',
        'ams_tier_benefit_rel',
        'benefit_id',
        'tier_id',
        string='Available for Tiers'
    )
    
    # Instructions for members
    instructions = fields.Html(
        'How to Use',
        help='Instructions for members on how to use this benefit'
    )
    
    # External integration
    external_code = fields.Char(
        'External Code',
        help='Code for integration with external systems'
    )
    
    def _compute_usage_stats(self):
        """Compute usage statistics"""
        for benefit in self:
            # Count eligible members
            active_subscriptions = self.env['ams.subscription'].search([
                ('state', '=', 'active'),
                ('tier_id', 'in', benefit.tier_ids.ids)
            ])
            benefit.eligible_member_count = len(active_subscriptions)
            
            # Usage count would be computed from actual usage records
            # This would integrate with event registrations, sales, etc.
            benefit.usage_count = 0  # Placeholder

    def action_view_eligible_members(self):
        """View members eligible for this benefit"""
        self.ensure_one()
        
        subscriptions = self.env['ams.subscription'].search([
            ('state', '=', 'active'),
            ('tier_id', 'in', self.tier_ids.ids)
        ])
        
        partners = subscriptions.mapped('partner_id')
        
        return {
            'name': f'Members Eligible for {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('id', 'in', partners.ids)],
            'context': {'default_membership_benefit_id': self.id}
        }
