# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestAMSSystemConfig(TransactionCase):
    """Test cases for AMS System Configuration module."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.config_model = self.env['ams.config.settings']
        self.param_model = self.env['ir.config_parameter']
        self.sequence_model = self.env['ir.sequence']
        
        # Create a test configuration record
        self.config = self.config_model.create({})

    def test_default_configuration_values(self):
        """Test that default configuration values are properly set."""
        # Test membership defaults
        self.assertTrue(self.config.auto_member_id)
        self.assertEqual(self.config.member_id_prefix, 'M')
        self.assertEqual(self.config.grace_period_days, 30)
        self.assertEqual(self.config.renewal_window_days, 90)
        self.assertFalse(self.config.allow_multiple_memberships)
        
        # Test portal defaults
        self.assertTrue(self.config.portal_enabled)
        self.assertFalse(self.config.portal_self_registration)
        self.assertFalse(self.config.communication_opt_out_default)
        self.assertTrue(self.config.emergency_communications_override)
        
        # Test financial defaults
        self.assertEqual(self.config.fiscal_year_start, 'january')
        self.assertFalse(self.config.chapter_revenue_sharing)
        self.assertEqual(self.config.default_chapter_percentage, 30.0)
        
        # Test feature defaults
        self.assertTrue(self.config.enterprise_subscriptions_enabled)
        self.assertFalse(self.config.continuing_education_required)
        self.assertTrue(self.config.fundraising_enabled)
        self.assertTrue(self.config.event_member_pricing)

    def test_grace_period_validation(self):
        """Test grace period validation constraints."""
        # Test valid grace period
        self.config.grace_period_days = 30
        # Should not raise exception
        
        # Test invalid negative grace period
        with self.assertRaises(ValidationError):
            self.config.grace_period_days = -5
            self.config._check_grace_period_days()
        
        # Test invalid excessive grace period
        with self.assertRaises(ValidationError):
            self.config.grace_period_days = 400
            self.config._check_grace_period_days()

    def test_renewal_window_validation(self):
        """Test renewal window validation constraints."""
        # Test valid renewal window
        self.config.renewal_window_days = 90
        # Should not raise exception
        
        # Test invalid negative renewal window
        with self.assertRaises(ValidationError):
            self.config.renewal_window_days = -10
            self.config._check_renewal_window_days()
        
        # Test invalid excessive renewal window
        with self.assertRaises(ValidationError):
            self.config.renewal_window_days = 500
            self.config._check_renewal_window_days()

    def test_chapter_percentage_validation(self):
        """Test chapter revenue percentage validation constraints."""
        # Test valid percentage
        self.config.default_chapter_percentage = 25.0
        # Should not raise exception
        
        # Test invalid negative percentage
        with self.assertRaises(ValidationError):
            self.config.default_chapter_percentage = -5.0
            self.config._check_chapter_percentage()
        
        # Test invalid excessive percentage
        with self.assertRaises(ValidationError):
            self.config.default_chapter_percentage = 150.0
            self.config._check_chapter_percentage()

    def test_member_id_prefix_validation(self):
        """Test member ID prefix validation constraints."""
        # Test valid prefix
        self.config.auto_member_id = True
        self.config.member_id_prefix = 'MEMBER'
        # Should not raise exception
        
        # Test invalid long prefix
        with self.assertRaises(ValidationError):
            self.config.member_id_prefix = 'VERYLONGPREFIX'
            self.config._check_member_id_prefix()
        
        # Test invalid non-alphanumeric prefix
        with self.assertRaises(ValidationError):
            self.config.member_id_prefix = 'M@#'
            self.config._check_member_id_prefix()

    def test_continuing_education_dependency_check(self):
        """Test continuing education module dependency validation."""
        # Mock the module search to simulate missing CE module
        def mock_search(domain, limit=None):
            return self.env['ir.module.module']  # Empty recordset
        
        original_search = self.env['ir.module.module'].search
        self.env['ir.module.module'].search = mock_search
        
        try:
            with self.assertRaises(ValidationError):
                self.config.continuing_education_required = True
                self.config._check_ce_requirements()
        finally:
            # Restore original search method
            self.env['ir.module.module'].search = original_search

    def test_onchange_auto_member_id(self):
        """Test onchange behavior for auto member ID toggle."""
        # Enable auto member ID
        self.config.auto_member_id = True
        self.config.member_id_prefix = 'TEST'
        
        # Disable auto member ID
        self.config.auto_member_id = False
        self.config._onchange_auto_member_id()
        
        # Check that dependent fields are cleared
        self.assertFalse(self.config.member_id_prefix)
        self.assertFalse(self.config.member_id_sequence)

    def test_onchange_chapter_revenue_sharing(self):
        """Test onchange behavior for chapter revenue sharing toggle."""
        # Enable chapter revenue sharing
        self.config.chapter_revenue_sharing = True
        self.config.default_chapter_percentage = 25.0
        
        # Disable chapter revenue sharing
        self.config.chapter_revenue_sharing = False
        self.config._onchange_chapter_revenue_sharing()
        
        # Check that percentage is reset
        self.assertEqual(self.config.default_chapter_percentage, 0.0)

    def test_onchange_portal_enabled(self):
        """Test onchange behavior for portal enablement."""
        # Enable portal and self-registration
        self.config.portal_enabled = True
        self.config.portal_self_registration = True
        
        # Disable portal
        self.config.portal_enabled = False
        self.config._onchange_portal_enabled()
        
        # Check that self-registration is disabled
        self.assertFalse(self.config.portal_self_registration)

    def test_get_global_setting(self):
        """Test utility method for getting global settings."""
        # Set a test parameter
        test_key = 'test_setting'
        test_value = 'test_value'
        self.param_model.sudo().set_param(f'ams_system_config.{test_key}', test_value)
        
        # Test getting the setting
        result = self.config_model.get_global_setting(test_key)
        self.assertEqual(result, test_value)
        
        # Test getting non-existent setting with default
        result = self.config_model.get_global_setting('non_existent', 'default_value')
        self.assertEqual(result, 'default_value')

    def test_set_global_setting(self):
        """Test utility method for setting global settings."""
        test_key = 'test_setting_write'
        test_value = 'test_value_write'
        
        # Set the setting
        self.config_model.set_global_setting(test_key, test_value)
        
        # Verify it was set correctly
        result = self.param_model.sudo().get_param(f'ams_system_config.{test_key}')
        self.assertEqual(result, test_value)

    def test_get_member_id_format(self):
        """Test member ID format configuration retrieval."""
        # Set test values
        self.param_model.sudo().set_param('ams_system_config.auto_member_id', True)
        self.param_model.sudo().set_param('ams_system_config.member_id_prefix', 'TEST')
        
        # Get format configuration
        format_config = self.config_model.get_member_id_format()
        
        # Verify results
        self.assertTrue(format_config['auto_generate'])
        self.assertEqual(format_config['prefix'], 'TEST')
        self.assertIn('sequence_id', format_config)

    def test_get_membership_policies(self):
        """Test membership policy configuration retrieval."""
        # Set test values
        self.param_model.sudo().set_param('ams_system_config.grace_period_days', '45')
        self.param_model.sudo().set_param('ams_system_config.renewal_window_days', '120')
        self.param_model.sudo().set_param('ams_system_config.allow_multiple_memberships', True)
        
        # Get policy configuration
        policies = self.config_model.get_membership_policies()
        
        # Verify results
        self.assertEqual(policies['grace_period_days'], 45)
        self.assertEqual(policies['renewal_window_days'], 120)
        self.assertTrue(policies['allow_multiple'])

    def test_get_portal_configuration(self):
        """Test portal configuration retrieval."""
        # Set test values
        self.param_model.sudo().set_param('ams_system_config.portal_enabled', True)
        self.param_model.sudo().set_param('ams_system_config.portal_self_registration', True)
        
        # Get portal configuration
        portal_config = self.config_model.get_portal_configuration()
        
        # Verify results
        self.assertTrue(portal_config['enabled'])
        self.assertTrue(portal_config['self_registration'])

    def test_get_feature_flags(self):
        """Test feature flags retrieval."""
        # Set test values
        self.param_model.sudo().set_param('ams_system_config.enterprise_subscriptions_enabled', False)
        self.param_model.sudo().set_param('ams_system_config.fundraising_enabled', True)
        
        # Get feature flags
        features = self.config_model.get_feature_flags()
        
        # Verify results
        self.assertFalse(features['enterprise_subscriptions'])
        self.assertTrue(features['fundraising'])
        self.assertIn('continuing_education', features)
        self.assertIn('event_member_pricing', features)
        self.assertIn('chapter_revenue_sharing', features)

    def test_validate_system_configuration(self):
        """Test system configuration validation."""
        # Test with missing currency (should generate error)
        self.param_model.sudo().set_param('ams_system_config.default_currency_id', '')
        errors = self.config_model.validate_system_configuration()
        self.assertTrue(any('currency' in error.lower() for error in errors))
        
        # Test with auto member ID but no prefix (should generate error)
        self.param_model.sudo().set_param('ams_system_config.auto_member_id', True)
        self.param_model.sudo().set_param('ams_system_config.member_id_prefix', '')
        errors = self.config_model.validate_system_configuration()
        self.assertTrue(any('prefix' in error.lower() for error in errors))

    def test_create_member_id_sequence(self):
        """Test member ID sequence creation."""
        # Set configuration
        self.config.member_id_prefix = 'TEST'
        
        # Create sequence
        sequence = self.config._create_member_id_sequence()
        
        # Verify sequence was created correctly
        self.assertTrue(sequence)
        self.assertEqual(sequence.code, 'ams.member.id')
        self.assertEqual(sequence.prefix, 'TEST')
        self.assertEqual(sequence.padding, 6)

    def test_set_values_creates_sequence(self):
        """Test that set_values creates sequence when needed."""
        # Configure for auto ID generation without existing sequence
        self.config.auto_member_id = True
        self.config.member_id_prefix = 'AUTO'
        self.config.member_id_sequence = False
        
        # Save configuration
        self.config.set_values()
        
        # Check that sequence was created and parameter set
        sequence_id = self.param_model.sudo().get_param('ams_system_config.member_id_sequence_id')
        self.assertTrue(sequence_id)
        
        # Verify sequence exists
        sequence = self.sequence_model.browse(int(sequence_id))
        self.assertTrue(sequence.exists())
        self.assertEqual(sequence.prefix, 'AUTO')

    def test_existing_sequence_update(self):
        """Test updating existing sequence when prefix changes."""
        # Create initial sequence
        sequence = self.sequence_model.create({
            'name': 'Test AMS Member ID',
            'code': 'ams.member.id',
            'prefix': 'OLD',
            'padding': 6,
        })
        
        # Set new prefix
        self.config.member_id_prefix = 'NEW'
        
        # Create sequence (should update existing)
        updated_sequence = self.config._create_member_id_sequence()
        
        # Verify same sequence was updated, not new one created
        self.assertEqual(updated_sequence.id, sequence.id)
        self.assertEqual(updated_sequence.prefix, 'NEW')

    def tearDown(self):
        """Clean up after tests."""
        # Clean up any test configuration parameters
        test_params = self.param_model.search([
            ('key', 'like', 'ams_system_config.test_%')
        ])
        test_params.unlink()
        
        super().tearDown()