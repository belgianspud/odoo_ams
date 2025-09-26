# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Membership-related fields
    contains_memberships = fields.Boolean('Contains Memberships', compute='_compute_contains_memberships', store=True)
    membership_ids = fields.One2many('ams.membership.base', 'invoice_id', 'Memberships')
    membership_count = fields.Integer('Membership Count', compute='_compute_membership_count')
    
    # Auto-create settings
    auto_create_memberships = fields.Boolean('Auto Create Memberships', default=True,
                                           help="Automatically create membership records when invoice is paid")

    @api.depends('invoice_line_ids.product_id')
    def _compute_contains_memberships(self):
        """Check if invoice contains subscription products"""
        for move in self:
            has_subscriptions = any(
                line.product_id.product_tmpl_id.is_subscription_product 
                for line in move.invoice_line_ids
            )
            move.contains_memberships = has_subscriptions

    def _compute_membership_count(self):
        """Count related membership records"""
        for move in self:
            move.membership_count = len(move.membership_ids)

    def action_post(self):
        """Override to create memberships when invoice is posted and paid"""
        result = super().action_post()
        
        # Check if invoice is immediately paid (e.g., from online payment)
        for move in self:
            if move.payment_state == 'paid' and move.contains_memberships:
                move._create_membership_records()
        
        return result

    def _create_membership_records(self):
        """Create membership records for subscription products"""
        self.ensure_one()
        
        if not self.auto_create_memberships:
            return
        
        if self.move_type != 'out_invoice':
            return
        
        if self.state != 'posted' or self.payment_state != 'paid':
            return
        
        created_memberships = []
        
        for line in self.invoice_line_ids:
            if not line.product_id.product_tmpl_id.is_subscription_product:
                continue
            
            if not line.product_id.product_tmpl_id.create_membership_record:
                continue
            
            # Check if membership already exists for this line
            existing = self.env['ams.membership.base'].search([
                ('invoice_line_id', '=', line.id)
            ])
            
            if existing:
                continue
            
            # Create membership record
            try:
                membership = line.product_id.product_tmpl_id.create_membership_record(
                    partner=self.partner_id,
                    invoice_line=line,
                    start_date=self.invoice_date or fields.Date.today()
                )
                
                if membership:
                    created_memberships.append(membership)
                    
            except Exception as e:
                _logger.error(f"Failed to create membership for invoice line {line.id}: {str(e)}")
                continue
        
        if created_memberships:
            # Log membership creation
            membership_names = [m.name for m in created_memberships]
            self.message_post(
                body=_("Membership records created: %s") % ', '.join(membership_names),
                message_type='notification'
            )

    def action_view_memberships(self):
        """View related memberships"""
        self.ensure_one()
        
        if not self.membership_ids:
            raise UserError(_("No membership records found for this invoice."))
        
        return {
            'name': _('Memberships from Invoice %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.membership.base',
            'view_mode': 'list,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {
                'default_invoice_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_create_memberships_manually(self):
        """Manually create membership records"""
        self.ensure_one()
        
        if not self.contains_memberships:
            raise UserError(_("This invoice does not contain subscription products."))
        
        if self.state != 'posted':
            raise UserError(_("Invoice must be posted to create memberships."))
        
        # Create memberships regardless of payment status
        self._create_membership_records()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Memberships Created'),
                'message': _('Membership records have been created for subscription products.'),
                'type': 'success'
            }
        }

    def action_membership_upgrade_wizard(self):
        """Open membership upgrade wizard for existing memberships"""
        self.ensure_one()
        
        # Find existing active memberships for this partner
        existing_memberships = self.env['ams.membership.base'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['active', 'grace'])
        ])
        
        if not existing_memberships:
            raise UserError(_("No active memberships found for this member."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Upgrade'),
            'res_model': 'ams.membership.upgrade.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_invoice_id': self.id,
                'existing_membership_ids': existing_memberships.ids,
            }
        }

    # Override payment registration to trigger membership creation
    def _get_reconciled_info_JSON_values(self):
        """Override to check for membership creation after payment"""
        result = super()._get_reconciled_info_JSON_values()
        
        # Check if we need to create memberships after payment
        if self.payment_state == 'paid' and self.contains_memberships:
            if not self.membership_ids and self.auto_create_memberships:
                self._create_membership_records()
        
        return result


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Membership-related fields
    is_subscription_line = fields.Boolean('Is Subscription Line', 
                                        compute='_compute_is_subscription_line', store=True)
    membership_id = fields.Many2one('ams.membership.base', 'Related Membership', readonly=True)
    membership_start_date = fields.Date('Membership Start Date')
    membership_end_date = fields.Date('Membership End Date')
    
    # Pro-rating fields
    is_prorated = fields.Boolean('Is Pro-rated', default=False)
    original_price = fields.Float('Original Price')
    proration_factor = fields.Float('Pro-ration Factor', default=1.0)
    proration_period = fields.Char('Pro-ration Period')

    @api.depends('product_id')
    def _compute_is_subscription_line(self):
        """Check if line contains subscription product"""
        for line in self:
            line.is_subscription_line = (
                line.product_id and 
                line.product_id.product_tmpl_id.is_subscription_product
            )

    @api.onchange('product_id', 'membership_start_date')
    def _onchange_product_membership_dates(self):
        """Calculate membership dates and pro-rating when product changes"""
        if self.is_subscription_line and self.product_id:
            product_tmpl = self.product_id.product_tmpl_id
            
            # Set default start date
            if not self.membership_start_date:
                self.membership_start_date = fields.Date.today()
            
            # Calculate end date
            self.membership_end_date = product_tmpl.calculate_membership_end_date(
                self.membership_start_date
            )
            
            # Calculate pro-rated price if enabled
            if product_tmpl.enable_prorating:
                prorated_price = product_tmpl.calculate_prorated_price(
                    self.membership_start_date,
                    self.membership_end_date
                )
                
                if prorated_price != product_tmpl.list_price:
                    self.is_prorated = True
                    self.original_price = product_tmpl.list_price
                    self.price_unit = prorated_price
                    self.proration_factor = prorated_price / product_tmpl.list_price if product_tmpl.list_price > 0 else 1.0
                    
                    # Set proration period description
                    period_days = (self.membership_end_date - self.membership_start_date).days
                    total_days = product_tmpl.membership_duration
                    self.proration_period = _("%(period_days)d of %(total_days)d days") % {
                        'period_days': period_days,
                        'total_days': total_days
                    }

    def create_membership_record(self):
        """Create membership record for this invoice line"""
        self.ensure_one()
        
        if not self.is_subscription_line:
            raise UserError(_("This line does not contain a subscription product."))
        
        if self.membership_id:
            raise UserError(_("Membership record already exists for this line."))
        
        if self.move_id.state != 'posted':
            raise UserError(_("Invoice must be posted to create membership."))
        
        # Create membership using product template method
        membership = self.product_id.product_tmpl_id.create_membership_record(
            partner=self.move_id.partner_id,
            invoice_line=self,
            start_date=self.membership_start_date or fields.Date.today()
        )
        
        if membership:
            self.membership_id = membership.id
            return membership
        else:
            raise UserError(_("Failed to create membership record."))

    def action_view_membership(self):
        """View related membership record"""
        self.ensure_one()
        
        if not self.membership_id:
            raise UserError(_("No membership record linked to this line."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Record'),
            'res_model': self.membership_id._name,
            'res_id': self.membership_id.id,
            'view_mode': 'form',
        }

    def get_membership_description(self):
        """Get formatted description of membership terms"""
        self.ensure_one()
        
        if not self.is_subscription_line:
            return ""
        
        description_parts = []
        
        # Add membership period
        if self.membership_start_date and self.membership_end_date:
            description_parts.append(
                _("Membership Period: %s to %s") % (
                    self.membership_start_date.strftime('%m/%d/%Y'),
                    self.membership_end_date.strftime('%m/%d/%Y')
                )
            )
        
        # Add pro-ration info
        if self.is_prorated:
            description_parts.append(
                _("Pro-rated: %s (%.1f%%)") % (
                    self.proration_period,
                    self.proration_factor * 100
                )
            )
        
        # Add auto-renewal info
        product_tmpl = self.product_id.product_tmpl_id
        if product_tmpl.auto_renewal_eligible:
            description_parts.append(_("Auto-renewal eligible"))
        
        return "\n".join(description_parts)

    # Constraints
    @api.constrains('membership_start_date', 'membership_end_date')
    def _check_membership_dates(self):
        """Validate membership dates"""
        for line in self.filtered('is_subscription_line'):
            if line.membership_start_date and line.membership_end_date:
                if line.membership_end_date <= line.membership_start_date:
                    raise ValidationError(_("Membership end date must be after start date."))

    @api.constrains('proration_factor')
    def _check_proration_factor(self):
        """Validate pro-ration factor"""
        for line in self:
            if line.is_prorated and (line.proration_factor <= 0 or line.proration_factor > 1):
                raise ValidationError(_("Pro-ration factor must be between 0 and 1."))

    @api.constrains('original_price')
    def _check_original_price(self):
        """Validate original price"""
        for line in self:
            if line.is_prorated and line.original_price <= 0:
                raise ValidationError(_("Original price must be positive for pro-rated lines."))