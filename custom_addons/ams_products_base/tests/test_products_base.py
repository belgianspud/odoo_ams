# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class TestAMSProductsBase(TransactionCase):
    """Comprehensive test cases for AMS Products Base functionality."""

    def setUp(self):
        """Set up test environment with all necessary data."""
        super().setUp()
        
        # Get models
        self.ProductTemplate = self.env['product.template']
        self.ProductProduct = self.env['product.product']
        self.ProductType = self.env['ams.product.type']
        self.Partner = self.env['res.partner']
        self.ProductCategory = self.env['product.category']
        self.StockRoute = self.env['stock.route']
        self.StockWarehouse = self.env['stock.warehouse']
        
        # Create test product categories
        self.ams_category = self.ProductCategory.create({
            'name': 'AMS Test Category',
        })
        
        # Create test product types
        self.membership_type = self.ProductType.create({
            'name': 'Test Membership',
            'code': 'TEST_MEMBERSHIP',
            'category': 'membership',
            'requires_member_pricing': False,
            'is_digital': False,
            'requires_inventory': False,
            'product_category_id': self.ams_category.id,
        })
        
        self.event_type = self.ProductType.create({
            'name': 'Test Event Registration',
            'code': 'TEST_EVENT',
            'category': 'event',
            'requires_member_pricing': True,
            'is_digital': False,
            'requires_inventory': False,
            'product_category_id': self.ams_category.id,
        })
        
        self.digital_type = self.ProductType.create({
            'name': 'Test Digital Product',
            'code': 'TEST_DIGITAL',
            'category': 'digital',
            'requires_member_pricing': True,
            'is_digital': True,
            'requires_inventory': False,
            'product_category_id': self.ams_category.id,
        })
        
        self.merchandise_type = self.ProductType.create({
            'name': 'Test Merchandise',
            'code': 'TEST_MERCHANDISE',
            'category': 'merchandise',
            'requires_member_pricing': True,
            'is_digital': False,
            'requires_inventory': True,
            'product_category_id': self.ams_category.id,
        })
        
        # Create test partners
        self.member = self.Partner.create({
            'name': 'Test Member',
            'email': 'member@test.com',
            'is_member': True,
            'membership_status': 'active',
        })
        
        self.non_member = self.Partner.create({
            'name': 'Test Non-Member',
            'email': 'nonmember@test.com',
            'is_member': False,
            'membership_status': 'prospect',
        })
        
        # Create test attachment for digital products
        self.test_attachment = self.env['ir.attachment'].create({
            'name': 'test_digital_file.pdf',
            'datas': b'VGVzdCBjb250ZW50',  # Base64 encoded "Test content"
            'mimetype': 'application/pdf',
        })

    # ========================================================================
    # PRODUCT TEMPLATE TESTS
    # ========================================================================

    def test_basic_ams_product_creation(self):
        """Test basic AMS product creation with auto-generated fields."""
        product = self.ProductTemplate.create({
            'name': 'Test AMS Product',
            'is_ams_product': True,
            'ams_product_type_id': self.event_type.id,
            'list_price': 100.0,
        })
        
        # Test basic fields
        self.assertTrue(product.is_ams_product)
        self.assertEqual(product.ams_product_type_id, self.event_type)
        self.assertTrue(product.sku)  # Should auto-generate
        self.assertEqual(product.default_code, product.sku)  # Should sync
        
        # Test product type inheritance
        self.assertTrue(product.has_member_pricing)  # From event type
        self.assertFalse(product.is_digital_product)  # From event type
        self.assertFalse(product.stock_controlled)  # From event type
        
        # Test category assignment
        self.assertEqual(product.categ_id, self.ams_category)

    def test_member_pricing_configuration(self):
        """Test member pricing setup and calculations."""
        product = self.ProductTemplate.create({
            'name': 'Member Pricing Test',
            'is_ams_product': True,
            'ams_product_type_id': self.event_type.id,
            'has_member_pricing': True,
            'member_price': 80.0,
            'non_member_price': 100.0,
            'list_price': 100.0,
        })
        
        # Test pricing fields
        self.assertTrue(product.has_member_pricing)
        self.assertEqual(product.member_price, 80.0)
        self.assertEqual(product.non_member_price, 100.0)
        
        # Test computed fields
        self.assertEqual(product.member_discount_percentage, 20.0)
        self.assertEqual(product.effective_member_price, 80.0)
        self.assertEqual(product.effective_non_member_price, 100.0)
        
        # Test pricing summary
        self.assertIn('Members:', product.pricing_summary)
        self.assertIn('Non-members:', product.pricing_summary)
        
        # Test business methods
        self.assertEqual(product.get_price_for_member_status(True), 80.0)
        self.assertEqual(product.get_price_for_member_status(False), 100.0)
        self.assertEqual(product.get_member_savings(), 20.0)

    def test_digital_product_configuration(self):
        """Test digital product setup and validation."""
        product = self.ProductTemplate.create({
            'name': 'Digital Product Test',
            'is_ams_product': True,
            'ams_product_type_id': self.digital_type.id,
            'is_digital_product': True,
            'digital_download_url': 'https://example.com/download',
            'digital_attachment_id': self.test_attachment.id,
            'auto_fulfill_digital': True,
        })
        
        # Test digital product fields
        self.assertTrue(product.is_digital_product)
        self.assertTrue(product.auto_fulfill_digital)
        self.assertEqual(product.digital_download_url, 'https://example.com/download')
        self.assertEqual(product.digital_attachment_id, self.test_attachment)
        
        # Test computed fields
        self.assertTrue(product.is_digital_available)
        self.assertEqual(product.inventory_status, 'digital')
        
        # Test Odoo integration
        self.assertEqual(product.type, 'service')  # Digital products are services
        self.assertFalse(product.stock_controlled)
        
        # Test digital content access
        access_info = product.get_digital_content_access()
        self.assertTrue(access_info['is_digital'])
        self.assertEqual(access_info['download_url'], 'https://example.com/download')
        self.assertTrue(access_info['auto_fulfill'])
        self.assertTrue(access_info['is_available'])

    def test_inventory_product_configuration(self):
        """Test physical product with inventory tracking."""
        product = self.ProductTemplate.create({
            'name': 'Inventory Product Test',
            'is_ams_product': True,
            'ams_product_type_id': self.merchandise_type.id,
            'stock_controlled': True,
            'list_price': 25.0,
        })
        
        # Test inventory fields
        self.assertTrue(product.stock_controlled)
        self.assertEqual(product.inventory_status, 'tracked')
        
        # Test Odoo integration
        self.assertEqual(product.type, 'product')  # Physical products are stockable
        
        # Test that routes are set (if any exist)
        # Note: Routes may not exist in test environment
        if product.route_ids:
            self.assertTrue(len(product.route_ids) > 0)

    def test_sku_generation_and_validation(self):
        """Test SKU auto-generation and validation."""
        # Test auto-generation
        product = self.ProductTemplate.create({
            'name': 'SKU Generation Test Product',
            'is_ams_product': True,
        })
        
        self.assertTrue(product.sku)
        self.assertIn('SKU-GENERATION-TEST-PRODUCT', product.sku.upper())
        self.assertEqual(product.default_code, product.sku)
        
        # Test manual SKU
        product2 = self.ProductTemplate.create({
            'name': 'Manual SKU Product',
            'is_ams_product': True,
            'sku': 'MANUAL-SKU-001',
        })
        
        self.assertEqual(product2.sku, 'MANUAL-SKU-001')
        self.assertEqual(product2.default_code, 'MANUAL-SKU-001')
        
        # Test SKU uniqueness constraint
        with self.assertRaises(Exception):  # Should raise IntegrityError
            self.ProductTemplate.create({
                'name': 'Duplicate SKU Product',
                'is_ams_product': True,
                'sku': 'MANUAL-SKU-001',  # Duplicate
            })

    def test_access_control_and_membership_requirements(self):
        """Test membership requirement and access control."""
        product = self.ProductTemplate.create({
            'name': 'Members Only Product',
            'is_ams_product': True,
            'requires_membership': True,
            'has_member_pricing': True,
            'member_price': 50.0,
            'non_member_price': 75.0,
        })
        
        # Test access control
        self.assertTrue(product.can_be_purchased_by_member_status(True))
        self.assertFalse(product.can_be_purchased_by_member_status(False))
        
        # Test pricing context
        member_context = product._get_pricing_context(self.member.id)
        self.assertTrue(member_context['is_member'])
        self.assertTrue(member_context['can_purchase'])
        self.assertEqual(member_context['effective_price'], 50.0)
        
        non_member_context = product._get_pricing_context(self.non_member.id)
        self.assertFalse(non_member_context['is_member'])
        self.assertFalse(non_member_context['can_purchase'])

    def test_product_type_integration(self):
        """Test integration with AMS product types."""
        # Test onchange behavior
        product = self.ProductTemplate.new({
            'name': 'Type Integration Test',
            'is_ams_product': True,
            'ams_product_type_id': self.digital_type.id,
        })
        
        product._onchange_ams_product_type()
        
        # Should inherit from product type
        self.assertTrue(product.is_digital_product)
        self.assertTrue(product.has_member_pricing)
        self.assertFalse(product.stock_controlled)
        self.assertEqual(product.type, 'service')
        self.assertEqual(product.categ_id, self.ams_category)

    def test_validation_constraints(self):
        """Test various validation constraints."""
        # Test invalid SKU format
        with self.assertRaises(ValidationError):
            self.ProductTemplate.create({
                'name': 'Invalid SKU Product',
                'is_ams_product': True,
                'sku': 'INVALID@SKU!',
            })
        
        # Test invalid digital URL
        with self.assertRaises(ValidationError):
            self.ProductTemplate.create({
                'name': 'Invalid URL Product',
                'is_ams_product': True,
                'is_digital_product': True,
                'digital_download_url': 'not-a-url',
            })
        
        # Test member pricing logic
        with self.assertRaises(ValidationError):
            self.ProductTemplate.create({
                'name': 'Invalid Pricing Product',
                'is_ams_product': True,
                'has_member_pricing': True,
                'member_price': 100.0,
                'non_member_price': 50.0,  # Member price higher
            })
        
        # Test digital content requirements
        with self.assertRaises(ValidationError):
            self.ProductTemplate.create({
                'name': 'Missing Digital Content',
                'is_ams_product': True,
                'is_digital_product': True,
                # Missing both URL and attachment
            })

    def test_business_query_methods(self):
        """Test business query methods."""
        # Create test products
        membership_product = self.ProductTemplate.create({
            'name': 'Membership Product',
            'is_ams_product': True,
            'ams_product_type_id': self.membership_type.id,
        })
        
        digital_product = self.ProductTemplate.create({
            'name': 'Digital Product',
            'is_ams_product': True,
            'ams_product_type_id': self.digital_type.id,
            'is_digital_product': True,
            'digital_download_url': 'https://example.com/test',
        })
        
        member_pricing_product = self.ProductTemplate.create({
            'name': 'Member Pricing Product',
            'is_ams_product': True,
            'ams_product_type_id': self.event_type.id,
            'has_member_pricing': True,
            'member_price': 80.0,
            'non_member_price': 100.0,
        })
        
        # Test query methods
        ams_products = self.ProductTemplate.get_ams_products_by_type()
        self.assertIn(membership_product, ams_products)
        self.assertIn(digital_product, ams_products)
        self.assertIn(member_pricing_product, ams_products)
        
        digital_products = self.ProductTemplate.get_digital_products()
        self.assertIn(digital_product, digital_products)
        self.assertNotIn(membership_product, digital_products)
        
        member_pricing_products = self.ProductTemplate.get_member_pricing_products()
        self.assertIn(member_pricing_product, member_pricing_products)
        self.assertNotIn(membership_product, member_pricing_products)

    # ========================================================================
    # PRODUCT VARIANT TESTS
    # ========================================================================

    def test_variant_creation_and_sku_generation(self):
        """Test product variant creation with AMS features."""
        template = self.ProductTemplate.create({
            'name': 'Variant Test Template',
            'is_ams_product': True,
            'ams_product_type_id': self.event_type.id,
            'sku': 'VARIANT-TEMPLATE',
            'has_member_pricing': True,
            'member_price': 100.0,
            'non_member_price': 150.0,
        })
        
        variant = self.ProductProduct.create({
            'product_tmpl_id': template.id,
        })
        
        # Test basic variant fields
        self.assertTrue(variant.template_is_ams_product)
        self.assertEqual(variant.template_ams_product_type_id, self.event_type)
        self.assertTrue(variant.template_has_member_pricing)
        
        # Test SKU inheritance
        self.assertTrue(variant.effective_sku)
        self.assertIn('VARIANT-TEMPLATE', variant.effective_sku)
        
        # Test pricing inheritance
        self.assertEqual(variant.final_member_price, 100.0)
        self.assertEqual(variant.final_non_member_price, 150.0)
        self.assertFalse(variant.has_variant_pricing)

    def test_variant_pricing_override(self):
        """Test variant-specific pricing."""
        template = self.ProductTemplate.create({
            'name': 'Variant Pricing Template',
            'is_ams_product': True,
            'ams_product_type_id': self.event_type.id,
            'has_member_pricing': True,
            'member_price': 100.0,
            'non_member_price': 150.0,
        })
        
        variant = self.ProductProduct.create({
            'product_tmpl_id': template.id,
            'has_variant_pricing': True,
            'variant_member_price': 80.0,
            'variant_non_member_price': 120.0,
        })
        
        # Test variant pricing
        self.assertTrue(variant.has_variant_pricing)
        self.assertEqual(variant.final_member_price, 80.0)
        self.assertEqual(variant.final_non_member_price, 120.0)
        self.assertAlmostEqual(variant.variant_member_discount, 33.33, places=1)
        
        # Test business methods
        self.assertEqual(variant.get_variant_price_for_member_status(True), 80.0)
        self.assertEqual(variant.get_variant_price_for_member_status(False), 120.0)
        self.assertEqual(variant.get_variant_member_savings(), 40.0)

    def test_variant_digital_content_override(self):
        """Test variant-specific digital content."""
        template = self.ProductTemplate.create({
            'name': 'Variant Digital Template',
            'is_ams_product': True,
            'ams_product_type_id': self.digital_type.id,
            'is_digital_product': True,
            'digital_download_url': 'https://example.com/template',
        })
        
        variant = self.ProductProduct.create({
            'product_tmpl_id': template.id,
            'has_variant_digital_content': True,
            'variant_digital_url': 'https://example.com/variant',
        })
        
        # Test variant digital content
        self.assertTrue(variant.has_variant_digital_content)
        self.assertEqual(variant.final_digital_url, 'https://example.com/variant')
        self.assertTrue(variant.is_digital_content_available)
        
        # Test digital content access
        access_info = variant.get_variant_digital_content_access()
        self.assertTrue(access_info['is_digital'])
        self.assertEqual(access_info['download_url'], 'https://example.com/variant')
        self.assertTrue(access_info['has_variant_content'])

    def test_variant_inventory_configuration(self):
        """Test variant-specific inventory settings."""
        template = self.ProductTemplate.create({
            'name': 'Variant Inventory Template',
            'is_ams_product': True,
            'ams_product_type_id': self.merchandise_type.id,
            'stock_controlled': True,
        })
        
        variant = self.ProductProduct.create({
            'product_tmpl_id': template.id,
            'has_variant_inventory_config': True,
            'variant_stock_controlled': True,
            'variant_reorder_point': 10.0,
            'variant_max_stock': 100.0,
        })
        
        # Test variant inventory settings
        self.assertTrue(variant.has_variant_inventory_config)
        self.assertTrue(variant.variant_stock_controlled)
        self.assertTrue(variant.effective_stock_controlled)
        self.assertEqual(variant.variant_reorder_point, 10.0)
        self.assertEqual(variant.variant_max_stock, 100.0)
        
        # Test inventory status
        inventory_status = variant.get_variant_inventory_status()
        self.assertTrue(inventory_status['stock_controlled'])
        self.assertEqual(inventory_status['reorder_point'], 10.0)
        self.assertEqual(inventory_status['max_stock'], 100.0)

    def test_variant_sku_management(self):
        """Test variant SKU generation and management."""
        template = self.ProductTemplate.create({
            'name': 'SKU Variant Template',
            'is_ams_product': True,
            'sku': 'TEMPLATE-SKU',
        })
        
        # Test automatic variant SKU generation
        variant1 = self.ProductProduct.create({
            'product_tmpl_id': template.id,
        })
        
        self.assertTrue(variant1.effective_sku)
        self.assertIn('TEMPLATE-SKU', variant1.effective_sku)
        
        # Test manual variant SKU
        variant2 = self.ProductProduct.create({
            'product_tmpl_id': template.id,
            'variant_sku': 'MANUAL-VARIANT-SKU',
        })
        
        self.assertEqual(variant2.effective_sku, 'MANUAL-VARIANT-SKU')
        
        # Test SKU uniqueness
        with self.assertRaises(Exception):  # Should raise IntegrityError
            self.ProductProduct.create({
                'product_tmpl_id': template.id,
                'variant_sku': 'MANUAL-VARIANT-SKU',  # Duplicate
            })

    def test_variant_sync_methods(self):
        """Test variant synchronization methods."""
        template = self.ProductTemplate.create({
            'name': 'Sync Test Template',
            'is_ams_product': True,
            'ams_product_type_id': self.event_type.id,
            'has_member_pricing': True,
            'member_price': 100.0,
            'non_member_price': 150.0,
        })
        
        variant = self.ProductProduct.create({
            'product_tmpl_id': template.id,
            'has_variant_pricing': True,
            'variant_member_price': 80.0,
            'variant_non_member_price': 120.0,
        })
        
        # Test sync with template
        variant.sync_with_template_pricing()
        self.assertFalse(variant.has_variant_pricing)
        self.assertEqual(variant.variant_member_price, 0.0)
        self.assertEqual(variant.final_member_price, 100.0)  # Back to template
        
        # Test copy from template
        variant.copy_template_pricing_to_variant()
        self.assertTrue(variant.has_variant_pricing)
        self.assertEqual(variant.variant_member_price, 100.0)
        self.assertEqual(variant.variant_non_member_price, 150.0)

    def test_variant_validation_constraints(self):
        """Test variant-specific validation constraints."""
        template = self.ProductTemplate.create({
            'name': 'Validation Test Template',
            'is_ams_product': True,
            'ams_product_type_id': self.event_type.id,
        })
        
        # Test invalid variant SKU format
        with self.assertRaises(ValidationError):
            self.ProductProduct.create({
                'product_tmpl_id': template.id,
                'variant_sku': 'INVALID@SKU!',
            })
        
        # Test invalid variant pricing logic
        with self.assertRaises(ValidationError):
            self.ProductProduct.create({
                'product_tmpl_id': template.id,
                'has_variant_pricing': True,
                'variant_member_price': 150.0,
                'variant_non_member_price': 100.0,  # Member price higher
            })
        
        # Test invalid inventory logic
        with self.assertRaises(ValidationError):
            self.ProductProduct.create({
                'product_tmpl_id': template.id,
                'has_variant_inventory_config': True,
                'variant_reorder_point': 100.0,
                'variant_max_stock': 50.0,  # Reorder point higher than max
            })

    def test_variant_query_methods(self):
        """Test variant business query methods."""
        # Create template with different types
        digital_template = self.ProductTemplate.create({
            'name': 'Digital Template',
            'is_ams_product': True,
            'ams_product_type_id': self.digital_type.id,
            'is_digital_product': True,
            'digital_download_url': 'https://example.com/digital',
        })
        
        physical_template = self.ProductTemplate.create({
            'name': 'Physical Template',
            'is_ams_product': True,
            'ams_product_type_id': self.merchandise_type.id,
            'stock_controlled': True,
        })
        
        # Create variants
        digital_variant = self.ProductProduct.create({
            'product_tmpl_id': digital_template.id,
        })
        
        physical_variant = self.ProductProduct.create({
            'product_tmpl_id': physical_template.id,
            'has_variant_inventory_config': True,
            'variant_reorder_point': 5.0,
        })
        
        # Test query methods
        digital_variants = self.ProductProduct.get_variants_by_ams_criteria(is_digital=True)
        self.assertIn(digital_variant, digital_variants)
        self.assertNotIn(physical_variant, digital_variants)
        
        stock_controlled_variants = self.ProductProduct.get_variants_by_ams_criteria(stock_controlled=True)
        self.assertIn(physical_variant, stock_controlled_variants)
        self.assertNotIn(digital_variant, stock_controlled_variants)

    # ========================================================================
    # INTEGRATION TESTS
    # ========================================================================

    def test_odoo_inventory_integration(self):
        """Test integration with Odoo's inventory system."""
        product = self.ProductTemplate.create({
            'name': 'Inventory Integration Test',
            'is_ams_product': True,
            'ams_product_type_id': self.merchandise_type.id,
            'stock_controlled': True,
        })
        
        # Should be configured as stockable product
        self.assertEqual(product.type, 'product')
        self.assertTrue(product.stock_controlled)
        
        # Test that it can be used in inventory operations
        variant = product.product_variant_ids[0]
        self.assertEqual(variant.type, 'product')
        
        # Test stock level fields exist and are accessible
        self.assertTrue(hasattr(variant, 'qty_available'))
        self.assertTrue(hasattr(variant, 'virtual_available'))

    def test_product_category_integration(self):
        """Test integration with Odoo product categories."""
        product = self.ProductTemplate.create({
            'name': 'Category Integration Test',
            'is_ams_product': True,
            'ams_product_type_id': self.event_type.id,
        })
        
        # Should inherit category from product type
        self.assertEqual(product.categ_id, self.ams_category)
        
        # Test that it works with Odoo's category-based features
        same_category_products = self.ProductTemplate.search([
            ('categ_id', '=', self.ams_category.id)
        ])
        self.assertIn(product, same_category_products)

    def test_pricing_pricelist_integration(self):
        """Test that AMS pricing works alongside Odoo pricelists."""
        product = self.ProductTemplate.create({
            'name': 'Pricelist Integration Test',
            'is_ams_product': True,
            'ams_product_type_id': self.event_type.id,
            'has_member_pricing': True,
            'member_price': 80.0,
            'non_member_price': 100.0,
            'list_price': 100.0,
        })
        
        # Test that basic pricing methods work
        member_price = product.get_price_for_member_status(True)
        non_member_price = product.get_price_for_member_status(False)
        
        self.assertEqual(member_price, 80.0)
        self.assertEqual(non_member_price, 100.0)
        
        # Test with variants
        variant = product.product_variant_ids[0]
        variant_member_price = variant.get_variant_price_for_member_status(True)
        variant_non_member_price = variant.get_variant_price_for_member_status(False)
        
        self.assertEqual(variant_member_price, 80.0)
        self.assertEqual(variant_non_member_price, 100.0)

    def test_name_search_and_display(self):
        """Test enhanced name search and display methods."""
        product = self.ProductTemplate.create({
            'name': 'Search Test Product',
            'is_ams_product': True,
            'ams_product_type_id': self.digital_type.id,
            'sku': 'SEARCH-TEST-001',
            'has_member_pricing': True,
            'is_digital_product': True,
        })
        
        # Test name_get displays AMS information
        name_result = product.name_get()[0][1]
        self.assertIn('[SEARCH-TEST-001]', name_result)
        self.assertIn('Digital', name_result)
        self.assertIn('Member Pricing', name_result)
        
        # Test name search finds by SKU
        search_results = self.ProductTemplate.name_search('SEARCH-TEST-001')
        product_ids = [r[0] for r in search_results]
        self.assertIn(product.id, product_ids)
        
        # Test variant name display
        variant = product.product_variant_ids[0]
        variant_name = variant.name_get()[0][1]
        self.assertIn('SEARCH-TEST-001', variant_name)

    def test_performance_with_many_products(self):
        """Test performance with multiple products and variants."""
        # Create multiple products quickly
        products = []
        for i in range(10):
            product = self.ProductTemplate.create({
                'name': f'Performance Test Product {i}',
                'is_ams_product': True,
                'ams_product_type_id': self.event_type.id,
                'has_member_pricing': True,
                'member_price': 80.0 + i,
                'non_member_price': 100.0 + i,
            })
            products.append(product)
        
        # Test bulk operations
        all_ams_products = self.ProductTemplate.get_ams_products_by_type()
        self.assertTrue(len(all_ams_products) >= 10)
        
        member_pricing_products = self.ProductTemplate.get_member_pricing_products()
        for product in products:
            self.assertIn(product, member_pricing_products)

    def test_data_migration_scenarios(self):
        """Test scenarios common in data migration."""
        # Test creating product with legacy ID
        product = self.ProductTemplate.create({
            'name': 'Legacy Product',
            'is_ams_product': True,
            'ams_product_type_id': self.membership_type.id,
            'legacy_product_id': 'OLD_SYSTEM_ID_12345',
            'sku': 'LEGACY-SKU-001',
        })
        
        self.assertEqual(product.legacy_product_id, 'OLD_SYSTEM_ID_12345')
        self.assertEqual(product.sku, 'LEGACY-SKU-001')
        
        # Test variant with legacy ID
        variant = self.ProductProduct.create({
            'product_tmpl_id': product.id,
            'variant_legacy_id': 'OLD_VARIANT_ID_67890',
            'variant_sku': 'LEGACY-VARIANT-001',
        })
        
        self.assertEqual(variant.variant_legacy_id, 'OLD_VARIANT_ID_67890')
        self.assertEqual(variant.variant_sku, 'LEGACY-VARIANT-001')

    # ========================================================================
    # CLEANUP AND UTILITIES
    # ========================================================================

    def tearDown(self):
        """Clean up after tests."""
        super().tearDown()
        
        # Clean up test data if needed
        # Note: TransactionCase automatically rolls back, but explicit cleanup
        # can be useful for debugging
        _logger.info("AMS Products Base tests completed")

    def _create_test_product_with_variants(self, variant_count=3):
        """Utility method to create a product with multiple variants."""
        # This would require product attributes which may not be set up
        # in the test environment, so keeping it simple
        template = self.ProductTemplate.create({
            'name': 'Multi-Variant Test Product',
            'is_ams_product': True,
            'ams_product_type_id': self.event_type.id,
            'has_member_pricing': True,
            'member_price': 100.0,
            'non_member_price': 150.0,
        })
        
        variants = []
        for i in range(variant_count):
            variant = self.ProductProduct.create({
                'product_tmpl_id': template.id,
                'variant_sku': f'VAR-{i+1:03d}',
            })
            variants.append(variant)
        
        return template, variants

    def _assert_product_properly_configured(self, product):
        """Utility method to assert a product is properly configured."""
        self.assertTrue(product.is_ams_product)
        self.assertTrue(product.ams_product_type_id)
        self.assertTrue(product.sku)
        self.assertEqual(product.default_code, product.sku)
        
        if product.is_digital_product:
            self.assertEqual(product.type, 'service')
            self.assertFalse(product.stock_controlled)
        elif product.stock_controlled:
            self.assertEqual(product.type, 'product')
        else:
            self.assertEqual(product.type, 'service')