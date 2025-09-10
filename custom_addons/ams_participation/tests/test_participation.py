# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta, datetime
from unittest.mock import patch


class TestAMSParticipation(TransactionCase):
    """Test cases for AMS Participation model."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Get models
        self.participation_model = self.env['ams.participation']
        self.history_model = self.env['ams.participation.history']
        self.cancellation_reason_model = self.env['ams.cancellation.reason']
        self.subscription_product_model = self.env['ams.subscription.product']
        self.committee_position_model = self.env['ams.committee.position']
        
        # Create test partners
        self.individual_member = self.env['res.partner'].create({
            'name': 'John Smith',
            'email': 'john.smith@example.com',
            'is_company': False,
            'is_member': True,
            'membership_status': 'active',
            'member_since': date.today() - timedelta(days=365),
        })
        
        self.organization_member = self.env['res.partner'].create({
            'name': 'Acme Corporation',
            'email': 'info@acme.com',
            'is_company': True,
            'is_member': True,
            'membership_status': 'active',
            'member_since': date.today() - timedelta(days=730),
        })
        
        self.employee_contact = self.env['res.partner'].create({
            'name': 'Jane Doe',
            'email': 'jane.doe@acme.com',
            'is_company': False,
            'parent_id': self.organization_member.id,
            'is_member': False,
        })
        
        # Create test subscription product
        self.membership_product = self.subscription_product_model.create({
            'name': 'Annual Membership',
            'code': 'ANNUAL_MEMB',
            'product_type': 'membership',
            'list_price': 250.00,
            'term_length': 365,
            'is_renewable': True,
            'is_membership_product': True,
        })
        
        # Create test committee position
        self.committee_position = self.committee_position_model.create({
            'name': 'Chairman',
            'code': 'BOARD_CHAIR',
            'committee_name': 'Board of Directors',
            'committee_type': 'board',
            'is_executive': True,
            'is_voting': True,
            'requires_election': True,
            'term_length_months': 24,
        })
        
        # Create test cancellation reason
        self.cancellation_reason = self.cancellation_reason_model.create({
            'name': 'Voluntary Withdrawal',
            'code': 'VOL_WITHDRAW',
            'category': 'voluntary',
            'applies_to_membership': True,
            'immediate_termination': False,
            'allows_refund': True,
        })

    def test_participation_creation_basic(self):
        """Test basic participation creation."""
        today = date.today()
        end_date = today + timedelta(days=365)
        
        participation = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': today,
            'begin_date': today,
            'end_date': end_date,
            'paid_through_date': end_date,
            'subscription_product_id': self.membership_product.id,
        })
        
        # Test basic fields
        self.assertEqual(participation.partner_id, self.individual_member)
        self.assertEqual(participation.participation_type, 'membership')
        self.assertEqual(participation.status, 'active')
        self.assertTrue(participation.active)
        
        # Test computed fields
        self.assertFalse(participation.is_company_participation)
        self.assertEqual(participation.relationship_context, 'direct')
        self.assertTrue(participation.display_name)
        
        # Test history creation
        history_records = self.history_model.search([('participation_id', '=', participation.id)])
        self.assertTrue(history_records)
        self.assertEqual(history_records[0].new_status, 'active')

    def test_participation_creation_with_company(self):
        """Test participation creation with company relationship."""
        today = date.today()
        
        participation = self.participation_model.create({
            'partner_id': self.employee_contact.id,
            'company_id': self.organization_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': today,
            'begin_date': today,
            'end_date': today + timedelta(days=365),
        })
        
        # Test company relationship
        self.assertEqual(participation.company_id, self.organization_member)
        self.assertEqual(participation.relationship_context, 'employee')
        self.assertFalse(participation.is_company_participation)

    def test_participation_date_defaults(self):
        """Test automatic date field defaults."""
        participation = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'prospect',
            # Don't set dates - test defaults
        })
        
        # Test that default dates are set
        self.assertTrue(participation.join_date)
        self.assertTrue(participation.begin_date)
        self.assertTrue(participation.end_date)
        self.assertEqual(participation.join_date, participation.begin_date)

    def test_single_active_membership_constraint(self):
        """Test that only one active membership is allowed per member."""
        today = date.today()
        
        # Create first active membership
        participation1 = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': today,
            'begin_date': today,
            'end_date': today + timedelta(days=365),
        })
        
        # Try to create second active membership - should fail
        with self.assertRaises(ValidationError):
            self.participation_model.create({
                'partner_id': self.individual_member.id,
                'participation_type': 'membership',
                'status': 'active',
                'join_date': today,
                'begin_date': today,
                'end_date': today + timedelta(days=365),
            })
        
        # But can create non-active membership
        participation2 = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'prospect',
            'join_date': today,
            'begin_date': today,
            'end_date': today + timedelta(days=365),
        })
        
        self.assertTrue(participation2)

    def test_multiple_chapter_participations_allowed(self):
        """Test that multiple active chapter participations are allowed."""
        today = date.today()
        
        # Create multiple active chapter participations
        participation1 = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'chapter',
            'status': 'active',
            'join_date': today,
            'begin_date': today,
            'end_date': today + timedelta(days=365),
        })
        
        participation2 = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'chapter',
            'status': 'active',
            'join_date': today,
            'begin_date': today,
            'end_date': today + timedelta(days=365),
        })
        
        # Both should be valid
        self.assertTrue(participation1)
        self.assertTrue(participation2)

    def test_committee_position_constraint(self):
        """Test committee position can only be set for committee participation."""
        today = date.today()
        
        # Valid committee participation with position
        participation = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'committee_position',
            'committee_position_id': self.committee_position.id,
            'status': 'active',
            'join_date': today,
            'begin_date': today,
            'end_date': today + timedelta(days=730),  # 2 years for board position
        })
        
        self.assertEqual(participation.committee_position_id, self.committee_position)
        
        # Invalid - committee position on non-committee participation
        with self.assertRaises(ValidationError):
            self.participation_model.create({
                'partner_id': self.individual_member.id,
                'participation_type': 'membership',
                'committee_position_id': self.committee_position.id,
                'status': 'active',
                'join_date': today,
                'begin_date': today,
                'end_date': today + timedelta(days=365),
            })

    def test_date_validation(self):
        """Test date field validation."""
        today = date.today()
        
        # Invalid - begin_date after end_date
        with self.assertRaises(ValidationError):
            self.participation_model.create({
                'partner_id': self.individual_member.id,
                'participation_type': 'membership',
                'status': 'active',
                'join_date': today,
                'begin_date': today + timedelta(days=30),
                'end_date': today,  # Before begin_date
            })

    def test_computed_fields(self):
        """Test computed field calculations."""
        today = date.today()
        paid_through = today + timedelta(days=30)
        
        participation = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': today,
            'begin_date': today,
            'end_date': today + timedelta(days=365),
            'paid_through_date': paid_through,
            'auto_pay': True,
        })
        
        # Test days_until_expiry
        self.assertEqual(participation.days_until_expiry, 30)
        
        # Test is_overdue (should be False since paid_through is in future)
        self.assertFalse(participation.is_overdue)
        
        # Test grace period computation
        self.assertTrue(participation.grace_period_end_date)
        expected_grace_end = paid_through + timedelta(days=30)  # Default grace period
        self.assertEqual(participation.grace_period_end_date, expected_grace_end)
        
        # Test can_auto_renew
        self.assertTrue(participation.can_auto_renew)

    def test_status_change_tracking(self):
        """Test that status changes are properly tracked."""
        participation = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'prospect',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
        })
        
        # Initial history record should exist
        initial_history = self.history_model.search([
            ('participation_id', '=', participation.id),
            ('new_status', '=', 'prospect')
        ])
        self.assertTrue(initial_history)
        
        # Change status and check history
        participation.with_context(
            status_change_reason='Test activation'
        ).status = 'active'
        
        activation_history = self.history_model.search([
            ('participation_id', '=', participation.id),
            ('old_status', '=', 'prospect'),
            ('new_status', '=', 'active')
        ])
        
        self.assertTrue(activation_history)
        self.assertEqual(activation_history.reason, 'Test activation')
        self.assertFalse(activation_history.automated)

    def test_status_change_side_effects(self):
        """Test side effects of status changes."""
        today = date.today()
        
        participation = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': today,
            'begin_date': today,
            'end_date': today + timedelta(days=365),
        })
        
        # Test termination sets terminated_date
        participation.status = 'terminated'
        self.assertEqual(participation.terminated_date, today)
        
        # Test suspension sets suspend_end_date
        participation.status = 'suspended'
        self.assertTrue(participation.suspend_end_date)
        expected_suspend_end = today + timedelta(days=30)  # Default suspend period
        self.assertEqual(participation.suspend_end_date, expected_suspend_end)

    def test_action_methods(self):
        """Test action methods."""
        participation = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'prospect',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
        })
        
        # Test action_activate
        participation.action_activate()
        self.assertEqual(participation.status, 'active')
        
        # Test action_suspend
        participation.action_suspend()
        self.assertEqual(participation.status, 'suspended')
        
        # Test action_terminate
        participation.action_terminate()
        self.assertEqual(participation.status, 'terminated')

    def test_renewal_functionality(self):
        """Test participation renewal."""
        today = date.today()
        end_date = today + timedelta(days=30)  # Expiring soon
        
        participation = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': today - timedelta(days=335),
            'begin_date': today - timedelta(days=335),
            'end_date': end_date,
            'paid_through_date': end_date,
            'auto_pay': True,
        })
        
        # Test can_auto_renew is True
        self.assertTrue(participation.can_auto_renew)
        
        # Test renewal
        old_end_date = participation.end_date
        participation.action_renew()
        
        # Should extend dates by 1 year
        expected_new_end = old_end_date + timedelta(days=365)
        self.assertEqual(participation.end_date, expected_new_end)
        self.assertEqual(participation.paid_through_date, expected_new_end)
        self.assertEqual(participation.status, 'active')

    def test_automatic_status_transitions(self):
        """Test automatic status transition processing."""
        today = date.today()
        
        # Create participation that should transition to grace
        expired_participation = self.participation_model.create({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
            'status': 'active',
            'join_date': today - timedelta(days=400),
            'begin_date': today - timedelta(days=400),
            'end_date': today - timedelta(days=35),
            'paid_through_date': today - timedelta(days=5),  # Expired 5 days ago
        })
        
        # Process automatic transitions
        transitions_made = self.participation_model.process_automatic_status_transitions()
        
        # Should have moved to grace
        expired_participation.refresh()
        self.assertEqual(expired_participation.status, 'grace')
        self.assertGreater(transitions_made, 0)

    def test_participation_type_onchange(self):
        """Test participation type onchange behavior."""
        participation = self.participation_model.new({
            'partner_id': self.individual_member.id,
            'participation_type': 'membership',
        })
        
        participation._onchange_participation_type()
        
        # Should set end_date to 1 year from today for membership
        expected_end = date.today() + timedelta(days=365)
        self.assertEqual(participation.end_date, expected_end)
        
        # Test event attendance (should be 1 day)
        participation.participation_type = 'event_attendance'
        participation._onchange_participation_type()
        
        expected_end = date.today() + timedelta(days=1)
        self.assertEqual(participation.end_date, expected_end)

    def test_partner_onchange(self):
        """Test partner onchange behavior."""
        participation = self.participation_model.new({})
        
        # Test with employee contact
        participation.partner_id = self.employee_contact
        participation._onchange_partner_id()
        
        # Should suggest parent company
        self.assertEqual(participation.company_id, self.organization_member)


class TestAMSParticipationHistory(TransactionCase):
    """Test cases for AMS Participation History model."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        self.history_model = self.env['ams.participation.history']
        self.participation_model = self.env['ams.participation']
        
        # Create test partner
        self.test_partner = self.env['res.partner'].create({
            'name': 'Test Member',
            'email': 'test@example.com',
            'is_company': False,
            'is_member': True,
        })
        
        # Create test participation
        self.test_participation = self.participation_model.create({
            'partner_id': self.test_partner.id,
            'participation_type': 'membership',
            'status': 'prospect',
            'join_date': date.today(),
            'begin_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
        })

    def test_history_creation(self):
        """Test history record creation."""
        history = self.history_model.create({
            'participation_id': self.test_participation.id,
            'old_status': 'prospect',
            'new_status': 'active',
            'reason': 'Test activation',
            'automated': False,
        })
        
        # Test basic fields
        self.assertEqual(history.participation_id, self.test_participation)
        self.assertEqual(history.old_status, 'prospect')
        self.assertEqual(history.new_status, 'active')
        self.assertEqual(history.reason, 'Test activation')
        self.assertFalse(history.automated)
        
        # Test computed fields
        self.assertTrue(history.change_summary)
        self.assertEqual(history.status_direction, 'activation')
        self.assertTrue(history.is_significant_change)

    def test_status_direction_computation(self):
        """Test status direction computation."""
        # Test activation
        history_activation = self.history_model.create({
            'participation_id': self.test_participation.id,
            'old_status': 'prospect',
            'new_status': 'active',
            'reason': 'Activation test',
        })
        self.assertEqual(history_activation.status_direction, 'activation')
        
        # Test deactivation
        history_deactivation = self.history_model.create({
            'participation_id': self.test_participation.id,
            'old_status': 'active',
            'new_status': 'suspended',
            'reason': 'Deactivation test',
        })
        self.assertEqual(history_deactivation.status_direction, 'deactivation')
        
        # Test recovery
        history_recovery = self.history_model.create({
            'participation_id': self.test_participation.id,
            'old_status': 'suspended',
            'new_status': 'active',
            'reason': 'Recovery test',
        })
        self.assertEqual(history_recovery.status_direction, 'recovery')

    def test_significant_change_detection(self):
        """Test significant change detection."""
        # Significant change: prospect to active
        significant_history = self.history_model.create({
            'participation_id': self.test_participation.id,
            'old_status': 'prospect',
            'new_status': 'active',
            'reason': 'Significant change',
        })
        self.assertTrue(significant_history.is_significant_change)
        
        # Non-significant change (lateral move)
        non_significant_history = self.history_model.create({
            'participation_id': self.test_participation.id,
            'old_status': 'suspended',
            'new_status': 'cancelled',
            'reason': 'Non-significant change',
        })
        self.assertFalse(non_significant_history.is_significant_change)

    def test_history_modification_restrictions(self):
        """Test that history records are protected from modification."""
        history = self.history_model.create({
            'participation_id': self.test_participation.id,
            'old_status': 'prospect',
            'new_status': 'active',
            'reason': 'Test modification restriction',
        })
        
        # Should be able to update reason (allowed field)
        history.reason = 'Updated reason'
        
        # Should not be able to update critical fields without system permissions
        with self.assertRaises(ValidationError):
            history.old_status = 'active'

    def test_get_participation_timeline(self):
        """Test getting participation timeline."""
        # Create multiple history records
        history1 = self.history_model.create({
            'participation_id': self.test_participation.id,
            'old_status': '',
            'new_status': 'prospect',
            'reason': 'Initial creation',
            'change_date': datetime.now() - timedelta(days=30),
        })
        
        history2 = self.history_model.create({
            'participation_id': self.test_participation.id,
            'old_status': 'prospect',
            'new_status': 'active',
            'reason': 'Activation',
            'change_date': datetime.now() - timedelta(days=15),
        })
        
        timeline = self.history_model.get_participation_timeline(self.test_participation.id)
        
        self.assertEqual(len(timeline), 3)  # Including the auto-created one
        self.assertEqual(timeline[0]['new_status'], 'prospect')
        self.assertEqual(timeline[1]['new_status'], 'active')

    def test_status_change_statistics(self):
        """Test status change statistics."""
        # Create multiple history records
        today = date.today()
        
        for i in range(5):
            self.history_model.create({
                'participation_id': self.test_participation.id,
                'old_status': 'prospect',
                'new_status': 'active',
                'reason': f'Test {i}',
                'change_date': datetime.combine(today, datetime.min.time()),
            })
        
        stats = self.history_model.get_status_change_statistics(
            date_from=today,
            date_to=today
        )
        
        self.assertGreater(stats['total_changes'], 0)
        self.assertIn('by_direction', stats)
        self.assertIn('by_new_status', stats)


class TestAMSCancellationReason(TransactionCase):
    """Test cases for AMS Cancellation Reason model."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        self.cancellation_reason_model = self.env['ams.cancellation.reason']

    def test_cancellation_reason_creation(self):
        """Test cancellation reason creation."""
        reason = self.cancellation_reason_model.create({
            'name': 'Test Reason',
            'code': 'TEST_REASON',
            'category': 'voluntary',
            'applies_to_membership': True,
            'immediate_termination': False,
            'allows_refund': True,
        })
        
        # Test basic fields
        self.assertEqual(reason.name, 'Test Reason')
        self.assertEqual(reason.code, 'TEST_REASON')
        self.assertEqual(reason.category, 'voluntary')
        
        # Test computed fields
        self.assertTrue(reason.display_name)
        self.assertIn('Membership', reason.applicable_types)
        self.assertIn('Refund eligible', reason.impact_summary)

    def test_code_auto_generation(self):
        """Test automatic code generation."""
        reason = self.cancellation_reason_model.new({
            'name': 'Financial Hardship'
        })
        reason._onchange_name()
        
        self.assertEqual(reason.code, 'FINANCIAL_HARDSHIP')

    def test_category_onchange_defaults(self):
        """Test category onchange setting defaults."""
        reason = self.cancellation_reason_model.new({
            'category': 'involuntary'
        })
        reason._onchange_category()
        
        # Involuntary should set strict defaults
        self.assertTrue(reason.immediate_termination)
        self.assertFalse(reason.allows_refund)
        self.assertTrue(reason.requires_approval)
        self.assertTrue(reason.blocks_rejoining)

    def test_applicable_reason_filtering(self):
        """Test getting applicable reasons for participation types."""
        # Create reasons with different applicability
        membership_reason = self.cancellation_reason_model.create({
            'name': 'Membership Reason',
            'code': 'MEMB_REASON',
            'category': 'voluntary',
            'applies_to_membership': True,
            'applies_to_chapter': False,
        })
        
        chapter_reason = self.cancellation_reason_model.create({
            'name': 'Chapter Reason',
            'code': 'CHAP_REASON',
            'category': 'voluntary',
            'applies_to_membership': False,
            'applies_to_chapter': True,
        })
        
        # Test filtering
        membership_reasons = self.cancellation_reason_model.get_applicable_reasons('membership')
        chapter_reasons = self.cancellation_reason_model.get_applicable_reasons('chapter')
        
        self.assertIn(membership_reason, membership_reasons)
        self.assertNotIn(chapter_reason, membership_reasons)
        self.assertIn(chapter_reason, chapter_reasons)
        self.assertNotIn(membership_reason, chapter_reasons)

    def test_validation_constraints(self):
        """Test validation constraints."""
        # Must apply to at least one participation type
        with self.assertRaises(ValidationError):
            self.cancellation_reason_model.create({
                'name': 'Invalid Reason',
                'code': 'INVALID',
                'category': 'voluntary',
                'applies_to_membership': False,
                'applies_to_chapter': False,
                'applies_to_committee': False,
                'applies_to_event': False,
                'applies_to_course': False,
            })

    def test_workflow_configuration(self):
        """Test getting workflow configuration."""
        reason = self.cancellation_reason_model.create({
            'name': 'Test Workflow',
            'code': 'TEST_WORKFLOW',
            'category': 'involuntary',
            'immediate_termination': True,
            'allows_refund': False,
            'requires_approval': True,
            'requires_documentation': True,
            'blocks_rejoining': True,
            'follow_up_days': 30,
        })
        
        workflow = reason.get_cancellation_workflow()
        
        self.assertTrue(workflow['immediate_termination'])
        self.assertFalse(workflow['allows_refund'])
        self.assertTrue(workflow['requires_approval'])
        self.assertTrue(workflow['requires_documentation'])
        self.assertTrue(workflow['blocks_rejoining'])
        self.assertEqual(workflow['follow_up_days'], 30)


class TestAMSPlaceholderModels(TransactionCase):
    """Test cases for placeholder models."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        self.subscription_product_model = self.env['ams.subscription.product']
        self.committee_position_model = self.env['ams.committee.position']

    def test_subscription_product_creation(self):
        """Test subscription product placeholder creation."""
        product = self.subscription_product_model.create({
            'name': 'Test Product',
            'code': 'TEST_PROD',
            'product_type': 'membership',
            'list_price': 100.0,
            'term_length': 365,
        })
        
        self.assertEqual(product.name, 'Test Product')
        self.assertEqual(product.code, 'TEST_PROD')
        self.assertEqual(product.list_price, 100.0)
        self.assertTrue(product.display_name)

    def test_committee_position_creation(self):
        """Test committee position placeholder creation."""
        position = self.committee_position_model.create({
            'name': 'Test Position',
            'code': 'TEST_POS',
            'committee_name': 'Test Committee',
            'committee_type': 'standing',
            'term_length_months': 12,
        })
        
        self.assertEqual(position.name, 'Test Position')
        self.assertEqual(position.code, 'TEST_POS')
        self.assertEqual(position.committee_name, 'Test Committee')
        self.assertTrue(position.display_name)

    def test_committee_position_eligibility(self):
        """Test committee position eligibility checking."""
        position = self.committee_position_model.create({
            'name': 'Test Position',
            'code': 'TEST_POS',
            'committee_name': 'Test Committee',
            'committee_type': 'standing',
            'minimum_membership_months': 12,
        })
        
        # Create test member
        member = self.env['res.partner'].create({
            'name': 'Test Member',
            'is_member': True,
            'member_since': date.today() - timedelta(days=400),  # > 12 months
        })
        
        eligibility = position.check_eligibility(member.id)
        
        self.assertTrue(eligibility['eligible'])
        self.assertEqual(len(eligibility['issues']), 0)