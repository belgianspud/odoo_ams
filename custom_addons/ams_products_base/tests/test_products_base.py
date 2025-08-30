"""Test cases for AMS Products Base functionality."""

from odoo.tests import common
from odoo.exceptions import ValidationError, UserError


class TestAMSProductsBase(common.TransactionCase):
    """Test AMS Products Base module functionality."""

    def setUp(self):
        super().setUp()
        self.AMSProduct = self.env['ams.product.standard']
        self.Product = self.env['product.product']
        self.MemberType = self.env['ams.member.type']
        self.Partner = self.env['res.partner']
        
        # Create test member type
        self.individual_type = self.MemberType.create({
            'name': 'Test Individual',
            'code': 'TEST_IND',
            'is_individual': True,
            'is_organization': False,
        })
        
        # Create test product
        self.base_product = self.Product.create({
            'name': 'Test Product',
            'type': 'consu',
            'list_price': 50.00,
            'default_code': 'TEST-001',
        })
        
        # Create test partner
        self.test_partner = self.Partner.create({
            'name': 'Test Member',
            'is_company': False,
            'member_type_id': self.individual_type.id,
        })

    def test_create_ams_product(self):
        """Test creating an AMS product standard."""
        ams_product = self.AMSProduct.create({
            'product_id': self.base_product.id,
            'ams_product_type': 'merchandise',
            'sku': 'AMS-TEST-001',
            'member_price': 40.00,
            'non_member_price': 50.00,
        })
        
        self.assertTrue(ams_product.id)
        self.assertEqual(ams_product.name, 'Test Product')
        self.assertEqual(ams_product.ams_product_type, 'merchandise')
        self.assertEqual(ams_product.member_price, 40.00)
        self.assertEqual(ams_product.non_member_price, 50.00)

    def test_member_discount_calculation(self):
        """Test automatic member discount percentage calculation."""
        ams_product = self.AMSProduct.create({
            'product_id': self.base_product.id,
            'ams_product_type': 'merchandise',
            'member_price': 30.00,
            'non_member_price': 50.00,
        })
        
        # Trigger computation
        ams_product._compute_member_discount()
        
        # Should be 40% discount (20/50 * 100)
        self.assertEqual(ams_product.member_discount_percentage, 40.0)

    def test_pricing_validation(self):
        """Test pricing validation constraints."""
        # Member price higher than non-member price should fail
        with self.assertRaises(ValidationError):
            self.AMSProduct.create({
                'product_id': self.base_product.id,
                'ams_product_type': 'merchandise',
                'member_price': 60.00,
                'non_member_price': 50.00,
            })

    def test_digital_product_validation(self):
        """Test digital product validation."""
        # Digital product without URL or attachment should fail
        with self.assertRaises(ValidationError):
            ams_product = self.AMSProduct.create({
                'product_id': self.base_product.id,
                'ams_product_type': 'digital_download',
                'digital_delivery_enabled': True,
            })
            ams_product._check_digital_settings()

        # Digital product with URL should pass
        ams_product = self.AMSProduct.create({
            'product_id': self.base_product.id,
            'ams_product_type': 'digital_download',
            'digital_delivery_enabled': True,
            'digital_download_url': 'https://example.com/download',
        })
        ams_product._check_digital_settings()  # Should not raise

    def test_seasonal_date_validation(self):
        """Test seasonal product date validation."""
        with self.assertRaises(ValidationError):
            ams_product = self.AMSProduct.create({
                'product_id': self.base_product.id,
                'ams_product_type': 'event_material',
                'seasonal_product': True,
                'season_start_date': '2024-06-01',
                'season_end_date': '2024-05-01',  # End before start
            })
            ams_product._check_seasonal_dates()

    def test_product_eligibility_check(self):
        """Test product eligibility checking."""
        # Create member-only product
        ams_product = self.AMSProduct.create({
            'product_id': self.base_product.id,
            'ams_product_type': 'certification_package',
            'requires_membership': True,
        })
        
        # Non-member should be ineligible
        non_member = self.Partner.create({
            'name': 'Non Member',
            'is_company': False,
        })
        
        eligibility = ams_product.check_product_eligibility(non_member.id)
        self.assertFalse(eligibility['eligible'])
        self.assertIn('membership', eligibility['reason'])

    def test_customer_price_calculation(self):
        """Test customer price calculation."""
        ams_product = self.AMSProduct.create({
            'product_id': self.base_product.id,
            'ams_product_type': 'merchandise',
            'member_price': 40.00,
            'non_member_price': 50.00,
        })
        
        # Set up member with is_member=True
        self.test_partner.write({'is_member': True})
        
        price_info = ams_product.get_customer_price(self.test_partner.id)
        
        self.assertEqual(price_info['unit_price'], 40.00)
        self.assertEqual(price_info['price_type'], 'member')
        self.assertEqual(price_info['total_price'], 40.00)

    def test_stock_availability_check(self):
        """Test stock availability checking."""
        # Stock controlled product
        ams_product = self.AMSProduct.create({
            'product_id': self.base_product.id,
            'ams_product_type': 'merchandise',
            'stock_controlled': True,
        })
        
        availability = ams_product.check_stock_availability(5)
        # Should return availability info (exact values depend on stock setup)
        self.assertIn('available', availability)
        self.assertIn('quantity', availability)
        
        # Non-stock controlled product
        ams_product_service = self.AMSProduct.create({
            'product_id': self.base_product.id,
            'ams_product_type': 'digital_download',
            'stock_controlled': False,
        })
        
        availability = ams_product_service.check_stock_availability(100)
        self.assertTrue(availability['available'])

    def test_digital_access_token_generation(self):
        """Test digital access token generation."""
        ams_product = self.AMSProduct.create({
            'product_id': self.base_product.id,
            'ams_product_type': 'digital_download',
            'digital_delivery_enabled': True,
            'digital_download_url': 'https://example.com/download',
        })
        
        token = ams_product.generate_digital_access_token()
        self.assertTrue(token)
        self.assertTrue(len(token) > 20)  # Should be a decent length

    def test_sku_auto_generation(self):
        """Test automatic SKU generation."""
        ams_product = self.AMSProduct.create({
            'product_id': self.base_product.id,
            'ams_product_type': 'merchandise',
            # No SKU provided
        })
        
        # Should auto-generate SKU
        self.assertTrue(ams_product.sku)
        self.assertTrue(ams_product.sku.startswith('AMS-'))

    def test_name_get_display(self):
        """Test custom name_get display."""
        ams_product = self.AMSProduct.create({
            'product_id': self.base_product.id,
            'ams_product_type': 'publication',
        })
        
        name_display = ams_product.name_get()
        self.assertIn('Publication', name_display[0][1])
        self.assertIn('Test Product', name_display[0][1])

    def test_name_search(self):
        """Test enhanced name search."""
        ams_product = self.AMSProduct.create({
            'product_id': self.base_product.id,
            'ams_product_type': 'merchandise',
            'sku': 'SEARCH-TEST-123',
            'product_code': 'PCODE-456',
        })
        
        # Search by SKU
        results = self.AMSProduct._name_search('SEARCH-TEST')
        self.assertIn(ams_product.id, results)
        
        # Search by product code
        results = self.AMSProduct._name_search('PCODE')
        self.assertIn(ams_product.id, results)


class TestProductProductExtensions(common.TransactionCase):
    """Test product.product extensions."""

    def setUp(self):
        super().setUp()
        self.Product = self.env['product.product']
        self.AMSProduct = self.env['ams.product.standard']
        
        # Create base product
        self.product = self.Product.create({
            'name': 'Extension Test Product',
            'type': 'consu',
            'list_price': 100.00,
        })

    def test_ams_product_computation(self):
        """Test AMS product relationship computation."""
        # Initially should not be AMS product
        self.assertFalse(self.product.is_ams_product)
        self.assertFalse(self.product.ams_product_id)
        
        # Create AMS extension
        ams_product = self.AMSProduct.create({
            'product_id': self.product.id,
            'ams_product_type': 'merchandise',
            'member_price': 80.00,
            'non_member_price': 100.00,
        })
        
        # Trigger recomputation
        self.product._compute_ams_product()
        
        # Should now be AMS product
        self.assertTrue(self.product.is_ams_product)
        self.assertEqual(self.product.ams_product_id, ams_product)

    def test_member_pricing_computation(self):
        """Test member pricing computation."""
        # Create AMS extension with member pricing
        ams_product = self.AMSProduct.create({
            'product_id': self.product.id,
            'ams_product_type': 'merchandise',
            'member_price': 75.00,
            'non_member_price': 100.00,
        })
        
        # Trigger recomputation
        self.product._compute_ams_product()
        self.product._compute_has_member_pricing()
        
        # Should have member pricing
        self.assertTrue(self.product.has_member_pricing)
        self.assertEqual(self.product.member_price, 75.00)
        self.assertEqual(self.product.non_member_price, 100.00)

    def test_create_ams_extension(self):
        """Test creating AMS extension from product."""
        self.assertFalse(self.product.is_ams_product)
        
        # Create extension
        ams_product = self.product.create_ams_extension({
            'ams_product_type': 'publication',
            'member_price': 50.00,
            'non_member_price': 75.00,
        })
        
        self.assertTrue(ams_product)
        self.assertTrue(self.product.is_ams_product)
        self.assertEqual(ams_product.ams_product_type, 'publication')

    def test_create_duplicate_extension_fails(self):
        """Test that creating duplicate extension fails."""
        # Create first extension
        self.product.create_ams_extension({'ams_product_type': 'merchandise'})
        
        # Try to create second extension should fail
        with self.assertRaises(UserError):
            self.product.create_ams_extension({'ams_product_type': 'publication'})

    def test_remove_ams_extension(self):
        """Test removing AMS extension."""
        # Create extension
        self.product.create_ams_extension({'ams_product_type': 'merchandise'})
        self.assertTrue(self.product.is_ams_product)
        
        # Remove extension
        self.product.remove_ams_extension()
        self.assertFalse(self.product.is_ams_product)

    def test_ams_price_for_partner(self):
        """Test getting AMS price for partner."""
        # Create member
        partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'is_member': True,
        })
        
        # Product without AMS extension
        price_info = self.product.get_ams_price_for_partner(partner.id)
        self.assertEqual(price_info['price_type'], 'standard')
        self.assertEqual(price_info['unit_price'], 100.00)
        
        # Add AMS extension
        self.product.create_ams_extension({
            'ams_product_type': 'merchandise',
            'member_price': 80.00,
            'non_member_price': 100.00,
        })
        
        price_info = self.product.get_ams_price_for_partner(partner.id)
        self.assertEqual(price_info['price_type'], 'member')
        self.assertEqual(price_info['unit_price'], 80.00)

    def test_ams_eligibility_check(self):
        """Test AMS eligibility checking."""
        partner = self.env['res.partner'].create({
            'name': 'Test Customer',
        })
        
        # Product without AMS extension
        eligibility = self.product.check_ams_eligibility(partner.id)
        self.assertTrue(eligibility['eligible'])
        
        # Add AMS extension with membership requirement
        self.product.create_ams_extension({
            'ams_product_type': 'certification_package',
            'requires_membership': True,
        })
        
        eligibility = self.product.check_ams_eligibility(partner.id)
        self.assertFalse(eligibility['eligible'])  # Not a member

    def test_product_unlink_cleanup(self):
        """Test that AMS extensions are cleaned up when product is deleted."""
        # Create AMS extension
        ams_product = self.AMSProduct.create({
            'product_id': self.product.id,
            'ams_product_type': 'merchandise',
        })
        
        ams_product_id = ams_product.id
        
        # Delete product
        self.product.unlink()
        
        # AMS product should also be deleted
        self.assertFalse(self.AMSProduct.browse(ams_product_id).exists())

    def test_get_ams_product_summary(self):
        """Test getting AMS product summary."""
        # Without AMS extension
        summary = self.product.get_ams_product_summary()
        self.assertFalse(summary['has_ams_extension'])
        
        # With AMS extension
        self.product.create_ams_extension({
            'ams_product_type': 'digital_download',
            'member_price': 25.00,
            'non_member_price': 50.00,
            'digital_delivery_enabled': True,
            'requires_membership': True,
        })
        
        summary = self.product.get_ams_product_summary()
        self.assertTrue(summary['has_ams_extension'])
        self.assertEqual(summary['ams_product_type'], 'digital_download')
        self.assertTrue(summary['has_member_pricing'])
        self.assertTrue(summary['is_digital'])
        self.assertTrue(summary['requires_membership'])


class TestAMSProductUtilities(common.TransactionCase):
    """Test AMS product utility methods."""

    def setUp(self):
        super().setUp()
        self.Product = self.env['product.product']
        self.AMSProduct = self.env['ams.product.standard']
        
        # Create test products
        self.merchandise_product = self.Product.create({
            'name': 'Test Merchandise',
            'type': 'consu',
        })
        
        self.digital_product = self.Product.create({
            'name': 'Test Digital',
            'type': 'service',
        })
        
        # Create AMS extensions
        self.AMSProduct.create({
            'product_id': self.merchandise_product.id,
            'ams_product_type': 'merchandise',
            'member_price': 20.00,
            'non_member_price': 25.00,
        })
        
        self.AMSProduct.create({
            'product_id': self.digital_product.id,
            'ams_product_type': 'digital_download',
            'digital_delivery_enabled': True,
            'digital_download_url': 'https://example.com/download',
        })

    def test_get_ams_products_by_type(self):
        """Test getting products by AMS type."""
        merchandise_products = self.Product.get_ams_products_by_type('merchandise')
        self.assertIn(self.merchandise_product, merchandise_products)
        self.assertNotIn(self.digital_product, merchandise_products)
        
        digital_products = self.Product.get_ams_products_by_type('digital_download')
        self.assertIn(self.digital_product, digital_products)
        self.assertNotIn(self.merchandise_product, digital_products)

    def test_get_member_priced_products(self):
        """Test getting products with member pricing."""
        member_priced = self.Product.get_member_priced_products()
        self.assertIn(self.merchandise_product, member_priced)
        # Digital product doesn't have member pricing set up
        self.assertNotIn(self.digital_product, member_priced)

    def test_get_digital_products(self):
        """Test getting digital products."""
        digital_products = self.Product.get_digital_products()
        self.assertIn(self.digital_product, digital_products)
        self.assertNotIn(self.merchandise_product, digital_products)

    def test_enhanced_search(self):
        """Test enhanced search functionality."""
        # This tests the custom _search method indirectly
        results = self.Product.search([('ams_product_type', '=', 'merchandise')])
        self.assertIn(self.merchandise_product, results)
        self.assertNotIn(self.digital_product, results)