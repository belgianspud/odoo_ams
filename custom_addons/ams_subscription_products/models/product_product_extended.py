# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ProductProductSubscriptionExtended(models.Model):
    """
    Extend product variants to support subscription-specific behavior types.
    """
    _inherit = 'product.product'

    # Extend the template behavior selection to match the extended template field
    template_ams_product_behavior = fields.Selection(
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

    @api.depends('template_has_digital_content', 'qty_available', 'template_ams_product_behavior')
    def _compute_availability_status(self):
        """Enhanced availability status computation including subscription-specific behaviors"""
        super()._compute_availability_status()
        
        for variant in self:
            # Handle subscription-specific behavior types
            if variant.template_ams_product_behavior == 'chapter':
                variant.availability_status = 'membership_available'
            elif variant.template_ams_product_behavior == 'committee':
                if hasattr(variant, 'template_requires_approval') and variant.template_requires_approval:
                    variant.availability_status = 'membership_available'  # Requires approval but available
                else:
                    variant.availability_status = 'membership_available'
            elif variant.template_ams_product_behavior == 'training':
                if variant.template_has_digital_content:
                    variant.availability_status = 'digital_available'
                else:
                    variant.availability_status = 'service_available'

    def name_get(self):
        """Enhanced name display including subscription-specific behavior indicators"""
        result = super().name_get()
        
        # Add subscription-specific behavior indicators
        subscription_behavior_indicators = {
            'chapter': '👥',  # People icon for chapter
            'committee': '🏛️',  # Building icon for committee
            'training': '🎓',  # Graduation cap for training
        }
        
        enhanced_result = []
        for variant_id, name in result:
            variant = self.browse(variant_id)
            
            if variant.template_ams_product_behavior in subscription_behavior_indicators:
                indicator = subscription_behavior_indicators[variant.template_ams_product_behavior]
                name = f"{indicator} {name}"
                
            enhanced_result.append((variant_id, name))
                
        return enhanced_result