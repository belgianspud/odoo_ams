from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)


class MemberSubscription(models.Model):
    _name = 'ams.member.subscription'
    _description = 'Member Subscription'
    _order = 'start_date desc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Subscription Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        required=True,
        tracking=True,
        domain=[('is_company', '=', False)]
    )
    
    membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Membership Type',
        required=True,
        tracking=True
    )
    
    chapter_id = fields.Many2one(
        'ams.chapter',
        string='Chapter',
        tracking=True,
        help="Chapter this membership belongs to"
    )
    
    # Subscription Lifecycle
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('active', 'Active'),
        ('pending_renewal', 'Pending Renewal'),
        ('expired', 'Expired'),
        ('lapsed', 'Lapsed'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended')
    ], string='Status', default='draft', required=True, tracking=True)
    
    stage_id = fields.Many2one(
        'ams.subscription.stage',
        string='Stage',
        tracking=True,
        group_expand='_read_group_stage_ids'
    )
    
    # Dates
    application_date = fields.Date(
        string='Application Date',
        default=fields.Date.context_today,
        tracking=True
    )
    
    approval_date = fields.Date(
        string='Approval Date',
        tracking=True
    )
    
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    
    end_date = fields.Date(
        string='End Date',
        compute='_compute_end_date',
        store=True,
        tracking=True
    )
    
    renewal_date = fields.Date(
        string='Renewal Date',
        compute='_compute_renewal_date',
        store=True,
        help="Date when renewal notice should be sent"
    )
    
    # Financial Information
    unit_price = fields.Float(
        string='Unit Price',
        digits='Product Price',
        tracking=True
    )
    
    discount_percent = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0
    )
    
    discount_amount = fields.Float(
        string='Discount Amount',
        digits='Product Price',
        compute='_compute_amounts',
        store=True
    )
    
    subtotal = fields.Float(
        string='Subtotal',
        digits='Product Price',
        compute='_compute_amounts',
        store=True
    )
    
    tax_amount = fields.Float(
        string='Tax Amount',
        digits='Product Price',
        compute='_compute_amounts',
        store=True
    )
    
    total_amount = fields.Float(
        string='Total Amount',
        digits='Product Price',
        compute='_compute_amounts',
        store=True
    )
    
    # Renewal Information
    auto_renew = fields.Boolean(
        string='Auto-Renew',
        default=False,
        help="Automatically renew this subscription"
    )
    
    renewal_sent = fields.Boolean(
        string='Renewal Notice Sent',
        default=False
    )
    
    renewal_count = fields.Integer(
        string='Renewal Count',
        default=0,
        help="Number of times this subscription has been renewed"
    )
    
    # Payment Information
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
        ('other', 'Other')
    ], string='Payment Method')
    
    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('refunded', 'Refunded')
    ], string='Payment Status', default='unpaid', tracking=True)
    
    # Related Records
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        copy=False
    )
    
    invoice_ids = fields.One2many(
        'account.move',
        'subscription_id',
        string='Invoices',
        domain=[('move_type', '=', 'out_invoice')]
    )
    
    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_invoice_count'
    )
    
    parent_subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Previous Subscription',
        help="Previous subscription this renewal is based on"
    )
    
    child_subscription_ids = fields.One2many(
        'ams.member.subscription',
        'parent_subscription_id',
        string='Renewal Subscriptions'
    )
    
    # Notes and Comments
    notes = fields.Html(
        string='Internal Notes'
    )
    
    member_notes = fields.Html(
        string='Member Notes',
        help="Notes visible to the member"
    )
    
    # Approval Information
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        tracking=True
    )
    
    rejection_reason = fields.Text(
        string='Rejection Reason'
    )

    @api.depends('partner_id', 'membership_type_id', 'name')
    def _compute_display_name(self):
        for record in self:
            if record.partner_id and record.membership_type_id:
                record.display_name = f"{record.partner_id.name} - {record.membership_type_id.name}"
            else:
                record.display_name = record.name or _('New Subscription')

    @api.depends('start_date', 'membership_type_id')
    def _compute_end_date(self):
        for record in self:
            if record.start_date and record.membership_type_id:
                record.end_date = record.membership_type_id.get_expiration_date(record.start_date)
            else:
                record.end_date = False

    @api.depends('end_date', 'membership_type_id')
    def _compute_renewal_date(self):
        for record in self:
            if record.end_date and record.membership_type_id:
                notice_days = record.membership_type_id.renewal_notice_days or 30
                record.renewal_date = record.end_date - relativedelta(days=notice_days)
            else:
                record.renewal_date = False

    @api.depends('unit_price', 'discount_percent')
    def _compute_amounts(self):
        for record in self:
            record.discount_amount = record.unit_price * (record.discount_percent / 100)
            record.subtotal = record.unit_price - record.discount_amount
            # For now, we'll set tax to 0. This can be extended later
            record.tax_amount = 0.0
            record.total_amount = record.subtotal + record.tax_amount

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    @api.onchange('membership_type_id')
    def _onchange_membership_type_id(self):
        if self.membership_type_id:
            self.unit_price = self.membership_type_id.price
            # Check if chapter is required and allowed
            if self.membership_type_id.chapter_based:
                # Fix: Safely get chapter ID
                chapter_id = self.chapter_id.id if self.chapter_id else False
                if chapter_id and not self.membership_type_id.is_available_for_chapter(chapter_id):
                    self.chapter_id = False
                    return {'warning': {
                        'title': _('Chapter Restriction'),
                        'message': _('This membership type is not available for the selected chapter.')
                    }}

    @api.onchange('chapter_id')
    def _onchange_chapter_id(self):
        if self.chapter_id and self.membership_type_id:
            # Fix: Check if chapter_id exists before accessing .id
            chapter_id = self.chapter_id.id if self.chapter_id else False
            if chapter_id and not self.membership_type_id.is_available_for_chapter(chapter_id):
                return {'warning': {
                    'title': _('Chapter Restriction'),
                    'message': _('The selected membership type is not available for this chapter.')
                }}
                
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ams.member.subscription') or _('New')
        
        records = super().create(vals_list)
        
        for record in records:
            # Set initial stage
            if not record.stage_id:
                stage = self.env['ams.subscription.stage'].search([
                    ('sequence', '=', 1)
                ], limit=1)
                if stage:
                    record.stage_id = stage.id
        
        return records

    def action_submit_for_approval(self):
        """Submit subscription for approval"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Only draft subscriptions can be submitted for approval."))
            
            if record.membership_type_id.requires_approval:
                record.state = 'pending_approval'
                record.message_post(body=_("Subscription submitted for approval."))
            else:
                record.action_approve()

    def action_approve(self):
        """Approve the subscription"""
        for record in self:
            if record.state not in ['draft', 'pending_approval']:
                raise UserError(_("Only draft or pending subscriptions can be approved."))
            
            record.write({
                'state': 'active',
                'approval_date': fields.Date.today(),
                'approved_by': self.env.user.id,
            })
            
            # Create sale order if needed
            if not record.sale_order_id:
                record._create_sale_order()
            
            record.message_post(body=_("Subscription approved and activated."))

    def action_reject(self):
        """Reject the subscription"""
        return {
            'name': _('Reject Subscription'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_id': self.id}
        }

    def action_cancel(self):
        """Cancel the subscription"""
        for record in self:
            record.state = 'cancelled'
            record.message_post(body=_("Subscription cancelled."))

    def action_suspend(self):
        """Suspend the subscription"""
        for record in self:
            if record.state != 'active':
                raise UserError(_("Only active subscriptions can be suspended."))
            record.state = 'suspended'
            record.message_post(body=_("Subscription suspended."))

    def action_reactivate(self):
        """Reactivate a suspended subscription"""
        for record in self:
            if record.state != 'suspended':
                raise UserError(_("Only suspended subscriptions can be reactivated."))
            record.state = 'active'
            record.message_post(body=_("Subscription reactivated."))

    def action_renew(self):
        """Create a renewal subscription"""
        self.ensure_one()
        
        if self.state not in ['active', 'pending_renewal', 'expired']:
            raise UserError(_("Only active, pending renewal, or expired subscriptions can be renewed."))
        
        # Fix: Safely get chapter ID
        chapter_id = self.chapter_id.id if self.chapter_id else False
        
        # Create new subscription
        renewal_vals = {
            'partner_id': self.partner_id.id,
            'membership_type_id': self.membership_type_id.id,
            'chapter_id': chapter_id,
            'start_date': self.end_date + relativedelta(days=1) if self.end_date else fields.Date.today(),
            'unit_price': self.membership_type_id.get_renewal_price(self),
            'parent_subscription_id': self.id,
            'auto_renew': self.auto_renew,
            'payment_method': self.payment_method,
        }
        
        renewal = self.create(renewal_vals)
        
        # Update renewal count
        self.renewal_count += 1
        
        return {
            'name': _('Renewal Subscription'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.member.subscription',
            'res_id': renewal.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_sale_order(self):
        """Create a sale order for this subscription"""
        self.ensure_one()
        
        if not self.membership_type_id.product_template_id:
            raise UserError(_("No product defined for membership type %s") % self.membership_type_id.name)
        
        sale_vals = {
            'partner_id': self.partner_id.id,
            'date_order': fields.Datetime.now(),
            'subscription_id': self.id,
            'order_line': [(0, 0, {
                'product_id': self.membership_type_id.product_template_id.product_variant_id.id,
                'product_uom_qty': 1,
                'price_unit': self.unit_price,
                'discount': self.discount_percent,
                'name': f"{self.membership_type_id.name} Membership - {self.partner_id.name}",
            })]
        }
        
        sale_order = self.env['sale.order'].create(sale_vals)
        self.sale_order_id = sale_order.id
        
        return sale_order

    def action_view_invoices(self):
        """View invoices related to this subscription"""
        self.ensure_one()
        
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        
        if len(self.invoice_ids) > 1:
            action['domain'] = [('id', 'in', self.invoice_ids.ids)]
        elif len(self.invoice_ids) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = self.invoice_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        
        return action

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """Always display all stages in kanban view"""
        return self.env['ams.subscription.stage'].search([], order=order)

    @api.model
    def check_subscription_renewals(self):
        """Cron job to check for subscriptions that need renewal notices"""
        today = fields.Date.today()
        
        # Find subscriptions that need renewal notices
        subscriptions_to_notify = self.search([
            ('state', '=', 'active'),
            ('renewal_date', '<=', today),
            ('renewal_sent', '=', False),
            ('auto_renew', '=', False)
        ])
        
        for subscription in subscriptions_to_notify:
            subscription._send_renewal_notice()
            subscription.renewal_sent = True
        
        # Check for expired subscriptions
        expired_subscriptions = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today)
        ])
        
        for subscription in expired_subscriptions:
            grace_period = subscription.membership_type_id.grace_period_days or 30
            grace_end = subscription.end_date + relativedelta(days=grace_period)
            
            if today <= grace_end:
                subscription.state = 'expired'
            else:
                subscription.state = 'lapsed'

    def _send_renewal_notice(self):
        """Send renewal notice to member"""
        self.ensure_one()
        
        template = self.env.ref('ams_subscriptions.email_template_renewal_notice', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        
        self.message_post(body=_("Renewal notice sent to member."))

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError(_("Start date cannot be after end date."))