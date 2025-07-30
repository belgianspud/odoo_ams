from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Subscription Information
    subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Related Subscription',
        help="Subscription this sale order is created for"
    )
    
    is_membership_order = fields.Boolean(
        string='Is Membership Order',
        compute='_compute_is_membership_order',
        store=True,
        help="Check if this is a membership-related order"
    )
    
    membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Membership Type',
        related='subscription_id.membership_type_id',
        store=True,
        help="Type of membership being purchased"
    )
    
    chapter_id = fields.Many2one(
        'ams.chapter',
        string='Chapter',
        related='subscription_id.chapter_id',
        store=True,
        help="Chapter for this membership"
    )
    
    # Membership Order Details
    membership_start_date = fields.Date(
        string='Membership Start Date',
        related='subscription_id.start_date',
        store=True
    )
    
    membership_end_date = fields.Date(
        string='Membership End Date',
        related='subscription_id.end_date',
        store=True
    )
    
    is_renewal_order = fields.Boolean(
        string='Is Renewal Order',
        compute='_compute_is_renewal_order',
        store=True,
        help="Check if this is a membership renewal"
    )
    
    # Payment and Billing
    membership_discount_percent = fields.Float(
        string='Membership Discount %',
        related='subscription_id.discount_percent',
        store=True
    )
    
    auto_renew = fields.Boolean(
        string='Auto-Renew',
        related='subscription_id.auto_renew',
        store=True,
        help="Automatically renew this membership"
    )
    
    # Member Information (for easy access)
    member_id = fields.Many2one(
        'res.partner',
        string='Member',
        related='subscription_id.partner_id',
        store=True
    )
    
    member_number = fields.Char(
        string='Member Number',
        related='member_id.membership_number',
        store=True
    )
    
    # Special Handling Flags
    requires_membership_approval = fields.Boolean(
        string='Requires Membership Approval',
        compute='_compute_requires_approval',
        store=True,
        help="Check if membership requires approval before activation"
    )
    
    membership_approved = fields.Boolean(
        string='Membership Approved',
        default=False,
        help="Check when membership has been approved"
    )
    
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By'
    )
    
    approval_date = fields.Datetime(
        string='Approval Date'
    )
    
    # Invoicing
    membership_invoice_policy = fields.Selection([
        ('immediate', 'Invoice Immediately'),
        ('upon_approval', 'Invoice Upon Approval'),
        ('upon_activation', 'Invoice Upon Activation'),
        ('manual', 'Manual Invoicing')
    ], string='Membership Invoice Policy', default='immediate')

    @api.depends('subscription_id')
    def _compute_is_membership_order(self):
        """Determine if this is a membership order"""
        for order in self:
            order.is_membership_order = bool(order.subscription_id)

    @api.depends('subscription_id.parent_subscription_id')
    def _compute_is_renewal_order(self):
        """Determine if this is a renewal order"""
        for order in self:
            order.is_renewal_order = bool(
                order.subscription_id and order.subscription_id.parent_subscription_id
            )

    @api.depends('subscription_id.membership_type_id.requires_approval')
    def _compute_requires_approval(self):
        """Determine if membership requires approval"""
        for order in self:
            if order.subscription_id and order.subscription_id.membership_type_id:
                order.requires_membership_approval = order.subscription_id.membership_type_id.requires_approval
            else:
                order.requires_membership_approval = False

    @api.onchange('partner_id')
    def _onchange_partner_membership_info(self):
        """Update membership information when partner changes"""
        if self.partner_id and self.is_membership_order:
            # Check if partner is already a member
            existing_subscription = self.env['ams.member.subscription'].search([
                ('partner_id', '=', self.partner_id.id),
                ('state', 'in', ['active', 'pending_renewal'])
            ], limit=1)
            
            if existing_subscription:
                return {'warning': {
                    'title': _('Existing Membership'),
                    'message': _('This person already has an active membership. '
                               'Consider creating a renewal instead.')
                }}

    def action_confirm(self):
        """Override confirm to handle membership logic"""
        result = super().action_confirm()
        
        for order in self:
            if order.is_membership_order and order.subscription_id:
                # Handle membership-specific confirmation logic
                order._process_membership_confirmation()
        
        return result

    def _process_membership_confirmation(self):
        """Process membership-specific logic when order is confirmed"""
        self.ensure_one()
        
        if not self.subscription_id:
            return
        
        # Update subscription based on invoice policy
        if self.membership_invoice_policy == 'immediate':
            self._activate_membership_if_ready()
        elif self.requires_membership_approval:
            self.subscription_id.action_submit_for_approval()
        else:
            self._activate_membership_if_ready()

    def _activate_membership_if_ready(self):
        """Activate membership if all conditions are met"""
        self.ensure_one()
        
        if not self.subscription_id:
            return
        
        # Check if approval is needed
        if self.requires_membership_approval and not self.membership_approved:
            return
        
        # Check if payment is required
        if self.invoice_status in ['to invoice', 'invoiced']:
            # Activate subscription
            if self.subscription_id.state in ['draft', 'pending_approval']:
                self.subscription_id.action_approve()

    def action_approve_membership(self):
        """Approve membership application"""
        self.ensure_one()
        
        if not self.is_membership_order:
            raise UserError(_("This is not a membership order."))
        
        if self.membership_approved:
            raise UserError(_("Membership is already approved."))
        
        self.write({
            'membership_approved': True,
            'approved_by': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })
        
        # Approve the subscription
        if self.subscription_id:
            self.subscription_id.action_approve()
        
        # Send approval notification
        self._send_membership_approval_notification()

    def action_reject_membership(self):
        """Reject membership application"""
        self.ensure_one()
        
        if not self.is_membership_order:
            raise UserError(_("This is not a membership order."))
        
        # Cancel the order
        self.action_cancel()
        
        # Reject the subscription
        if self.subscription_id:
            self.subscription_id.action_reject()

    def _send_membership_approval_notification(self):
        """Send notification when membership is approved"""
        self.ensure_one()
        
        template = self.env.ref(
            'ams_subscriptions.email_template_membership_approved', 
            raise_if_not_found=False
        )
        
        if template and self.partner_id.email:
            template.send_mail(self.id, force_send=True)

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Override invoice creation for membership handling"""
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)
        
        for invoice in invoices:
            # Link invoice to subscription
            for line in invoice.invoice_line_ids:
                if line.sale_line_ids:
                    order = line.sale_line_ids[0].order_id
                    if order.subscription_id:
                        invoice.subscription_id = order.subscription_id.id
                        break
        
        return invoices

    @api.model
    def create_membership_order(self, partner_id, membership_type_id, chapter_id=None, **kwargs):
        """Helper method to create a membership order"""
        
        partner = self.env['res.partner'].browse(partner_id)
        membership_type = self.env['ams.membership.type'].browse(membership_type_id)
        
        # Validate inputs
        if not partner.exists():
            raise ValidationError(_("Invalid partner specified."))
        
        if not membership_type.exists():
            raise ValidationError(_("Invalid membership type specified."))
        
        # Check if product exists for membership type
        if not membership_type.product_template_id:
            raise ValidationError(
                _("No product defined for membership type '%s'") % membership_type.name
            )
        
        # Create subscription first
        subscription_vals = {
            'partner_id': partner_id,
            'membership_type_id': membership_type_id,
            'chapter_id': chapter_id,
            'unit_price': membership_type.price,
            'start_date': fields.Date.today(),
        }
        subscription_vals.update(kwargs.get('subscription_vals', {}))
        
        subscription = self.env['ams.member.subscription'].create(subscription_vals)
        
        # Create sale order
        order_vals = {
            'partner_id': partner_id,
            'subscription_id': subscription.id,
            'order_line': [(0, 0, {
                'product_id': membership_type.product_template_id.product_variant_id.id,
                'product_uom_qty': 1,
                'price_unit': membership_type.price,
                'name': f"{membership_type.name} Membership - {partner.name}",
            })]
        }
        order_vals.update(kwargs.get('order_vals', {}))
        
        order = self.create(order_vals)
        
        # Link subscription to sale order
        subscription.sale_order_id = order.id
        
        return order

    def action_view_subscription(self):
        """View related subscription"""
        self.ensure_one()
        
        if not self.subscription_id:
            raise UserError(_("No subscription linked to this order."))
        
        return {
            'name': _('Subscription'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.member.subscription',
            'res_id': self.subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_renewal_order(self):
        """Create a renewal order for this membership"""
        self.ensure_one()
        
        if not self.is_membership_order:
            raise UserError(_("This is not a membership order."))
        
        if not self.subscription_id:
            raise UserError(_("No subscription found to renew."))
        
        # Create renewal subscription
        renewal_action = self.subscription_id.action_renew()
        
        return renewal_action

    @api.model
    def get_membership_sales_statistics(self, date_from=None, date_to=None):
        """Get membership sales statistics"""
        domain = [('is_membership_order', '=', True)]
        
        if date_from:
            domain.append(('date_order', '>=', date_from))
        if date_to:
            domain.append(('date_order', '<=', date_to))
        
        orders = self.search(domain)
        
        stats = {
            'total_orders': len(orders),
            'confirmed_orders': len(orders.filtered(lambda o: o.state in ['sale', 'done'])),
            'renewal_orders': len(orders.filtered(lambda o: o.is_renewal_order)),
            'total_amount': sum(orders.mapped('amount_total')),
            'by_membership_type': {},
            'by_chapter': {},
        }
        
        # Group by membership type
        for order in orders:
            if order.membership_type_id:
                type_name = order.membership_type_id.name
                if type_name not in stats['by_membership_type']:
                    stats['by_membership_type'][type_name] = {
                        'count': 0,
                        'amount': 0.0
                    }
                stats['by_membership_type'][type_name]['count'] += 1
                stats['by_membership_type'][type_name]['amount'] += order.amount_total
        
        # Group by chapter
        for order in orders:
            if order.chapter_id:
                chapter_name = order.chapter_id.name
                if chapter_name not in stats['by_chapter']:
                    stats['by_chapter'][chapter_name] = {
                        'count': 0,
                        'amount': 0.0
                    }
                stats['by_chapter'][chapter_name]['count'] += 1
                stats['by_chapter'][chapter_name]['amount'] += order.amount_total
        
        return stats

    def write(self, vals):
        """Override write to handle state changes"""
        result = super().write(vals)
        
        # Handle state changes for membership orders
        if 'state' in vals:
            for order in self:
                if order.is_membership_order and order.subscription_id:
                    if vals['state'] == 'cancel':
                        # Cancel related subscription
                        if order.subscription_id.state in ['draft', 'pending_approval']:
                            order.subscription_id.action_cancel()
                    elif vals['state'] == 'sale':
                        # Process membership confirmation
                        order._process_membership_confirmation()
        
        return result

    @api.constrains('subscription_id', 'partner_id')
    def _check_subscription_partner_match(self):
        """Ensure subscription partner matches order partner"""
        for order in self:
            if order.subscription_id and order.partner_id:
                if order.subscription_id.partner_id != order.partner_id:
                    raise ValidationError(
                        _("Order partner must match subscription partner.")
                    )


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Membership Information
    is_membership_line = fields.Boolean(
        string='Is Membership Line',
        compute='_compute_is_membership_line',
        store=True,
        help="Check if this line is for a membership product"
    )
    
    membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Membership Type',
        compute='_compute_membership_info',
        store=True
    )
    
    # Benefit Information
    related_benefit_id = fields.Many2one(
        'ams.subscription.benefit',
        string='Related Benefit',
        help="Benefit this line item relates to"
    )

    @api.depends('product_id')
    def _compute_is_membership_line(self):
        """Determine if this is a membership line"""
        for line in self:
            if line.product_id:
                # Check if product is linked to any membership type
                membership_type = self.env['ams.membership.type'].search([
                    ('product_template_id', '=', line.product_id.product_tmpl_id.id)
                ], limit=1)
                line.is_membership_line = bool(membership_type)
            else:
                line.is_membership_line = False

    @api.depends('product_id', 'is_membership_line')
    def _compute_membership_info(self):
        """Compute membership type information"""
        for line in self:
            if line.is_membership_line and line.product_id:
                membership_type = self.env['ams.membership.type'].search([
                    ('product_template_id', '=', line.product_id.product_tmpl_id.id)
                ], limit=1)
                line.membership_type_id = membership_type.id if membership_type else False
            else:
                line.membership_type_id = False

    @api.onchange('product_id')
    def _onchange_product_membership_info(self):
        """Update line information when membership product is selected"""
        if self.is_membership_line and self.membership_type_id:
            # Update line description
            if self.order_id.partner_id:
                self.name = f"{self.membership_type_id.name} Membership - {self.order_id.partner_id.name}"
            else:
                self.name = f"{self.membership_type_id.name} Membership"