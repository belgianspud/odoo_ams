"""Test cases for subscription toggle functionality."""

from odoo.tests import common
from odoo.exceptions import ValidationError


class TestSubscriptionToggle(common.TransactionCase):
    """Test subscription toggle functionality on product.template."""

    def setUp(self):
        super().setUp()
        self.Product = self.env['product.template']
        self.SubscriptionProduct = self.env['ams.subscription.product']

    def test_enable_subscription_on_new_product(self):
        """Test enabling subscription on a new product."""
        product = self.Product.create({
            'name': 'Test Product',
            'detailed_type': 'service',
            'sale_ok': True,
            'is_subscription_product': True,
        })
        
        # Should auto-create subscription definition
        self.assertTrue(product.subscription_product_id)
        self.assertEqual(product.subscription_product_id.name, 'Test Product Subscription')
        self.assertEqual(product.subscription_product_id.product_id, product)

    def test_enable_subscription_on_existing_product(self):
        """Test enabling subscription on an existing product."""
        # Create regular product first
        product = self.Product.create({
            'name': 'Existing Product',
            'detailed_type': 'consu',
            'sale_ok': True,
        })
        
        # Initially no subscription
        self.assertFalse(product.is_subscription_product)
        self.assertFalse(product.subscription_product_id)
        
        # Enable subscription
        product.write({
            'is_subscription_product': True,
            'detailed_type': 'service',  # Should be service for subscriptions
        })
        
        # Should auto-create subscription definition
        self.assertTrue(product.subscription_product_id)
        self.assertEqual(product.subscription_product_id.product_id, product)

    def test_disable_subscription(self):
        """Test disabling subscription on a product."""
        product = self.Product.create({
            'name': 'Test Product',
            'is_subscription_product': True,
        })
        
        subscription_id = product.subscription_product_id.id
        
        # Disable subscription
        product.is_subscription_product = False
        
        # Subscription link should be cleared
        self.assertFalse(product.subscription_product_id)
        
        # But subscription record should still exist (for data integrity)
        subscription = self.SubscriptionProduct.browse(subscription_id)
        self.assertTrue(subscription.exists())

    def test_subscription_auto_configuration(self):
        """Test automatic configuration when enabling subscription."""
        product = self.Product.create({
            'name': 'Auto Config Test',
            'detailed_type': 'consu',  # Not service initially
            'sale_ok': False,  # Not saleable initially
            'is_subscription_product': True,
        })
        
        # Should auto-configure as service and saleable
        self.assertEqual(product.detailed_type, 'service')
        self.assertTrue(product.sale_ok)

    def test_subscription_code_generation(self):
        """Test automatic subscription code generation."""
        product = self.Product.create({
            'name': 'Code Test Product',
            'default_code': 'TEST123',
            'is_subscription_product': True,
        })
        
        # Should generate code based on product code
        self.assertEqual(product.subscription_product_id.code, 'TEST123')
        
        # Test without product code
        product2 = self.Product.create({
            'name': 'No Code Product',
            'is_subscription_product': True,
        })
        
        # Should generate fallback code
        self.assertTrue(product2.subscription_product_id.code.startswith('SUB_'))

    def test_subscription_smart_defaults(self):
        """Test smart default detection from product name."""
        # Test enterprise detection
        enterprise_product = self.Product.create({
            'name': 'Enterprise Corporate Membership',
            'is_subscription_product': True,
        })
        
        self.assertEqual(enterprise_product.subscription_product_id.subscription_scope, 'enterprise')
        
        # Test duration detection
        monthly_product = self.Product.create({
            'name': 'Monthly Professional Service',
            'is_subscription_product': True,
        })
        
        self.assertEqual(monthly_product.subscription_product_id.default_duration, 1)
        self.assertEqual(monthly_product.subscription_product_id.duration_unit, 'months')
        
        # Test type detection
        chapter_product = self.Product.create({
            'name': 'Local Chapter Membership',
            'is_subscription_product': True,
        })
        
        self.assertEqual(chapter_product.subscription_product_id.product_type, 'chapter')

    def test_subscription_validation(self):
        """Test validation constraints for subscription products."""
        # Test that subscription products should be services
        with self.assertRaises(ValidationError):
            self.Product.create({
                'name': 'Invalid Subscription',
                'detailed_type': 'product',  # Physical product
                'is_subscription_product': True,
            })

    def test_subscription_summary(self):
        """Test subscription summary method."""
        product = self.Product.create({
            'name': 'Summary Test',
            'is_subscription_product': True,
            'list_price': 100.0,
        })
        
        summary = product.get_subscription_summary()
        
        self.assertTrue(summary['is_subscription'])
        self.assertEqual(summary['scope'], 'individual')
        self.assertEqual(summary['type'], 'membership')
        self.assertEqual(summary['price']['default'], 100.0)

    def test_subscription_onchange_methods(self):
        """Test onchange methods for subscription toggle."""
        product = self.Product.new({
            'name': 'OnChange Test',
            'detailed_type': 'consu',
            'sale_ok': False,
        })
        
        # Test onchange when enabling subscription
        product.is_subscription_product = True
        product._onchange_is_subscription_product()
        
        self.assertEqual(product.detailed_type, 'service')
        self.assertTrue(product.sale_ok)

    def test_name_display_for_subscriptions(self):
        """Test custom name display for subscription products."""
        product = self.Product.create({
            'name': 'Display Test Product',
            'is_subscription_product': True,
        })
        
        name_get_result = product.name_get()
        display_name = name_get_result[0][1]
        
        self.assertTrue(display_name.startswith('[SUBSCRIPTION]'))
        self.assertIn('Display Test Product', display_name)

    def test_action_methods(self):
        """Test action methods for subscription products."""
        product = self.Product.create({
            'name': 'Action Test Product',
            'is_subscription_product': True,
        })
        
        # Test configure subscription action
        action = product.action_configure_subscription()
        self.assertEqual(action['res_model'], 'ams.subscription.product')
        self.assertEqual(action['res_id'], product.subscription_product_id.id)
        
        # Test manage pricing tiers action
        action = product.action_manage_pricing_tiers()
        self.assertEqual(action['res_model'], 'ams.subscription.pricing.tier')
        self.assertIn(
            ('subscription_product_id', '=', product.subscription_product_id.id),
            action['domain']
        )

    def test_subscription_wizard_action(self):
        """Test subscription creation wizard action."""
        product = self.Product.create({
            'name': 'Wizard Test Product',
            'is_subscription_product': False,
        })
        
        action = product.action_create_subscription_wizard()
        self.assertEqual(action['res_model'], 'ams.subscription.builder.wizard')
        self.assertEqual(action['context']['default_product_id'], product.id)

    def test_bulk_subscription_operations(self):
        """Test bulk enabling/disabling of subscriptions."""
        products = self.Product.create([
            {'name': 'Bulk Test 1', 'detailed_type': 'service'},
            {'name': 'Bulk Test 2', 'detailed_type': 'service'},
            {'name': 'Bulk Test 3', 'detailed_type': 'service'},
        ])
        
        # Bulk enable subscriptions
        products.write({'is_subscription_product': True})
        
        # All should have subscription definitions
        for product in products:
            self.assertTrue(product.subscription_product_id)
            self.assertEqual(product.subscription_product_id.product_id, product)

    def test_subscription_search_filters(self):
        """Test search filters for subscription products."""
        # Create mix of products
        regular_product = self.Product.create({
            'name': 'Regular Product',
            'is_subscription_product': False,
        })
        
        subscription_product = self.Product.create({
            'name': 'Subscription Product', 
            'is_subscription_product': True,
        })
        
        # Test subscription filter
        subscription_products = self.Product.search([
            ('is_subscription_product', '=', True)
        ])
        
        self.assertIn(subscription_product, subscription_products)
        self.assertNotIn(regular_product, subscription_products)

    def test_computed_fields(self):
        """Test computed fields for subscription products."""
        product = self.Product.create({
            'name': 'Computed Test',
            'is_subscription_product': True,
            'list_price': 200.0,
        })
        
        # Create some pricing tiers
        self.env['ams.subscription.pricing.tier'].create([
            {
                'subscription_product_id': product.subscription_product_id.id,
                'member_type_id': self.env.ref('ams_member_data.member_type_student').id,
                'price': 100.0,
                'currency_id': self.env.company.currency_id.id,
            },
            {
                'subscription_product_id': product.subscription_product_id.id,
                'member_type_id': self.env.ref('ams_member_data.member_type_individual').id,
                'price': 180.0,
                'currency_id': self.env.company.currency_id.id,
            }
        ])
        
        # Recompute fields
        product.subscription_product_id._compute_pricing_tier_count()
        product._compute_pricing_tier_count()
        
        self.assertEqual(product.pricing_tier_count, 2)

    def test_subscription_uniqueness(self):
        """Test that products can only have one subscription configuration."""
        product = self.Product.create({
            'name': 'Unique Test',
            'is_subscription_product': True,
        })
        
        # Try to create duplicate subscription configuration
        with self.assertRaises(Exception):  # Should violate unique constraint
            self.SubscriptionProduct.create({
                'name': 'Duplicate Subscription',
                'code': 'DUP_001',
                'product_id': product.id,
                'subscription_scope': 'individual',
                'product_type': 'membership',
                'default_duration': 12,
                'duration_unit': 'months',
                'default_price': 100.0,
                'currency_id': self.env.company.currency_id.id,
            })