# -*- coding: utf-8 -*-

from . import models
from . import wizards
from . import controllers

def post_init_hook(env):
    """
    Post-installation hook to set up initial data and configurations.
    """
    # Set up default membership sequence if not exists
    sequence = env['ir.sequence'].search([('code', '=', 'ams.membership.number')], limit=1)
    if not sequence:
        env['ir.sequence'].create({
            'name': 'Membership Number Sequence',
            'code': 'ams.membership.number',
            'prefix': 'MEM',
            'padding': 6,
            'number_increment': 1,
            'number_next_actual': 1,
        })
    
    # Initialize default subscription product types if they don't exist
    product_template = env['product.template']
    
    # Create sample subscription products for each product class if none exist
    product_classes = [
        ('membership', 'Membership Products'),
        ('chapter', 'Chapter Memberships'),
        ('subscription', 'Publication Subscriptions'),
        ('newsletter', 'Newsletter Subscriptions'),
        ('courses', 'Educational Courses'),
        ('donations', 'Recurring Donations'),
    ]
    
    for product_class, category_name in product_classes:
        existing = product_template.search([('product_class', '=', product_class)], limit=1)
        if not existing:
            # Create a sample product for this class
            member_type = env['ams.member.type'].search([('product_class', '=', product_class)], limit=1)
            if member_type:
                product_template.create({
                    'name': f'Sample {category_name.title()}',
                    'type': 'service',
                    'is_subscription_product': True,
                    'product_class': product_class,
                    'member_type_id': member_type.id,
                    'list_price': member_type.base_annual_fee,
                    'recurrence_period': member_type.recurrence_period,
                    'membership_period_type': member_type.membership_period_type,
                    'membership_duration': member_type.membership_duration,
                    'active': False,  # Make inactive by default - just for reference
                })