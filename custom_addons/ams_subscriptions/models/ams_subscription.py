from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

class AMSSubscription(models.Model):
    _name = 'ams.subscription'
    _description = 'AMS Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # For chatter and tracking

    name = fields.Char(string='Subscription Name', required=True, tracking=True)
    
    # Link to Customer / Account
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    account_id = fields.Many2one('res.partner', string='Account', help='Used for enterprise memberships')

    # Product and Sale Info
    product_id = fields.Many2one('product.product', string='Product', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_line_id = fields.Many2one('account.move.line', string='Invoice Line')

    # Subscription Type and Tier
    subscription_type = fields.Selection([
        ('individual', 'Membership - Individual'),
        ('enterprise', 'Membership - Enterprise'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication'),
        ('seat', 'Enterprise Seat Add-On'),
    ], string='Subscription Type', required=True)

    tier_id = fields.Many2one('ams.subscription.tier', string='Tier / Level')

    # Lifecycle
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('grace', 'Grace'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], string='Status', default='draft', tracking=True)

    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    paid_through_date = fields.Date(string='Paid Through Date')
    grace_end_date = fields.Date(string='Grace Period End', compute='_compute_lifecycle_dates', store=True)
    suspend_end_date = fields.Date(string='Suspension End', compute='_compute_lifecycle_dates', store=True)
    terminate_date = fields.Date(string='Termination Date', compute='_compute_lifecycle_dates', store=True)

    # Enterprise Seat Management
    base_seats = fields.Integer(string='Base Seats', default=0)
    extra_seats = fields.Integer(string='Extra Seats', default=0)
    total_seats = fields.Integer(string='Total Seats', compute='_compute_total_seats', store=True)

    seat_ids = fields.One2many('ams.subscription.seat', 'subscription_id', string='Assigned Seats')

    # Flags
    auto_renew = fields.Boolean(string='Auto Renew', default=True)
    is_free = fields.Boolean(string='Free Subscription', default=False)

    @api.depends('base_seats', 'extra_seats')
    def _compute_total_seats(self):
        for sub in self:
            sub.total_seats = (sub.base_seats or 0) + (sub.extra_seats or 0)

    @api.depends('paid_through_date', 'tier_id.grace_days', 'tier_id.suspend_days', 'tier_id.terminate_days')
    def _compute_lifecycle_dates(self):
        for sub in self:
            if sub.paid_through_date and sub.tier_id:
                sub.grace_end_date = sub.paid_through_date + timedelta(days=sub.tier_id.grace_days or 30)
                sub.suspend_end_date = sub.grace_end_date + timedelta(days=sub.tier_id.suspend_days or 60)
                sub.terminate_date = sub.suspend_end_date + timedelta(days=sub.tier_id.terminate_days or 30)
            else:
                sub.grace_end_date = False
                sub.suspend_end_date = False
                sub.terminate_date = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-populate fields when product is selected"""
        if self.product_id:
            product_tmpl = self.product_id.product_tmpl_id
            self.subscription_type = product_tmpl.ams_product_type
            self.tier_id = product_tmpl.subscription_tier_id.id
            
            # Set default paid through date based on product subscription period
            if product_tmpl.subscription_period and not self.paid_through_date:
                self.paid_through_date = self._calculate_end_date(self.start_date or fields.Date.today(), product_tmpl.subscription_period)

    def _calculate_end_date(self, start_date, period):
        """Calculate end date based on subscription period"""
        if period == 'monthly':
            return start_date + relativedelta(months=1) - timedelta(days=1)
        elif period == 'quarterly':
            return start_date + relativedelta(months=3) - timedelta(days=1)
        elif period == 'semi_annual':
            return start_date + relativedelta(months=6) - timedelta(days=1)
        elif period == 'annual':
            # Annual subscriptions run calendar year
            return date(start_date.year, 12, 31)
        else:
            return start_date + relativedelta(years=1) - timedelta(days=1)

    def action_activate(self):
        for sub in self:
            sub.state = 'active'
            if not sub.paid_through_date:
                # Default to 1 year if not set; can be overridden by tier or product period
                product_period = sub.product_id.product_tmpl_id.subscription_period
                sub.paid_through_date = sub._calculate_end_date(sub.start_date, product_period or 'annual')

    def action_set_grace(self):
        self.write({'state': 'grace'})

    def action_suspend(self):
        self.write({'state': 'suspended'})

    def action_terminate(self):
        self.write({'state': 'terminated'})

    @api.model
    def create_from_invoice_payment(self, invoice_line):
        """Create subscription when invoice line is paid"""
        product = invoice_line.product_id.product_tmpl_id
        
        # Only create subscriptions for AMS products
        if not product or product.ams_product_type == 'none':
            return False
            
        # Handle Enterprise Seat Add-ons differently
        if product.is_seat_addon:
            return self._handle_seat_addon_payment(invoice_line)
        
        # Check if subscription already exists for this invoice line
        existing_sub = self.search([('invoice_line_id', '=', invoice_line.id)], limit=1)
        if existing_sub:
            return existing_sub
        
        # Create new subscription
        partner = invoice_line.move_id.partner_id
        start_date = fields.Date.today()
        
        subscription_vals = {
            'name': f"{partner.name} - {product.name}",
            'partner_id': partner.id,
            'account_id': partner.parent_id.id if partner.parent_id else partner.id,
            'product_id': invoice_line.product_id.id,
            'subscription_type': product.ams_product_type,
            'tier_id': product.subscription_tier_id.id if product.subscription_tier_id else False,
            'start_date': start_date,
            'paid_through_date': self._calculate_end_date(start_date, product.subscription_period or 'annual'),
            'state': 'active',
            'invoice_id': invoice_line.move_id.id,
            'invoice_line_id': invoice_line.id,
            'base_seats': product.subscription_tier_id.default_seats if product.ams_product_type == 'enterprise' else 0,
            'extra_seats': 0,
            'auto_renew': product.subscription_tier_id.auto_renew if product.subscription_tier_id else True,
            'is_free': product.subscription_tier_id.is_free if product.subscription_tier_id else False,
        }
        
        subscription = self.create(subscription_vals)
        subscription.message_post(body=f"Subscription created from invoice payment: {invoice_line.move_id.name}")
        
        return subscription

    def _handle_seat_addon_payment(self, invoice_line):
        """Add seats to existing enterprise subscription"""
        partner = invoice_line.move_id.partner_id
        
        # Find active enterprise subscription for this partner
        enterprise_sub = self.search([
            ('partner_id', '=', partner.id),
            ('subscription_type', '=', 'enterprise'),
            ('state', '=', 'active'),
        ], limit=1)
        
        if enterprise_sub:
            seats_to_add = int(invoice_line.quantity)
            enterprise_sub.extra_seats += seats_to_add
            enterprise_sub.message_post(
                body=f"{seats_to_add} seats added via invoice payment: {invoice_line.move_id.name}"
            )
            return enterprise_sub
        else:
            # No active enterprise subscription found - log warning
            invoice_line.move_id.message_post(
                body="Warning: Seat add-on purchased but no active enterprise subscription found."
            )
            return False

    # ------------------------------------------------
    # Subscription Lifecycle & Renewal Automation
    # ------------------------------------------------
    def _cron_process_subscription_lifecycle(self):
        """Run daily: Move subscriptions through Active -> Grace -> Suspended -> Terminated."""
        today = fields.Date.today()
        subs = self.search([('state', '!=', 'terminated')])
        for sub in subs:
            tier = sub.tier_id
            if not tier or tier.is_free:
                continue  # free subscriptions do not expire

            grace_end = sub.paid_through_date + timedelta(days=tier.grace_days)
            suspend_end = grace_end + timedelta(days=tier.suspend_days)

            if today > suspend_end:
                sub.state = 'terminated'
            elif today > grace_end:
                sub.state = 'suspended'
            elif today > sub.paid_through_date:
                sub.state = 'grace'
            else:
                sub.state = 'active'

    def _cron_generate_renewal_invoices(self):
        """Run daily: Auto-generate renewal invoices 2 weeks before paid_through_date."""
        today = fields.Date.today()
        renew_window = today + timedelta(days=14)
        subs = self.search([('state', '=', 'active'), ('paid_through_date', '<=', renew_window)])

        for sub in subs:
            # Avoid duplicate renewal invoices
            existing_invoice = self.env['account.move'].search([
                ('invoice_origin', '=', sub.name),
                ('state', '=', 'draft'),
            ], limit=1)
            if existing_invoice:
                continue

            # Create a draft invoice
            product = self.env['product.product'].search([('id','=',sub.product_id.id)], limit=1)
            if not product:
                continue

            move_vals = {
                'move_type': 'out_invoice',
                'partner_id': sub.partner_id.id,
                'invoice_origin': sub.name,
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': product.list_price,
                })],
            }
            invoice = self.env['account.move'].create(move_vals)

            # Optional: email notification could be added here
            sub.message_post(body=f"Renewal invoice {invoice.name or invoice.id} generated.")


class AccountMove(models.Model):
    """Hook into invoice payments to create subscriptions"""
    _inherit = 'account.move'

    def _post(self, soft=True):
        """Override to trigger subscription creation when invoice is posted and paid"""
        result = super()._post(soft=soft)
        
        # Check for paid invoices after posting
        for move in self.filtered(lambda m: m.move_type == 'out_invoice'):
            if move.payment_state in ['paid', 'in_payment']:
                self._create_subscriptions_from_payment(move)
        
        return result

    def _create_subscriptions_from_payment(self, invoice):
        """Create subscriptions for AMS products when invoice is paid"""
        for line in invoice.invoice_line_ids:
            if line.product_id and line.product_id.product_tmpl_id.ams_product_type != 'none':
                # Check if subscription already exists
                existing_sub = self.env['ams.subscription'].search([
                    ('invoice_line_id', '=', line.id)
                ], limit=1)
                if not existing_sub:
                    self.env['ams.subscription'].create_from_invoice_payment(line)


class AccountPartialReconcile(models.Model):
    """Hook into payment reconciliation to create subscriptions"""
    _inherit = 'account.partial.reconcile'

    @api.model_create_multi
    def create(self, vals_list):
        """Override to trigger subscription creation when payments are reconciled"""
        reconciles = super().create(vals_list)
        
        for reconcile in reconciles:
            # Check if this reconciliation involves an invoice payment
            debit_move = reconcile.debit_move_id.move_id
            credit_move = reconcile.credit_move_id.move_id
            
            # Find the invoice (could be either debit or credit depending on the reconciliation)
            invoice = None
            if debit_move.move_type == 'out_invoice':
                invoice = debit_move
            elif credit_move.move_type == 'out_invoice':
                invoice = credit_move
            
            if invoice and invoice.payment_state in ['paid', 'in_payment']:
                invoice._create_subscriptions_from_payment(invoice)
        
        return reconciles


class AccountPayment(models.Model):
    """Hook into payment posting to create subscriptions"""
    _inherit = 'account.payment'

    def action_post(self):
        """Override to trigger subscription creation when payment is posted"""
        result = super().action_post()
        
        # After payment is posted, check related invoices
        for payment in self:
            if payment.state == 'posted' and payment.partner_type == 'customer':
                # Find invoices that this payment reconciles with
                reconciled_moves = payment.line_ids.mapped('matched_debit_ids.debit_move_id.move_id') | \
                                 payment.line_ids.mapped('matched_credit_ids.credit_move_id.move_id')
                
                invoices = reconciled_moves.filtered(lambda m: m.move_type == 'out_invoice')
                for invoice in invoices:
                    if invoice.payment_state in ['paid', 'in_payment']:
                        invoice._create_subscriptions_from_payment(invoice)
        
        return result


class AccountPaymentRegister(models.TransientModel):
    """Hook into payment registration wizard"""
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        """Override to trigger subscription creation after payment creation"""
        result = super().action_create_payments()
        
        # Get the invoices being paid
        active_ids = self.env.context.get('active_ids', [])
        invoices = self.env['account.move'].browse(active_ids).filtered(
            lambda m: m.move_type == 'out_invoice'
        )
        
        # Check each invoice for AMS products and create subscriptions
        for invoice in invoices:
            # Refresh invoice state from database
            invoice._cr.commit()
            invoice.invalidate_recordset()
            
            if invoice.payment_state in ['paid', 'in_payment']:
                invoice._create_subscriptions_from_payment(invoice)
        
        return result