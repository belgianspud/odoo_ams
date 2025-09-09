# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class TestMemberData(TransactionCase):

    def setUp(self):
        super().setUp()
        
        # Get test country and state
        self.country_us = self.env.ref('base.us')
        self.state_ca = self.env.ref('base.state_us_5')  # California
        
        # Create test individual data using existing Odoo fields where possible
        self.individual_data = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone': '555-1234',
            'mobile': '555-9999',
            'date_of_birth': '1985-05-15',
            'gender': 'male',
            'credentials': 'CPA, MBA',
            'is_company': False,
            'street': '123 Main St',
            'city': 'Los Angeles',
            'state_id': self.state_ca.id,
            'zip': '90210',
            'country_id': self.country_us.id,
            'is_member': True,
            'membership_status': 'active',
        }
        
        # Create test organization data using existing Odoo fields
        self.organization_data = {
            'name': 'Acme Corporation',
            'acronym': 'ACME',
            'website': 'https://www.acme.com',
            'email': 'info@acme.com',
            'phone': '555-0000',
            'organization_type': 'corporation',
            'year_established': 2000,
            'employee_count': 500,
            'annual_revenue': 10000000,
            'vat': '12-3456789',  # Using existing vat field
            'ein_number': '12-3456789',
            'is_company': True,
            'is_member': True,
            'membership_status': 'active',
        }

    def test_individual_member_creation(self):
        """Test creating an individual member with AMS extensions"""
        partner = self.env['res.partner'].create(self.individual_data)
        
        # Test basic fields
        self.assertEqual(partner.name, 'John Doe')
        self.assertEqual(partner.email, 'john.doe@example.com')
        self.assertEqual(partner.date_of_birth, date(1985, 5, 15))
        self.assertEqual(partner.gender, 'male')
        self.assertEqual(partner.credentials, 'CPA, MBA')
        self.assertFalse(partner.is_company)
        
        # Test membership fields
        self.assertTrue(partner.is_member)
        self.assertEqual(partner.membership_status, 'active')
        
        # Test member ID generation
        self.assertTrue(partner.member_id)
        self.assertTrue(partner.member_id.startswith('M'))

    def test_organization_member_creation(self):
        """Test creating an organization member with AMS extensions"""
        partner = self.env['res.partner'].create(self.organization_data)
        
        # Test basic fields
        self.assertEqual(partner.name, 'Acme Corporation')
        self.assertEqual(partner.acronym, 'ACME')
        self.assertEqual(partner.website, 'https://www.acme.com')
        self.assertEqual(partner.organization_type, 'corporation')
        self.assertTrue(partner.is_company)
        
        # Test membership fields
        self.assertTrue(partner.is_member)
        self.assertEqual(partner.membership_status, 'active')
        
        # Test member ID generation
        self.assertTrue(partner.member_id)
        self.assertTrue(partner.member_id.startswith('M'))
        
        # Test computed display name with acronym
        expected_name = 'Acme Corporation (ACME)'
        self.assertEqual(partner.display_name_org, expected_name)

    def test_member_id_computation(self):
        """Test member ID computation using ref field"""
        # Create member without setting ref
        partner = self.env['res.partner'].create({
            'name': 'Test Member',
            'is_member': True,
            'is_company': False,
        })
        
        # Should have generated member_id
        self.assertTrue(partner.member_id)
        self.assertTrue(partner.member_id.startswith('M'))
        
        # Test that ref field is populated
        self.assertTrue(partner.ref)
        
        # Test inverse computation
        partner.member_id = 'M000999'
        self.assertEqual(partner.ref, '999')

    def test_membership_duration_computation(self):
        """Test membership duration calculation"""
        partner = self.env['res.partner'].create({
            'name': 'Duration Test',
            'is_member': True,
            'member_since': date.today() - timedelta(days=365),
            'is_company': False,
        })
        
        # Should be approximately 365 days
        self.assertAlmostEqual(partner.membership_duration_days, 365, delta=1)

    def test_renewal_due_computation(self):
        """Test renewal due calculation"""
        # Create member with renewal due soon
        partner = self.env['res.partner'].create({
            'name': 'Renewal Test',
            'is_member': True,
            'membership_status': 'active',
            'renewal_date': date.today() + timedelta(days=15),
            'is_company': False,
        })
        
        # Should be renewal due (within 30 days)
        self.assertTrue(partner.is_renewal_due)
        
        # Test with renewal far in future
        partner.renewal_date = date.today() + timedelta(days=60)
        self.assertFalse(partner.is_renewal_due)

    def test_website_url_validation(self):
        """Test website URL validation for organizations"""
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Test Org',
                'website': 'not-a-url',
                'is_company': True,
            })

    def test_website_url_auto_format(self):
        """Test automatic website URL formatting"""
        partner = self.env['res.partner'].create({
            'name': 'Test Org',
            'website': 'www.test.com',  # Missing protocol
            'is_company': True,
        })
        
        # Should auto-add https://
        self.assertEqual(partner.website, 'https://www.test.com')

    def test_ein_format_validation(self):
        """Test EIN number format validation"""
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Test Org',
                'ein_number': '123456789',  # Wrong format
                'is_company': True,
            })
        
        # Test correct format
        partner = self.env['res.partner'].create({
            'name': 'Test Org',
            'ein_number': '12-3456789',  # Correct format
            'is_company': True,
        })
        self.assertEqual(partner.ein_number, '12-3456789')

    def test_ein_auto_format(self):
        """Test EIN auto-formatting"""
        partner = self.env['res.partner'].create({
            'name': 'Test Org',
            'is_company': True,
        })
        
        # Test auto-formatting on change
        partner.ein_number = '123456789'
        partner._onchange_ein_number()
        self.assertEqual(partner.ein_number, '12-3456789')

    def test_year_established_validation(self):
        """Test year established validation"""
        current_year = date.today().year
        
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Test Org',
                'year_established': 1700,  # Too old
                'is_company': True,
            })
        
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Test Org',
                'year_established': current_year + 1,  # Future date
                'is_company': True,
            })

    def test_employee_count_computation(self):
        """Test employee count computation using child_ids"""
        # Create organization
        organization = self.env['res.partner'].create(self.organization_data)
        
        # Create employee
        employee = self.env['res.partner'].create({
            'name': 'John Employee',
            'parent_id': organization.id,
            'is_company': False,
        })
        
        # Test computed employee count
        self.assertEqual(organization.employee_count_computed, 1)
        self.assertIn(employee, organization.child_ids)

    def test_action_make_member(self):
        """Test converting prospect to member"""
        partner = self.env['res.partner'].create({
            'name': 'Prospect Test',
            'is_member': False,
            'is_company': False,
        })
        
        # Convert to member
        partner.action_make_member()
        
        self.assertTrue(partner.is_member)
        self.assertEqual(partner.membership_status, 'active')
        self.assertEqual(partner.join_date, date.today())

    def test_action_renew_membership(self):
        """Test membership renewal"""
        partner = self.env['res.partner'].create({
            'name': 'Renewal Test',
            'is_member': True,
            'membership_status': 'active',
            'is_company': False,
        })
        
        # Renew membership
        partner.action_renew_membership()
        
        self.assertEqual(partner.membership_status, 'active')
        self.assertEqual(partner.join_date, date.today())
        expected_renewal = date.today() + timedelta(days=365)
        self.assertEqual(partner.renewal_date, expected_renewal)

    def test_action_view_employees(self):
        """Test view employees action for organizations"""
        organization = self.env['res.partner'].create(self.organization_data)
        
        action = organization.action_view_employees()
        
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'res.partner')
        self.assertIn(('parent_id', '=', organization.id), action['domain'])

    def test_get_organization_summary(self):
        """Test organization summary method"""
        organization = self.env['res.partner'].create(self.organization_data)
        
        summary = organization.get_organization_summary()
        
        self.assertEqual(summary['name'], 'Acme Corporation')
        self.assertEqual(summary['acronym'], 'ACME')
        self.assertEqual(summary['type'], 'corporation')
        self.assertEqual(summary['employees'], 500)
        self.assertEqual(summary['revenue'], 10000000)
        self.assertEqual(summary['established'], 2000)

    def test_member_since_auto_set(self):
        """Test that member_since is automatically set when becoming a member"""
        partner = self.env['res.partner'].create({
            'name': 'Auto Member Since Test',
            'is_member': True,
            'is_company': False,
        })
        
        # member_since should be set automatically
        self.assertEqual(partner.member_since, date.today())

    def test_legacy_contact_id_preservation(self):
        """Test that legacy fields are preserved"""
        partner = self.env['res.partner'].create({
            'name': 'Legacy User',
            'legacy_contact_id': 'OLD123',
            'is_company': False,
        })
        
        self.assertEqual(partner.legacy_contact_id, 'OLD123')

    def test_engagement_score_tracking(self):
        """Test engagement score functionality"""
        partner = self.env['res.partner'].create({
            'name': 'Engagement Test',
            'is_member': True,
            'engagement_score': 85.5,
            'is_company': False,
        })
        
        self.assertEqual(partner.engagement_score, 85.5)

    def test_donor_level_classification(self):
        """Test donor level classification"""
        partner = self.env['res.partner'].create({
            'name': 'Donor Test',
            'is_member': True,
            'donor_level': 'gold',
            'total_contributions': 5000.00,
            'is_company': False,
        })
        
        self.assertEqual(partner.donor_level, 'gold')
        self.assertEqual(partner.total_contributions, 5000.00)