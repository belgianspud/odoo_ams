# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class TestAMSBillingPeriod(TransactionCase):
    """Test cases for AMS Billing Period model."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.billing_period_model = self.env['ams.billing.period']
        
        # Clean existing default periods for test isolation
        existing_defaults = self.billing_period_model.search([('is_default', '=', True)])
        existing_defaults.write({'is_default': False})
        
    def test_billing_period_creation(self):
        """Test basic billing period creation."""
        period = self.billing_period_model.create({
            'name': 'Test Monthly',
            'code': 'TEST_MONTHLY',
            'duration_value': 1,
            'duration_unit': 'months',
        })
        
        self.assertEqual(period.name, 'Test Monthly')
        self.assertEqual(period.code, 'TEST_MONTHLY')
        self.assertEqual(period.duration_value, 1)
        self.assertEqual(period.duration_unit, 'months')
        self.assertTrue(period.active)

    def test_code_auto_generation(self):
        """Test automatic code generation from name."""
        period = self.billing_period_model.new({
            'name': 'Annual Billing Period'
        })
        period._onchange_name()
        
        self.assertEqual(period.code, 'ANNUAL_BILLING_PERIOD')

    def test_name_suggestion_from_duration(self):
        """Test name suggestion based on duration."""
        # Test monthly suggestion
        period = self.billing_period_model.new({
            'duration_value': 1,
            'duration_unit': 'months'
        })
        period._onchange_duration()
        self.assertEqual(period.name, 'Monthly')
        
        # Test quarterly suggestion
        period = self.billing_period_model.new({
            'duration_value': 3,
            'duration_unit': 'months'
        })
        period._onchange_duration()
        self.assertEqual(period.name, 'Quarterly')
        
        # Test annual suggestion
        period = self.billing_period_model.new({
            'duration_value': 12,
            'duration_unit': 'months'
        })
        period._onchange_duration()
        self.assertEqual(period.name, 'Annual')

    def test_unique_constraints(self):
        """Test unique constraints on code and name."""
        self.billing_period_model.create({
            'name': 'Test Period',
            'code': 'TEST',
            'duration_value': 1,
            'duration_unit': 'months',
        })
        
        # Test duplicate code
        with self.assertRaises(Exception):
            self.billing_period_model.create({
                'name': 'Another Period',
                'code': 'TEST',
                'duration_value': 2,
                'duration_unit': 'months',
            })
        
        # Test duplicate name
        with self.assertRaises(Exception):
            self.billing_period_model.create({
                'name': 'Test Period',
                'code': 'ANOTHER',
                'duration_value': 2,
                'duration_unit': 'months',
            })

    def test_code_format_validation(self):
        """Test code format validation."""
        # Valid code
        period = self.billing_period_model.create({
            'name': 'Valid Code',
            'code': 'VALID_CODE-123',
            'duration_value': 1,
            'duration_unit': 'months',
        })
        self.assertEqual(period.code, 'VALID_CODE-123')
        
        # Invalid code (special characters)
        with self.assertRaises(ValidationError):
            self.billing_period_model.create({
                'name': 'Invalid Code',
                'code': 'INVALID@CODE!',
                'duration_value': 1,
                'duration_unit': 'months',
            })
        
        # Invalid code (too long)
        with self.assertRaises(ValidationError):
            self.billing_period_model.create({
                'name': 'Long Code',
                'code': 'THIS_CODE_IS_TOO_LONG_FOR_VALIDATION',
                'duration_value': 1,
                'duration_unit': 'months',
            })

    def test_duration_validation(self):
        """Test duration value validation."""
        # Invalid duration value (zero)
        with self.assertRaises(ValidationError):
            self.billing_period_model.create({
                'name': 'Zero Duration',
                'code': 'ZERO',
                'duration_value': 0,
                'duration_unit': 'months',
            })
        
        # Invalid duration value (negative)
        with self.assertRaises(ValidationError):
            self.billing_period_model.create({
                'name': 'Negative Duration',
                'code': 'NEGATIVE',
                'duration_value': -1,
                'duration_unit': 'months',
            })
        
        # Invalid duration (too many years)
        with self.assertRaises(ValidationError):
            self.billing_period_model.create({
                'name': 'Too Long',
                'code': 'TOO_LONG',
                'duration_value': 15,
                'duration_unit': 'years',
            })

    def test_total_days_computation(self):
        """Test total days computation for different units."""
        # Test days
        period_days = self.billing_period_model.create({
            'name': 'Test Days',
            'code': 'TEST_DAYS',
            'duration_value': 7,
            'duration_unit': 'days',
        })
        self.assertEqual(period_days.total_days, 7)
        
        # Test weeks
        period_weeks = self.billing_period_model.create({
            'name': 'Test Weeks',
            'code': 'TEST_WEEKS',
            'duration_value': 2,
            'duration_unit': 'weeks',
        })
        self.assertEqual(period_weeks.total_days, 14)
        
        # Test months (approximate)
        period_months = self.billing_period_model.create({
            'name': 'Test Months',
            'code': 'TEST_MONTHS',
            'duration_value': 1,
            'duration_unit': 'months',
        })
        self.assertEqual(period_months.total_days, 30)  # int(1 * 30.44)
        
        # Test years (approximate)
        period_years = self.billing_period_model.create({
            'name': 'Test Years',
            'code': 'TEST_YEARS',
            'duration_value': 1,
            'duration_unit': 'years',
        })
        self.assertEqual(period_years.total_days, 365)  # int(1 * 365.25)

    def test_period_summary_computation(self):
        """Test period summary computation."""
        # Test singular
        period = self.billing_period_model.create({
            'name': 'Test Month',
            'code': 'TEST_MONTH',
            'duration_value': 1,
            'duration_unit': 'months',
        })
        self.assertIn('1 Month', period.period_summary)
        
        # Test plural
        period = self.billing_period_model.create({
            'name': 'Test Months',
            'code': 'TEST_MONTHS',
            'duration_value': 3,
            'duration_unit': 'months',
        })
        self.assertIn('3 Months', period.period_summary)

    def test_default_period_management(self):
        """Test default period management."""
        # Create first period - should become default automatically
        period1 = self.billing_period_model.create({
            'name': 'First Period',
            'code': 'FIRST',
            'duration_value': 1,
            'duration_unit': 'months',
        })
        self.assertTrue(period1.is_default)
        
        # Create second period - should not be default
        period2 = self.billing_period_model.create({
            'name': 'Second Period',
            'code': 'SECOND',
            'duration_value': 3,
            'duration_unit': 'months',
        })
        self.assertFalse(period2.is_default)
        
        # Test single default constraint
        with self.assertRaises(ValidationError):
            period2.write({'is_default': True})
        
        # Test setting new default (should unset others)
        period2.action_set_as_default()
        period1.refresh()
        period2.refresh()
        self.assertFalse(period1.is_default)
        self.assertTrue(period2.is_default)

    def test_get_default_period(self):
        """Test getting default period."""
        # No periods exist
        default = self.billing_period_model.get_default_period()
        self.assertFalse(default)
        
        # Create period
        period = self.billing_period_model.create({
            'name': 'Test Default',
            'code': 'DEFAULT',
            'duration_value': 12,
            'duration_unit': 'months',
            'is_default': True,
        })
        
        default = self.billing_period_model.get_default_period()
        self.assertEqual(default, period)

    def test_calculate_next_date(self):
        """Test next date calculation."""
        start_date = date(2024, 1, 1)
        
        # Test days
        period_days = self.billing_period_model.create({
            'name': 'Test Days',
            'code': 'TEST_DAYS',
            'duration_value': 7,
            'duration_unit': 'days',
        })
        next_date = period_days.calculate_next_date(start_date)
        expected = start_date + timedelta(days=7)
        self.assertEqual(next_date, expected)
        
        # Test weeks
        period_weeks = self.billing_period_model.create({
            'name': 'Test Weeks',
            'code': 'TEST_WEEKS',
            'duration_value': 2,
            'duration_unit': 'weeks',
        })
        next_date = period_weeks.calculate_next_date(start_date)
        expected = start_date + timedelta(weeks=2)
        self.assertEqual(next_date, expected)
        
        # Test months
        period_months = self.billing_period_model.create({
            'name': 'Test Months',
            'code': 'TEST_MONTHS',
            'duration_value': 3,
            'duration_unit': 'months',
        })
        next_date = period_months.calculate_next_date(start_date)
        expected = start_date + relativedelta(months=3)
        self.assertEqual(next_date, expected)
        
        # Test years
        period_years = self.billing_period_model.create({
            'name': 'Test Years',
            'code': 'TEST_YEARS',
            'duration_value': 1,
            'duration_unit': 'years',
        })
        next_date = period_years.calculate_next_date(start_date)
        expected = start_date + relativedelta(years=1)
        self.assertEqual(next_date, expected)

    def test_calculate_period_end(self):
        """Test period end date calculation."""
        start_date = date(2024, 1, 1)
        
        period = self.billing_period_model.create({
            'name': 'Test Monthly',
            'code': 'TEST_MONTHLY',
            'duration_value': 1,
            'duration_unit': 'months',
        })
        
        end_date = period.calculate_period_end(start_date)
        expected_next = start_date + relativedelta(months=1)
        expected_end = expected_next - timedelta(days=1)
        self.assertEqual(end_date, expected_end)

    def test_get_period_range(self):
        """Test getting period date range."""
        start_date = date(2024, 1, 1)
        
        period = self.billing_period_model.create({
            'name': 'Test Quarterly',
            'code': 'TEST_QUARTERLY',
            'duration_value': 3,
            'duration_unit': 'months',
        })
        
        start, end = period.get_period_range(start_date)
        self.assertEqual(start, start_date)
        
        expected_end = start_date + relativedelta(months=3) - timedelta(days=1)
        self.assertEqual(end, expected_end)

    def test_get_periods_by_duration(self):
        """Test filtering periods by duration unit."""
        monthly = self.billing_period_model.create({
            'name': 'Monthly',
            'code': 'MONTHLY',
            'duration_value': 1,
            'duration_unit': 'months',
        })
        
        yearly = self.billing_period_model.create({
            'name': 'Yearly',
            'code': 'YEARLY',
            'duration_value': 1,
            'duration_unit': 'years',
        })
        
        # Test filtering by months
        monthly_periods = self.billing_period_model.get_periods_by_duration('months')
        self.assertIn(monthly, monthly_periods)
        self.assertNotIn(yearly, monthly_periods)
        
        # Test filtering by years
        yearly_periods = self.billing_period_model.get_periods_by_duration('years')
        self.assertIn(yearly, yearly_periods)
        self.assertNotIn(monthly, yearly_periods)

    def test_get_shortest_longest_period(self):
        """Test getting shortest and longest periods."""
        weekly = self.billing_period_model.create({
            'name': 'Weekly',
            'code': 'WEEKLY',
            'duration_value': 1,
            'duration_unit': 'weeks',
        })
        
        yearly = self.billing_period_model.create({
            'name': 'Yearly',
            'code': 'YEARLY',
            'duration_value': 1,
            'duration_unit': 'years',
        })
        
        shortest = self.billing_period_model.get_shortest_period()
        longest = self.billing_period_model.get_longest_period()
        
        self.assertEqual(shortest, weekly)
        self.assertEqual(longest, yearly)

    def test_get_period_description(self):
        """Test period description formatting."""
        period = self.billing_period_model.create({
            'name': 'Test Period',
            'code': 'TEST',
            'duration_value': 6,
            'duration_unit': 'months',
            'description': 'Semi-annual billing',
            'is_default': True,
        })
        
        description = period.get_period_description()
        self.assertIn('6 Months', description)
        self.assertIn('Semi-annual billing', description)
        self.assertIn('(Default)', description)

    def test_toggle_active(self):
        """Test toggling active status."""
        period = self.billing_period_model.create({
            'name': 'Test Toggle',
            'code': 'TOGGLE',
            'duration_value': 1,
            'duration_unit': 'months',
            'active': True,
        })
        
        # Toggle to inactive
        period.toggle_active()
        self.assertFalse(period.active)
        
        # Toggle back to active
        period.toggle_active()
        self.assertTrue(period.active)

    def test_toggle_active_default_period(self):
        """Test that default period cannot be deactivated."""
        period = self.billing_period_model.create({
            'name': 'Default Period',
            'code': 'DEFAULT',
            'duration_value': 12,
            'duration_unit': 'months',
            'is_default': True,
            'active': True,
        })
        
        # Should not be able to deactivate default period
        with self.assertRaises(ValidationError):
            period.toggle_active()

    def test_copy_method(self):
        """Test copy method with unique names and codes."""
        original = self.billing_period_model.create({
            'name': 'Original Period',
            'code': 'ORIGINAL',
            'duration_value': 3,
            'duration_unit': 'months',
            'is_default': True,
        })
        
        copy = original.copy()
        
        self.assertEqual(copy.name, 'Original Period (Copy)')
        self.assertEqual(copy.code, 'ORIGINAL_COPY')
        self.assertEqual(copy.duration_value, 3)
        self.assertEqual(copy.duration_unit, 'months')
        self.assertFalse(copy.is_default)  # Copy should not be default

    def test_name_get(self):
        """Test custom name display."""
        period = self.billing_period_model.create({
            'name': 'Test Period',
            'code': 'TEST',
            'duration_value': 1,
            'duration_unit': 'months',
            'is_default': True,
        })
        
        name_get_result = period.name_get()[0][1]
        self.assertIn('[TEST]', name_get_result)
        self.assertIn('Test Period', name_get_result)
        self.assertIn('(1 Month', name_get_result)
        self.assertIn('★', name_get_result)  # Default indicator

    def test_name_search(self):
        """Test custom name search functionality."""
        period = self.billing_period_model.create({
            'name': 'Annual Membership',
            'code': 'ANNUAL',
            'duration_value': 12,
            'duration_unit': 'months',
        })
        
        # Test search by name
        results = self.billing_period_model.name_search('Annual')
        period_ids = [r[0] for r in results]
        self.assertIn(period.id, period_ids)
        
        # Test search by code
        results = self.billing_period_model.name_search('ANNUAL')
        period_ids = [r[0] for r in results]
        self.assertIn(period.id, period_ids)
        
        # Test search by period summary
        results = self.billing_period_model.name_search('12 Months')
        period_ids = [r[0] for r in results]
        self.assertIn(period.id, period_ids)

    def test_prevent_no_default_periods(self):
        """Test that at least one period must remain default."""
        period1 = self.billing_period_model.create({
            'name': 'Period 1',
            'code': 'PERIOD1',
            'duration_value': 1,
            'duration_unit': 'months',
            'is_default': True,
        })
        
        period2 = self.billing_period_model.create({
            'name': 'Period 2',
            'code': 'PERIOD2',
            'duration_value': 3,
            'duration_unit': 'months',
            'is_default': False,
        })
        
        # Should not be able to unset the only default
        with self.assertRaises(ValidationError):
            period1.write({'is_default': False})

    def test_date_string_handling(self):
        """Test that string dates are properly handled."""
        period = self.billing_period_model.create({
            'name': 'Test String Date',
            'code': 'STRING_DATE',
            'duration_value': 1,
            'duration_unit': 'months',
        })
        
        # Test with string date
        next_date = period.calculate_next_date('2024-01-01')
        expected = date(2024, 2, 1)
        self.assertEqual(next_date, expected)

    def tearDown(self):
        """Clean up after tests."""
        super().tearDown()