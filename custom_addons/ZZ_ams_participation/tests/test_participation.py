"""Test cases for AMS Participation functionality."""

from datetime import date, timedelta
from odoo.tests import common
from odoo.exceptions import ValidationError, UserError


class TestAMSParticipation(common.TransactionCase):
    """Test AMS Participation model and functionality."""

    def setUp(self):
        super().setUp()
        self.Participation = self.env['ams.participation']
        self.Partner = self.env['res.partner']
        self.MemberType = self.env['ams.member.type']
        self.MemberStatus = self.env['ams.member.status']
        self.CancellationReason = self.env['ams.cancellation.reason']
        
        # Create test member types
        self.individual_type = self.MemberType.create({
            'name': 'Test Individual',
            'code': 'TEST_IND',
            'is_individual': True,
            'is_organization': False,
        })
        
        self.org_type = self.MemberType.create({
            'name': 'Test Organization',
            'code': 'TEST_ORG',
            'is_individual': False,
            'is_organization': True,
        })
        
        # Create test member status
        self.active_status = self.MemberStatus.create({
            'name': 'Test Active',
            'code': 'test_active',
            'is_active': True,
            'sequence': 20,
        })
        
        # Create test members
        self.individual_member = self.Partner.create({
            'name': 'John Test Member',
            'member_type_id': self.individual_type.id,
            'member_status_id': self.active_status.id,
            'is_company': False,
        })
        
        self.organization_member = self.Partner.create({
            'name': 'Test Corporation',
            'member_type_id': self.org_type.id,
            'member_status_id': self.active_status.id,
            'is_company': True,
        })
        
        # Create test cancellation reason
        self.cancellation_reason = self.CancellationReason.create({
            'name': 'Test Cancellation',
            'code': 'TEST_CANCEL',
            'category': 'voluntary',
        })

    def test_create_individual_participation(self):
        """Test creating a participation for an individual member."""
        participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'prospect',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=365),
        })
        
        self.assertTrue(participation.id)
        self.assertEqual(participation.partner_id, self.individual_member)
        self.assertEqual(participation.participation_type, 'membership')
        self.assertEqual(participation.status, 'prospect')
        self.assertFalse(participation.company_id)

    def test_create_organization_participation(self):
        """Test creating a participation for an organization member."""
        participation = self.Participation.create({
            'company_id': self.organization_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=365),
        })
        
        self.assertTrue(participation.id)
        self.assertEqual(participation.company_id, self.organization_member)
        self.assertEqual(participation.participation_type, 'membership')
        self.assertEqual(participation.status, 'active')
        self.assertFalse(participation.partner_id)

    def test_member_assignment_constraints(self):
        """Test that participation must be assigned to either individual or organization."""
        # Test no member assigned
        with self.assertRaises(ValidationError):
            self.Participation.create({
                'participation_type': 'membership',
                'status': 'prospect',
                'join_date': date.today(),
                'begin_date': date.today(),
                'end_date': date.today() + timedelta(days=365),
                'bill_through_date': date.today() + timedelta(days=365),
                'paid_through_date': date.today() + timedelta(days=365),
            })
        
        # Test both members assigned
        with self.assertRaises(ValidationError):
            self.Participation.create({
                'partner_id': self.individual_member.id,
                'company_id': self.organization_member.id,
                'participation_type': 'membership',
                'status': 'prospect',
                'join_date': date.today(),
                'begin_date': date.today(),
                'end_date': date.today() + timedelta(days=365),
                'bill_through_date': date.today() + timedelta(days=365),
                'paid_through_date': date.today() + timedelta(days=365),
            })

    def test_date_validations(self):
        """Test date field validations.""" 
        # Test begin date after end date
        with self.assertRaises(ValidationError):
            self.Participation.create({
                'partner_id': self.individual_member.id,
                'participation_type': 'membership',
                'status': 'prospect',
                'join_date': date.today(),
                'begin_date': date.today() + timedelta(days=10),
                'end_date': date.today(),  # End before begin
                'bill_through_date': date.today() + timedelta(days=365),
                'paid_through_date': date.today() + timedelta(days=365),
            })
        
        # Test join date after begin date
        with self.assertRaises(ValidationError):
            self.Participation.create({
                'partner_id': self.individual_member.id,
                'participation_type': 'membership',
                'status': 'prospect',
                'join_date': date.today() + timedelta(days=10),  # Join after begin
                'begin_date': date.today(),
                'end_date': date.today() + timedelta(days=365),
                'bill_through_date': date.today() + timedelta(days=365),
                'paid_through_date': date.today() + timedelta(days=365),
            })

    def test_computed_fields(self):
        """Test computed fields calculations."""
        participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=30),
            'bill_through_date': date.today() + timedelta(days=30),
            'paid_through_date': date.today() + timedelta(days=30),
        })
        
        # Test display name
        self.assertIn(self.individual_member.name, participation.display_name)
        self.assertIn('Membership', participation.display_name)
        
        # Test member display name
        self.assertEqual(participation.member_display_name, self.individual_member.name)
        
        # Test days remaining
        self.assertEqual(participation.days_remaining, 30)
        
        # Test is_expired (should be False since paid through date is in future)
        self.assertFalse(participation.is_expired)
        
        # Test is_renewable
        self.assertTrue(participation.is_renewable)  # Active status is renewable

    def test_status_transitions(self):
        """Test participation status transitions."""
        participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'prospect',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=365),
        })
        
        # Test valid transition: prospect -> active
        participation.update_participation_status('active', reason='Payment received')
        self.assertEqual(participation.status, 'active')
        
        # Test valid transition: active -> grace
        participation.update_participation_status('grace', reason='Payment expired')
        self.assertEqual(participation.status, 'grace')
        self.assertTrue(participation.grace_period_end_date)
        
        # Test valid transition: grace -> cancelled
        participation.update_participation_status('cancelled', reason='Member request')
        self.assertEqual(participation.status, 'cancelled')
        self.assertTrue(participation.terminated_date)

    def test_invalid_status_transitions(self):
        """Test that invalid status transitions are blocked."""
        participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'terminated',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=365),
        })
        
        # Test invalid transition: terminated -> active (terminated is terminal)
        with self.assertRaises(ValidationError):
            participation.update_participation_status('active', reason='Invalid transition')

    def test_participation_history_creation(self):
        """Test that history records are created for status changes."""
        participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'prospect',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=365),
        })
        
        # Initially no history (just creation)
        initial_history_count = len(participation.history_ids)
        
        # Change status
        participation.update_participation_status('active', reason='Test transition')
        
        # Should have one more history record
        self.assertEqual(len(participation.history_ids), initial_history_count + 1)
        
        # Check history record details
        latest_history = participation.history_ids[0]  # Most recent first
        self.assertEqual(latest_history.old_status, 'prospect')
        self.assertEqual(latest_history.new_status, 'active')
        self.assertEqual(latest_history.reason, 'Test transition')
        self.assertEqual(latest_history.participation_id, participation)

    def test_action_methods(self):
        """Test participation action methods."""
        # Test activation action
        participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'prospect',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=365),
        })
        
        # Test activate action
        participation.action_activate()
        self.assertEqual(participation.status, 'active')
        
        # Test suspend action
        participation.action_suspend()
        self.assertEqual(participation.status, 'suspended')
        self.assertTrue(participation.suspend_end_date)
        
        # Test cancel action
        participation.action_cancel()
        self.assertEqual(participation.status, 'cancelled')

    def test_action_method_constraints(self):
        """Test that action methods have proper constraints."""
        participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=365),
        })
        
        # Test that activate only works on prospects
        with self.assertRaises(UserError):
            participation.action_activate()  # Already active

    def test_cancellation_reason_constraint(self):
        """Test cancellation reason can only be set for cancelled/terminated participations."""
        participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=365),
        })
        
        # Test that cancellation reason cannot be set for active participation
        with self.assertRaises(ValidationError):
            participation.cancellation_reason_id = self.cancellation_reason.id

    def test_automated_lifecycle_processing(self):
        """Test automated participation lifecycle processing."""
        # Create expired participation
        expired_participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': date.today() - timedelta(days=400),
            'begin_date': date.today() - timedelta(days=400),
            'end_date': date.today() + timedelta(days=300),
            'bill_through_date': date.today() + timedelta(days=300),
            'paid_through_date': date.today() - timedelta(days=1),  # Expired yesterday
        })
        
        # Run automated processing
        self.Participation.process_participation_lifecycle()
        
        # Should move to grace status
        self.assertEqual(expired_participation.status, 'grace')
        self.assertTrue(expired_participation.grace_period_end_date)

    def test_get_active_participations(self):
        """Test get_active_participations method."""
        # Create various participations
        active_participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=365),
        })
        
        grace_participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'chapter',
            'status': 'grace',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=365),
        })
        
        cancelled_participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'committee_position',
            'status': 'cancelled',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=365),
        })
        
        # Get active participations
        active_participations = self.Participation.get_active_participations()
        
        # Should include active and grace, but not cancelled
        self.assertIn(active_participation, active_participations)
        self.assertIn(grace_participation, active_participations)
        self.assertNotIn(cancelled_participation, active_participations)

    def test_get_expiring_participations(self):
        """Test get_expiring_participations method."""
        # Create participation expiring in 15 days
        expiring_participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=15),
        })
        
        # Create participation expiring in 60 days
        future_participation = self.Participation.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=60),
        })
        
        # Get participations expiring within 30 days
        expiring_participations = self.Participation.get_expiring_participations(30)
        
        # Should include the 15-day one, but not the 60-day one
        self.assertIn(expiring_participation, expiring_participations)
        self.assertNotIn(future_participation, expiring_participations)


class TestAMSCancellationReason(common.TransactionCase):
    """Test AMS Cancellation Reason model."""

    def setUp(self):
        super().setUp()
        self.CancellationReason = self.env['ams.cancellation.reason']

    def test_create_cancellation_reason(self):
        """Test creating a cancellation reason."""
        reason = self.CancellationReason.create({
            'name': 'Test Reason',
            'code': 'TEST_REASON',
            'category': 'voluntary',
            'description': 'Test cancellation reason',
        })
        
        self.assertTrue(reason.id)
        self.assertEqual(reason.name, 'Test Reason')
        self.assertEqual(reason.code, 'TEST_REASON')
        self.assertEqual(reason.category, 'voluntary')

    def test_code_format_validation(self):
        """Test code format validation."""
        # Valid code
        reason = self.CancellationReason.create({
            'name': 'Valid Code',
            'code': 'VALID_CODE',
            'category': 'voluntary',
        })
        self.assertEqual(reason.code, 'VALID_CODE')
        
        # Invalid code - lowercase
        with self.assertRaises(ValidationError):
            self.CancellationReason.create({
                'name': 'Invalid Code',
                'code': 'invalid_code',
                'category': 'voluntary',
            })
        
        # Invalid code - spaces
        with self.assertRaises(ValidationError):
            self.CancellationReason.create({
                'name': 'Invalid Code',
                'code': 'INVALID CODE',
                'category': 'voluntary',
            })

    def test_helper_methods(self):
        """Test helper methods for getting reasons by category."""
        # Create reasons in different categories
        voluntary = self.CancellationReason.create({
            'name': 'Voluntary Reason',
            'code': 'VOLUNTARY',
            'category': 'voluntary',
        })
        
        involuntary = self.CancellationReason.create({
            'name': 'Involuntary Reason',
            'code': 'INVOLUNTARY',
            'category': 'involuntary',
        })
        
        administrative = self.CancellationReason.create({
            'name': 'Administrative Reason',
            'code': 'ADMINISTRATIVE',
            'category': 'administrative',
        })
        
        # Test category-specific methods
        voluntary_reasons = self.CancellationReason.get_voluntary_reasons()
        self.assertIn(voluntary, voluntary_reasons)
        self.assertNotIn(involuntary, voluntary_reasons)
        
        involuntary_reasons = self.CancellationReason.get_involuntary_reasons()
        self.assertIn(involuntary, involuntary_reasons)
        self.assertNotIn(voluntary, involuntary_reasons)
        
        administrative_reasons = self.CancellationReason.get_administrative_reasons()
        self.assertIn(administrative, administrative_reasons)
        self.assertNotIn(voluntary, administrative_reasons)

    def test_usage_count_computation(self):
        """Test that usage count is computed correctly."""
        reason = self.CancellationReason.create({
            'name': 'Usage Test',
            'code': 'USAGE_TEST',
            'category': 'voluntary',
        })
        
        # Initially should be 0
        self.assertEqual(reason.usage_count, 0)


class TestAMSParticipationHistory(common.TransactionCase):
    """Test AMS Participation History model."""

    def setUp(self):
        super().setUp()
        self.ParticipationHistory = self.env['ams.participation.history']
        self.Partner = self.env['res.partner']
        self.MemberType = self.env['ams.member.type']
        self.Participation = self.env['ams.participation']
        
        # Create test data
        self.member_type = self.MemberType.create({
            'name': 'Test Type',
            'code': 'TEST',
            'is_individual': True,
            'is_organization': False,
        })
        
        self.member = self.Partner.create({
            'name': 'Test Member',
            'member_type_id': self.member_type.id,
            'is_company': False,
        })
        
        self.participation = self.Participation.create({
            'partner_id': self.member.id,
            'participation_type': 'membership',
            'status': 'prospect',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'bill_through_date': date.today() + timedelta(days=365),
            'paid_through_date': date.today() + timedelta(days=365),
        })

    def test_create_history_entry(self):
        """Test creating a history entry."""
        history = self.ParticipationHistory.create({
            'participation_id': self.participation.id,
            'old_status': 'prospect',
            'new_status': 'active',
            'reason': 'Payment received',
        })
        
        self.assertTrue(history.id)
        self.assertEqual(history.participation_id, self.participation)
        self.assertEqual(history.old_status, 'prospect')
        self.assertEqual(history.new_status, 'active')
        self.assertEqual(history.reason, 'Payment received')

    def test_status_change_validation(self):
        """Test that status must actually change."""
        with self.assertRaises(ValidationError):
            self.ParticipationHistory.create({
                'participation_id': self.participation.id,
                'old_status': 'prospect',
                'new_status': 'prospect',  # Same status
                'reason': 'No change',
            })

    def test_computed_display_fields(self):
        """Test computed display fields."""
        history = self.ParticipationHistory.create({
            'participation_id': self.participation.id,
            'old_status': 'prospect',
            'new_status': 'active',
            'reason': 'Payment received',
        })
        
        # Test status change description
        self.assertIn('Prospect', history.status_change_description)
        self.assertIn('Active', history.status_change_description)
        self.assertIn('→', history.status_change_description)
        
        # Test display name includes member name and change info
        self.assertIn(self.member.name, history.display_name)
        self.assertIn('prospect', history.display_name)
        self.assertIn('active', history.display_name)

    def test_helper_method_create_history_entry(self):
        """Test helper method for creating history entries."""
        history = self.ParticipationHistory.create_history_entry(
            self.participation, 'prospect', 'active', 'Test reason'
        )
        
        self.assertTrue(history.id)
        self.assertEqual(history.participation_id, self.participation)
        self.assertEqual(history.old_status, 'prospect')
        self.assertEqual(history.new_status, 'active')
        self.assertEqual(history.reason, 'Test reason')
        
        # Test that helper method prevents same status
        result = self.ParticipationHistory.create_history_entry(
            self.participation, 'active', 'active', 'No change'
        )
        self.assertFalse(result)  # Should return False for same status