from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Computed fields for subscriptions
    subscription_ids = fields.One2many('ams.subscription', 'partner_id', 'All Subscriptions')
    
    # Active subscription counts
    active_subscription_count = fields.Integer('Active Subscriptions', compute='_compute_subscription_counts', store=True)
    total_subscription_count = fields.Integer('Total Subscriptions', compute='_compute_subscription_counts', store=True)
    expired_subscription_count = fields.Integer('Expired Subscriptions', compute='_compute_subscription_counts', store=True)
    cancelled_subscription_count = fields.Integer('Cancelled Subscriptions', compute='_compute_subscription_counts', store=True)
    pending_renewal_count = fields.Integer('Pending Renewals', compute='_compute_subscription_counts', store=True)
    
    # Current membership details
    current_membership_id = fields.Many2one('ams.subscription', 'Current Membership', compute='_compute_current_membership', store=True)
    membership_status = fields.Selection(related='current_membership_id.state', string='Membership Status', store=True)
    membership_start_date = fields.Date(related='current_membership_id.start_date', string='Membership Start', store=True)
    membership_end_date = fields.Date(related='current_membership_id.end_date', string='Membership End', store=True)
    membership_amount = fields.Float(related='current_membership_id.amount', string='Membership Amount', store=True)
    next_renewal_date = fields.Date(related='current_membership_id.next_renewal_date', string='Next Renewal', store=True)
    auto_renewal_enabled = fields.Boolean(related='current_membership_id.auto_renewal', string='Auto Renewal', store=True)
    
    # Categorized subscription fields
    active_membership_count = fields.Integer('Active Memberships', compute='_compute_subscription_counts', store=True)
    active_chapter_subscription_ids = fields.One2many('ams.subscription', 'partner_id', 'Active Chapters',
                                                     domain=[('subscription_code', '=', 'chapter'), ('state', '=', 'active')])
    active_publication_subscription_ids = fields.One2many('ams.subscription', 'partner_id', 'Active Publications',
                                                         domain=[('subscription_code', '=', 'publication'), ('state', '=', 'active')])
    
    # Historical subscription fields
    past_membership_subscription_ids = fields.One2many('ams.subscription', 'partner_id', 'Past Memberships',
                                                      domain=[('subscription_code', '=', 'membership'), ('state', 'in', ['expired', 'cancelled'])])
    past_chapter_subscription_ids = fields.One2many('ams.subscription', 'partner_id', 'Past Chapters',
                                                   domain=[('subscription_code', '=', 'chapter'), ('state', 'in', ['expired', 'cancelled'])])
    past_publication_subscription_ids = fields.One2many('ams.subscription', 'partner_id', 'Past Publications',
                                                       domain=[('subscription_code', '=', 'publication'), ('state', 'in', ['expired', 'cancelled'])])
    
    # Renewal management
    pending_renewal_subscription_ids = fields.One2many('ams.subscription', 'partner_id', 'Pending Renewals',
                                                      domain=[('state', '=', 'pending_renewal')])
    next_renewal_due_date = fields.Date('Next Renewal Due', compute='_compute_renewal_info', store=True)
    
    # Financial summary
    total_subscription_value = fields.Float('Total Subscription Value', compute='_compute_financial_summary', store=True)
    active_subscription_value = fields.Float('Active Subscription Value', compute='_compute_financial_summary', store=True)
    
    @api.depends('subscription_ids', 'subscription_ids.state', 'subscription_ids.subscription_code')
    def _compute_subscription_counts(self):
        for partner in self:
            subscriptions = partner.subscription_ids
            partner.total_subscription_count = len(subscriptions)
            partner.active_subscription_count = len(subscriptions.filtered(lambda s: s.state == 'active'))
            partner.expired_subscription_count = len(subscriptions.filtered(lambda s: s.state == 'expired'))
            partner.cancelled_subscription_count = len(subscriptions.filtered(lambda s: s.state == 'cancelled'))
            partner.pending_renewal_count = len(subscriptions.filtered(lambda s: s.state == 'pending_renewal'))
            partner.active_membership_count = len(subscriptions.filtered(lambda s: s.subscription_code == 'membership' and s.state == 'active'))
    
    @api.depends('subscription_ids', 'subscription_ids.state', 'subscription_ids.subscription_code')
    def _compute_current_membership(self):
        for partner in self:
            # Find the most recent active membership
            current_membership = partner.subscription_ids.filtered(
                lambda s: s.subscription_code == 'membership' and s.state == 'active'
            ).sorted('start_date', reverse=True)
            
            partner.current_membership_id = current_membership[0] if current_membership else False
    
    @api.depends('subscription_ids', 'subscription_ids.next_renewal_date', 'subscription_ids.state')
    def _compute_renewal_info(self):
        for partner in self:
            pending_renewals = partner.subscription_ids.filtered(lambda s: s.state == 'pending_renewal')
            if pending_renewals:
                partner.next_renewal_due_date = min(pending_renewals.mapped('next_renewal_date'))
            else:
                partner.next_renewal_due_date = False
    
    @api.depends('subscription_ids', 'subscription_ids.amount', 'subscription_ids.state')
    def _compute_financial_summary(self):
        for partner in self:
            all_subscriptions = partner.subscription_ids
            active_subscriptions = all_subscriptions.filtered(lambda s: s.state == 'active')
            
            partner.total_subscription_value = sum(all_subscriptions.mapped('amount'))
            partner.active_subscription_value = sum(active_subscriptions.mapped('amount'))
    
    def action_view_active_subscriptions(self):
        """Action to view active subscriptions"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Active Subscriptions',
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id), ('state', '=', 'active')],
            'context': {
                'default_partner_id': self.id,
                'search_default_active': 1,
            }
        }
    
    def action_view_all_subscriptions(self):
        """Action to view all subscriptions"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - All Subscriptions',
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
            }
        }
    
    def action_create_membership(self):
        """Action to create a new membership subscription"""
        membership_type = self.env['ams.subscription.type'].search([('code', '=', 'membership')], limit=1)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Membership',
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.id,
                'default_subscription_type_id': membership_type.id if membership_type else False,
            }
        }
    
    def action_enable_auto_renewal(self):
        """Enable auto renewal for active subscriptions"""
        active_subscriptions = self.subscription_ids.filtered(lambda s: s.state == 'active' and s.is_recurring)
        active_subscriptions.write({'auto_renewal': True})
    
    def action_disable_auto_renewal(self):
        """Disable auto renewal for active subscriptions"""
        active_subscriptions = self.subscription_ids.filtered(lambda s: s.state == 'active' and s.is_recurring)
        active_subscriptions.write({'auto_renewal': False})
    
    def action_view_subscription_products(self):
        """Action to view available subscription products"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Available Subscription Products',
            'res_model': 'product.template',
            'view_mode': 'kanban,tree,form',
            'domain': [('is_subscription_product', '=', True), ('website_published', '=', True)],
            'context': {
                'search_default_is_subscription_product': 1,
                'search_default_website_published': 1,
            }
        }