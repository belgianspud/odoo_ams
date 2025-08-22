class AMSSubscription(models.Model):
    _inherit = 'ams.subscription'
    
    # Add computed benefit access
    available_benefit_ids = fields.Many2many(
        'ams.membership.benefit',
        compute='_compute_available_benefits',
        string='Available Benefits'
    )
    
    benefit_summary = fields.Html(
        'Benefit Summary',
        compute='_compute_available_benefits'
    )
    
    @api.depends('tier_id.benefit_ids', 'state')
    def _compute_available_benefits(self):
        for subscription in self:
            if subscription.state == 'active' and subscription.tier_id:
                subscription.available_benefit_ids = subscription.tier_id.benefit_ids.filtered('active')
                
                # Build HTML summary
                if subscription.available_benefit_ids:
                    benefits_html = "<ul>"
                    for benefit in subscription.available_benefit_ids:
                        benefits_html += f"<li><strong>{benefit.name}</strong>"
                        if benefit.discount_percentage:
                            benefits_html += f" ({benefit.discount_percentage}% discount)"
                        benefits_html += f"<br/><small>{benefit.description or ''}</small></li>"
                    benefits_html += "</ul>"
                    subscription.benefit_summary = benefits_html
                else:
                    subscription.benefit_summary = "<p>No additional benefits included.</p>"
            else:
                subscription.available_benefit_ids = False
                subscription.benefit_summary = "<p>No benefits available for inactive subscriptions.</p>"
