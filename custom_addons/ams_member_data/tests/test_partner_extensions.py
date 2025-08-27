"""Test cases for AMS Partner Extensions functionality."""

from odoo.tests import common
from odoo.exceptions import ValidationError


class TestResPartnerIndividual(common.TransactionCase):
    """Test individual partner extensions."""

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.MemberType = self.env['ams.member.type']
        self.MemberStatus = self.env['ams.member.status']
        
        # Create test member type and status
        self.individual_type = self.MemberType.create({
            'name': 'Test Individual',
            'code': 'TEST_IND',
            'is_individual': True,
            'is_organization': False,
        })
        
        self.active_status = self.MemberStatus.create({
            'name': 'Test Active',
            'code': 'test_active',
            'is_active': True,
            'sequence': 20,
        })

    def test_create_individual_member(self):
        """Test creating an individual member."""
        partner = self.Partner.create({
            'first_name': 'John',
            'middle_name': 'Q',
            'last_name': 'Doe',
            'suffix': 'Jr',
            'member_type_id': self.individual_type.id,
            'member_status_id': self.active_status.id,
            'is_company': False,
        })
        
        # Check member ID was generated
        self.assertTrue(partner.member_id)
        self.assertTrue(partner.member_id.startswith('M'))
        
        # Check original join date was set
        self.assertTrue(partner.original_join_date)

    def test_name_computation_from_components(self):
        """Test that name is computed from components."""
        partner = self.Partner.create({
            'first_name': 'Jane',
            'last_name': 'Smith',
            'member_type_id': self.individual_type.id,
            'is_company': False,
        })
        
        # Trigger onchange to update name
        partner._onchange_name_components()
        self.assertEqual(partner.name, 'Jane Smith')
        
        # Test with all components
        partner.write({
            'middle_name': 'Marie',
            'suffix': 'PhD',
        })
        
        # Trigger onchange again
        partner._onchange_name_components()
        self.assertEqual(partner.name, 'Jane Marie Smith PhD')

    def test_phone_validation(self):
        """Test phone number format validation."""
        partner = self.Partner.create({
            'name': 'Test Person',
            'member_type_id': self.individual_type.id,
            'is_company': False,
        })
        
        # Valid phone formats
        valid_phones = ['+1234567890', '+441234567890', '+33123456789']
        
        for phone in valid_phones:
            partner.business_phone = phone
            # Should not raise exception
            partner._validate_phone_format()
        
        # Invalid phone format
        with self.assertRaises(ValidationError):
            partner.business_phone = 'invalid-phone'
            partner._validate_phone_format()

    def test_email_validation(self):
        """Test email format validation."""
        partner = self.Partner.create({
            'name': 'Test Person',
            'member_type_id': self.individual_type.id,
            'is_company': False,
        })
        
        # Valid email
        partner.email = 'test@example.com'
        partner._validate_email_format()  # Should not raise
        
        # Invalid email
        with self.assertRaises(ValidationError):
            partner.email = 'invalid-email'
            partner._validate_email_format()
        
        # Valid secondary email
        partner.secondary_email = 'secondary@example.com'
        partner._validate_email_format()  # Should not raise
        
        # Invalid secondary email
        with self.assertRaises(ValidationError):
            partner.secondary_email = 'invalid-secondary'
            partner._validate_email_format()

    def test_member_type_consistency(self):
        """Test member type consistency validation."""
        # Individual type should not be assigned to company
        with self.assertRaises(ValidationError):
            self.Partner.create({
                'name': 'Test Company',
                'member_type_id': self.individual_type.id,
                'is_company': True,  # This should conflict
            })

    def test_computed_fields(self):
        """Test computed fields like is_member, current_status."""
        partner = self.Partner.create({
            'first_name': 'Test',
            'last_name': 'Member',
            'member_type_id': self.individual_type.id,
            'member_status_id': self.active_status.id,
            'is_company': False,
        })
        
        # Test is_member computation based on member_status_id
        partner._compute_is_member()
        # Should be True because active_status.is_active = True
        self.assertTrue(partner.is_member)
        
        # Test current status computation
        partner._compute_current_status()
        self.assertEqual(partner.current_status, 'active')
        
        # Test with inactive status
        inactive_status = self.MemberStatus.create({
            'name': 'Test Inactive',
            'code': 'test_inactive',
            'is_active': False,
            'sequence': 30,
        })
        
        partner.member_status_id = inactive_status.id
        partner._compute_is_member()
        self.assertFalse(partner.is_member)
        
        partner._compute_current_status()
        self.assertEqual(partner.current_status, 'inactive')

    def test_secondary_address_fields(self):
        """Test secondary address functionality."""
        partner = self.Partner.create({
            'name': 'Test Member',
            'member_type_id': self.individual_type.id,
            'is_company': False,
            'secondary_address_line1': '456 Secondary St',
            'secondary_address_line2': 'Apt 2B',
            'secondary_address_city': 'Secondary City',
            'secondary_address_zip': '54321',
            'secondary_address_type': 'billing',
        })
        
        self.assertEqual(partner.secondary_address_line1, '456 Secondary St')
        self.assertEqual(partner.secondary_address_type, 'billing')

    def test_action_view_participations(self):
        """Test the action method for viewing participations."""
        partner = self.Partner.create({
            'name': 'Test Member',
            'member_type_id': self.individual_type.id,
            'is_company': False,
        })
        
        action = partner.action_view_participations()
        self.assertEqual(action['res_model'], 'ams.participation')
        self.assertIn(('partner_id', '=', partner.id), action['domain'])


class TestResPartnerOrganization(common.TransactionCase):
    """Test organization partner extensions."""

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.MemberType = self.env['ams.member.type']
        self.MemberStatus = self.env['ams.member.status']
        
        # Create test organization member type
        self.org_type = self.MemberType.create({
            'name': 'Test Organization',
            'code': 'TEST_ORG',
            'is_individual': False,
            'is_organization': True,
        })
        
        self.active_status = self.MemberStatus.create({
            'name': 'Test Active Org',
            'code': 'test_active_org',
            'is_active': True,
            'sequence': 20,
        })

    def test_create_organization_member(self):
        """Test creating an organization member."""
        partner = self.Partner.create({
            'name': 'Test Corporation',
            'member_type_id': self.org_type.id,
            'member_status_id': self.active_status.id,
            'is_company': True,
            'acronym': 'TC',
            'website_url': 'https://testcorp.com',
            'tin_number': '123456789',
            'ein_number': '987654321',
        })
        
        # Check member ID was generated
        self.assertTrue(partner.member_id)
        
        # Check organization-specific fields
        self.assertEqual(partner.acronym, 'TC')
        self.assertEqual(partner.website_url, 'https://testcorp.com')
        self.assertEqual(partner.tin_number, '123456789')
        self.assertEqual(partner.ein_number, '987654321')

    def test_website_url_validation(self):
        """Test website URL format validation."""
        partner = self.Partner.create({
            'name': 'Test Org',
            'member_type_id': self.org_type.id,
            'is_company': True,
        })
        
        # Valid URLs
        valid_urls = [
            'https://example.com',
            'http://test.org',
            'https://subdomain.example.com/path',
            'http://localhost:8080',
        ]
        
        for url in valid_urls:
            partner.website_url = url
            partner._validate_website_url()  # Should not raise
        
        # Invalid URL
        with self.assertRaises(ValidationError):
            partner.website_url = 'not-a-valid-url'
            partner._validate_website_url()

    def test_tax_number_validation(self):
        """Test TIN and EIN validation."""
        partner = self.Partner.create({
            'name': 'Test Org',
            'member_type_id': self.org_type.id,
            'is_company': True,
        })
        
        # Valid TIN formats (relaxed for testing)
        partner.tin_number = '123456789'
        partner._validate_tax_numbers()  # Should not raise
        
        # Valid EIN format  
        partner.ein_number = '987654321'
        partner._validate_tax_numbers()  # Should not raise
        
        # Invalid TIN (letters)
        with self.assertRaises(ValidationError):
            partner.tin_number = 'invalid-tin'
            partner._validate_tax_numbers()
        
        # Invalid EIN (too short)
        with self.assertRaises(ValidationError):
            partner.ein_number = '123456'  # Too short
            partner._validate_tax_numbers()

    def test_employee_relationships(self):
        """Test employee relationship management."""
        # Create organization
        org = self.Partner.create({
            'name': 'Test Organization',
            'member_type_id': self.org_type.id,
            'is_company': True,
        })
        
        # Create individual member type for employees
        individual_type = self.MemberType.create({
            'name': 'Employee',
            'code': 'EMP',
            'is_individual': True,
            'is_organization': False,
        })
        
        # Create employee
        employee = self.Partner.create({
            'name': 'John Employee',
            'parent_id': org.id,
            'member_type_id': individual_type.id,
            'is_company': False,
        })
        
        # Check relationship
        self.assertIn(employee, org.employee_ids)
        self.assertEqual(employee.parent_id, org)

    def test_portal_contact_validation(self):
        """Test portal primary contact validation."""
        # Create organization
        org = self.Partner.create({
            'name': 'Test Organization',
            'member_type_id': self.org_type.id,
            'is_company': True,
        })
        
        # Create employee
        employee = self.Partner.create({
            'name': 'Portal Admin',
            'parent_id': org.id,
            'is_company': False,
        })
        
        # Valid portal contact (employee of this org)
        org.portal_primary_contact_id = employee.id
        org._validate_portal_contact()  # Should not raise
        
        # Create unrelated person
        unrelated = self.Partner.create({
            'name': 'Unrelated Person',
            'is_company': False,
        })
        
        # Invalid portal contact (not an employee)
        with self.assertRaises(ValidationError):
            org.portal_primary_contact_id = unrelated.id
            org._validate_portal_contact()

    def test_enterprise_seat_computation(self):
        """Test enterprise seat computation."""
        org = self.Partner.create({
            'name': 'Enterprise Org',
            'member_type_id': self.org_type.id,
            'is_company': True,
        })
        
        # Initially no seats
        org._compute_enterprise_seats()
        self.assertEqual(org.total_seats, 0)
        self.assertEqual(org.assigned_seats, 0)
        self.assertEqual(org.available_seats, 0)

    def test_acronym_generation(self):
        """Test automatic acronym generation.""" 
        org = self.Partner.new({
            'name': 'International Business Machines',
            'is_company': True,
        })
        
        # Trigger onchange
        org._onchange_name_acronym()
        
        # Should generate IBM
        self.assertEqual(org.acronym, 'IBM')
        
        # Don't override existing acronym
        org.acronym = 'CUSTOM'
        org._onchange_name_acronym()
        self.assertEqual(org.acronym, 'CUSTOM')

    def test_action_methods(self):
        """Test action methods for viewing employees."""
        org = self.Partner.create({
            'name': 'Test Organization',
            'member_type_id': self.org_type.id,
            'is_company': True,
        })
        
        # Test view employees action
        action = org.action_view_employees()
        self.assertEqual(action['res_model'], 'res.partner')
        self.assertIn(('parent_id', '=', org.id), action['domain'])
        
        # Test view member employees action
        action = org.action_view_member_employees()
        self.assertEqual(action['res_model'], 'res.partner')
        self.assertIn(('parent_id', '=', org.id), action['domain'])
        self.assertIn(('is_member', '=', True), action['domain'])

        # Test view participations action
        action = org.action_view_participations()
        self.assertEqual(action['res_model'], 'ams.participation')
        self.assertIn(('company_id', '=', org.id), action['domain'])


class TestPartnerIntegration(common.TransactionCase):
    """Test integration between individuals and organizations."""

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.MemberType = self.env['ams.member.type']
        
        self.individual_type = self.MemberType.create({
            'name': 'Individual',
            'code': 'IND',
            'is_individual': True,
            'is_organization': False,
        })
        
        self.org_type = self.MemberType.create({
            'name': 'Organization',
            'code': 'ORG',
            'is_individual': False,
            'is_organization': True,
        })

    def test_member_id_sequence(self):
        """Test that member IDs are generated sequentially."""
        # Create first member
        member1 = self.Partner.create({
            'name': 'Member One',
            'member_type_id': self.individual_type.id,
            'is_company': False,
        })
        
        # Create second member
        member2 = self.Partner.create({
            'name': 'Member Two',
            'member_type_id': self.individual_type.id,
            'is_company': False,
        })
        
        # Both should have member IDs
        self.assertTrue(member1.member_id)
        self.assertTrue(member2.member_id)
        
        # Both should start with 'M'
        self.assertTrue(member1.member_id.startswith('M'))
        self.assertTrue(member2.member_id.startswith('M'))

    def test_mixed_member_creation(self):
        """Test creating both individual and organization members."""
        # Create individual
        individual = self.Partner.create({
            'first_name': 'John',
            'last_name': 'Doe',
            'member_type_id': self.individual_type.id,
            'is_company': False,
        })
        
        # Create organization
        organization = self.Partner.create({
            'name': 'Acme Corp',
            'member_type_id': self.org_type.id,
            'is_company': True,
            'acronym': 'ACME',
        })
        
        # Both should have different characteristics
        self.assertFalse(individual.is_company)
        self.assertTrue(individual.member_type_id.is_individual)
        
        self.assertEqual(organization.name, 'Acme Corp')
        self.assertEqual(organization.acronym, 'ACME')
        self.assertTrue(organization.is_company)
        self.assertTrue(organization.member_type_id.is_organization)

    def test_name_onchange_for_individuals(self):
        """Test that name onchange works properly for individuals."""
        individual = self.Partner.create({
            'member_type_id': self.individual_type.id,
            'is_company': False,
            'first_name': 'Test',
            'last_name': 'User',
        })
        
        # Trigger onchange
        individual._onchange_name_components()
        self.assertEqual(individual.name, 'Test User')
        
        # Update components
        individual.middle_name = 'Middle'
        individual._onchange_name_components()
        self.assertEqual(individual.name, 'Test Middle User')