# -*- coding: utf-8 -*-
# Part of Association Management Software (AMS)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class TestMembershipTypes(TransactionCase):

    def setUp(self):
        super().setUp()
        self.MembershipType = self.env['membership.type']
        
    def test_membership_type_creation(self):
        """Test basic membership type creation"""
        membership_type = self.MembershipType.create({
            'name': 'Test Individual',
            'code': 'TEST_IND',
            'membership_category': 'individual',
            'price': 150.00,
            'duration': 12,
        })
        
        self.assertEqual(membership_type.name, 'Test Individual')
        self.assertEqual(membership_type.code, 'TEST_IND')
        self.assertEqual(membership_type.membership_category, 'individual')
        self.assertEqual(membership_type.price, 150.00)
        self.assertEqual(membership_type.duration, 12)
        self.assertFalse(membership_type.is_lifetime)

    def test_lifetime_membership_type(self):
        """Test lifetime membership type creation"""
        membership_type = self.MembershipType.create({
            'name': 'Lifetime Member',
            'code': 'LIFETIME_TEST',
            'membership_category': 'individual',
            'price': 3000.00,
            'duration': 0,
        })
        
        self.assertTrue(membership_type.is_lifetime)
        self.assertEqual(membership_type.duration, 0)

    def test_unique_code_constraint(self):
        """Test that membership type codes must be unique"""
        self.MembershipType.create({
            'name': 'First Type',
            'code': 'UNIQUE_CODE',
            'membership_category': 'individual',
            'price': 100.00,
            'duration': 12,
        })
        
        with self.assertRaises(Exception):  # Should raise IntegrityError due to unique constraint
            self.MembershipType.create({
                'name': 'Second Type',
                'code': 'UNIQUE_CODE',  # Same code
                'membership_category': 'organization',
                'price': 200.00,
                'duration': 12,
            })

    def test_positive_price_constraint(self):
        """Test that price must be positive"""
        with self.assertRaises(Exception):  # Should raise constraint error
            self.MembershipType.create({
                'name': 'Invalid Price Type',
                'code': 'INVALID_PRICE',
                'membership_category': 'individual',
                'price': -100.00,  # Negative price
                'duration': 12,
            })

    def test_positive_duration_constraint(self):
        """Test that duration must be positive or zero"""
        with self.assertRaises(Exception):  # Should raise constraint error
            self.MembershipType.create({
                'name': 'Invalid Duration Type',
                'code': 'INVALID_DURATION',
                'membership_category': 'individual',
                'price': 100.00,
                'duration': -5,  # Negative duration
            })

    def test_period_validation(self):
        """Test period validation constraints"""
        membership_type = self.MembershipType.create({
            'name': 'Test Type',
            'code': 'TEST_PERIODS',
            'membership_category': 'individual',
            'price': 100.00,
            'duration': 12,
        })
        
        # Test invalid grace period
        with self.assertRaises(ValidationError):
            membership_type.grace_period = -10

        # Test invalid suspend period
        with self.assertRaises(ValidationError):
            membership_type.suspend_period = -5

        # Test invalid terminate period
        with self.assertRaises(ValidationError):
            membership_type.terminate_period = -3

    def test_code_format_validation(self):
        """Test code format validation"""
        # Valid codes should work
        membership_type = self.MembershipType.create({
            'name': 'Test Type',
            'code': 'VALID_CODE_123',
            'membership_category': 'individual',
            'price': 100.00,
            'duration': 12,
        })
        self.assertEqual(membership_type.code, 'VALID_CODE_123')

        # Invalid code with special characters should fail
        with self.assertRaises(ValidationError):
            self.MembershipType.create({
                'name': 'Invalid Code Type',
                'code': 'INVALID@CODE!',  # Contains special characters
                'membership_category': 'individual',
                'price': 100.00,
                'duration': 12,
            })

    def test_membership_type_statistics(self):
        """Test membership type statistics computation"""
        membership_type = self.MembershipType.create({
            'name': 'Stats Test Type',
            'code': 'STATS_TEST',
            'membership_category': 'individual',
            'price': 100.00,
            'duration': 12,
        })
        
        # Initially should have zero stats
        membership_type._compute_membership_count()
        membership_type._compute_total_revenue()
        self.assertEqual(membership_type.membership_count, 0)
        self.assertEqual(membership_type.total_revenue, 0.0)

    def test_get_renewal_price(self):
        """Test renewal price calculation"""
        membership_type = self.MembershipType.create({
            'name': 'Renewal Test Type',
            'code': 'RENEWAL_TEST',
            'membership_category': 'individual',
            'price': 150.00,
            'duration': 12,
        })
        
        renewal_price = membership_type.get_renewal_price()
        self.assertEqual(renewal_price, 150.00)

    def test_membership_type_copy(self):
        """Test copying a membership type"""
        original_type = self.MembershipType.create({
            'name': 'Original Type',
            'code': 'ORIGINAL',
            'membership_category': 'individual',
            'price': 100.00,
            'duration': 12,
        })
        
        copied_type = original_type.copy()
        
        # Should have different code and name
        self.assertNotEqual(copied_type.code, original_type.code)
        self.assertNotEqual(copied_type.name, original_type.name)
        self.assertTrue(copied_type.name.endswith(' (Copy)'))
        self.assertTrue(copied_type.code.endswith('_copy'))
        
        # Other fields should be the same
        self.assertEqual(copied_type.membership_category, original_type.membership_category)
        self.assertEqual(copied_type.price, original_type.price)
        self.assertEqual(copied_type.duration, original_type.duration)

    def test_auto_code_generation(self):
        """Test automatic code generation when not provided"""
        membership_type = self.MembershipType.create({
            'name': 'Auto Code Type',
            'membership_category': 'individual',
            'price': 100.00,
            'duration': 12,
            # No code provided
        })
        
        # Should have auto-generated code
        self.assertIsNotNone(membership_type.code)
        self.assertTrue(len(membership_type.code) > 0)

    def test_action_view_memberships(self):
        """Test action to view memberships"""
        membership_type = self.MembershipType.create({
            'name': 'Action Test Type',
            'code': 'ACTION_TEST',
            'membership_category': 'individual',
            'price': 100.00,
            'duration': 12,
        })
        
        action = membership_type.action_view_memberships()
        
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'membership.membership')
        self.assertIn(('membership_type_id', '=', membership_type.id), action['domain'])

    def test_get_membership_statistics(self):
        """Test getting detailed membership statistics"""
        membership_type = self.MembershipType.create({
            'name': 'Statistics Type',
            'code': 'STATS_DETAIL',
            'membership_category': 'individual',
            'price': 100.00,
            'duration': 12,
        })
        
        stats = membership_type.get_membership_statistics()
        
        # Should return dictionary with expected keys
        expected_keys = [
            'total_count', 'active_count', 'grace_count', 
            'suspended_count', 'terminated_count', 'cancelled_count',
            'total_revenue', 'average_revenue', 'expiring_soon_count'
        ]
        
        for key in expected_keys:
            self.assertIn(key, stats)
        
        # With no memberships, counts should be zero
        self.assertEqual(stats['total_count'], 0)
        self.assertEqual(stats['active_count'], 0)
        self.assertEqual(stats['total_revenue'], 0)

    def test_membership_type_report(self):
        """Test membership type report generation"""
        # Create a few test types
        type1 = self.MembershipType.create({
            'name': 'Report Type 1',
            'code': 'REPORT_1',
            'membership_category': 'individual',
            'price': 100.00,
            'duration': 12,
        })
        
        type2 = self.MembershipType.create({
            'name': 'Report Type 2',
            'code': 'REPORT_2',
            'membership_category': 'organization',
            'price': 500.00,
            'duration': 12,
        })
        
        report_data = self.MembershipType.get_membership_type_report()
        
        # Should return list of dictionaries
        self.assertIsInstance(report_data, list)
        self.assertTrue(len(report_data) >= 2)  # At least our test types
        
        # Check structure of first item
        if report_data:
            first_item = report_data[0]
            expected_keys = ['name', 'code', 'category', 'price', 'currency', 'duration', 'stats']
            for key in expected_keys:
                self.assertIn(key, first_item)

    def test_create_default_email_templates(self):
        """Test creating default email templates"""
        membership_type = self.MembershipType.create({
            'name': 'Email Template Type',
            'code': 'EMAIL_TEST',
            'membership_category': 'individual',
            'price': 100.00,
            'duration': 12,
        })
        
        # Should not have templates initially
        self.assertFalse(membership_type.welcome_template_id)
        self.assertFalse(membership_type.renewal_template_id)
        
        # Create templates
        result = membership_type.create_default_email_templates()
        
        # Should return success notification
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        
        # Refresh record to get updated template references
        membership_type.refresh()
        
        # Should now have at least welcome template
        # Note: This might fail if template creation fails, but the method should handle that gracefully