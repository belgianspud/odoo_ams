# AMS Member Data Module

## Overview

The AMS Member Data module is the foundational data layer for the Association Management System (AMS). It extends Odoo's native contact management with association-specific member and organization data structures while maximizing use of existing Odoo Community 18 fields.

## Features

### Universal Member Fields (Individuals & Organizations)
- **Member Status Management**: Prospect, Active, Grace Period, Lapsed, Former, Honorary, Suspended
- **Member ID Generation**: Auto-generated unique identifiers using Odoo's `ref` field
- **Membership Dates**: Join date, member since, renewal date, paid through date
- **Engagement Tracking**: Engagement scores, payment history, contribution totals
- **Donor Classification**: Bronze, Silver, Gold, Platinum donor levels

### Individual Member Extensions
- **Demographics**: Date of birth, gender selection
- **Professional Info**: Credentials and certifications
- **Computed Fields**: Membership duration, days until renewal, renewal due status

### Organization Member Extensions
- **Corporate Identity**: Acronyms, organization types, year established
- **Business Details**: Employee count, annual revenue
- **Tax Information**: EIN numbers (with validation), uses existing `vat` field
- **Employee Management**: Portal contact designation, employee relationships
- **Computed Fields**: Employee count from linked contacts, display name with acronym

## Leveraged Existing Odoo Fields

This module maximizes use of existing `res.partner` fields:

| AMS Need | Existing Odoo Field | Notes |
|----------|-------------------|-------|
| Website URL | `website` | Built-in URL validation |
| Tax ID | `vat` | Standard VAT/Tax field |
| Industry | `industry_id` | Standard industry classification |
| Contact Tags | `category_id` | For member types/classifications |
| Employee Relations | `parent_id`/`child_ids` | Standard contact hierarchy |
| Job Title | `function` | Built-in function field |
| Name Titles | `title` | Mr./Ms./Dr. prefixes |
| Member ID Storage | `ref` | Internal reference with formatting |
| Contact Info | `email`, `phone`, `mobile` | Standard contact fields |
| Address | `street`, `city`, `state_id`, etc. | Full address management |

## Installation

1. **Install via Odoo Apps interface:**
   - Go to Apps menu
   - Search for "AMS Member Data" 
   - Click Install

2. **Install via command line:**
   ```bash
   ./odoo-bin -d <database> -i ams_member_data --stop-after-init

Dependencies:

base (Odoo core)
contacts (Contact management)
mail (Messaging and activities)



Configuration
Initial Setup

Member ID Sequence: Automatically configured (M000001, M000002, etc.)
Contact Categories: Use existing Odoo contact tags for member types
Industries: Use existing Odoo industry classifications

Data Migration

Use legacy_contact_id field for mapping from old systems
Member IDs stored in standard ref field for compatibility
Standard Odoo import tools work with all fields

Usage
Creating Individual Members

Go to AMS > Members > Individual Members
Click Create
Fill in name and contact information
Check Is Member and set Membership Status
Member ID auto-generates on save

Creating Organization Members

Go to AMS > Members > Organization Members
Click Create
Set Company Type to Company
Fill in organization details (name, acronym, type, etc.)
Add employees using the Portal & Access tab

Converting Prospects to Members

Use the Make Member button on prospect records
Or check the Is Member checkbox and set appropriate status

API Reference
Key Fields Added to res.partner
Universal Member Fields
pythonis_member = fields.Boolean()                    # Member flag
membership_status = fields.Selection()          # Lifecycle status  
member_id = fields.Char(compute, inverse)       # Formatted ID
join_date = fields.Date()                       # Current term start
member_since = fields.Date()                    # Original join date
renewal_date = fields.Date()                    # Expected renewal
paid_through_date = fields.Date()               # Coverage end
engagement_score = fields.Float()               # Engagement metric
last_payment_date = fields.Date()               # Recent payment
last_payment_amount = fields.Monetary()         # Payment amount
total_contributions = fields.Monetary()         # Lifetime giving
donor_level = fields.Selection()                # Recognition level
Individual-Specific Fields
pythondate_of_birth = fields.Date()                   # Birth date
gender = fields.Selection()                     # Gender identity
credentials = fields.Text()                     # Professional creds
Organization-Specific Fields
pythonacronym = fields.Char()                         # Organization acronym
organization_type = fields.Selection()          # Corp, nonprofit, etc.
year_established = fields.Integer()             # Founded year
employee_count = fields.Integer()               # Total employees
annual_revenue = fields.Monetary()              # Revenue amount
ein_number = fields.Char()                      # US EIN (validated)
portal_primary_contact_id = fields.Many2one()   # Portal admin
Key Methods
Member Actions
pythonaction_make_member()                            # Convert to member
action_renew_membership()                       # Renew membership
action_view_employees()                         # View org employees
get_organization_summary()                      # Org summary data
Computed Field Methods
python_compute_member_id()                            # Format member ID
_compute_membership_duration()                  # Days as member
_compute_is_renewal_due()                       # Renewal status
_compute_employee_count_computed()              # Count employees
Data Validation
Automatic Validations

EIN Format: US format XX-XXXXXXX with auto-formatting
Website URLs: Auto-adds https:// prefix, validates format
Year Established: Range validation (1800 to current year)
Employee Count: Positive number validation

Business Rules

Member ID Generation: Auto-generated on first save when is_member = True
Member Since Date: Auto-set when first becoming a member
Renewal Due Logic: True when renewal date within 30 days for active/grace members

Integration Points
With Odoo Core

Activities & Messages: Full integration with mail module
Contact Management: Extends existing contact forms and views
Search & Filters: All fields available in standard search views
Reporting: Fields available in standard Odoo reporting tools

With Future AMS Modules

Member Types: Will connect to ams_member_types module
Billing: Will integrate with ams_billing_core for payment tracking
Events: Will link to ams_event_core for registration pricing
Portal: Will connect to ams_portal_* modules for self-service

Troubleshooting
Common Issues
Member ID not generating:

Check that sequence ams.member.id exists in Settings > Technical > Sequences
Ensure is_member = True when creating the record

Search filters not working:

Check that computed fields have store=True for database search capability
Verify domain syntax in search views

Validation errors:

EIN format must be XX-XXXXXXX (auto-formats from 9 digits)
Website URLs must include protocol (auto-adds https://)
Year established must be between 1800 and current year

Development Notes
Design Principles

Leverage Existing Fields: Use res.partner fields wherever possible
Minimal Extensions: Only add fields truly missing for associations
Computed Fields: Use computed fields with proper dependencies
Validation: Implement helpful validation with auto-correction
Integration: Design for integration with higher-layer modules

Database Impact

Extends res.partner with ~15 additional fields
Uses existing ref field for member ID storage
All computed fields properly stored for search performance
No new models created - pure extension approach

License
LGPL-3
Support
For technical support, see the main AMS project documentation.