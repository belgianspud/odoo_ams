from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Subscription Information
    subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Related Subscription',
        help="Subscription this invoice is created for"
    )
    
    is_membership_invoice = fields.Boolean(
        string='Is Membership Invoice',
        compute='_compute_is_membership_invoice',
        store=True,
        help="Check if this is a membership-related invoice"
    )
    
    membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Membership Type',
        related='subscription_id.membership_type_id',
        store=True,
        help="Type of membership being invoiced"
    )
    
    chapter_id = fields.Many2one(
        'ams.chapter',
        string='Chapter',
        related='subscription_id.chapter_id',
        store=True,
        help="Chapter for this membership"
    )
    
    # Membership Invoice Details
    membership_period_start = fields.Date(
        string='Membership Period Start',
        related='subscription_id.start_date',
        store=True
    )
    
    membership_period_end = fields.Date(
        string='Membership Period End',
        related='subscription_id.end_date',
        store=True
    )
    
    is_renewal_invoice = fields.Boolean(
        string='Is Renewal Invoice',
        compute='_compute_is_renewal_invoice',
        store=True,
        help="Check if this is a membership renewal invoice"
    )
    
    # Member Information
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
    
    # Payment and Revenue Recognition
    membership_revenue_recognition = fields.Selection([
        ('immediate', 'Immediate Recognition'),
        ('deferred', 'Deferred Over Period'),
        ('milestone', 'Milestone Based')
    ], string='Revenue Recognition Method', default='immediate')
    
    deferred_revenue_account_id = fields.Many2one(
        'account.account',
        string='Deferred Revenue Account',
        help="Account for deferred membership revenue"
    )
    
    # Recurring Invoice Information
    is_recurring_invoice = fields.Boolean(
        string='Is Recurring Invoice',
        default=False,
        help="Check if this is part of a recurring billing cycle"
    )
    
    recurring_sequence = fields.Integer(
        string='Recurring Sequence',
        help="Sequence number in recurring billing cycle"
    )
    
    # Proration and Adjustments
    is_prorated = fields.Boolean(
        string='Is Prorated',
        default=False,
        help="Check if this invoice includes prorated amounts"
    )
    
    proration_start_date = fields.Date(
        string='Proration Start Date',
        help="Start date for prorated period"
    )
    
    proration_end_date = fields.Date(
        string='Proration End Date',
        help="End date for prorated period"
    )
    
    # Special Invoice Types
    invoice_type_category = fields.Selection([
        ('new_membership', 'New Membership'),
        ('renewal', 'Membership Renewal'),
        ('upgrade', 'Membership Upgrade'),
        ('downgrade', 'Membership Downgrade'),
        ('additional_service', 'Additional Service'),
        ('refund', 'Membership Refund'),
        ('adjustment', 'Billing Adjustment')
    ], string='Invoice Category', compute='_compute_invoice_category', store=True)
    
    # Late Fees and Penalties
    includes_late_fee = fields.Boolean(
        string='Includes Late Fee',
        default=False
    )
    
    late_fee_amount = fields.Float(
        string='Late Fee Amount',
        digits='Product Price'
    )
    
    # Dunning and Collections
    dunning_level = fields.Selection([
        ('0', 'No Dunning'),
        ('1', 'First Notice'),
        ('2', 'Second Notice'),
        ('3', 'Final Notice'),
        ('4', 'Collections')
    ], string='Dunning Level', default='0')
    
    dunning_date = fields.Date(
        string='Last Dunning Date',
        help="Date of last dunning notice sent"
    )
    
    # Membership Status Impact
    affects_membership_status = fields.Boolean(
        string='Affects Membership Status',
        default=True,
        help="Check if payment of this invoice affects membership status"
    )
    
    # Commission and Referrals
    referral_partner_id = fields.Many2one(
        'res.partner',
        string='Referred By',
        help="Partner who referred this member"
    )
    
    commission_amount = fields.Float(
        string='Commission Amount',
        digits='Product Price',
        help="Commission amount for referral or sales agent"
    )
    
    commission_paid = fields.Boolean(
        string='Commission Paid',
        default=False
    )

    @api.depends('subscription_id')
    def _compute_is_membership_invoice(self):
        """Determine if this is a membership invoice"""
        for invoice in self:
            invoice.is_membership_invoice = bool(invoice.subscription_id)

    @api.depends('subscription_id.parent_subscription_id')
    def _compute_is_renewal_invoice(self):
        """Determine if this is a renewal invoice"""
        for invoice in self:
            invoice.is_renewal_invoice = bool(
                invoice.subscription_id and invoice.subscription_id.parent_subscription_id
            )

    @api.depends('is_renewal_invoice', 'is_membership_invoice', 'move_type')
    def _compute_invoice_category(self):
        """Determine invoice category"""
        for invoice in self:
            if not invoice.is_membership_invoice:
                invoice.invoice_type_category = False
            elif invoice.move_type == 'out_refund':
                invoice.invoice_type_category = 'refund'
            elif invoice.is_renewal_invoice:
                invoice.invoice_type_category = 'renewal'
            elif invoice.subscription_id:
                # Check if it's the first invoice for this subscription
                previous_invoices = self.search([
                    ('subscription_id', '=', invoice.subscription_id.id),
                    ('id', '!=', invoice.id),
                    ('state', '!=', 'cancel')
                ])
                if not previous_invoices:
                    invoice.invoice_type_category = 'new_membership'
                else:
                    invoice.invoice_type_category = 'additional_service'
            else:
                invoice.invoice_type_category = False

    def action_post(self):
        """Override post to handle membership-specific logic"""
        result = super().action_post()
        
        for invoice in self:
            if invoice.is_membership_invoice and invoice.subscription_id:
                invoice._process_membership_invoice_posting()
        
        return result

    def _process_membership_invoice_posting(self):
        """Process membership-specific logic when invoice is posted"""
        self.ensure_one()
        
        if not self.subscription_id:
            return
        
        # Update subscription payment status
        self._update_subscription_payment_status()
        
        # Handle revenue recognition
        if self.membership_revenue_recognition == 'deferred':
            self._create_deferred_revenue_entries()
        
        # Send member notification
        self._send_membership_invoice_notification()
        
        # Log activity
        self.subscription_id.message_post(
            body=_("Invoice %s posted for %s") % (self.name, self.amount_total)
        )

    def _update_subscription_payment_status(self):
        """Update subscription payment status based on invoice payments"""
        self.ensure_one()
        
        if not self.subscription_id:
            return
        
        # Get all invoices for this subscription
        subscription_invoices = self.search([
            ('subscription_id', '=', self.subscription_id.id),
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice')
        ])
        
        total_amount = sum(subscription_invoices.mapped('amount_total'))
        paid_amount = sum(subscription_invoices.mapped('amount_residual_signed'))
        
        if paid_amount <= 0:
            payment_status = 'paid'
        elif paid_amount < total_amount:
            payment_status = 'partial'
        else:
            payment_status = 'unpaid'
        
        self.subscription_id.payment_status = payment_status

    def _create_deferred_revenue_entries(self):
        """Create deferred revenue journal entries"""
        self.ensure_one()
        
        if not self.deferred_revenue_account_id or not self.membership_period_start or not self.membership_period_end:
            return
        
        # Calculate monthly revenue recognition
        start_date = fields.Date.from_string(self.membership_period_start)
        end_date = fields.Date.from_string(self.membership_period_end)
        
        total_months = ((end_date.year - start_date.year) * 12 + 
                       (end_date.month - start_date.month) + 1)
        
        monthly_amount = self.amount_total / total_months if total_months > 0 else 0
        
        # Create monthly recognition entries
        current_date = start_date
        for month in range(total_months):
            recognition_date = current_date.replace(day=1)  # First of month
            
            # Create journal entry for revenue recognition
            move_vals = {
                'date': recognition_date,
                'journal_id': self.journal_id.id,
                'ref': f"Revenue Recognition - {self.name} - Month {month + 1}",
                'line_ids': [
                    (0, 0, {
                        'account_id': self.deferred_revenue_account_id.id,
                        'debit': monthly_amount,
                        'credit': 0,
                        'name': f"Deferred Revenue Recognition - {self.subscription_id.display_name}",
                    }),
                    (0, 0, {
                        'account_id': self._get_revenue_account().id,
                        'debit': 0,
                        'credit': monthly_amount,
                        'name': f"Membership Revenue - {self.subscription_id.display_name}",
                    })
                ]
            }
            
            # Create the move but don't post it automatically
            move = self.env['account.move'].create(move_vals)
            
            current_date = current_date + relativedelta(months=1)

    def _get_revenue_account(self):
        """Get appropriate revenue account for membership"""
        # Default to the first invoice line's account
        if self.invoice_line_ids:
            return self.invoice_line_ids[0].account_id
        
        # Fallback to default revenue account
        return self.env['account.account'].search([
            ('code', 'like', '4%'),  # Revenue accounts typically start with 4
            ('company_id', '=', self.company_id.id)
        ], limit=1)

    def _send_membership_invoice_notification(self):
        """Send notification when membership invoice is posted"""
        self.ensure_one()
        
        template = self.env.ref(
            'ams_subscriptions.email_template_membership_invoice',
            raise_if_not_found=False
        )
        
        if template and self.partner_id.email:
            template.send_mail(self.id, force_send=True)

    def action_payment_received(self):
        """Handle actions when payment is received"""
        for invoice in self:
            if invoice.is_membership_invoice and invoice.subscription_id:
                # Update subscription status if fully paid
                if invoice.payment_state == 'paid':
                    invoice._activate_membership_on_payment()
                
                # Clear dunning level
                invoice.dunning_level = '0'

    def _activate_membership_on_payment(self):
        """Activate membership when payment is received"""
        self.ensure_one()
        
        if not self.subscription_id:
            return
        
        # Check if subscription should be activated
        if (self.subscription_id.state in ['draft', 'pending_approval'] and 
            self.affects_membership_status):
            
            # If no approval required, activate immediately
            if not self.subscription_id.membership_type_id.requires_approval:
                self.subscription_id.action_approve()
            
            # Send activation notification
            self._send_membership_activation_notification()

    def _send_membership_activation_notification(self):
        """Send notification when membership is activated"""
        self.ensure_one()
        
        template = self.env.ref(
            'ams_subscriptions.email_template_membership_activated',
            raise_if_not_found=False
        )
        
        if template and self.partner_id.email:
            template.send_mail(self.subscription_id.id, force_send=True)

    def action_send_dunning_notice(self):
        """Send dunning notice for overdue membership fees"""
        self.ensure_one()
        
        if not self.is_membership_invoice:
            raise UserError(_("This is not a membership invoice."))
        
        if self.payment_state == 'paid':
            raise UserError(_("Invoice is already paid."))
        
        # Increment dunning level
        current_level = int(self.dunning_level or '0')
        if current_level < 4:
            self.dunning_level = str(current_level + 1)
        
        self.dunning_date = fields.Date.today()
        
        # Send dunning notice
        template_ref = f'ams_subscriptions.email_template_dunning_notice_{self.dunning_level}'
        template = self.env.ref(template_ref, raise_if_not_found=False)
        
        if template and self.partner_id.email:
            template.send_mail(self.id, force_send=True)
        
        # Log dunning activity
        self.message_post(
            body=_("Dunning notice level %s sent to %s") % (self.dunning_level, self.partner_id.name)
        )

    def action_add_late_fee(self):
        """Add late fee to overdue invoice"""
        self.ensure_one()
        
        if self.payment_state == 'paid':
            raise UserError(_("Cannot add late fee to paid invoice."))
        
        if self.includes_late_fee:
            raise UserError(_("Late fee already added to this invoice."))
        
        # Calculate late fee (could be configurable)
        late_fee_percentage = 0.05  # 5%
        late_fee = self.amount_total * late_fee_percentage
        
        # Create late fee line
        late_fee_product = self.env.ref('ams_subscriptions.product_late_fee', raise_if_not_found=False)
        
        if late_fee_product:
            self.write({
                'invoice_line_ids': [(0, 0, {
                    'product_id': late_fee_product.id,
                    'quantity': 1,
                    'price_unit': late_fee,
                    'name': f"Late Fee - {self.name}",
                })]
            })
        
        self.write({
            'includes_late_fee': True,
            'late_fee_amount': late_fee,
        })

    @api.model
    def create_recurring_invoices(self):
        """Cron job to create recurring membership invoices"""
        today = fields.Date.today()
        
        # Find subscriptions that need renewal invoices
        subscriptions_to_invoice = self.env['ams.member.subscription'].search([
            ('state', '=', 'active'),
            ('auto_renew', '=', True),
            ('renewal_date', '<=', today),
            ('renewal_sent', '=', False)
        ])
        
        for subscription in subscriptions_to_invoice:
            try:
                self._create_renewal_invoice(subscription)
                subscription.renewal_sent = True
            except Exception as e:
                _logger.error(f"Failed to create renewal invoice for subscription {subscription.id}: {e}")

    @api.model
    def _create_renewal_invoice(self, subscription):
        """Create renewal invoice for a subscription"""
        if not subscription.membership_type_id.product_template_id:
            raise ValidationError(
                _("No product defined for membership type %s") % subscription.membership_type_id.name
            )
        
        # Create invoice
        invoice_vals = {
            'partner_id': subscription.partner_id.id,
            'move_type': 'out_invoice',
            'subscription_id': subscription.id,
            'invoice_type_category': 'renewal',
            'is_recurring_invoice': True,
            'invoice_line_ids': [(0, 0, {
                'product_id': subscription.membership_type_id.product_template_id.product_variant_id.id,
                'quantity': 1,
                'price_unit': subscription.membership_type_id.get_renewal_price(subscription),
                'name': f"Membership Renewal - {subscription.membership_type_id.name}",
            })]
        }
        
        invoice = self.create(invoice_vals)
        
        # Send renewal invoice
        if subscription.partner_id.email:
            template = self.env.ref(
                'ams_subscriptions.email_template_renewal_invoice',
                raise_if_not_found=False
            )
            if template:
                template.send_mail(invoice.id, force_send=True)
        
        return invoice

    @api.model
    def get_membership_revenue_report(self, date_from=None, date_to=None):
        """Generate membership revenue report"""
        domain = [
            ('is_membership_invoice', '=', True),
            ('state', '=', 'posted')
        ]
        
        if date_from:
            domain.append(('invoice_date', '>=', date_from))
        if date_to:
            domain.append(('invoice_date', '<=', date_to))
        
        invoices = self.search(domain)
        
        report_data = {
            'total_revenue': sum(invoices.mapped('amount_total')),
            'total_invoices': len(invoices),
            'by_membership_type': {},
            'by_chapter': {},
            'by_category': {},
        }
        
        # Group by membership type
        for invoice in invoices:
            if invoice.membership_type_id:
                type_name = invoice.membership_type_id.name
                if type_name not in report_data['by_membership_type']:
                    report_data['by_membership_type'][type_name] = 0
                report_data['by_membership_type'][type_name] += invoice.amount_total
        
        # Group by chapter
        for invoice in invoices:
            if invoice.chapter_id:
                chapter_name = invoice.chapter_id.name
                if chapter_name not in report_data['by_chapter']:
                    report_data['by_chapter'][chapter_name] = 0
                report_data['by_chapter'][chapter_name] += invoice.amount_total
        
        # Group by category
        for invoice in invoices:
            category = invoice.invoice_type_category or 'other'
            if category not in report_data['by_category']:
                report_data['by_category'][category] = 0
            report_data['by_category'][category] += invoice.amount_total
        
        return report_data

    def unlink(self):
        """Override unlink to handle subscription references"""
        for invoice in self:
            if invoice.subscription_id and invoice.subscription_id.sale_order_id:
                # Update subscription's sale order if this was the main invoice
                sale_order = invoice.subscription_id.sale_order_id
                remaining_invoices = sale_order.invoice_ids.filtered(lambda i: i.id != invoice.id)
                if not remaining_invoices:
                    # No more invoices, might want to reset subscription status
                    pass
        
        return super().unlink()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Subscription Line Information
    subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Related Subscription',
        related='move_id.subscription_id',
        store=True
    )
    
    membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Membership Type',
        related='move_id.membership_type_id',
        store=True
    )
    
    # Benefit Line Information
    benefit_id = fields.Many2one(
        'ams.subscription.benefit',
        string='Related Benefit',
        help="Benefit this line item relates to"
    )
    
    # Revenue Recognition
    is_deferred_revenue = fields.Boolean(
        string='Is Deferred Revenue',
        default=False
    )
    
    recognition_start_date = fields.Date(
        string='Recognition Start Date'
    )
    
    recognition_end_date = fields.Date(
        string='Recognition End Date'
    )
    
    # Proration Information
    is_prorated_line = fields.Boolean(
        string='Is Prorated Line',
        default=False
    )
    
    proration_factor = fields.Float(
        string='Proration Factor',
        digits=(12, 4),
        help="Factor used for proration calculation"
    )
    
    original_amount = fields.Float(
        string='Original Amount',
        digits='Product Price',
        help="Amount before proration"
    )

    @api.onchange('product_id')
    def _onchange_product_membership_info(self):
        """Update line information when membership product is selected"""
        if self.product_id:
            # Check if product is linked to membership type
            membership_type = self.env['ams.membership.type'].search([
                ('product_template_id', '=', self.product_id.product_tmpl_id.id)
            ], limit=1)
            
            if membership_type and self.move_id.partner_id:
                self.name = f"{membership_type.name} Membership - {self.move_id.partner_id.name}"