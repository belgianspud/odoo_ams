# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class AMSSubscriptionModificationWizard(models.TransientModel):
    """Wizard for subscription modifications"""
    _name = 'ams.subscription.modification.wizard'
    _description = 'Subscription Modification Wizard'

    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        readonly=True
    )
    
    modification_type = fields.Selection([
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
    ], string='Modification Type', required=True)
    
    current_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='Current Tier',
        readonly=True
    )
    
    new_tier_id = fields.Many2one(
        'ams.subscription.tier',
        string='New Tier',
        required=True,
        domain="[('subscription_type', '=', current_tier_type)]"
    )
    
    current_tier_type = fields.Selection(
        related='current_tier_id.subscription_type',
        string='Current Tier Type'
    )
    
    reason = fields.Text(
        string='Reason for Change',
        required=True,
        help='Please explain why you are making this change'
    )
    
    proration_amount = fields.Float(
        string='Proration Amount',
        readonly=True,
        help='Amount that will be charged/credited'
    )
    
    proration_explanation = fields.Text(
        string='Proration Explanation',
        readonly=True,
        help='Explanation of proration calculation'
    )
    
    # Current subscription info for display
    current_tier_name = fields.Char(
        related='current_tier_id.name',
        string='Current Tier Name',
        readonly=True
    )
    
    subscription_name = fields.Char(
        related='subscription_id.name',
        string='Subscription Name',
        readonly=True
    )
    
    subscription_state = fields.Selection(
        related='subscription_id.state',
        string='Subscription Status',
        readonly=True
    )

    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super().default_get(fields_list)
        
        subscription_id = self.env.context.get('default_subscription_id')
        if subscription_id:
            subscription = self.env['ams.subscription'].browse(subscription_id)
            res.update({
                'subscription_id': subscription.id,
                'current_tier_id': subscription.tier_id.id,
                'modification_type': self.env.context.get('default_modification_type', 'upgrade'),
            })
        
        return res

    @api.onchange('new_tier_id')
    def _onchange_new_tier_id(self):
        """Calculate proration when tier changes"""
        if self.subscription_id and self.new_tier_id and self.current_tier_id:
            try:
                # Calculate proration amount
                self.proration_amount = self.subscription_id._calculate_proration(
                    self.current_tier_id, 
                    self.new_tier_id, 
                    self.modification_type
                )
                
                # Generate explanation
                if self.proration_amount > 0:
                    self.proration_explanation = (
                        f"You will be charged ${self.proration_amount:.2f} for this {self.modification_type}. "
                        f"This amount is prorated based on the remaining time in your current billing period."
                    )
                elif self.proration_amount < 0:
                    self.proration_explanation = (
                        f"You will receive a credit of ${abs(self.proration_amount):.2f} for this {self.modification_type}. "
                        f"This amount is prorated based on the remaining time in your current billing period."
                    )
                else:
                    self.proration_explanation = (
                        "No additional charges or credits will apply for this change."
                    )
                    
            except Exception as e:
                self.proration_amount = 0.0
                self.proration_explanation = f"Unable to calculate proration: {str(e)}"
        else:
            self.proration_amount = 0.0
            self.proration_explanation = ""

    @api.onchange('modification_type')
    def _onchange_modification_type(self):
        """Update domain and clear selection when modification type changes"""
        if self.new_tier_id:
            # Trigger proration recalculation
            self._onchange_new_tier_id()

    def action_confirm_modification(self):
        """Confirm the subscription modification"""
        self.ensure_one()
        
        # Validate the modification
        if not self.subscription_id:
            raise UserError("No subscription selected.")
        
        if not self.new_tier_id:
            raise UserError("Please select a new tier.")
        
        if self.new_tier_id == self.current_tier_id:
            raise UserError("The new tier must be different from the current tier.")
        
        if not self.subscription_id.allow_modifications:
            raise UserError("This subscription does not allow modifications.")
        
        if self.subscription_id.state != 'active':
            raise UserError("Only active subscriptions can be modified.")
        
        try:
            # Perform the modification
            modification = self.subscription_id.action_modify_subscription(
                self.new_tier_id.id, 
                self.modification_type
            )
            
            # Update modification reason
            if modification:
                modification.reason = self.reason
                modification.action_confirm()
                modification.action_apply()
            
            # Show success message
            message = f'Subscription {self.modification_type} completed successfully!'
            if self.proration_amount > 0:
                message += f' You will be charged ${self.proration_amount:.2f}.'
            elif self.proration_amount < 0:
                message += f' You will receive a credit of ${abs(self.proration_amount):.2f}.'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except UserError:
            raise
        except Exception as e:
            raise UserError(f"An error occurred while modifying the subscription: {str(e)}")

    def action_cancel(self):
        """Cancel the modification wizard"""
        return {'type': 'ir.actions.act_window_close'}

    def action_preview_changes(self):
        """Preview what changes will be made"""
        self.ensure_one()
        
        preview_text = f"""
Subscription Modification Preview:

Current Tier: {self.current_tier_id.name}
New Tier: {self.new_tier_id.name}
Modification Type: {self.modification_type.title()}

Financial Impact:
{self.proration_explanation}

Reason: {self.reason}

This change will take effect immediately upon confirmation.
        """
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Modification Preview',
            'res_model': 'ams.subscription.modification.preview',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_preview_text': preview_text,
                'default_wizard_id': self.id,
            }
        }


class AMSSubscriptionModificationPreview(models.TransientModel):
    """Preview wizard for subscription modifications"""
    _name = 'ams.subscription.modification.preview'
    _description = 'Subscription Modification Preview'

    preview_text = fields.Text(
        string='Preview',
        readonly=True
    )
    
    wizard_id = fields.Many2one(
        'ams.subscription.modification.wizard',
        string='Modification Wizard'
    )

    def action_back_to_wizard(self):
        """Go back to the modification wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Modify Subscription',
            'res_model': 'ams.subscription.modification.wizard',
            'res_id': self.wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm_from_preview(self):
        """Confirm modification from preview"""
        if self.wizard_id:
            return self.wizard_id.action_confirm_modification()
        return {'type': 'ir.actions.act_window_close'}