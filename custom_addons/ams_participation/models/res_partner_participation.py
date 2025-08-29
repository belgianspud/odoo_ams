from odoo import models, fields, api


class ResPartnerParticipation(models.Model):
    """Extend res.partner with participation tracking capabilities."""
    _inherit = 'res.partner'

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

    def _compute_participation_stats(self):
        """Compute participation statistics."""
        # Get all partners and their participations in bulk for efficiency
        if not self:
            return
            
        # Build domain based on partner types
        individual_partner_ids = self.filtered(lambda p: not p.is_company).ids
        company_partner_ids = self.filtered(lambda p: p.is_company).ids
        
        # Initialize all fields
        for partner in self:
            partner.participation_count = 0
            partner.active_participation_count = 0
            partner.has_active_membership = False
        
        if not individual_partner_ids and not company_partner_ids:
            return
            
        # Query participations in bulk
        domain = []
        if individual_partner_ids:
            domain.append(('partner_id', 'in', individual_partner_ids))
        if company_partner_ids:
            if domain:
                domain = ['|'] + domain + [('company_id', 'in', company_partner_ids)]
            else:
                domain = [('company_id', 'in', company_partner_ids)]
        
        participations = self.env['ams.participation'].search(domain)
        
        # Group participations by partner
        partner_participations = {}
        for participation in participations:
            partner_id = participation.partner_id.id if participation.partner_id else participation.company_id.id
            if partner_id not in partner_participations:
                partner_participations[partner_id] = []
            partner_participations[partner_id].append(participation)
        
        # Calculate stats for each partner
        for partner in self:
            partner_participations_list = partner_participations.get(partner.id, [])
            
            # Total participations
            partner.participation_count = len(partner_participations_list)
            
            # Active participations
            active_participations = [p for p in partner_participations_list if p.status in ['active', 'grace']]
            partner.active_participation_count = len(active_participations)
            
            # Has active membership
            active_memberships = [p for p in active_participations if p.participation_type == 'membership']
            partner.has_active_membership = len(active_memberships) > 0

    def _compute_primary_membership(self):
        """Get primary active membership participation."""
        # Initialize all partners
        for partner in self:
            partner.primary_membership_id = False
            
        if not self:
            return
            
        # Build domain for active memberships
        individual_partner_ids = self.filtered(lambda p: not p.is_company).ids
        company_partner_ids = self.filtered(lambda p: p.is_company).ids
        
        domain = [
            ('participation_type', '=', 'membership'),
            ('status', 'in', ['active', 'grace'])
        ]
        
        if individual_partner_ids:
            domain.append(('partner_id', 'in', individual_partner_ids))
        if company_partner_ids:
            if individual_partner_ids:
                domain = ['|', ('partner_id', 'in', individual_partner_ids), ('company_id', 'in', company_partner_ids)] + domain[1:]
            else:
                domain.append(('company_id', 'in', company_partner_ids))
        
        memberships = self.env['ams.participation'].search(
            domain, order='status desc, begin_date desc'
        )
        
        # Assign primary membership to each partner
        for partner in self:
            partner_membership = memberships.filtered(
                lambda m: (m.partner_id.id == partner.id and not partner.is_company) or 
                         (m.company_id.id == partner.id and partner.is_company)
            )[:1]  # Get first (primary) membership
            
            if partner_membership:
                partner.primary_membership_id = partner_membership

    @property
    def participation_ids(self):
        """Get all participations for this partner."""
        if self.is_company:
            return self.env['ams.participation'].search([('company_id', '=', self.id)])
        else:
            return self.env['ams.participation'].search([('partner_id', '=', self.id)])

    @property  
    def active_participation_ids(self):
        """Get active participations (active and grace status)."""
        if self.is_company:
            return self.env['ams.participation'].search([
                ('company_id', '=', self.id),
                ('status', 'in', ['active', 'grace'])
            ])
        else:
            return self.env['ams.participation'].search([
                ('partner_id', '=', self.id),
                ('status', 'in', ['active', 'grace'])
            ])

    @property
    def participation_history_ids(self):
        """Get historical/inactive participations."""
        if self.is_company:
            return self.env['ams.participation'].search([
                ('company_id', '=', self.id),
                ('status', 'not in', ['active', 'grace'])
            ])
        else:
            return self.env['ams.participation'].search([
                ('partner_id', '=', self.id),
                ('status', 'not in', ['active', 'grace'])
            ])

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