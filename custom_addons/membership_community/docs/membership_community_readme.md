# Membership Community - Base Module

## Overview

The `membership_community` module provides the **core infrastructure** for membership management in Odoo 18. It extends the `subscription_management` module with membership-specific features while remaining lean and extensible.

## Philosophy

This base module follows a **modular design principle**:

- **Base Module (membership_community)**: Provides core infrastructure only
- **Specialized Modules**: Add specific features for different membership types
  - `membership_individual`: Individual members (student, retired, professional, etc.)
  - `membership_organizational`: Organizational memberships with seats
  - `membership_chapter`: Chapter/section memberships

## What's Included in Base

### Core Models

1. **membership.category**
   - Basic category management (name, code, type, tier)
   - Portal access configuration
   - Verification requirements
   - Product mapping
   - **Does NOT include**: Age requirements, education requirements, seat management, chapter-specific fields

2. **membership.benefit**
   - Basic benefit definition (name, code, category, type)
   - Monetary value tracking
   - Product/category associations
   - Marketing display options
   - **Does NOT include**: Seasonal availability, partner benefits, complex eligibility, redemption methods

3. **membership.feature**
   - Basic feature definition (name, code, category, type)
   - Product associations
   - **Does NOT include**: Module-specific configurations, complex integrations

4. **res.partner** (extended)
   - Basic membership status (`is_member`, `membership_state`)
   - Member category tracking
   - Membership dates
   - Portal access level
   - Features/benefits available
   - **Does NOT include**: Type-specific flags, professional credentials, organizational roles

5. **subscription.subscription** (extended)
   - Membership category link
   - Basic eligibility verification
   - Membership source tracking
   - **Does NOT include**: Approval workflow, primary membership validation, seat management

6. **product.template** (extended)
   - Membership product flag
   - Subscription type selection
   - Category mapping
   - Features/benefits configuration
   - Portal access level
   - **Does NOT include**: Professional features, seat management, chapter requirements

## What's Removed from Base

The following fields have been **removed from base views** and should be implemented in specialized modules:

### From membership.category:
- `min_age`, `max_age`, `auto_transition_age`
- `requires_degree`, `required_degree_level`
- `requires_license`, `requires_experience`
- `requires_enrollment_verification`
- `min_seats_required`, `supports_seats`
- `requires_primary_membership`
- `allows_upgrade_to`, `allows_downgrade_to`

### From membership.benefit:
- `seasonal`, `available_months`
- `is_partner_benefit`, `partner_organization`
- `redemption_method`, `redemption_instructions`
- `requires_activation`, `has_usage_limit`
- `discount_type`, `discount_applies_to`

### From membership.feature:
- `grants_portal_access`, `portal_access_level`
- `enables_credential_tracking`, `enables_ce_tracking`
- `enables_member_directory`, `enables_messaging`
- `seasonal`, `available_months`

### From res.partner:
- `is_student_member`, `is_retired_member`, `is_honorary_member`
- `is_organizational_member`, `is_seat_member`
- `parent_organization_id`, `organizational_role`
- `birthdate`, `credential_ids`, `ce_credit_ids`
- `chapter_membership_ids`, `chapter_count`
- `has_professional_features`, `has_credentials`

### From subscription.subscription:
- `approval_status`, `approved_by`, `approval_date`
- `requires_approval`, `rejection_reason`
- `requires_primary_membership`, `primary_membership_ids`
- `primary_membership_valid`

## Installation

```bash
# Install base module
odoo-bin -i membership_community

# Then install specialized modules as needed
odoo-bin -i membership_individual
odoo-bin -i membership_organizational
odoo-bin -i membership_chapter
```

## Dependencies

- `base`
- `mail`
- `product`
- `subscription_management` (must be installed first)

## Extension Pattern

Specialized modules extend the base using Odoo's inheritance mechanism:

```python
# In membership_individual/models/membership_category.py
class MembershipCategory(models.Model):
    _inherit = 'membership.category'
    
    # Extend category types
    @api.model
    def _get_category_types(self):
        types = super()._get_category_types()
        types.extend([
            ('student', 'Student'),
            ('retired', 'Retired'),
            ('honorary', 'Honorary'),
        ])
        return types
    
    # Add individual-specific fields
    min_age = fields.Integer('Minimum Age', default=0)
    max_age = fields.Integer('Maximum Age', default=0)
    requires_degree = fields.Boolean('Requires Degree', default=False)
```

## Key Features

### 1. Membership Categories
- Define unlimited member categories
- Base types: individual, organizational, chapter
- Extensible type system
- Member tier system (basic, standard, premium, platinum)
- Portal access levels

### 2. Benefits & Features
- Define membership benefits (discounts, access, publications, etc.)
- Define technical features (portal access, tracking, etc.)
- Link to products and categories
- Monetary value tracking
- Marketing display configuration

### 3. Member Management
- Track membership status (none, active, trial, expired)
- Member since date
- Category assignment
- Portal access management
- Available features and benefits

### 4. Subscription Integration
- Seamless integration with subscription_management
- Membership category on subscriptions
- Eligibility verification workflow
- Source type tracking (direct, renewal, import, admin)
- Join date tracking

### 5. Product Configuration
- Mark products as membership products
- Link to subscription plans
- Associate benefits and features
- Set default member categories
- Configure portal access

## Menu Structure

```
Membership
├── Memberships
│   ├── All Memberships
│   ├── Active Memberships
│   ├── Pending Verification
│   └── Due for Renewal
├── Members
│   ├── Member Directory
│   └── All Contacts
├── Products
│   ├── Membership Products
│   └── Subscription Plans
└── Configuration
    ├── Member Categories
    └── Features & Benefits
```

## Security Groups

- **Membership User**: Read-only access to memberships and members
- **Membership Manager**: Full access to manage memberships, verify eligibility, and configure settings

## Workflow Example

### Creating a Membership

1. **Define Category**
   ```
   Membership > Configuration > Member Categories > Create
   - Name: Individual Member
   - Code: IND
   - Type: individual
   - Tier: standard
   ```

2. **Create Membership Product**
   ```
   Membership > Products > Membership Products > Create
   - Name: Annual Individual Membership
   - Check "Is Membership Product"
   - Create Subscription Plan:
     - Price: $100
     - Billing Period: Yearly
   ```

3. **Member Signs Up**
   ```
   Sales > Orders > Create
   - Select customer
   - Add membership product
   - Confirm order
   → Subscription automatically created
   → Member status updated
   ```

4. **Verify Eligibility** (if required)
   ```
   Membership > Memberships > Pending Verification
   - Open subscription
   - Click "Verify Eligibility"
   ```

## Extending the Base Module

### Creating a Specialized Module

See the included documentation for creating specialized modules:

1. **membership_individual**: For individual member types
   - Student memberships with age restrictions
   - Retired member categories
   - Professional credentials tracking
   - Continuing education (CE) credits

2. **membership_organizational**: For organizational memberships
   - Seat-based memberships
   - Parent-child organization relationships
   - Seat management and allocation

3. **membership_chapter**: For chapter memberships
   - Geographic chapters
   - Specialty sections
   - Primary membership requirements
   - Chapter officer management

### Inheritance Pattern

All specialized modules follow this pattern:

```python
# __manifest__.py
{
    'name': 'Membership Individual',
    'depends': [
        'membership_community',  # Base module
    ],
    # ...
}

# models/membership_category.py
class MembershipCategory(models.Model):
    _inherit = 'membership.category'
    
    # Add new fields
    # Extend methods
    # Add new methods
```

## Data Flow

```
Sale Order (Membership Product)
    ↓
Subscription Created
    ↓
Membership Category Assigned
    ↓
Partner Status Updated (is_member = True)
    ↓
Benefits & Features Available
    ↓
Portal Access Granted
```

## Reporting

Basic membership reports available:

- Active member count by category
- Membership revenue
- Renewal pipeline (90 days)
- New members this month

Specialized modules can add:
- Demographics (age, location) - membership_individual
- Organizational hierarchies - membership_organizational
- Chapter participation - membership_chapter

## Technical Notes

### Field Naming Convention

- **Base fields**: Simple names (e.g., `is_member`, `member_tier`)
- **Type-specific fields**: Prefixed (e.g., `is_student_member`, `min_age`)
- **Module-specific fields**: Clear namespace (e.g., `credential_ids`, `seat_ids`)

### Compute Field Strategy

Base module computes:
- `is_member`: Based on active subscriptions
- `membership_state`: Current subscription state
- `membership_category_id`: From primary subscription
- `available_features/benefits`: From active subscription products

Specialized modules add:
- Type-specific computed fields
- Additional statistics
- Advanced eligibility checks

### Extensibility Points

The base module provides these extension points:

1. **Category Types**: `_get_category_types()` method
2. **Eligibility Checking**: `check_eligibility()` method
3. **Source Types**: `_get_source_types()` method
4. **Subscription Product Types**: `_get_subscription_product_types()` method

## Support

For issues or questions:
1. Check this README
2. Review the implementation guide documents
3. Examine specialized module examples
4. Consult Odoo documentation for inheritance patterns

## License

LGPL-3

## Version

18.0.1.0.0 - Odoo 18 Community Edition