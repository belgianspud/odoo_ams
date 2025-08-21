# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, AccessError
from datetime import datetime, timedelta
from unittest.mock import patch
import json
import logging

_logger = logging.getLogger(__name__)


class TestAuditLog(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.AuditLog = self.env['ams.audit.log']
        self.Partner = self.env['res.partner']
        self.Users = self.env['res.users']
        
        # Create test users with different audit permissions
        self.audit_viewer = self.Users.create({
            'name': 'Audit Viewer',
            'login': 'audit_viewer',
            'email': 'viewer@test.com',
            'groups_id': [(4, self.env.ref('ams_core_audit.group_audit_viewer').id)]
        })
        
        self.audit_manager = self.Users.create({
            'name': 'Audit Manager',
            'login': 'audit_manager', 
            'email': 'manager@test.com',
            'groups_id': [(4, self.env.ref('ams_core_audit.group_audit_manager').id)]
        })
        
        self.regular_user = self.Users.create({
            'name': 'Regular User',
            'login': 'regular_user',
            'email': 'user@test.com',
            'groups_id': [(4, self.env.ref('base.group_user').id)]
        })
        
        # Create test partner for audit testing
        self.test_partner = self.Partner.create({
            'name': 'Test Member',
            'email': 'test@member.com',
            'is_member': True,
            'member_status': 'active'
        })
    
    def test_audit_log_creation(self):
        """Test basic audit log entry creation"""
        # Test creating audit log entry
        audit_log = self.AuditLog.create_audit_log(
            model_name='res.partner',
            record_id=self.test_partner.id,
            action='create',
            description='Test partner created',
            category='member_data',
            risk_level='low'
        )
        
        self.assertTrue(audit_log)
        self.assertEqual(audit_log.model_name, 'res.partner')
        self.assertEqual(audit_log.record_id, self.test_partner.id)
        self.assertEqual(audit_log.action, 'create')
        self.assertEqual(audit_log.category, 'member_data')
        self.assertEqual(audit_log.risk_level, 'low')
        self.assertEqual(audit_log.user_id, self.env.user)
    
    def test_audit_log_with_field_changes(self):
        """Test audit log creation with field changes"""
        field_changes = {
            'name': {'old': 'Old Name', 'new': 'New Name'},
            'email': {'old': 'old@email.com', 'new': 'new@email.com'}
        }
        
        audit_log = self.AuditLog.create_audit_log(
            model_name='res.partner',
            record_id=self.test_partner.id,
            action='write',
            description='Partner updated',
            field_changes=field_changes,
            category='member_data',
            risk_level='medium',
            is_sensitive=True,
            privacy_impact=True
        )
        
        self.assertTrue(audit_log.field_changes)
        self.assertEqual(audit_log.field_changes_json, field_changes)
        self.assertTrue(audit_log.is_sensitive)
        self.assertTrue(audit_log.privacy_impact)
        self.assertTrue(audit_log.requires_review)
    
    def test_audit_log_retention_date_computation(self):
        """Test retention date computation based on category and risk level"""
        # Test different categories and risk levels
        test_cases = [
            ('financial', 'high', 11),  # 10 base + 1 for high risk
            ('privacy', 'critical', 13),  # 10 base + 3 for critical risk
            ('security', 'medium', 5),   # 5 base + 0 for medium risk
            ('system', 'low', 2),        # 2 base + 0 for low risk
        ]
        
        for category, risk_level, expected_years in test_cases:
            audit_log = self.AuditLog.create({
                'model_name': 'test.model',
                'record_id': 1,
                'action': 'test',
                'description': 'Test entry',
                'category': category,
                'risk_level': risk_level,
                'timestamp': datetime.now()
            })
            
            audit_log._compute_retention_date()
            
            # Calculate expected retention date
            expected_date = audit_log.timestamp.date() + timedelta(days=expected_years * 365)
            self.assertEqual(audit_log.retention_date, expected_date)
    
    def test_audit_log_access_control(self):
        """Test access control for different user types"""
        # Create audit log as admin
        audit_log = self.AuditLog.create({
            'model_name': 'res.partner',
            'record_id': self.test_partner.id,
            'action': 'write',
            'description': 'Test audit log'
        })
        
        # Test audit viewer can read but not write
        audit_log_as_viewer = audit_log.with_user(self.audit_viewer)
        self.assertTrue(audit_log_as_viewer.read(['description']))
        
        with self.assertRaises(AccessError):
            audit_log_as_viewer.write({'notes': 'Viewer note'})
        
        # Test audit manager can read and write (review fields)
        audit_log_as_manager = audit_log.with_user(self.audit_manager)
        audit_log_as_manager.write({
            'reviewed': True,
            'notes': 'Manager review note'
        })
        self.assertTrue(audit_log.reviewed)
        
        # Test regular user cannot access audit logs
        with self.assertRaises(AccessError):
            audit_log.with_user(self.regular_user).read(['description'])
    
    def test_audit_log_modification_restrictions(self):
        """Test that audit logs cannot be improperly modified"""
        audit_log = self.AuditLog.create({
            'model_name': 'res.partner',
            'record_id': self.test_partner.id,
            'action': 'write',
            'description': 'Test audit log'
        })
        
        # Even audit managers cannot modify core audit data
        with self.assertRaises(AccessError):
            audit_log.with_user(self.audit_manager).write({
                'action': 'create',  # Cannot change action
                'model_name': 'other.model'  # Cannot change model
            })
        
        # Only review-related fields can be modified
        audit_log.with_user(self.audit_manager).write({
            'reviewed': True,
            'reviewed_by': self.audit_manager.id,
            'notes': 'Review completed'
        })
        
        self.assertTrue(audit_log.reviewed)
        self.assertEqual(audit_log.reviewed_by, self.audit_manager)
    
    def test_audit_log_deletion_restrictions(self):
        """Test that audit logs cannot be deleted by unauthorized users"""
        audit_log = self.AuditLog.create({
            'model_name': 'res.partner',
            'record_id': self.test_partner.id,
            'action': 'write',
            'description': 'Test audit log'
        })
        
        # Regular users and viewers cannot delete
        with self.assertRaises(AccessError):
            audit_log.with_user(self.regular_user).unlink()
        
        with self.assertRaises(AccessError):
            audit_log.with_user(self.audit_viewer).unlink()
        
        # Managers cannot delete
        with self.assertRaises(AccessError):
            audit_log.with_user(self.audit_manager).unlink()
    
    def test_audit_summary_generation(self):
        """Test audit summary generation"""
        # Create multiple audit log entries
        for i in range(5):
            self.AuditLog.create({
                'model_name': 'res.partner',
                'record_id': self.test_partner.id,
                'action': 'write' if i % 2 else 'create',
                'description': f'Test entry {i}',
                'category': 'member_data' if i < 3 else 'privacy',
                'risk_level': 'high' if i == 0 else 'low',
                'is_sensitive': i == 0,
                'requires_review': i == 0
            })
        
        # Generate summary
        summary = self.AuditLog.get_audit_summary(
            model_name='res.partner',
            record_id=self.test_partner.id,
            days=30
        )
        
        self.assertEqual(summary['total_entries'], 5)
        self.assertEqual(summary['by_action']['write'], 3)
        self.assertEqual(summary['by_action']['create'], 2)
        self.assertEqual(summary['by_category']['member_data'], 3)
        self.assertEqual(summary['by_category']['privacy'], 2)
        self.assertEqual(summary['sensitive_count'], 1)
        self.assertEqual(summary['requires_review_count'], 1)
    
    def test_audit_log_cleanup(self):
        """Test audit log cleanup functionality"""
        # Create old audit log entries
        old_date = datetime.now() - timedelta(days=3000)  # Over 8 years old
        old_audit_log = self.AuditLog.create({
            'model_name': 'res.partner',
            'record_id': self.test_partner.id,
            'action': 'write',
            'description': 'Old audit log',
            'timestamp': old_date,
            'category': 'system',
            'risk_level': 'low'
        })
        
        # Force computation of retention date
        old_audit_log._compute_retention_date()
        
        # Test cleanup as audit manager
        count = self.AuditLog.with_user(self.audit_manager).cleanup_old_logs()
        
        # Should have archived the old log
        self.assertGreater(count, 0)
        self.assertIn('Archived by automated cleanup', old_audit_log.notes)


class TestAuditMixin(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.AuditLog = self.env['ams.audit.log']
    
    def test_partner_audit_mixin_create(self):
        """Test that partner creation generates audit log"""
        initial_count = self.AuditLog.search_count([])
        
        partner = self.Partner.create({
            'name': 'Test Partner',
            'email': 'test@partner.com',
            'is_member': True
        })
        
        # Should have created an audit log entry
        new_count = self.AuditLog.search_count([])
        self.assertGreater(new_count, initial_count)
        
        # Check the audit log entry
        audit_log = self.AuditLog.search([
            ('model_name', '=', 'res.partner'),
            ('record_id', '=', partner.id),
            ('action', '=', 'create')
        ], limit=1)
        
        self.assertTrue(audit_log)
        self.assertEqual(audit_log.description, f"Created {partner._description}: {partner.display_name}")
        self.assertTrue(audit_log.field_changes_json)
    
    def test_partner_audit_mixin_write(self):
        """Test that partner updates generate audit logs"""
        partner = self.Partner.create({
            'name': 'Test Partner',
            'email': 'original@email.com'
        })
        
        initial_count = self.AuditLog.search_count([
            ('model_name', '=', 'res.partner'),
            ('record_id', '=', partner.id)
        ])
        
        # Update partner
        partner.write({
            'name': 'Updated Partner',
            'email': 'updated@email.com'
        })
        
        # Should have created another audit log entry
        new_count = self.AuditLog.search_count([
            ('model_name', '=', 'res.partner'),
            ('record_id', '=', partner.id)
        ])
        self.assertGreater(new_count, initial_count)
        
        # Check the update audit log
        audit_log = self.AuditLog.search([
            ('model_name', '=', 'res.partner'),
            ('record_id', '=', partner.id),
            ('action', '=', 'write')
        ], limit=1)
        
        self.assertTrue(audit_log)
        self.assertIn('name', audit_log.field_changes_json)
        self.assertIn('email', audit_log.field_changes_json)
        self.assertEqual(audit_log.field_changes_json['name']['old'], 'Test Partner')
        self.assertEqual(audit_log.field_changes_json['name']['new'], 'Updated Partner')
    
    def test_partner_audit_mixin_unlink(self):
        """Test that partner deletion generates audit logs"""
        partner = self.Partner.create({
            'name': 'Test Partner to Delete',
            'email': 'delete@partner.com'
        })
        partner_id = partner.id
        partner_name = partner.name
        
        # Delete partner
        partner.unlink()
        
        # Check deletion audit log
        audit_log = self.AuditLog.search([
            ('model_name', '=', 'res.partner'),
            ('record_id', '=', partner_id),
            ('action', '=', 'unlink')
        ], limit=1)
        
        self.assertTrue(audit_log)
        self.assertEqual(audit_log.risk_level, 'high')  # Deletions are high risk
        self.assertIn(partner_name, audit_log.description)
    
    def test_sensitive_field_detection(self):
        """Test detection of sensitive field changes"""
        partner = self.Partner.create({
            'name': 'Test Partner',
            'email': 'test@partner.com'
        })
        
        # Update sensitive field
        partner.write({
            'date_of_birth': '1990-01-01'
        })
        
        # Check audit log for sensitive flag
        audit_log = self.AuditLog.search([
            ('model_name', '=', 'res.partner'),
            ('record_id', '=', partner.id),
            ('action', '=', 'write')
        ], limit=1)
        
        self.assertTrue(audit_log.is_sensitive)
        self.assertTrue(audit_log.requires_review)
    
    def test_privacy_impact_detection(self):
        """Test detection of privacy-impacting changes"""
        partner = self.Partner.create({
            'name': 'Test Partner',
            'email': 'original@email.com'
        })
        
        # Update privacy-impacting field
        partner.write({
            'email': 'new@email.com'
        })
        
        # Check audit log for privacy impact
        audit_log = self.AuditLog.search([
            ('model_name', '=', 'res.partner'),
            ('record_id', '=', partner.id),
            ('action', '=', 'write')
        ], limit=1)
        
        self.assertTrue(audit_log.privacy_impact)
    
    def test_audit_computed_fields(self):
        """Test audit-related computed fields on partners"""
        partner = self.Partner.create({
            'name': 'Test Partner',
            'email': 'test@partner.com'
        })
        
        # Create some audit log entries
        for i in range(3):
            self.AuditLog.create({
                'model_name': 'res.partner',
                'record_id': partner.id,
                'action': 'write',
                'description': f'Test entry {i}',
                'is_sensitive': i == 0
            })
        
        # Test computed fields
        partner._compute_audit_log_count()
        partner._compute_sensitive_audit_count()
        partner._compute_last_audit_date()
        
        self.assertEqual(partner.audit_log_count, 4)  # 3 + 1 from creation
        self.assertEqual(partner.sensitive_audit_count, 1)
        self.assertTrue(partner.last_audit_date)
    
    def test_audit_view_actions(self):
        """Test audit view actions on partners"""
        partner = self.Partner.create({
            'name': 'Test Partner',
            'email': 'test@partner.com'
        })
        
        # Test view audit logs action
        action = partner.action_view_audit_logs()
        
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'ams.audit.log')
        self.assertIn(('model_name', '=', 'res.partner'), action['domain'])
        self.assertIn(('record_id', '=', partner.id), action['domain'])
    
    def test_risk_level_determination(self):
        """Test risk level determination for different scenarios"""
        partner = self.Partner.create({
            'name': 'Test Partner',
            'email': 'test@partner.com',
            'is_member': True
        })
        
        # Test member status change (should be medium risk)
        partner.write({'member_status': 'lapsed'})
        
        audit_log = self.AuditLog.search([
            ('model_name', '=', 'res.partner'),
            ('record_id', '=', partner.id),
            ('action', '=', 'write')
        ], limit=1)
        
        self.assertEqual(audit_log.risk_level, 'medium')
    
    def test_audit_compliance_status(self):
        """Test audit compliance status calculation"""
        partner = self.Partner.create({
            'name': 'Test Partner',
            'email': 'test@partner.com',
            'is_member': True
        })
        
        # Create some test audit entries
        self.AuditLog.create({
            'model_name': 'res.partner',
            'record_id': partner.id,
            'action': 'write',
            'description': 'High risk change',
            'risk_level': 'high',
            'requires_review': True,
            'reviewed': False
        })
        
        # Get compliance status
        status = partner.get_audit_compliance_status()
        
        self.assertIn('total_entries', status)
        self.assertIn('unreviewed_high_risk', status)
        self.assertIn('compliance_score', status)
        self.assertIn('overall_status', status)
        
        # Should have compliance issues due to unreviewed high-risk entry
        self.assertGreater(status['unreviewed_high_risk'], 0)
        self.assertLess(status['compliance_score'], 100)


class TestAuditIntegration(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.AuditLog = self.env['ams.audit.log']
        self.Partner = self.env['res.partner']
    
    @patch('odoo.addons.ams_core_audit.models.audit_log._logger')
    def test_audit_log_error_handling(self, mock_logger):
        """Test audit log error handling doesn't break operations"""
        partner = self.Partner.create({
            'name': 'Test Partner',
            'email': 'test@partner.com'
        })
        
        # Mock audit log creation failure
        with patch.object(self.AuditLog, 'create_audit_log', side_effect=Exception('Test error')):
            # Partner update should still work even if audit logging fails
            partner.write({'name': 'Updated Name'})
            
            # Check that error was logged
            mock_logger.error.assert_called()
            
            # Partner should still be updated
            self.assertEqual(partner.name, 'Updated Name')
    
    def test_audit_cron_job_execution(self):
        """Test audit cron job functionality"""
        # Create old audit log
        old_date = datetime.now() - timedelta(days=3000)
        old_log = self.AuditLog.create({
            'model_name': 'test.model',
            'record_id': 1,
            'action': 'test',
            'description': 'Old test entry',
            'timestamp': old_date,
            'category': 'system',
            'risk_level': 'low'
        })
        
        # Force retention date computation
        old_log._compute_retention_date()
        
        # Execute cleanup cron job
        self.AuditLog._cron_cleanup_old_logs()
        
        # Check that old log was marked for archival
        old_log.refresh()
        self.assertIn('Archived', old_log.notes)
    
    def test_audit_name_get(self):
        """Test audit log name_get method"""
        audit_log = self.AuditLog.create({
            'model_name': 'res.partner',
            'record_id': 1,
            'action': 'create',
            'description': 'Test entry',
            'model_description': 'Contact',
            'record_name': 'Test Partner',
            'timestamp': datetime.now()
        })
        
        name_get_result = audit_log.name_get()[0][1]
        
        self.assertIn('Create Contact', name_get_result)
        self.assertIn('Test Partner', name_get_result)
        self.assertIn(audit_log.timestamp.strftime('%Y-%m-%d'), name_get_result)