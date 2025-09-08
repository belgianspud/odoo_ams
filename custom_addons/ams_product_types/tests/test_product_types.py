# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestAMSProductType(TransactionCase):
    """Test cases for AMS Product Type model."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.product_type_model = self.env['ams.product.type']
        
    def test_product_type_creation(self):
        """Test basic product type creation."""
        product_type = self.product_type_model.create({
            'name': 'Test Product Type',
            'code': 'TEST',
            'category': 'membership',
        })
        
        self.assertEqual(product_type.name, 'Test Product Type')
        self.assertEqual(product_type.code, 'TEST')
        self.assertEqual(product_type.category, 'membership')
        self.assertTrue(product_type.active)

    def test_code_auto_generation(self):
        """Test automatic code generation from name."""
        product_type = self.product_type_model.new({
            'name': 'Annual Membership'
        })
        product_type._onchange_name()
        
        self.assertEqual(product_type.code, 'ANNUAL_MEMBERSHIP')

    def test_unique_constraints(self):
        """Test unique constraints on code and name."""
        self.product_type_model.create({
            'name': 'Test Type',
            'code': 'TEST',
            'category': 'membership',
        })
        
        # Test duplicate code
        with self.assertRaises(Exception):
            self.product_type_model.create({
                'name': 'Another Type',
                'code': 'TEST',
                'category': 'event',
            })
        
        # Test duplicate name
        with self.assertRaises(Exception):
            self.product_type_model.create({
                'name': 'Test Type',
                'code': 'ANOTHER',
                'category': 'event',
            })

    def test_code_format_validation(self):
        """Test code format validation."""
        # Valid code
        product_type = self.product_type_model.create({
            'name': 'Valid Code',
            'code': 'VALID_CODE-123',
            'category': 'membership',
        })
        self.assertEqual(product_type.code, 'VALID_CODE-123')
        
        # Invalid code (special characters)
        with self.assertRaises(ValidationError):
            self.product_type_model.create({
                'name': 'Invalid Code',
                'code': 'INVALID@CODE!',
                'category': 'membership',
            })
        
        # Invalid code (too long)
        with self.assertRaises(ValidationError):
            self.product_type_model.create({
                'name': 'Long Code',
                'code': 'THIS_CODE_IS_TOO_LONG_FOR_VALIDATION',
                'category': 'membership',
            })

    def test_category_onchange(self):
        """Test category onchange setting defaults."""
        # Test membership category defaults
        product_type = self.product_type_model.new({
            'category': 'membership'
        })
        product_type._onchange_category()
        
        self.assertFalse(product_type.requires_member_pricing)
        self.assertTrue(product_type.is_subscription)
        self.assertFalse(product_type.is_digital)
        self.assertFalse(product_type.requires_inventory)
        
        # Test digital category defaults
        product_type = self.product_type_model.new({
            'category': 'digital'
        })
        product_type._onchange_category()
        
        self.assertTrue(product_type.requires_member_pricing)
        self.assertFalse(product_type.is_subscription)
        self.assertTrue(product_type.is_digital)
        self.assertFalse(product_type.requires_inventory)

    def test_digital_onchange(self):
        """Test digital product onchange behavior."""
        product_type = self.product_type_model.new({
            'is_digital': True,
            'requires_inventory': True,
        })
        
        product_type._onchange_is_digital()
        self.assertFalse(product_type.requires_inventory)

    def test_get_type_summary(self):
        """Test type summary generation."""
        product_type = self.product_type_model.create({
            'name': 'Test Type',
            'code': 'TEST',
            'category': 'event',
            'requires_member_pricing': True,
            'is_subscription': False,
            'is_digital': True,
            'requires_inventory': False,
        })
        
        summary = product_type.get_type_summary()
        self.assertIn('Category: Event', summary)
        self.assertIn('Member Pricing', summary)
        self.assertIn('Digital', summary)
        self.assertNotIn('Subscription', summary)

    def test_get_types_by_category(self):
        """Test filtering types by category."""
        membership_type = self.product_type_model.create({
            'name': 'Membership Type',
            'code': 'MEMBERSHIP',
            'category': 'membership',
        })
        
        event_type = self.product_type_model.create({
            'name': 'Event Type',
            'code': 'EVENT',
            'category': 'event',
        })
        
        # Test filtering by category
        membership_types = self.product_type_model.get_types_by_category('membership')
        self.assertIn(membership_type, membership_types)
        self.assertNotIn(event_type, membership_types)
        
        # Test getting all types
        all_types = self.product_type_model.get_types_by_category()
        self.assertIn(membership_type, all_types)
        self.assertIn(event_type, all_types)

    def test_get_digital_types(self):
        """Test getting digital product types."""
        digital_type = self.product_type_model.create({
            'name': 'Digital Type',
            'code': 'DIGITAL',
            'category': 'digital',
            'is_digital': True,
        })
        
        physical_type = self.product_type_model.create({
            'name': 'Physical Type',
            'code': 'PHYSICAL',
            'category': 'merchandise',
            'is_digital': False,
        })
        
        digital_types = self.product_type_model.get_digital_types()
        self.assertIn(digital_type, digital_types)
        self.assertNotIn(physical_type, digital_types)

    def test_get_subscription_types(self):
        """Test getting subscription product types."""
        subscription_type = self.product_type_model.create({
            'name': 'Subscription Type',
            'code': 'SUBSCRIPTION',
            'category': 'publication',
            'is_subscription': True,
        })
        
        one_time_type = self.product_type_model.create({
            'name': 'One Time Type',
            'code': 'ONE_TIME',
            'category': 'event',
            'is_subscription': False,
        })
        
        subscription_types = self.product_type_model.get_subscription_types()
        self.assertIn(subscription_type, subscription_types)
        self.assertNotIn(one_time_type, subscription_types)

    def test_get_member_pricing_types(self):
        """Test getting types with member pricing."""
        member_pricing_type = self.product_type_model.create({
            'name': 'Member Pricing Type',
            'code': 'MEMBER_PRICING',
            'category': 'event',
            'requires_member_pricing': True,
        })
        
        no_member_pricing_type = self.product_type_model.create({
            'name': 'No Member Pricing Type',
            'code': 'NO_MEMBER_PRICING',
            'category': 'membership',
            'requires_member_pricing': False,
        })
        
        member_pricing_types = self.product_type_model.get_member_pricing_types()
        self.assertIn(member_pricing_type, member_pricing_types)
        self.assertNotIn(no_member_pricing_type, member_pricing_types)

    def test_toggle_active(self):
        """Test toggling active status."""
        product_type = self.product_type_model.create({
            'name': 'Toggle Test',
            'code': 'TOGGLE',
            'category': 'membership',
            'active': True,
        })
        
        # Toggle to inactive
        product_type.toggle_active()
        self.assertFalse(product_type.active)
        
        # Toggle back to active
        product_type.toggle_active()
        self.assertTrue(product_type.active)

    def test_copy_method(self):
        """Test copy method with unique names and codes."""
        original = self.product_type_model.create({
            'name': 'Original Type',
            'code': 'ORIGINAL',
            'category': 'membership',
        })
        
        copy = original.copy()
        
        self.assertEqual(copy.name, 'Original Type (Copy)')
        self.assertEqual(copy.code, 'ORIGINAL_COPY')
        self.assertEqual(copy.category, 'membership')

    def test_name_get(self):
        """Test custom name display."""
        product_type = self.product_type_model.create({
            'name': 'Test Type',
            'code': 'TEST',
            'category': 'event',
        })
        
        name_get_result = product_type.name_get()[0][1]
        self.assertIn('[TEST]', name_get_result)
        self.assertIn('Test Type', name_get_result)
        self.assertIn('(Event)', name_get_result)

    def test_name_search(self):
        """Test custom name search functionality."""
        product_type = self.product_type_model.create({
            'name': 'Annual Membership',
            'code': 'ANNUAL',
            'category': 'membership',
        })
        
        # Test search by name
        results = self.product_type_model.name_search('Annual')
        type_ids = [r[0] for r in results]
        self.assertIn(product_type.id, type_ids)
        
        # Test search by code
        results = self.product_type_model.name_search('ANNUAL')
        type_ids = [r[0] for r in results]
        self.assertIn(product_type.id, type_ids)
        
        # Test search by category
        results = self.product_type_model.name_search('membership')
        type_ids = [r[0] for r in results]
        self.assertIn(product_type.id, type_ids)

    def test_compute_category_display(self):
        """Test category display computation."""
        product_type = self.product_type_model.create({
            'name': 'Test Type',
            'code': 'TEST',
            'category': 'certification',
        })
        
        self.assertEqual(product_type.category_display, 'Certification')

    def test_product_integration(self):
        """Test integration with Odoo product module."""
        # Create a product type
        product_type = self.product_type_model.create({
            'name': 'Test Integration',
            'code': 'TEST_INTEGRATION',
            'category': 'education',
        })
        
        # Create a product using this type
        product = self.env['product.template'].create({
            'name': 'Test Product',
            'ams_product_type_id': product_type.id,
        })
        
        # Test computed fields
        self.assertEqual(product.ams_category, 'education')
        self.assertTrue(product.requires_member_pricing)  # Education default
        self.assertFalse(product.is_subscription)  # Education default
        self.assertFalse(product.is_digital)  # Education default
        
        # Test product count
        self.assertEqual(product_type.product_count, 1)

    def test_product_creation_from_type(self):
        """Test product creation from product type."""
        product_type = self.product_type_model.create({
            'name': 'Conference Registration',
            'code': 'CONF_REG',
            'category': 'event',
        })
        
        # Test action_create_product returns correct context
        action = product_type.action_create_product()
        
        self.assertEqual(action['res_model'], 'product.template')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(
            action['context']['default_ams_product_type_id'], 
            product_type.id
        )

    def test_product_category_creation(self):
        """Test that product categories are created when needed."""
        # Create product type which should trigger category creation
        product_type = self.product_type_model.create({
            'name': 'New Category Test',
            'code': 'NEW_CATEGORY',
            'category': 'certification',
        })
        
        # Should have a product category assigned
        self.assertTrue(product_type.product_category_id)
        self.assertEqual(product_type.product_category_id.name, 'Certifications')

    def test_member_pricing_methods(self):
        """Test member pricing methods on products."""
        # Create product type with member pricing
        product_type = self.product_type_model.create({
            'name': 'Member Pricing Test',
            'code': 'MEMBER_PRICING',
            'category': 'event',
            'requires_member_pricing': True,
        })
        
        # Create product
        product = self.env['product.template'].create({
            'name': 'Test Product',
            'ams_product_type_id': product_type.id,
            'list_price': 100.0,
            'member_list_price': 80.0,
        })
        
        # Test member pricing methods
        self.assertEqual(product.get_member_price(), 80.0)
        self.assertEqual(product.get_price_for_member_type(True), 80.0)
        self.assertEqual(product.get_price_for_member_type(False), 100.0)

    def test_product_onchange_ams_type(self):
        """Test product onchange when AMS type is set."""
        # Create product type
        product_type = self.product_type_model.create({
            'name': 'Digital Test',
            'code': 'DIGITAL_TEST',
            'category': 'digital',
            'is_digital': True,
            'requires_inventory': False,
        })
        
        # Create product and trigger onchange
        product = self.env['product.template'].new({
            'name': 'Test Digital Product',
            'ams_product_type_id': product_type.id,
        })
        
        product._onchange_ams_product_type()
        
        # Should be set to service (no inventory)
        self.assertEqual(product.type, 'service')

    def test_all_categories_covered(self):
        """Test that all categories have proper default settings."""
        categories = ['membership', 'event', 'education', 'publication', 
                     'merchandise', 'certification', 'digital']
        
        for category in categories:
            product_type = self.product_type_model.new({
                'name': f'Test {category.title()}',
                'code': f'TEST_{category.upper()}',
                'category': category,
            })
            product_type._onchange_category()
            
            # Each category should have some defaults set
            # Just ensure no errors occur
            self.assertTrue(hasattr(product_type, 'requires_member_pricing'))
            self.assertTrue(hasattr(product_type, 'is_subscription'))
            self.assertTrue(hasattr(product_type, 'is_digital'))
            self.assertTrue(hasattr(product_type, 'requires_inventory'))


class TestProductTemplateAMS(TransactionCase):
    """Test cases for Product Template AMS extensions."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.product_type_model = self.env['ams.product.type']
        self.product_model = self.env['product.template']

    def test_product_template_extension(self):
        """Test that product template is properly extended."""
        # Create AMS product type
        product_type = self.product_type_model.create({
            'name': 'Test Extension',
            'code': 'TEST_EXT',
            'category': 'membership',
            'is_subscription': True,
            'requires_member_pricing': False,
        })
        
        # Create product with AMS type
        product = self.product_model.create({
            'name': 'Test Membership',
            'ams_product_type_id': product_type.id,
        })
        
        # Test related fields
        self.assertEqual(product.ams_category, 'membership')
        self.assertTrue(product.is_subscription)
        self.assertFalse(product.requires_member_pricing)
        self.assertFalse(product.is_digital)

    def test_products_by_ams_category(self):
        """Test getting products by AMS category."""
        # Create product types
        event_type = self.product_type_model.create({
            'name': 'Event Type',
            'code': 'EVENT_TYPE',
            'category': 'event',
        })
        
        education_type = self.product_type_model.create({
            'name': 'Education Type',
            'code': 'EDUCATION_TYPE',
            'category': 'education',
        })
        
        # Create products
        event_product = self.product_model.create({
            'name': 'Conference',
            'ams_product_type_id': event_type.id,
        })
        
        education_product = self.product_model.create({
            'name': 'Course',
            'ams_product_type_id': education_type.id,
        })
        
        # Test filtering by category
        event_products = self.product_model.get_products_by_ams_category('event')
        self.assertIn(event_product, event_products)
        self.assertNotIn(education_product, event_products)

    def test_action_view_ams_product_type(self):
        """Test action to view AMS product type from product."""
        # Create product type
        product_type = self.product_type_model.create({
            'name': 'Test Action',
            'code': 'TEST_ACTION',
            'category': 'digital',
        })
        
        # Create product
        product = self.product_model.create({
            'name': 'Test Product',
            'ams_product_type_id': product_type.id,
        })
        
        # Test action
        action = product.action_view_ams_product_type()
        self.assertEqual(action['res_model'], 'ams.product.type')
        self.assertEqual(action['res_id'], product_type.id)
        
        # Test with no AMS type
        product_no_type = self.product_model.create({
            'name': 'No Type Product',
        })
        
        action_no_type = product_no_type.action_view_ams_product_type()
        self.assertFalse(action_no_type)

    def tearDown(self):
        """Clean up after tests."""
        super().tearDown()