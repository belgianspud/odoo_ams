# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # Subscription-related fields - UPDATED: Remove chapter logic
    has_subscription_lines = fields.Boolean(
        string='Has Subscription Lines',
        compute='_compute_has_subscription_lines',
        store=True,
        help='This invoice contains subscription product lines'
    )
    
    # NEW: Chapter-related fields (delegated to ams_chapters module)
    has_chapter_lines = fields.Boolean(
        string='Has Chapter Lines',
        compute='_compute_has_chapter_lines',
        store=True,
        help='This invoice contains chapter product lines'
    )
    
    @api.depends('invoice_line_ids.product_id.is_subscription_product')
    def _compute_has_subscription_lines(self):
        """Check if invoice contains subscription product lines (excluding memberships)"""
        for move in self:
            subscription_lines = move.invoice_line_ids.filtered(
                lambda line: (line.product_id and 
                            line.product_id.product_tmpl_id.is_subscription_product and
                            line.product_id.product_tmpl_id.subscription_product_type != 'membership')
            )
            move.has_subscription_lines = bool(subscription_lines)
    
    @api.depends('invoice_line_ids.product_id.is_chapter_product')
    def _compute_has_chapter_lines(self):
        """Check if invoice contains chapter product lines"""
        for move in self:
            chapter_lines = move.invoice_line_ids.filtered(
                lambda line: (line.product_id and 
                            line.product_id.product_tmpl_id.is_chapter_product)
            )
            move.has_chapter_lines = bool(chapter_lines)
    
    def _post(self, soft=True):
        """Override _post to handle subscription activation when invoice is posted"""
        result = super()._post(soft)
        
        # Process subscription activations for customer invoices that are posted
        for move in self:
            if (move.move_type == 'out_invoice' and 
                move.state == 'posted' and 
                (move.has_subscription_lines or move.has_chapter_lines)):
                # ENSURE PORTAL ACCESS TOKEN EXISTS FOR SUBSCRIPTION/CHAPTER INVOICES
                if not move.access_token:
                    move._portal_ensure_token()
                move._process_subscription_activations()
        
        return result
    
    def _process_subscription_activations(self):
        """Process subscription/membership/chapter activations when invoice is posted and paid"""
        self.ensure_one()
        
        # Only process if invoice is paid or in payment
        if self.payment_state not in ['paid', 'in_payment']:
            return
        
        for line in self.invoice_line_ids:
            if not line.product_id:
                continue
            
            try:
                product_tmpl = line.product_id.product_tmpl_id
                
                # Handle subscription products (memberships and pure subscriptions)
                if product_tmpl.is_subscription_product:
                    if product_tmpl.subscription_product_type == 'membership':
                        membership = self._activate_membership_from_line(line)
                        if membership:
                            _logger.info(f"Activated membership {membership.name} from invoice {self.name}")
                    else:
                        # Handle pure subscription products (publication, event, etc.)
                        subscription = self._activate_subscription_from_line(line)
                        if subscription:
                            _logger.info(f"Activated subscription {subscription.name} from invoice {self.name}")
                
                # Handle chapter products - UPDATED: Delegate to ams_chapters module
                elif product_tmpl.is_chapter_product:
                    chapter_membership = self._activate_chapter_membership_from_line(line)
                    if chapter_membership:
                        _logger.info(f"Activated chapter membership {chapter_membership} from invoice {self.name}")
                    
            except Exception as e:
                _logger.error(f"Failed to activate subscription from invoice line {line.id}: {str(e)}")
                continue
    
    def _activate_membership_from_line(self, line):
        """Activate membership from paid invoice line"""
        # First, try to find existing membership from sale order line
        membership = self.env['ams.membership'].search([
            ('sale_order_line_id.product_id', '=', line.product_id.id),
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['draft', 'active'])
        ], limit=1)
        
        if membership:
            # Update existing membership with invoice information
            membership.write({
                'invoice_id': self.id,
                'invoice_line_id': line.id,
                'payment_status': 'paid',
                'state': 'active',
                'last_renewal_date': fields.Date.today(),
            })
            _logger.info(f"Activated existing membership {membership.name}")
        else:
            # Create new membership from invoice payment
            membership = self.env['ams.membership'].create_from_invoice_payment(line)
            if membership:
                _logger.info(f"Created and activated membership {membership.name} from invoice payment")
        
        return membership
    
    def _activate_subscription_from_line(self, line):
        """Activate subscription from paid invoice line"""
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
    
    def _activate_chapter_membership_from_line(self, line):
        """Activate chapter membership from paid invoice line - UPDATED: Delegate to ams_chapters module"""
        _logger.info(f"Processing chapter product invoice line {line.id}")
        
        # Check if ams_chapters module is installed
        if 'ams.chapter.membership' in self.env:
            _logger.info("Delegating chapter membership activation to ams_chapters module")
            try:
                # Delegate to the ams_chapters module
                return self.env['ams.chapter.membership'].create_from_invoice_payment(line)
            except Exception as e:
                _logger.error(f"Error delegating to ams_chapters module: {str(e)}")
                return self._handle_chapter_fallback(line)
        else:
            _logger.warning("ams_chapters module not available for chapter product activation")
            return self._handle_chapter_fallback(line)
    
    def _handle_chapter_fallback(self, line):
        """Handle chapter product when ams_chapters module is not available"""
        partner = self.partner_id
        product = line.product_id
        
        # Log the payment for chapter product
        partner.message_post(
            body=f"Payment received for chapter product: {product.name} from invoice {self.name}. "
                 f"Chapter membership activation requires ams_chapters module.",
            subject="Chapter Product Payment - Module Required"
        )
        
        _logger.warning(f"Chapter product {product.name} paid by {partner.name} but ams_chapters module not available")
        
        # Return a descriptive string instead of an object
        return f"Chapter payment logged for {product.name} - requires ams_chapters module"

    def _get_portal_return_action(self):
        """Override portal return action for membership/subscription/chapter invoices"""
        # First try the standard method
        try:
            action = super()._get_portal_return_action()
        except:
            action = None
        
        # If this invoice is related to a membership/subscription/chapter, provide specific return action
        if hasattr(self, 'has_subscription_lines') and (self.has_subscription_lines or self.has_chapter_lines):
            # Check for membership line first
            membership_line = self.invoice_line_ids.filtered(
                lambda l: (l.product_id and l.product_id.product_tmpl_id.is_subscription_product and 
                         l.product_id.product_tmpl_id.subscription_product_type == 'membership')
            )
            if membership_line:
                # Try to find the related membership
                membership = self.env['ams.membership'].search([
                    ('invoice_id', '=', self.id),
                    ('invoice_line_id', '=', membership_line[0].id)
                ], limit=1)
                if membership:
                    return {
                        'type': 'ir.actions.act_url',
                        'target': 'self',
                        'url': f'/my/memberships/{membership.id}'
                    }
            
            # Check for subscription line
            subscription_line = self.invoice_line_ids.filtered(
                lambda l: (l.product_id and l.product_id.product_tmpl_id.is_subscription_product and 
                         l.product_id.product_tmpl_id.subscription_product_type != 'membership')
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
            
            # Check for chapter line - UPDATED: Try to delegate to ams_chapters module
            chapter_line = self.invoice_line_ids.filtered(
                lambda l: (l.product_id and l.product_id.product_tmpl_id.is_chapter_product)
            )
            if chapter_line:
                if 'ams.chapter.membership' in self.env:
                    try:
                        # Try to find the related chapter membership
                        chapter_membership = self.env['ams.chapter.membership'].search([
                            ('invoice_id', '=', self.id),
                            ('invoice_line_id', '=', chapter_line[0].id)
                        ], limit=1)
                        if chapter_membership:
                            return {
                                'type': 'ir.actions.act_url', 
                                'target': 'self',
                                'url': f'/my/chapters/{chapter_membership.id}'
                            }
                    except Exception as e:
                        _logger.warning(f"Could not find chapter membership for return action: {str(e)}")
        
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
                (getattr(move, 'has_subscription_lines', False) or getattr(move, 'has_chapter_lines', False))):
                move._portal_ensure_token()

    def _portal_ensure_token(self):
        """Ensure this invoice has a portal access token"""
        if not self.access_token:
            # Generate a new token
            import secrets
            self.access_token = secrets.token_urlsafe(32)


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    def action_post(self):
        """Override action_post to trigger subscription processing when payment is posted"""
        result = super().action_post()
        
        # Process subscription activations for customer payments
        for payment in self:
            if payment.payment_type == 'inbound' and payment.state == 'posted':
                payment._process_subscription_payments()
        
        return result
    
    def _process_subscription_payments(self):
        """Process subscription activations from payments"""
        self.ensure_one()
        
        # Get reconciled invoices
        reconciled_moves = self._get_reconciled_invoices()
        
        for invoice in reconciled_moves:
            if ((getattr(invoice, 'has_subscription_lines', False) or getattr(invoice, 'has_chapter_lines', False)) 
                and invoice.payment_state in ['paid', 'in_payment']):
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
    
    is_subscription_line = fields.Boolean(
        string='Subscription Line',
        compute='_compute_is_subscription_line',
        store=True,
        help='This invoice line is for a subscription product'
    )
    
    # NEW: Chapter line identification
    is_chapter_line = fields.Boolean(
        string='Chapter Line',
        compute='_compute_is_chapter_line',
        store=True,
        help='This invoice line is for a chapter product'
    )
    
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
    
    # NEW: Related chapter membership (if ams_chapters module is installed)
    related_chapter_membership_id = fields.Many2one(
        'ams.chapter.membership',
        string='Related Chapter Membership',
        compute='_compute_related_records',
        store=True
    )
    
    @api.depends('product_id.is_subscription_product')
    def _compute_is_subscription_line(self):
        """Check if this line is for a subscription product"""
        for line in self:
            line.is_subscription_line = bool(
                line.product_id and getattr(line.product_id.product_tmpl_id, 'is_subscription_product', False)
            )
    
    @api.depends('product_id.is_chapter_product')
    def _compute_is_chapter_line(self):
        """Check if this line is for a chapter product"""
        for line in self:
            line.is_chapter_line = bool(
                line.product_id and getattr(line.product_id.product_tmpl_id, 'is_chapter_product', False)
            )
    
    @api.depends('move_id', 'product_id')
    def _compute_related_records(self):
        """Find related membership/subscription/chapter records"""
        for line in self:
            line.related_membership_id = False
            line.related_subscription_id = False
            line.related_chapter_membership_id = False
            
            if not (line.is_subscription_line or line.is_chapter_line):
                continue
            
            # Look for related membership (from subscription products with membership type)
            if line.is_subscription_line and line.product_id.product_tmpl_id.subscription_product_type == 'membership':
                try:
                    membership = self.env['ams.membership'].search([
                        ('invoice_line_id', '=', line.id)
                    ], limit=1)
                    if membership:
                        line.related_membership_id = membership.id
                        continue
                except Exception:
                    pass
            
            # Look for related subscription (from pure subscription products)
            elif line.is_subscription_line and line.product_id.product_tmpl_id.subscription_product_type != 'membership':
                try:
                    subscription = self.env['ams.subscription'].search([
                        ('invoice_line_id', '=', line.id)
                    ], limit=1)
                    if subscription:
                        line.related_subscription_id = subscription.id
                        continue
                except Exception:
                    pass
            
            # Look for related chapter membership (if ams_chapters module is installed)
            elif line.is_chapter_line and 'ams.chapter.membership' in self.env:
                try:
                    chapter_membership = self.env['ams.chapter.membership'].search([
                        ('invoice_line_id', '=', line.id)
                    ], limit=1)
                    if chapter_membership:
                        line.related_chapter_membership_id = chapter_membership.id
                except Exception:
                    pass