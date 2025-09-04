from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class AMSBillingPeriod(models.Model):
    """Billing period definitions for subscription management."""
    _name = 'ams.billing.period'
    _description = 'Subscription Billing Period'
    _order = 'sequence, period_value'
    _rec_name = 'name'

    # ==========================================
    # CORE IDENTIFICATION FIELDS
    # ==========================================
    
    name = fields.Char(
        string='Period Name',
        required=True,
        help='Display name for this billing period (e.g., "Monthly", "Annual")'
    )
    
    code = fields.Char(
        string='Code',
        help='Unique code for this billing period'
    )
    
    # ==========================================
    # PERIOD DEFINITION FIELDS
    # ==========================================
    
    period_value = fields.Integer(
        string='Period Length',
        required=True,
        help='Numeric value for the period length'
    )
    
    period_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
    ], string='Period Unit',
       required=True,
       default='months',
       help='Unit of measurement for the period')
    
    # ==========================================
    # BILLING CONFIGURATION FIELDS
    # ==========================================
    
    grace_days = fields.Integer(
        string='Grace Period (Days)',
        default=30,
        help='Default grace period for this billing cycle'
    )
    
    renewal_notice_days = fields.Integer(
        string='Renewal Notice (Days)',
        help='Days before expiration to send renewal notices'
    )
    
    early_renewal_days = fields.Integer(
        string='Early Renewal Window (Days)',
        help='Days before expiration to allow early renewal'
    )
    
    # ==========================================
    # DISPLAY AND ORGANIZATION FIELDS
    # ==========================================
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order for display in lists'
    )
    
    description = fields.Text(
        string='Description',
        help='Detailed description of this billing period'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this billing period is available for new subscriptions'
    )
    
    # ==========================================
    # COMPUTED FIELDS
    # ==========================================
    
    period_display = fields.Char(
        string='Period Display',
        compute='_compute_period_display',
        store=True,
        help='Human-readable period description'
    )
    
    total_days = fields.Integer(
        string='Total Days',
        compute='_compute_total_days',
        store=True,
        help='Approximate total days in this period'
    )
    
    subscription_count = fields.Integer(
        string='Subscriptions Using',
        compute='_compute_subscription_count',
        help='Number of subscription products using this period'
    )
    
    is_short_term = fields.Boolean(
        string='Short Term',
        compute='_compute_period_classification',
        help='Period is 3 months or less'
    )
    
    is_long_term = fields.Boolean(
        string='Long Term',
        compute='_compute_period_classification',
        help='Period is 12 months or more'
    )
    
    # ==========================================
    # STATISTICAL FIELDS
    # ==========================================
    
    renewal_rate = fields.Float(
        string='Average Renewal Rate %',
        compute='_compute_renewal_statistics',
        help='Historical renewal rate for this period'
    )
    
    churn_rate = fields.Float(
        string='Average Churn Rate %',
        compute='_compute_renewal_statistics',
        help='Historical churn rate for this period'
    )
    
    # ==========================================
    # SQL CONSTRAINTS
    # ==========================================
    
    _sql_constraints = [
        ('positive_period_value', 'CHECK(period_value > 0)',
         'Period value must be positive.'),
        ('positive_grace_days', 'CHECK(grace_days >= 0)',
         'Grace period cannot be negative.'),
        ('code_unique', 'UNIQUE(code)',
         'Period code must be unique.'),
    ]

    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('period_value', 'period_unit')
    def _compute_period_display(self):
        """Generate human-readable period display."""
        for record in self:
            if record.period_value and record.period_unit:
                unit_name = dict(record._fields['period_unit'].selection)[record.period_unit]
                if record.period_value == 1:
                    # Singular form
                    unit_name = unit_name.rstrip('s')
                record.period_display = f"{record.period_value} {unit_name}"
            else:
                record.period_display = "Not configured"

    @api.depends('period_value', 'period_unit')
    def _compute_total_days(self):
        """Calculate approximate total days for comparison purposes."""
        for record in self:
            if record.period_value and record.period_unit:
                # Approximate conversion to days
                multipliers = {
                    'days': 1,
                    'weeks': 7,
                    'months': 30,  # Approximate
                    'years': 365,  # Approximate
                }
                multiplier = multipliers.get(record.period_unit, 1)
                record.total_days = record.period_value * multiplier
            else:
                record.total_days = 0

    @api.depends('total_days')
    def _compute_period_classification(self):
        """Classify periods as short-term or long-term."""
        for record in self:
            record.is_short_term = record.total_days <= 90  # 3 months or less
            record.is_long_term = record.total_days >= 365  # 12 months or more

    def _compute_subscription_count(self):
        """Count subscription products using this billing period."""
        for record in self:
            # This would be enhanced when subscription instances are implemented
            # For now, we'll count based on duration matching
            matching_subscriptions = self.env['ams.subscription.product'].search([
                ('default_duration', '=', record.period_value),
                ('duration_unit', '=', record.period_unit)
            ])
            record.subscription_count = len(matching_subscriptions)

    def _compute_renewal_statistics(self):
        """Compute renewal and churn statistics."""
        for record in self:
            # Placeholder for future implementation with actual subscription data
            # This would integrate with ams_participation module for real statistics
            record.renewal_rate = 0.0
            record.churn_rate = 0.0

    # ==========================================
    # VALIDATION CONSTRAINTS
    # ==========================================

    @api.constrains('renewal_notice_days', 'total_days')
    def _validate_renewal_notice(self):
        """Validate renewal notice period is reasonable."""
        for record in self:
            if record.renewal_notice_days and record.total_days:
                if record.renewal_notice_days > record.total_days:
                    raise ValidationError(
                        f"Renewal notice period ({record.renewal_notice_days} days) "
                        f"cannot exceed total period length ({record.total_days} days)."
                    )
                
                # Warning for very long notice periods
                if record.renewal_notice_days > record.total_days * 0.5:
                    # This is a warning, not an error
                    pass

    @api.constrains('early_renewal_days', 'total_days')
    def _validate_early_renewal(self):
        """Validate early renewal window is reasonable."""
        for record in self:
            if record.early_renewal_days and record.total_days:
                if record.early_renewal_days > record.total_days:
                    raise ValidationError(
                        f"Early renewal window ({record.early_renewal_days} days) "
                        f"cannot exceed total period length ({record.total_days} days)."
                    )

    @api.constrains('grace_days', 'total_days')
    def _validate_grace_period(self):
        """Validate grace period is reasonable."""
        for record in self:
            if record.grace_days and record.total_days:
                # Grace period shouldn't be longer than the billing period itself
                if record.grace_days > record.total_days:
                    raise ValidationError(
                        f"Grace period ({record.grace_days} days) should not exceed "
                        f"the billing period length ({record.total_days} days)."
                    )

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    def calculate_next_billing_date(self, start_date):
        """Calculate the next billing date from a start date.
        
        Args:
            start_date: Starting date for calculation
            
        Returns:
            date: Next billing date
        """
        self.ensure_one()
        
        if self.period_unit == 'days':
            return start_date + fields.timedelta(days=self.period_value)
        elif self.period_unit == 'weeks':
            return start_date + fields.timedelta(weeks=self.period_value)
        elif self.period_unit == 'months':
            # Use dateutil for month arithmetic
            return start_date + relativedelta(months=self.period_value)
        elif self.period_unit == 'years':
            return start_date + relativedelta(years=self.period_value)
        return start_date

    def calculate_renewal_notice_date(self, expiry_date):
        """Calculate when to send renewal notices.
        
        Args:
            expiry_date: Subscription expiry date
            
        Returns:
            date: Date to send renewal notice
        """
        self.ensure_one()
        
        notice_days = self.renewal_notice_days or 30
        return expiry_date - fields.timedelta(days=notice_days)

    def calculate_grace_period_end(self, expiry_date):
        """Calculate grace period end date.
        
        Args:
            expiry_date: Subscription expiry date
            
        Returns:
            date: Grace period end date
        """
        self.ensure_one()
        
        return expiry_date + fields.timedelta(days=self.grace_days)

    def is_suitable_for_duration(self, duration, unit):
        """Check if this billing period matches given duration.
        
        Args:
            duration: Duration value
            unit: Duration unit
            
        Returns:
            bool: True if matching
        """
        self.ensure_one()
        
        return (self.period_value == duration and self.period_unit == unit)

    def get_billing_configuration(self):
        """Get complete billing configuration.
        
        Returns:
            dict: Billing configuration details
        """
        self.ensure_one()
        
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'period': {
                'value': self.period_value,
                'unit': self.period_unit,
                'display': self.period_display,
                'total_days': self.total_days,
            },
            'configuration': {
                'grace_days': self.grace_days,
                'renewal_notice_days': self.renewal_notice_days,
                'early_renewal_days': self.early_renewal_days,
            },
            'classification': {
                'is_short_term': self.is_short_term,
                'is_long_term': self.is_long_term,
            }
        }

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    @api.model
    def get_standard_periods(self):
        """Get commonly used billing periods.
        
        Returns:
            recordset: Standard billing periods
        """
        standard_codes = ['monthly', 'quarterly', 'annual']
        return self.search([('code', 'in', standard_codes), ('active', '=', True)])

    @api.model
    def get_period_for_duration(self, duration, unit):
        """Find billing period matching specific duration.
        
        Args:
            duration: Duration value
            unit: Duration unit
            
        Returns:
            recordset: Matching period (empty if none found)
        """
        return self.search([
            ('period_value', '=', duration),
            ('period_unit', '=', unit),
            ('active', '=', True)
        ], limit=1)

    @api.model
    def create_standard_periods(self):
        """Create standard billing periods if they don't exist.
        
        Returns:
            recordset: Created periods
        """
        standard_periods = [
            {
                'name': 'Monthly',
                'code': 'monthly',
                'period_value': 1,
                'period_unit': 'months',
                'grace_days': 7,
                'renewal_notice_days': 30,
                'sequence': 10,
            },
            {
                'name': 'Quarterly',
                'code': 'quarterly',
                'period_value': 3,
                'period_unit': 'months',
                'grace_days': 15,
                'renewal_notice_days': 45,
                'sequence': 20,
            },
            {
                'name': 'Semi-Annual',
                'code': 'semi_annual',
                'period_value': 6,
                'period_unit': 'months',
                'grace_days': 30,
                'renewal_notice_days': 60,
                'sequence': 30,
            },
            {
                'name': 'Annual',
                'code': 'annual',
                'period_value': 12,
                'period_unit': 'months',
                'grace_days': 30,
                'renewal_notice_days': 90,
                'sequence': 40,
            },
            {
                'name': 'Biennial',
                'code': 'biennial',
                'period_value': 2,
                'period_unit': 'years',
                'grace_days': 60,
                'renewal_notice_days': 120,
                'sequence': 50,
            }
        ]
        
        created_periods = self.env['ams.billing.period']
        
        for period_data in standard_periods:
            # Check if period already exists
            existing = self.search([('code', '=', period_data['code'])])
            if not existing:
                created_periods |= self.create(period_data)
        
        return created_periods

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set defaults."""
        for vals in vals_list:
            # Auto-generate code if not provided
            if not vals.get('code'):
                vals['code'] = self._generate_code(vals)
            
            # Set default renewal notice if not provided
            if not vals.get('renewal_notice_days'):
                vals['renewal_notice_days'] = self._calculate_default_renewal_notice(vals)
        
        return super().create(vals_list)

    def _generate_code(self, vals):
        """Generate code from name and period."""
        name = vals.get('name', '').lower().replace(' ', '_')
        period_value = vals.get('period_value', '')
        period_unit = vals.get('period_unit', '')
        
        if name:
            return name
        else:
            return f"{period_value}_{period_unit}"

    def _calculate_default_renewal_notice(self, vals):
        """Calculate sensible default for renewal notice."""
        period_value = vals.get('period_value', 1)
        period_unit = vals.get('period_unit', 'months')
        
        # Calculate approximate days
        multipliers = {'days': 1, 'weeks': 7, 'months': 30, 'years': 365}
        total_days = period_value * multipliers.get(period_unit, 1)
        
        # Renewal notice should be roughly 10-25% of period length
        if total_days <= 30:  # Short periods
            return max(7, int(total_days * 0.25))
        elif total_days <= 90:  # Quarterly
            return 30
        elif total_days <= 365:  # Annual
            return 90
        else:  # Multi-year
            return 120

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_view_matching_subscriptions(self):
        """View subscription products using this billing period."""
        self.ensure_one()
        
        return {
            'name': f'Subscriptions - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.product',
            'view_mode': 'tree,form',
            'domain': [
                ('default_duration', '=', self.period_value),
                ('duration_unit', '=', self.period_unit)
            ],
            'context': {
                'default_default_duration': self.period_value,
                'default_duration_unit': self.period_unit,
            }
        }

    # ==========================================
    # DISPLAY AND SEARCH METHODS
    # ==========================================

    def name_get(self):
        """Custom display name with period information."""
        result = []
        for record in self:
            if record.period_display:
                name = f"{record.name} ({record.period_display})"
            else:
                name = record.name
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced search including code and period display."""
        args = args or []
        domain = []
        
        if name:
            domain = ['|', '|', '|',
                     ('name', operator, name),
                     ('code', operator, name),
                     ('period_display', operator, name),
                     ('description', operator, name)]
        
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)