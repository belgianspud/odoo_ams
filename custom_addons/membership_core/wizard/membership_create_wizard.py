# -*- coding: utf-8 -*-
# Part of Association Management Software (AMS)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)

class MembershipCreateWizard(models.TransientModel):
    _name = 'membership.create.wizard'
    _description = 'Create Membership Wizard'

    # Partner selection
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        help='Partner who will receive the membership'
    )
    
    is_new_partner = fields.Boolean(
        string='Create New Partner',
        default=False,
        help='Check to create a new partner'
    )
    
    # New partner fields
    partner_name = fields.Char(
        string='Name',
        help='Name for new partner'
    )
    
    partner_email = fields.Char(
        string='Email',
        help='Email for new partner'
    )
    
    partner_phone = fields.Char(
        string='Phone',
        help='Phone for new partner'
    )
    
    partner_is_company = fields.Boolean(
        string='Is a Company',
        default=False,
        help='Check if new partner is a company'
    )
    
    # Membership configuration
    membership_type_id = fields.Many2one(
        'membership.type',
        string='Membership Type',
        required=True,
        domain="[('active', '=', True)]",
        help='Type of membership to create'
    )
    
    membership_category = fields.Selection(
        related='membership_type_id.membership_category',
        string='Category',
        readonly=True
    )
    
    # Date configuration
    start_date = fields.Date(
        string='Start Date',
        default=fields.Date.today,
        required=True,
        help='Membership start date'
    )
    
    custom_end_date = fields.Boolean(
        string='Custom End Date',
        default=False,
        help='Set a custom end date instead of using membership type duration'
    )
    
    end_date = fields.Date(
        string='End Date',
        help='Custom membership end date'
    )
    
    calculated_end_date = fields.Date(
        string='Calculated End Date',
        compute='_compute_calculated_end_date',
        help='Automatically calculated end date based on membership type'
    )
    
    # Financial information
    amount_paid = fields.Float(
        string='Amount Paid',
        digits='Product Price',
        help='Amount already paid for this membership'
    )
    
    price = fields.Float(
        related='membership_type_id.price',
        string='Membership Price',
        readonly=True
    )
    
    currency_id = fields.Many2one(
        related='membership_type_id.currency_id',
        readonly=True
    )
    
    # Additional options
    auto_activate = fields.Boolean(
        string='Activate Immediately',
        default=True,
        help='Automatically activate membership after creation'
    )
    
    send_welcome_email = fields.Boolean(
        string='Send Welcome Email',
        default=True,
        help='Send welcome email after activation'
    )
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes for this membership'
    )
    
    # Validation fields
    has_conflicting_membership = fields.Boolean(
        string='Has Conflicting Membership',
        compute='_compute_validation_info',
        help='True if partner already has a conflicting membership'
    )
    
    conflicting_membership_id = fields.Many2one(
        'membership.membership',
        string='Conflicting Membership',
        compute='_compute_validation_info'
    )
    
    validation_message = fields.Text(
        string='Validation Message',
        compute='_compute_validation_info'
    )
    
    @api.depends('start_date', 'membership_type_id.duration', 'custom_end_date')
    def _compute_calculated_end_date(self):
        for wizard in self:
            if wizard.start_date and wizard.membership_type_id:
                if wizard.membership_type_id.is_lifetime or wizard.membership_type_id.duration == 0:
                    wizard.calculated_end_date = False
                else:
                    wizard.calculated_end_date = wizard.start_date + relativedelta(months=wizard.membership_type_id.duration)
            else:
                wizard.calculated_end_date = False
    
    @api.depends('partner_id', 'membership_type_id', 'start_date')
    def _compute_validation_info(self):
        for wizard in self:
            wizard.has_conflicting_membership = False
            wizard.conflicting_membership_id = False
            wizard.validation_message = ""
            
            if wizard.partner_id and wizard.membership_type_id:
                # Check for parent membership conflicts
                if wizard.membership_type_id.membership_category in ['individual', 'organization']:
                    existing_parent = self.env['membership.membership'].search([
                        ('partner_id', '=', wizard.partner_id.id),
                        ('state', 'in', ['active', 'grace']),
                        ('membership_type_id.membership_category', 'in', ['individual', 'organization'])
                    ], limit=1)
                    
                    if existing_parent:
                        wizard.has_conflicting_membership = True
                        wizard.conflicting_membership_id = existing_parent.id
                        wizard.validation_message = _(
                            "Partner already has an active parent membership (%s). "
                            "Only one parent membership is allowed per partner."
                        ) % existing_parent.membership_type_id.name
                
                # Check for duplicate memberships of same type
                existing_same_type = self.env['membership.membership'].search([
                    ('partner_id', '=', wizard.partner_id.id),
                    ('membership_type_id', '=', wizard.membership_type_id.id),
                    ('state', 'in', ['active', 'grace'])
                ], limit=1)
                
                if existing_same_type:
                    wizard.has_conflicting_membership = True
                    wizard.conflicting_membership_id = existing_same_type.id
                    wizard.validation_message = _(
                        "Partner already has an active membership of this type (%s)."
                    ) % existing_same_type.name
    
    @api.onchange('membership_type_id')
    def _onchange_membership_type(self):
        """Update amount paid when membership type changes"""
        if self.membership_type_id:
            self.amount_paid = self.membership_type_id.price
    
    @api.onchange('is_new_partner')
    def _onchange_is_new_partner(self):
        """Clear partner when switching to new partner mode"""
        if self.is_new_partner:
            self.partner_id = False
        else:
            self.partner_name = ""
            self.partner_email = ""
            self.partner_phone = ""
            self.partner_is_company = False
    
    @api.onchange('partner_is_company', 'membership_type_id')
    def _onchange_partner_company_type_validation(self):
        """Validate partner type against membership category"""
        if self.partner_is_company and self.membership_type_id:
            if self.membership_type_id.membership_category == 'individual':
                return {
                    'warning': {
                        'title': _('Membership Type Mismatch'),
                        'message': _('You selected an individual membership type for a company. '
                                   'Consider selecting an organization membership type instead.')
                    }
                }
        elif not self.partner_is_company and self.membership_type_id:
            if self.membership_type_id.membership_category == 'organization':
                return {
                    'warning': {
                        'title': _('Membership Type Mismatch'),
                        'message': _('You selected an organization membership type for an individual. '
                                   'Consider selecting an individual membership type instead.')
                    }
                }
    
    def action_create_membership(self):
        """Create the membership record"""
        self.ensure_one()
        
        # Validate required fields
        if self.is_new_partner:
            if not self.partner_name:
                raise ValidationError(_("Partner name is required when creating a new partner."))
            partner = self._create_partner()
        else:
            if not self.partner_id:
                raise ValidationError(_("Please select a partner or choose to create a new one."))
            partner = self.partner_id
        
        # Check for conflicts one more time
        if self.has_conflicting_membership:
            raise ValidationError(self.validation_message)
        
        # Determine end date
        if self.custom_end_date and self.end_date:
            end_date = self.end_date
        else:
            end_date = self.calculated_end_date
        
        # Create membership
        membership_vals = {
            'partner_id': partner.id,
            'membership_type_id': self.membership_type_id.id,
            'start_date': self.start_date,
            'end_date': end_date,
            'amount_paid': self.amount_paid,
            'notes': self.notes,
            'state': 'draft'
        }
        
        membership = self.env['membership.membership'].create(membership_vals)
        
        # Auto-activate if requested
        if self.auto_activate:
            membership.action_activate()
            
            # Send welcome email if requested and template exists
            if (self.send_welcome_email and 
                membership.membership_type_id.welcome_template_id and
                membership.state == 'active'):
                try:
                    membership.membership_type_id.welcome_template_id.send_mail(membership.id)
                except Exception as e:
                    # Log warning but don't fail the process
                    _logger.warning(f"Failed to send welcome email for membership {membership.name}: {str(e)}")
        
        # Return action to view the created membership
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Created'),
            'res_model': 'membership.membership',
            'res_id': membership.id,
            'view_mode': 'form',
            'target': 'current'
        }
    
    def _create_partner(self):
        """Create new partner from wizard data"""
        partner_vals = {
            'name': self.partner_name,
            'email': self.partner_email,
            'phone': self.partner_phone,
            'is_company': self.partner_is_company,
            'customer_rank': 1,
            'supplier_rank': 0
        }
        
        return self.env['res.partner'].create(partner_vals)
    
    def action_view_conflicting_membership(self):
        """View the conflicting membership"""
        self.ensure_one()
        if not self.conflicting_membership_id:
            raise UserError(_("No conflicting membership found."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Conflicting Membership'),
            'res_model': 'membership.membership',
            'res_id': self.conflicting_membership_id.id,
            'view_mode': 'form',
            'target': 'new'
        }
    
    def action_override_conflict(self):
        """Override conflict and create anyway (for managers)"""
        self.ensure_one()
        
        # Check permissions
        if not self.env.user.has_group('membership_core.group_membership_manager'):
            raise ValidationError(_("Only membership managers can override conflicts."))
        
        # Temporarily disable conflict checking
        self = self.with_context(skip_conflict_check=True)
        return self.action_create_membership()


class MembershipCreateWizardLine(models.TransientModel):
    _name = 'membership.create.wizard.line'
    _description = 'Create Membership Wizard Line'
    
    wizard_id = fields.Many2one(
        'membership.create.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True
    )
    
    membership_type_id = fields.Many2one(
        'membership.type',
        string='Membership Type',
        required=True
    )
    
    amount_paid = fields.Float(
        string='Amount Paid',
        digits='Product Price'
    )
    
    notes = fields.Text(
        string='Notes'
    )