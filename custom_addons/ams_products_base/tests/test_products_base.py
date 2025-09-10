# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestAMSProductsBase(TransactionCase):
    """Test cases for AMS Products Base functionality."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Get models
        self.product_template_model = self.env['product.template']
        self.product_product_model = self.env['product.product']
        self.product_type_model = self.env['ams.product.type']
        self.partner_model = self.env['res.partner']
        
        # Create test product type
        self.product_type = self.product_type_model.create({
            'name': 'Test Event Registration',
            'code': 'TEST_EVENT_REG',
            'category': 'event',
            'requires_member_pricing': True,
            'is_digital': False,
            'requires_inventory': False,
        })
        
        # Create test digital product type
        self.digital_product_type = self.product_type_model.create({
            'name': 'Test Digital Download',
            'code': 'TEST_DIGITAL',
            'category': 'digital',
            'requires_member_pricing': True,
            'is_digital': True,
            'requires_inventory': False,
        })
        
        # Create test partners
        self.member = self.partner_model.create({
            'name': 'Test Member',
            'email': 'member@test.com',
            'is_member': True,
            'membership_status': 'active',
        })
        
        self.non_member = self.partner_model.create({
            'name': 'Test Non-Member',
            'email': 'nonmember@test.com',
            'is_member': False,
            'membership_status': 'prospect',
        })

    def test_ams_product_creation(self):
        """Test basic AMS product creation."""
        product = self.product_template_model.create({
            'name': 'Test Conference Registration',
            'is_ams_product': True,
            'ams_product_type_id': self.product_type.id,
            'has_member_pricing': True,
            'member_price': 200.0,
            'non_member_price': 300.0,
        })
        
        self.assertTrue(product.is_ams_product)
        self.assertEqual(product.ams_product_type_id, self.product_type)
        self.assertTrue(product.has_member_pricing)
        self.assertEqual(product.member_price, 200.0)
        self.assertEqual(product.non_member_price, 300.0)
        self.assertTrue(product.sku)  # Should auto-generate

    def test_member_pricing_calculation(self):
        """Test member pricing and discount calculations."""
        product = self.product_template_model.create({
            'name': 'Test Pricing Product',
            'is_ams_product': True,
            'has_member_pricing': True,
            'member_price': 80.0,
            'non_member_price': 100.0,
        })
        
        # Test discount calculation
        self.assertEqual(product.member_discount_percentage, 20.0)
        
        # Test effective pricing
        self.assertEqual(product.effective_member_price, 80.0)
        self.assertEqual(product.effective_non_member_price, 100.0)
        
        # Test pricing summary
        self.assertIn('Members:', product.pricing_summary)
        self.assertIn('Non-members:', product.pricing_summary)

    def test_digital_product_features(self):
        """Test digital product functionality."""
        attachment = self.env['ir.attachment'].create({
            'name': 'test_file.pdf',
            'datas': b'test content',
            'mimetype': 'application/pdf',
        })
        
        product = self.product_template_model.create({
            'name': 'Test Digital Product',
            'is_ams_product': True,
            'ams_product_type_id': self.digital_product_type.id,
            'is_digital_product': True,
            'digital_download_url': 'https://example.com/download',
            'digital_attachment_id': attachment.id,
            'auto_fulfill_digital': True,
        })
        
        self.assertTrue(product.is_digital_product)
        self.assertTrue(product.is_digital_available)
        self.assertTrue(product.auto_fulfill_digital)
        self.assertEqual(product.digital_download_url, 'https://example.com/download')
        self.assertEqual(product.digital_attachment_id, attachment)

    def test_sku_generation(self):
        """Test SKU auto-generation."""
        product = self.product_template_model.create({
            'name': 'Test Product for SKU',
            'is_ams_product': True,
        })
        
        # Should auto-generate SKU from name
        self.assertTrue(product.sku)
        self.assertIn('TEST-PRODUCT-FOR-SKU', product.sku.upper())

    def test_product_type_integration(self):
        """Test integration with AMS product types."""
        product = self.product_template_model.new({
            'name': 'Test Integration Product',
            'is_ams_product': True,
            'ams_product_type_id': self.digital_product_type.id,
        })
        
        # Trigger onchange
        product._onchange_ams_product_type()
        
        # Should inherit settings from product type
        self.assertTrue(product.is_digital_product)
        self.assertTrue(product.has_member_pricing)
        self.assertFalse(product.stock_controlled)
        self.assertEqual(product.type, 'service')

    def test_member_access_control(self):
        """Test member access control methods."""
        product = self.product_template_model.create({
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
        
        # Test pricing by member status
        self.assertEqual(product.get_price_for_member_status(True), 50.0)
        self.assertEqual(product.get_price_for_member_status(False), 75.0)
        
        # Test member savings
        self.assertEqual(product.get_member_savings(), 25.0)

    def test_digital_content_access(self):
        """Test digital content access methods."""
        product = self.product_template_model.create({
            'name': 'Digital Test Product',
            'is_ams_product': True,
            'is_digital_product': True,
            'digital_download_url': 'https://example.com/test',
            'auto_fulfill_digital': True,
        })
        
        access_info = product.get_digital_content_access()
        
        self.assertTrue(access_info['is_digital'])
        self.assertEqual(access_info['download_url'], 'https://example.com/test')
        self.assertTrue(access_info['auto_fulfill'])
        self.assertTrue(access_info['is_available'])

    def test_validation_constraints(self):
        """Test validation and constraints."""
        # Test invalid SKU format
        with self.assertRaises(ValidationError):
            self.product_template_model.create({
                'name': 'Invalid SKU Product',
                'is_ams_product': True,
                'sku': 'INVALID@SKU!',
            })
        
        # Test invalid digital URL
        with self.assertRaises(ValidationError):
            self.product_template_model.create({
                'name': 'Invalid URL Product',
                'is_ams_product': True,
                'is_digital_product': True,
                'digital_download_url': 'not-a-url',
            })
        
        # Test member pricing logic
        with self.assertRaises(ValidationError):
            self.product_template_model.create({
                'name': 'Invalid Pricing Product',
                'is_ams_product': True,
                'has_member_pricing': True,
                'member_price': 100.0,
                'non_member_price': 50.0,  # Member price higher than non-member
            })

    def test_product_variant_creation(self):
        """Test product variant creation with AMS features."""
        # Create template with variants
        template = self.product_template_model.create({
            'name': 'Test Variant Template',
            'is_ams_product': True,
            'has_member_pricing': True,
            'member_price': 100.0,
            'non_member_price': 150.0,
            'sku': 'TEST-TEMPLATE',
        })
        
        # Create variant manually
        variant = self.product_product_model.create({
            'product_tmpl_id': template.id,
            'variant_sku': 'TEST-VARIANT-001',
        })
        
        self.assertEqual(variant.effective_sku, 'TEST-VARIANT-001')
        self.assertEqual(variant.final_member_price, 100.0)
        self.assertEqual(variant.final_non_member_price, 150.0)
        self.assertFalse(variant.has_variant_pricing)

    def test_variant_pricing_override(self):
        """Test variant-specific pricing."""
        template = self.product_template_model.create({
            'name': 'Test Variant Pricing Template',
            'is_ams_product': True,
            'has_member_pricing': True,
            'member_price': 100.0,
            'non_member_price': 150.0,
        })
        
        variant = self.product_product_model.create({
            'product_tmpl_id': template.id,
            'has_variant_pricing': True,
            'variant_member_price': 80.0,
            'variant_non_member_price': 120.0,
        })
        
        # Should use variant pricing
        self.assertEqual(variant.final_member_price, 80.0)
        self.assertEqual(variant.final_non_member_price, 120.0)
        self.assertEqual(variant.variant_member_discount, 33.33)  # Approximately

    def test_variant_digital_content(self):
        """Test variant-specific digital content."""
        template = self.product_template_model.create({
            'name': 'Test Variant Digital Template',
            'is_ams_product': True,
            'is_digital_product': True,
            'digital_download_url': 'https://example.com/template',
        })
        
        variant = self.product_product_model.create({
            'product_tmpl_id': template.id,
            'has_variant_digital_content': True,
            'variant_digital_url': 'https://example.com/variant',
        })
        
        # Should use variant digital content
        self.assertEqual(variant.final_digital_url, 'https://example.com/variant')
        self.assertTrue(variant.is_digital_content_available)
        
        access_info = variant.get_variant_digital_content_access()
        self.assertEqual(access_info['download_url'], 'https://example.com/variant')
        self.assertTrue(access_info['has_variant_content'])

    def test_business_methods(self):
        """Test business methods and queries."""
        # Create test products
        member_pricing_product = self.product_template_model.create({
            'name': 'Member Pricing Product',
            'is_ams_product': True,
            'has_member_pricing': True,
            'member_price': 50.0,
            'non_member_price': 75.0,
        })
        
        digital_product = self.product_template_model.create({
            'name': 'Digital Product',
            'is_ams_product': True,
            'is_digital_product': True,
            'digital_download_url': 'https://example.com/digital',
        })
        
        membership_required_product = self.product_template_model.create({
            'name': 'Members Only Product',
            'is_ams_product': True,
            'requires_membership': True,
        })
        
        # Test query methods
        ams_products = self.product_template_model.get_ams_products_by_type()
        self.assertIn(member_pricing_product, ams_products)
        self.assertIn(digital_product, ams_products)
        self.assertIn(membership_required_product, ams_products)
        
        member_pricing_products = self.product_template_model.get_member_pricing_products()
        self.assertIn(member_pricing_product, member_pricing_products)
        self.assertNotIn(digital_product, member_pricing_products)
        
        digital_products = self.product_template_model.get_digital_products()
        self.assertIn(digital_product, digital_products)
        self.assertNotIn(member_pricing_product, digital_products)
        
        membership_products = self.product_template_model.get_membership_required_products()
        self.assertIn(membership_required_product, membership_products)
        self.assertNotIn(member_pricing_product, membership_products)

    def test_pricing_context_generation(self):
        """Test pricing context generation for partners."""
        product = self.product_template_model.create({
            'name': 'Context Test Product',
            'is_ams_product': True,
            'has_member_pricing': True,
            'requires_membership': True,
            'member_price': 100.0,
            'non_member_price': 150.0,
        })
        
        # Test member context
        member_context = product._get_pricing_context(self.member.id)
        self.assertTrue(member_context['is_member'])
        self.assertTrue(member_context['can_purchase'])
        self.assertEqual(member_context['effective_price'], 100.0)
        self.assertEqual(member_context['member_savings'], 50.0)
        
        # Test non-member context
        non_member_context = product._get_pricing_context(self.non_member.id)
        self.assertFalse(non_member_context['is_member'])
        self.assertFalse(non_member_context['can_purchase'])  # Requires membership
        self.assertEqual(non_member_context['effective_price'], 150.0)
        self.assertEqual(non_member_context['member_savings'], 0.0)

    def test_variant_business_methods(self):
        """Test variant-specific business methods."""
        template = self.product_template_model.create({
            'name': 'Variant Business Test',
            'is_ams_product': True,
            'has_member_pricing': True,
            'member_price': 100.0,
            'non_member_price': 150.0,
        })
        
        variant = self.product_product_model.create({
            'product_tmpl_id': template.id,
            'has_variant_pricing': True,
            'variant_member_price': 80.0,
            'variant_non_member_price': 120.0,
        })
        
        # Test variant pricing methods
        self.assertEqual(variant.get_variant_price_for_member_status(True), 80.0)
        self.assertEqual(variant.get_variant_price_for_member_status(False), 120.0)
        self.assertEqual(variant.get_variant_member_savings(), 40.0)
        
        # Test variant context
        context = variant._get_variant_pricing_context(self.member.id)
        self.assertTrue(context['has_variant_pricing'])
        self.assertEqual(context['effective_price'], 80.0)

    def test_sku_uniqueness(self):
        """Test SKU uniqueness constraints."""
        # Create first product with SKU
        product1 = self.product_template_model.create({
            'name': 'First Product',
            'is_ams_product': True,
            'sku': 'UNIQUE-SKU-001',
        })
        
        # Try to create second product with same SKU
        with self.assertRaises(Exception):  # Should raise IntegrityError
            self.product_template_model.create({
                'name': 'Second Product',
                'is_ams_product': True,
                'sku': 'UNIQUE-SKU-001',
            })

    def test_variant_sku_generation(self):
        """Test variant SKU generation."""
        template = self.product_template_model.create({
            'name': 'SKU Generation Template',
            'is_ams_product': True,
            'sku': 'BASE-SKU',
        })
        
        # Create variant without specifying SKU
        variant = self.product_product_model.create({
            'product_tmpl_id': template.id,
        })
        
        # Should generate effective SKU
        self.assertTrue(variant.effective_sku)
        self.assertIn('BASE-SKU', variant.effective_sku)

    def test_copy_and_name_methods(self):
        """Test copy behavior and name methods."""
        product = self.product_template_model.create({
            'name': 'Original Product',
            'is_ams_product': True,
            'sku': 'ORIGINAL-SKU',
            'has_member_pricing': True,
            'is_digital_product': True,
        })
        
        # Test name_get
        name_result = product.name_get()[0][1]
        self.assertIn('[ORIGINAL-SKU]', name_result)
        self.assertIn('(Digital)', name_result)
        self.assertIn('(Member Pricing)', name_result)

    def test_onchange_methods(self):
        """Test onchange method behavior."""
        product = self.product_template_model.new({
            'name': 'Onchange Test Product',
            'is_ams_product': True,
        })
        
        # Test member pricing onchange
        product.has_member_pricing = True
        product.list_price = 100.0
        product._onchange_has_member_pricing()
        self.assertEqual(product.non_member_price, 100.0)
        
        # Test digital product onchange
        product.is_digital_product = True
        product._onchange_is_digital_product()
        self.assertFalse(product.stock_controlled)
        self.assertEqual(product.type, 'service')
        self.assertTrue(product.auto_fulfill_digital)

    def test_variant_sync_methods(self):
        """Test variant pricing sync methods."""
        template = self.product_template_model.create({
            'name': 'Sync Test Template',
            'is_ams_product': True,
            'has_member_pricing': True,
            'member_price': 100.0,
            'non_member_price': 150.0,
        })
        
        variant = self.product_product_model.create({
            'product_tmpl_id': template.id,
            'has_variant_pricing': True,
            'variant_member_price': 80.0,
            'variant_non_member_price': 120.0,
        })
        
        # Test sync with template
        variant.sync_with_template_pricing()
        self.assertFalse(variant.has_variant_pricing)
        self.assertEqual(variant.variant_member_price, 0.0)
        
        # Test copy template pricing to variant
        variant.copy_template_pricing_to_variant()
        self.assertTrue(variant.has_variant_pricing)
        self.assertEqual(variant.variant_member_price, 100.0)
        self.assertEqual(variant.variant_non_member_price, 150.0)

    def test_filtering_by_criteria(self):
        """Test filtering variants by AMS criteria."""
        # Create template and variants with different characteristics
        digital_template = self.product_template_model.create({
            'name': 'Digital Template',
            'is_ams_product': True,
            'is_digital_product': True,
            'has_member_pricing': True,
        })
        
        physical_template = self.product_template_model.create({
            'name': 'Physical Template',
            'is_ams_product': True,
            'is_digital_product': False,
            'requires_membership': True,
        })
        
        digital_variant = self.product_product_model.create({
            'product_tmpl_id': digital_template.id,
        })
        
        physical_variant = self.product_product_model.create({
            'product_tmpl_id': physical_template.id,
        })
        
        # Test filtering
        digital_variants = self.product_product_model.get_variants_by_ams_criteria(is_digital=True)
        self.assertIn(digital_variant, digital_variants)
        self.assertNotIn(physical_variant, digital_variants)
        
        member_pricing_variants = self.product_product_model.get_variants_by_ams_criteria(has_member_pricing=True)
        self.assertIn(digital_variant, member_pricing_variants)
        self.assertNotIn(physical_variant, member_pricing_variants)
        
        membership_required_variants = self.product_product_model.get_variants_by_ams_criteria(requires_membership=True)
        self.assertIn(physical_variant, membership_required_variants)
        self.assertNotIn(digital_variant, membership_required_variants)

    def tearDown(self):
        """Clean up after tests."""
        super().tearDown()