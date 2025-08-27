"""Test cases for AMS Member Types functionality."""

from odoo.tests import common
from odoo.exceptions import ValidationError


class TestAMSMemberTypes(common.TransactionCase):
    """Test AMS Member Types model."""

    def setUp(self):
        super().setUp()
        self.MemberType = self.env['ams.member.type']

    def test_create_individual_member_type(self):
        """Test creating an individual member type."""
        member_type = self.MemberType.create({
            'name': 'Professional',
            'code': 'PROF',
            'is_individual': True,
            'is_organization': False,
            'description': 'Professional individual membership',
        })
        
        self.assertTrue(member_type.id)
        self.assertEqual(member_type.name, 'Professional')
        self.assertEqual(member_type.code, 'PROF')
        self.assertTrue(member_type.is_individual)
        self.assertFalse(member_type.is_organization)
        self.assertTrue(member_type.active)

    def test_create_organization_member_type(self):
        """Test creating an organization member type."""
        member_type = self.MemberType.create({
            'name': 'Corporate Plus',
            'code': 'CORP_PLUS',
            'is_individual': False,
            'is_organization': True,
            'description': 'Premium corporate membership',
        })
        
        self.assertTrue(member_type.id)
        self.assertEqual(member_type.name, 'Corporate Plus')
        self.assertEqual(member_type.code, 'CORP_PLUS')
        self.assertFalse(member_type.is_individual)
        self.assertTrue(member_type.is_organization)

    def test_unique_constraints(self):
        """Test that code and name must be unique."""
        # Create first member type
        self.MemberType.create({
            'name': 'Test Type',
            'code': 'TEST',
            'is_individual': True,
            'is_organization': False,
        })
        
        # Try to create duplicate code
        with self.assertRaises(Exception):
            self.MemberType.create({
                'name': 'Different Name',
                'code': 'TEST',  # Duplicate code
                'is_individual': True,
                'is_organization': False,
            })
        
        # Try to create duplicate name
        with self.assertRaises(Exception):
            self.MemberType.create({
                'name': 'Test Type',  # Duplicate name
                'code': 'DIFF',
                'is_individual': True,
                'is_organization': False,
            })

    def test_type_flags_validation(self):
        """Test that exactly one type flag must be set."""
        # Test no flags set
        with self.assertRaises(ValidationError):
            self.MemberType.create({
                'name': 'Invalid Type',
                'code': 'INVALID',
                'is_individual': False,
                'is_organization': False,
            })
        
        # Test both flags set
        with self.assertRaises(ValidationError):
            self.MemberType.create({
                'name': 'Invalid Type',
                'code': 'INVALID2',
                'is_individual': True,
                'is_organization': True,
            })

    def test_member_count_computation(self):
        """Test that member count is computed correctly."""
        # Create member type
        member_type = self.MemberType.create({
            'name': 'Test Individual',
            'code': 'TEST_IND',
            'is_individual': True,
            'is_organization': False,
        })
        
        # Initially should be 0
        self.assertEqual(member_type.member_count, 0)
        
        # Create a member with this type
        self.env['res.partner'].create({
            'name': 'Test Member',
            'member_type_id': member_type.id,
            'is_company': False,
        })
        
        # Recompute and check
        member_type._compute_member_count()
        self.assertEqual(member_type.member_count, 1)

    def test_name_get(self):
        """Test custom name_get method."""
        member_type = self.MemberType.create({
            'name': 'Student Member',
            'code': 'STU',
            'is_individual': True,
            'is_organization': False,
        })
        
        name_get_result = member_type.name_get()
        self.assertEqual(name_get_result[0][1], '[STU] Student Member')

    def test_sequence_ordering(self):
        """Test that member types are ordered by sequence."""
        type1 = self.MemberType.create({
            'name': 'Type 1',
            'code': 'TYPE1',
            'is_individual': True,
            'is_organization': False,
            'sequence': 20,
        })
        
        type2 = self.MemberType.create({
            'name': 'Type 2', 
            'code': 'TYPE2',
            'is_individual': True,
            'is_organization': False,
            'sequence': 10,
        })
        
        # Search ordered by sequence
        types = self.MemberType.search([
            ('id', 'in', [type1.id, type2.id])
        ], order='sequence, name')
        
        self.assertEqual(types[0], type2)  # Lower sequence first
        self.assertEqual(types[1], type1)

    def test_default_data_loaded(self):
        """Test that default member types are created."""
        # Check for default individual types
        individual_type = self.MemberType.search([('code', '=', 'IND')], limit=1)
        self.assertTrue(individual_type)
        self.assertEqual(individual_type.name, 'Individual')
        self.assertTrue(individual_type.is_individual)
        
        student_type = self.MemberType.search([('code', '=', 'STU')], limit=1)
        self.assertTrue(student_type)
        self.assertEqual(student_type.name, 'Student')
        self.assertTrue(student_type.is_individual)
        
        # Check for default organization types
        org_type = self.MemberType.search([('code', '=', 'ORG')], limit=1)
        self.assertTrue(org_type)
        self.assertEqual(org_type.name, 'Organization')
        self.assertTrue(org_type.is_organization)
        
        corp_type = self.MemberType.search([('code', '=', 'CORP')], limit=1)
        self.assertTrue(corp_type)
        self.assertEqual(corp_type.name, 'Corporate')
        self.assertTrue(corp_type.is_organization)


class TestAMSMemberStatus(common.TransactionCase):
    """Test AMS Member Status model."""

    def setUp(self):
        super().setUp()
        self.MemberStatus = self.env['ams.member.status']

    def test_create_member_status(self):
        """Test creating a member status."""
        status = self.MemberStatus.create({
            'name': 'Pending',
            'code': 'pending',
            'is_active': False,
            'sequence': 15,
            'color': 3,
            'description': 'Application pending review',
        })
        
        self.assertTrue(status.id)
        self.assertEqual(status.name, 'Pending')
        self.assertEqual(status.code, 'pending')
        self.assertFalse(status.is_active)
        self.assertEqual(status.sequence, 15)
        self.assertEqual(status.color, 3)

    def test_color_validation(self):
        """Test color range validation."""
        # Valid color
        status = self.MemberStatus.create({
            'name': 'Test Status',
            'code': 'test',
            'is_active': False,
            'sequence': 10,
            'color': 5,  # Valid color
        })
        self.assertEqual(status.color, 5)
        
        # Invalid color - too high
        with self.assertRaises(ValidationError):
            self.MemberStatus.create({
                'name': 'Invalid Status',
                'code': 'invalid',
                'is_active': False,
                'sequence': 10,
                'color': 15,  # Invalid - too high
            })
        
        # Invalid color - negative
        with self.assertRaises(ValidationError):
            self.MemberStatus.create({
                'name': 'Invalid Status 2',
                'code': 'invalid2',
                'is_active': False,
                'sequence': 10,
                'color': -1,  # Invalid - negative
            })

    def test_helper_methods(self):
        """Test helper methods for getting specific statuses."""
        # Test get_active_statuses
        active_statuses = self.MemberStatus.get_active_statuses()
        self.assertTrue(len(active_statuses) >= 1)
        for status in active_statuses:
            self.assertTrue(status.is_active)
        
        # Test get_default_prospect_status
        prospect_status = self.MemberStatus.get_default_prospect_status()
        if prospect_status:
            self.assertEqual(prospect_status.code, 'prospect')
        
        # Test get_default_active_status
        active_status = self.MemberStatus.get_default_active_status()
        if active_status:
            self.assertEqual(active_status.code, 'active')

    def test_default_data_loaded(self):
        """Test that default member statuses are created.""" 
        # Check for default statuses
        prospect = self.MemberStatus.search([('code', '=', 'prospect')], limit=1)
        self.assertTrue(prospect)
        self.assertEqual(prospect.name, 'Prospect')
        self.assertFalse(prospect.is_active)
        
        active = self.MemberStatus.search([('code', '=', 'active')], limit=1)
        self.assertTrue(active)
        self.assertEqual(active.name, 'Active')
        self.assertTrue(active.is_active)
        
        grace = self.MemberStatus.search([('code', '=', 'grace')], limit=1)
        self.assertTrue(grace)
        self.assertEqual(grace.name, 'Grace')
        self.assertTrue(grace.is_active)  # Grace period still counts as active
        
        lapsed = self.MemberStatus.search([('code', '=', 'lapsed')], limit=1)
        self.assertTrue(lapsed)
        self.assertEqual(lapsed.name, 'Lapsed')
        self.assertFalse(lapsed.is_active)