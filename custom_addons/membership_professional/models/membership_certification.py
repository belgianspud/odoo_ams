# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MembershipCertification(models.Model):
    """
    Board Certifications & Professional Certifications
    Similar to credentials but specifically for board certifications
    """
    _name = 'membership.certification'
    _description = 'Professional Certification'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Certification Name',
        required=True,
        translate=True,
        tracking=True,
        help='Full certification name (e.g., Board Certified in Internal Medicine)'
    )
    
    code = fields.Char(
        string='Code',
        required=True,
        help='Certification code or abbreviation'
    )
    
    active = fields.Boolean(
        default=True,
        help='Inactive certifications are hidden'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    description = fields.Text(
        string='Description',
        translate=True
    )
    
    color = fields.Integer(string='Color')

    # Certification Details
    certification_type = fields.Selection([
        ('board', 'Board Certification'),
        ('professional', 'Professional Certification'),
        ('specialist', 'Specialist Certification'),
        ('fellowship', 'Fellowship'),
    ], string='Type',
       required=True,
       default='board')
    
    issuing_board = fields.Char(
        string='Issuing Board/Organization',
        help='Organization that issues this certification'
    )
    
    requires_recertification = fields.Boolean(
        string='Requires Recertification',
        default=True,
        help='Must be renewed/recertified periodically'
    )
    
    recertification_period_years = fields.Integer(
        string='Recertification Period (Years)',
        default=10,
        help='Years between recertification'
    )
    
    requires_continuing_education = fields.Boolean(
        string='Requires CE',
        default=True
    )
    
    ce_hours_required = fields.Float(
        string='CE Hours Required',
        help='CE hours required per recertification period'
    )

    # Relations
    partner_ids = fields.Many2many(
        'res.partner',
        'partner_certification_rel',
        'certification_id',
        'partner_id',
        string='Certified Members'
    )
    
    member_count = fields.Integer(
        string='Member Count',
        compute='_compute_member_count'
    )

    @api.depends('partner_ids')
    def _compute_member_count(self):
        for cert in self:
            cert.member_count = len(cert.partner_ids)

    def action_view_members(self):
        """View members with this certification"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Certified Members - %s') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('certification_ids', 'in', [self.id])],
        }

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Certification code must be unique!'),
    ]