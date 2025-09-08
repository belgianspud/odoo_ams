"""Test cases for AMS Subscription Products functionality."""

from odoo.tests import common
from odoo.exceptions import ValidationError


class TestAMSSubscriptionProducts(common.TransactionCase):
    """Test AMS Subscription Products model."""

    def setUp(self):
        super().setUp()
        self.SubscriptionProduct = self.env['ams.subscription.product']
        self.Product = self.env['product.template']
        self.MemberType = self.env['ams.member.type']
        self.PricingTier = self.env['ams.subscription.pricing.tier']
        
        # Create test product
        self.test_product = self.Product.create({
            'name': 'Test Membership Product',
            'detailed_type': 'service',
            'sale_ok': True,
        })
        
        # Get default member types
        self.individual_type = self.env.ref('ams_member_data.member_type_individual')
        self.student_type = self.env.ref('ams_member_data.member_type_student')
        self.corporate_type = self.env.ref('ams_member_data.member_type_corporate')

    def test_create_individual_subscription(self):
        """Test creating an individual subscription product."""
        subscription = self.SubscriptionProduct.create({
            'name': 'Individual Professional Membership',
            'code': 'IND_PROF_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 299.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        self.assertTrue(subscription.id)
        self.assertEqual(subscription.name, 'Individual Professional Membership')
        self.assertEqual(subscription.subscription_scope, 'individual')
        self.assertEqual(subscription.product_type, 'membership')
        self.assertEqual(subscription.default_duration, 12)
        self.assertEqual(subscription.duration_unit, 'months')
        self.assertEqual(subscription.default_price, 299.00)
        self.assertTrue(subscription.is_renewable)  # Default value

    def test_create_enterprise_subscription(self):
        """Test creating an enterprise subscription product."""
        subscription = self.SubscriptionProduct.create({
            'name': 'Enterprise Corporate Membership',
            'code': 'ENT_CORP_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'enterprise',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 2499.00,
            'currency_id': self.env.company.currency_id.id,
            'default_seat_count': 10,
            'allow_seat_purchase': True,
        })
        
        self.assertEqual(subscription.subscription_scope, 'enterprise')
        self.assertEqual(subscription.default_seat_count, 10)
        self.assertTrue(subscription.allow_seat_purchase)

    def test_subscription_code_uniqueness(self):
        """Test that subscription codes must be unique."""
        # Create first subscription
        self.SubscriptionProduct.create({
            'name': 'First Subscription',
            'code': 'UNIQUE_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 100.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        # Try to create duplicate code
        with self.assertRaises(Exception):
            self.SubscriptionProduct.create({
                'name': 'Second Subscription',
                'code': 'UNIQUE_001',  # Duplicate code
                'product_id': self.test_product.id,
                'subscription_scope': 'individual',
                'product_type': 'membership',
                'default_duration': 6,
                'duration_unit': 'months',
                'default_price': 150.00,
                'currency_id': self.env.company.currency_id.id,
            })

    def test_duration_display_computation(self):
        """Test duration display field computation."""
        subscription = self.SubscriptionProduct.create({
            'name': 'Duration Test',
            'code': 'DUR_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 6,
            'duration_unit': 'months',
            'default_price': 150.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        self.assertEqual(subscription.duration_display, '6 months')
        
        # Test singular form
        subscription.write({
            'default_duration': 1,
            'duration_unit': 'year'
        })
        subscription._compute_duration_display()
        self.assertEqual(subscription.duration_display, '1 year')

    def test_enterprise_validation(self):
        """Test validation for enterprise subscriptions."""
        # Enterprise subscription without seat count should fail
        with self.assertRaises(ValidationError):
            self.SubscriptionProduct.create({
                'name': 'Invalid Enterprise',
                'code': 'INV_ENT_001',
                'product_id': self.test_product.id,
                'subscription_scope': 'enterprise',
                'product_type': 'membership',
                'default_duration': 12,
                'duration_unit': 'months',
                'default_price': 1000.00,
                'currency_id': self.env.company.currency_id.id,
                'default_seat_count': 0,  # Invalid for enterprise
            })

    def test_seat_product_validation(self):
        """Test seat product validation."""
        # Create main enterprise subscription
        main_subscription = self.SubscriptionProduct.create({
            'name': 'Main Enterprise',
            'code': 'MAIN_ENT_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'enterprise',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 2000.00,
            'currency_id': self.env.company.currency_id.id,
            'default_seat_count': 5,
        })
        
        # Create seat product
        seat_product = self.Product.create({
            'name': 'Additional Seat Product',
            'detailed_type': 'service',
        })
        
        seat_subscription = self.SubscriptionProduct.create({
            'name': 'Additional Seat',
            'code': 'ADD_SEAT_001',
            'product_id': seat_product.id,
            'subscription_scope': 'individual',  # Seat products should be individual
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 200.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        # Link seat product - should work
        main_subscription.seat_product_id = seat_subscription.id
        main_subscription._validate_seat_product()
        
        # Test self-reference (should fail)
        with self.assertRaises(ValidationError):
            main_subscription.seat_product_id = main_subscription.id
            main_subscription._validate_seat_product()

    def test_renewal_window_validation(self):
        """Test renewal window validation."""
        subscription = self.SubscriptionProduct.create({
            'name': 'Renewal Test',
            'code': 'REN_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 200.00,
            'currency_id': self.env.company.currency_id.id,
            'is_renewable': True,
            'renewal_window_days': 90,
        })
        
        # Valid renewal window
        subscription._validate_renewal_window()
        
        # Invalid renewal window (negative)
        with self.assertRaises(ValidationError):
            subscription.renewal_window_days = -30
            subscription._validate_renewal_window()
        
        # Invalid renewal window (too long)
        with self.assertRaises(ValidationError):
            subscription.renewal_window_days = 400
            subscription._validate_renewal_window()

    def test_member_pricing_functionality(self):
        """Test member pricing tier functionality."""
        subscription = self.SubscriptionProduct.create({
            'name': 'Pricing Test Subscription',
            'code': 'PRICE_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 300.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        # Create pricing tiers
        student_tier = self.PricingTier.create({
            'subscription_product_id': subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,  # 50% discount
            'currency_id': self.env.company.currency_id.id,
        })
        
        individual_tier = self.PricingTier.create({
            'subscription_product_id': subscription.id,
            'member_type_id': self.individual_type.id,
            'price': 270.00,  # 10% discount
            'currency_id': self.env.company.currency_id.id,
        })
        
        # Test member pricing calculation
        student_pricing = subscription.get_member_pricing(member_type_id=self.student_type.id)
        self.assertEqual(student_pricing['price'], 150.00)
        self.assertEqual(student_pricing['price_type'], 'member_tier')
        self.assertEqual(student_pricing['discount_percentage'], 50.0)
        
        individual_pricing = subscription.get_member_pricing(member_type_id=self.individual_type.id)
        self.assertEqual(individual_pricing['price'], 270.00)
        self.assertEqual(individual_pricing['discount_percentage'], 10.0)
        
        # Test pricing for member type without special pricing
        corporate_pricing = subscription.get_member_pricing(member_type_id=self.corporate_type.id)
        self.assertEqual(corporate_pricing['price'], 300.00)  # Default price
        self.assertEqual(corporate_pricing['price_type'], 'default')

    def test_computed_pricing_fields(self):
        """Test computed pricing-related fields."""
        subscription = self.SubscriptionProduct.create({
            'name': 'Computed Test Subscription',
            'code': 'COMP_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 400.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        # Initially no pricing tiers
        subscription._compute_has_member_pricing()
        subscription._compute_price_range()
        
        self.assertFalse(subscription.has_member_pricing)
        self.assertEqual(subscription.min_member_price, 400.00)
        self.assertEqual(subscription.max_member_price, 400.00)
        
        # Add pricing tiers
        self.PricingTier.create([
            {
                'subscription_product_id': subscription.id,
                'member_type_id': self.student_type.id,
                'price': 200.00,
                'currency_id': self.env.company.currency_id.id,
            },
            {
                'subscription_product_id': subscription.id,
                'member_type_id': self.corporate_type.id,
                'price': 600.00,
                'currency_id': self.env.company.currency_id.id,
            }
        ])
        
        # Recompute fields
        subscription._compute_has_member_pricing()
        subscription._compute_price_range()
        
        self.assertTrue(subscription.has_member_pricing)
        self.assertEqual(subscription.min_member_price, 200.00)
        self.assertEqual(subscription.max_member_price, 600.00)

    def test_member_eligibility_check(self):
        """Test member eligibility checking."""
        subscription = self.SubscriptionProduct.create({
            'name': 'Eligibility Test',
            'code': 'ELIG_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 250.00,
            'currency_id': self.env.company.currency_id.id,
            'member_only': True,
            'requires_approval': False,
        })
        
        # Create test member
        member = self.env['res.partner'].create({
            'name': 'Test Member',
            'is_member': True,
            'member_type_id': self.individual_type.id,
        })
        
        # Create non-member
        non_member = self.env['res.partner'].create({
            'name': 'Non Member',
            'is_member': False,
        })
        
        # Test member eligibility
        member_eligible, member_msg = subscription.check_member_eligibility(member)
        self.assertTrue(member_eligible)
        
        # Test non-member eligibility (should fail for member-only subscription)
        non_member_eligible, non_member_msg = subscription.check_member_eligibility(non_member)
        self.assertFalse(non_member_eligible)
        self.assertIn("members only", non_member_msg.lower())

    def test_billing_configuration(self):
        """Test billing configuration method."""
        subscription = self.SubscriptionProduct.create({
            'name': 'Billing Config Test',
            'code': 'BILL_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'enterprise',
            'product_type': 'membership',
            'default_duration': 24,
            'duration_unit': 'months',
            'default_price': 3000.00,
            'currency_id': self.env.company.currency_id.id,
            'is_renewable': True,
            'renewal_window_days': 120,
            'auto_renewal_enabled': True,
            'requires_approval': True,
            'default_seat_count': 15,
            'allow_seat_purchase': True,
        })
        
        config = subscription.get_billing_configuration()
        
        self.assertEqual(config['duration'], 24)
        self.assertEqual(config['duration_unit'], 'months')
        self.assertTrue(config['is_renewable'])
        self.assertEqual(config['renewal_window_days'], 120)
        self.assertTrue(config['auto_renewal_enabled'])
        self.assertTrue(config['requires_approval'])
        
        enterprise_config = config['enterprise_seats']
        self.assertTrue(enterprise_config['is_enterprise'])
        self.assertEqual(enterprise_config['default_seats'], 15)
        self.assertTrue(enterprise_config['allow_additional'])

    def test_subscription_summary(self):
        """Test subscription summary method."""
        subscription = self.SubscriptionProduct.create({
            'name': 'Summary Test Subscription',
            'code': 'SUM_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'chapter',
            'default_duration': 6,
            'duration_unit': 'months',
            'default_price': 175.00,
            'currency_id': self.env.company.currency_id.id,
            'is_renewable': True,
            'auto_renewal_enabled': False,
            'requires_approval': False,
            'member_only': True,
        })
        
        summary = subscription.get_subscription_summary()
        
        self.assertEqual(summary['name'], 'Summary Test Subscription')
        self.assertEqual(summary['code'], 'SUM_001')
        self.assertEqual(summary['type'], 'chapter')
        self.assertEqual(summary['scope'], 'individual')
        self.assertEqual(summary['duration'], '6 months')
        self.assertEqual(summary['price']['default'], 175.00)
        self.assertTrue(summary['features']['renewable'])
        self.assertFalse(summary['features']['auto_renewal'])
        self.assertTrue(summary['features']['member_only'])

    def test_create_pricing_tier_method(self):
        """Test create_pricing_tier helper method."""
        subscription = self.SubscriptionProduct.create({
            'name': 'Tier Creation Test',
            'code': 'TIER_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 500.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        # Create pricing tier using helper method
        tier = subscription.create_pricing_tier(
            member_type_id=self.student_type.id,
            price=250.00,
            requires_verification=True,
            verification_criteria="Student ID required"
        )
        
        self.assertEqual(tier.subscription_product_id, subscription)
        self.assertEqual(tier.member_type_id, self.student_type)
        self.assertEqual(tier.price, 250.00)
        self.assertTrue(tier.requires_verification)
        self.assertEqual(tier.verification_criteria, "Student ID required")

    def test_action_methods(self):
        """Test action methods."""
        subscription = self.SubscriptionProduct.create({
            'name': 'Action Test Subscription',
            'code': 'ACT_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 300.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        # Test manage pricing tiers action
        action = subscription.action_manage_pricing_tiers()
        self.assertEqual(action['res_model'], 'ams.subscription.pricing.tier')
        self.assertIn(('subscription_product_id', '=', subscription.id), action['domain'])
        
        # Test view product action
        action = subscription.action_view_product()
        self.assertEqual(action['res_model'], 'product.template')
        self.assertEqual(action['res_id'], subscription.product_id.id)

    def test_name_get_display(self):
        """Test custom name_get method."""
        subscription = self.SubscriptionProduct.create({
            'name': 'Display Test Subscription',
            'code': 'DISP_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'enterprise',
            'product_type': 'publication',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 400.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        name_get_result = subscription.name_get()
        display_name = name_get_result[0][1]
        
        self.assertIn('[Publication - Enterprise]', display_name)
        self.assertIn('Display Test Subscription', display_name)

    def test_code_generation_on_create(self):
        """Test automatic code generation during creation."""
        # Test with product that has default_code
        product_with_code = self.Product.create({
            'name': 'Product With Code',
            'default_code': 'PWC_001',
            'detailed_type': 'service',
        })
        
        subscription = self.SubscriptionProduct.create({
            'name': 'Auto Code Test',
            'product_id': product_with_code.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 200.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        self.assertEqual(subscription.code, 'PWC_001')
        
        # Test without code (should generate sequential)
        subscription2 = self.SubscriptionProduct.create({
            'name': 'No Code Test',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 200.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        self.assertTrue(subscription2.code.startswith('SUB_'))

    def test_utility_methods(self):
        """Test utility class methods."""
        # Create different types of subscriptions
        membership_sub = self.SubscriptionProduct.create({
            'name': 'Membership Subscription',
            'code': 'MEM_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 300.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        enterprise_product = self.Product.create({
            'name': 'Enterprise Product',
            'detailed_type': 'service',
        })
        
        enterprise_sub = self.SubscriptionProduct.create({
            'name': 'Enterprise Subscription',
            'code': 'ENT_001',
            'product_id': enterprise_product.id,
            'subscription_scope': 'enterprise',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 2500.00,
            'currency_id': self.env.company.currency_id.id,
            'default_seat_count': 10,
        })
        
        # Test get_membership_subscriptions
        membership_subs = self.SubscriptionProduct.get_membership_subscriptions()
        self.assertIn(membership_sub, membership_subs)
        self.assertIn(enterprise_sub, membership_subs)
        
        # Test get_enterprise_subscriptions
        enterprise_subs = self.SubscriptionProduct.get_enterprise_subscriptions()
        self.assertIn(enterprise_sub, enterprise_subs)
        self.assertNotIn(membership_sub, enterprise_subs)