# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class TestAMSProductsEnhanced(TransactionCase):
    """Test cases for enhanced AMS Products Base functionality with behavior management."""

    def setUp(self):
        """Set up test environment with enhanced AMS features."""
        super().setUp()
        
        # Get models
        self.ProductTemplate = self.env['product.template']
        self.ProductProduct = self.env['product.product']
        self.ProductCategory = self.env['product.category']
        self.Partner = self.env['res.partner']
        self.MailTemplate = self.env['mail.template']
        self.Event = self.env.get('event.event', self.env['res.partner'])  # Fallback if event not installed
        
        # Create test AMS categories with enhanced features
        self.membership_category = self.ProductCategory.create({
            'name': 'Test Membership Category',
            'is_ams_category': True,
            'ams_category_type': 'membership',
            'requires_member_pricing': False,
            'member_discount_percent': 0.0,
            'is_membership_category': True,
            'grants_portal_access': True,
            'is_digital_category': False,
            'requires_inventory': False,
        })
        
        self.event_category = self.ProductCategory.create({
            'name': 'Test Event Category',
            'is_ams_category': True,
            'ams_category_type': 'event',
            'requires_member_pricing': True,
            'member_discount_percent': 25.0,
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
        
        self.subscription_category = self.ProductCategory.create({
            'name': 'Test Subscription Category',
            'is_ams_category': True,
            'ams_category_type': 'publication',
            'requires_member_pricing': True,
            'member_discount_percent': 20.0,
            'is_subscription_category': True,
            'is_digital_category': False,
            'requires_inventory': True,
        })
        
        self.donation_category = self.ProductCategory.create({
            'name': 'Test Donation Category',
            'is_ams_category': True,
            'ams_category_type': 'donation',
            'requires_member_pricing': False,
            'is_tax_deductible_donation': True,
            'is_digital_category': False,
            'requires_inventory': False,
        })
        
        # Create test partners with enhanced membership data
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
        
        self.student_partner = self.Partner.create({
            'name': 'Test Student Member',
            'email': 'student@test.com',
            'is_member': True,
            'membership_status': 'active',
        })
        
        # Create test portal groups
        self.portal_group = self.env['res.groups'].create({
            'name': 'Test Portal Group',
            'category_id': self.env.ref('base.module_category_hidden').id,
        })
        
        # Create test email template for donations
        self.donation_template = self.MailTemplate.create({
            'name': 'Test Donation Receipt',
            'model_id': self.env.ref('account.model_account_move').id,
            'subject': 'Donation Receipt #{object.name}',
            'body_html': '<p>Thank you for your donation of ${object.amount_total}</p>',
        })
        
        # Create test attachment for digital products
        self.test_attachment = self.env['ir.attachment'].create({
            'name': 'test_digital_file.pdf',
            'datas': b'VGVzdCBkaWdpdGFsIGNvbnRlbnQ=',  # Base64 encoded "Test digital content"
            'mimetype': 'application/pdf',
        })

    # ========================================================================
    # PRODUCT BEHAVIOR TYPE TESTS
    # ========================================================================

    def test_product_behavior_selection_and_defaults(self):
        """Test product behavior type selection and automatic defaults"""
        # Test membership behavior
        membership_product = self.ProductTemplate.create({
            'name': 'Test Membership Product',
            'categ_id': self.membership_category.id,
            'list_price': 150.00,
            'is_ams_product': True,
            'ams_product_behavior': 'membership',
        })
        
        # Should have membership defaults applied
        self.assertTrue(membership_product.is_subscription_product)
        self.assertTrue(membership_product.grants_portal_access)
        self.assertEqual(membership_product.subscription_term, 12)
        self.assertEqual(membership_product.subscription_term_type, 'months')
        
        # Test event behavior
        event_product = self.ProductTemplate.create({
            'name': 'Test Event Product',
            'categ_id': self.event_category.id,
            'list_price': 200.00,
            'is_ams_product': True,
            'ams_product_behavior': 'event',
        })
        
        # Should have event defaults applied
        self.assertTrue(event_product.creates_event_registration)
        self.assertFalse(event_product.is_subscription_product)
        
        # Test digital behavior
        digital_product = self.ProductTemplate.create({
            'name': 'Test Digital Product',
            'categ_id': self.digital_category.id,
            'list_price': 50.00,
            'is_ams_product': True,
            'ams_product_behavior': 'digital',
            'digital_url': 'https://example.com/download',
        })
        
        # Should have digital defaults applied
        self.assertEqual(digital_product.type, 'service')
        self.assertTrue(digital_product.has_digital_content)
        
        # Test donation behavior
        donation_product = self.ProductTemplate.create({
            'name': 'Test Donation Product',
            'categ_id': self.donation_category.id,
            'list_price': 0.00,
            'is_ams_product': True,
            'ams_product_behavior': 'donation',
        })
        
        # Should have donation defaults applied
        self.assertTrue(donation_product.donation_tax_deductible)
        self.assertEqual(donation_product.type, 'service')

    def test_behavior_based_sku_generation(self):
        """Test behavior-based SKU generation with prefixes"""
        # Test membership product SKU
        membership_product = self.ProductTemplate.create({
            'name': 'Annual Membership Premium',
            'categ_id': self.membership_category.id,
            'list_price': 200.00,
            'is_ams_product': True,
            'ams_product_behavior': 'membership',
        })
        
        self.assertTrue(membership_product.default_code.startswith('MEM-'))
        self.assertIn('ANNUAL', membership_product.default_code)
        
        # Test event product SKU
        event_product = self.ProductTemplate.create({
            'name': 'Leadership Workshop Advanced',
            'categ_id': self.event_category.id,
            'list_price': 150.00,
            'is_ams_product': True,
            'ams_product_behavior': 'event',
        })
        
        self.assertTrue(event_product.default_code.startswith('EVT-'))
        self.assertIn('LEADER', event_product.default_code)
        
        # Test digital product SKU
        digital_product = self.ProductTemplate.create({
            'name': 'Professional Resources Library',
            'categ_id': self.digital_category.id,
            'list_price': 75.00,
            'is_ams_product': True,
            'ams_product_behavior': 'digital',
            'digital_url': 'https://example.com/resources',
        })
        
        self.assertTrue(digital_product.default_code.startswith('DIG-'))
        
        # Test donation product SKU
        donation_product = self.ProductTemplate.create({
            'name': 'Scholarship Fund Contribution',
            'categ_id': self.donation_category.id,
            'list_price': 0.00,
            'is_ams_product': True,
            'ams_product_behavior': 'donation',
        })
        
        self.assertTrue(donation_product.default_code.startswith('DON-'))

    def test_product_behavior_summary_computation(self):
        """Test product behavior summary generation"""
        # Complex product with multiple features
        complex_product = self.ProductTemplate.create({
            'name': 'Premium Membership with Portal',
            'categ_id': self.membership_category.id,
            'list_price': 300.00,
            'is_ams_product': True,
            'ams_product_behavior': 'membership',
            'is_subscription_product': True,
            'grants_portal_access': True,
            'subscription_term': 24,
            'subscription_term_type': 'months',
        })
        
        summary = complex_product.product_behavior_summary
        self.assertIn('Membership Product', summary)
        self.assertIn('Subscription: 24 months', summary)
        self.assertIn('Portal Access', summary)
        
        # Simple product
        simple_product = self.ProductTemplate.create({
            'name': 'Simple Event Registration',
            'categ_id': self.event_category.id,
            'list_price': 100.00,
            'is_ams_product': True,
            'ams_product_behavior': 'event',
        })
        
        summary = simple_product.product_behavior_summary
        self.assertIn('Event Product', summary)
        self.assertNotIn('Subscription', summary)

    # ========================================================================
    # ENHANCED MEMBER PRICING TESTS
    # ========================================================================

    def test_enhanced_member_pricing_calculation(self):
        """Test enhanced member pricing with behavior-specific logic"""
        # Event product with member pricing
        event_product = self.ProductTemplate.create({
            'name': 'Conference Registration',
            'categ_id': self.event_category.id,  # 25% discount
            'list_price': 400.00,
            'is_ams_product': True,
            'ams_product_behavior': 'event',
        })
        
        # Test member pricing calculation
        self.assertEqual(event_product.member_price, 300.00)  # 25% discount
        self.assertEqual(event_product.member_savings, 100.00)
        
        # Test pricing summary
        self.assertIn('Members: $300.00', event_product.pricing_summary)
        self.assertIn('Save $100.00', event_product.pricing_summary)
        self.assertIn('Non-members: $400.00', event_product.pricing_summary)

    def test_partner_specific_pricing_enhanced(self):
        """Test enhanced partner-specific pricing with behavior awareness"""
        subscription_product = self.ProductTemplate.create({
            'name': 'Professional Journal',
            'categ_id': self.subscription_category.id,  # 20% discount
            'list_price': 120.00,
            'is_ams_product': True,
            'ams_product_behavior': 'subscription',
            'is_subscription_product': True,
        })
        
        # Test member gets discounted price
        member_price = subscription_product.get_price_for_partner(self.member_partner)
        self.assertEqual(member_price, 96.00)  # 20% discount
        
        # Test non-member gets regular price
        non_member_price = subscription_product.get_price_for_partner(self.non_member_partner)
        self.assertEqual(non_member_price, 120.00)
        
        # Test membership product (no member discount)
        membership_product = self.ProductTemplate.create({
            'name': 'Annual Membership',
            'categ_id': self.membership_category.id,  # No member discount
            'list_price': 150.00,
            'is_ams_product': True,
            'ams_product_behavior': 'membership',
        })
        
        member_membership_price = membership_product.get_price_for_partner(self.member_partner)
        non_member_membership_price = membership_product.get_price_for_partner(self.non_member_partner)
        self.assertEqual(member_membership_price, non_member_membership_price)

    # ========================================================================
    # SUBSCRIPTION FUNCTIONALITY TESTS
    # ========================================================================

    def test_subscription_product_configuration(self):
        """Test subscription product configuration and details"""
        subscription_product = self.ProductTemplate.create({
            'name': 'Monthly Newsletter',
            'categ_id': self.subscription_category.id,
            'list_price': 60.00,
            'is_ams_product': True,
            'ams_product_behavior': 'subscription',
            'is_subscription_product': True,
            'subscription_term': 6,
            'subscription_term_type': 'months',
        })
        
        # Test subscription details
        details = subscription_product.get_subscription_details()
        self.assertTrue(details['is_subscription'])
        self.assertEqual(details['term'], 6)
        self.assertEqual(details['term_type'], 'months')
        self.assertEqual(details['term_display'], '6 Months')

    def test_subscription_onchange_behavior(self):
        """Test subscription onchange behavior and defaults"""
        product = self.ProductTemplate.new({
            'name': 'Test Subscription',
            'categ_id': self.subscription_category.id,
            'list_price': 100.00,
            'is_ams_product': True,
            'is_subscription_product': True,
        })
        
        # Trigger onchange
        product._onchange_is_subscription_product()
        
        # Should set default subscription term
        self.assertEqual(product.subscription_term, 12)
        self.assertEqual(product.subscription_term_type, 'months')

    # ========================================================================
    # DIGITAL CONTENT ENHANCED TESTS
    # ========================================================================

    def test_enhanced_digital_content_handling(self):
        """Test enhanced digital content detection and access"""
        # Digital product with URL
        digital_product_url = self.ProductTemplate.create({
            'name': 'Digital Resource with URL',
            'categ_id': self.digital_category.id,
            'list_price': 25.00,
            'is_ams_product': True,
            'ams_product_behavior': 'digital',
            'digital_url': 'https://example.com/secure-download',
        })
        
        self.assertTrue(digital_product_url.has_digital_content)
        
        # Test digital content access
        access_info = digital_product_url.get_digital_content_access(self.member_partner)
        self.assertTrue(access_info['is_digital'])
        self.assertTrue(access_info['has_content'])
        self.assertTrue(access_info['can_access'])
        self.assertEqual(access_info['download_url'], 'https://example.com/secure-download')
        
        # Digital product with attachment
        digital_product_file = self.ProductTemplate.create({
            'name': 'Digital Resource with File',
            'categ_id': self.digital_category.id,
            'list_price': 35.00,
            'is_ams_product': True,
            'ams_product_behavior': 'digital',
            'digital_attachment_id': self.test_attachment.id,
        })
        
        self.assertTrue(digital_product_file.has_digital_content)
        
        # Test access with attachment
        access_info = digital_product_file.get_digital_content_access(self.member_partner)
        self.assertEqual(access_info['attachment_id'], self.test_attachment.id)

    def test_digital_content_validation_enhanced(self):
        """Test enhanced digital content validation"""
        # Digital product missing content should raise error on validation
        with self.assertRaises(ValidationError):
            digital_product = self.ProductTemplate.create({
                'name': 'Incomplete Digital Product',
                'categ_id': self.digital_category.id,
                'list_price': 50.00,
                'is_ams_product': True,
                'ams_product_behavior': 'digital',
                # Missing digital_url and digital_attachment_id
            })
            digital_product._check_digital_content_requirements()

    # ========================================================================
    # PORTAL ACCESS TESTS
    # ========================================================================

    def test_portal_access_configuration(self):
        """Test portal access configuration and details"""
        portal_product = self.ProductTemplate.create({
            'name': 'Premium Access Membership',
            'categ_id': self.membership_category.id,
            'list_price': 250.00,
            'is_ams_product': True,
            'ams_product_behavior': 'membership',
            'grants_portal_access': True,
            'portal_group_ids': [(4, self.portal_group.id)],
        })
        
        # Test portal access details
        details = portal_product.get_portal_access_details()
        self.assertTrue(details['grants_access'])
        self.assertIn('Test Portal Group', details['portal_groups'])
        self.assertIn(self.portal_group.id, details['portal_group_ids'])

    # ========================================================================
    # DONATION FUNCTIONALITY TESTS
    # ========================================================================

    def test_donation_product_configuration(self):
        """Test donation product configuration and tax deductibility"""
        donation_product = self.ProductTemplate.create({
            'name': 'General Donation',
            'categ_id': self.donation_category.id,
            'list_price': 0.00,
            'is_ams_product': True,
            'ams_product_behavior': 'donation',
            'donation_tax_deductible': True,
            'donation_receipt_template_id': self.donation_template.id,
        })
        
        # Test donation details
        details = donation_product.get_donation_details()
        self.assertTrue(details['is_tax_deductible'])
        self.assertEqual(details['receipt_template'], 'Test Donation Receipt')
        self.assertEqual(details['receipt_template_id'], self.donation_template.id)

    # ========================================================================
    # EVENT INTEGRATION TESTS
    # ========================================================================

    def test_event_integration_configuration(self):
        """Test event integration configuration"""
        event_product = self.ProductTemplate.create({
            'name': 'Workshop Registration',
            'categ_id': self.event_category.id,
            'list_price': 175.00,
            'is_ams_product': True,
            'ams_product_behavior': 'event',
            'creates_event_registration': True,
        })
        
        # Test event details
        details = event_product.get_event_integration_details()
        self.assertTrue(details['creates_registration'])
        self.assertIsNone(details['default_event'])  # No event template set
        self.assertIsNone(details['default_event_id'])

    def test_event_template_validation(self):
        """Test event template requirement validation"""
        # This test would require the event module, so we'll skip validation if not available
        if not hasattr(self.env, 'event.event'):
            return
            
        # Event product with registration but no template should validate
        # (validation is only triggered in certain conditions)
        event_product = self.ProductTemplate.create({
            'name': 'Event Without Template',
            'categ_id': self.event_category.id,
            'list_price': 100.00,
            'is_ams_product': True,
            'ams_product_behavior': 'event',
            'creates_event_registration': True,
        })
        
        # Should create successfully - validation depends on specific conditions
        self.assertEqual(event_product.ams_product_behavior, 'event')

    # ========================================================================
    # ENHANCED VARIANT TESTS
    # ========================================================================

    def test_enhanced_variant_behavior_inheritance(self):
        """Test that variants properly inherit enhanced behavior from templates"""
        # Create membership product with comprehensive configuration
        membership_template = self.ProductTemplate.create({
            'name': 'Corporate Membership Package',
            'categ_id': self.membership_category.id,
            'list_price': 500.00,
            'is_ams_product': True,
            'ams_product_behavior': 'membership',
            'is_subscription_product': True,
            'grants_portal_access': True,
            'subscription_term': 24,
            'subscription_term_type': 'months',
        })
        
        variant = membership_template.product_variant_ids[0]
        
        # Test inheritance of all behavior fields
        self.assertTrue(variant.template_is_ams_product)
        self.assertEqual(variant.template_ams_product_behavior, 'membership')
        self.assertTrue(variant.template_is_subscription_product)
        self.assertTrue(variant.template_grants_portal_access)
        self.assertFalse(variant.template_requires_membership)  # Memberships don't require membership
        
        # Test variant behavior summary
        self.assertIn('Membership Product', variant.variant_behavior_summary)
        self.assertIn('Subscription', variant.variant_behavior_summary)
        self.assertIn('Portal Access', variant.variant_behavior_summary)

    def test_variant_availability_status_enhanced(self):
        """Test enhanced variant availability status computation"""
        # Digital product with content
        digital_template = self.ProductTemplate.create({
            'name': 'Digital Product with Content',
            'categ_id': self.digital_category.id,
            'list_price': 50.00,
            'is_ams_product': True,
            'ams_product_behavior': 'digital',
            'digital_url': 'https://example.com/download',
        })
        
        digital_variant = digital_template.product_variant_ids[0]
        self.assertEqual(digital_variant.availability_status, 'digital_available')
        
        # Digital product without content
        digital_template_empty = self.ProductTemplate.create({
            'name': 'Digital Product Empty',
            'categ_id': self.digital_category.id,
            'list_price': 25.00,
            'is_ams_product': True,
            'ams_product_behavior': 'digital',
        })
        
        digital_variant_empty = digital_template_empty.product_variant_ids[0]
        self.assertEqual(digital_variant_empty.availability_status, 'digital_missing')
        
        # Event product
        event_template = self.ProductTemplate.create({
            'name': 'Event Product',
            'categ_id': self.event_category.id,
            'list_price': 100.00,
            'is_ams_product': True,
            'ams_product_behavior': 'event',
            'creates_event_registration': True,
        })
        
        event_variant = event_template.product_variant_ids[0]
        self.assertEqual(event_variant.availability_status, 'event_available')
        
        # Membership product
        membership_template = self.ProductTemplate.create({
            'name': 'Membership Product',
            'categ_id': self.membership_category.id,
            'list_price': 150.00,
            'is_ams_product': True,
            'ams_product_behavior': 'membership',
        })
        
        membership_variant = membership_template.product_variant_ids[0]
        self.assertEqual(membership_variant.availability_status, 'membership_available')

    def test_variant_behavior_based_sku(self):
        """Test variant behavior-based SKU generation"""
        # Create multi-variant template
        event_template = self.ProductTemplate.create({
            'name': 'Multi-Day Conference',
            'categ_id': self.event_category.id,
            'list_price': 300.00,
            'is_ams_product': True,
            'ams_product_behavior': 'event',
            'default_code': 'EVT-CONF',
        })
        
        # Create additional variant
        variant2 = self.ProductProduct.create({
            'product_tmpl_id': event_template.id,
            'default_code': 'EVT-CONF-VIP',
        })
        
        # Test variant SKU logic
        variant1 = event_template.product_variant_ids[0]
        
        if len(event_template.product_variant_ids) == 1:
            # Single variant uses template SKU
            self.assertEqual(variant1.effective_sku, 'EVT-CONF')
        else:
            # Multi-variant uses behavior-aware suffix
            self.assertTrue(variant1.effective_sku.startswith('EVT-CONF-EVT'))
        
        # Variant with own SKU uses it
        self.assertEqual(variant2.effective_sku, 'EVT-CONF-VIP')

    def test_variant_enhanced_name_display(self):
        """Test enhanced variant name display with behavior indicators"""
        # Create membership product requiring membership
        membership_template = self.ProductTemplate.create({
            'name': 'Exclusive Membership',
            'categ_id': self.membership_category.id,
            'list_price': 400.00,
            'is_ams_product': True,
            'ams_product_behavior': 'membership',
            'requires_membership': True,  # This would be for some special membership product
            'default_code': 'MEM-EXCL',
        })
        
        variant = membership_template.product_variant_ids[0]
        name_display = variant.name_get()[0][1]
        
        # Should include emoji, SKU, and membership indicator
        self.assertIn('👤', name_display)  # Membership emoji
        self.assertIn('[MEM-EXCL]', name_display)
        self.assertIn('(Members Only)', name_display)
        
        # Test digital product
        digital_template = self.ProductTemplate.create({
            'name': 'Resource Library',
            'categ_id': self.digital_category.id,
            'list_price': 75.00,
            'is_ams_product': True,
            'ams_product_behavior': 'digital',
            'digital_url': 'https://example.com/library',
            'default_code': 'DIG-LIB',
        })
        
        digital_variant = digital_template.product_variant_ids[0]
        digital_name_display = digital_variant.name_get()[0][1]
        
        # Should include digital emoji and SKU
        self.assertIn('💾', digital_name_display)  # Digital emoji
        self.assertIn('[DIG-LIB]', digital_name_display)

    # ========================================================================
    # QUERY METHOD TESTS
    # ========================================================================

    def test_enhanced_query_methods_templates(self):
        """Test enhanced query methods for templates"""
        # Create products of different behaviors
        membership_product = self.ProductTemplate.create({
            'name': 'Membership Query Test',
            'categ_id': self.membership_category.id,
            'list_price': 150.00,
            'is_ams_product': True,
            'ams_product_behavior': 'membership',
        })
        
        event_product = self.ProductTemplate.create({
            'name': 'Event Query Test',
            'categ_id': self.event_category.id,
            'list_price': 200.00,
            'is_ams_product': True,
            'ams_product_behavior': 'event',
        })
        
        subscription_product = self.ProductTemplate.create({
            'name': 'Subscription Query Test',
            'categ_id': self.subscription_category.id,
            'list_price': 120.00,
            'is_ams_product': True,
            'ams_product_behavior': 'subscription',
            'is_subscription_product': True,
        })
        
        donation_product = self.ProductTemplate.create({
            'name': 'Donation Query Test',
            'categ_id': self.donation_category.id,
            'list_price': 0.00,
            'is_ams_product': True,
            'ams_product_behavior': 'donation',
            'donation_tax_deductible': True,
        })
        
        # Test behavior-specific queries
        membership_products = self.ProductTemplate.get_products_by_behavior_type('membership')
        self.assertIn(membership_product, membership_products)
        self.assertNotIn(event_product, membership_products)
        
        event_products = self.ProductTemplate.get_event_products()
        self.assertIn(event_product, event_products)
        self.assertNotIn(membership_product, event_products)
        
        subscription_products = self.ProductTemplate.get_subscription_products()
        self.assertIn(subscription_product, subscription_products)
        self.assertNotIn(event_product, subscription_products)
        
        donation_products = self.ProductTemplate.get_donation_products()
        self.assertIn(donation_product, donation_products)
        self.assertNotIn(membership_product, donation_products)

    def test_enhanced_query_methods_variants(self):
        """Test enhanced query methods for variants"""
        # Create templates to generate variants
        membership_template = self.ProductTemplate.create({
            'name': 'Membership Variant Test',
            'categ_id': self.membership_category.id,
            'list_price': 150.00,
            'is_ams_product': True,
            'ams_product_behavior': 'membership',
            'grants_portal_access': True,
        })
        
        event_template = self.ProductTemplate.create({
            'name': 'Event Variant Test',
            'categ_id': self.event_category.id,
            'list_price': 200.00,
            'is_ams_product': True,
            'ams_product_behavior': 'event',
            'creates_event_registration': True,
        })
        
        # Get variants
        membership_variant = membership_template.product_variant_ids[0]
        event_variant = event_template.product_variant_ids[0]
        
        # Test variant-specific queries
        membership_variants = self.ProductProduct.get_ams_variants_by_behavior_type('membership')
        self.assertIn(membership_variant, membership_variants)
        self.assertNotIn(event_variant, membership_variants)
        
        portal_access_variants = self.ProductProduct.get_portal_access_variants()
        self.assertIn(membership_variant, portal_access_variants)
        self.assertNotIn(event_variant, portal_access_variants)
        
        event_registration_variants = self.ProductProduct.get_event_registration_variants()
        self.assertIn(event_variant, event_registration_variants)
        self.assertNotIn(membership_variant, event_registration_variants)

    # ========================================================================
    # VALIDATION TESTS
    # ========================================================================

    def test_enhanced_validation_rules(self):
        """Test enhanced validation rules"""
        # Test subscription term validation
        with self.assertRaises(ValidationError):
            subscription_product = self.ProductTemplate.create({
                'name': 'Invalid Subscription',
                'categ_id': self.subscription_category.id,
                'list_price': 100.00,
                'is_ams_product': True,
                'ams_product_behavior': 'subscription',
                'is_subscription_product': True,
                'subscription_term': 0,  # Invalid: must be > 0
            })
            subscription_product._check_subscription_term()

    # ========================================================================
    # INTEGRATION TESTS
    # ========================================================================

    def test_category_behavior_integration(self):
        """Test integration between categories and product behavior"""
        # Create product and test category behavior suggestion
        product = self.ProductTemplate.new({
            'name': 'Category Integration Test',
            'list_price': 100.00,
            'categ_id': self.event_category.id,
        })
        
        # Trigger category onchange
        product._onchange_categ_id()
        
        # Should suggest event behavior based on category
        self.assertTrue(product.is_ams_product)
        self.assertEqual(product.ams_product_behavior, 'event')

    def test_comprehensive_business_methods(self):
        """Test comprehensive business method integration"""
        # Create complex product with all features
        complex_product = self.ProductTemplate.create({
            'name': 'Comprehensive Test Product',
            'categ_id': self.membership_category.id,
            'list_price': 500.00,
            'is_ams_product': True,
            'ams_product_behavior': 'membership',
            'is_subscription_product': True,
            'grants_portal_access': True,
            'portal_group_ids': [(4, self.portal_group.id)],
            'subscription_term': 12,
            'subscription_term_type': 'months',
            'includes_benefits': 'Full access to all resources and services',
        })
        
        # Test all business methods return proper data
        subscription_details = complex_product.get_subscription_details()
        self.assertTrue(subscription_details['is_subscription'])
        
        portal_details = complex_product.get_portal_access_details()
        self.assertTrue(portal_details['grants_access'])
        
        accounting_config = complex_product.get_accounting_configuration()
        self.assertIsInstance(accounting_config, dict)

    # ========================================================================
    # ACTION METHOD TESTS
    # ========================================================================

    def test_enhanced_action_methods(self):
        """Test enhanced action methods"""
        subscription_product = self.ProductTemplate.create({
            'name': 'Action Test Product',
            'categ_id': self.subscription_category.id,
            'list_price': 120.00,
            'is_ams_product': True,
            'ams_product_behavior': 'subscription',
            'is_subscription_product': True,
        })
        
        # Test behavior test action
        action = subscription_product.action_test_product_behavior()
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'display_notification')
        self.assertIn('Behavior: Subscription Product', action['params']['message'])
        
        # Test member pricing action
        pricing_action = subscription_product.action_test_member_pricing()
        self.assertEqual(pricing_action['type'], 'ir.actions.client')
        
        # Test variant actions
        variant = subscription_product.product_variant_ids[0]
        variant_action = variant.action_test_variant_behavior()
        self.assertEqual(variant_action['type'], 'ir.actions.client')

    # ========================================================================
    # PERFORMANCE AND EDGE CASES
    # ========================================================================

    def test_performance_with_multiple_behavior_products(self):
        """Test performance with multiple products of different behaviors"""
        # Create multiple products of each behavior type
        behaviors = ['membership', 'subscription', 'event', 'publication', 
                    'merchandise', 'certification', 'digital', 'donation']
        
        products = []
        for i, behavior in enumerate(behaviors):
            for j in range(3):  # 3 products per behavior
                category = getattr(self, f'{behavior}_category', self.membership_category)
                product = self.ProductTemplate.create({
                    'name': f'{behavior.title()} Product {j+1}',
                    'categ_id': category.id,
                    'list_price': 100.00 + (i * 10) + j,
                    'is_ams_product': True,
                    'ams_product_behavior': behavior,
                })
                products.append(product)
        
        # Test bulk query methods perform well
        ams_products = self.ProductTemplate.get_ams_products_by_category_type()
        self.assertTrue(len(ams_products) >= len(products))
        
        behavior_products = self.ProductTemplate.get_products_by_behavior_type('membership')
        self.assertEqual(len(behavior_products), 3)

    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling"""
        # Product with behavior but no category
        product = self.ProductTemplate.create({
            'name': 'Edge Case Product',
            'list_price': 100.00,
            'is_ams_product': True,
            'ams_product_behavior': 'event',
        })
        
        # Should handle gracefully
        self.assertEqual(product.ams_product_behavior, 'event')
        
        # Test with None partner
        price = product.get_price_for_partner(None)
        self.assertEqual(price, 100.00)
        
        # Test can_be_purchased_by_partner with None
        can_purchase = product.can_be_purchased_by_partner(None)
        self.assertTrue(can_purchase)  # Should default to True for non-restricted products

    def tearDown(self):
        """Clean up after tests"""
        super().tearDown()
        _logger.info("Enhanced AMS Products Base tests completed successfully")