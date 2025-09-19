# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class ProductTemplateSubscriptionExtended(models.Model):
    """
    Extend product template to add subscription-specific behavior types.
    """
    _inherit = 'product.template'

    # Extend the ams_product_behavior selection to include subscription-specific types
    ams_product_behavior = fields.Selection(
        selection_add=[
            ('chapter', 'Chapter Membership'),
            ('committee', 'Committee Access'),
            ('training', 'Training & Education'),
        ],
        ondelete={
            'chapter': 'cascade',
            'committee': 'cascade', 
            'training': 'cascade',
        }
    )

    @api.onchange('ams_product_behavior')
    def _onchange_ams_product_behavior_subscription(self):
        """Apply subscription-specific defaults based on selected behavior type"""
        result = super()._onchange_ams_product_behavior()
        
        if not self.ams_product_behavior:
            return result
            
        # Extended behavior defaults for subscription module
        subscription_behavior_defaults = {
            'chapter': {
                'is_subscription': True,
                'subscription_scope': 'individual',
                'is_renewable': True,
                'auto_renewal_enabled': True,
                'grants_portal_access': True,
                'type': 'service',
            },
            'committee': {
                'is_subscription': True,
                'subscription_scope': 'individual', 
                'is_renewable': True,
                'auto_renewal_enabled': False,
                'grants_portal_access': True,
                'requires_approval': True,
                'type': 'service',
            },
            'training': {
                'is_subscription': False,  # Training courses are typically not recurring
                'grants_portal_access': True,
                'type': 'service',
            },
        }
        
        defaults = subscription_behavior_defaults.get(self.ams_product_behavior, {})
        for field, value in defaults.items():
            if hasattr(self, field) and not getattr(self, field):
                setattr(self, field, value)
                
        return result