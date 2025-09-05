# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestAMSConfig(TransactionCase):

    def setUp(self):
        super().setUp()
        self.config_model = self.env['ams.config.settings']

    def test_default_values(self):
        """Test that default configuration values are set correctly"""
        config = self.config_model.create({})
        
        # Test default values
        self.assertTrue(config.auto_member_id)
        self.assertEqual(config.member_id_prefix, 'M')
        self.assertEqual(config.member_id_padding, 6)
        self.assertEqual(config.grace_period_days, 30)
        self.assertEqual(config.renewal_window_days, 90)
        self.assertTrue(config.portal_enabled)
        self.assertEqual(config.fiscal_year_start, 'january')

    def test_member_id_padding_validation(self):
        """Test member ID padding validation"""
        config = self.config_model.create({})
        
        # Test invalid padding values
        with self.assertRaises(ValidationError):
            config.member_id_padding = 2  # Too small
        
        with self.assertRaises(ValidationError):
            config.member_id_padding = 15  # Too large
        
        # Test valid padding values
        config.member_id_padding = 5  # Should work
        self.assertEqual(config.member_id_padding, 5)

    def test_grace_period_validation(self):
        """Test grace period validation"""
        config = self.config_model.create({})
        
        # Test invalid grace periods
        with self.assertRaises(ValidationError):
            config.grace_period_days = -1  # Negative
        
        with self.assertRaises(ValidationError):
            config.grace_period_days = 400  # Too large
        
        # Test valid grace period
        config.grace_period_days = 45  # Should work
        self.assertEqual(config.grace_period_days, 45)

    def test_renewal_window_validation(self):
        """Test renewal window validation"""
        config = self.config_model.create({})
        
        # Test invalid renewal windows
        with self.assertRaises(ValidationError):
            config.renewal_window_days = 5  # Too small
        
        with self.assertRaises(ValidationError):
            config.renewal_window_days = 400  # Too large
        
        # Test valid renewal window
        config.renewal_window_days = 120  # Should work
        self.assertEqual(config.renewal_window_days, 120)

    def test_chapter_percentage_validation(self):
        """Test chapter percentage validation"""
        config = self.config_model.create({})
        
        # Test invalid percentages
        with self.assertRaises(ValidationError):
            config.default_chapter_percentage = -5  # Negative
        
        with self.assertRaises(ValidationError):
            config.default_chapter_percentage = 105  # Over 100%
        
        # Test valid percentage
        config.default_chapter_percentage = 25.5  # Should work
        self.assertEqual(config.default_chapter_percentage, 25.5)

    def test_data_retention_validation(self):
        """Test data retention years validation"""
        config = self.config_model.create({})
        
        # Test invalid retention periods
        with self.assertRaises(ValidationError):
            config.data_retention_years = 0  # Too small
        
        with self.assertRaises(ValidationError):
            config.data_retention_years = 75  # Too large
        
        # Test valid retention period
        config.data_retention_years = 10  # Should work
        self.assertEqual(config.data_retention_years, 10)

    def test_config_parameter_integration(self):
        """Test integration with ir.config_parameter"""
        config = self.config_model.create({
            'auto_member_id': False,
            'member_id_prefix': 'MEM',
            'grace_period_days': 45,
        })
        
        # Execute to save parameters
        config.execute()
        
        # Check that parameters were saved
        auto_member_id = self.env['ir.config_parameter'].sudo().get_param('ams.auto_member_id')
        member_id_prefix = self.env['ir.config_parameter'].sudo().get_param('ams.member_id_prefix')
        grace_period = self.env['ir.config_parameter'].sudo().get_param('ams.grace_period_days')
        
        self.assertEqual(auto_member_id, 'False')
        self.assertEqual(member_id_prefix, 'MEM')
        self.assertEqual(grace_period, '45')

    def test_get_values_with_defaults(self):
        """Test that get_values returns proper defaults"""
        values = self.config_model.get_values()
        
        # Check that we get reasonable defaults
        self.assertIn('auto_member_id', values)
        self.assertIn('member_id_prefix', values)
        self.assertIn('grace_period_days', values)

    def test_fiscal_year_dates_calculation(self):
        """Test fiscal year date calculation"""
        config = self.config_model.create({'fiscal_year_start': 'july'})
        config.execute()
        
        # Test fiscal year calculation for a date in August (should be current FY)
        test_date = self.env['ir.fields'].Date.from_string('2023-08-15')
        start_date, end_date = config.get_fiscal_year_dates(test_date)
        
        self.assertEqual(start_date.month, 7)  # July
        self.assertEqual(start_date.day, 1)
        self.assertEqual(end_date.month, 6)  # June (next year)
        self.assertEqual(end_date.day, 30)

    def test_member_sequence_update(self):
        """Test that member sequence is updated when settings change"""
        # Get the sequence
        sequence = self.env.ref('ams_member_data.seq_member_id')
        original_prefix = sequence.prefix
        original_padding = sequence.padding
        
        # Update config
        config = self.config_model.create({
            'member_id_prefix': 'TEST',
            'member_id_padding': 8,
            'member_id_sequence_id': sequence.id,
        })
        config.set_values()
        
        # Check that sequence was updated
        sequence.refresh()
        self.assertEqual(sequence.prefix, 'TEST')
        self.assertEqual(sequence.padding, 8)
        
        # Reset for cleanup
        sequence.write({
            'prefix': original_prefix,
            'padding': original_padding,
        })

    def test_action_reset_member_sequence(self):
        """Test reset member sequence action"""
        sequence = self.env.ref('ams_member_data.seq_member_id')
        
        # Set sequence to a higher number
        sequence.number_next = 100
        
        config = self.config_model.create({
            'member_id_sequence_id': sequence.id,
        })
        
        # Reset sequence
        result = config.action_reset_member_sequence()
        
        # Check that sequence was reset
        sequence.refresh()
        self.assertEqual(sequence.number_next, 1)
        
        # Check return value
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')

    def test_action_test_member_id_generation(self):
        """Test member ID generation test action"""
        sequence = self.env.ref('ams_member_data.seq_member_id')
        
        config = self.config_model.create({
            'member_id_sequence_id': sequence.id,
        })
        
        # Test generation
        result = config.action_test_member_id_generation()
        
        # Check return value
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertIn('Test Member ID generated:', result['params']['message'])

    def test_feature_toggles(self):
        """Test feature toggle settings"""
        config = self.config_model.create({
            'enterprise_subscriptions_enabled': False,
            'fundraising_enabled': False,
            'event_member_pricing': False,
        })
        config.execute()
        
        # Check that parameters were saved
        enterprise_enabled = self.env['ir.config_parameter'].sudo().get_param('ams.enterprise_subscriptions_enabled')
        fundraising_enabled = self.env['ir.config_parameter'].sudo().get_param('ams.fundraising_enabled')
        event_pricing = self.env['ir.config_parameter'].sudo().get_param('ams.event_member_pricing')
        
        self.assertEqual(enterprise_enabled, 'False')
        self.assertEqual(fundraising_enabled, 'False')
        self.assertEqual(event_pricing, 'False')

    def test_currency_default_setting(self):
        """Test that default currency is set from company if not specified"""
        company_currency = self.env.company.currency_id
        
        values = self.config_model.get_values()
        
        if company_currency:
            self.assertEqual(values.get('default_currency_id'), company_currency.id)