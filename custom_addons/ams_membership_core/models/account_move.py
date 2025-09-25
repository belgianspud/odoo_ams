# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # Enhanced subscription-related fields with chapter support
    has_subscription_lines = fields.Boolean(
        string='Has Subscription Lines',
        compute='_compute_has_subscription_lines',
        store=True,
        help='This invoice contains subscription product lines'
    )
    
    has_membership_lines = fields.Boolean(
        string='Has Membership Lines',
        compute='_compute_has_membership_lines',
        store=True,
        help='This invoice contains regular membership product lines'
    )
    
    has_chapter_lines = fields.Boolean(
        string='Has Chapter Lines',
        compute='_compute_has_chapter_lines',
        store=True,
        help='This invoice contains chapter membership product lines'
    )
    
    # Analytics fields
    chapter_revenue = fields.Monetary(
        string='Chapter Revenue',
        compute='_compute_chapter_revenue',
        store=True,
        currency_field='currency_id',
        help='Total revenue from chapter membership lines'
    )
    
    membership_revenue = fields.Monetary(
        string='Membership Revenue',
        compute='_compute_membership_revenue',
        store=True,
        currency_field='currency_id',
        help='Total revenue from regular membership lines'
    )
    
    @api.depends('invoice_line_ids.product_id.is_subscription_product', 'invoice_line_ids.product_id.subscription_product_type')
    def _compute_has_subscription_lines(self):
        """Check if invoice contains pure subscription product lines (not memberships or chapters)"""
        for move in self:
            subscription_lines = move.invoice_line_ids.filtered(
                lambda line: (line.product_id and 
                            line.product_id.product_tmpl_id.is_subscription_product and
                            line.product_id.product_tmpl_id.subscription_product_type not in ['membership', 'chapter'])
            )
            move.has_subscription_lines = bool(subscription_lines)
    
    @api.depends('invoice_line_ids.product_id.is_subscription_product', 'invoice_line_ids.product_id.subscription_product_type')
    def _compute_has_membership_lines(self):
        """Check if invoice contains regular membership product lines"""
        for move in self:
            membership_lines = move.invoice_line_ids.filtered(
                lambda line: (line.product_id and 
                            line.product_id.product_tmpl_id.is_subscription_product and
                            line.product_id.product_tmpl_id.subscription_product_type == 'membership')
            )
            move.has_membership_lines = bool(membership_lines)
    
    @api.depends('invoice_line_ids.product_id.is_subscription_product', 'invoice_line_ids.product_id.subscription_product_type')
    def _compute_has_chapter_lines(self):
        """Check if invoice contains chapter membership product lines"""
        for move in self:
            chapter_lines = move.invoice_line_ids.filtered(
                lambda line: (line.product_id and 
                            line.product_id.product_tmpl_id.is_subscription_product and
                            line.product_id.product_tmpl_id.subscription_product_type == 'chapter')
            )
            move.has_chapter_lines = bool(chapter_lines)
    
    @api.depends('invoice_line_ids.product_id.subscription_product_type', 'invoice_line_ids.price_subtotal')
    def _compute_chapter_revenue(self):
        """Calculate total chapter membership revenue"""
        for move in self:
            chapter_revenue = 0.0
            for line in move.invoice_line_ids:
                if (line.product_id and 
                    line.product_id.product_tmpl_id.subscription_product_type == 'chapter'):
                    chapter_revenue += line.price_subtotal
            move.chapter_revenue = chapter_revenue
    
    @api.depends('invoice_line_ids.product_id.subscription_product_type', 'invoice_line_ids.price_subtotal')
    def _compute_membership_revenue(self):
        """Calculate total regular membership revenue"""
        for move in self:
            membership_revenue = 0.0
            for line in move.invoice_line_ids:
                if (line.product_id and 
                    line.product_id.product_tmpl_id.subscription_product_type == 'membership'):
                    membership_revenue += line.price_subtotal
            move.membership_revenue = membership_revenue
    
    def _post(self, soft=True):
        """Override _post to handle enhanced subscription activation when invoice is posted"""
        result = super()._post(soft)
        
        # Process subscription activations for customer invoices that are posted
        for move in self:
            if (move.move_type == 'out_invoice' and 
                move.state == 'posted' and 
                (move.has_subscription_lines or move.has_membership_lines or move.has_chapter_lines)):
                # ENSURE PORTAL ACCESS TOKEN EXISTS FOR SUBSCRIPTION/MEMBERSHIP/CHAPTER INVOICES
                if not move.access_token:
                    move._portal_ensure_token()
                move._process_subscription_activations()
        
        return result
    
    def _process_subscription_activations(self):
        """Enhanced subscription/membership activation processing with better chapter support"""
        self.ensure_one()
        
        # Only process if invoice is paid or in payment
        if self.payment_state not in ['paid', 'in_payment']:
            return
        
        for line in self.invoice_line_ids:
            if not line.product_id:
                continue
            
            try:
                product_tmpl = line.product_id.product_tmpl_id
                
                # Handle subscription products (memberships and chapters together, pure subscriptions separately)
                if product_tmpl.is_subscription_product:
                    if product_tmpl.subscription_product_type in ['membership', 'chapter']:
                        # Both regular memberships and chapter memberships are handled by the same model
                        membership = self._activate_membership_from_line(line)
                        if membership:
                            membership_type = "chapter membership" if product_tmpl.subscription_product_type == 'chapter' else "membership"
                            _logger.info(f"Activated {membership_type} {membership.name} from invoice {self.name}")
                    else:
                        # Handle pure subscription products (publication, event, etc.)
                        subscription = self._activate_subscription_from_line(line)
                        if subscription:
                            _logger.info(f"Activated subscription {subscription.name} from invoice {self.name}")
                    
            except Exception as e:
                _logger.error(f"Failed to activate subscription from invoice line {line.id}: {str(e)}")
                continue
    
    def _activate_membership_from_line(self, line):
        """Enhanced membership activation with comprehensive chapter support"""
        product_tmpl = line.product_id.product_tmpl_id
        
        # Verify this is a membership or chapter product
        if product_tmpl.subscription_product_type not in ['membership', 'chapter']:
            _logger.warning(f"Line {line.id} is not a membership or chapter product")
            return None
        
        # First, try to find existing membership from sale order line
        membership = self.env['ams.membership'].search([
            ('sale_order_line_id.product_id', '=', line.product_id.id),
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['draft', 'active'])
        ], limit=1)
        
        if membership:
            # Update existing membership with invoice information
            update_vals = {
                'invoice_id': self.id,
                'invoice_line_id': line.id,
                'payment_status': 'paid',
                'state': 'active',
                'last_renewal_date': fields.Date.today(),
            }
            
            membership.write(update_vals)
            
            membership_type = "chapter membership" if membership.is_chapter_membership else "membership"
            _logger.info(f"Activated existing {membership_type} {membership.name}")
        else:
            # Create new membership from invoice payment using enhanced creation method
            membership = self.env['ams.membership'].create_from_invoice_payment(line)
            if membership:
                membership_type = "chapter membership" if membership.is_chapter_membership else "membership"
                _logger.info(f"Created and activated {membership_type} {membership.name} from invoice payment")
        
        return membership
    
    def _activate_subscription_from_line(self, line):
        """Activate pure subscription from paid invoice line (no membership/chapter support)"""
        product_tmpl = line.product_id.product_tmpl_id
        
        # Verify this is a pure subscription product (not membership or chapter)
        if product_tmpl.subscription_product_type in ['membership', 'chapter']:
            _logger.warning(f"Line {line.id} is a membership/chapter product, should not be processed as subscription")
            return None
        
        # First, try to find existing subscription from sale order line
        subscription = self.env['ams.subscription'].search([
            ('sale_order_line_id.product_id', '=', line.product_id.id),
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['draft', 'active'])
        ], limit=1)
        
        if subscription:
            # Update existing subscription with invoice information
            subscription.write({
                'invoice_id': self.id,
                'invoice_line_id': line.id,
                'payment_status': 'paid',
                'state': 'active',
                'last_renewal_date': fields.Date.today(),
            })
            _logger.info(f"Activated existing subscription {subscription.name}")
        else:
            # Create new subscription from invoice payment
            subscription = self.env['ams.subscription'].create_from_invoice_payment(line)
            if subscription:
                _logger.info(f"Created and activated subscription {subscription.name} from invoice payment")
        
        return subscription

    def _get_portal_return_action(self):
        """Enhanced portal return action for membership/subscription/chapter invoices"""
        # First try the standard method
        try:
            action = super()._get_portal_return_action()
        except:
            action = None
        
        # If this invoice is related to a membership/subscription/chapter, provide specific return action
        if (hasattr(self, 'has_subscription_lines') and 
            (self.has_subscription_lines or self.has_membership_lines or self.has_chapter_lines)):
            
            # Check for membership line first (both regular and chapter)
            membership_line = self.invoice_line_ids.filtered(
                lambda l: (l.product_id and l.product_id.product_tmpl_id.is_subscription_product and 
                         l.product_id.product_tmpl_id.subscription_product_type in ['membership', 'chapter'])
            )
            if membership_line:
                # Try to find the related membership
                membership = self.env['ams.membership'].search([
                    ('invoice_id', '=', self.id),
                    ('invoice_line_id', '=', membership_line[0].id)
                ], limit=1)
                if membership:
                    # Enhanced return URL for chapter vs regular membership
                    if membership.is_chapter_membership:
                        return {
                            'type': 'ir.actions.act_url',
                            'target': 'self',
                            'url': f'/my/chapters/{membership.id}'
                        }
                    else:
                        return {
                            'type': 'ir.actions.act_url',
                            'target': 'self',
                            'url': f'/my/memberships/{membership.id}'
                        }
            
            # Check for pure subscription line
            subscription_line = self.invoice_line_ids.filtered(
                lambda l: (l.product_id and l.product_id.product_tmpl_id.is_subscription_product and 
                         l.product_id.product_tmpl_id.subscription_product_type not in ['membership', 'chapter'])
            )
            if subscription_line:
                # Try to find the related subscription
                subscription = self.env['ams.subscription'].search([
                    ('invoice_id', '=', self.id),
                    ('invoice_line_id', '=', subscription_line[0].id)
                ], limit=1)
                if subscription:
                    return {
                        'type': 'ir.actions.act_url', 
                        'target': 'self',
                        'url': f'/my/subscriptions/{subscription.id}'
                    }
        
        return action or {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/my'
        }

    def _compute_access_token(self):
        """Ensure membership/subscription/chapter invoices have access tokens"""
        super()._compute_access_token()
        # Additional token generation for subscription and chapter invoices
        for move in self:
            if (not move.access_token and 
                (getattr(move, 'has_subscription_lines', False) or 
                 getattr(move, 'has_membership_lines', False) or
                 getattr(move, 'has_chapter_lines', False))):
                move._portal_ensure_token()

    def _portal_ensure_token(self):
        """Ensure this invoice has a portal access token"""
        if not self.access_token:
            # Generate a new token
            import secrets
            self.access_token = secrets.token_urlsafe(32)

    def action_chapter_revenue_analysis(self):
        """Open chapter revenue analysis"""
        self.ensure_one()
        
        return {
            'name': _('Chapter Revenue Analysis'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,pivot,graph',
            'domain': [
                ('move_id', '=', self.id),
                ('product_id.subscription_product_type', '=', 'chapter')
            ],
            'context': {
                'group_by': ['product_id', 'partner_id'],
                'search_default_chapter_products': 1
            }
        }


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    def action_post(self):
        """Override action_post to trigger enhanced subscription processing when payment is posted"""
        result = super().action_post()
        
        # Process subscription activations for customer payments
        for payment in self:
            if payment.payment_type == 'inbound' and payment.state == 'posted':
                payment._process_subscription_payments()
        
        return result
    
    def _process_subscription_payments(self):
        """Process enhanced subscription activations from payments"""
        self.ensure_one()
        
        # Get reconciled invoices
        reconciled_moves = self._get_reconciled_invoices()
        
        for invoice in reconciled_moves:
            if ((getattr(invoice, 'has_subscription_lines', False) or 
                 getattr(invoice, 'has_membership_lines', False) or
                 getattr(invoice, 'has_chapter_lines', False)) and 
                invoice.payment_state in ['paid', 'in_payment']):
                invoice._process_subscription_activations()
    
    def _get_reconciled_invoices(self):
        """Get invoices reconciled with this payment"""
        reconciled_invoices = self.env['account.move']
        
        # Get reconciled move lines
        try:
            reconciled_lines = self.line_ids.mapped('matched_debit_ids.debit_move_id') | \
                              self.line_ids.mapped('matched_credit_ids.credit_move_id')
            
            # Filter for customer invoices
            for line in reconciled_lines:
                if (line.move_id.move_type == 'out_invoice' and 
                    line.move_id not in reconciled_invoices):
                    reconciled_invoices |= line.move_id
        except Exception as e:
            _logger.warning(f"Error getting reconciled invoices: {str(e)}")
        
        return reconciled_invoices


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    # Enhanced line classification
    is_subscription_line = fields.Boolean(
        string='Subscription Line',
        compute='_compute_line_types',
        store=True,
        help='This invoice line is for a pure subscription product'
    )
    
    is_membership_line = fields.Boolean(
        string='Membership Line',
        compute='_compute_line_types',
        store=True,
        help='This invoice line is for a regular membership product'
    )
    
    is_chapter_line = fields.Boolean(
        string='Chapter Line',
        compute='_compute_line_types',
        store=True,
        help='This invoice line is for a chapter membership product'
    )
    
    # Enhanced related records
    related_membership_id = fields.Many2one(
        'ams.membership',
        string='Related Membership',
        compute='_compute_related_records',
        store=True
    )
    
    related_subscription_id = fields.Many2one(
        'ams.subscription', 
        string='Related Subscription',
        compute='_compute_related_records',
        store=True
    )
    
    # Chapter-specific fields
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
    
    @api.depends('product_id.is_subscription_product', 'product_id.subscription_product_type')
    def _compute_line_types(self):
        """Enhanced line type computation with better chapter support"""
        for line in self:
            if line.product_id and line.product_id.product_tmpl_id.is_subscription_product:
                product_type = line.product_id.product_tmpl_id.subscription_product_type
                
                line.is_membership_line = (product_type == 'membership')
                line.is_chapter_line = (product_type == 'chapter')
                line.is_subscription_line = (product_type not in ['membership', 'chapter'])
            else:
                line.is_subscription_line = False
                line.is_membership_line = False
                line.is_chapter_line = False
    
    @api.depends('product_id.chapter_type', 'product_id.chapter_location')
    def _compute_chapter_info(self):
        """Compute chapter information from product"""
        for line in self:
            if line.is_chapter_line and line.product_id:
                line.chapter_type = line.product_id.product_tmpl_id.chapter_type
                line.chapter_location = line.product_id.product_tmpl_id.chapter_location
            else:
                line.chapter_type = False
                line.chapter_location = False
    
    @api.depends('move_id', 'product_id', 'is_membership_line', 'is_chapter_line', 'is_subscription_line')
    def _compute_related_records(self):
        """Enhanced related record computation"""
        for line in self:
            line.related_membership_id = False
            line.related_subscription_id = False
            
            if not (line.is_subscription_line or line.is_membership_line or line.is_chapter_line):
                continue
            
            # Look for related membership (from both regular and chapter membership products)
            if line.is_membership_line or line.is_chapter_line:
                try:
                    membership = self.env['ams.membership'].search([
                        ('invoice_line_id', '=', line.id)
                    ], limit=1)
                    if membership:
                        line.related_membership_id = membership.id
                        continue
                except Exception:
                    pass
            
            # Look for related subscription (from pure subscription products only)
            elif line.is_subscription_line:
                try:
                    subscription = self.env['ams.subscription'].search([
                        ('invoice_line_id', '=', line.id)
                    ], limit=1)
                    if subscription:
                        line.related_subscription_id = subscription.id
                        continue
                except Exception:
                    pass
    
    def action_view_related_membership(self):
        """View related membership record"""
        self.ensure_one()
        
        if not self.related_membership_id:
            raise UserError(_("No related membership found for this line."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Membership'),
            'res_model': 'ams.membership',
            'res_id': self.related_membership_id.id,
            'view_mode': 'form',
        }
    
    def action_view_related_subscription(self):
        """View related subscription record"""
        self.ensure_one()
        
        if not self.related_subscription_id:
            raise UserError(_("No related subscription found for this line."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Subscription'),
            'res_model': 'ams.subscription',
            'res_id': self.related_subscription_id.id,
            'view_mode': 'form',
        }