# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class TestAMSProductsBase(TransactionCase):
    """Test cases for simplified AMS Products Base functionality."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Get models
        self.ProductTemplate = self.env['product.template']
        self.ProductProduct = self.env['product.product']
        self.ProductCategory = self.env['product.category']
        self.Partner = self.env['res.partner']
        
        # Create test AMS categories (leveraging ams_product_types)
        self.event_category = self.ProductCategory.create({
            'name': 'Test Event Category',
            'is_ams_category': True,
            'ams_category_type': 'event',
            'requires_member_pricing': True,
            'member_discount_percent': 20.0,
            'is_digital_category': False,
            'requires_inventory': False,
        })
        
        self.digital_category = self.ProductCategory.create({
            'name': 'Test Digital Category',
            'is_ams_category': True,
            'ams_category_type': 'digital',
            'requires_member_pricing': True,
            'member_discount_percent': 15.0,
            'is_digital_category': True,
            'requires_inventory': False,
        })
        
        self.membership_category = self.ProductCategory.create({
            'name': 'Test Membership Category',
            'is_ams_category': True,
            'ams_category_type': 'membership',
            'requires_member_pricing': False,
            'is_membership_category': True,
            'grants_portal_access': True,
            'is_digital_category': False,
            'requires_inventory': False,
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
        
        # Create test attachment for digital products
        self.test_attachment = self.env['ir.attachment'].create({
            'name': 'test_file.pdf',
            'datas': b'VGVzdCBjb250ZW50',  # Base64 encoded "Test content"
            'mimetype': 'application/pdf',
        })

    # ========================================================================
    # PRODUCT TEMPLATE TESTS
    # ========================================================================

    def test_ams_product_detection_from_category(self):
        """Test that AMS products are auto-detected from category"""
        # Create product with AMS category
        product = self.ProductTemplate.create({
            'name': 'Test AMS Product',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        # Should be detected as AMS product
        self.assertTrue(product.is_ams_product)
        self.assertEqual(product.ams_category_display, 'event')
        
        # Create product with non-AMS category
        standard_category = self.ProductCategory.create({
            'name': 'Standard Category',
            'is_ams_category': False,
        })
        
        standard_product = self.ProductTemplate.create({
            'name': 'Standard Product',
            'categ_id': standard_category.id,
            'list_price': 50.0,
        })
        
        # Should not be AMS product
        self.assertFalse(standard_product.is_ams_product)

    def test_member_pricing_calculation(self):
        """Test member pricing calculation from category discount"""
        product = self.ProductTemplate.create({
            'name': 'Member Pricing Test',
            'categ_id': self.event_category.id,  # 20% discount
            'list_price': 100.0,
        })
        
        # Test member pricing calculation
        self.assertEqual(product.member_price, 80.0)  # 20% discount
        self.assertEqual(product.member_savings, 20.0)
        
        # Test pricing summary
        self.assertIn('Members: $80.00', product.pricing_summary)
        self.assertIn('Save $20.00', product.pricing_summary)
        self.assertIn('Non-members: $100.00', product.pricing_summary)

    def test_get_price_for_partner(self):
        """Test partner-specific pricing"""
        product = self.ProductTemplate.create({
            'name': 'Partner Pricing Test',
            'categ_id': self.event_category.id,  # 20% member discount
            'list_price': 100.0,
        })
        
        # Test member gets discounted price
        member_price = product.get_price_for_partner(self.member_partner)
        self.assertEqual(member_price, 80.0)
        
        # Test non-member gets regular price
        non_member_price = product.get_price_for_partner(self.non_member_partner)
        self.assertEqual(non_member_price, 100.0)
        
        # Test no partner provided
        no_partner_price = product.get_price_for_partner(None)
        self.assertEqual(no_partner_price, 100.0)

    def test_membership_requirement_detection(self):
        """Test membership requirement detection"""
        # Membership products require membership
        membership_product = self.ProductTemplate.create({
            'name': 'Membership Product',
            'categ_id': self.membership_category.id,
            'list_price': 150.0,
        })
        
        self.assertTrue(membership_product.requires_membership)
        
        # Regular event products don't require membership
        event_product = self.ProductTemplate.create({
            'name': 'Event Product',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        self.assertFalse(event_product.requires_membership)

    def test_can_be_purchased_by_partner(self):
        """Test purchase permission checking"""
        membership_product = self.ProductTemplate.create({
            'name': 'Members Only Product',
            'categ_id': self.membership_category.id,
            'list_price': 150.0,
        })
        
        # Member can purchase
        self.assertTrue(
            membership_product.can_be_purchased_by_partner(self.member_partner)
        )
        
        # Non-member cannot purchase
        self.assertFalse(
            membership_product.can_be_purchased_by_partner(self.non_member_partner)
        )
        
        # Regular product can be purchased by anyone
        event_product = self.ProductTemplate.create({
            'name': 'Public Event',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        self.assertTrue(event_product.can_be_purchased_by_partner(self.member_partner))
        self.assertTrue(event_product.can_be_purchased_by_partner(self.non_member_partner))

    def test_digital_content_handling(self):
        """Test digital content detection and validation"""
        # Digital product with URL
        digital_product = self.ProductTemplate.create({
            'name': 'Digital Product with URL',
            'categ_id': self.digital_category.id,
            'list_price': 50.0,
            'digital_url': 'https://example.com/download',
        })
        
        self.assertTrue(digital_product.has_digital_content)
        
        # Digital product with attachment
        digital_product_file = self.ProductTemplate.create({
            'name': 'Digital Product with File',
            'categ_id': self.digital_category.id,
            'list_price': 75.0,
            'digital_attachment_id': self.test_attachment.id,
        })
        
        self.assertTrue(digital_product_file.has_digital_content)
        
        # Digital product with no content
        digital_product_empty = self.ProductTemplate.create({
            'name': 'Digital Product Empty',
            'categ_id': self.digital_category.id,
            'list_price': 25.0,
        })
        
        self.assertFalse(digital_product_empty.has_digital_content)

    def test_get_digital_content_access(self):
        """Test digital content access information"""
        digital_product = self.ProductTemplate.create({
            'name': 'Digital Access Test',
            'categ_id': self.digital_category.id,
            'list_price': 50.0,
            'digital_url': 'https://example.com/secure-download',
            'digital_attachment_id': self.test_attachment.id,
        })
        
        # Test access for member
        member_access = digital_product.get_digital_content_access(self.member_partner)
        self.assertTrue(member_access['is_digital'])
        self.assertTrue(member_access['has_content'])
        self.assertTrue(member_access['can_access'])
        self.assertEqual(member_access['download_url'], 'https://example.com/secure-download')
        
        # Test access for non-member
        non_member_access = digital_product.get_digital_content_access(self.non_member_partner)
        self.assertTrue(non_member_access['is_digital'])
        self.assertTrue(non_member_access['has_content'])
        self.assertTrue(non_member_access['can_access'])  # No membership restriction

    def test_simple_sku_generation(self):
        """Test simple SKU generation"""
        product = self.ProductTemplate.create({
            'name': 'Test SKU Generation Product',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        # Should have generated SKU
        self.assertTrue(product.default_code)
        self.assertIn('TESTSKU', product.default_code.upper())
        
        # Test uniqueness
        product2 = self.ProductTemplate.create({
            'name': 'Test SKU Generation Product',  # Same name
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        self.assertNotEqual(product.default_code, product2.default_code)

    def test_category_onchange(self):
        """Test category onchange behavior"""
        product = self.ProductTemplate.new({
            'name': 'Category Change Test',
            'list_price': 100.0,
        })
        
        # Set category and trigger onchange
        product.categ_id = self.event_category
        product._onchange_categ_id()
        
        # Should inherit category properties
        self.assertTrue(product.is_ams_product)

    # ========================================================================
    # VALIDATION TESTS
    # ========================================================================

    def test_digital_url_validation(self):
        """Test digital URL format validation"""
        # Valid URL should work
        valid_product = self.ProductTemplate.create({
            'name': 'Valid URL Product',
            'categ_id': self.digital_category.id,
            'list_price': 50.0,
            'digital_url': 'https://example.com/download',
        })
        self.assertEqual(valid_product.digital_url, 'https://example.com/download')
        
        # Invalid URL should raise error
        with self.assertRaises(ValidationError):
            self.ProductTemplate.create({
                'name': 'Invalid URL Product',
                'categ_id': self.digital_category.id,
                'list_price': 50.0,
                'digital_url': 'not-a-valid-url',
            })

    def test_digital_content_requirements(self):
        """Test digital product content requirements"""
        # Digital product missing content should raise error
        with self.assertRaises(ValidationError):
            product = self.ProductTemplate.create({
                'name': 'Missing Content Product',
                'categ_id': self.digital_category.id,
                'list_price': 50.0,
                # No digital_url or digital_attachment_id
            })
            # Trigger validation
            product._check_digital_content_requirements()

    # ========================================================================
    # QUERY METHOD TESTS
    # ========================================================================

    def test_get_ams_products_by_category_type(self):
        """Test getting products by category type"""
        # Create products of different types
        event_product = self.ProductTemplate.create({
            'name': 'Event Product',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        digital_product = self.ProductTemplate.create({
            'name': 'Digital Product',
            'categ_id': self.digital_category.id,
            'list_price': 50.0,
        })
        
        # Test filtering by category type
        event_products = self.ProductTemplate.get_ams_products_by_category_type('event')
        self.assertIn(event_product, event_products)
        self.assertNotIn(digital_product, event_products)
        
        # Test getting all AMS products
        all_ams_products = self.ProductTemplate.get_ams_products_by_category_type()
        self.assertIn(event_product, all_ams_products)
        self.assertIn(digital_product, all_ams_products)

    def test_get_member_pricing_products(self):
        """Test getting products with member pricing"""
        member_pricing_product = self.ProductTemplate.create({
            'name': 'Member Pricing Product',
            'categ_id': self.event_category.id,  # Has member pricing
            'list_price': 100.0,
        })
        
        no_member_pricing_product = self.ProductTemplate.create({
            'name': 'No Member Pricing Product',
            'categ_id': self.membership_category.id,  # No member pricing
            'list_price': 150.0,
        })
        
        member_pricing_products = self.ProductTemplate.get_member_pricing_products()
        self.assertIn(member_pricing_product, member_pricing_products)
        self.assertNotIn(no_member_pricing_product, member_pricing_products)

    def test_get_digital_products(self):
        """Test getting digital products"""
        digital_product = self.ProductTemplate.create({
            'name': 'Digital Product',
            'categ_id': self.digital_category.id,
            'list_price': 50.0,
        })
        
        physical_product = self.ProductTemplate.create({
            'name': 'Physical Product',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        digital_products = self.ProductTemplate.get_digital_products()
        self.assertIn(digital_product, digital_products)
        self.assertNotIn(physical_product, digital_products)

    # ========================================================================
    # PRODUCT VARIANT TESTS
    # ========================================================================

    def test_variant_ams_detection(self):
        """Test variant AMS detection from template"""
        template = self.ProductTemplate.create({
            'name': 'Variant Template',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        variant = template.product_variant_ids[0]
        
        self.assertTrue(variant.template_is_ams_product)
        self.assertEqual(variant.template_ams_category_display, 'event')

    def test_variant_effective_sku(self):
        """Test variant effective SKU computation"""
        template = self.ProductTemplate.create({
            'name': 'SKU Variant Template',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
            'default_code': 'TEMPLATE-SKU',
        })
        
        variant = template.product_variant_ids[0]
        
        # Single variant should use template SKU
        self.assertEqual(variant.effective_sku, 'TEMPLATE-SKU')
        
        # Create additional variant
        variant2 = self.ProductProduct.create({
            'product_tmpl_id': template.id,
            'default_code': 'VARIANT-SKU',
        })
        
        # Variant with own SKU should use it
        self.assertEqual(variant2.effective_sku, 'VARIANT-SKU')

    def test_variant_pricing_delegation(self):
        """Test that variant pricing delegates to template"""
        template = self.ProductTemplate.create({
            'name': 'Variant Pricing Template',
            'categ_id': self.event_category.id,  # 20% member discount
            'list_price': 100.0,
        })
        
        variant = template.product_variant_ids[0]
        
        # Test variant pricing matches template
        member_price = variant.get_price_for_partner(self.member_partner)
        self.assertEqual(member_price, 80.0)  # 20% discount
        
        non_member_price = variant.get_price_for_partner(self.non_member_partner)
        self.assertEqual(non_member_price, 100.0)

    def test_variant_availability_status(self):
        """Test variant availability status computation"""
        # Digital product variant
        digital_template = self.ProductTemplate.create({
            'name': 'Digital Variant Template',
            'categ_id': self.digital_category.id,
            'list_price': 50.0,
            'digital_url': 'https://example.com/download',
        })
        
        digital_variant = digital_template.product_variant_ids[0]
        self.assertEqual(digital_variant.availability_status, 'digital_available')
        
        # Service product variant
        service_template = self.ProductTemplate.create({
            'name': 'Service Variant Template',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
            'type': 'service',
        })
        
        service_variant = service_template.product_variant_ids[0]
        self.assertEqual(service_variant.availability_status, 'service_available')

    def test_variant_name_get(self):
        """Test variant enhanced name display"""
        template = self.ProductTemplate.create({
            'name': 'Name Display Template',
            'categ_id': self.membership_category.id,  # Requires membership
            'list_price': 150.0,
            'default_code': 'NAME-DISPLAY',
        })
        
        variant = template.product_variant_ids[0]
        name_display = variant.name_get()[0][1]
        
        # Should include SKU and membership indicator
        self.assertIn('[NAME-DISPLAY]', name_display)
        self.assertIn('(Members Only)', name_display)

    def test_variant_query_methods(self):
        """Test variant query methods"""
        # Create templates of different types
        event_template = self.ProductTemplate.create({
            'name': 'Event Variant Query',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        digital_template = self.ProductTemplate.create({
            'name': 'Digital Variant Query',
            'categ_id': self.digital_category.id,
            'list_price': 50.0,
            'digital_url': 'https://example.com/test',
        })
        
        membership_template = self.ProductTemplate.create({
            'name': 'Membership Variant Query',
            'categ_id': self.membership_category.id,
            'list_price': 150.0,
        })
        
        # Get variants
        event_variant = event_template.product_variant_ids[0]
        digital_variant = digital_template.product_variant_ids[0]
        membership_variant = membership_template.product_variant_ids[0]
        
        # Test query methods
        event_variants = self.ProductProduct.get_ams_variants_by_category_type('event')
        self.assertIn(event_variant, event_variants)
        self.assertNotIn(digital_variant, event_variants)
        
        membership_required_variants = self.ProductProduct.get_membership_required_variants()
        self.assertIn(membership_variant, membership_required_variants)
        self.assertNotIn(event_variant, membership_required_variants)

    # ========================================================================
    # INTEGRATION TESTS
    # ========================================================================

    def test_ams_member_data_integration(self):
        """Test integration with ams_member_data module"""
        product = self.ProductTemplate.create({
            'name': 'Integration Test Product',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        # Test membership checking uses ams_member_data fields
        self.assertTrue(product._check_partner_membership(self.member_partner))
        self.assertFalse(product._check_partner_membership(self.non_member_partner))

    def test_ams_product_types_integration(self):
        """Test integration with ams_product_types module"""
        # Test that category attributes drive product behavior
        product = self.ProductTemplate.create({
            'name': 'Category Integration Test',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        # Should inherit from category
        self.assertTrue(product.is_ams_product)
        self.assertEqual(product.ams_category_display, 'event')
        self.assertEqual(product.member_price, 80.0)  # 20% discount from category

    def test_legacy_system_integration(self):
        """Test legacy system ID handling"""
        product = self.ProductTemplate.create({
            'name': 'Legacy Integration Product',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
            'legacy_product_id': 'OLD_SYSTEM_12345',
        })
        
        variant = product.product_variant_ids[0]
        variant.variant_legacy_id = 'OLD_VARIANT_67890'
        
        self.assertEqual(product.legacy_product_id, 'OLD_SYSTEM_12345')
        self.assertEqual(variant.variant_legacy_id, 'OLD_VARIANT_67890')

    # ========================================================================
    # ACTION METHOD TESTS
    # ========================================================================

    def test_action_view_category(self):
        """Test action to view product category"""
        product = self.ProductTemplate.create({
            'name': 'Action Test Product',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        action = product.action_view_category()
        self.assertEqual(action['res_model'], 'product.category')
        self.assertEqual(action['res_id'], self.event_category.id)

    def test_action_test_member_pricing(self):
        """Test member pricing test action"""
        product = self.ProductTemplate.create({
            'name': 'Pricing Test Product',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        # Should return notification action
        action = product.action_test_member_pricing()
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'display_notification')

    # ========================================================================
    # PERFORMANCE AND EDGE CASES
    # ========================================================================

    def test_performance_with_multiple_products(self):
        """Test performance with multiple products"""
        # Create multiple products
        products = []
        for i in range(10):
            product = self.ProductTemplate.create({
                'name': f'Performance Test Product {i}',
                'categ_id': self.event_category.id,
                'list_price': 100.0 + i,
            })
            products.append(product)
        
        # Test bulk query methods
        ams_products = self.ProductTemplate.get_ams_products_by_category_type('event')
        self.assertTrue(len(ams_products) >= 10)
        
        member_pricing_products = self.ProductTemplate.get_member_pricing_products()
        for product in products:
            self.assertIn(product, member_pricing_products)

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        product = self.ProductTemplate.create({
            'name': 'Edge Case Product',
            'categ_id': self.event_category.id,
            'list_price': 100.0,
        })
        
        # Test with None partner
        price = product.get_price_for_partner(None)
        self.assertEqual(price, 100.0)
        
        # Test with partner missing membership fields
        minimal_partner = self.Partner.create({'name': 'Minimal Partner'})
        can_purchase = product.can_be_purchased_by_partner(minimal_partner)
        self.assertTrue(can_purchase)  # Non-membership-required product

    def tearDown(self):
        """Clean up after tests"""
        super().tearDown()
        _logger.info("AMS Products Base tests completed successfully")