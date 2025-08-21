# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class TestProfessionalDesignation(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.ProfessionalDesignation = self.env['ams.professional.designation']
        self.MemberDesignation = self.env['ams.member.designation']
        self.Partner = self.env['res.partner']
        
    def test_designation_creation(self):
        """Test professional designation creation"""
        designation = self.ProfessionalDesignation.create({
            'name': 'Test Certification',
            'code': 'TC',
            'designation_type': 'certification',
            'issuing_body': 'Test Board',
            'requires_continuing_education': True,
            'ce_hours_required': 20,
        })
        
        self.assertEqual(designation.name, 'Test Certification')
        self.assertEqual(designation.code, 'TC')
        self.assertTrue(designation.requires_continuing_education)
        self.assertEqual(designation.ce_hours_required, 20)
        
    def test_designation_code_unique(self):
        """Test designation code uniqueness constraint"""
        self.ProfessionalDesignation.create({
            'name': 'First Designation',
            'code': 'UNIQUE',
            'designation_type': 'certification',
            'issuing_body': 'Test Board',
        })
        
        # Try to create duplicate code
        with self.assertRaises(ValidationError):
            self.ProfessionalDesignation.create({
                'name': 'Second Designation', 
                'code': 'UNIQUE',
                'designation_type': 'license',
                'issuing_body': 'Other Board',
            })
            
    def test_member_designation_creation(self):
        """Test member designation assignment"""
        partner = self.Partner.create({
            'name': 'Test Professional',
            'is_member': True,
        })
        
        designation = self.ProfessionalDesignation.create({
            'name': 'Professional License',
            'code': 'PL',
            'designation_type': 'license',
            'issuing_body': 'State Board',
            'has_expiration': True,
            'renewal_period_months': 24,
        })
        
        member_designation = self.MemberDesignation.create({
            'partner_id': partner.id,
            'designation_id': designation.id,
            'license_number': 'L123456',
            'earned_date': date(2020, 1, 1),
            'expiration_date': date(2025, 1, 1),
            'issuing_jurisdiction': 'Test State',
        })
        
        self.assertEqual(member_designation.partner_id, partner)
        self.assertEqual(member_designation.designation_id, designation)
        self.assertEqual(member_designation.license_number, 'L123456')
        self.assertEqual(member_designation.status, 'active')
        
    def test_member_designation_expiration(self):
        """Test member designation expiration computation"""
        partner = self.Partner.create({
            'name': 'Test Professional',
            'is_member': True,
        })
        
        designation = self.ProfessionalDesignation.create({
            'name': 'Expiring License',
            'code': 'EL',
            'designation_type': 'license',
            'issuing_body': 'State Board',
        })
        
        # Create expired designation
        expired_designation = self.MemberDesignation.create({
            'partner_id': partner.id,
            'designation_id': designation.id,
            'earned_date': date(2020, 1, 1),
            'expiration_date': date.today() - timedelta(days=30),
        })
        
        expired_designation._compute_is_expired()
        self.assertTrue(expired_designation.is_expired)
        
        # Create soon-to-expire designation
        expiring_designation = self.MemberDesignation.create({
            'partner_id': partner.id,
            'designation_id': designation.id,
            'earned_date': date(2020, 1, 1),
            'expiration_date': date.today() + timedelta(days=30),
        })
        
        expiring_designation._compute_days_until_expiration()
        self.assertAlmostEqual(expiring_designation.days_until_expiration, 30, delta=1)


class TestMemberSpecialty(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.MemberSpecialty = self.env['ams.member.specialty']
        self.MemberSpecialtyLine = self.env['ams.member.specialty.line']
        self.Partner = self.env['res.partner']
        
    def test_specialty_creation(self):
        """Test member specialty creation"""
        specialty = self.MemberSpecialty.create({
            'name': 'Cardiology',
            'code': 'CARD',
            'specialty_type': 'clinical',
            'requires_certification': True,
            'certification_body': 'American Board of Internal Medicine',
        })
        
        self.assertEqual(specialty.name, 'Cardiology')
        self.assertEqual(specialty.code, 'CARD')
        self.assertTrue(specialty.requires_certification)
        
    def test_specialty_hierarchy(self):
        """Test specialty parent-child relationships"""
        parent_specialty = self.MemberSpecialty.create({
            'name': 'Internal Medicine',
            'code': 'IM',
            'specialty_type': 'clinical',
        })
        
        child_specialty = self.MemberSpecialty.create({
            'name': 'Cardiology',
            'code': 'CARD',
            'specialty_type': 'subspecialty',
            'parent_specialty_id': parent_specialty.id,
        })
        
        self.assertEqual(child_specialty.parent_specialty_id, parent_specialty)
        self.assertIn(child_specialty, parent_specialty.child_specialty_ids)
        
    def test_specialty_recursion_check(self):
        """Test prevention of circular specialty references"""
        specialty1 = self.MemberSpecialty.create({
            'name': 'Specialty 1',
            'code': 'SP1',
            'specialty_type': 'clinical',
        })
        
        specialty2 = self.MemberSpecialty.create({
            'name': 'Specialty 2', 
            'code': 'SP2',
            'specialty_type': 'subspecialty',
            'parent_specialty_id': specialty1.id,
        })
        
        # Try to create circular reference
        with self.assertRaises(ValidationError):
            specialty1.parent_specialty_id = specialty2.id
            
    def test_member_specialty_assignment(self):
        """Test assigning specialties to members"""
        partner = self.Partner.create({
            'name': 'Test Doctor',
            'is_member': True,
        })
        
        specialty = self.MemberSpecialty.create({
            'name': 'Emergency Medicine',
            'code': 'EM',
            'specialty_type': 'clinical',
        })
        
        specialty_line = self.MemberSpecialtyLine.create({
            'partner_id': partner.id,
            'specialty_id': specialty.id,
            'is_primary': True,
            'proficiency_level': 'advanced',
            'date_acquired': date(2018, 1, 1),
            'years_experience': 5,
        })
        
        self.assertEqual(specialty_line.partner_id, partner)
        self.assertEqual(specialty_line.specialty_id, specialty)
        self.assertTrue(specialty_line.is_primary)
        self.assertEqual(specialty_line.proficiency_level, 'advanced')
        
    def test_single_primary_specialty(self):
        """Test that members can only have one primary specialty"""
        partner = self.Partner.create({
            'name': 'Test Doctor',
            'is_member': True,
        })
        
        specialty1 = self.MemberSpecialty.create({
            'name': 'Specialty 1',
            'code': 'SP1',
            'specialty_type': 'clinical',
        })
        
        specialty2 = self.MemberSpecialty.create({
            'name': 'Specialty 2',
            'code': 'SP2', 
            'specialty_type': 'clinical',
        })
        
        # Create first primary specialty
        self.MemberSpecialtyLine.create({
            'partner_id': partner.id,
            'specialty_id': specialty1.id,
            'is_primary': True,
        })
        
        # Try to create second primary specialty - should fail
        with self.assertRaises(ValidationError):
            self.MemberSpecialtyLine.create({
                'partner_id': partner.id,
                'specialty_id': specialty2.id,
                'is_primary': True,
            })


class TestProfessionalPartnerExtension(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.ProfessionalDesignation = self.env['ams.professional.designation']
        self.MemberSpecialty = self.env['ams.member.specialty']
        
    def test_partner_professional_fields(self):
        """Test partner professional field extensions"""
        partner = self.Partner.create({
            'name': 'Dr. Test Professional',
            'is_member': True,
            'practice_name': 'Test Medical Practice',
            'practice_type': 'clinic',
            'years_in_practice': 10,
            'license_certification_number': 'L123456',
            'license_status': 'active',
        })
        
        self.assertEqual(partner.practice_name, 'Test Medical Practice')
        self.assertEqual(partner.practice_type, 'clinic')
        self.assertEqual(partner.years_in_practice, 10)
        self.assertEqual(partner.license_certification_number, 'L123456')
        self.assertEqual(partner.license_status, 'active')
        
    def test_orcid_validation(self):
        """Test ORCID ID format validation"""
        partner = self.Partner.create({
            'name': 'Test Researcher',
            'is_member': True,
        })
        
        # Valid ORCID ID
        partner.orcid_id = '0000-0000-0000-0000'
        self.assertEqual(partner.orcid_id, '0000-0000-0000-0000')
        
        # Invalid ORCID ID should raise validation error
        with self.assertRaises(ValidationError):
            partner.orcid_id = 'invalid-orcid'
            
    def test_professional_credentials_computation(self):
        """Test computation of professional credentials summary"""
        partner = self.Partner.create({
            'name': 'Test Professional',
            'is_member': True,
        })
        
        # Create designations
        md_designation = self.ProfessionalDesignation.create({
            'name': 'Doctor of Medicine',
            'code': 'MD',
            'designation_type': 'degree',
            'issuing_body': 'Medical School',
        })
        
        board_cert = self.ProfessionalDesignation.create({
            'name': 'Board Certified',
            'code': 'BC',
            'designation_type': 'certification',
            'issuing_body': 'Medical Board',
        })
        
        # Assign designations to partner
        self.env['ams.member.designation'].create({
            'partner_id': partner.id,
            'designation_id': md_designation.id,
            'status': 'active',
        })
        
        self.env['ams.member.designation'].create({
            'partner_id': partner.id,
            'designation_id': board_cert.id,
            'status': 'active',
        })
        
        partner._compute_professional_credentials()
        self.assertIn('MD', partner.professional_credentials)
        self.assertIn('BC', partner.professional_credentials)
        
    def test_professional_compliance_status(self):
        """Test professional compliance status computation"""
        partner = self.Partner.create({
            'name': 'Test Professional',
            'is_member': True,
            'license_status': 'active',
        })
        
        # Create designation
        designation = self.ProfessionalDesignation.create({
            'name': 'Professional License',
            'code': 'PL',
            'designation_type': 'license',
            'issuing_body': 'State Board',
        })
        
        # Create active member designation
        self.env['ams.member.designation'].create({
            'partner_id': partner.id,
            'designation_id': designation.id,
            'expiration_date': date.today() + timedelta(days=365),
            'status': 'active',
        })
        
        partner._compute_professional_compliance_status()
        self.assertEqual(partner.professional_compliance_status, 'compliant')
        
    def test_ce_hours_computation(self):
        """Test continuing education hours requirement computation"""
        partner = self.Partner.create({
            'name': 'Test Professional',
            'is_member': True,
        })
        
        # Create designation with CE requirements
        designation = self.ProfessionalDesignation.create({
            'name': 'Licensed Professional',
            'code': 'LP',
            'designation_type': 'license',
            'issuing_body': 'State Board',
            'requires_continuing_education': True,
            'ce_hours_required': 30,
        })
        
        # Create specialty with CE requirements
        specialty = self.MemberSpecialty.create({
            'name': 'Specialty Area',
            'code': 'SA',
            'specialty_type': 'clinical',
            'has_continuing_education': True,
            'ce_hours_annual': 15,
        })
        
        # Assign to partner
        self.env['ams.member.designation'].create({
            'partner_id': partner.id,
            'designation_id': designation.id,
            'status': 'active',
        })
        
        self.env['ams.member.specialty.line'].create({
            'partner_id': partner.id,
            'specialty_id': specialty.id,
            'status': 'active',
        })
        
        partner._compute_ce_hours_required()
        self.assertEqual(partner.ce_hours_required, 45)  # 30 + 15


class TestMemberProfileProfessional(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.MemberProfile = self.env['ams.member.profile']
        
    def test_social_media_validation(self):
        """Test social media field validation"""
        partner = self.Partner.create({
            'name': 'Test Member',
            'is_member': True,
        })
        
        profile = self.MemberProfile.create({
            'partner_id': partner.id,
        })
        
        # Valid LinkedIn URL
        profile.linkedin_url = 'https://linkedin.com/in/testuser'
        self.assertEqual(profile.linkedin_url, 'https://linkedin.com/in/testuser')
        
        # Invalid LinkedIn URL should raise validation error
        with self.assertRaises(ValidationError):
            profile.linkedin_url = 'https://facebook.com/testuser'
            
        # Valid Twitter handle
        profile.twitter_handle = 'testuser'
        self.assertEqual(profile.twitter_handle, 'testuser')
        
        # Twitter handle with @ should be cleaned
        profile.twitter_handle = '@testuser'
        self.assertEqual(profile.twitter_handle, 'testuser')
        
    def test_year_validation(self):
        """Test year field validation"""
        partner = self.Partner.create({
            'name': 'Test Member',
            'is_member': True,
        })
        
        profile = self.MemberProfile.create({
            'partner_id': partner.id,
        })
        
        # Valid graduation year
        current_year = date.today().year
        profile.graduation_year = current_year - 5
        self.assertEqual(profile.graduation_year, current_year - 5)
        
        # Invalid graduation year (too far in future)
        with self.assertRaises(ValidationError):
            profile.graduation_year = current_year + 20
            
        # Invalid graduation year (too old)
        with self.assertRaises(ValidationError):
            profile.graduation_year = 1800
            
    def test_research_metrics_validation(self):
        """Test research metrics validation"""
        partner = self.Partner.create({
            'name': 'Test Researcher',
            'is_member': True,
        })
        
        profile = self.MemberProfile.create({
            'partner_id': partner.id,
        })
        
        # Valid research metrics
        profile.h_index = 25
        profile.publications_count = 50
        self.assertEqual(profile.h_index, 25)
        self.assertEqual(profile.publications_count, 50)
        
        # Invalid negative values should raise validation error
        with self.assertRaises(ValidationError):
            profile.h_index = -5
            
        with self.assertRaises(ValidationError):
            profile.publications_count = -10
            
    def test_professional_links_method(self):
        """Test get_professional_links method"""
        partner = self.Partner.create({
            'name': 'Test Professional',
            'is_member': True,
        })
        
        profile = self.MemberProfile.create({
            'partner_id': partner.id,
            'linkedin_url': 'https://linkedin.com/in/testuser',
            'twitter_handle': 'testuser',
            'github_profile': 'https://github.com/testuser',
        })
        
        links = profile.get_professional_links()
        
        self.assertIn('LinkedIn', links)
        self.assertIn('Twitter', links)
        self.assertIn('GitHub', links)
        self.assertEqual(links['LinkedIn'], 'https://linkedin.com/in/testuser')
        self.assertEqual(links['Twitter'], 'https://twitter.com/testuser')
        self.assertEqual(links['GitHub'], 'https://github.com/testuser')
        
    def test_networking_availability_method(self):
        """Test get_networking_availability method"""
        partner = self.Partner.create({
            'name': 'Test Professional',
            'is_member': True,
        })
        
        profile = self.MemberProfile.create({
            'partner_id': partner.id,
            'available_for_mentoring': True,
            'available_for_speaking': True,
            'seeking_mentorship': False,
            'networking_interests': 'Professional development, Research collaboration',
        })
        
        availability = profile.get_networking_availability()
        
        self.assertTrue(availability['available_for_mentoring'])
        self.assertTrue(availability['available_for_speaking'])
        self.assertFalse(availability['seeking_mentorship'])
        self.assertIn('Professional development', availability['networking_interests'])


class TestProfessionalIntegration(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.ProfessionalDesignation = self.env['ams.professional.designation']
        self.MemberSpecialty = self.env['ams.member.specialty']
        self.MemberProfile = self.env['ams.member.profile']
        
    def test_complete_professional_member_setup(self):
        """Test complete professional member setup workflow"""
        # Create member
        partner = self.Partner.create({
            'name': 'Dr. Jane Smith',
            'email': 'jane.smith@example.com',
            'is_member': True,
            'practice_name': 'Smith Medical Group',
            'practice_type': 'group',
            'years_in_practice': 15,
            'license_certification_number': 'MD123456',
        })
        
        # Create member profile
        profile = self.MemberProfile.create({
            'partner_id': partner.id,
            'alma_mater': 'Harvard Medical School',
            'graduation_year': 2008,
            'linkedin_url': 'https://linkedin.com/in/janesmith',
            'publications_count': 25,
            'h_index': 12,
            'available_for_mentoring': True,
        })
        
        # Create professional designation
        md_designation = self.ProfessionalDesignation.create({
            'name': 'Doctor of Medicine',
            'code': 'MD',
            'designation_type': 'degree',
            'issuing_body': 'Harvard Medical School',
        })
        
        # Create specialty
        cardiology = self.MemberSpecialty.create({
            'name': 'Cardiology',
            'code': 'CARD',
            'specialty_type': 'clinical',
            'requires_certification': True,
        })
        
        # Assign designation to member
        self.env['ams.member.designation'].create({
            'partner_id': partner.id,
            'designation_id': md_designation.id,
            'earned_date': date(2008, 5, 15),
            'status': 'active',
        })
        
        # Assign specialty to member
        self.env['ams.member.specialty.line'].create({
            'partner_id': partner.id,
            'specialty_id': cardiology.id,
            'is_primary': True,
            'proficiency_level': 'expert',
            'date_acquired': date(2012, 1, 1),
            'years_experience': 12,
            'is_board_certified': True,
        })
        
        # Test computed fields
        partner._compute_professional_credentials()
        partner._compute_specialty_summary()
        partner._compute_primary_specialty()
        
        self.assertIn('MD', partner.professional_credentials)
        self.assertEqual(partner.primary_specialty_id, cardiology)
        self.assertIn('Cardiology', partner.specialty_summary)
        self.assertEqual(partner.designation_count, 1)
        self.assertEqual(partner.specialty_count, 1)
        
        # Test professional summary
        summary = partner.get_professional_summary()
        self.assertIn('Dr. Jane Smith', summary)
        self.assertIn('MD', summary)
        self.assertIn('Cardiology', summary)
        self.assertIn('Smith Medical Group', summary)