# -*- coding: utf-8 -*-
"""Test cases for AMS Communication module functionality."""

from odoo.tests import common
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from unittest.mock import patch


class TestAMSCommunicationPreference(common.TransactionCase):
    """Test AMS Communication Preference model."""

    def setUp(self):
        super().setUp()
        self.CommunicationPreference = self.env['ams.communication.preference']
        self.Partner = self.env['res.partner']
        
        # Create test partner
        self.test_partner = self.Partner.create({
            'name': 'John Test Member',
            'email': 'john@test.com',
            'phone': '+1234567890',
            'mobile': '+1987654321',
            'street': '123 Test St',
            'city': 'Test City',
            'is_company': False,
        })

    def test_create_communication_preference(self):
        """Test creating a communication preference."""
        preference = self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
            'consent_source': 'test_form',
            'consent_method': 'website_form',
            'ip_address': '192.168.1.1'
        })
        
        self.assertTrue(preference.id)
        self.assertEqual(preference.partner_id, self.test_partner)
        self.assertEqual(preference.communication_type, 'email')
        self.assertEqual(preference.category, 'marketing')
        self.assertTrue(preference.opted_in)
        self.assertEqual(preference.consent_source, 'test_form')
        self.assertEqual(preference.consent_method, 'website_form')
        self.assertEqual(preference.ip_address, '192.168.1.1')
        self.assertTrue(preference.date_updated)

    def test_unique_constraint(self):
        """Test unique constraint on partner/type/category combination."""
        # Create first preference
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        
        # Try to create duplicate
        with self.assertRaises(Exception):
            self.CommunicationPreference.create({
                'partner_id': self.test_partner.id,
                'communication_type': 'email',
                'category': 'marketing',  # Same combination
                'opted_in': False,
            })

    def test_display_name_computation(self):
        """Test display name computation."""
        preference = self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        
        preference._compute_display_name()
        expected = f"{self.test_partner.name} - Email - Marketing (Opted In)"
        self.assertEqual(preference.display_name, expected)
        
        # Test opted out
        preference.opted_in = False
        preference._compute_display_name()
        expected = f"{self.test_partner.name} - Email - Marketing (Opted Out)"
        self.assertEqual(preference.display_name, expected)

    def test_validation_email_no_address(self):
        """Test validation when opting in to email without email address."""
        # Remove email from partner
        self.test_partner.email = False
        
        with self.assertRaises(ValidationError):
            self.CommunicationPreference.create({
                'partner_id': self.test_partner.id,
                'communication_type': 'email',
                'category': 'marketing',
                'opted_in': True,  # Should fail validation
            })

    def test_validation_sms_no_mobile(self):
        """Test validation when opting in to SMS without mobile number."""
        # Remove mobile from partner
        self.test_partner.mobile = False
        
        with self.assertRaises(ValidationError):
            self.CommunicationPreference.create({
                'partner_id': self.test_partner.id,
                'communication_type': 'sms',
                'category': 'membership',
                'opted_in': True,  # Should fail validation
            })

    def test_validation_mail_no_address(self):
        """Test validation when opting in to mail without address."""
        # Remove address from partner
        self.test_partner.street = False
        
        with self.assertRaises(ValidationError):
            self.CommunicationPreference.create({
                'partner_id': self.test_partner.id,
                'communication_type': 'mail',
                'category': 'fundraising',
                'opted_in': True,  # Should fail validation
            })

    def test_check_communication_allowed(self):
        """Test check_communication_allowed method."""
        # Create preference
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        
        # Test allowed communication
        allowed = self.CommunicationPreference.check_communication_allowed(
            self.test_partner.id, 'email', 'marketing'
        )
        self.assertTrue(allowed)
        
        # Update to opted out
        preference = self.CommunicationPreference.search([
            ('partner_id', '=', self.test_partner.id),
            ('communication_type', '=', 'email'),
            ('category', '=', 'marketing')
        ])
        preference.opted_in = False
        
        # Test not allowed communication
        allowed = self.CommunicationPreference.check_communication_allowed(
            self.test_partner.id, 'email', 'marketing'
        )
        self.assertFalse(allowed)

    def test_default_preferences_emergency(self):
        """Test that emergency communications default to allowed."""
        # Test default for emergency category (no preference exists)
        allowed = self.CommunicationPreference.check_communication_allowed(
            self.test_partner.id, 'email', 'emergency'
        )
        self.assertTrue(allowed)  # Emergency should default to True

    def test_create_default_preferences(self):
        """Test creating default preferences for a member."""
        result = self.CommunicationPreference.create_default_preferences(
            self.test_partner.id
        )
        
        self.assertTrue(result)
        
        # Check that preferences were created
        preferences = self.CommunicationPreference.search([
            ('partner_id', '=', self.test_partner.id)
        ])
        self.assertTrue(len(preferences) > 0)
        
        # Should have preferences for all communication types the partner can receive
        comm_types = preferences.mapped('communication_type')
        self.assertIn('email', comm_types)  # Partner has email
        self.assertIn('sms', comm_types)    # Partner has mobile
        self.assertIn('phone', comm_types)  # Partner has phone/mobile
        self.assertIn('mail', comm_types)   # Partner has address

    def test_toggle_preference(self):
        """Test toggling preference status."""
        preference = self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'events',
            'opted_in': True,
        })
        
        original_date = preference.date_updated
        
        # Toggle to opted out
        preference.toggle_preference()
        self.assertFalse(preference.opted_in)
        self.assertGreater(preference.date_updated, original_date)
        self.assertEqual(preference.consent_method, 'staff_update')
        
        # Toggle back to opted in
        preference.toggle_preference()
        self.assertTrue(preference.opted_in)

    def test_update_preference_with_tracking(self):
        """Test updating preference with proper consent tracking."""
        preference = self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'education',
            'opted_in': False,
        })
        
        # Update with tracking info
        preference.update_preference(
            opted_in=True,
            consent_source='member_portal',
            consent_method='website_form',
            ip_address='10.0.0.1'
        )
        
        self.assertTrue(preference.opted_in)
        self.assertEqual(preference.consent_source, 'member_portal')
        self.assertEqual(preference.consent_method, 'website_form')
        self.assertEqual(preference.ip_address, '10.0.0.1')

    def test_get_partner_preferences(self):
        """Test getting preferences for a specific partner."""
        # Create multiple preferences
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'sms',
            'category': 'marketing',
            'opted_in': False,
        })
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'events',
            'opted_in': True,
        })
        
        # Get all preferences
        all_prefs = self.CommunicationPreference.get_partner_preferences(
            self.test_partner.id
        )
        self.assertEqual(len(all_prefs), 3)
        
        # Get email preferences only
        email_prefs = self.CommunicationPreference.get_partner_preferences(
            self.test_partner.id, communication_type='email'
        )
        self.assertEqual(len(email_prefs), 2)
        
        # Get marketing preferences only
        marketing_prefs = self.CommunicationPreference.get_partner_preferences(
            self.test_partner.id, category='marketing'
        )
        self.assertEqual(len(marketing_prefs), 2)
        
        # Get specific preference
        specific_pref = self.CommunicationPreference.get_partner_preferences(
            self.test_partner.id, communication_type='email', category='marketing'
        )
        self.assertEqual(len(specific_pref), 1)
        self.assertTrue(specific_pref.opted_in)

    def test_compliance_report(self):
        """Test GDPR compliance reporting."""
        # Create preferences with varying compliance data
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
            'consent_source': 'website_form',
            'consent_method': 'website_form',
            'ip_address': '192.168.1.1'
        })
        
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'sms',
            'category': 'events',
            'opted_in': True,
            # Missing consent tracking info
        })
        
        report = self.CommunicationPreference.get_compliance_report()
        
        self.assertEqual(report['total_preferences'], 2)
        self.assertEqual(report['missing_consent_source'], 1)
        self.assertEqual(report['missing_consent_method'], 1)
        self.assertLess(report['compliance_percentage'], 100)

    def test_action_methods(self):
        """Test action methods for opt in/out."""
        preference = self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'committee',
            'opted_in': False,
        })
        
        # Test opt in action
        preference.action_opt_in()
        self.assertTrue(preference.opted_in)
        self.assertEqual(preference.consent_method, 'staff_update')
        
        # Test opt out action
        preference.action_opt_out()
        self.assertFalse(preference.opted_in)


class TestAMSCommunicationLog(common.TransactionCase):
    """Test AMS Communication Log model."""

    def setUp(self):
        super().setUp()
        self.CommunicationLog = self.env['ams.communication.log']
        self.Partner = self.env['res.partner']
        
        # Create test partner
        self.test_partner = self.Partner.create({
            'name': 'Jane Test Member',
            'email': 'jane@test.com',
            'mobile': '+1555123456',
            'is_company': False,
        })

    def test_create_communication_log(self):
        """Test creating a communication log entry."""
        log = self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'membership',
            'subject': 'Welcome to the Association',
            'sent_date': datetime.now(),
            'delivery_status': 'sent',
            'body_plain': 'Welcome message content',
            'campaign_id': 'WELCOME_2024'
        })
        
        self.assertTrue(log.id)
        self.assertEqual(log.partner_id, self.test_partner)
        self.assertEqual(log.communication_type, 'email')
        self.assertEqual(log.category, 'membership')
        self.assertEqual(log.subject, 'Welcome to the Association')
        self.assertEqual(log.delivery_status, 'sent')
        self.assertEqual(log.campaign_id, 'WELCOME_2024')

    def test_display_name_computation(self):
        """Test display name computation."""
        log = self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'sms',
            'category': 'events',
            'subject': 'Event Reminder',
            'sent_date': datetime(2024, 1, 15, 10, 30),
            'delivery_status': 'delivered',
        })
        
        log._compute_display_name()
        expected = f"{self.test_partner.name} - SMS - Events - Event Reminder (2024-01-15 10:30)"
        self.assertEqual(log.display_name, expected)

    def test_delivery_successful_computation(self):
        """Test delivery successful computation."""
        log = self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'delivery_status': 'delivered',
        })
        
        log._compute_delivery_successful()
        self.assertTrue(log.delivery_successful)
        
        # Test failed status
        log.delivery_status = 'failed'
        log._compute_delivery_successful()
        self.assertFalse(log.delivery_successful)
        
        # Test opened status
        log.delivery_status = 'opened'
        log._compute_delivery_successful()
        self.assertTrue(log.delivery_successful)

    def test_engagement_score_computation(self):
        """Test engagement score computation."""
        log = self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'education',
            'delivery_status': 'delivered',
            'open_count': 2,
            'click_count': 1,
        })
        
        log._compute_engagement_score()
        # Base score (1.0) + opens (1.0) + clicks (1.0) = 3.0
        self.assertEqual(log.engagement_score, 3.0)
        
        # Test bounced status (should be 0)
        log.delivery_status = 'bounced'
        log._compute_engagement_score()
        self.assertEqual(log.engagement_score, 0.0)

    def test_days_since_sent_computation(self):
        """Test days since sent computation."""
        yesterday = datetime.now() - timedelta(days=1)
        log = self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'mail',
            'category': 'fundraising',
            'sent_date': yesterday,
        })
        
        log._compute_days_since_sent()
        self.assertEqual(log.days_since_sent, 1)

    def test_date_validation(self):
        """Test that delivery date cannot be before sent date."""
        sent_date = datetime.now()
        delivery_date = sent_date - timedelta(hours=1)  # Before sent date
        
        with self.assertRaises(ValidationError):
            self.CommunicationLog.create({
                'partner_id': self.test_partner.id,
                'communication_type': 'email',
                'category': 'membership',
                'sent_date': sent_date,
                'delivery_date': delivery_date,  # Invalid
            })

    def test_log_communication_method(self):
        """Test the log_communication class method."""
        log = self.CommunicationLog.log_communication(
            partner_id=self.test_partner.id,
            communication_type='email',
            category='events',
            subject='Event Registration Confirmation',
            campaign_id='EVENT_REG_2024',
            body_plain='Thank you for registering',
            external_message_id='ext_msg_123'
        )
        
        self.assertTrue(log.id)
        self.assertEqual(log.partner_id, self.test_partner)
        self.assertEqual(log.subject, 'Event Registration Confirmation')
        self.assertEqual(log.campaign_id, 'EVENT_REG_2024')
        self.assertEqual(log.external_message_id, 'ext_msg_123')
        self.assertEqual(log.delivery_status, 'sent')

    def test_update_delivery_status(self):
        """Test updating delivery status."""
        log = self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'delivery_status': 'sent',
        })
        
        # Update to delivered
        log.update_delivery_status('delivered')
        self.assertEqual(log.delivery_status, 'delivered')
        self.assertTrue(log.delivery_date)
        
        # Update to bounced with reason
        log.update_delivery_status('bounced', bounce_reason='Invalid email address')
        self.assertEqual(log.delivery_status, 'bounced')
        self.assertEqual(log.bounce_reason, 'Invalid email address')

    def test_track_open(self):
        """Test tracking email opens."""
        log = self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'newsletter',
            'delivery_status': 'sent',
            'open_count': 0,
        })
        
        # Track first open
        log.track_open()
        self.assertEqual(log.open_count, 1)
        self.assertEqual(log.delivery_status, 'opened')
        self.assertTrue(log.opened_date)
        
        # Track second open
        log.track_open()
        self.assertEqual(log.open_count, 2)

    def test_track_click(self):
        """Test tracking link clicks."""
        log = self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'events',
            'delivery_status': 'delivered',
            'click_count': 0,
            'open_count': 0,
        })
        
        # Track click (should also count as open if not already opened)
        log.track_click()
        self.assertEqual(log.click_count, 1)
        self.assertEqual(log.open_count, 1)  # Auto-incremented
        self.assertEqual(log.delivery_status, 'clicked')
        self.assertTrue(log.clicked_date)
        self.assertTrue(log.opened_date)

    def test_get_delivery_stats(self):
        """Test delivery statistics calculation."""
        # Create multiple log entries
        self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'delivery_status': 'delivered',
            'sent_date': datetime.now()
        })
        self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'delivery_status': 'opened',
            'sent_date': datetime.now()
        })
        self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'delivery_status': 'bounced',
            'sent_date': datetime.now()
        })
        
        stats = self.CommunicationLog.get_delivery_stats()
        
        self.assertEqual(stats['total_sent'], 3)
        self.assertEqual(stats['delivered'], 1)
        self.assertEqual(stats['opened'], 1)
        self.assertEqual(stats['bounced'], 1)
        self.assertAlmostEqual(stats['delivery_rate'], 33.33, places=1)
        self.assertAlmostEqual(stats['bounce_rate'], 33.33, places=1)

    def test_process_webhook_update(self):
        """Test processing webhook updates from external providers."""
        log = self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'membership',
            'delivery_status': 'sent',
            'external_message_id': 'webhook_test_123'
        })
        
        # Process webhook update
        status_data = {
            'event': 'delivered',
            'timestamp': datetime.now(),
            'reason': None
        }
        
        result = self.CommunicationLog.process_webhook_update(
            'webhook_test_123', status_data
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['communication_id'], log.id)
        
        # Check that status was updated
        log.refresh()
        self.assertEqual(log.delivery_status, 'delivered')


class TestResPartnerCommunication(common.TransactionCase):
    """Test res.partner communication extensions."""

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.CommunicationPreference = self.env['ams.communication.preference']
        self.CommunicationLog = self.env['ams.communication.log']
        
        # Create test partner with member type
        if hasattr(self.env, 'ams.member.type'):
            self.member_type = self.env['ams.member.type'].create({
                'name': 'Test Individual',
                'code': 'TEST_IND',
                'is_individual': True,
                'is_organization': False,
            })
            
            self.test_partner = self.Partner.create({
                'name': 'Bob Test Member',
                'email': 'bob@test.com',
                'mobile': '+1444555666',
                'street': '456 Member St',
                'city': 'Member City',
                'is_company': False,
                'member_type_id': self.member_type.id,
            })
        else:
            # Fallback if member_data module not available
            self.test_partner = self.Partner.create({
                'name': 'Bob Test Member',
                'email': 'bob@test.com',
                'mobile': '+1444555666',
                'street': '456 Member St',
                'city': 'Member City',
                'is_company': False,
            })

    def test_computed_preference_fields(self):
        """Test computed communication preference fields."""
        # Create preferences
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'events',
            'opted_in': False,
        })
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'sms',
            'category': 'emergency',
            'opted_in': True,
        })
        
        # Compute preferences
        self.test_partner._compute_communication_preferences()
        
        # Email should be opted in (at least one email category is opted in)
        self.assertTrue(self.test_partner.email_opted_in)
        
        # SMS should be opted in
        self.assertTrue(self.test_partner.sms_opted_in)
        
        # Marketing should be opted in
        self.assertTrue(self.test_partner.marketing_communications)
        
        # Events should be False (only email events exists and it's opted out)
        self.assertFalse(self.test_partner.event_communications)

    def test_communication_stats_computation(self):
        """Test communication statistics computation."""
        # Create communication logs
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'membership',
            'sent_date': yesterday,
            'delivery_status': 'delivered',
            'engagement_score': 2.5,
        })
        self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'events',
            'sent_date': now,
            'delivery_status': 'bounced',
            'engagement_score': 0.0,
            'opened_date': now,
        })
        
        # Compute stats
        self.test_partner._compute_communication_stats()
        
        self.assertEqual(self.test_partner.total_communications_sent, 2)
        self.assertEqual(self.test_partner.email_bounce_count, 1)
        self.assertEqual(self.test_partner.last_communication_date, now)
        self.assertEqual(self.test_partner.last_email_open_date, now)
        self.assertEqual(self.test_partner.communication_engagement_score, 1.25)  # Average of 2.5 and 0.0

    def test_preference_summary_computation(self):
        """Test preference summary computation."""
        # Create some preferences
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'sms',
            'category': 'events',
            'opted_in': False,
        })
        
        # Compute summary
        self.test_partner._compute_preference_summary()
        
        self.assertTrue(self.test_partner.has_communication_preferences)
        self.assertEqual(self.test_partner.preference_count, 2)
        self.assertEqual(self.test_partner.opted_in_count, 1)
        self.assertEqual(self.test_partner.opted_out_count, 1)

    def test_can_send_communication(self):
        """Test can_send_communication method."""
        # Create preference
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'membership',
            'opted_in': True,
        })
        
        # Test allowed communication
        can_send = self.test_partner.can_send_communication('email', 'membership')
        self.assertTrue(can_send)
        
        # Test emergency communication (should always be allowed)
        can_send_emergency = self.test_partner.can_send_communication('email', 'emergency')
        self.assertTrue(can_send_emergency)
        
        # Create opted-out preference
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'sms',
            'category': 'marketing',
            'opted_in': False,
        })
        
        # Test not allowed communication
        can_send_marketing = self.test_partner.can_send_communication('sms', 'marketing')
        self.assertFalse(can_send_marketing)

    def test_set_communication_preference(self):
        """Test setting communication preferences."""
        # Set new preference
        pref = self.test_partner.set_communication_preference(
            'email', 'education', True,
            consent_source='test_method',
            consent_method='staff_update',
            ip_address='127.0.0.1'
        )
        
        self.assertTrue(pref.opted_in)
        self.assertEqual(pref.consent_source, 'test_method')
        self.assertEqual(pref.ip_address, '127.0.0.1')
        
        # Update existing preference
        updated_pref = self.test_partner.set_communication_preference(
            'email', 'education', False,
            consent_source='updated_method'
        )
        
        # Should be same record, just updated
        self.assertEqual(pref.id, updated_pref.id)
        self.assertFalse(updated_pref.opted_in)
        self.assertEqual(updated_pref.consent_source, 'updated_method')

    def test_create_default_communication_preferences(self):
        """Test creating default preferences."""
        # Initially no preferences
        self.assertEqual(len(self.test_partner.communication_preference_ids), 0)
        
        # Create defaults
        prefs = self.test_partner.create_default_communication_preferences()
        
        self.assertTrue(prefs)
        self.assertGreater(len(self.test_partner.communication_preference_ids), 0)
        
        # Should have preferences for communication types the partner can receive
        pref_types = self.test_partner.communication_preference_ids.mapped('communication_type')
        self.assertIn('email', pref_types)  # Has email
        self.assertIn('sms', pref_types)    # Has mobile
        self.assertIn('mail', pref_types)   # Has address

    def test_opt_out_all_marketing(self):
        """Test opting out of all marketing communications."""
        # Create marketing preferences
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
        })
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'sms',
            'category': 'marketing',
            'opted_in': True,
        })
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'events',  # Not marketing
            'opted_in': True,
        })
        
        # Opt out of all marketing
        result = self.test_partner.opt_out_all_marketing()
        self.assertTrue(result)
        
        # Check that marketing preferences are opted out
        marketing_prefs = self.test_partner.communication_preference_ids.filtered(
            lambda p: p.category == 'marketing'
        )
        for pref in marketing_prefs:
            self.assertFalse(pref.opted_in)
        
        # Events preference should still be opted in
        events_pref = self.test_partner.communication_preference_ids.filtered(
            lambda p: p.category == 'events'
        )
        self.assertTrue(events_pref.opted_in)

    def test_log_communication(self):
        """Test logging communications for a partner."""
        log = self.test_partner.log_communication(
            communication_type='email',
            category='committee',
            subject='Committee Meeting Notice',
            campaign_id='COMMITTEE_2024'
        )
        
        self.assertTrue(log.id)
        self.assertEqual(log.partner_id, self.test_partner)
        self.assertEqual(log.communication_type, 'email')
        self.assertEqual(log.category, 'committee')
        self.assertEqual(log.subject, 'Committee Meeting Notice')

    def test_get_communication_data_export(self):
        """Test GDPR data export."""
        # Create some test data
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'marketing',
            'opted_in': True,
            'consent_source': 'website_form'
        })
        
        self.CommunicationLog.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'membership',
            'subject': 'Welcome Message',
            'delivery_status': 'delivered'
        })
        
        # Export data
        export_data = self.test_partner.get_communication_data_export()
        
        self.assertEqual(export_data['partner_name'], self.test_partner.name)
        self.assertTrue(export_data['export_date'])
        self.assertEqual(len(export_data['communication_preferences']), 1)
        self.assertEqual(len(export_data['communication_history']), 1)
        self.assertIn('statistics', export_data)

    def test_get_preferred_communication_method(self):
        """Test getting preferred communication method."""
        # Create preferences with email opted in
        self.CommunicationPreference.create({
            'partner_id': self.test_partner.id,
            'communication_type': 'email',
            'category': 'membership',
            'opted_in': True,
        })
        
        # Should prefer email (first in preference order and available)
        preferred = self.test_partner.get_preferred_communication_method('membership')
        self.assertEqual(preferred, 'email')
        
        # Remove email address, should fall back to SMS
        self.test_partner.email = False
        preferred = self.test_partner.get_preferred_communication_method('membership')
        # Default should allow SMS for membership, and partner has mobile
        self.assertEqual(preferred, 'sms')

    def test_automatic_preference_creation_on_member_type_assignment(self):
        """Test that preferences are created when member type is assigned."""
        if not hasattr(self.env, 'ams.member.type'):
            self.skipTest("Member data module not available")
        
        # Create partner without member type
        partner = self.Partner.create({
            'name': 'New Member',
            'email': 'new@test.com',
            'is_company': False,
        })
        
        # Should have no preferences initially
        self.assertEqual(len(partner.communication_preference_ids), 0)
        
        # Assign member type
        partner.member_type_id = self.member_type.id
        
        # Should now have default preferences
        self.assertGreater(len(partner.communication_preference_ids), 0)