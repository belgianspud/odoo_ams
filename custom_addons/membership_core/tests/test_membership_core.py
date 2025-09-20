# -*- coding: utf-8 -*-
# Part of Association Management Software (AMS)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class TestMembershipCore(TransactionCase):

    def setUp(self):
        super().setUp()
        self.MembershipType = self.env['membership.type']
        self.Membership = self.env['membership.membership']
        self.Partner = self.env['res.partner']
        self.AccountMove = self.env['account.move']
        self.CreateWizard = self.env['membership.create.wizard']
        self.RenewalWizard = self.env['membership.renewal.wizard']
        
        # Create test membership types
        self.individual_type = self.MembershipType.create({
            'name': 'Individual Basic',
            'code': 'IND_BASIC',
            'membership_category': 'individual',
            'price': 100.00,
            'duration': 12,
            'grace_period': 30,
            'suspend_period': 60,
            'terminate_period': 30,
        })
        
        self.organization_type = self.MembershipType.create({
            'name': 'Organization Standard',
            'code': 'ORG_STD',
            'membership_category': 'organization',
            'price': 500.00,
            'duration': 12,
        })
        
        self.lifetime_type = self.MembershipType.create({
            'name': 'Lifetime Member',
            'code': 'LIFETIME',
            'membership_category': 'individual',
            'price': 2500.00,
            'duration': 0,
        })
        
        # Create test partners
        self.individual_partner = self.Partner.create({
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'is_company': False,
        })
        
        self.company_partner = self.Partner.create({
            'name': 'Tech Corp Inc',
            'email': 'info@techcorp.com',
            'is_company': True,
        })

    def test_membership_creation(self):
        """Test basic membership creation"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'draft',
            'amount_paid': 100.00,
        })
        
        self.assertEqual(membership.partner_id, self.individual_partner)
        self.assertEqual(membership.membership_type_id, self.individual_type)
        self.assertEqual(membership.state, 'draft')
        self.assertEqual(membership.amount_paid, 100.00)
        self.assertNotEqual(membership.name, 'New')  # Should get sequence number

    def test_membership_activation(self):
        """Test membership activation process"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'draft',
            'amount_paid': 100.00,
        })
        
        # Activate membership
        membership.action_activate()
        
        self.assertEqual(membership.state, 'active')
        self.assertEqual(membership.start_date, fields.Date.today())
        self.assertIsNotNone(membership.end_date)
        
        # Check end date calculation for non-lifetime membership
        expected_end_date = fields.Date.today() + relativedelta(months=12)
        self.assertEqual(membership.end_date, expected_end_date)

    def test_lifetime_membership_activation(self):
        """Test lifetime membership activation"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.lifetime_type.id,
            'state': 'draft',
            'amount_paid': 2500.00,
        })
        
        membership.action_activate()
        
        self.assertEqual(membership.state, 'active')
        self.assertFalse(membership.end_date)  # No end date for lifetime

    def test_parent_membership_exclusivity(self):
        """Test that only one parent membership is allowed per partner"""
        # Create first active membership
        first_membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today(),
            'amount_paid': 100.00,
        })
        
        # Try to create second parent membership - should fail
        with self.assertRaises(ValidationError):
            second_membership = self.Membership.create({
                'partner_id': self.individual_partner.id,
                'membership_type_id': self.organization_type.id,
                'state': 'active',
                'start_date': fields.Date.today(),
                'amount_paid': 500.00,
            })
            second_membership._check_parent_membership_exclusivity()

    def test_membership_renewal(self):
        """Test membership renewal functionality"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today() - timedelta(days=300),
            'end_date': fields.Date.today() + timedelta(days=65),
            'amount_paid': 100.00,
        })
        
        original_end_date = membership.end_date
        
        # Renew membership
        membership.action_renew(amount_paid=100.00)
        
        self.assertEqual(membership.state, 'active')
        self.assertTrue(membership.end_date > original_end_date)
        self.assertEqual(membership.amount_paid, 200.00)

    def test_membership_suspension(self):
        """Test membership suspension"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today(),
            'amount_paid': 100.00,
        })
        
        membership.action_suspend(reason="Test suspension")
        
        self.assertEqual(membership.state, 'suspended')
        self.assertIsNotNone(membership.suspension_end_date)

    def test_membership_termination(self):
        """Test membership termination"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today(),
            'amount_paid': 100.00,
        })
        
        membership.action_terminate(reason="Test termination")
        
        self.assertEqual(membership.state, 'terminated')
        self.assertEqual(membership.termination_date, fields.Date.today())

    def test_membership_cancellation(self):
        """Test membership cancellation"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today(),
            'amount_paid': 100.00,
        })
        
        membership.action_cancel(reason="Test cancellation")
        
        self.assertEqual(membership.state, 'cancelled')

    def test_days_until_expiry_calculation(self):
        """Test days until expiry calculation"""
        # Future expiry
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today() + timedelta(days=30),
        })
        
        days_until_expiry = membership.get_days_until_expiry()
        self.assertEqual(days_until_expiry, 30)
        
        # Past expiry
        membership.end_date = fields.Date.today() - timedelta(days=10)
        days_until_expiry = membership.get_days_until_expiry()
        self.assertEqual(days_until_expiry, 0)
        
        # Lifetime membership
        membership.end_date = False
        days_until_expiry = membership.get_days_until_expiry()
        self.assertIsNone(days_until_expiry)

    def test_is_expiring_soon(self):
        """Test expiring soon detection"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today() + timedelta(days=15),
        })
        
        self.assertTrue(membership.is_expiring_soon(30))
        self.assertTrue(membership.is_expiring_soon(20))
        self.assertFalse(membership.is_expiring_soon(10))

    def test_partner_membership_status_computation(self):
        """Test partner membership status computation"""
        # Initially not a member
        self.assertFalse(self.individual_partner.is_member)
        self.assertFalse(self.individual_partner.active_membership_id)
        
        # Create active membership
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today(),
            'amount_paid': 100.00,
        })
        
        # Trigger computation
        self.individual_partner._compute_membership_status()
        
        self.assertTrue(self.individual_partner.is_member)
        self.assertEqual(self.individual_partner.active_membership_id, membership)
        self.assertEqual(self.individual_partner.membership_state, 'active')

    def test_partner_membership_statistics(self):
        """Test partner membership statistics computation"""
        # Create multiple memberships
        active_membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today(),
            'amount_paid': 100.00,
        })
        
        terminated_membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'terminated',
            'start_date': fields.Date.today() - timedelta(days=400),
            'amount_paid': 100.00,
        })
        
        # Trigger computation
        self.individual_partner._compute_membership_statistics()
        
        self.assertEqual(self.individual_partner.membership_count, 2)
        self.assertEqual(self.individual_partner.active_membership_count, 1)
        self.assertEqual(self.individual_partner.total_membership_paid, 200.00)

    def test_partner_action_view_memberships(self):
        """Test partner action to view memberships"""
        action = self.individual_partner.action_view_memberships()
        
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'membership.membership')
        self.assertIn(('partner_id', '=', self.individual_partner.id), action['domain'])

    def test_partner_has_active_membership_type(self):
        """Test checking if partner has specific active membership type"""
        # Initially false
        self.assertFalse(self.individual_partner.has_active_membership_type(self.individual_type.id))
        
        # Create active membership
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today(),
        })
        
        self.assertTrue(self.individual_partner.has_active_membership_type(self.individual_type.id))
        self.assertFalse(self.individual_partner.has_active_membership_type(self.organization_type.id))

    def test_create_membership_wizard(self):
        """Test membership creation wizard"""
        wizard = self.CreateWizard.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'start_date': fields.Date.today(),
            'amount_paid': 100.00,
            'auto_activate': True,
        })
        
        # Test validation
        wizard._compute_validation_info()
        self.assertFalse(wizard.has_conflicting_membership)
        
        # Create membership
        result = wizard.action_create_membership()
        
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'membership.membership')
        
        # Check membership was created
        created_membership = self.Membership.browse(result['res_id'])
        self.assertEqual(created_membership.partner_id, self.individual_partner)
        self.assertEqual(created_membership.state, 'active')

    def test_create_membership_wizard_new_partner(self):
        """Test creating membership with new partner"""
        wizard = self.CreateWizard.create({
            'is_new_partner': True,
            'partner_name': 'New Test Partner',
            'partner_email': 'new@example.com',
            'partner_is_company': False,
            'membership_type_id': self.individual_type.id,
            'start_date': fields.Date.today(),
            'amount_paid': 100.00,
            'auto_activate': True,
        })
        
        result = wizard.action_create_membership()
        
        # Check that new partner was created
        created_membership = self.Membership.browse(result['res_id'])
        self.assertEqual(created_membership.partner_id.name, 'New Test Partner')
        self.assertEqual(created_membership.partner_id.email, 'new@example.com')

    def test_create_membership_wizard_conflict_detection(self):
        """Test conflict detection in create wizard"""
        # Create existing active membership
        existing_membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today(),
        })
        
        # Try to create conflicting membership
        wizard = self.CreateWizard.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.organization_type.id,  # Different type but same category conflict
            'start_date': fields.Date.today(),
            'amount_paid': 500.00,
        })
        
        wizard._compute_validation_info()
        self.assertTrue(wizard.has_conflicting_membership)
        self.assertIn('parent membership', wizard.validation_message)

    def test_renewal_wizard(self):
        """Test membership renewal wizard"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today() - timedelta(days=300),
            'end_date': fields.Date.today() + timedelta(days=65),
            'amount_paid': 100.00,
        })
        
        wizard = self.RenewalWizard.create({
            'membership_id': membership.id,
            'renewal_type': 'standard',
            'payment_received': True,
            'amount_paid': 100.00,
        })
        
        # Test calculations
        wizard._compute_new_end_date()
        wizard._compute_renewal_price()
        wizard._compute_final_price()
        
        self.assertTrue(wizard.can_renew)
        self.assertEqual(wizard.renewal_price, 100.00)
        self.assertEqual(wizard.final_price, 100.00)
        
        # Process renewal
        result = wizard.action_renew_membership()
        
        # Check membership was renewed
        membership.refresh()
        self.assertEqual(membership.state, 'active')
        self.assertEqual(membership.amount_paid, 200.00)

    def test_renewal_wizard_custom_period(self):
        """Test renewal wizard with custom period"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today() + timedelta(days=30),
        })
        
        wizard = self.RenewalWizard.create({
            'membership_id': membership.id,
            'renewal_type': 'custom_period',
            'renewal_months': 6,
            'payment_received': True,
            'amount_paid': 50.00,
        })
        
        wizard._compute_renewal_price()
        # Should be prorated: 100 * (6/12) = 50
        self.assertEqual(wizard.renewal_price, 50.00)

    def test_renewal_wizard_lifetime_conversion(self):
        """Test converting to lifetime membership"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today(),
            'end_date': fields.Date.today() + timedelta(days=30),
        })
        
        wizard = self.RenewalWizard.create({
            'membership_id': membership.id,
            'renewal_type': 'lifetime',
            'payment_received': True,
            'amount_paid': 1000.00,
        })
        
        wizard._compute_renewal_price()
        self.assertEqual(wizard.renewal_price, 1000.00)  # 10x base price
        
        wizard.action_renew_membership()
        
        membership.refresh()
        self.assertFalse(membership.end_date)  # No end date for lifetime

    def test_cron_update_membership_states(self):
        """Test automated membership state updates"""
        # Create expired membership
        expired_membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today() - timedelta(days=400),
            'end_date': fields.Date.today() - timedelta(days=5),  # Expired 5 days ago
        })
        
        # Run cron job
        self.Membership._cron_update_membership_states()
        
        expired_membership.refresh()
        self.assertEqual(expired_membership.state, 'grace')
        self.assertIsNotNone(expired_membership.grace_end_date)

    def test_cron_send_renewal_reminders(self):
        """Test automated renewal reminders"""
        # Create membership expiring in 30 days
        expiring_membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'state': 'active',
            'start_date': fields.Date.today() - timedelta(days=335),
            'end_date': fields.Date.today() + timedelta(days=30),
            'renewal_reminder_sent': False,
        })
        
        # Create renewal template
        renewal_template = self.env['mail.template'].create({
            'name': 'Test Renewal Template',
            'model_id': self.env.ref('membership_core.model_membership_membership').id,
            'subject': 'Renewal Reminder',
            'body_html': '<p>Your membership expires soon</p>',
        })
        self.individual_type.renewal_template_id = renewal_template.id
        
        # Run cron job
        self.Membership._cron_send_renewal_reminders()
        
        expiring_membership.refresh()
        self.assertTrue(expiring_membership.renewal_reminder_sent)

    def test_account_move_integration(self):
        """Test integration with account.move (invoices)"""
        # Create invoice line with membership type
        invoice = self.AccountMove.create({
            'partner_id': self.individual_partner.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': 'Membership Fee',
                'quantity': 1.0,
                'price_unit': 100.00,
                'membership_type_id': self.individual_type.id,
            })]
        })
        
        # Check that line is marked as membership line
        membership_line = invoice.invoice_line_ids[0]
        membership_line._compute_is_membership_line()
        self.assertTrue(membership_line.is_membership_line)
        
        # Check invoice is marked as membership invoice
        invoice._compute_is_membership_invoice()
        self.assertTrue(invoice.is_membership_invoice)

    def test_sequence_generation(self):
        """Test membership number sequence generation"""
        membership1 = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
        })
        
        membership2 = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
        })
        
        self.assertNotEqual(membership1.name, 'New')
        self.assertNotEqual(membership2.name, 'New')
        self.assertNotEqual(membership1.name, membership2.name)

    def test_display_name_computation(self):
        """Test membership display name computation"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
        })
        
        membership._compute_display_name()
        expected_display_name = f"{membership.name} - {self.individual_partner.name}"
        self.assertEqual(membership.display_name, expected_display_name)

    def test_renewal_date_computation(self):
        """Test renewal date computation"""
        membership = self.Membership.create({
            'partner_id': self.individual_partner.id,
            'membership_type_id': self.individual_type.id,
            'end_date': fields.Date.today() + timedelta(days=60),
        })
        
        membership._compute_renewal_date()
        expected_renewal_date = membership.end_date - timedelta(days=30)
        self.assertEqual(membership.renewal_date, expected_renewal_date)