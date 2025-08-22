class AMSSubscriptionTier(models.Model):
    _inherit = 'ams.subscription.tier'
    
    # Add benefits to tiers
    benefit_ids = fields.Many2many(
        'ams.membership.benefit',
        'ams_tier_benefit_rel',
        'tier_id',
        'benefit_id',
        string='Included Benefits'
    )
    
    benefit_count = fields.Integer(
        'Benefit Count',
        compute='_compute_benefit_count'
    )
    
    @api.depends('benefit_ids')
    def _compute_benefit_count(self):
        for tier in self:
            tier.benefit_count = len(tier.benefit_ids.filtered('active'))
