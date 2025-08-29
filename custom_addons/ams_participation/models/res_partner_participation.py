from odoo import models, fields, api


class ResPartnerParticipation(models.Model):
    """Extend res.partner with participation tracking capabilities."""
    _inherit = 'res.partner'

    # Computed participation fields
    participation_ids = fields.One2many(
        'ams.participation',
        compute='_compute_all_participations',
        string='All Participations',
        help='All participation records for this member'
    )
    
    active_participation_ids = fields.One2many(
        'ams.participation',
        compute='_compute_active_participations', 
        string='Active Participations',
        help='Current active participations (active and grace status)'
    )
    
    participation_history_ids = fields.One2many(
        'ams.participation',
        compute='_compute_participation_history',
        string='Participation History', 
        help='Past and inactive participations'
    )
    
    # Participation statistics
    participation_count = fields.Integer(
        string='Total Participations',
        compute='_compute_participation_stats'
    )
    
    active_participation_count = fields.Integer(
        string='Active Participations', 
        compute='_compute_participation_stats'
    )
    
    has_active_membership = fields.Boolean(
        string='Has Active Membership',
        compute='_compute_participation_stats',
        help='Has at least one active membership participation'
    )
    
    primary_membership_id = fields.Many2one(
        'ams.participation',
        string='Primary Membership',
        compute='_compute_primary_membership',
        help='Primary active membership participation'
    )

    @api.depends('name', 'is_company')
    def _compute_all_participations(self):
        """Get all participations for this partner."""
        for partner in self:
            if partner.is_company:
                participations = self.env['ams.participation'].search([
                    ('company_id', '=', partner.id)
                ])
            else:
                participations = self.env['ams.participation'].search([
                    ('partner_id', '=', partner.id)
                ])
            partner.participation_ids = participations

    @api.depends('name', 'is_company')
    def _compute_active_participations(self):
        """Get active participations (active and grace status)."""
        for partner in self:
            if partner.is_company:
                participations = self.env['ams.participation'].search([
                    ('company_id', '=', partner.id),
                    ('status', 'in', ['active', 'grace'])
                ])
            else:
                participations = self.env['ams.participation'].search([
                    ('partner_id', '=', partner.id),
                    ('status', 'in', ['active', 'grace'])
                ])
            partner.active_participation_ids = participations

    @api.depends('name', 'is_company')
    def _compute_participation_history(self):
        """Get historical/inactive participations."""
        for partner in self:
            if partner.is_company:
                participations = self.env['ams.participation'].search([
                    ('company_id', '=', partner.id),
                    ('status', 'not in', ['active', 'grace'])
                ])
            else:
                participations = self.env['ams.participation'].search([
                    ('partner_id', '=', partner.id),
                    ('status', 'not in', ['active', 'grace'])
                ])
            partner.participation_history_ids = participations

    @api.depends('name', 'is_company')
    def _compute_participation_stats(self):
        """Compute participation statistics."""
        for partner in self:
            if partner.is_company:
                domain_base = [('company_id', '=', partner.id)]
            else:
                domain_base = [('partner_id', '=', partner.id)]
            
            # Total participations
            partner.participation_count = self.env['ams.participation'].search_count(domain_base)
            
            # Active participations
            active_domain = domain_base + [('status', 'in', ['active', 'grace'])]
            partner.active_participation_count = self.env['ams.participation'].search_count(active_domain)
            
            # Has active membership
            membership_domain = domain_base + [
                ('participation_type', '=', 'membership'),
                ('status', 'in', ['active', 'grace'])
            ]
            partner.has_active_membership = bool(
                self.env['ams.participation'].search_count(membership_domain)
            )

    @api.depends('name', 'is_company')
    def _compute_primary_membership(self):
        """Get primary active membership participation."""
        for partner in self:
            if partner.is_company:
                domain = [
                    ('company_id', '=', partner.id),
                    ('participation_type', '=', 'membership'),
                    ('status', 'in', ['active', 'grace'])
                ]
            else:
                domain = [
                    ('partner_id', '=', partner.id),
                    ('participation_type', '=', 'membership'),
                    ('status', 'in', ['active', 'grace'])
                ]
            
            membership = self.env['ams.participation'].search(
                domain, order='status desc, begin_date desc', limit=1
            )
            partner.primary_membership_id = membership

    def action_view_participations(self):
        """Open participations for this member."""
        self.ensure_one()
        if self.is_company:
            domain = [('company_id', '=', self.id)]
        else:
            domain = [('partner_id', '=', self.id)]
            
        return {
            'name': f'Participations - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.participation',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_partner_id': None if self.is_company else self.id,
                'default_company_id': self.id if self.is_company else None,
            },
        }

    def action_create_participation(self):
        """Quick action to create a new participation."""
        self.ensure_one()
        return {
            'name': f'New Participation - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.participation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': None if self.is_company else self.id,
                'default_company_id': self.id if self.is_company else None,
                'default_participation_type': 'membership',
            },
        }