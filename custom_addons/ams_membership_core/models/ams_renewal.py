# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AMSRenewal(models.Model):
    _name = 'ams.renewal'
    _description = 'Membership/Subscription Renewal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'renewal_date desc, id desc'
    _rec_name = 'display_name'

    # Core Fields
    name = fields.Char('Renewal Reference', required=True, copy=False, readonly=True,
                      default=lambda self: _('New'))
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    
    # Related Records
    membership_id = fields.Many2one('ams.membership', 'Membership', ondelete='cascade')
    subscription_id = fields.Many2one('ams.subscription', 'Subscription', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Member/Subscriber', 
                                compute='_compute_partner_id', store=True)
    
    # Enhanced Chapter Support
    is_chapter_renewal = fields.Boolean('Chapter Renewal', 
                                       compute='_compute_chapter_info', store=True)
    chapter_type = fields.Selection([
        ('local', 'Local Chapter'),
        ('regional', 'Regional Chapter'),
        ('state', 'State Chapter'),
        ('national', 'National Chapter'),
        ('international', 'International Chapter'),
        ('special', 'Special Interest Chapter'),
        ('student', 'Student Chapter'),
        ('professional', 'Professional Chapter'),
    ], string='Chapter Type', compute='_compute_chapter_info', store=True)
    chapter_location = fields.Char('Chapter Location', compute='_compute_chapter_info', store=True)
    
    # Renewal Details
    renewal_date = fields.Date('Renewal Date', required=True, default=fields.Date.today, tracking=True)
    previous_end_date = fields.Date('Previous End Date', compute='_compute_previous_dates', store=True)
    new_end_date = fields.Date('New End Date', required=True, tracking=True)
    
    # Enhanced Renewal Configuration with Chapter Support
    renewal_type = fields.Selection([
        ('manual', 'Manual Renewal'),
        ('automatic', 'Automatic Renewal'),
        ('early', 'Early Renewal'),
        ('late', 'Late Renewal'),
        ('grace', 'Grace Period Renewal'),
        ('chapter_bulk', 'Chapter Bulk Renewal'),  # NEW: Bulk renewal for chapters
        ('chapter_transfer', 'Chapter Transfer'),  # NEW: Transfer between chapters
    ], string='Renewal Type', default='manual', required=True, tracking=True)
    
    renewal_period = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('chapter_term', 'Chapter Term'),  # NEW: Chapter-specific terms
    ], string='Renewal Period', default='annual', required=True)
    
    # Chapter-Specific Renewal Settings
    maintains_chapter_role = fields.Boolean('Maintains Chapter Role',
                                          help='Member maintains their chapter role/position')
    chapter_role_change = fields.Selection([
        ('no_change', 'No Change'),
        ('promote', 'Promotion'),
        ('demote', 'Demotion'),
        ('transfer', 'Role Transfer'),
    ], string='Chapter Role Change', default='no_change')
    
    new_chapter_role = fields.Selection([
        ('member', 'Member'),
        ('volunteer', 'Volunteer'),
        ('committee_member', 'Committee Member'),
        ('officer', 'Officer'),
        ('board_member', 'Board Member'),
        ('president', 'President'),
        ('vice_president', 'Vice President'),
        ('secretary', 'Secretary'),
        ('treasurer', 'Treasurer'),
    ], string='New Chapter Role')
    
    # Financial Information
    amount = fields.Monetary('Renewal Amount', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                 default=lambda self: self.env.company.currency_id)
    original_amount = fields.Monetary('Original Amount', currency_field='currency_id',
                                     help='Amount before any discounts or prorations')
    discount_amount = fields.Monetary('Discount Amount', currency_field='currency_id', default=0.0)
    proration_amount = fields.Monetary('Proration Amount', currency_field='currency_id', default=0.0,
                                      help='Positive for additional charge, negative for credit')
    
    # Enhanced Chapter Discounts
    chapter_loyalty_discount = fields.Monetary('Chapter Loyalty Discount', currency_field='currency_id', default=0.0,
                                              help='Discount for long-term chapter membership')
    multi_chapter_discount = fields.Monetary('Multi-Chapter Discount', currency_field='currency_id', default=0.0,
                                            help='Discount for members of multiple chapters')
    early_chapter_renewal_discount = fields.Monetary('Early Chapter Renewal Discount', 
                                                    currency_field='currency_id', default=0.0,
                                                    help='Discount for renewing chapter membership early')
    
    # Payment Integration
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', readonly=True)
    invoice_id = fields.Many2one('account.move', 'Invoice', readonly=True)
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
    ], string='Payment Status', compute='_compute_payment_state', store=True)
    
    # Status Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Enhanced Renewal Analysis with Chapter Support
    is_early_renewal = fields.Boolean('Early Renewal', compute='_compute_renewal_analysis', store=True)
    is_late_renewal = fields.Boolean('Late Renewal', compute='_compute_renewal_analysis', store=True)
    days_early = fields.Integer('Days Early', compute='_compute_renewal_analysis', store=True)
    days_late = fields.Integer('Days Late', compute='_compute_renewal_analysis', store=True)
    
    # Chapter-Specific Analysis
    years_in_chapter = fields.Float('Years in Chapter', compute='_compute_chapter_analysis', store=True)
    is_chapter_transfer = fields.Boolean('Is Chapter Transfer', 
                                        compute='_compute_chapter_analysis', store=True)
    previous_chapter_id = fields.Many2one('product.template', 'Previous Chapter',
                                         domain=[('subscription_product_type', '=', 'chapter')])
    
    # Revenue Recognition (placeholder for future billing integration)
    revenue_recognition_date = fields.Date('Revenue Recognition Date')
    deferred_revenue_amount = fields.Monetary('Deferred Revenue', currency_field='currency_id')
    
    # Additional Information
    notes = fields.Text('Notes')
    renewal_reason = fields.Text('Renewal Reason/Comments')
    
    # Chapter-Specific Information
    chapter_notes = fields.Text('Chapter-Specific Notes',
                               help='Notes specific to chapter membership renewal')
    chapter_committee_continuity = fields.Text('Committee Continuity',
                                              help='Information about committee role continuity')

    @api.depends('membership_id', 'subscription_id', 'is_chapter_renewal')
    def _compute_display_name(self):
        for renewal in self:
            if renewal.membership_id:
                prefix = "Chapter " if renewal.is_chapter_renewal else ""
                renewal.display_name = f"{prefix}Membership Renewal - {renewal.membership_id.display_name}"
            elif renewal.subscription_id:
                renewal.display_name = f"Subscription Renewal - {renewal.subscription_id.display_name}"
            else:
                renewal.display_name = renewal.name or _('New Renewal')
    
    @api.depends('membership_id.partner_id', 'subscription_id.partner_id')
    def _compute_partner_id(self):
        for renewal in self:
            if renewal.membership_id:
                renewal.partner_id = renewal.membership_id.partner_id
            elif renewal.subscription_id:
                renewal.partner_id = renewal.subscription_id.partner_id
            else:
                renewal.partner_id = False
    
    @api.depends('membership_id.end_date', 'subscription_id.end_date')
    def _compute_previous_dates(self):
        for renewal in self:
            if renewal.membership_id:
                renewal.previous_end_date = renewal.membership_id.end_date
            elif renewal.subscription_id:
                renewal.previous_end_date = renewal.subscription_id.end_date
            else:
                renewal.previous_end_date = False
    
    @api.depends('membership_id.is_chapter_membership', 'membership_id.chapter_type', 'membership_id.chapter_location')
    def _compute_chapter_info(self):
        for renewal in self:
            if renewal.membership_id and renewal.membership_id.is_chapter_membership:
                renewal.is_chapter_renewal = True
                renewal.chapter_type = renewal.membership_id.chapter_type
                renewal.chapter_location = renewal.membership_id.chapter_location
            else:
                renewal.is_chapter_renewal = False
                renewal.chapter_type = False
                renewal.chapter_location = False
    
    @api.depends('membership_id.start_date', 'previous_chapter_id')
    def _compute_chapter_analysis(self):
        for renewal in self:
            if renewal.is_chapter_renewal and renewal.membership_id:
                # Calculate years in chapter
                if renewal.membership_id.start_date:
                    days_in_chapter = (fields.Date.today() - renewal.membership_id.start_date).days
                    renewal.years_in_chapter = days_in_chapter / 365.25
                else:
                    renewal.years_in_chapter = 0.0
                
                # Check if this is a chapter transfer
                renewal.is_chapter_transfer = bool(renewal.previous_chapter_id and 
                                                 renewal.previous_chapter_id != renewal.membership_id.product_id.product_tmpl_id)
            else:
                renewal.years_in_chapter = 0.0
                renewal.is_chapter_transfer = False
    
    @api.depends('invoice_id.payment_state')
    def _compute_payment_state(self):
        for renewal in self:
            if renewal.invoice_id:
                renewal.payment_state = renewal.invoice_id.payment_state
            else:
                renewal.payment_state = 'not_paid'
    
    @api.depends('renewal_date', 'previous_end_date')
    def _compute_renewal_analysis(self):
        for renewal in self:
            if not renewal.previous_end_date or not renewal.renewal_date:
                renewal.is_early_renewal = False
                renewal.is_late_renewal = False
                renewal.days_early = 0
                renewal.days_late = 0
                continue
            
            days_diff = (renewal.renewal_date - renewal.previous_end_date).days
            
            if days_diff < 0:  # Renewed before expiration
                renewal.is_early_renewal = True
                renewal.is_late_renewal = False
                renewal.days_early = abs(days_diff)
                renewal.days_late = 0
            elif days_diff > 0:  # Renewed after expiration
                renewal.is_early_renewal = False
                renewal.is_late_renewal = True
                renewal.days_early = 0
                renewal.days_late = days_diff
            else:  # Renewed exactly on expiration date
                renewal.is_early_renewal = False
                renewal.is_late_renewal = False
                renewal.days_early = 0
                renewal.days_late = 0

    @api.model
    def create(self, vals):
        """Override create to handle sequence and setup"""
        if vals.get('name', _('New')) == _('New'):
            # Use different sequences for different renewal types
            if vals.get('membership_id'):
                membership = self.env['ams.membership'].browse(vals['membership_id'])
                if membership.is_chapter_membership:
                    sequence_code = 'ams.renewal.chapter'
                else:
                    sequence_code = 'ams.renewal.membership'
            else:
                sequence_code = 'ams.renewal.subscription'
            
            vals['name'] = self.env['ir.sequence'].next_by_code(sequence_code) or self.env['ir.sequence'].next_by_code('ams.renewal') or _('New')
        
        renewal = super().create(vals)
        
        # Auto-calculate amounts if not provided
        if not vals.get('original_amount'):
            renewal._calculate_renewal_amounts()
        
        return renewal
    
    def write(self, vals):
        """Override write to handle state changes"""
        result = super().write(vals)
        
        # Handle state changes
        if 'state' in vals:
            for renewal in self:
                renewal._handle_state_change(vals['state'])
        
        return result
    
    def _handle_state_change(self, new_state):
        """Enhanced renewal state change handling with chapter support"""
        self.ensure_one()
        
        if new_state == 'confirmed':
            # Apply the renewal to the membership/subscription
            self._apply_renewal()
        elif new_state == 'cancelled':
            # Handle cancellation logic
            self._handle_renewal_cancellation()
    
    def _apply_renewal(self):
        """Enhanced renewal application with chapter support"""
        self.ensure_one()
        
        if self.membership_id:
            # Standard renewal application
            renewal_vals = {
                'end_date': self.new_end_date,
                'last_renewal_date': self.renewal_date,
                'state': 'active',  # Reactivate if was in grace/suspended
            }
            
            # Apply chapter-specific changes
            if self.is_chapter_renewal:
                # Handle chapter role changes
                if self.chapter_role_change != 'no_change' and self.new_chapter_role:
                    renewal_vals['chapter_role'] = self.new_chapter_role
                    renewal_vals['chapter_position_start_date'] = self.renewal_date
                
                # Add chapter renewal notes
                if self.chapter_notes:
                    current_notes = self.membership_id.notes or ''
                    renewal_vals['notes'] = f"{current_notes}\n\nChapter Renewal {self.renewal_date}: {self.chapter_notes}"
            
            self.membership_id.write(renewal_vals)
            
            # Log chapter-specific renewal information
            if self.is_chapter_renewal:
                msg_body = f"Chapter membership renewed until {self.new_end_date}"
                if self.chapter_role_change != 'no_change':
                    msg_body += f" with role change to {self.new_chapter_role}"
                
                self.membership_id.message_post(
                    body=msg_body,
                    subject="Chapter Membership Renewed"
                )
            
            _logger.info(f"Applied renewal to membership {self.membership_id.name}")
        
        elif self.subscription_id:
            self.subscription_id.write({
                'end_date': self.new_end_date,
                'last_renewal_date': self.renewal_date,
                'state': 'active',  # Reactivate if was in grace/suspended
            })
            _logger.info(f"Applied renewal to subscription {self.subscription_id.name}")
    
    def _handle_renewal_cancellation(self):
        """Handle renewal cancellation"""
        self.ensure_one()
        
        # Cancel related sale order if exists
        if self.sale_order_id and self.sale_order_id.state not in ['sale', 'done']:
            try:
                self.sale_order_id.action_cancel()
            except Exception as e:
                _logger.warning(f"Could not cancel sale order {self.sale_order_id.name}: {str(e)}")
        
        # Cancel related invoice if exists and not paid
        if self.invoice_id and self.invoice_id.payment_state == 'not_paid':
            try:
                self.invoice_id.button_cancel()
            except Exception as e:
                _logger.warning(f"Could not cancel invoice {self.invoice_id.name}: {str(e)}")
    
    def _calculate_renewal_amounts(self):
        """Enhanced renewal amount calculation with chapter discounts"""
        self.ensure_one()
        
        base_amount = 0.0
        
        if self.membership_id:
            base_amount = self.membership_id.membership_fee
        elif self.subscription_id:
            base_amount = self.subscription_id.subscription_fee
        
        # Apply standard discounts
        discount = 0.0
        
        # Early renewal discounts
        if self.is_early_renewal:
            discount += self._calculate_early_renewal_discount(base_amount)
        
        # Chapter-specific discounts
        if self.is_chapter_renewal:
            discount += self._calculate_chapter_discounts(base_amount)
        
        # Calculate proration if applicable
        proration = self._calculate_proration_amount(base_amount)
        
        # Set amounts
        self.original_amount = base_amount
        self.discount_amount = discount
        self.proration_amount = proration
        self.amount = base_amount - discount + proration
    
    def _calculate_early_renewal_discount(self, base_amount):
        """Calculate early renewal discount"""
        self.ensure_one()
        
        if not self.is_early_renewal:
            return 0.0
        
        # Enhanced discount rates for chapters
        if self.is_chapter_renewal:
            if self.days_early >= 90:  # 3+ months early for chapters
                return base_amount * 0.08  # 8% discount for chapters
            elif self.days_early >= 60:  # 2+ months early for chapters
                return base_amount * 0.05  # 5% discount for chapters
            elif self.days_early >= 30:  # 1+ month early for chapters
                return base_amount * 0.03  # 3% discount for chapters
        else:
            # Standard early renewal discounts
            if self.days_early >= 60:  # 2+ months early
                return base_amount * 0.05  # 5% discount
            elif self.days_early >= 30:  # 1+ month early
                return base_amount * 0.025  # 2.5% discount
        
        return 0.0
    
    def _calculate_chapter_discounts(self, base_amount):
        """Calculate chapter-specific discounts"""
        self.ensure_one()
        
        if not self.is_chapter_renewal:
            return 0.0
        
        total_discount = 0.0
        
        # Chapter loyalty discount (based on years in chapter)
        if self.years_in_chapter >= 10:
            loyalty_discount = base_amount * 0.15  # 15% for 10+ years
        elif self.years_in_chapter >= 5:
            loyalty_discount = base_amount * 0.10  # 10% for 5+ years
        elif self.years_in_chapter >= 3:
            loyalty_discount = base_amount * 0.05  # 5% for 3+ years
        else:
            loyalty_discount = 0.0
        
        self.chapter_loyalty_discount = loyalty_discount
        total_discount += loyalty_discount
        
        # Multi-chapter discount (if member has other chapter memberships)
        other_chapters = self.env['ams.membership'].search([
            ('partner_id', '=', self.partner_id.id),
            ('is_chapter_membership', '=', True),
            ('state', '=', 'active'),
            ('id', '!=', self.membership_id.id)
        ])
        
        if len(other_chapters) >= 2:
            multi_discount = base_amount * 0.10  # 10% for 3+ chapters
        elif len(other_chapters) >= 1:
            multi_discount = base_amount * 0.05  # 5% for 2+ chapters
        else:
            multi_discount = 0.0
        
        self.multi_chapter_discount = multi_discount
        total_discount += multi_discount
        
        # Early chapter renewal discount (additional to standard early discount)
        if self.is_early_renewal and self.days_early >= 45:
            early_chapter_discount = base_amount * 0.02  # Additional 2% for early chapter renewal
            self.early_chapter_renewal_discount = early_chapter_discount
            total_discount += early_chapter_discount
        
        return total_discount
    
    def _calculate_proration_amount(self, base_amount):
        """Calculate proration amount (placeholder for future implementation)"""
        self.ensure_one()
        
        # TODO: Implement proration logic based on:
        # - Mid-cycle changes
        # - Partial period renewals
        # - Upgrade/downgrade scenarios
        # - Chapter transfers
        
        return 0.0
    
    # Chapter-Specific Action Methods
    def action_chapter_transfer(self):
        """Initiate chapter transfer process"""
        self.ensure_one()
        
        if not self.is_chapter_renewal:
            raise UserError(_("This is not a chapter membership renewal."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Chapter Transfer'),
            'res_model': 'chapter.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_renewal_id': self.id,
                'default_current_chapter_id': self.membership_id.product_id.product_tmpl_id.id,
            }
        }
    
    def action_chapter_role_change(self):
        """Change chapter role during renewal"""
        self.ensure_one()
        
        if not self.is_chapter_renewal:
            raise UserError(_("This is not a chapter membership renewal."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Chapter Role Change'),
            'res_model': 'chapter.role.change.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_renewal_id': self.id,
                'default_current_role': self.membership_id.chapter_role,
            }
        }
    
    # Action Methods
    def action_create_invoice(self):
        """Create invoice for this renewal"""
        self.ensure_one()
        
        if self.invoice_id:
            raise UserError(_("Invoice already exists for this renewal."))
        
        # Create sale order first if it doesn't exist
        if not self.sale_order_id:
            self._create_sale_order()
        
        # Create and post invoice
        invoices = self.sale_order_id._create_invoices()
        if invoices:
            self.invoice_id = invoices[0].id
            self.state = 'pending'
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }
    
    def _create_sale_order(self):
        """Enhanced sale order creation with chapter support"""
        self.ensure_one()
        
        product = None
        if self.membership_id:
            product = self.membership_id.product_id
        elif self.subscription_id:
            product = self.subscription_id.product_id
        
        if not product:
            raise UserError(_("No product found for renewal."))
        
        # Enhanced product name for chapter renewals
        product_name = product.name
        if self.is_chapter_renewal:
            product_name = f"Chapter Renewal: {product.name}"
            if self.chapter_role_change != 'no_change':
                product_name += f" (Role: {self.new_chapter_role})"
        
        # Create sale order
        sale_vals = {
            'partner_id': self.partner_id.id,
            'date_order': self.renewal_date,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': self.amount,
                'name': product_name,
            })],
        }
        
        sale_order = self.env['sale.order'].create(sale_vals)
        self.sale_order_id = sale_order.id
        
        # Confirm the sale order
        sale_order.action_confirm()
        
        return sale_order
    
    def action_confirm(self):
        """Confirm the renewal"""
        for renewal in self:
            if renewal.state != 'draft':
                raise UserError(_("Only draft renewals can be confirmed."))
            
            renewal.write({'state': 'confirmed'})
    
    def action_cancel(self):
        """Cancel the renewal"""
        for renewal in self:
            renewal.write({'state': 'cancelled'})
    
    def action_view_invoice(self):
        """View renewal invoice"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_("No invoice exists for this renewal."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }
    
    def action_view_sale_order(self):
        """View renewal sale order"""
        self.ensure_one()
        
        if not self.sale_order_id:
            raise UserError(_("No sale order exists for this renewal."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Sale Order'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
        }
    
    @api.model
    def generate_renewal_reminders(self):
        """Enhanced renewal reminder generation with chapter support"""
        reminder_days = 30  # TODO: Make configurable
        reminder_date = fields.Date.today() + timedelta(days=reminder_days)
        
        # Find expiring memberships (including chapters)
        expiring_memberships = self.env['ams.membership'].search([
            ('state', '=', 'active'),
            ('end_date', '<=', reminder_date),
            ('auto_renew', '=', False),
            ('renewal_reminder_sent', '=', False),
        ])
        
        # Find expiring subscriptions
        expiring_subscriptions = self.env['ams.subscription'].search([
            ('state', '=', 'active'),
            ('end_date', '<=', reminder_date),
            ('auto_renew', '=', False),
            ('renewal_reminder_sent', '=', False),
        ])
        
        # Create renewal records and send reminders
        for membership in expiring_memberships:
            self._create_renewal_reminder(membership=membership)
        
        for subscription in expiring_subscriptions:
            self._create_renewal_reminder(subscription=subscription)
        
        _logger.info(f"Generated {len(expiring_memberships + expiring_subscriptions)} renewal reminders")
    
    def _create_renewal_reminder(self, membership=None, subscription=None):
        """Enhanced renewal reminder creation with chapter support"""
        vals = {
            'membership_id': membership.id if membership else False,
            'subscription_id': subscription.id if subscription else False,
            'renewal_type': 'manual',
            'state': 'draft',
        }
        
        if membership:
            vals.update({
                'new_end_date': membership._calculate_renewal_end_date(),
                'amount': membership.membership_fee,
            })
            
            # Chapter-specific renewal type
            if membership.is_chapter_membership:
                vals['renewal_type'] = 'chapter_bulk'
            
            membership.renewal_reminder_sent = True
        
        if subscription:
            vals.update({
                'new_end_date': subscription._calculate_renewal_end_date(),
                'amount': subscription.subscription_fee,
            })
            subscription.renewal_reminder_sent = True
        
        renewal = self.create(vals)
        
        # Send appropriate reminder email
        template_ref = 'ams_membership_core.email_chapter_renewal_reminder' if (membership and membership.is_chapter_membership) else 'ams_membership_core.email_membership_renewal_reminder'
        try:
            template = self.env.ref(template_ref, raise_if_not_found=False)
            if template:
                template.send_mail(renewal.id, force_send=True)
        except Exception as e:
            _logger.warning(f"Failed to send renewal reminder: {str(e)}")
        
        return renewal
    
    @api.model
    def process_automatic_renewals(self):
        """Enhanced automatic renewal processing with chapter support"""
        today = fields.Date.today()
        
        # Find auto-renewable memberships that have expired (including chapters)
        auto_memberships = self.env['ams.membership'].search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
            ('auto_renew', '=', True),
        ])
        
        # Find auto-renewable subscriptions that have expired
        auto_subscriptions = self.env['ams.subscription'].search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
            ('auto_renew', '=', True),
        ])
        
        # Process renewals
        for membership in auto_memberships:
            try:
                self._process_automatic_renewal(membership=membership)
            except Exception as e:
                _logger.error(f"Failed to auto-renew membership {membership.name}: {str(e)}")
        
        for subscription in auto_subscriptions:
            try:
                self._process_automatic_renewal(subscription=subscription)
            except Exception as e:
                _logger.error(f"Failed to auto-renew subscription {subscription.name}: {str(e)}")
        
        _logger.info(f"Processed {len(auto_memberships + auto_subscriptions)} automatic renewals")
    
    def _process_automatic_renewal(self, membership=None, subscription=None):
        """Enhanced automatic renewal processing with chapter support"""
        vals = {
            'membership_id': membership.id if membership else False,
            'subscription_id': subscription.id if subscription else False,
            'renewal_type': 'automatic',
            'state': 'confirmed',
        }
        
        if membership:
            vals.update({
                'new_end_date': membership._calculate_renewal_end_date(),
                'amount': membership.membership_fee,
                'renewal_period': membership.renewal_interval,
            })
            
            # Enhanced chapter automatic renewal
            if membership.is_chapter_membership:
                vals['maintains_chapter_role'] = True
                vals['chapter_notes'] = f'Automatic chapter renewal for {membership.product_id.name}'
        
        if subscription:
            vals.update({
                'new_end_date': subscription._calculate_renewal_end_date(),
                'amount': subscription.subscription_fee,
                'renewal_period': subscription.renewal_interval,
            })
        
        renewal = self.create(vals)
        
        # Create invoice for automatic renewal
        try:
            renewal.action_create_invoice()
        except Exception as e:
            _logger.warning(f"Failed to create invoice for automatic renewal {renewal.name}: {str(e)}")
        
        return renewal
    
    # Constraints
    @api.constrains('membership_id', 'subscription_id')
    def _check_related_record(self):
        for renewal in self:
            if not renewal.membership_id and not renewal.subscription_id:
                raise ValidationError(_("Renewal must be linked to either a membership or subscription."))
            if renewal.membership_id and renewal.subscription_id:
                raise ValidationError(_("Renewal cannot be linked to both membership and subscription."))
    
    @api.constrains('renewal_date', 'new_end_date')
    def _check_dates(self):
        for renewal in self:
            if renewal.new_end_date <= renewal.renewal_date:
                raise ValidationError(_("New end date must be after renewal date."))
    
    @api.constrains('amount')
    def _check_amount(self):
        for renewal in self:
            if renewal.amount < 0:
                raise ValidationError(_("Renewal amount cannot be negative."))
    
    @api.constrains('chapter_role_change', 'new_chapter_role', 'is_chapter_renewal')
    def _check_chapter_role_change(self):
        for renewal in self:
            if renewal.chapter_role_change != 'no_change' and not renewal.new_chapter_role:
                raise ValidationError(_("New chapter role must be specified when role change is selected."))
            
            if renewal.chapter_role_change != 'no_change' and not renewal.is_chapter_renewal:
                raise ValidationError(_("Chapter role changes can only be made for chapter renewals."))