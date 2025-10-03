# -*- coding: utf-8 -*-
{
    'name': 'Membership - Professional Extensions',
    'version': '1.0.0',
    'category': 'Membership',
    'summary': 'Professional credentials, specialties, and license tracking for membership management',
    'description': """
Membership Professional Extensions
===================================

Adds comprehensive professional credential and license tracking for membership associations:

**Key Features:**

* **Professional Credentials**
  - Track academic degrees (MD, PhD, etc.)
  - Professional licenses (PE, CPA, etc.)
  - Certifications and designations
  - Credential history with verification
  
* **Professional Specialties**
  - Hierarchical specialty management
  - Multiple specialties per member
  - Specialty-based segmentation
  
* **License Tracking**
  - License expiration monitoring
  - Automated expiration reminders
  - Continuing education (CE) tracking
  - Verification workflow
  - Multi-jurisdiction support
  
* **Employment Information**
  - Current employer tracking
  - Years of experience calculation
  - Industry sector classification
  - Job title and department
  
* **Continuing Education**
  - CE hours tracking per license
  - CE compliance monitoring
  - Requirements management
  
* **Verification & Compliance**
  - Document attachment support
  - Verification workflow
  - Automated compliance checks
  - Reporting and notifications

**Perfect for:**
- Medical associations (ACEP, AMA)
- Engineering societies (AIAA, ASCE)
- Professional certifying bodies
- Any association requiring credential verification
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'membership_community',
        'mail',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/credential_data.xml',
        'data/specialty_data.xml',
        'data/email_templates.xml',
        'data/ir_cron.xml',
        'data/ir_sequence.xml',
        
        # Views
        'views/membership_credential_views.xml',
        'views/membership_specialty_views.xml',
        'views/membership_license_views.xml',
        'views/membership_certification_views.xml',
        'views/res_partner_views.xml',
        'views/menu_views.xml',
        
        # Reports
        'report/member_credential_report.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}