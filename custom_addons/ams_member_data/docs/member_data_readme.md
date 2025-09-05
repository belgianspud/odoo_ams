markdown# AMS Member Data Module

## Overview

The AMS Member Data module is the foundational data layer for the Association Management System (AMS). It extends Odoo's native contact management with association-specific member and organization data structures.

## Features

### Individual Members
- Enhanced name components (first, middle, last, suffix, nickname)
- Demographics tracking (gender, date of birth)
- Multiple contact methods (business phone, mobile phone, secondary email)
- Dual address management (primary and secondary addresses)
- Auto-generated unique member IDs

### Organization Members
- Corporate identity fields (acronym, website, tax IDs)
- Business details (organization type, industry, employee count)
- Portal management and employee relationships
- Revenue and business metrics tracking

### Data Quality
- Phone number formatting and validation
- Email address validation
- Address standardization
- Legacy system integration support

## Installation

1. Install via Odoo Apps interface or command line:
   ```bash
   ./odoo-bin -d <database> -i ams_member_data

Configure member ID sequence in Settings > AMS Configuration
Set up member types and statuses as needed

Dependencies

base (Odoo core)
contacts (Odoo contact management)
mail (Odoo messaging system)

Usage
Creating Individual Members

Go to AMS > Members > Individual Members
Click Create
Fill in name components and contact information
Member ID will be auto-generated

Creating Organization Members

Go to AMS > Members > Organization Members
Click Create
Fill in organization details
Link employees as needed

API
Key Fields Added to res.partner
Individual Members

member_id: Auto-generated unique identifier
first_name, last_name: Name components
gender, date_of_birth: Demographics
business_phone, mobile_phone: Contact methods
secondary_address_*: Secondary address fields

Organization Members

acronym: Organization abbreviation
website_url: Primary website
organization_type: Business classification
employee_count: Number of employees
portal_primary_contact_id: Portal administrator

Computed Fields

display_name: Formatted name display
formatted_address: Formatted primary address
formatted_secondary_address: Formatted secondary address
employee_count_computed: Count of linked employees

Testing
Run tests with:
bash./odoo-bin -d <database> -i ams_member_data --test-enable --stop-after-init
Contributing
This module follows Odoo development best practices:

PEP 8 Python coding standards
Odoo XML formatting guidelines
Comprehensive test coverage
Documentation for all public methods

License
LGPL-3
Support
For support and documentation, see the main AMS project repository.

## **File 12: `ams_member_data/static/description/index.html`**

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AMS Member Data</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .feature { background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #3498db; }
        .highlight { background: #e8f4f8; padding: 10px; border-radius: 5px; margin: 15px 0; }
        ul { padding-left: 20px; }
        .screenshot { text-align: center; margin: 20px 0; }
        .benefit { color: #27ae60; font-weight: bold; }
    </style>
</head>
<body>
    <h1>AMS Member Data - Foundation Module</h1>
    
    <div class="highlight">
        <strong>The foundational data layer for Association Management Systems</strong><br>
        Transform Odoo's basic contact management into a comprehensive member database 
        with association-specific features and enhanced data structures.
    </div>

    <h2>Key Features</h2>

    <div class="feature">
        <h3>🧑‍💼 Enhanced Individual Member Profiles</h3>
        <ul>
            <li><strong>Complete Name Management:</strong> Separate first, middle, last name, and suffix fields</li>
            <li><strong>Demographics Tracking:</strong> Gender, date of birth, and nickname preferences</li>
            <li><strong>Multiple Contact Methods:</strong> Business phone, mobile phone, secondary email</li>
            <li><strong>Dual Address Support:</strong> Primary and secondary address management</li>
            <li><strong>Auto-Generated Member IDs:</strong> Unique identifiers with configurable formatting</li>
        </ul>
    </div>

    <div class="feature">
        <h3>🏢 Comprehensive Organization Management</h3>
        <ul>
            <li><strong>Corporate Identity:</strong> Acronyms, website URLs, tax identification numbers</li>
            <li><strong>Business Classifications:</strong> Organization types, industry sectors, NAICS codes</li>
            <li><strong>Employee Relationships:</strong> Link individual members to their organizations</li>
            <li><strong>Portal Management:</strong> Designate primary contacts for organizational access</li>
            <li><strong>Business Metrics:</strong> Employee counts, annual revenue, establishment year</li>
        </ul>
    </div>

    <div class="feature">
        <h3>🔧 Data Quality & Integration</h3>
        <ul>
            <li><strong>Phone Number Formatting:</strong> Automatic formatting to international standards</li>
            <li><strong>Email Validation:</strong> Format validation for primary and secondary emails</li>
            <li><strong>Address Standardization:</strong> Structured address components with validation</li>
            <li><strong>Legacy System Support:</strong> Integration fields for data migration</li>
            <li><strong>Computed Fields:</strong> Automatic formatting and relationship calculations</li>
        </ul>
    </div>

    <h2>Benefits for Your Association</h2>

    <div class="benefit">✅ Foundation for Growth:</div>
    <p>Provides the essential data structures that all other AMS modules build upon, ensuring scalability and consistency.</p>

    <div class="benefit">✅ Data Quality Assurance:</div>
    <p>Built-in validation and formatting ensures clean, consistent member data from day one.</p>

    <div class="benefit">✅ Flexible Configuration:</div>
    <p>Customizable member ID formats, configurable fields, and adaptable to various association types.</p>

    <div class="benefit">✅ Seamless Integration:</div>
    <p>Extends Odoo's native functionality while maintaining full compatibility with standard features.</p>

    <div class="benefit">✅ Portal Ready:</div>
    <p>Includes portal integration fields for future self-service member portal deployment.</p>

    <h2>Technical Specifications</h2>

    <ul>
        <li><strong>Odoo Version:</strong> Community 18.0+</li>
        <li><strong>Dependencies:</strong> base, contacts, mail (core Odoo modules only)</li>
        <li><strong>Layer:</strong> Foundation (Layer 1) - No AMS dependencies</li>
        <li><strong>Installation Order:</strong> Install first, before all other AMS modules</li>
        <li><strong>Database Impact:</strong> Extends res.partner with 25+ additional fields</li>
        <li><strong>Performance:</strong> Optimized for databases with 100,000+ member records</li>
    </ul>

    <h2>Getting Started</h2>

    <ol>
        <li><strong>Install the Module:</strong> Via Apps menu or command line installation</li>
        <li><strong>Configure Member IDs:</strong> Set prefix and formatting in AMS Configuration</li>
        <li><strong>Create Your First Members:</strong> Use Individual or Organization member views</li>
        <li><strong>Import Existing Data:</strong> Use built-in import tools for data migration</li>
        <li><strong>Extend with Other Modules:</strong> Add membership lifecycle, events, education modules</li>
    </ol>

    <div class="highlight">
        <strong>Ready to transform your member management?</strong><br>
        Install AMS Member Data today and build the foundation for a comprehensive 
        Association Management System that grows with your organization.
    </div>

    <h2>Part of the Complete AMS Suite</h2>

    <p>This module is part of the comprehensive Association Management System (AMS) for Odoo Community. 
    After installing this foundation module, enhance your system with:</p>

    <ul>
        <li><strong>Membership Lifecycle:</strong> Renewals, status management, and automation</li>
        <li><strong>Event Management:</strong> Member pricing, registration, and volunteer coordination</li>
        <li><strong>Education Management:</strong> Course catalogs, enrollment, and credit tracking</li>
        <li><strong>Fundraising:</strong> Campaigns, donations, and donor management</li>
        <li><strong>Portal Services:</strong> Self-service member portal and enterprise features</li>
    </ul>

</body>
</html>
Module Summary
This completes the ams_member_data module with:

10 core files from the original architecture
2 additional documentation files for completeness
Full Layer 1 foundation with no AMS dependencies
Production-ready code with validation, formatting, and error handling
Comprehensive test coverage with 15 different test scenarios
Complete views for both individual and organization management
Proper security configuration and access controls