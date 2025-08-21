# AMS Core Professional

Professional designations, specialties, licenses, and career tracking for the Association Management System.

## Overview

This module extends the AMS Core Base with professional-specific functionality for managing member credentials, specialties, and professional development tracking.

## Features

### Professional Designations
- Manage degrees, certifications, licenses, and professional titles
- Track designation requirements (exams, experience, education)
- Handle renewal periods and continuing education requirements
- Monitor expiration dates and compliance status

### Member Specialties  
- Organize practice areas and subspecialties hierarchically
- Track member proficiency levels and years of experience
- Manage certification and board certification status
- Monitor practice settings and percentage allocation

### Professional Networking
- LinkedIn, ResearchGate, ORCID integration
- Academic and research network profiles
- Industry-specific professional networks
- Social media presence tracking

### Career Tracking
- Educational background and alma mater
- Publications and research metrics (H-index, citation counts)
- Professional service and volunteer activities
- Teaching, mentoring, and speaking availability

### Compliance Monitoring
- License status and expiration tracking
- Continuing education hour requirements
- Professional compliance scoring
- Automated renewal reminders

## Models

### `ams.professional.designation`
Defines professional designations like degrees, certifications, and licenses with their requirements and renewal periods.

### `ams.member.designation`  
Junction model linking members to their professional designations with specific details like license numbers and expiration dates.

### `ams.member.specialty`
Defines specialty areas and practice domains that can be organized hierarchically.

### `ams.member.specialty.line`
Junction model linking members to specialties with proficiency levels, certification status, and practice details.

## Extended Models

### `res.partner`
Extended with professional fields:
- Professional credentials summary
- Primary license information
- Practice details (name, type, years in practice)
- Professional online presence (ORCID, ResearchGate, etc.)
- Compliance status indicators

### `ams.member.profile`
Extended with professional networking and career fields:
- Social media and professional network profiles
- Educational background and career milestones
- Research and publication metrics
- Professional goals and availability for mentoring/speaking

## Installation

1. Ensure `ams_core_base` is installed
2. Install this module from the Apps menu
3. Configure professional designations and specialties
4. Assign designations and specialties to members

## Configuration

### Professional Designations
Navigate to **Association Management > Professional > Professional Designations** to set up:
- Medical designations (MD, DO, RN, etc.)
- Engineering designations (PE, EIT, etc.)  
- Legal designations (JD, Bar Admission, etc.)
- Business certifications (CPA, CFA, etc.)

### Member Specialties
Navigate to **Association Management > Professional > Member Specialties** to configure:
- Practice areas and subspecialties
- Certification requirements
- Continuing education needs

## Usage

### Assigning Professional Credentials
1. Open a member record
2. Go to the **Professional** tab
3. Add professional designations and specialties
4. Set license information and continuing education details

### Tracking Compliance
- Monitor expiring designations from the dashboard
- Review compliance status on member records
- Use filters to find members needing renewal

### Professional Networking
1. Update member profiles with professional network URLs
2. Track research output and academic achievements
3. Identify members available for mentoring or speaking

## Security

Access control by user group:
- **Members**: Can view and update their own professional information
- **Staff**: Can manage all member professional data
- **Managers**: Can configure designations and specialties
- **Administrators**: Full access to all professional management features

## Dependencies

- `ams_core_base` (required)
- `contacts` (Odoo core)
- `mail` (Odoo core)

## Data

The module includes sample data for common professional designations and specialties across industries:
- Healthcare (MD, DO, RN, specialties)
- Engineering (PE, EIT, disciplines)
- Legal (JD, Bar Admission, practice areas)
- Business (CPA, CFA, specializations)

## Technical Notes

### Computed Fields
- Professional credentials are automatically computed from active designations
- Compliance status is calculated based on license and designation status
- CE hour requirements are summed from all active designations and specialties

### Validation
- ORCID IDs are validated for proper format
- Social media handles are cleaned and validated
- Date logic is enforced (earned dates before expiration dates)
- Single primary specialty per member is enforced

### Automation
- Member IDs are auto-generated when members are created
- Reciprocal relationships are created automatically
- Expiration notifications are sent based on configuration

## Customization

The module is designed to be customizable for different association types:

### Medical Associations
- Pre-configured medical specialties and board certifications
- Integration with medical licensing boards
- CME hour tracking

### Engineering Associations  
- PE licensing and EIT certification tracking
- Engineering discipline specialties
- Professional development hour requirements

### Legal Associations
- Bar admission and practice area tracking
- CLE hour requirements
- Court admission tracking

### Business Associations
- Professional certifications (CPA, CFA, etc.)
- Industry specializations
- Professional development tracking

## Support

For technical support or feature requests, please contact the AMS development team or submit issues through the project repository.

## License

This module is licensed under LGPL-3. See LICENSE file for details.