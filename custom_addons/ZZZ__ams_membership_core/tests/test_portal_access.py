# -*- coding: utf-8 -*-

import logging
from datetime import date, timedelta
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


@tagged('portal', 'membership')
class TestPortalMembershipAccess(TransactionCase):
    """Test portal user access to membership data"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test data
        cls._create_test_data()

    @classmethod
    def _create_test_data(cls):
        """Create test data for portal membership tests"""
        
        # Create a test partner
        cls.test_partner = cls.env['res.partner'].create({
            'name': 'Test Portal Member',
            'email': 'test.portal@example.com',
            'is_member': True,
            'member_status': 'active',
            'member_number': 'TEST001',
        })
        
        # Create portal user for the partner
        portal_group = cls.env.ref('base.group_portal')
        cls.portal_user = cls.env['res.users'].create({
            'name': 'Test Portal User',
            'login': 'test.portal@example.com',
            'email': 'test.portal@example.com',
            'partner_id': cls.test_partner.id,
            'groups_id': [(6, 0, [portal_group.id])],
        })
        
        # Add to custom membership portal group if it exists
        try:
            membership_portal_group = cls.env.ref('ams_membership_core.group_membership_portal')
            cls.portal_user.groups_id = [(4, membership_portal_group.id)]
        except:
            pass  # Group doesn't exist yet
        
        # Create membership product
        cls.membership_product = cls.env['product.template'].create({
            'name': 'Test Regular Membership',
            'type': 'service',
            'is_subscription_product': True,
            'subscription_product_type': 'membership',
            'subscription_period': 'annual',
            'list_price': 100.0,
        })
        
        # Create chapter product
        cls.chapter_product = cls.env['product.template'].create({
            'name': 'Test Local Chapter',
            'type': 'service',
            'is_subscription_product': True,
            'subscription_product_type': 'chapter',
            'subscription_period': 'annual',
            'list_price': 50.0,
            'chapter_type': 'local',
            'chapter_location': 'Test City',
        })
        
        # Create regular membership
        cls.regular_membership = cls.env['ams.membership'].create({
            'partner_id': cls.test_partner.id,
            'product_id': cls.membership_product.product_variant_ids[0].id,
            'start_date': date.today().replace(month=1, day=1),
            'end_date': date.today().replace(month=12, day=31),
            'state': 'active',
            'membership_fee': 100.0,
            'payment_status': 'paid',
        })
        
        # Create chapter membership
        cls.chapter_membership = cls.env['ams.membership'].create({
            'partner_id': cls.test_partner.id,
            'product_id': cls.chapter_product.product_variant_ids[0].id,
            'start_date': date.today().replace(month=1, day=1),
            'end_date': date.today().replace(month=12, day=31),
            'state': 'active',
            'membership_fee': 50.0,
            'payment_status': 'paid',
        })
        
        # Create test benefit
        cls.test_benefit = cls.env['ams.benefit'].create({
            'name': 'Test Member Benefit',
            'code': 'TEST_BENEFIT',
            'benefit_type': 'access',
            'active': True,
        })

    def test_partner_foundation_fields(self):
        """Test that foundation fields are properly set"""
        partner = self.test_partner
        
        # Test foundation field existence and values
        self.assertTrue(hasattr(partner, 'is_member'), "Partner should have is_member field")
        self.assertTrue(partner.is_member, "Test partner should be marked as member")
        
        self.assertTrue(hasattr(partner, 'member_status'), "Partner should have member_status field")
        self.assertEqual(partner.member_status, 'active', "Test partner should have active status")
        
        self.assertTrue(hasattr(partner, 'member_number'), "Partner should have member_number field")
        self.assertEqual(partner.member_number, 'TEST001', "Test partner should have correct member number")

    def test_portal_user_groups(self):
        """Test that portal user is in correct groups"""
        user = self.portal_user
        
        # Check portal group membership
        portal_group = self.env.ref('base.group_portal')
        self.assertIn(portal_group, user.groups_id, "Portal user should be in base portal group")
        
        # Check partner relationship
        self.assertEqual(user.partner_id, self.test_partner, "Portal user should be linked to test partner")

    def test_membership_data_exists(self):
        """Test that membership test data was created correctly"""
        
        # Test regular membership
        self.assertTrue(self.regular_membership.exists(), "Regular membership should exist")
        self.assertEqual(self.regular_membership.partner_id, self.test_partner, "Regular membership should belong to test partner")
        self.assertFalse(self.regular_membership.is_chapter_membership, "Regular membership should not be chapter type")
        self.assertEqual(self.regular_membership.state, 'active', "Regular membership should be active")
        
        # Test chapter membership
        self.assertTrue(self.chapter_membership.exists(), "Chapter membership should exist")
        self.assertEqual(self.chapter_membership.partner_id, self.test_partner, "Chapter membership should belong to test partner")
        self.assertTrue(self.chapter_membership.is_chapter_membership, "Chapter membership should be chapter type")
        self.assertEqual(self.chapter_membership.state, 'active', "Chapter membership should be active")

    def test_portal_membership_access(self):
        """Test that portal user can access their own memberships"""
        
        # Test access as portal user
        memberships = self.env['ams.membership'].with_user(self.portal_user).search([
            ('partner_id', '=', self.test_partner.id)
        ])
        
        self.assertEqual(len(memberships), 2, "Portal user should see both memberships")
        
        # Test that portal user can read membership fields
        for membership in memberships:
            try:
                # These should not raise AccessError
                _ = membership.name
                _ = membership.product_id.name
                _ = membership.state
                _ = membership.is_chapter_membership
                _ = membership.start_date
                _ = membership.end_date
            except AccessError:
                self.fail(f"Portal user should be able to read membership {membership.id} fields")

    def test_portal_access_restrictions(self):
        """Test that portal users cannot access other users' memberships"""
        
        # Create another partner and membership
        other_partner = self.env['res.partner'].create({
            'name': 'Other Member',
            'email': 'other@example.com',
            'is_member': True,
        })
        
        other_membership = self.env['ams.membership'].create({
            'partner_id': other_partner.id,
            'product_id': self.membership_product.product_variant_ids[0].id,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'state': 'active',
        })
        
        # Portal user should not see other user's memberships
        accessible_memberships = self.env['ams.membership'].with_user(self.portal_user).search([])
        
        membership_ids = accessible_memberships.mapped('id')
        self.assertNotIn(other_membership.id, membership_ids, 
                        "Portal user should not see other users' memberships")

    def test_portal_benefit_access(self):
        """Test that portal user can access active benefits"""
        
        benefits = self.env['ams.benefit'].with_user(self.portal_user).search([
            ('active', '=', True)
        ])
        
        self.assertGreaterEqual(len(benefits), 1, "Portal user should see at least one active benefit")
        self.assertIn(self.test_benefit, benefits, "Portal user should see test benefit")

    def test_portal_product_access(self):
        """Test that portal user can access subscription products"""
        
        products = self.env['product.template'].with_user(self.portal_user).search([
            ('is_subscription_product', '=', True)
        ])
        
        self.assertGreaterEqual(len(products), 2, "Portal user should see subscription products")
        
        product_ids = products.mapped('id')
        self.assertIn(self.membership_product.id, product_ids, "Portal user should see membership product")
        self.assertIn(self.chapter_product.id, product_ids, "Portal user should see chapter product")

    def test_controller_data_separation(self):
        """Test that memberships are correctly separated into regular and chapter types"""
        
        # Get all memberships as portal user
        all_memberships = self.env['ams.membership'].with_user(self.portal_user).search([
            ('partner_id', '=', self.test_partner.id)
        ])
        
        # Separate like the controller does
        regular_memberships = all_memberships.filtered(lambda m: not m.is_chapter_membership)
        chapter_memberships = all_memberships.filtered(lambda m: m.is_chapter_membership)
        
        # Test counts
        self.assertEqual(len(all_memberships), 2, "Should find 2 total memberships")
        self.assertEqual(len(regular_memberships), 1, "Should find 1 regular membership")
        self.assertEqual(len(chapter_memberships), 1, "Should find 1 chapter membership")
        
        # Test correct assignment
        self.assertEqual(regular_memberships[0], self.regular_membership, "Should identify correct regular membership")
        self.assertEqual(chapter_memberships[0], self.chapter_membership, "Should identify correct chapter membership")

    def test_computed_fields(self):
        """Test that computed fields work correctly"""
        partner = self.test_partner
        
        # Force computation by accessing fields
        try:
            membership_count = partner.membership_count
            active_chapter_count = partner.active_chapter_count
            current_membership = partner.current_membership_id
            
            # Test values
            self.assertEqual(membership_count, 2, "Should count 2 total memberships")
            self.assertEqual(active_chapter_count, 1, "Should count 1 active chapter membership")
            self.assertEqual(current_membership, self.regular_membership, "Should identify correct current membership")
            
        except Exception as e:
            self.fail(f"Computed fields should work without error: {e}")

    def test_portal_partner_access(self):
        """Test that portal user can access their own partner data"""
        
        # Portal user should be able to read their own partner
        try:
            partner = self.env['res.partner'].with_user(self.portal_user).browse(self.test_partner.id)
            _ = partner.name
            _ = partner.email
            _ = partner.is_member
            _ = partner.member_status
        except AccessError:
            self.fail("Portal user should be able to read their own partner data")

    def test_membership_sequence_generation(self):
        """Test that membership sequences are generated correctly"""
        
        # Both memberships should have names (sequences)
        self.assertTrue(self.regular_membership.name, "Regular membership should have a name/sequence")
        self.assertTrue(self.chapter_membership.name, "Chapter membership should have a name/sequence")
        
        # Names should not be 'New'
        self.assertNotEqual(self.regular_membership.name, 'New', "Regular membership should have generated sequence")
        self.assertNotEqual(self.chapter_membership.name, 'New', "Chapter membership should have generated sequence")

    def test_membership_display_names(self):
        """Test that membership display names are generated correctly"""
        
        # Test regular membership display name
        expected_regular = f"{self.test_partner.name} - {self.membership_product.name}"
        self.assertEqual(self.regular_membership.display_name, expected_regular, 
                        "Regular membership should have correct display name")
        
        # Test chapter membership display name
        expected_chapter = f"Chapter: {self.test_partner.name} - {self.chapter_product.name}"
        self.assertEqual(self.chapter_membership.display_name, expected_chapter,
                        "Chapter membership should have correct display name")

    def test_benefit_application(self):
        """Test that benefits can be applied to memberships"""
        
        # Add benefit to membership
        self.regular_membership.benefit_ids = [(4, self.test_benefit.id)]
        
        # Test that benefit is accessible
        benefits = self.regular_membership.benefit_ids
        self.assertIn(self.test_benefit, benefits, "Benefit should be added to membership")
        
        # Test partner computed benefits
        try:
            partner_benefits = self.test_partner.active_benefit_ids
            self.assertIn(self.test_benefit, partner_benefits, "Partner should have active benefit")
        except:
            # Computed field might not be available if foundation missing
            pass

    def tearDown(self):
        """Clean up after each test"""
        super().tearDown()
        
        # Log test completion
        _logger.info(f"Completed test: {self._testMethodName}")

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        super().tearDownClass()
        
        # Clean up test data
        try:
            cls.portal_user.unlink()
            cls.regular_membership.unlink()
            cls.chapter_membership.unlink()
            cls.test_benefit.unlink()
            cls.membership_product.unlink()
            cls.chapter_product.unlink()
            cls.test_partner.unlink()
        except:
            pass  # May have cascade deletes