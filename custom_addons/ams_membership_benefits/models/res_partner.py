class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Add partner benefit access
    current_benefit_ids = fields.Many2many(
        'ams.membership.benefit',
        compute='_compute_current_benefits',
        string='Current Benefits'
    )
    
    @api.depends('current_individual_subscription_id.available_benefit_ids',
                 'enterprise_seat_ids.individual_subscription_id.available_benefit_ids')
    def _compute_current_benefits(self):
        for partner in self:
            benefits = self.env['ams.membership.benefit']
            
            # From individual subscription
            if partner.current_individual_subscription_id:
                benefits |= partner.current_individual_subscription_id.available_benefit_ids
            
            # From enterprise seat assignments
            for seat in partner.enterprise_seat_ids.filtered('active'):
                if seat.individual_subscription_id:
                    benefits |= seat.individual_subscription_id.available_benefit_ids
            
            partner.current_benefit_ids = benefits
    
    def action_view_my_benefits(self):
        """View current member benefits"""
        self.ensure_one()
        
        return {
            'name': f'Benefits for {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership.benefit',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.current_benefit_ids.ids)],
            'context': {'create': False, 'edit': False}
        }
