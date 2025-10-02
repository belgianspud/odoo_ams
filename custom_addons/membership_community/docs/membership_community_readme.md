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
   - **NEW**: Parent-child category hierarchy for chapter support
   - **NEW**: `parent_category_id` - Link to parent category
   - **NEW**: `is_parent_required` - Flag requiring parent membership
   - Portal access configuration
   - Verification requirements
   - Product mapping
   - **Does NOT include**: Age requirements, education requirements, chapter-specific fields (those are in specialized modules)

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
   - **NEW**: Geographic fields (`country_id`, `state_id`, `zip`) - for chapter matching
   - **NEW**: `eligible_chapters` - Computed field for chapter eligibility
   - **NEW**: `chapter_memberships` - Many2many to chapters member belongs to
   - **Does NOT include**: Type-specific flags, professional credentials, organizational roles

5. **subscription.subscription** (extended)
   - Membership category link
   - Basic eligibility verification
   - Membership source tracking
   - **NEW**: Primary membership relationships
   - **NEW**: `primary_subscription_id` - Link to required parent subscription
   - **NEW**: `requires_primary_membership` - Computed flag
   - **NEW**: `primary_subscription_valid` - Validation of primary subscription
   - **NEW**: `related_subscription_ids` - Track all related memberships
   - **NEW**: Primary membership validation hooks (extensible methods)
   - **Does NOT include**: Approval workflow, seat management (base has it), chapter-specific validation

6. **product.template** (extended)
   - Membership product flag
   - Subscription type selection
   - Category mapping
   - Features/benefits configuration
   - Portal access level
   - Seat management configuration (for organizational memberships)
   - **Does NOT include**: Professional features, chapter requirements

## What's New for Chapter Support

### Category Hierarchy
```python
# Categories can now have parent-child relationships
national_category = env['membership.category'].search([('code', '=', 'NATIONAL')])
chapter_category = env['membership.category'].create({
    'name': 'California Chapter',
    'code': 'CHAP_CA',
    'category_type': 'chapter',
    'parent_category_id': national_category.id,
    'is_parent_required': True,
})
Primary Membership Validation
python# Subscriptions can require a primary/parent subscription
chapter_subscription = env['subscription.subscription'].create({
    'partner_id': member.id,
    'plan_id': chapter_plan.id,
    'membership_category_id': chapter_category.id,
    # Auto-assigns primary_subscription_id if available
})

# Check if primary is valid
if chapter_subscription.requires_primary_membership:
    is_valid, error = chapter_subscription._check_primary_membership_requirement()
Extension Hooks for Chapters
The base module provides hooks that the chapter module will override:
python# In subscription.subscription
def _check_primary_membership_requirement(self):
    """Override in membership_chapter for custom validation"""
    pass

def _get_required_primary_categories(self):
    """Override in membership_chapter to specify which categories are valid primaries"""
    pass

def _get_valid_primary_subscriptions(self):
    """Override in membership_chapter to filter available primary subscriptions"""
    pass
Geographic Eligibility
python# Partners can now check which chapters they're eligible for
partner = env['res.partner'].browse(partner_id)
eligible_chapters = partner.eligible_chapters  # Computed field
Quick Setup Wizard (Enhanced)
The Quick Setup Wizard now supports chapter configuration:
Chapter Creation

Select "Chapter Membership" type
Specify geographic location
Choose parent membership category
Configure features and benefits
Click "Create Membership"

Result: Complete chapter setup with:

Chapter category linked to parent
Product with chapter designation
Subscription plan
Primary membership requirement validation

Installation
bash# Install base module
odoo-bin -i membership_community

# Then install specialized modules as needed
odoo-bin -i membership_individual
odoo-bin -i membership_organizational
odoo-bin -i membership_chapter
Dependencies

base
mail
product
subscription_management (must be installed first)

Extension Pattern
Specialized modules extend the base using Odoo's inheritance mechanism:
python# In membership_chapter/models/membership_category.py
class MembershipCategory(models.Model):
    _inherit = 'membership.category'
    
    # Extend category types
    @api.model
    def _get_category_types(self):
        types = super()._get_category_types()
        # Add chapter-specific types if needed
        return types
    
    # Add chapter-specific fields
    geographic_scope = fields.Selection([
        ('national', 'National'),
        ('regional', 'Regional'),
        ('state', 'State'),
        ('local', 'Local'),
    ], string='Geographic Scope')
Key Features
1. Membership Categories

Define unlimited member categories
Base types: individual, organizational, chapter, seat
Extensible type system
NEW: Parent-child hierarchy
NEW: Primary membership requirements
Member tier system (basic, standard, premium, platinum)
Portal access levels

2. Benefits & Features

Define membership benefits (discounts, access, publications, etc.)
Define technical features (portal access, tracking, etc.)
Link to products and categories
Monetary value tracking
Marketing display configuration

3. Member Management

Track membership status (none, active, trial, expired)
Member since date
Category assignment
Portal access management
Available features and benefits
NEW: Chapter membership tracking
NEW: Geographic eligibility

4. Subscription Integration

Seamless integration with subscription_management
Membership category on subscriptions
NEW: Primary subscription validation
NEW: Related subscription tracking
Eligibility verification workflow
Source type tracking (direct, renewal, import, admin)
Join date tracking

5. Product Configuration

Mark products as membership products
Link to subscription plans
Associate benefits and features
Set default member categories
Configure portal access
NEW: Chapter product support

6. Primary Membership System (NEW)

Subscriptions can require primary/parent memberships
Automatic validation of primary membership status
Auto-assignment of primary subscriptions when available
Extensible validation hooks for specialized modules
Prevents activation without valid primary

Menu Structure
Membership
├── 🚀 Quick Setup (NEW - supports chapters!)
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
    ├── 🚀 Quick Setup
    ├── Member Categories
    └── Features & Benefits
Security Groups

Membership User: Read-only access to memberships and members
Membership Manager: Full access to manage memberships, verify eligibility, and configure settings

Workflow Example
Creating a Chapter Membership

Use Quick Setup Wizard

   Membership > 🚀 Quick Setup
   - Type: Chapter Membership
   - Name: California Chapter
   - Location: California
   - Parent: National Membership
   - Requires National: Yes

Result

Category created with parent link
Product created with chapter designation
Plan created
Primary membership validation enabled


Member Joins Chapter

   - Member must have active National membership
   - System validates primary membership
   - Creates chapter subscription linked to national
   - Member gets both national and chapter benefits
Extending for Chapters
The membership_chapter module extends this base to add:

Chapter Model: Geographic/specialty chapters with officers
Primary Membership Validation: Ensures members have national membership
Chapter Events: Chapter-specific event management
Geographic Assignment: Auto-assign members to chapters by location
Chapter Reporting: Chapter-specific analytics and reports
Officer Management: Chapter board and committee structure

Key Extension Points
For Categories:
python# membership_chapter extends:
- Geographic scope fields
- Location-based eligibility rules
- Chapter officer assignments
- Meeting management
For Subscriptions:
python# membership_chapter extends:
- Primary membership validation logic
- Geographic matching algorithms
- Chapter-specific approval workflows
- Officer-only features
For Partners:
python# membership_chapter extends:
- Chapter affiliation tracking
- Officer role management
- Chapter-specific benefits
- Geographic chapter matching
Data Flow
Sale Order (Membership Product)
    ↓
Subscription Created
    ↓
Primary Membership Checked (if required) ← NEW!
    ↓
Membership Category Assigned
    ↓
Partner Status Updated (is_member = True)
    ↓
Benefits & Features Available
    ↓
Portal Access Granted
Primary Membership Flow (NEW)
Chapter Subscription Created
    ↓
requires_primary_membership = True
    ↓
System checks for valid primary subscription
    ↓
    ├─ Found: Auto-assign as primary_subscription_id
    │          primary_subscription_valid = True
    │          ↓
    │          Subscription can be activated
    │
    └─ Not Found: primary_subscription_valid = False
                  ↓
                  Subscription blocked from activation
                  ↓
                  User must create/activate national membership first
Reporting
Basic membership reports available:

Active member count by category
Membership revenue
Renewal pipeline (90 days)
New members this month
NEW: Members by chapter (when chapter module installed)
NEW: Primary membership compliance

Specialized modules can add:

Demographics (age, location) - membership_individual
Organizational hierarchies - membership_organizational
NEW: Chapter participation - membership_chapter
NEW: Chapter growth trends - membership_chapter

Technical Notes
Field Naming Convention

Base fields: Simple names (e.g., is_member, member_tier)
Type-specific fields: Prefixed (e.g., is_student_member, min_age)
Module-specific fields: Clear namespace (e.g., credential_ids, seat_ids, chapter_ids)
NEW: Relationship fields: parent_subscription_id, primary_subscription_id

Compute Field Strategy
Base module computes:

is_member: Based on active subscriptions
membership_state: Current subscription state
membership_category_id: From primary subscription
available_features/benefits: From active subscription products
NEW: requires_primary_membership: From category configuration
NEW: primary_subscription_valid: Validates primary subscription
NEW: eligible_chapters: Geographic chapter matching (placeholder)

Specialized modules add:

Type-specific computed fields
Additional statistics
Advanced eligibility checks
NEW: Chapter-specific computations

Extensibility Points
The base module provides these extension points:

Category Types: _get_category_types() method
Eligibility Checking: check_eligibility() method
Source Types: _get_source_types() method
Subscription Product Types: _get_subscription_product_types() method
NEW: Primary Membership Validation: _check_primary_membership_requirement() method
NEW: Required Primary Categories: _get_required_primary_categories() method
NEW: Valid Primary Subscriptions: _get_valid_primary_subscriptions() method
NEW: Geographic Eligibility: _compute_eligible_chapters() method

Constraints and Validation
Base Validation:

Unique category codes
Unique member numbers
Subscription-category compatibility (soft warning)
Seat allocation limits

NEW - Primary Membership Validation:

Primary subscription must belong to same partner
Primary subscription must be active/trial
Blocks activation if primary invalid
Auto-assignment on create/update

Chapter Module Adds:

Geographic validation
Primary membership enforcement
Chapter capacity limits
Officer eligibility

API Examples
Check Primary Membership
python# Check if subscription requires and has valid primary
subscription = env['subscription.subscription'].browse(sub_id)

if subscription.requires_primary_membership:
    is_valid, error_msg = subscription._check_primary_membership_requirement()
    if not is_valid:
        print(f"Primary membership issue: {error_msg}")
Get Eligible Chapters
python# Find chapters a member can join
partner = env['res.partner'].browse(partner_id)
eligible = partner.eligible_chapters
print(f"Member can join: {eligible.mapped('name')}")
Create Chapter Subscription
python# Create subscription with primary requirement
subscription = env['subscription.subscription'].create({
    'partner_id': partner_id,
    'plan_id': chapter_plan_id,
    'membership_category_id': chapter_category_id,
    # System will auto-assign primary_subscription_id if available
})

# Verify primary is valid before activating
if subscription.primary_subscription_valid:
    subscription.action_confirm()
else:
    print("Cannot activate: Primary membership required")
Support
For issues or questions:

Check this README
Review the implementation guide documents
Examine specialized module examples
Consult Odoo documentation for inheritance patterns

License
LGPL-3
Version
18.0.1.0.0 - Odoo 18 Community Edition

Changelog
v18.0.1.0.0 (Current)

✨ Added parent-child category hierarchy
✨ Added primary membership requirement system
✨ Added primary subscription validation
✨ Added geographic eligibility framework
✨ Enhanced Quick Setup Wizard with chapter support
✨ Added extensibility hooks for chapter management
🔧 Added related subscription tracking
📚 Updated documentation for chapter extensions