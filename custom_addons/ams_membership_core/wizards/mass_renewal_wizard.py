# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class MassRenewalWizard(models.TransientModel):
    _name = 'ams.mass.renewal.wizard'
    _description = 'Mass Renewal Wizard'

    # Batch Information
    name = fields.Char('Batch Name', required=True, 
                      default=lambda self: f"Mass Renewal {fields.Date.today()}")
    batch_code = fields.Char('Batch Code', readonly=True,
                            default=lambda self: self.env['ir.sequence'].next_by_code('ams.mass.renewal'))
    
    # Selection Criteria
    renewal_type = fields.Selection([
        ('membership', 'Memberships Only'),
        ('subscription', 'Subscriptions Only'),
        ('both', 'Both Memberships & Subscriptions'),
    ], string='Renewal Type', default='membership', required=True)
    
    target_records = fields.Selection([
        ('expiring', 'Expiring Soon'),
        ('expired', 'Already Expired'),
        ('custom_date', 'Custom Date Range'),
        ('selected', 'Selected Records'),
    ], string='Target Records', default='expiring', required=True)
    
    # Date Filters
    expiry_days_ahead = fields.Integer('Days Ahead for Expiring', default=60,
                                      help='Include records expiring within this many days')
    custom_start_date = fields.Date('Custom Start Date')
    custom_end_date = fields.Date('Custom End Date')
    
    # Member Type Filters
    member_type_ids = fields.Many2many('ams.member.type', string='Member Types',
                                      help='Leave empty to include all member types')
    
    # Product Filters
    product_ids = fields.Many2many('product.product', string='Products',
                                  domain=[('is_subscription_product', '=', True)],
                                  help='Leave empty to include all subscription products')
    
    # Status Filters
    include_active = fields.Boolean('Include Active', default=True)
    include_grace = fields.Boolean('Include Grace Period', default=True)
    include_suspended = fields.Boolean('Include Suspended', default=False)
    
    # Renewal Settings
    new_renewal_period = fields.Selection([
        ('keep_existing', 'Keep Existing Period'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='New Renewal Period', default='keep_existing', required=True)
    
    apply_early_bird_discount = fields.Boolean('Apply Early Bird Discount', default=False)
    early_bird_discount_percent = fields.Float('Early Bird Discount %', default=5.0)
    
    # Processing Options
    create_invoices = fields.Boolean('Create Invoices', default=True)
    send_renewal_emails = fields.Boolean('Send Renewal Emails', default=True)
    auto_confirm_renewals = fields.Boolean('Auto Confirm Renewals', default=False,
                                          help='Automatically confirm renewals (skip draft state)')
    
    # Preview and Results
    eligible_count = fields.Integer('Eligible Records', compute='_compute_eligible_count')
    preview_line_ids = fields.One2many('ams.mass.renewal.preview', 'wizard_id', 'Preview Lines')
    
    # Processing Results
    processed_count = fields.Integer('Processed Records', readonly=True, default=0)
    success_count = fields.Integer('Successful Renewals', readonly=True, default=0)
    error_count = fields.Integer('Errors', readonly=True, default=0)
    processing_log = fields.Text('Processing Log', readonly=True)

    @api.depends('renewal_type', 'target_records', 'expiry_days_ahead', 'custom_start_date', 
                 'custom_end_date', 'member_type_ids', 'product_ids', 'include_active', 
                 'include_grace', 'include_suspended')
    def _compute_eligible_count(self):
        for wizard in self:
            try:
                eligible_records = wizard._get_eligible_records()
                if isinstance(eligible_records, tuple):
                    # Both memberships and subscriptions
                    memberships, subscriptions = eligible_records
                    wizard.eligible_count = len(memberships) + len(subscriptions)
                else:
                    wizard.eligible_count = len(eligible_records)
            except Exception as e:
                _logger.warning(f"Error computing eligible count: {str(e)}")
                wizard.eligible_count = 0

    def _get_eligible_records(self):
        """Get records eligible for mass renewal"""
        self.ensure_one()
        
        if self.renewal_type == 'membership':
            return self._get_eligible_memberships()
        elif self.renewal_type == 'subscription':
            return self._get_eligible_subscriptions()
        else:  # both
            memberships = self._get_eligible_memberships()
            subscriptions = self._get_eligible_subscriptions()
            return memberships, subscriptions

    def _get_eligible_memberships(self):
        """Get eligible memberships"""
        domain = self._build_membership_domain()
        return self.env['ams.membership'].search(domain)

    def _get_eligible_subscriptions(self):
        """Get eligible subscriptions"""
        domain = self._build_subscription_domain()
        return self.env['ams.subscription'].search(domain)

    def _build_membership_domain(self):
        """Build domain for membership selection"""
        domain = []
        
        # Status filters
        status_list = []
        if self.include_active:
            status_list.append('active')
        if self.include_grace:
            status_list.append('grace')
        if self.include_suspended:
            status_list.append('suspended')
        
        if status_list:
            domain.append(('state', 'in', status_list))
        
        # Member type filter
        if self.member_type_ids:
            domain.append(('member_type_id', 'in', self.member_type_ids.ids))
        
        # Product filter
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        # Date filters
        domain.extend(self._build_date_domain())
        
        return domain

    def _build_subscription_domain(self):
        """Build domain for subscription selection"""
        domain = []
        
        # Status filters
        status_list = []
        if self.include_active:
            status_list.append('active')
        if self.include_suspended:
            status_list.append('suspended')
        
        if status_list:
            domain.append(('state', 'in', status_list))
        
        # Product filter
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        # Date filters
        domain.extend(self._build_date_domain())
        
        return domain

    def _build_date_domain(self):
        """Build date domain based on target records"""
        domain = []
        today = fields.Date.today()
        
        if self.target_records == 'expiring':
            future_date = today + timedelta(days=self.expiry_days_ahead)
            domain.extend([
                ('end_date', '>=', today),
                ('end_date', '<=', future_date)
            ])
        elif self.target_records == 'expired':
            domain.append(('end_date', '<', today))
        elif self.target_records == 'custom_date':
            if self.custom_start_date:
                domain.append(('end_date', '>=', self.custom_start_date))
            if self.custom_end_date:
                domain.append(('end_date', '<=', self.custom_end_date))
        
        return domain

    def action_preview_records(self):
        """Preview eligible records before processing"""
        self.ensure_one()
        
        # Clear existing preview lines
        self.preview_line_ids.unlink()
        
        preview_lines = []
        
        try:
            if self.renewal_type in ['membership', 'both']:
                memberships = self._get_eligible_memberships()
                for membership in memberships:
                    preview_lines.append({
                        'wizard_id': self.id,
                        'record_type': 'membership',
                        'membership_id': membership.id,
                        'partner_id': membership.partner_id.id,
                        'product_id': membership.product_id.id,
                        'current_end_date': membership.end_date,
                        'proposed_end_date': self._calculate_new_end_date(membership.end_date),
                        'current_amount': membership.membership_fee,
                        'proposed_amount': self._calculate_renewal_amount(membership.membership_fee),
                    })
            
            if self.renewal_type in ['subscription', 'both']:
                subscriptions = self._get_eligible_subscriptions()
                for subscription in subscriptions:
                    preview_lines.append({
                        'wizard_id': self.id,
                        'record_type': 'subscription',
                        'subscription_id': subscription.id,
                        'partner_id': subscription.partner_id.id,
                        'product_id': subscription.product_id.id,
                        'current_end_date': subscription.end_date,
                        'proposed_end_date': self._calculate_new_end_date(subscription.end_date),
                        'current_amount': subscription.subscription_fee,
                        'proposed_amount': self._calculate_renewal_amount(subscription.subscription_fee),
                    })
            
            if preview_lines:
                self.env['ams.mass.renewal.preview'].create(preview_lines)
        
        except Exception as e:
            raise UserError(_("Error creating preview: %s") % str(e))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mass Renewal Preview'),
            'res_model': 'ams.mass.renewal.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('ams_membership_core.view_mass_renewal_wizard_preview').id,
            'target': 'new',
        }

    def _calculate_new_end_date(self, current_end_date):
        """Calculate new end date based on renewal period"""
        if not current_end_date:
            current_end_date = fields.Date.today()
            
        base_date = max(current_end_date, fields.Date.today())
        
        if self.new_renewal_period == 'keep_existing':
            # Add one year by default if keeping existing
            return base_date + relativedelta(years=1)
        elif self.new_renewal_period == 'monthly':
            return base_date + relativedelta(months=1)
        elif self.new_renewal_period == 'quarterly':
            return base_date + relativedelta(months=3)
        elif self.new_renewal_period == 'semi_annual':
            return base_date + relativedelta(months=6)
        else:  # annual
            return base_date + relativedelta(years=1)

    def _calculate_renewal_amount(self, current_amount):
        """Calculate renewal amount with discounts"""
        if not current_amount:
            current_amount = 0.0
            
        amount = current_amount
        
        if self.apply_early_bird_discount and self.early_bird_discount_percent:
            discount = amount * (self.early_bird_discount_percent / 100.0)
            amount -= discount
        
        return amount

    def action_process_renewals(self):
        """Process mass renewals"""
        self.ensure_one()
        
        if not self.eligible_count:
            raise UserError(_("No eligible records found for renewal."))
        
        # Initialize counters and log
        processed_count = 0
        success_count = 0
        error_count = 0
        log_entries = []
        
        log_entries.append(f"Starting mass renewal batch: {self.name}")
        log_entries.append(f"Batch code: {self.batch_code}")
        log_entries.append(f"Target records: {self.eligible_count}")
        log_entries.append("-" * 50)
        
        try:
            if self.renewal_type in ['membership', 'both']:
                memberships = self._get_eligible_memberships()
                for membership in memberships:
                    try:
                        self._process_membership_renewal(membership, log_entries)
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        log_entries.append(f"ERROR - {membership.partner_id.name}: {str(e)}")
                        _logger.error(f"Error processing membership {membership.id}: {str(e)}")
                    processed_count += 1
            
            if self.renewal_type in ['subscription', 'both']:
                subscriptions = self._get_eligible_subscriptions()
                for subscription in subscriptions:
                    try:
                        self._process_subscription_renewal(subscription, log_entries)
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        log_entries.append(f"ERROR - {subscription.partner_id.name}: {str(e)}")
                        _logger.error(f"Error processing subscription {subscription.id}: {str(e)}")
                    processed_count += 1
                    
        except Exception as e:
            log_entries.append(f"CRITICAL ERROR: {str(e)}")
            _logger.error(f"Critical error in mass renewal: {str(e)}")
        
        # Update wizard with results
        log_entries.append("-" * 50)
        log_entries.append(f"Processing completed:")
        log_entries.append(f"- Total processed: {processed_count}")
        log_entries.append(f"- Successful: {success_count}")
        log_entries.append(f"- Errors: {error_count}")
        
        self.write({
            'processed_count': processed_count,
            'success_count': success_count,
            'error_count': error_count,
            'processing_log': '\n'.join(log_entries)
        })
        
        return self._show_results()

    def _process_membership_renewal(self, membership, log_entries):
        """Process individual membership renewal"""
        renewal_vals = {
            'membership_id': membership.id,
            'renewal_date': fields.Date.today(),
            'new_end_date': self._calculate_new_end_date(membership.end_date),
            'amount': self._calculate_renewal_amount(membership.membership_fee),
            'renewal_type': 'manual',
            'state': 'confirmed' if self.auto_confirm_renewals else 'draft',
        }
        
        if self.new_renewal_period != 'keep_existing':
            renewal_vals['renewal_period'] = self.new_renewal_period
        
        renewal = self.env['ams.renewal'].create(renewal_vals)
        
        if self.create_invoices:
            try:
                renewal.action_create_invoice()
            except Exception as e:
                _logger.warning(f"Failed to create invoice for renewal {renewal.name}: {str(e)}")
        
        log_entries.append(f"SUCCESS - {membership.partner_id.name}: Renewal {renewal.name} created")

    def _process_subscription_renewal(self, subscription, log_entries):
        """Process individual subscription renewal"""
        renewal_vals = {
            'subscription_id': subscription.id,
            'renewal_date': fields.Date.today(),
            'new_end_date': self._calculate_new_end_date(subscription.end_date),
            'amount': self._calculate_renewal_amount(subscription.subscription_fee),
            'renewal_type': 'manual',
            'state': 'confirmed' if self.auto_confirm_renewals else 'draft',
        }
        
        if self.new_renewal_period != 'keep_existing':
            renewal_vals['renewal_period'] = self.new_renewal_period
        
        renewal = self.env['ams.renewal'].create(renewal_vals)
        
        if self.create_invoices:
            try:
                renewal.action_create_invoice()
            except Exception as e:
                _logger.warning(f"Failed to create invoice for renewal {renewal.name}: {str(e)}")
        
        log_entries.append(f"SUCCESS - {subscription.partner_id.name}: Renewal {renewal.name} created")

    def _show_results(self):
        """Show processing results"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mass Renewal Results'),
            'res_model': 'ams.mass.renewal.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('ams_membership_core.view_mass_renewal_wizard_results').id,
            'target': 'new',
        }

    # Constraints
    @api.constrains('expiry_days_ahead')
    def _check_expiry_days(self):
        for wizard in self:
            if wizard.expiry_days_ahead < 0:
                raise ValidationError(_("Days ahead cannot be negative."))

    @api.constrains('early_bird_discount_percent')
    def _check_discount_percent(self):
        for wizard in self:
            if wizard.apply_early_bird_discount:
                if wizard.early_bird_discount_percent < 0 or wizard.early_bird_discount_percent > 100:
                    raise ValidationError(_("Discount percentage must be between 0 and 100."))

    @api.constrains('custom_start_date', 'custom_end_date')
    def _check_custom_dates(self):
        for wizard in self:
            if (wizard.target_records == 'custom_date' and 
                wizard.custom_start_date and wizard.custom_end_date):
                if wizard.custom_end_date <= wizard.custom_start_date:
                    raise ValidationError(_("End date must be after start date."))


class MassRenewalPreview(models.TransientModel):
    _name = 'ams.mass.renewal.preview'
    _description = 'Mass Renewal Preview Line'

    wizard_id = fields.Many2one('ams.mass.renewal.wizard', 'Wizard', required=True, ondelete='cascade')
    
    record_type = fields.Selection([
        ('membership', 'Membership'),
        ('subscription', 'Subscription'),
    ], string='Type', required=True)
    
    membership_id = fields.Many2one('ams.membership', 'Membership')
    subscription_id = fields.Many2one('ams.subscription', 'Subscription')
    
    partner_id = fields.Many2one('res.partner', 'Member/Subscriber', required=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    
    current_end_date = fields.Date('Current End Date')
    proposed_end_date = fields.Date('Proposed End Date')
    
    current_amount = fields.Monetary('Current Amount', currency_field='currency_id')
    proposed_amount = fields.Monetary('Proposed Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    include_in_batch = fields.Boolean('Include in Batch', default=True)