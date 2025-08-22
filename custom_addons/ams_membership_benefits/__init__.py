# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import wizards

def post_init_hook(env):
    """
    Post-installation hook to set up default benefits and configurations
    """
    # Create default benefit categories if they don't exist
    category_obj = env['ams.benefit.category']
    default_categories = [
        ('events', 'Event Benefits', 'Benefits related to event access and pricing'),
        ('elearning', 'eLearning Benefits', 'Benefits related to course access and education'),
        ('portal', 'Portal Access', 'Benefits related to member portal features'),
        ('networking', 'Networking Benefits', 'Benefits related to member networking and directory'),
        ('publications', 'Publication Benefits', 'Benefits related to publications and resources'),
        ('support', 'Support Benefits', 'Benefits related to customer support and services'),
    ]
    
    for code, name, description in default_categories:
        if not category_obj.search([('code', '=', code)]):
            category_obj.create({
                'code': code,
                'name': name,
                'description': description,
                'sequence': len(category_obj.search([])) + 1,
            })
    
    # Set up default benefit configurations for existing tiers
    tier_obj = env['ams.subscription.tier']
    benefit_obj = env['ams.membership.benefit']
    
    # Create basic event discount benefit for all tiers
    if not benefit_obj.search([('code', '=', 'event_member_discount')]):
        event_discount = benefit_obj.create({
            'name': 'Member Event Discount',
            'code': 'event_member_discount',
            'benefit_type': 'discount_percentage',
            'category_id': category_obj.search([('code', '=', 'events')], limit=1).id,
            'discount_percentage': 15.0,
            'description': 'Standard member discount on all association events',
            'active': True,
        })
        
        # Apply to all existing individual and enterprise tiers
        individual_tiers = tier_obj.search([('subscription_type', '=', 'individual')])
        enterprise_tiers = tier_obj.search([('subscription_type', '=', 'enterprise')])
        
        if individual_tiers or enterprise_tiers:
            event_discount.tier_ids = [(6, 0, (individual_tiers + enterprise_tiers).ids)]

def uninstall_hook(env):
    """
    Pre-uninstallation hook to clean up benefit assignments
    """
    # Remove benefit assignments from subscription tiers
    # but keep the tier records themselves intact
    env['ams.subscription.tier'].search([]).write({'benefit_ids': [(5, 0, 0)]})
    
    # Log the uninstallation
    env['ir.logging'].sudo().create({
        'name': 'AMS Membership Benefits',
        'type': 'server',
        'level': 'INFO',
        'message': 'AMS Membership Benefits module uninstalled successfully. Benefit assignments cleared.',
        'path': 'ams_membership_benefits',
        'func': 'uninstall_hook',
        'line': '1',
    })