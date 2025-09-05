"""Test cases for AMS Subscription Pricing Tiers functionality."""

from odoo.tests import common
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class TestAMSSubscriptionPricingTiers(common.TransactionCase):
    """Test AMS Subscription Pricing Tiers model."""

    def setUp(self):
        super().setUp()
        self.SubscriptionProduct = self.env['ams.subscription.product']
        self.PricingTier = self.env['ams.subscription.pricing.tier']
        self.Product = self.env['product.template']
        self.MemberType = self.env['ams.member.type']
        
        # Create test product
        self.test_product = self.Product.create({
            'name': 'Test Pricing Product',
            'detailed_type': 'service',
            'sale_ok': True,
        })
        
        # Create test subscription
        self.test_subscription = self.SubscriptionProduct.create({
            'name': 'Test Subscription for Pricing',
            'code': 'TEST_PRICE_001',
            'product_id': self.test_product.id,
            'subscription_scope': 'individual',
            'product_type': 'membership',
            'default_duration': 12,
            'duration_unit': 'months',
            'default_price': 300.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        # Get default member types
        self.individual_type = self.env.ref('ams_member_data.member_type_individual')
        self.student_type = self.env.ref('ams_member_data.member_type_student')
        self.retired_type = self.env.ref('ams_member_data.member_type_retired')
        self.corporate_type = self.env.ref('ams_member_data.member_type_corporate')

    def test_create_basic_pricing_tier(self):
        """Test creating a basic pricing tier."""
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        self.assertTrue(tier.id)
        self.assertEqual(tier.subscription_product_id, self.test_subscription)
        self.assertEqual(tier.member_type_id, self.student_type)
        self.assertEqual(tier.price, 150.00)
        self.assertEqual(tier.currency_id, self.env.company.currency_id)

    def test_pricing_tier_display_name(self):
        """Test computed display name for pricing tiers."""
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        tier._compute_display_name()
        expected_name = f"{self.test_subscription.name} - {self.student_type.name} ({self.env.company.currency_id.symbol}150.0)"
        self.assertEqual(tier.display_name, expected_name)

    def test_discount_calculations(self):
        """Test discount percentage and amount calculations."""
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,  # 50% discount from 300.00
            'currency_id': self.env.company.currency_id.id,
        })
        
        tier._compute_discount_percentage()
        
        self.assertEqual(tier.discount_amount, 150.00)  # 300 - 150
        self.assertEqual(tier.discount_percentage, 50.0)  # 50% discount

    def test_premium_pricing(self):
        """Test premium pricing (higher than default)."""
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.corporate_type.id,
            'price': 450.00,  # 50% markup from 300.00
            'currency_id': self.env.company.currency_id.id,
        })
        
        tier._compute_discount_percentage()
        
        self.assertEqual(tier.discount_amount, -150.00)  # 300 - 450 (negative = markup)
        self.assertEqual(tier.discount_percentage, 0.0)  # No discount shown for markup

    def test_validity_period_functionality(self):
        """Test validity period for pricing tiers."""
        today = date.today()
        future_date = today + timedelta(days=30)
        past_date = today - timedelta(days=30)
        
        # Create tier with validity period
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            'currency_id': self.env.company.currency_id.id,
            'valid_from': today,
            'valid_to': future_date,
        })
        
        # Test current availability
        tier._compute_is_currently_available()
        self.assertTrue(tier.is_currently_available)
        
        # Test future pricing (not yet active)
        future_tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.retired_type.id,
            'price': 200.00,
            'currency_id': self.env.company.currency_id.id,
            'valid_from': future_date,
        })
        
        future_tier._compute_is_currently_available()
        self.assertFalse(future_tier.is_currently_available)
        
        # Test expired pricing
        expired_tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.individual_type.id,
            'price': 250.00,
            'currency_id': self.env.company.currency_id.id,
            'valid_to': past_date,
        })
        
        expired_tier._compute_is_currently_available()
        self.assertFalse(expired_tier.is_currently_available)

    def test_verification_requirements(self):
        """Test verification requirements for pricing tiers."""
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 100.00,
            'currency_id': self.env.company.currency_id.id,
            'requires_verification': True,
            'verification_criteria': 'Valid student ID and enrollment verification required.',
        })
        
        self.assertTrue(tier.requires_verification)
        self.assertEqual(tier.verification_criteria, 'Valid student ID and enrollment verification required.')

    def test_validation_constraints(self):
        """Test various validation constraints."""
        # Test overlapping validity periods (should fail)
        today = date.today()
        future_date = today + timedelta(days=30)
        
        # Create first tier
        tier1 = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            'currency_id': self.env.company.currency_id.id,
            'valid_from': today,
            'valid_to': future_date,
        })
        
        # Try to create overlapping tier (should fail validation)
        with self.assertRaises(ValidationError):
            self.PricingTier.create({
                'subscription_product_id': self.test_subscription.id,
                'member_type_id': self.student_type.id,  # Same member type
                'price': 160.00,
                'currency_id': self.env.company.currency_id.id,
                'valid_from': today + timedelta(days=15),  # Overlapping period
                'valid_to': future_date + timedelta(days=15),
            })

    def test_price_reasonableness_validation(self):
        """Test price reasonableness validation."""
        # Extremely high price should trigger validation warning
        with self.assertRaises(ValidationError):
            self.PricingTier.create({
                'subscription_product_id': self.test_subscription.id,
                'member_type_id': self.student_type.id,
                'price': 1000.00,  # More than 200% of default (300.00)
                'currency_id': self.env.company.currency_id.id,
            })

    def test_verification_criteria_validation(self):
        """Test validation of verification criteria."""
        # Should fail when verification required but no criteria provided
        with self.assertRaises(ValidationError):
            self.PricingTier.create({
                'subscription_product_id': self.test_subscription.id,
                'member_type_id': self.student_type.id,
                'price': 150.00,
                'currency_id': self.env.company.currency_id.id,
                'requires_verification': True,
                # Missing verification_criteria
            })

    def test_date_applicability_checking(self):
        """Test is_applicable_for_date method."""
        today = date.today()
        future_date = today + timedelta(days=30)
        past_date = today - timedelta(days=30)
        
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            'currency_id': self.env.company.currency_id.id,
            'valid_from': today,
            'valid_to': future_date,
        })
        
        # Test current date (should be applicable)
        self.assertTrue(tier.is_applicable_for_date(today))
        
        # Test future date within range
        self.assertTrue(tier.is_applicable_for_date(today + timedelta(days=15)))
        
        # Test past date (should not be applicable)
        self.assertFalse(tier.is_applicable_for_date(past_date))
        
        # Test future date beyond range
        self.assertFalse(tier.is_applicable_for_date(future_date + timedelta(days=10)))

    def test_pricing_details_method(self):
        """Test get_pricing_details method."""
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            'currency_id': self.env.company.currency_id.id,
            'requires_verification': True,
            'verification_criteria': 'Student ID required',
            'valid_from': date.today(),
        })
        
        details = tier.get_pricing_details()
        
        self.assertEqual(details['tier_id'], tier.id)
        self.assertEqual(details['member_type']['name'], self.student_type.name)
        self.assertEqual(details['pricing']['price'], 150.00)
        self.assertEqual(details['pricing']['discount_percentage'], 50.0)
        self.assertTrue(details['verification']['requires_verification'])
        self.assertEqual(details['verification']['criteria'], 'Student ID required')

    def test_member_eligibility_checking(self):
        """Test check_member_eligibility method."""
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            'currency_id': self.env.company.currency_id.id,
            'requires_verification': True,
            'verification_criteria': 'Student status verification required',
        })
        
        # Create test member with correct type
        student_member = self.env['res.partner'].create({
            'name': 'Test Student',
            'member_type_id': self.student_type.id,
        })
        
        # Create member with wrong type
        individual_member = self.env['res.partner'].create({
            'name': 'Test Individual',
            'member_type_id': self.individual_type.id,
        })
        
        # Test eligible member
        eligible, reason = tier.check_member_eligibility(student_member)
        self.assertTrue(eligible)
        self.assertIn('verification', reason.lower())
        
        # Test ineligible member (wrong type)
        eligible, reason = tier.check_member_eligibility(individual_member)
        self.assertFalse(eligible)
        self.assertIn('member type', reason.lower())

    def test_get_applicable_pricing_class_method(self):
        """Test get_applicable_pricing class method."""
        today = date.today()
        future_date = today + timedelta(days=30)
        
        # Create multiple tiers for same subscription/member type
        old_tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 120.00,
            'currency_id': self.env.company.currency_id.id,
            'valid_from': today - timedelta(days=60),
            'valid_to': today - timedelta(days=30),
        })
        
        current_tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            'currency_id': self.env.company.currency_id.id,
            'valid_from': today,
            'valid_to': future_date,
        })
        
        # Get applicable pricing for today
        applicable = self.PricingTier.get_applicable_pricing(
            self.test_subscription.id,
            self.student_type.id,
            today
        )
        
        self.assertEqual(applicable, current_tier)
        
        # Get applicable pricing for past date
        past_applicable = self.PricingTier.get_applicable_pricing(
            self.test_subscription.id,
            self.student_type.id,
            today - timedelta(days=45)
        )
        
        self.assertEqual(past_applicable, old_tier)

    def test_currency_inheritance(self):
        """Test currency inheritance from subscription."""
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            # currency_id should be inherited from subscription
        })
        
        self.assertEqual(tier.currency_id, self.test_subscription.currency_id)

    def test_action_methods(self):
        """Test action methods for pricing tiers."""
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        # Test view subscription action
        action = tier.action_view_subscription()
        self.assertEqual(action['res_model'], 'ams.subscription.product')
        self.assertEqual(action['res_id'], self.test_subscription.id)
        
        # Test duplicate tier action
        action = tier.action_duplicate_tier()
        self.assertEqual(action['res_model'], 'ams.subscription.pricing.tier')
        self.assertEqual(action['view_mode'], 'form')

    def test_utility_class_methods(self):
        """Test utility class methods."""
        # Create tiers of different types
        student_tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        retired_tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.retired_type.id,
            'price': 200.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        # Test get_member_type_pricing_summary
        summary = self.PricingTier.get_member_type_pricing_summary(self.student_type.id)
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]['pricing']['price'], 150.00)
        
        # Test get_subscription_pricing_matrix
        matrix = self.PricingTier.get_subscription_pricing_matrix(self.test_subscription.id)
        self.assertIn(self.student_type.name, matrix)
        self.assertIn(self.retired_type.name, matrix)

    def test_discount_display_method(self):
        """Test get_discount_display method."""
        # Test discount tier
        discount_tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,  # 50% discount
            'currency_id': self.env.company.currency_id.id,
        })
        
        discount_tier._compute_discount_percentage()
        display = discount_tier.get_discount_display()
        self.assertIn('Save 50%', display)
        
        # Test premium tier
        premium_tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.corporate_type.id,
            'price': 450.00,  # 50% markup
            'currency_id': self.env.company.currency_id.id,
        })
        
        premium_tier._compute_discount_percentage()
        display = premium_tier.get_discount_display()
        # Premium pricing shows as standard pricing since discount_percentage is 0
        self.assertIn('Standard pricing', display)

    def test_name_get_and_search(self):
        """Test name_get and name search functionality."""
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        # Test name_get
        name_get_result = tier.name_get()
        display_name = name_get_result[0][1]
        self.assertIn(self.test_subscription.name, display_name)
        self.assertIn(self.student_type.name, display_name)
        self.assertIn('150.0', display_name)

    def test_multiple_tiers_same_subscription(self):
        """Test multiple pricing tiers for the same subscription."""
        tiers_data = [
            (self.student_type.id, 100.00),
            (self.individual_type.id, 250.00),
            (self.retired_type.id, 200.00),
            (self.corporate_type.id, 400.00),
        ]
        
        created_tiers = []
        for member_type_id, price in tiers_data:
            tier = self.PricingTier.create({
                'subscription_product_id': self.test_subscription.id,
                'member_type_id': member_type_id,
                'price': price,
                'currency_id': self.env.company.currency_id.id,
            })
            created_tiers.append(tier)
        
        # Test that all tiers were created
        self.assertEqual(len(created_tiers), 4)
        
        # Test subscription's computed fields
        self.test_subscription._compute_has_member_pricing()
        self.test_subscription._compute_price_range()
        
        self.assertTrue(self.test_subscription.has_member_pricing)
        self.assertEqual(self.test_subscription.min_member_price, 100.00)
        self.assertEqual(self.test_subscription.max_member_price, 400.00)

    def test_pricing_tier_lifecycle(self):
        """Test complete lifecycle of pricing tiers."""
        # Create initial tier
        tier = self.PricingTier.create({
            'subscription_product_id': self.test_subscription.id,
            'member_type_id': self.student_type.id,
            'price': 150.00,
            'currency_id': self.env.company.currency_id.id,
        })
        
        # Update price
        tier.write({'price': 125.00})
        tier._compute_discount_percentage()
        
        # Check updated discount calculation
        expected_discount = ((300.00 - 125.00) / 300.00) * 100
        self.assertAlmostEqual(tier.discount_percentage, expected_discount, places=1)
        
        # Add validity period
        today = date.today()
        future_date = today + timedelta(days=60)
        
        tier.write({
            'valid_from': today,
            'valid_to': future_date,
            'requires_verification': True,
            'verification_criteria': 'Updated verification requirements'
        })
        
        tier._compute_is_currently_available()
        self.assertTrue(tier.is_currently_available)
        
        # Test pricing details after updates
        details = tier.get_pricing_details()
        self.assertEqual(details['pricing']['price'], 125.00)
        self.assertTrue(details['verification']['requires_verification'])