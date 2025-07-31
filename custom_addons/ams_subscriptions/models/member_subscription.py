from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
import logging

class MemberSubscription(models.Model):
    _inherit = 'ams.member.subscription'
    
    # Recurring Billing Fields
    recurring_rule_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'), 
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    ], string='Recurrence', default='yearly', tracking=True)

    recurring_interval = fields.Integer(
        string='Repeat Every',
        default=1,
        help="Repeat every X years/months/weeks/days"
    )

    next_invoice_date = fields.Date(
        string='Next Invoice Date',
        compute='_compute_next_invoice_date',
        store=True,
        help="Date when next recurring invoice will be generated"
    )
    
    # Payment Automation
    auto_payment = fields.Boolean(
        string='Automatic Payment',
        default=False,
        help="Automatically charge saved payment method"
    )
    
    payment_token_id = fields.Many2one(
        'payment.token',
        string='Saved Payment Method',
        help="Saved payment method for automatic charging"
    )
    
    # MRR/ARR Tracking
    mrr_amount = fields.Float(
        string='Monthly Recurring Revenue',
        compute='_compute_recurring_revenue',
        store=True,
        help="Monthly recurring revenue from this subscription"
    )
    
    arr_amount = fields.Float(
        string='Annual Recurring Revenue', 
        compute='_compute_recurring_revenue',
        store=True,
        help="Annual recurring revenue from this subscription"
    )
    
    # Revenue Recognition
    revenue_recognition_method = fields.Selection([
        ('immediate', 'Immediate'),
        ('monthly', 'Monthly'),
        ('daily', 'Daily')
    ], string='Revenue Recognition', default='immediate')
    
    deferred_revenue_account_id = fields.Many2one(
        'account.account',
        string='Deferred Revenue Account'
    )
    
    # Dunning Management
    dunning_level = fields.Selection([
        ('0', 'No Dunning'),
        ('1', 'First Notice'),
        ('2', 'Second Notice'), 
        ('3', 'Final Notice'),
        ('4', 'Collections')
    ], string='Dunning Level', default='0')
    
    last_dunning_date = fields.Date(string='Last Dunning Date')
    
    # Proration Support
    is_prorated = fields.Boolean(string='Is Prorated', default=False)
    proration_factor = fields.Float(string='Proration Factor', digits=(12, 4))

    @api.depends('recurring_rule_type', 'recurring_interval', 'start_date', 'state')
    def _compute_next_invoice_date(self):
        """Compute next invoice date based on recurrence rules"""
        for subscription in self:
            if subscription.state not in ['active', 'pending_renewal'] or not subscription.start_date:
                subscription.next_invoice_date = False
                continue
                
            # Get last invoice date or use start date
            last_invoice = subscription.invoice_ids.filtered(
                lambda inv: inv.state == 'posted'
            ).sorted('invoice_date', reverse=True)[:1]
            
            base_date = last_invoice.invoice_date if last_invoice else subscription.start_date
            
            # Calculate next date based on recurrence
            if subscription.recurring_rule_type == 'daily':
                next_date = base_date + relativedelta(days=subscription.recurring_interval)
            elif subscription.recurring_rule_type == 'weekly':
                next_date = base_date + relativedelta(weeks=subscription.recurring_interval)
            elif subscription.recurring_rule_type == 'monthly':
                next_date = base_date + relativedelta(months=subscription.recurring_interval)
            else:  # yearly
                next_date = base_date + relativedelta(years=subscription.recurring_interval)
            
            subscription.next_invoice_date = next_date

    @api.depends('total_amount', 'recurring_rule_type', 'recurring_interval', 'state')
    def _compute_recurring_revenue(self):
        """Compute MRR and ARR amounts"""
        for subscription in self:
            if subscription.state not in ['active', 'pending_renewal']:
                subscription.mrr_amount = 0.0
                subscription.arr_amount = 0.0
                continue
            
            # Calculate monthly amount based on recurrence
            total = subscription.total_amount or 0.0
            
            if subscription.recurring_rule_type == 'daily':
                monthly_amount = (total * 30.44) / subscription.recurring_interval  # avg days per month
            elif subscription.recurring_rule_type == 'weekly':
                monthly_amount = (total * 4.345) / subscription.recurring_interval  # avg weeks per month
            elif subscription.recurring_rule_type == 'monthly':
                monthly_amount = total / subscription.recurring_interval
            else:  # yearly
                monthly_amount = total / (12 * subscription.recurring_interval)
            
            subscription.mrr_amount = monthly_amount
            subscription.arr_amount = monthly_amount * 12

    def action_generate_recurring_invoice(self):
        """Generate recurring invoice for this subscription"""
        self.ensure_one()
        
        if not self.next_invoice_date or self.next_invoice_date > fields.Date.today():
            return False
            
        # Create invoice
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'subscription_id': self.id,
            'is_recurring_invoice': True,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.membership_type_id.product_template_id.product_variant_id.id,
                'quantity': 1,
                'price_unit': self.unit_price,
                'discount': self.discount_percent,
                'name': f"Recurring {self.membership_type_id.name} - {self.partner_id.name}",
            })]
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Auto-pay if enabled and payment method available
        if self.auto_payment and self.payment_token_id:
            self._process_automatic_payment(invoice)
            
        return invoice

    def _process_automatic_payment(self, invoice):
        """Process automatic payment for invoice"""
        try:
            # Create payment transaction (this would integrate with payment providers)
            payment_vals = {
                'payment_method_line_id': self.payment_token_id.payment_method_id.id,
                'amount': invoice.amount_total,
                'currency_id': invoice.currency_id.id,
                'partner_id': invoice.partner_id.id,
                'partner_type': 'customer',
                'payment_type': 'inbound',
                'journal_id': self.env['account.journal'].search([
                    ('type', '=', 'bank')
                ], limit=1).id,
                'ref': f"Auto payment for {invoice.name}",
            }
            
            payment = self.env['account.payment'].create(payment_vals)
            payment.action_post()
            
            # Reconcile with invoice
            (payment.line_ids + invoice.line_ids).filtered(
                lambda line: line.account_id == payment.destination_account_id
            ).reconcile()
            
            # Reset dunning level
            self.dunning_level = '0'
            
        except Exception as e:
            # Log error and send dunning notice instead
            _logger.error(f"Auto payment failed for subscription {self.id}: {e}")
            self._escalate_dunning()

    def _escalate_dunning(self):
        """Escalate dunning level for failed payments"""
        current_level = int(self.dunning_level or '0')
        if current_level < 4:
            self.dunning_level = str(current_level + 1)
            self.last_dunning_date = fields.Date.today()
            
            # Send dunning notice
            template_ref = f'ams_subscriptions.email_template_dunning_notice_{self.dunning_level}'
            template = self.env.ref(template_ref, raise_if_not_found=False)
            if template:
                template.send_mail(self.id, force_send=True)

    @api.model
    def cron_generate_recurring_invoices(self):
        """Cron job to generate recurring invoices"""
        today = fields.Date.today()
        
        subscriptions_to_invoice = self.search([
            ('state', 'in', ['active', 'pending_renewal']),
            ('auto_renew', '=', True),
            ('next_invoice_date', '<=', today)
        ])
        
        invoices_created = 0
        for subscription in subscriptions_to_invoice:
            try:
                invoice = subscription.action_generate_recurring_invoice()
                if invoice:
                    invoices_created += 1
            except Exception as e:
                _logger.error(f"Failed to create recurring invoice for subscription {subscription.id}: {e}")
        
        _logger.info(f"Generated {invoices_created} recurring invoices")
        return invoices_created

    def calculate_proration(self, new_price, change_date=None):
        """Calculate prorated amount for mid-cycle changes"""
        self.ensure_one()
        
        if not change_date:
            change_date = fields.Date.today()
            
        if not self.end_date or change_date >= self.end_date:
            return new_price
            
        # Calculate remaining days
        total_days = (self.end_date - self.start_date).days + 1
        remaining_days = (self.end_date - change_date).days + 1
        
        if total_days <= 0:
            return new_price
            
        proration_factor = remaining_days / total_days
        prorated_amount = new_price * proration_factor
        
        return prorated_amount

# New Analytics Models
class AMSSubscriptionAnalytics(models.Model):
    _name = 'ams.subscription.analytics'
    _description = 'AMS Subscription Analytics'
    _auto = False  # SQL View

    # Date fields
    date = fields.Date(string='Date')
    month = fields.Char(string='Month')
    year = fields.Integer(string='Year')
    
    # Subscription metrics
    subscription_id = fields.Many2one('ams.member.subscription', string='Subscription')
    partner_id = fields.Many2one('res.partner', string='Member')
    membership_type_id = fields.Many2one('ams.membership.type', string='Membership Type')
    chapter_id = fields.Many2one('ams.chapter', string='Chapter')
    
    # Revenue metrics
    mrr = fields.Float(string='Monthly Recurring Revenue')
    arr = fields.Float(string='Annual Recurring Revenue')
    revenue_amount = fields.Float(string='Revenue Amount')
    
    # Status metrics
    state = fields.Char(string='State')
    is_new_subscription = fields.Boolean(string='New Subscription')
    is_churned = fields.Boolean(string='Churned')
    is_renewed = fields.Boolean(string='Renewed')
    
    # Churn analysis
    churn_date = fields.Date(string='Churn Date')
    churn_reason = fields.Char(string='Churn Reason')
    
    # Cohort analysis
    cohort_month = fields.Char(string='Cohort Month')
    months_since_start = fields.Integer(string='Months Since Start')

    def init(self):
        """Create SQL view for subscription analytics"""
        from odoo import tools
        
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        self.env.cr.execute(f"""
            CREATE VIEW {self._table} AS (
                SELECT 
                    ROW_NUMBER() OVER () as id,
                    s.id as subscription_id,
                    s.partner_id,
                    s.membership_type_id,
                    s.chapter_id,
                    s.start_date as date,
                    TO_CHAR(s.start_date, 'YYYY-MM') as month,
                    EXTRACT(year FROM s.start_date) as year,
                    s.mrr_amount as mrr,
                    s.arr_amount as arr,
                    s.total_amount as revenue_amount,
                    s.state,
                    CASE WHEN s.parent_subscription_id IS NULL THEN true ELSE false END as is_new_subscription,
                    CASE WHEN s.state IN ('cancelled', 'lapsed') THEN true ELSE false END as is_churned,
                    CASE WHEN s.parent_subscription_id IS NOT NULL THEN true ELSE false END as is_renewed,
                    CASE WHEN s.state IN ('cancelled', 'lapsed') THEN s.end_date ELSE NULL END as churn_date,
                    NULL as churn_reason,
                    TO_CHAR(s.start_date, 'YYYY-MM') as cohort_month,
                    EXTRACT(month FROM age(CURRENT_DATE, s.start_date)) as months_since_start
                FROM ams_member_subscription s
                WHERE s.state != 'draft'
            )
        """)

class AMSSubscriptionRecurring(models.Model):
    """Model for managing subscription recurring rules"""
    _name = 'ams.subscription.recurring'
    _description = 'Subscription Recurring Rules'
    
    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(default=True)
    
    # Recurrence settings
    recurring_rule_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'), 
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    ], string='Recurrence Type', required=True)
    
    recurring_interval = fields.Integer(string='Interval', default=1, required=True)
    
    # Applied to membership types
    membership_type_ids = fields.Many2many(
        'ams.membership.type',
        string='Applicable Membership Types'
    )
    
    # Automatic invoice generation
    auto_generate_invoice = fields.Boolean(string='Auto Generate Invoice', default=True)
    invoice_lead_days = fields.Integer(string='Invoice Lead Days', default=0,
                                     help="Generate invoice X days before due date")
    
    # Payment collection
    auto_collect_payment = fields.Boolean(string='Auto Collect Payment', default=False)
    retry_failed_payments = fields.Boolean(string='Retry Failed Payments', default=True)
    max_retry_attempts = fields.Integer(string='Max Retry Attempts', default=3)
    
    def apply_to_subscription(self, subscription):
        """Apply this recurring rule to a subscription"""
        subscription.write({
            'recurring_rule_type': self.recurring_rule_type,
            'recurring_interval': self.recurring_interval,
            'auto_payment': self.auto_collect_payment,
        })
        
class MemberSubscription(models.Model):
    _inherit = 'ams.member.subscription'
    
    # Template and Bundle Fields
    template_id = fields.Many2one(
        'ams.subscription.template',
        string='Created from Template'
    )
    
    is_bundle = fields.Boolean(string='Is Bundle Subscription')
    bundle_component = fields.Boolean(string='Is Bundle Component')
    bundle_parent_id = fields.Many2one(
        'ams.member.subscription',
        string='Bundle Parent'
    )
    bundle_component_ids = fields.One2many(
        'ams.member.subscription',
        'bundle_parent_id',
        string='Bundle Components'
    )
    
    # Trial Fields
    is_trial = fields.Boolean(string='Is Trial Subscription')
    trial_end_date = fields.Date(string='Trial End Date')
    trial_converted = fields.Boolean(string='Trial Converted')
    
    # Family/Corporate Plan Fields
    is_family_plan = fields.Boolean(string='Is Family Plan')
    family_members = fields.One2many(
        'ams.family.member',
        'subscription_id',
        string='Family Members'
    )
    max_family_members = fields.Integer(string='Max Family Members', default=4)
    
    # Corporate Plan Fields  
    is_corporate_plan = fields.Boolean(string='Is Corporate Plan')
    corporate_seats = fields.Integer(string='Corporate Seats')
    used_seats = fields.Integer(string='Used Seats', compute='_compute_used_seats')
    
    def _setup_trial_period(self, trial_days):
        """Setup trial period for subscription"""
        self.ensure_one()
        
        self.write({
            'is_trial': True,
            'trial_end_date': fields.Date.today() + timedelta(days=trial_days),
            'state': 'active'  # Activate trial immediately
        })
        
        # Schedule trial end check
        self.env.ref('ams_subscriptions.cron_check_trial_periods').sudo()._trigger()

    @api.depends('family_members', 'family_members.active')
    def _compute_used_seats(self):
        """Compute used seats for corporate plans"""
        for subscription in self:
            if subscription.is_corporate_plan:
                subscription.used_seats = len(subscription.family_members.filtered('active'))
            else:
                subscription.used_seats = 0

    def add_family_member(self, partner_id, relationship=None):
        """Add a family member to family plan"""
        self.ensure_one()
        
        if not self.is_family_plan:
            raise ValidationError(_("This is not a family plan subscription"))
        
        current_members = len(self.family_members.filtered('active'))
        if current_members >= self.max_family_members:
            raise ValidationError(_("Maximum family members limit reached"))
        
        family_member = self.env['ams.family.member'].create({
            'subscription_id': self.id,
            'partner_id': partner_id,
            'relationship': relationship,
            'added_date': fields.Date.today()
        })
        
        return family_member

    @api.model
    def check_trial_periods(self):
        """Cron job to check trial periods"""
        today = fields.Date.today()
        
        expired_trials = self.search([
            ('is_trial', '=', True),
            ('trial_end_date', '<=', today),
            ('trial_converted', '=', False),
            ('state', '=', 'active')
        ])
        
        for trial in expired_trials:
            # Check if payment method is available for conversion
            if trial.payment_token_id:
                # Auto-convert trial
                trial._convert_trial()
            else:
                # Send conversion notice
                trial._send_trial_conversion_notice()

    def _convert_trial(self):
        """Convert trial to paid subscription"""
        self.ensure_one()
        
        try:
            # Generate invoice for full subscription
            invoice = self.action_generate_recurring_invoice()
            
            # Process payment if auto-payment enabled
            if self.auto_payment and self.payment_token_id:
                self._process_automatic_payment(invoice)
            
            self.write({
                'trial_converted': True,
                'is_trial': False
            })
            
            # Trigger automation
            self.env['ams.subscription.automation'].trigger_automation(
                'subscription_activated', self
            )
            
        except Exception as e:
            _logger.error(f"Trial conversion failed for subscription {self.id}: {e}")
            self._send_trial_conversion_notice()

    def _send_trial_conversion_notice(self):
        """Send trial conversion notice"""
        template = self.env.ref(
            'ams_subscriptions.email_template_trial_conversion',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)

    # Override state changes to trigger automations
    def write(self, vals):
        result = super().write(vals)
        
        # Trigger automations on state changes
        if 'state' in vals:
            for subscription in self:
                if vals['state'] == 'active':
                    self.env['ams.subscription.automation'].trigger_automation(
                        'subscription_activated', subscription
                    )
                elif vals['state'] == 'cancelled':
                    self.env['ams.subscription.automation'].trigger_automation(
                        'subscription_cancelled', subscription
                    )
                elif vals['state'] == 'expired':
                    self.env['ams.subscription.automation'].trigger_automation(
                        'subscription_expired', subscription
                    )
        
        return result


class AMSFamilyMember(models.Model):
    """Family members for family plans"""
    _name = 'ams.family.member'
    _description = 'Family Member'

    subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Family Member',
        required=True
    )
    
    relationship = fields.Selection([
        ('spouse', 'Spouse'),
        ('child', 'Child'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('other', 'Other')
    ], string='Relationship')
    
    added_date = fields.Date(string='Added Date', default=fields.Date.today)
    active = fields.Boolean(string='Active', default=True)
    
    # Benefits access
    has_full_benefits = fields.Boolean(string='Full Benefits Access', default=True)
    restricted_benefits = fields.Many2many(
        'ams.subscription.benefit',
        string='Restricted Benefits'
    )