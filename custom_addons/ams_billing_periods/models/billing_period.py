# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class AMSBillingPeriod(models.Model):
    """Billing period definitions for association subscriptions and renewals."""
    
    _name = 'ams.billing.period'
    _inherit = ['mail.thread']
    _description = 'AMS Billing Period'
    _order = 'sequence, name'
    
    # ========================================================================
    # FIELDS
    # ========================================================================
    
    name = fields.Char(
        string="Period Name",
        required=True,
        help="Display name for this billing period"
    )
    
    code = fields.Char(
        string="Code",
        required=True,
        help="Unique code for this billing period"
    )
    
    duration_value = fields.Integer(
        string="Duration Value",
        required=True,
        help="Numeric value for the duration (e.g., 1, 3, 12)"
    )
    
    duration_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
    ], string="Duration Unit", required=True, help="Unit of time for the duration")
    
    sequence = fields.Integer(
        string="Display Order",
        default=10,
        help="Order for displaying billing periods"
    )
    
    is_default = fields.Boolean(
        string="Default Period",
        default=False,
        help="Mark this as the default billing period for new subscriptions"
    )
    
    description = fields.Text(
        string="Description",
        help="Detailed description of this billing period"
    )
    
    active = fields.Boolean(
        string="Active",
        default=True,
        help="Inactive periods cannot be used for new subscriptions"
    )
    
    # ========================================================================
    # COMPUTED FIELDS
    # ========================================================================
    
    total_days = fields.Integer(
        string="Total Days",
        compute='_compute_total_days',
        store=True,
        help="Approximate total days in this billing period"
    )
    
    period_summary = fields.Char(
        string="Period Summary",
        compute='_compute_period_summary',
        help="Human-readable summary of the billing period"
    )
    
    # ========================================================================
    # SQL CONSTRAINTS
    # ========================================================================
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Billing period code must be unique!'),
        ('name_unique', 'UNIQUE(name)', 'Billing period name must be unique!'),
        ('duration_value_positive', 'CHECK(duration_value > 0)', 'Duration value must be positive!'),
    ]
    
    # ========================================================================
    # CONSTRAINT METHODS
    # ========================================================================
    
    @api.constrains('code')
    def _check_code_format(self):
        """Validate code format."""
        for record in self:
            if record.code:
                if not record.code.replace('_', '').replace('-', '').isalnum():
                    raise ValidationError(_("Code can only contain letters, numbers, underscores, and hyphens"))
                if len(record.code) > 25:
                    raise ValidationError(_("Code cannot be longer than 25 characters"))
    
    @api.constrains('is_default')
    def _check_single_default(self):
        """Ensure only one billing period is marked as default."""
        if self.is_default:
            # Check if there's already a default period (excluding current record)
            existing_default = self.search([
                ('is_default', '=', True),
                ('id', '!=', self.id)
            ])
            if existing_default:
                raise ValidationError(_("Only one billing period can be marked as default. "
                                      "Please uncheck the default flag on '%s' first.") % existing_default.name)
    
    @api.constrains('duration_value', 'duration_unit')
    def _check_duration_validity(self):
        """Validate duration combinations."""
        for record in self:
            if record.duration_value <= 0:
                raise ValidationError(_("Duration value must be greater than 0"))
            
            # Check for reasonable limits
            if record.duration_unit == 'days' and record.duration_value > 3650:  # ~10 years
                raise ValidationError(_("Duration in days cannot exceed 3650 (approximately 10 years)"))
            elif record.duration_unit == 'weeks' and record.duration_value > 520:  # ~10 years
                raise ValidationError(_("Duration in weeks cannot exceed 520 (approximately 10 years)"))
            elif record.duration_unit == 'months' and record.duration_value > 120:  # 10 years
                raise ValidationError(_("Duration in months cannot exceed 120 (10 years)"))
            elif record.duration_unit == 'years' and record.duration_value > 10:
                raise ValidationError(_("Duration in years cannot exceed 10"))
    
    # ========================================================================
    # COMPUTE METHODS
    # ========================================================================
    
    @api.depends('duration_value', 'duration_unit')
    def _compute_total_days(self):
        """Compute approximate total days for the billing period."""
        for record in self:
            if record.duration_value and record.duration_unit:
                if record.duration_unit == 'days':
                    record.total_days = record.duration_value
                elif record.duration_unit == 'weeks':
                    record.total_days = record.duration_value * 7
                elif record.duration_unit == 'months':
                    # Use average of 30.44 days per month (365.25/12)
                    record.total_days = int(record.duration_value * 30.44)
                elif record.duration_unit == 'years':
                    # Use 365.25 days per year (accounting for leap years)
                    record.total_days = int(record.duration_value * 365.25)
                else:
                    record.total_days = 0
            else:
                record.total_days = 0
    
    @api.depends('duration_value', 'duration_unit')
    def _compute_period_summary(self):
        """Compute human-readable summary."""
        for record in self:
            if record.duration_value and record.duration_unit:
                unit_name = record.duration_unit
                if record.duration_value == 1:
                    # Singular form
                    unit_name = unit_name.rstrip('s')
                
                record.period_summary = f"{record.duration_value} {unit_name.title()}"
                
                # Add approximate days for non-day units
                if record.duration_unit != 'days' and record.total_days:
                    record.period_summary += f" (~{record.total_days} days)"
            else:
                record.period_summary = ""
    
    # ========================================================================
    # ONCHANGE METHODS
    # ========================================================================
    
    @api.onchange('name')
    def _onchange_name(self):
        """Auto-generate code from name if code is empty."""
        if self.name and not self.code:
            # Generate code from name: "Monthly Billing" -> "MONTHLY_BILLING"
            self.code = self.name.upper().replace(' ', '_').replace('-', '_')
            # Remove special characters except underscores
            self.code = ''.join(c for c in self.code if c.isalnum() or c == '_')
    
    @api.onchange('duration_value', 'duration_unit')
    def _onchange_duration(self):
        """Update name suggestion based on duration."""
        if self.duration_value and self.duration_unit and not self.name:
            # Suggest name based on common periods
            suggestions = {
                (1, 'days'): 'Daily',
                (7, 'days'): 'Weekly',
                (1, 'weeks'): 'Weekly',
                (2, 'weeks'): 'Bi-Weekly',
                (1, 'months'): 'Monthly',
                (3, 'months'): 'Quarterly',
                (6, 'months'): 'Semi-Annual',
                (12, 'months'): 'Annual',
                (1, 'years'): 'Annual',
                (2, 'years'): 'Biennial',
                (24, 'months'): 'Biennial',
            }
            
            suggestion = suggestions.get((self.duration_value, self.duration_unit))
            if suggestion:
                self.name = suggestion
            else:
                # Generic suggestion
                unit_name = self.duration_unit
                if self.duration_value == 1:
                    unit_name = unit_name.rstrip('s')
                self.name = f"{self.duration_value} {unit_name.title()}"
    
    # ========================================================================
    # CRUD METHODS
    # ========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle default period logic."""
        # If creating the first period and no default is set, make it default
        for vals in vals_list:
            if not self.search_count([]) and not vals.get('is_default'):
                vals['is_default'] = True
        
        return super().create(vals_list)
    
    def write(self, vals):
        """Override write to handle default period changes."""
        # If setting as default, unset other defaults first
        if vals.get('is_default'):
            other_defaults = self.search([
                ('is_default', '=', True),
                ('id', 'not in', self.ids)
            ])
            if other_defaults:
                other_defaults.write({'is_default': False})
        
        # If unsetting default, ensure at least one remains default (but only check this outside of data loading)
        if 'is_default' in vals and not vals['is_default'] and not self.env.context.get('install_mode'):
            if self.filtered('is_default'):
                # Check if this would leave no default periods
                other_defaults = self.search([
                    ('is_default', '=', True),
                    ('id', 'not in', self.ids)
                ])
                if not other_defaults:
                    raise ValidationError(_("At least one billing period must be marked as default"))
        
        return super().write(vals)
    
    def copy(self, default=None):
        """Override copy to ensure unique names and codes."""
        default = dict(default or {})
        default.update({
            'name': _("%s (Copy)") % self.name,
            'code': "%s_COPY" % self.code,
            'is_default': False,  # Copy should not be default
        })
        return super().copy(default)
    
    # ========================================================================
    # BUSINESS METHODS
    # ========================================================================
    
    @api.model
    def get_default_period(self):
        """Get the default billing period.
        
        Returns:
            recordset: Default billing period or first active period
        """
        default_period = self.search([('is_default', '=', True)], limit=1)
        if not default_period:
            # Fallback to first active period
            default_period = self.search([('active', '=', True)], limit=1)
        return default_period
    
    def calculate_next_date(self, start_date=None):
        """Calculate the next billing date from a start date.
        
        Args:
            start_date (date, optional): Start date for calculation. Defaults to today.
            
        Returns:
            date: Next billing date
        """
        self.ensure_one()
        
        if start_date is None:
            start_date = fields.Date.today()
        
        if isinstance(start_date, str):
            start_date = fields.Date.from_string(start_date)
        
        if self.duration_unit == 'days':
            return start_date + timedelta(days=self.duration_value)
        elif self.duration_unit == 'weeks':
            return start_date + timedelta(weeks=self.duration_value)
        elif self.duration_unit == 'months':
            return start_date + relativedelta(months=self.duration_value)
        elif self.duration_unit == 'years':
            return start_date + relativedelta(years=self.duration_value)
        else:
            return start_date
    
    def calculate_period_end(self, start_date=None):
        """Calculate the end date of a billing period.
        
        Args:
            start_date (date, optional): Start date. Defaults to today.
            
        Returns:
            date: End date of the billing period
        """
        self.ensure_one()
        next_date = self.calculate_next_date(start_date)
        # End date is one day before the next period starts
        return next_date - timedelta(days=1)
    
    def get_period_range(self, start_date=None):
        """Get the date range for a billing period.
        
        Args:
            start_date (date, optional): Start date. Defaults to today.
            
        Returns:
            tuple: (start_date, end_date)
        """
        self.ensure_one()
        
        if start_date is None:
            start_date = fields.Date.today()
        
        end_date = self.calculate_period_end(start_date)
        return (start_date, end_date)
    
    @api.model
    def get_periods_by_duration(self, duration_unit=None):
        """Get billing periods filtered by duration unit.
        
        Args:
            duration_unit (str, optional): Filter by duration unit
            
        Returns:
            recordset: Filtered billing periods
        """
        domain = [('active', '=', True)]
        if duration_unit:
            domain.append(('duration_unit', '=', duration_unit))
        
        return self.search(domain)
    
    @api.model
    def get_shortest_period(self):
        """Get the shortest billing period by total days."""
        periods = self.search([('active', '=', True)])
        if periods:
            return min(periods, key=lambda p: p.total_days)
        return self.browse()
    
    @api.model
    def get_longest_period(self):
        """Get the longest billing period by total days."""
        periods = self.search([('active', '=', True)])
        if periods:
            return max(periods, key=lambda p: p.total_days)
        return self.browse()
    
    def get_period_description(self):
        """Get formatted description of the billing period.
        
        Returns:
            str: Formatted description
        """
        self.ensure_one()
        
        description = self.period_summary
        if self.description:
            description += f" - {self.description}"
        
        if self.is_default:
            description += _(" (Default)")
        
        return description
    
    def action_set_as_default(self):
        """Set this period as the default billing period."""
        self.ensure_one()
        
        # Unset other defaults
        other_defaults = self.search([
            ('is_default', '=', True),
            ('id', '!=', self.id)
        ])
        other_defaults.write({'is_default': False})
        
        # Set this one as default
        self.write({'is_default': True})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Default Period Updated'),
                'message': _('"%s" has been set as the default billing period.') % self.name,
                'type': 'success',
            }
        }
    
    def toggle_active(self):
        """Toggle active status."""
        for record in self:
            # Prevent deactivating the default period
            if record.is_default and record.active:
                raise ValidationError(_("Cannot deactivate the default billing period. "
                                      "Please set another period as default first."))
            record.active = not record.active
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def name_get(self):
        """Custom name display."""
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f"[{record.code}] {name}"
            if record.period_summary:
                name = f"{name} ({record.period_summary})"
            if record.is_default:
                name = f"{name} ★"
            result.append((record.id, name))
        return result
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """Custom name search to include code and period summary."""
        args = args or []
        
        if name:
            # Search in name, code, and period summary
            domain = [
                '|', '|',
                ('name', operator, name),
                ('code', operator, name),
                ('period_summary', operator, name)
            ]
            args = domain + args
        
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)