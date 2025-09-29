# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LinkExistingPlanWizard(models.TransientModel):
    _name = 'link.existing.plan.wizard'
    _description = 'Link Existing Subscription Plan'

    product_template_id = fields.Many2one(
        'product.template', 
        'Product', 
        required=True
    )
    plan_id = fields.Many2one(
        'subscription.plan', 
        'Subscription Plan', 
        required=True,
        domain=[('product_template_id', '=', False)]
    )
    plan_ids = fields.Many2many(
        'subscription.plan',
        string='Available Plans',
        compute='_compute_available_plans'
    )
    warning_message = fields.Html(
        'Warning',
        compute='_compute_warning_message'
    )

    @api.depends('product_template_id')
    def _compute_available_plans(self):
        """Get plans that are not linked to any product"""
        for wizard in self:
            available_plans = self.env['subscription.plan'].search([
                ('product_template_id', '=', False)
            ])
            wizard.plan_ids = available_plans

    @api.depends('plan_id')
    def _compute_warning_message(self):
        """Show warning if plan was previously linked"""
        for wizard in self:
            if wizard.plan_id and wizard.plan_id.product_template_id:
                wizard.warning_message = f"""
                    <div class="alert alert-warning">
                        <strong>Warning:</strong> This plan is currently linked to 
                        <strong>{wizard.plan_id.product_template_id.name}</strong>. 
                        Linking it to this product will remove the previous link.
                    </div>
                """
            else:
                wizard.warning_message = False

    def action_link_plan(self):
        """Link the selected plan to the product"""
        self.ensure_one()
        
        if not self.plan_id:
            raise UserError(_('Please select a subscription plan to link.'))
        
        # Link the plan to the product
        self.plan_id.write({
            'product_template_id': self.product_template_id.id
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Subscription plan "%s" has been linked to this product.') % self.plan_id.name,
                'type': 'success',
                'sticky': False,
            }
        }