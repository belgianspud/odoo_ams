# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class TestCommunicationPreferences(TransactionCase):

    def setUp(self):
        super().setUp()
        
        # Create test member
        self.test_member = self.env['res.partner'].create({
            'name': 'Test Member',
            'first_name': 'Test',
            'last_name': 'Member',
            'email': 'test.member@example.com',
            'phone': '555-1234',
            'is_company': False,
            'member_id': 'M000123',
        })
        
        # Create test organization
        self.test_organization = self.env['res.partner'].create({
            'name': 'Test Organization',
            'email': 'info@testorg.com',
            'phone': '555-5678',
            'is_company': True,
            'member_id': 'M000124',
        })

    def test_communication_preference_creation(self):
        """Test creating communication preferences"""
        preference = self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
            'consent_source': 'test_creation',
        })
        
        self.assertTrue(preference.id)
        self.assertEqual(preference.partner_id, self.test_member)
        self.assertEqual(preference.communication_type, 'email')
        self.assertEqual(preference.category, 'marketing')
        self.assertTrue(preference.opted_in)
        self.assertTrue(preference.original_opt_in_date)

    def test_preference_uniqueness_constraint(self):
        """Test that duplicate preferences cannot be created"""
        # Create first preference
        self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        
        # Attempt to create duplicate
        with self.assertRaises(ValidationError):
            self.env['ams.communication.preference'].create({
                'partner_id': self.test_member.id,
                'communication_type': 'email',
                'category': 'marketing',
                'opted_in': False,
            })

    def test_preference_summary_computation(self):
        """Test preference summary computation"""
        preference = self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        
        expected_summary = f"{self.test_member.display_name} - Email - Marketing (Opted In)"
        self.assertEqual(preference.preference_summary, expected_summary)

    def test_status_display_computation(self):
        """Test status display computation"""
        # Basic opt-in
        preference = self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        self.assertEqual(preference.status_display, "Basic Opt-in")
        
        # GDPR consent
        preference.write({'gdpr_consent': True})
        self.assertEqual(preference.status_display, "GDPR Consent")
        
        # Double opt-in
        preference.write({'double_opt_in': True})
        self.assertEqual(preference.status_display, "Confirmed (GDPR + Double Opt-in)")
        
        # Opted out
        preference.write({'opted_in': False})
        self.assertEqual(preference.status_display, "Opted Out")

    def test_compliance_status_computation(self):
        """Test compliance status computation"""
        # Email with no special consent
        preference = self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        self.assertEqual(preference.compliance_status, 'non_compliant')
        
        # Email with GDPR consent
        preference.write({'gdpr_consent': True})
        self.assertEqual(preference.compliance_status, 'needs_confirmation')
        
        # Email with GDPR and double opt-in
        preference.write({'double_opt_in': True})
        self.assertEqual(preference.compliance_status, 'compliant')
        
        # Non-email communication
        sms_preference = self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'sms',
            'category': 'events',
            'opted_in': True,
            'gdpr_consent': True,
        })
        self.assertEqual(sms_preference.compliance_status, 'compliant')

    def test_opt_in_opt_out_tracking(self):
        """Test opt-in and opt-out date tracking"""
        preference = self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        
        # Check original opt-in date was set
        self.assertTrue(preference.original_opt_in_date)
        original_date = preference.original_opt_in_date
        
        # Opt out
        preference.write({'opted_in': False})
        self.assertTrue(preference.opt_out_date)
        self.assertFalse(preference.opt_out_date == original_date)
        
        # Opt back in
        preference.write({'opted_in': True})
        self.assertFalse(preference.opt_out_date)

    def test_gdpr_consent_tracking(self):
        """Test GDPR consent date tracking"""
        preference = self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        
        self.assertFalse(preference.gdpr_consent_date)
        
        # Grant GDPR consent
        preference.write({'gdpr_consent': True})
        self.assertTrue(preference.gdpr_consent_date)

    def test_double_opt_in_tracking(self):
        """Test double opt-in date tracking"""
        preference = self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        
        self.assertFalse(preference.double_opt_in_date)
        
        # Confirm double opt-in
        preference.write({'double_opt_in': True})
        self.assertTrue(preference.double_opt_in_date)

    def test_business_methods(self):
        """Test business methods"""
        # Create some preferences
        email_marketing = self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        
        sms_events = self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'sms',
            'category': 'events',
            'opted_in': False,
        })
        
        # Test get_member_preferences
        all_prefs = self.env['ams.communication.preference'].get_member_preferences(self.test_member.id)
        self.assertEqual(len(all_prefs), 2)
        
        email_prefs = self.env['ams.communication.preference'].get_member_preferences(
            self.test_member.id, communication_type='email'
        )
        self.assertEqual(len(email_prefs), 1)
        self.assertEqual(email_prefs[0], email_marketing)
        
        # Test check_communication_allowed
        self.assertTrue(self.env['ams.communication.preference'].check_communication_allowed(
            self.test_member.id, 'email', 'marketing'
        ))
        
        self.assertFalse(self.env['ams.communication.preference'].check_communication_allowed(
            self.test_member.id, 'sms', 'events'
        ))
        
        # Test for non-existing preference (should default to True)
        self.assertTrue(self.env['ams.communication.preference'].check_communication_allowed(
            self.test_member.id, 'mail', 'fundraising'
        ))

    def test_action_methods(self):
        """Test action methods"""
        preference = self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': False,
        })
        
        # Test opt-in action
        preference.action_opt_in()
        self.assertTrue(preference.opted_in)
        self.assertEqual(preference.consent_source, 'manual_opt_in')
        
        # Test opt-out action
        preference.action_opt_out()
        self.assertFalse(preference.opted_in)
        self.assertEqual(preference.consent_source, 'manual_opt_out')
        
        # Test GDPR consent action
        preference.action_confirm_gdpr_consent()
        self.assertTrue(preference.gdpr_consent)
        self.assertTrue(preference.opted_in)  # Should also opt in
        
        # Test double opt-in action
        preference.write({'double_opt_in': False})
        preference.action_confirm_double_opt_in()
        self.assertTrue(preference.double_opt_in)
        self.assertTrue(preference.opted_in)  # Should also opt in

    def test_create_default_preferences(self):
        """Test creating default preferences"""
        # Ensure no existing preferences
        existing = self.env['ams.communication.preference'].search([
            ('partner_id', '=', self.test_member.id)
        ])
        existing.unlink()
        
        # Create default preferences
        created_prefs = self.env['ams.communication.preference'].create_default_preferences(
            self.test_member.id
        )
        
        # Should create 24 preferences (4 comm types × 6 categories)
        self.assertEqual(len(created_prefs), 24)
        
        # Check that SMS marketing is opted out by default
        sms_marketing = created_prefs.filtered(
            lambda p: p.communication_type == 'sms' and p.category == 'marketing'
        )
        self.assertFalse(sms_marketing.opted_in)
        
        # Check that email membership is opted in by default
        email_membership = created_prefs.filtered(
            lambda p: p.communication_type == 'email' and p.category == 'membership'
        )
        self.assertTrue(email_membership.opted_in)

    def test_partner_communication_extensions(self):
        """Test res.partner communication extensions"""
        # Test that preferences are automatically created for new members
        new_member = self.env['res.partner'].create({
            'name': 'New Test Member',
            'first_name': 'New',
            'last_name': 'Member',
            'email': 'new.member@example.com',
            'is_company': False,
            'member_id': 'M000125',
        })
        
        # Should have communication preferences created
        self.assertTrue(new_member.communication_preference_ids)

    def test_partner_communication_stats(self):
        """Test partner communication statistics"""
        # Create some preferences
        prefs_data = [
            ('email', 'marketing', True),
            ('email', 'events', True),
            ('sms', 'events', True),
            ('sms', 'marketing', False),
            ('mail', 'fundraising', False),
        ]
        
        for comm_type, category, opted_in in prefs_data:
            self.env['ams.communication.preference'].create({
                'partner_id': self.test_member.id,
                'communication_type': comm_type,
                'category': category,
                'opted_in': opted_in,
            })
        
        # Test computed statistics
        self.assertEqual(self.test_member.email_opt_in_count, 2)
        self.assertEqual(self.test_member.sms_opt_in_count, 1)
        self.assertEqual(self.test_member.total_opt_ins, 3)

    def test_partner_communication_permissions(self):
        """Test partner communication permissions"""
        # Test global opt-out
        self.test_member.write({'communication_opt_out': True})
        self.assertFalse(self.test_member.can_email)
        self.assertFalse(self.test_member.can_sms)
        self.assertFalse(self.test_member.can_mail)
        self.assertFalse(self.test_member.can_call)
        
        # Reset and test specific do-not flags
        self.test_member.write({
            'communication_opt_out': False,
            'do_not_email': True,
            'do_not_sms': True,
        })
        self.assertFalse(self.test_member.can_email)
        self.assertFalse(self.test_member.can_sms)
        self.assertTrue(self.test_member.can_mail)
        self.assertTrue(self.test_member.can_call)
        
        # Test email bounce threshold
        self.test_member.write({
            'do_not_email': False,
            'email_bounce_count': 5,
        })
        self.assertFalse(self.test_member.can_email)

    def test_partner_business_methods(self):
        """Test partner business methods"""
        # Create a preference
        self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        
        # Test check_communication_allowed
        self.assertTrue(self.test_member.check_communication_allowed('email', 'marketing'))
        
        # Test global opt-out
        self.test_member.action_global_opt_out()
        self.assertTrue(self.test_member.communication_opt_out)
        self.assertTrue(self.test_member.do_not_email)
        self.assertFalse(self.test_member.communication_preference_ids.filtered('opted_in'))
        
        # Test global opt-in
        self.test_member.action_global_opt_in()
        self.assertFalse(self.test_member.communication_opt_out)
        self.assertFalse(self.test_member.do_not_email)

    def test_email_bounce_tracking(self):
        """Test email bounce tracking"""
        initial_count = self.test_member.email_bounce_count
        
        # Record a bounce
        self.test_member.record_email_bounce()
        self.assertEqual(self.test_member.email_bounce_count, initial_count + 1)
        self.assertTrue(self.test_member.last_email_bounce_date)
        
        # Record multiple bounces to trigger auto-disable
        for _ in range(4):
            self.test_member.record_email_bounce()
        
        self.assertTrue(self.test_member.do_not_email)
        
        # Reset bounces
        self.test_member.reset_email_bounces()
        self.assertEqual(self.test_member.email_bounce_count, 0)
        self.assertFalse(self.test_member.last_email_bounce_date)
        self.assertFalse(self.test_member.do_not_email)

    def test_gdpr_and_privacy_actions(self):
        """Test GDPR and privacy policy actions"""
        # Test GDPR consent
        self.test_member.action_gdpr_consent()
        self.assertTrue(self.test_member.gdpr_consent_given)
        self.assertTrue(self.test_member.gdpr_consent_date)
        
        # Test privacy policy acceptance
        self.test_member.action_accept_privacy_policy()
        self.assertTrue(self.test_member.privacy_policy_accepted)
        self.assertTrue(self.test_member.privacy_policy_date)

    def test_communication_summary(self):
        """Test communication summary generation"""
        # Create various preferences
        prefs_data = [
            ('email', 'marketing', True),
            ('email', 'events', True),
            ('sms', 'events', True),
            ('sms', 'marketing', False),
            ('mail', 'fundraising', False),
        ]
        
        for comm_type, category, opted_in in prefs_data:
            self.env['ams.communication.preference'].create({
                'partner_id': self.test_member.id,
                'communication_type': comm_type,
                'category': category,
                'opted_in': opted_in,
            })
        
        summary = self.test_member.get_communication_summary()
        
        self.assertEqual(summary['total_preferences'], 5)
        self.assertEqual(summary['opted_in'], 3)
        self.assertEqual(summary['opted_out'], 2)
        self.assertEqual(summary['by_type']['email']['opted_in'], 2)
        self.assertEqual(summary['by_category']['marketing']['opted_in'], 1)

    def test_name_get_and_search(self):
        """Test name_get and name_search functionality"""
        preference = self.env['ams.communication.preference'].create({
            'partner_id': self.test_member.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        
        # Test name_get
        name_result = preference.name_get()
        self.assertTrue(name_result)
        self.assertIn('Test Member', name_result[0][1])
        
        # Test name_search
        search_results = self.env['ams.communication.preference']._name_search('Test Member')
        self.assertIn(preference.id, search_results)

    def test_partner_email_update_resets_bounces(self):
        """Test that updating partner email resets bounce count"""
        # Set up bounces
        self.test_member.write({'email_bounce_count': 3})
        
        # Update email
        self.test_member.write({'email': 'newemail@example.com'})
        
        # Bounce count should be reset
        self.assertEqual(self.test_member.email_bounce_count, 0)