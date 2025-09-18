# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class TestAMSSubscriptionProducts(TransactionCase):
    """Test cases for AMS Subscription Products module."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Get models
        self.ProductTemplate = self.env['product.template']
        self.SubscriptionProduct = self.env['ams.subscription.product']
        self.BillingPeriod = self.env['ams.billing.period']
        self.Partner = self.env['res.partner']
        
        # Create test billing periods
        self.monthly_period = self.BillingPeriod.create({
            'name': 'Monthly',
            'code': 'MONTHLY',
            'duration_value': 1,
            'duration_unit': 'months',
            'sequence': 10,
        })
        
        self.quarterly_period = self.BillingPeriod.create({
            'name': 'Quarterly',
            'code': 'QUARTERLY',
            'duration_value': 3,
            'duration_unit': 'months',
            'sequence': 20,
        })
        
        self.annual_period = self.BillingPeriod.create({
            'name': 'Annual',
            'code': 'ANNUAL',
            'duration_value': 12,
            'duration_unit': 'months',
            'sequence': 30,
            'is_default': True,
        })
        
        # Create test product templates
        self.membership_template = self.ProductTemplate.create({
            'name': 'Test Membership Template',
            'list_price': 150.00,
            'ams_product_behavior': 'membership',
            'is_subscription': True,
            'default_billing_period_id': self.annual_period.id,
            'subscription_scope': 'individual',
            'is_renewable': True,
            'auto_renewal_enabled': True,
        })
        
        self.publication_template = self.ProductTemplate.create({
            'name': 'Test Publication Template',
            'list_price': 120.00,
            'ams_product_behavior': 'publication',
            'is_subscription': True,
            'default_billing_period_id': self.quarterly_period.id,
            'subscription_scope': 'individual',
        })
        
        self.enterprise_template = self.ProductTemplate.create({
            'name': 'Test Enterprise Template',
            'list_price': 1500.00,
            'ams_product_behavior': 'service',
            'is_subscription': True,
            'default_billing_period_id': self.annual_period.id,
            'subscription_scope': 'enterprise',
            'supports_seats': True,
            'default_seat_count': 5,
            'requires_approval': True,
        })
        
        # Create test partners
        self.member_partner = self.Partner.create({
            'name': 'Test Active Member',
            'email': 'member@test.com',
            'is_member': True,
            'membership_status': 'active',
        })
        
        self.non_member_partner = self.Partner.create({
            'name': 'Test Non-Member',
            'email': 'nonmember@test.com',
            'is_member': False,
            'membership_status': 'prospect',
        })

    # ========================================================================
    # PRODUCT TEMPLATE SUBSCRIPTION EXTENSION TESTS
    # ========================================================================

    def test_subscription_template_creation(self):
        """Test product template subscription extension creation"""
        template = self.ProductTemplate.create({
            'name': 'Test Subscription Template',
            'list_price': 200.00,
            'is_subscription': True,
            'default_billing_period_id': self.monthly_period.id,
            'subscription_scope': 'individual',
        })
        
        self.assertTrue(template.is_subscription)
        self.assertEqual(template.default_billing_period_id, self.monthly_period)
        self.assertEqual(template.subscription_scope, 'individual')
        self.assertTrue(template.is_renewable)  # Default value

    def test_subscription_onchange_behaviors(self):
        """Test onchange behaviors for subscription configuration"""
        # Test subscription toggle onchange
        template = self.ProductTemplate.new({
            'name': 'Test Onchange',
            'list_price': 100.00,
        })
        
        template.is_subscription = True
        template._onchange_is_subscription()
        
        # Should set defaults
        self.assertTrue(template.is_renewable)
        self.assertEqual(template.renewal_window_days, 90)
        
        # Test scope onchange
        template.subscription_scope = 'enterprise'
        template._onchange_subscription_scope()
        
        # Should set enterprise defaults
        self.assertTrue(template.requires_approval)
        self.assertTrue(template.supports_seats)
        self.assertEqual(template.default_seat_count, 5)

    def test_subscription_validation_constraints(self):
        """Test subscription validation constraints"""
        template = self.membership_template
        
        # Test invalid renewal window
        with self.assertRaises(ValidationError):
            template.write({'renewal_window_days': -1})
        
        with self.assertRaises(ValidationError):
            template.write({'renewal_window_days': 400})
        
        # Test invalid seat count
        template.write({'supports_seats': True})
        with self.assertRaises(ValidationError):
            template.write({'default_seat_count': 0})
        
        with self.assertRaises(ValidationError):
            template.write({'default_seat_count': 15000})

    def test_subscription_details_method(self):
        """Test get_subscription_details method"""
        # Test non-subscription template
        non_sub_template = self.ProductTemplate.create({
            'name': 'Non-Subscription',
            'list_price': 50.00,
            'is_subscription': False,
        })
        
        details = non_sub_template.get_subscription_details()
        self.assertFalse(details['is_subscription'])
        
        # Test subscription template
        details = self.membership_template.get_subscription_details()
        self.assertTrue(details['is_subscription'])
        self.assertEqual(details['subscription_scope'], 'individual')
        self.assertEqual(details['billing_period_name'], 'Annual')
        self.assertTrue(details['is_renewable'])
        self.assertTrue(details['auto_renewal_enabled'])

    def test_billing_period_methods(self):
        """Test billing period related methods"""
        template = self.membership_template
        
        # Test billing period options
        options = template.get_billing_period_options()
        self.assertIn(self.monthly_period, options)
        self.assertIn(self.annual_period, options)
        
        # Test next billing date calculation
        start_date = date(2024, 1, 1)
        next_date = template.calculate_next_billing_date(start_date)
        expected = date(2025, 1, 1)  # Annual period
        self.assertEqual(next_date, expected)
        
        # Test renewal notice date
        end_date = date(2024, 12, 31)
        notice_date = template.calculate_renewal_notice_date(end_date)
        expected_notice = date(2024, 10, 2)  # 90 days before
        self.assertEqual(notice_date, expected_notice)

    def test_subscription_query_methods(self):
        """Test subscription query methods"""
        # Get all subscription products
        all_subscriptions = self.ProductTemplate.get_subscription_products()
        self.assertIn(self.membership_template, all_subscriptions)
        self.assertIn(self.publication_template, all_subscriptions)
        
        # Get auto-renewable products
        auto_renewable = self.ProductTemplate.get_auto_renewable_products()
        self.assertIn(self.membership_template, auto_renewable)
        self.assertNotIn(self.publication_template, auto_renewable)  # auto_renewal not enabled
        
        # Get enterprise subscriptions
        enterprise_subs = self.ProductTemplate.get_enterprise_subscription_products()
        self.assertIn(self.enterprise_template, enterprise_subs)
        self.assertNotIn(self.membership_template, enterprise_subs)

    # ========================================================================
    # SUBSCRIPTION PRODUCT MODEL TESTS
    # ========================================================================

    def test_subscription_product_creation(self):
        """Test basic subscription product creation"""
        subscription = self.SubscriptionProduct.create({
            'name': 'Test Individual Membership',
            'code': 'TEST_INDIV',
            'subscription_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'base_price': 150.00,
            'product_template_id': self.membership_template.id,
        })
        
        self.assertEqual(subscription.name, 'Test Individual Membership')
        self.assertEqual(subscription.code, 'TEST_INDIV')
        self.assertEqual(subscription.subscription_type, 'membership')
        self.assertEqual(subscription.base_price, 150.00)
        self.assertTrue(subscription.active)

    def test_subscription_product_code_generation(self):
        """Test automatic code generation from name"""
        subscription = self.SubscriptionProduct.new({
            'name': 'Professional Annual Membership',
            'subscription_type': 'membership',
        })
        
        subscription._onchange_name()
        self.assertEqual(subscription.code, 'PROFESSIONAL_ANNUAL_MEMBERSHIP')
        
        # Test with special characters
        subscription = self.SubscriptionProduct.new({
            'name': 'Premium Service - Monthly',
            'subscription_type': 'service',
        })
        
        subscription._onchange_name()
        self.assertEqual(subscription.code, 'PREMIUM_SERVICE_MONTHLY')

    def test_subscription_product_type_onchange(self):
        """Test subscription type onchange behavior"""
        subscription = self.SubscriptionProduct.new({
            'name': 'Test Subscription',
            'subscription_type': 'membership',
        })
        
        subscription._onchange_subscription_type()
        
        # Should set membership defaults
        self.assertEqual(subscription.subscription_category, 'core')
        self.assertEqual(subscription.default_duration, 12)
        self.assertEqual(subscription.duration_unit, 'months')
        self.assertFalse(subscription.member_only)
        
        # Test chapter type
        subscription.subscription_type = 'chapter'
        subscription._onchange_subscription_type()
        
        self.assertEqual(subscription.subscription_category, 'specialty')
        self.assertTrue(subscription.member_only)

    def test_subscription_product_computed_fields(self):
        """Test computed fields"""
        subscription = self.SubscriptionProduct.create({
            'name': 'Test Quarterly Membership',
            'code': 'TEST_QUARTERLY',
            'subscription_type': 'membership',
            'subscription_category': 'core',
            'default_duration': 3,
            'duration_unit': 'months',
            'base_price': 75.00,
            'product_template_id': self.publication_template.id,
        })
        
        # Test duration display
        self.assertEqual(subscription.duration_display, '3 Months')
        
        # Test subscription summary
        self.assertIn('Membership', subscription.subscription_summary)
        self.assertIn('3 Months', subscription.subscription_summary)
        self.assertIn('$75.00', subscription.subscription_summary)

    def test_subscription_product_validation(self):
        """Test subscription product validation"""
        # Test unique constraints
        self.SubscriptionProduct.create({
            'name': 'Unique Test',
            'code': 'UNIQUE_TEST',
            'subscription_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'base_price': 100.00,
            'product_template_id': self.membership_template.id,
        })
        
        # Duplicate code should fail
        with self.assertRaises(Exception):
            self.SubscriptionProduct.create({
                'name': 'Another Test',
                'code': 'UNIQUE_TEST',  # Duplicate code
                'subscription_type': 'service',
                'default_duration': 6,
                'duration_unit': 'months',
                'base_price': 200.00,
                'product_template_id': self.publication_template.id,
            })
        
        # Test duration validation
        with self.assertRaises(ValidationError):
            self.SubscriptionProduct.create({
                'name': 'Invalid Duration',
                'code': 'INVALID_DURATION',
                'subscription_type': 'membership',
                'default_duration': 0,  # Invalid
                'duration_unit': 'months',
                'base_price': 100.00,
                'product_template_id': self.membership_template.id,
            })

    def test_subscription_product_billing_period_integration(self):
        """Test billing period integration"""
        subscription = self.SubscriptionProduct.create({
            'name': 'Test Billing Integration',
            'code': 'TEST_BILLING',
            'subscription_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'base_price': 150.00,
            'product_template_id': self.membership_template.id,
            'default_billing_period_id': self.annual_period.id,
            'billing_period_ids': [(4, self.monthly_period.id), (4, self.annual_period.id)],
        })
        
        self.assertEqual(subscription.billing_options_count, 2)
        self.assertEqual(subscription.default_billing_period_id, self.annual_period)
        self.assertIn(self.annual_period, subscription.billing_period_ids)
        
        # Test constraint: default must be in supported periods
        with self.assertRaises(ValidationError):
            subscription.write({
                'billing_period_ids': [(6, 0, [self.monthly_period.id])],  # Remove annual
                # But annual is still the default - should fail
            })

    def test_subscription_product_business_methods(self):
        """Test business methods"""
        subscription = self.SubscriptionProduct.create({
            'name': 'Test Business Methods',
            'code': 'TEST_BUSINESS',
            'subscription_type': 'membership',
            'subscription_category': 'premium',
            'default_duration': 24,
            'duration_unit': 'months',
            'base_price': 300.00,
            'product_template_id': self.membership_template.id,
            'default_billing_period_id': self.annual_period.id,
            'member_only': True,
        })
        
        # Test configuration method
        config = subscription.get_subscription_configuration()
        self.assertEqual(config['name'], 'Test Business Methods')
        self.assertEqual(config['type'], 'membership')
        self.assertEqual(config['category'], 'premium')
        self.assertEqual(config['duration'], 24)
        self.assertTrue(config['member_only'])
        
        # Test pricing info
        pricing = subscription.get_pricing_info()
        self.assertEqual(pricing['base_price'], 300.00)
        self.assertEqual(pricing['billing_period'], 'Annual')
        
        # Test availability for partners
        self.assertTrue(subscription.is_available_for_partner(self.member_partner))
        self.assertFalse(subscription.is_available_for_partner(self.non_member_partner))  # Member only
        
        # Test duration in days
        duration_days = subscription.get_duration_in_days()
        expected_days = int(24 * 30.44)  # 24 months
        self.assertEqual(duration_days, expected_days)

    def test_subscription_product_query_methods(self):
        """Test query methods"""
        # Create test subscriptions
        membership_sub = self.SubscriptionProduct.create({
            'name': 'Test Membership Query',
            'code': 'TEST_MEMBERSHIP_QUERY',
            'subscription_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'base_price': 150.00,
            'product_template_id': self.membership_template.id,
        })
        
        publication_sub = self.SubscriptionProduct.create({
            'name': 'Test Publication Query',
            'code': 'TEST_PUBLICATION_QUERY',
            'subscription_type': 'publication',
            'default_duration': 12,
            'duration_unit': 'months',
            'base_price': 120.00,
            'product_template_id': self.publication_template.id,
        })
        
        member_only_sub = self.SubscriptionProduct.create({
            'name': 'Test Member Only Query',
            'code': 'TEST_MEMBER_ONLY_QUERY',
            'subscription_type': 'service',
            'default_duration': 6,
            'duration_unit': 'months',
            'base_price': 200.00,
            'product_template_id': self.enterprise_template.id,
            'member_only': True,
        })
        
        # Test query methods
        active_subs = self.SubscriptionProduct.get_active_subscriptions()
        self.assertIn(membership_sub, active_subs)
        self.assertIn(publication_sub, active_subs)
        
        membership_subs = self.SubscriptionProduct.get_subscriptions_by_type('membership')
        self.assertIn(membership_sub, membership_subs)
        self.assertNotIn(publication_sub, membership_subs)
        
        member_only_subs = self.SubscriptionProduct.get_member_only_subscriptions()
        self.assertIn(member_only_sub, member_only_subs)
        self.assertNotIn(membership_sub, member_only_subs)
        
        public_subs = self.SubscriptionProduct.get_public_subscriptions()
        self.assertIn(membership_sub, public_subs)
        self.assertNotIn(member_only_sub, public_subs)

    def test_subscription_product_duration_range_query(self):
        """Test duration range query method"""
        # Create subscriptions with different durations
        short_sub = self.SubscriptionProduct.create({
            'name': 'Short Subscription',
            'code': 'SHORT_SUB',
            'subscription_type': 'service',
            'default_duration': 1,
            'duration_unit': 'months',
            'base_price': 25.00,
            'product_template_id': self.publication_template.id,
        })
        
        medium_sub = self.SubscriptionProduct.create({
            'name': 'Medium Subscription',
            'code': 'MEDIUM_SUB',
            'subscription_type': 'membership',
            'default_duration': 6,
            'duration_unit': 'months',
            'base_price': 100.00,
            'product_template_id': self.membership_template.id,
        })
        
        long_sub = self.SubscriptionProduct.create({
            'name': 'Long Subscription',
            'code': 'LONG_SUB',
            'subscription_type': 'certification',
            'default_duration': 2,
            'duration_unit': 'years',
            'base_price': 500.00,
            'product_template_id': self.enterprise_template.id,
        })
        
        # Test duration range queries
        short_term = self.SubscriptionProduct.get_subscriptions_by_duration_range(max_days=90)
        self.assertIn(short_sub, short_term)
        self.assertNotIn(long_sub, short_term)
        
        long_term = self.SubscriptionProduct.get_subscriptions_by_duration_range(min_days=365)
        self.assertIn(long_sub, long_term)
        self.assertNotIn(short_sub, long_term)

    def test_subscription_product_name_methods(self):
        """Test name display and search methods"""
        subscription = self.SubscriptionProduct.create({
            'name': 'Professional Membership',
            'code': 'PROF_MEM',
            'subscription_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'base_price': 200.00,
            'product_template_id': self.membership_template.id,
        })
        
        # Test name_get
        name_display = subscription.name_get()[0][1]
        self.assertIn('[PROF_MEM]', name_display)
        self.assertIn('Professional Membership', name_display)
        self.assertIn('(Membership)', name_display)
        
        # Test name search
        found_ids = self.SubscriptionProduct._name_search('Professional')
        self.assertIn(subscription.id, found_ids)
        
        found_ids = self.SubscriptionProduct._name_search('PROF_MEM')
        self.assertIn(subscription.id, found_ids)

    def test_subscription_product_ui_actions(self):
        """Test UI action methods"""
        subscription = self.SubscriptionProduct.create({
            'name': 'Test UI Actions',
            'code': 'TEST_UI',
            'subscription_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'base_price': 150.00,
            'product_template_id': self.membership_template.id,
        })
        
        # Test view product template action
        action = subscription.action_view_product_template()
        self.assertEqual(action['res_model'], 'product.template')
        self.assertEqual(action['res_id'], self.membership_template.id)
        
        # Test availability test action
        action = subscription.action_test_availability()
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'display_notification')

    def test_integration_subscription_products_with_billing_periods(self):
        """Test integration between subscription products and billing periods"""
        # Create subscription with billing period integration
        subscription = self.SubscriptionProduct.create({
            'name': 'Integration Test Subscription',
            'code': 'INTEGRATION_TEST',
            'subscription_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'base_price': 150.00,
            'product_template_id': self.membership_template.id,
            'default_billing_period_id': self.annual_period.id,
            'billing_period_ids': [(4, self.monthly_period.id), (4, self.quarterly_period.id), (4, self.annual_period.id)],
        })
        
        # Test that billing period integration works
        config = subscription.get_subscription_configuration()
        self.assertEqual(config['default_billing_period_id'], self.annual_period.id)
        self.assertIn(self.monthly_period.id, config['billing_period_ids'])
        
        # Test pricing with specific billing period
        pricing = subscription.get_pricing_info(self.quarterly_period)
        self.assertEqual(pricing['billing_period'], 'Quarterly')
        self.assertEqual(pricing['billing_period_id'], self.quarterly_period.id)

    def test_template_subscription_sync(self):
        """Test synchronization between product template and subscription product"""
        # Test onchange when template is selected
        subscription = self.SubscriptionProduct.new({
            'name': 'Sync Test',
            'product_template_id': self.membership_template.id,
        })
        
        subscription._onchange_product_template_id()
        
        # Should inherit price from template
        self.assertEqual(subscription.base_price, 150.00)
        
        # Should inherit billing period if template has it configured
        if hasattr(self.membership_template, 'default_billing_period_id') and self.membership_template.default_billing_period_id:
            self.assertEqual(subscription.default_billing_period_id, self.membership_template.default_billing_period_id)

    def tearDown(self):
        """Clean up after tests"""
        super().tearDown()
        _logger.info("AMS Subscription Products tests completed successfully")