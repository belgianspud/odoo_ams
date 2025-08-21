# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestMemberID(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.MemberProfile = self.env['ams.member.profile']
        
    def test_member_id_generation(self):
        """Test automatic member ID generation"""
        partner = self.Partner.create({
            'name': 'Test Member',
            'is_member': True,
        })
        
        self.assertTrue(partner.member_id)
        self.assertTrue(partner.member_id.startswith('MEM-'))
        self.assertEqual(partner.member_status, 'prospect')  # Default status
        
    def test_member_id_uniqueness(self):
        """Test member ID uniqueness constraint"""
        partner1 = self.Partner.create({
            'name': 'Member 1',
            'is_member': True,
        })
        
        # Try to create duplicate member ID (should fail)
        with self.assertRaises(ValidationError):
            partner2 = self.Partner.create({
                'name': 'Member 2',
                'is_member': True,
            })
            partner2.member_id = partner1.member_id
            
    def test_email_uniqueness_for_members(self):
        """Test email uniqueness among active members"""
        partner1 = self.Partner.create({
            'name': 'Member 1',
            'email': 'test@example.com',
            'is_member': True,
            'member_status': 'active',
        })
        
        # Try to create another active member with same email
        with self.assertRaises(ValidationError):
            self.Partner.create({
                'name': 'Member 2',
                'email': 'test@example.com',
                'is_member': True,
                'member_status': 'active',
            })
            
    def test_make_member_action(self):
        """Test converting prospect to member"""
        partner = self.Partner.create({
            'name': 'Test Prospect',
            'email': 'prospect@example.com',
            'member_status': 'prospect',
        })
        
        self.assertFalse(partner.is_member)
        
        # Convert to member
        partner.action_make_member()
        
        self.assertTrue(partner.is_member)
        self.assertEqual(partner.member_status, 'active')
        self.assertTrue(partner.member_id)
        self.assertTrue(partner.member_since)
        
    def test_member_profile_creation(self):
        """Test member profile creation and completeness"""
        partner = self.Partner.create({
            'name': 'Test Member',
            'is_member': True,
        })
        
        profile = self.MemberProfile.create({
            'partner_id': partner.id,
            'graduation_year': 2020,
            'graduation_institution': 'Test University',
            'volunteer_status': 'available',
        })
        
        # Check profile completeness calculation
        profile._compute_profile_completeness()
        self.assertGreater(profile.profile_completeness, 0)
        self.assertLessEqual(profile.profile_completeness, 100)
        
    def test_partner_unique_profile(self):
        """Test that each partner can only have one profile"""
        partner = self.Partner.create({
            'name': 'Test Member',
            'is_member': True,
        })
        
        # Create first profile
        profile1 = self.MemberProfile.create({
            'partner_id': partner.id,
        })
        
        # Try to create second profile for same partner
        with self.assertRaises(ValidationError):
            self.MemberProfile.create({
                'partner_id': partner.id,
            })
            
    def test_age_computation(self):
        """Test age computation from date of birth"""
        from datetime import date
        
        partner = self.Partner.create({
            'name': 'Test Member',
            'date_of_birth': date(1990, 1, 1),
        })
        
        partner._compute_age()
        self.assertGreater(partner.age, 30)  # Should be around 35 as of 2025
        
    def test_name_get_with_member_id(self):
        """Test name_get includes member ID and preferred name"""
        partner = self.Partner.create({
            'name': 'John Doe',
            'preferred_name': 'Johnny',
            'is_member': True,
        })
        
        name_get_result = partner.name_get()[0][1]
        
        self.assertIn(partner.member_id, name_get_result)
        self.assertIn('Johnny', name_get_result)
        self.assertIn('John Doe', name_get_result)
        
    def test_career_stage_options(self):
        """Test career stage field options"""
        partner = self.Partner.create({
            'name': 'Test Member',
            'career_stage': 'mid_career',
        })
        
        self.assertEqual(partner.career_stage, 'mid_career')
        
        # Test all valid options
        valid_stages = ['student', 'early_career', 'mid_career', 'senior', 'retired']
        for stage in valid_stages:
            partner.career_stage = stage
            self.assertEqual(partner.career_stage, stage)
            
    def test_organization_fields(self):
        """Test organization-specific fields"""
        org = self.Partner.create({
            'name': 'Test Hospital',
            'is_company': True,
            'organization_type': 'hospital',
            'industry_sector': 'Healthcare',
            'employee_count_bracket': '201_1000',
        })
        
        self.assertTrue(org.is_company)
        self.assertEqual(org.organization_type, 'hospital')
        self.assertEqual(org.industry_sector, 'Healthcare')
        self.assertEqual(org.employee_count_bracket, '201_1000')