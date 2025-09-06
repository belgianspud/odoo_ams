# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestAMSMemberType(TransactionCase):
    """Test cases for AMS Member Type model."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.member_type_model = self.env['ams.member.type']
        
    def test_member_type_creation(self):
        """Test basic member type creation."""
        member_type = self.member_type_model.create({
            'name': 'Test Member Type',
            'code': 'TEST',
            'is_individual': True,
            'is_organization': False,
        })
        
        self.assertEqual(member_type.name, 'Test Member Type')
        self.assertEqual(member_type.code, 'TEST')
        self.assertTrue(member_type.is_individual)
        self.assertFalse(member_type.is_organization)
        self.assertTrue(member_type.active)
        self.assertTrue(member_type.auto_approve)

    def test_code_auto_generation(self):
        """Test automatic code generation from name."""
        member_type = self.member_type_model.new({
            'name': 'Student Member'
        })
        member_type._onchange_name()
        
        self.assertEqual(member_type.code, 'STUDENT_MEMBER')

    def test_unique_constraints(self):
        """Test unique constraints on code and name."""
        self.member_type_model.create({
            'name': 'Test Type',
            'code': 'TEST',
            'is_individual': True,
        })
        
        # Test duplicate code
        with self.assertRaises(Exception):
            self.member_type_model.create({
                'name': 'Another Type',
                'code': 'TEST',
                'is_individual': True,
            })
        
        # Test duplicate name
        with self.assertRaises(Exception):
            self.member_type_model.create({
                'name': 'Test Type',
                'code': 'ANOTHER',
                'is_individual': True,
            })

    def test_age_range_validation(self):
        """Test age range validation."""
        # Valid age range
        member_type = self.member_type_model.create({
            'name': 'Valid Age Range',
            'code': 'VALID',
            'is_individual': True,
            'min_age': 18,
            'max_age': 65,
        })
        self.assertTrue(member_type.check_age_eligibility(25))
        self.assertFalse(member_type.check_age_eligibility(17))
        self.assertFalse(member_type.check_age_eligibility(66))
        
        # Invalid age range (min > max)
        with self.assertRaises(ValidationError):
            self.member_type_model.create({
                'name': 'Invalid Age Range',
                'code': 'INVALID',
                'is_individual': True,
                'min_age': 65,
                'max_age': 18,
            })

    def test_classification_validation(self):
        """Test member classification validation."""
        # Must be available for individuals or organizations
        with self.assertRaises(ValidationError):
            self.member_type_model.create({
                'name': 'No Classification',
                'code': 'NONE',
                'is_individual': False,
                'is_organization': False,
            })

    def test_code_format_validation(self):
        """Test code format validation."""
        # Valid code
        member_type = self.member_type_model.create({
            'name': 'Valid Code',
            'code': 'VALID_CODE-123',
            'is_individual': True,
        })
        self.assertEqual(member_type.code, 'VALID_CODE-123')
        
        # Invalid code (special characters)
        with self.assertRaises(ValidationError):
            self.member_type_model.create({
                'name': 'Invalid Code',
                'code': 'INVALID@CODE!',
                'is_individual': True,
            })
        
        # Invalid code (too long)
        with self.assertRaises(ValidationError):
            self.member_type_model.create({
                'name': 'Long Code',
                'code': 'THIS_CODE_IS_TOO_LONG_FOR_VALIDATION',
                'is_individual': True,
            })

    def test_approval_logic_validation(self):
        """Test approval and verification logic validation."""
        # Cannot have both auto-approve and requires verification
        with self.assertRaises(ValidationError):
            self.member_type_model.create({
                'name': 'Conflicting Logic',
                'code': 'CONFLICT',
                'is_individual': True,
                'auto_approve': True,
                'requires_verification': True,
            })

    def test_onchange_methods(self):
        """Test onchange method behaviors."""
        member_type = self.member_type_model.new({
            'requires_verification': True,
            'auto_approve': True,
        })
        
        # Test verification requirement onchange
        member_type._onchange_requires_verification()
        self.assertFalse(member_type.auto_approve)
        
        # Test auto-approve onchange
        member_type.auto_approve = True
        member_type._onchange_auto_approve()
        self.assertFalse(member_type.requires_verification)

    def test_get_available_types(self):
        """Test getting available member types."""
        # Create test types
        individual_type = self.member_type_model.create({
            'name': 'Individual Type',
            'code': 'IND',
            'is_individual': True,
            'is_organization': False,
            'min_age': 18,
            'max_age': 65,
        })
        
        org_type = self.member_type_model.create({
            'name': 'Organization Type',
            'code': 'ORG',
            'is_individual': False,
            'is_organization': True,
        })
        
        # Test filtering by classification
        individual_types = self.member_type_model.get_available_types(is_individual=True)
        self.assertIn(individual_type, individual_types)
        self.assertNotIn(org_type, individual_types)
        
        # Test filtering by age
        age_eligible = self.member_type_model.get_available_types(is_individual=True, age=25)
        self.assertIn(individual_type, age_eligible)
        
        age_ineligible = self.member_type_model.get_available_types(is_individual=True, age=70)
        self.assertNotIn(individual_type, age_ineligible)

    def test_eligibility_message(self):
        """Test eligibility message generation."""
        member_type = self.member_type_model.create({
            'name': 'Test Type',
            'code': 'TEST',
            'is_individual': True,
            'min_age': 18,
            'max_age': 65,
            'requires_verification': True,
        })
        
        message = member_type.get_eligibility_message()
        self.assertIn('Ages 18-65', message)
        self.assertIn('Individuals', message)
        self.assertIn('verification', message.lower())


class TestAMSMemberStatus(TransactionCase):
    """Test cases for AMS Member Status model."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.member_status_model = self.env['ams.member.status']

    def test_member_status_creation(self):
        """Test basic member status creation."""
        status = self.member_status_model.create({
            'name': 'Test Status',
            'code': 'TEST',
            'sequence': 10,
        })
        
        self.assertEqual(status.name, 'Test Status')
        self.assertEqual(status.code, 'TEST')
        self.assertEqual(status.sequence, 10)
        self.assertTrue(status.is_active)
        self.assertTrue(status.can_renew)
        self.assertTrue(status.can_purchase)

    def test_code_auto_generation(self):
        """Test automatic code generation from name."""
        status = self.member_status_model.new({
            'name': 'Active Member'
        })
        status._onchange_name()
        
        self.assertEqual(status.code, 'ACTIVE_MEMBER')

    def test_unique_constraints(self):
        """Test unique constraints on code and name."""
        self.member_status_model.create({
            'name': 'Test Status',
            'code': 'TEST',
            'sequence': 10,
        })
        
        # Test duplicate code
        with self.assertRaises(Exception):
            self.member_status_model.create({
                'name': 'Another Status',
                'code': 'TEST',
                'sequence': 20,
            })

    def test_auto_transition_validation(self):
        """Test auto-transition validation."""
        # Create target status first
        target_status = self.member_status_model.create({
            'name': 'Target Status',
            'code': 'TARGET',
            'sequence': 20,
        })
        
        # Valid auto-transition
        status = self.member_status_model.create({
            'name': 'Source Status',
            'code': 'SOURCE',
            'sequence': 10,
            'auto_transition_days': 30,
            'next_status_id': target_status.id,
        })
        self.assertEqual(status.auto_transition_days, 30)
        
        # Invalid: auto-transition days without next status
        with self.assertRaises(ValidationError):
            self.member_status_model.create({
                'name': 'Invalid Transition',
                'code': 'INVALID',
                'sequence': 15,
                'auto_transition_days': 30,
            })

    def test_circular_transition_validation(self):
        """Test circular transition prevention."""
        status1 = self.member_status_model.create({
            'name': 'Status 1',
            'code': 'STATUS1',
            'sequence': 10,
        })
        
        status2 = self.member_status_model.create({
            'name': 'Status 2',
            'code': 'STATUS2',
            'sequence': 20,
            'auto_transition_days': 30,
            'next_status_id': status1.id,
        })
        
        # This should create a circular reference and raise validation error
        with self.assertRaises(ValidationError):
            status1.write({
                'auto_transition_days': 30,
                'next_status_id': status2.id,
            })

    def test_status_consistency_validation(self):
        """Test status flag consistency validation."""
        # Active status cannot be suspended
        with self.assertRaises(ValidationError):
            self.member_status_model.create({
                'name': 'Inconsistent Status',
                'code': 'INCONSISTENT',
                'sequence': 10,
                'is_active': True,
                'is_suspended': True,
            })
        
        # Status cannot be both suspended and terminated
        with self.assertRaises(ValidationError):
            self.member_status_model.create({
                'name': 'Double Status',
                'code': 'DOUBLE',
                'sequence': 10,
                'is_suspended': True,
                'is_terminated': True,
            })

    def test_onchange_methods(self):
        """Test onchange method behaviors."""
        status = self.member_status_model.new({
            'is_suspended': True,
        })
        
        # Test suspended status onchange
        status._onchange_status_flags()
        self.assertFalse(status.is_active)
        self.assertFalse(status.can_renew)
        self.assertFalse(status.allows_portal_access)
        
        # Test terminated status onchange
        status = self.member_status_model.new({
            'is_terminated': True,
        })
        status._onchange_status_flags()
        self.assertFalse(status.is_active)
        self.assertFalse(status.can_renew)
        self.assertFalse(status.can_purchase)

    def test_transition_validation(self):
        """Test status transition validation."""
        active_status = self.member_status_model.create({
            'name': 'Active',
            'code': 'ACTIVE',
            'sequence': 20,
            'is_active': True,
        })
        
        suspended_status = self.member_status_model.create({
            'name': 'Suspended',
            'code': 'SUSPENDED',
            'sequence': 50,
            'is_suspended': True,
            'requires_approval': True,
        })
        
        # Test valid transition
        self.assertTrue(active_status.can_transition_to(suspended_status))
        
        # Test invalid transition (to same status)
        self.assertFalse(active_status.can_transition_to(active_status))

    def test_get_statuses_methods(self):
        """Test utility methods for getting specific statuses."""
        # Create test statuses
        active_status = self.member_status_model.create({
            'name': 'Active',
            'code': 'ACTIVE',
            'sequence': 20,
            'is_active': True,
            'can_renew': True,
        })
        
        inactive_status = self.member_status_model.create({
            'name': 'Inactive',
            'code': 'INACTIVE',
            'sequence': 30,
            'is_active': False,
            'can_renew': False,
        })
        
        # Test get_active_statuses
        active_statuses = self.member_status_model.get_active_statuses()
        self.assertIn(active_status, active_statuses)
        self.assertNotIn(inactive_status, active_statuses)
        
        # Test get_renewable_statuses
        renewable_statuses = self.member_status_model.get_renewable_statuses()
        self.assertIn(active_status, renewable_statuses)
        self.assertNotIn(inactive_status, renewable_statuses)

    def test_sequence_auto_assignment(self):
        """Test automatic sequence assignment."""
        status1 = self.member_status_model.create({
            'name': 'First Status',
            'code': 'FIRST',
        })
        
        status2 = self.member_status_model.create({
            'name': 'Second Status',
            'code': 'SECOND',
        })
        
        # Second status should have higher sequence
        self.assertGreater(status2.sequence, status1.sequence)

    def test_name_get(self):
        """Test custom name display."""
        status = self.member_status_model.create({
            'name': 'Test Status',
            'code': 'TEST',
            'sequence': 10,
            'is_active': False,
        })
        
        name_get_result = status.name_get()[0][1]
        self.assertIn('[TEST]', name_get_result)
        self.assertIn('Test Status', name_get_result)
        self.assertIn('(Inactive)', name_get_result)

    def tearDown(self):
        """Clean up after tests."""
        super().tearDown()