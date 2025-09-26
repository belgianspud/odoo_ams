# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Related fields from product template for easy access
    is_subscription_product = fields.Boolean('Subscription Product', 
                                            related='product_tmpl_id.is_subscription_product', 
                                            readonly=True)
    product_class = fields.Selection(related='product_tmpl_id.product_class', readonly=True)
    member_type_id = fields.Many2one('ams.member.type', 'Associated Member Type',
                                   related='product_tmpl_id.member_type_id', readonly=True)
    recurrence_period = fields.Selection(related='product_tmpl_id.recurrence_period', readonly=True)
    membership_period_type = fields.Selection(related='product_tmpl_id.membership_period_type', readonly=True)
    membership_duration = fields.Integer('Membership Duration (Days)', 
                                       related='product_tmpl_id.membership_duration', readonly=True)
    enable_prorating = fields.Boolean('Enable Pro-rating', 
                                     related='product_tmpl_id.enable_prorating', readonly=True)
    auto_renewal_eligible = fields.Boolean('Auto Renewal Eligible', 
                                         related='product_tmpl_id.auto_renewal_eligible', readonly=True)
    allow_multiple_active = fields.Boolean('Allow Multiple Active', 
                                         related='product_tmpl_id.allow_multiple_active', readonly=True)
    requires_approval = fields.Boolean('Requires Approval', 
                                     related='product_tmpl_id.requires_approval', readonly=True)
    member_only = fields.Boolean('Member Only', 
                                related='product_tmpl_id.member_only', readonly=True)
    guest_purchase_allowed = fields.Boolean('Guest Purchase Allowed', 
                                          related='product_tmpl_id.guest_purchase_allowed', readonly=True)
    membership_model = fields.Selection(related='product_tmpl_id.membership_model', readonly=True)
    create_membership_record = fields.Boolean('Create Membership Record', 
                                            related='product_tmpl_id.create_membership_record', readonly=True)