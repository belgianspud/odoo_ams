from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AMSBillingPeriod(models.Model):
    """Define billing periods for subscription products."""
    _name = 'ams.billing.period'
    _description = 'Subscription Billing Period'
    _order = 'sequence, period_value'

    # ==========================================
    # CORE IDENTIFICATION FIELDS
    # ==========================================
    
    name = fields.Char(
        string='Period Name',
        required=True,
        help='Display name for billing period (e.g., "Monthly", "Annual")'
    )
    
    code = fields.Char(
        string='Period Code',
        help='Unique code for technical reference'
    )
    
    description = fields.Text(
        string='Description',
        help='Detailed description of this billing period'
    )

    # ==========================================
    # PERIOD DEFINITION FIELDS
    # ==========================================
    
    period_value = fields.Integer(
        string='Period Length',
        required=True,
        default=1,
        help='Number of period units (e.g., 1 for monthly, 12 for annual)'
    )
    
    period_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
    ], string='Period Unit', required=True, default='months',
       help='Unit of time for the billing period')
    
    total_days = fields.Integer(
        string='Total Days',
        compute='_compute_total_days',
        store=True,
        help='Total number of days in this billing period'
    )

    # ==========================================
    # BILLING CONFIGURATION FIELDS
    # ==========================================
    
    grace_days = fields.Integer(
        string='Grace Period (Days)',
        default=30,
        help='Days after expiration before subscription is suspended'
    )
    
    invoice_advance_days = fields.Integer(
        string='Invoice Advance (Days)',
        default=30,
        help='Days before period end to generate renewal invoice'
    )
    
    payment_terms_days = fields.Integer(
        string='Payment Terms (Days)',
        default=30,
        help='Days customer has to pay invoice after generation'
    )

    # ==========================================
    # RENEWAL AND NOTIFICATION SETTINGS
    # ==========================================
    
    renewal_reminder_days = fields.Char(
        string='Renewal Reminder Schedule',
        default='90,60,30,7',
        help='Comma-separated list of days before expiration to send reminders'
    )
    
    auto_renewal_enabled = fields.Boolean(
        string='Auto-Renewal Enabled',
        default=True,
        help='Whether auto-renewal is available for this billing period'
    )
    
    early_renewal_discount_days = fields.Integer(
        string='Early Renewal Discount Window',
        default=60,
        help='Days before expiration when early renewal discounts apply'
    )
    
    early_renewal_discount_percentage = fields.Float(
        string='Early Renewal Discount %',
        default=0.0,
        help='Discount percentage for early renewals'
    )

    # ==========================================
    # DISPLAY AND ORGANIZATION FIELDS
    # ==========================================
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order for displaying billing periods'
    )
    
    is_default = fields.Boolean(
        string='Default Period',
        default=False,
        help='Default billing period for new subscriptions'
    )
    
    popular = fields.Boolean(
        string='Popular Choice',
        default=False,
        help='Mark as popular choice in selection interfaces'
    )
    
    recommended = fields.Boolean(
        string='Recommended',
        default=False,
        help='Recommended billing period for customers'
    )

    # ==========================================
    # PRICING MULTIPLIER FIELDS
    # ==========================================
    
    price_multiplier = fields.Float(
        string='Price Multiplier',
        default=1.0,
        help='Multiplier applied to base product price for this period'
    )
    
    discount_percentage = fields.Float(
        string='Period Discount %',
        default=0.0,
        help='Standard discount for choosing this billing period'
    )

    # ==========================================
    # METADATA FIELDS
    # ==========================================
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Active billing periods are available for selection'
    )
    
    usage_count = fields.Integer(
        string='Usage Count',
        compute='_compute_usage_statistics',
        help='Number of subscriptions using this billing period'
    )

    # ==========================================
    # COMPUTED FIELDS
    # ==========================================
    
    display_name_full = fields.Char(
        string='Full Display Name',
        compute='_compute_display_names',
        store=True,
        help='Full display name with period details'
    )
    
    period_description = fields.Char(
        string='Period Description',
        compute='_compute_display_names',
        store=True,
        help='Human-readable period description'
    )

    # ==========================================
    # SQL CONSTRAINTS
    # ==========================================
    
    _sql_constraints = [
        ('positive_period_value', 'CHECK(period_value > 0)', 
         'Period length must be positive.'),
        ('positive_grace_days', 'CHECK(grace_days >= 0)', 
         'Grace period cannot be negative.'),
        ('valid_price_multiplier', 'CHECK(price_multiplier >= 0)', 
         'Price multiplier cannot be negative.'),
        ('valid_discount_percentage', 
         'CHECK(discount_percentage >= 0 AND discount_percentage <= 100)', 
         'Discount percentage must be between 0 and 100.'),
        ('unique_default', 'EXCLUDE (is_default WITH =) WHERE (is_default = true)', 
         'Only one billing period can be set as default.'),
    ]

    # ==========================================
    # COMPUTED METHODS
    # ==========================================

    @api.depends('period_value', 'period_unit')
    def _compute_total_days(self):
        """Calculate total days in billing period."""
        for period in self:
            if period.period_unit == 'days':
                period.total_days = period.period_value
            elif period.period_unit == 'weeks':
                period.total_days = period.period_value * 7
            elif period.period_unit == 'months':
                period.total_days = period.period_value * 30  # Approximate
            elif period.period_unit == 'years':
                period.total_days = period.period_value * 365  # Approximate
            else:
                period.total_days = 0

    @api.depends('name', 'period_value', 'period_unit', 'discount_percentage')
    def _compute_display_names(self):
        """Generate display names and descriptions."""
        for period in self:
            # Period description
            unit_name = dict(period._fields['period_unit'].selection)[period.period_unit]
            if period.period_value == 1:
                # Singular form
                unit_display = unit_name.rstrip('s')  # Remove 's' from plural
            else:
                unit_display = unit_name
            
            period.period_description = f"{period.period_value} {unit_display}"
            
            # Full display name with discount if applicable
            full_name = period.name
            if period.discount_percentage > 0:
                full_name += f" ({period.discount_percentage:.0f}% off)"
            elif period.recommended:
                full_name += " (Recommended)"
            elif period.popular:
                full_name += " (Popular)"
            
            period.display_name_full = full_name

    def _compute_usage_statistics(self):
        """Compute usage statistics for billing periods."""
        for period in self:
            # This would connect to subscription instances when that module exists
            # For now, set to 0 as placeholder
            period.usage_count = 0

    # ==========================================
    # VALIDATION METHODS
    # ==========================================

    @api.constrains('renewal_reminder_days')
    def _check_renewal_reminder_format(self):
        """Validate renewal reminder days format."""
        for period in self:
            if period.renewal_reminder_days:
                try:
                    days_list = [int(d.strip()) for d in period.renewal_reminder_days.split(',')]
                    if any(day < 0 for day in days_list):
                        raise ValidationError("Renewal reminder days must be non-negative")
                    if any(day > period.total_days for day in days_list):
                        raise ValidationError("Renewal reminder days cannot exceed billing period length")
                except ValueError:
                    raise ValidationError("Renewal reminder days must be comma-separated numbers")

    @api.constrains('early_renewal_discount_days', 'total_days')
    def _check_early_renewal_logic(self):
        """Validate early renewal discount settings."""
        for period in self:
            if period.early_renewal_discount_days > period.total_days:
                raise ValidationError(
                    "Early renewal discount window cannot be longer than billing period"
                )

    @api.constrains('is_default')
    def _check_single_default(self):
        """Ensure only one default billing period exists."""
        if self.filtered('is_default'):
            default_count = self.search_count([('is_default', '=', True)])
            if default_count > 1:
                raise ValidationError("Only one billing period can be set as default")

    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================

    def get_renewal_reminder_schedule(self):
        """Get renewal reminder schedule as list of days."""
        self.ensure_one()
        if not self.renewal_reminder_days:
            return []
        
        try:
            return [int(d.strip()) for d in self.renewal_reminder_days.split(',')]
        except ValueError:
            return []

    def calculate_period_price(self, base_price):
        """Calculate price for this billing period."""
        self.ensure_one()
        
        # Apply price multiplier
        period_price = base_price * self.price_multiplier
        
        # Apply period discount
        if self.discount_percentage > 0:
            discount_amount = period_price * (self.discount_percentage / 100)
            period_price -= discount_amount
        
        return {
            'base_price': base_price,
            'period_price': period_price,
            'multiplier': self.price_multiplier,
            'discount_percentage': self.discount_percentage,
            'discount_amount': base_price * self.price_multiplier - period_price,
            'savings': (base_price - period_price) if period_price < base_price else 0
        }

    def get_next_billing_date(self, start_date=None):
        """Calculate next billing date from start date."""
        self.ensure_one()
        
        if not start_date:
            start_date = fields.Date.today()
        
        if self.period_unit == 'days':
            next_date = start_date + fields.timedelta(days=self.period_value)
        elif self.period_unit == 'weeks':
            next_date = start_date + fields.timedelta(weeks=self.period_value)
        elif self.period_unit == 'months':
            # Add months properly handling month boundaries
            import calendar
            from dateutil.relativedelta import relativedelta
            next_date = start_date + relativedelta(months=self.period_value)
        elif self.period_unit == 'years':
            from dateutil.relativedelta import relativedelta
            next_date = start_date + relativedelta(years=self.period_value)
        else:
            next_date = start_date
        
        return next_date

    def get_billing_summary(self):
        """Get comprehensive billing period summary."""
        self.ensure_one()
        
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'period_value': self.period_value,
            'period_unit': self.period_unit,
            'total_days': self.total_days,
            'period_description': self.period_description,
            'display_name': self.display_name_full,
            'grace_days': self.grace_days,
            'price_multiplier': self.price_multiplier,
            'discount_percentage': self.discount_percentage,
            'auto_renewal_enabled': self.auto_renewal_enabled,
            'is_default': self.is_default,
            'popular': self.popular,
            'recommended': self.recommended,
            'renewal_reminders': self.get_renewal_reminder_schedule(),
            'early_renewal_discount': {
                'days': self.early_renewal_discount_days,
                'percentage': self.early_renewal_discount_percentage
            }
        }

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    @api.model
    def get_default_period(self):
        """Get the default billing period."""
        default = self.search([('is_default', '=', True)], limit=1)
        return default or self.search([('active', '=', True)], limit=1)

    @api.model
    def get_popular_periods(self):
        """Get popular billing periods."""
        return self.search([
            ('active', '=', True),
            ('popular', '=', True)
        ], order='sequence')

    @api.model
    def get_recommended_period(self):
        """Get the recommended billing period."""
        recommended = self.search([
            ('active', '=', True),
            ('recommended', '=', True)
        ], limit=1)
        return recommended or self.get_default_period()

    @api.model
    def get_billing_options_for_selection(self):
        """Get billing periods formatted for selection widgets."""
        periods = self.search([('active', '=', True)], order='sequence')
        return [(period.id, period.display_name_full) for period in periods]

    # ==========================================
    # ACTION METHODS
    # ==========================================

    def action_set_as_default(self):
        """Set this period as the default."""
        self.ensure_one()
        
        # Remove default from all other periods
        self.search([('is_default', '=', True)]).write({'is_default': False})
        
        # Set this as default
        self.is_default = True
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Default Period Updated',
                'message': f'{self.name} is now the default billing period.',
                'type': 'success',
            }
        }

    def action_toggle_popular(self):
        """Toggle popular status."""
        self.ensure_one()
        self.popular = not self.popular
        
        status = "marked as popular" if self.popular else "removed from popular"
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Popular Status Updated',
                'message': f'{self.name} has been {status}.',
                'type': 'info',
            }
        }

    def action_toggle_recommended(self):
        """Toggle recommended status."""
        self.ensure_one()
        self.recommended = not self.recommended
        
        status = "marked as recommended" if self.recommended else "removed from recommended"
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Recommended Status Updated',
                'message': f'{self.name} has been {status}.',
                'type': 'info',
            }
        }

    # ==========================================
    # LIFECYCLE METHODS
    # ==========================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle defaults and validation."""
        for vals in vals_list:
            # Auto-generate code if not provided
            if not vals.get('code') and vals.get('name'):
                vals['code'] = vals['name'].upper().replace(' ', '_')
        
        return super().create(vals_list)

    def name_get(self):
        """Custom display name."""
        result = []
        for period in self:
            name = period.display_name_full or period.name
            result.append((period.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Enhanced search including period details."""
        args = args or []
        domain = []
        
        if name:
            domain = ['|', '|', '|',
                     ('name', operator, name),
                     ('code', operator, name),
                     ('period_description', operator, name),
                     ('description', operator, name)]
        
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)

    def write(self, vals):
        """Override write to handle special logic."""
        # Handle default period changes
        if vals.get('is_default') and len(self) == 1:
            # Remove default from all other periods
            self.search([('id', '!=', self.id), ('is_default', '=', True)]).write({'is_default': False})
        
        return super().write(vals)