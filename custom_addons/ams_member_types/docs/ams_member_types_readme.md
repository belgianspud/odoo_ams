# AMS Member Types

A foundational module for the Association Management System (AMS) that provides member classification and status lifecycle management.

## Overview

The AMS Member Types module enables associations to define and manage different categories of members (Individual, Corporate, Student, etc.) and track member status throughout their lifecycle (Active, Pending, Suspended, etc.). This module serves as a foundation for all other AMS modules that need to understand member classifications and status.

## Features

### Member Type Management
- **Flexible Classification**: Define member types for individuals, organizations, or both
- **Age-based Eligibility**: Set minimum and maximum age requirements
- **Approval Workflows**: Configure auto-approval or verification requirements
- **Comprehensive Validation**: Built-in business rule validation and constraints

### Member Status Lifecycle
- **Status Progression**: Define logical progression through membership lifecycle
- **Auto-transitions**: Automatic status changes after specified time periods
- **Permission Control**: Configure what members can do in each status
- **Visual Management**: Color-coded status indicators for easy identification

### Pre-configured Data
- **15+ Member Types**: Ready-to-use types including Regular, Student, Senior, Corporate, Non-Profit, etc.
- **12+ Member Statuses**: Complete lifecycle from Pending through Active to Terminated
- **Logical Defaults**: Sensible default configurations that work out-of-the-box

## Installation

### Prerequisites
- Odoo Community 18.0 or later
- No additional dependencies required

### Install Steps

1. **Copy Module**: Place the `ams_member_types` folder in your Odoo custom addons directory:
   ```
   /path/to/odoo/custom_addons/ams_member_types/
   ```

2. **Update Apps List**: In Odoo, go to Apps → Update Apps List

3. **Install Module**: Search for "AMS Member Types" and click Install

4. **Verify Installation**: Check that the module appears in Settings → Apps → Installed Apps

## Quick Start

### Accessing Member Types
1. Navigate to **Settings → Member Types**
2. Review the pre-configured member types
3. Customize existing types or create new ones as needed

### Accessing Member Statuses  
1. Navigate to **Settings → Member Statuses**
2. Review the pre-configured statuses
3. Adjust auto-transition rules and permissions as needed

### Basic Configuration
1. **Review Member Types**: Ensure the pre-defined types match your association's needs
2. **Customize Age Limits**: Adjust age requirements for types like Student or Senior
3. **Configure Verification**: Set which member types require manual verification
4. **Set Up Auto-transitions**: Configure how long members stay in each status before auto-transitioning

## Member Types

### Individual Member Types
| Type | Code | Age Range | Auto-Approve | Description |
|------|------|-----------|--------------|-------------|
| Regular | REGULAR | 18+ | Yes | Standard individual membership |
| Student | STUDENT | 16-35 | No | Discounted membership for students |
| Senior | SENIOR | 65+ | Yes | Discounted membership for seniors |
| Young Professional | YOUNG_PROF | 22-35 | Yes | Special networking membership |
| Professional | PROFESSIONAL | 21+ | No | Enhanced professional membership |
| International | INTERNATIONAL | 18+ | No | Global membership benefits |
| Lifetime | LIFETIME | 18+ | No | Permanent membership status |
| Honorary | HONORARY | Any | No | Recognition membership |
| Associate | ASSOCIATE | 16+ | Yes | Limited membership benefits |

### Organizational Member Types
| Type | Code | Verification Required | Description |
|------|------|----------------------|-------------|
| Corporate | CORPORATE | Yes | Full corporate membership |
| Non-Profit | NONPROFIT | Yes | Discounted non-profit membership |
| Educational | EDUCATION | Yes | Academic institution membership |

### Trial/Temporary Types
| Type | Code | Active | Description |
|------|------|--------|-------------|
| Trial | TRIAL | Yes | Temporary evaluation membership |
| Guest | GUEST | No | Event-based temporary access |

## Member Statuses

### Active Lifecycle Statuses
| Status | Code | Active Member | Can Renew | Portal Access | Auto-Transition |
|--------|------|---------------|-----------|---------------|-----------------|
| Lifetime | LIFETIME | Yes | No | Yes | None |
| Honorary | HONORARY | Yes | No | Yes | None |
| Emeritus | EMERITUS | Yes | No | Yes | None |
| Active | ACTIVE | Yes | Yes | Yes | None |
| Provisional | PROVISIONAL | Yes | No | Yes | 90 days → Active |
| Trial | TRIAL | Yes | Yes | Yes | 30 days → Expired |
| Grace Period | GRACE | Yes | Yes | Yes | 30 days → Lapsed |

### Inactive Lifecycle Statuses
| Status | Code | Active Member | Can Renew | Auto-Transition |
|--------|------|---------------|-----------|-----------------|
| Pending | PENDING | No | No | 30 days → Expired |
| Lapsed | LAPSED | No | Yes | 365 days → Expired |
| Leave of Absence | LEAVE | No | Yes | 365 days → Active |
| Expired | EXPIRED | No | No | None |
| Suspended | SUSPENDED | No | No | None |
| Terminated | TERMINATED | No | No | None |
| Deceased | DECEASED | No | No | None |

## Usage Examples

### Creating a Custom Member Type

```python
# Create a new member type for contractors
contractor_type = env['ams.member.type'].create({
    'name': 'Contractor Member',
    'code': 'CONTRACTOR',
    'is_individual': True,
    'is_organization': False,
    'min_age': 21,
    'max_age': 0,  # No maximum
    'requires_verification': True,
    'auto_approve': False,
    'description': 'Membership for independent contractors and consultants',
    'sequence': 35,
})
```

### Creating a Custom Status

```python
# Create a probationary status that auto-transitions to active
probation_status = env['ams.member.status'].create({
    'name': 'Probationary',
    'code': 'PROBATION',
    'is_active': True,
    'sequence': 17,
    'can_renew': False,
    'can_purchase': True,
    'allows_portal_access': True,
    'auto_transition_days': 180,
    'next_status_id': env.ref('ams_member_types.member_status_active').id,
    'description': 'New member probationary period',
    'color': 5,  # Orange color
})
```

### Checking Member Type Eligibility

```python
# Get available types for a 25-year-old individual
available_types = env['ams.member.type'].get_available_types(
    is_individual=True, 
    age=25
)

# Check if specific type is suitable for age 19
student_type = env.ref('ams_member_types.member_type_student')
is_eligible = student_type.check_age_eligibility(19)  # Returns True

# Get eligibility message for display
message = student_type.get_eligibility_message(age=19)
# Returns: "Ages 16-35 • Available for: Individuals • Requires verification"
```

### Working with Status Transitions

```python
# Check if transition is allowed
active_status = env.ref('ams_member_types.member_status_active')
suspended_status = env.ref('ams_member_types.member_status_suspended')

can_transition = active_status.can_transition_to(suspended_status)  # Returns True

# Get transition impact message
transition_msg = active_status.get_transition_message(suspended_status)
# Returns details about what will change
```

## Configuration

### Member Type Configuration

**Basic Information**
- **Name**: Display name for the member type
- **Code**: Unique identifier (auto-generated from name)
- **Sequence**: Display order in lists
- **Active**: Whether type is available for new members

**Classification**
- **For Individuals**: Available for individual members
- **For Organizations**: Available for organizational members

**Eligibility Rules**
- **Minimum Age**: Youngest allowed age (0 = no limit)
- **Maximum Age**: Oldest allowed age (0 = no limit)
- **Requires Verification**: Manual approval needed
- **Auto-approve**: Automatic approval for applications

### Member Status Configuration

**Basic Properties**
- **Name**: Display name for the status
- **Code**: Unique identifier
- **Sequence**: Order in lifecycle progression
- **Color**: Kanban view color (0-11)

**Classification Flags**
- **Counts as Active Member**: Included in active membership counts
- **Pending Status**: Awaiting action or approval
- **Suspended Status**: Disciplinary suspension
- **Terminated Status**: Permanent termination

**Permissions**
- **Can Renew**: Member can renew their membership
- **Can Purchase**: Member can buy products/services
- **Allows Portal Access**: Member can access online portal
- **Requires Approval**: Admin approval needed to enter this status

**Auto-transitions**
- **Auto-transition After**: Days before automatic transition
- **Next Status**: Status to transition to automatically

## API Reference

### ams.member.type

#### Methods

**check_age_eligibility(age)**
- Check if given age meets type requirements
- Returns: boolean

**get_eligibility_message(age=None)**
- Get human-readable eligibility requirements
- Returns: string

**get_available_types(is_individual=None, age=None)** (static)
- Get types available for given criteria
- Returns: recordset

**action_view_members()**
- Open view of members with this type
- Returns: action dictionary

#### Fields

**Core Fields**
- `name` (Char): Type name
- `code` (Char): Unique code
- `sequence` (Integer): Display order
- `active` (Boolean): Is active
- `description` (Text): Description

**Classification**
- `is_individual` (Boolean): For individuals
- `is_organization` (Boolean): For organizations

**Eligibility**
- `min_age` (Integer): Minimum age
- `max_age` (Integer): Maximum age
- `requires_verification` (Boolean): Needs verification
- `auto_approve` (Boolean): Auto-approve applications

**Computed**
- `member_count` (Integer): Current member count

### ams.member.status

#### Methods

**can_transition_to(target_status)**
- Check if transition to target status is allowed
- Returns: boolean

**get_transition_message(target_status)**
- Get description of transition impact
- Returns: string

**get_active_statuses()** (static)
- Get all statuses that count as active
- Returns: recordset

**get_renewable_statuses()** (static)
- Get all statuses that allow renewal
- Returns: recordset

**get_default_status()** (static)
- Get default status for new members
- Returns: record

#### Fields

**Core Fields**
- `name` (Char): Status name
- `code` (Char): Unique code
- `sequence` (Integer): Lifecycle order
- `description` (Text): Description
- `color` (Integer): Display color (0-11)

**Classification**
- `is_active` (Boolean): Counts as active member
- `is_pending` (Boolean): Pending status
- `is_suspended` (Boolean): Suspended status
- `is_terminated` (Boolean): Terminated status

**Permissions**
- `can_renew` (Boolean): Can renew membership
- `can_purchase` (Boolean): Can purchase products
- `allows_portal_access` (Boolean): Can access portal
- `requires_approval` (Boolean): Needs approval

**Auto-transitions**
- `auto_transition_days` (Integer): Days until auto-transition
- `next_status_id` (Many2one): Next status for auto-transition

**Computed**
- `member_count` (Integer): Current member count
- `is_final_status` (Boolean): No further transitions

## Data Management

### Importing Member Types

```xml
<record id="custom_member_type" model="ams.member.type">
    <field name="name">Custom Type</field>
    <field name="code">CUSTOM</field>
    <field name="is_individual">True</field>
    <field name="min_age">18</field>
    <field name="auto_approve">True</field>
</record>
```

### Importing Member Statuses

```xml
<record id="custom_status" model="ams.member.status">
    <field name="name">Custom Status</field>
    <field name="code">CUSTOM</field>
    <field name="sequence">25</field>
    <field name="is_active">True</field>
    <field name="color">3</field>
</record>
```

## Troubleshooting

### Common Issues

**Member Type Not Appearing in Lists**
- Check that `active` field is True
- Verify age eligibility if filtering by age
- Ensure proper `is_individual`/`is_organization` settings

**Status Transition Not Working**
- Verify `can_transition_to()` returns True
- Check if target status `requires_approval`
- Ensure no circular transition loops

**Auto-transition Not Occurring**
- Confirm `auto_transition_days` > 0
- Verify `next_status_id` is set
- Check that scheduled action is running

**Validation Errors on Save**
- Age range: min_age must be ≤ max_age
- Classification: must have either individual or organization
- Code format: only alphanumeric, underscore, hyphen
- Auto-approve logic: cannot have both auto_approve and requires_verification

### Debug Mode Features

Enable developer mode to access:
- Technical field information
- Database ID references
- Model inheritance details
- Computed field dependencies

### Performance Considerations

**Large Member Counts**
- Member count fields are computed on-demand
- Consider caching for high-traffic installations
- Use database indexes on frequently filtered fields

**Auto-transition Processing**
- Scheduled actions process transitions in batches
- Monitor execution time for large datasets
- Consider processing during off-peak hours

## Integration

### With Other AMS Modules

This module provides foundation data for:
- **ams_member_data**: Member classification and status
- **ams_membership_lifecycle**: Status transitions and renewals
- **ams_portal_core**: Portal access permissions
- **ams_billing_core**: Type-based pricing and permissions

### Extension Points

**Custom Business Logic**
- Override transition validation methods
- Add custom eligibility rules
- Extend auto-transition processing

**Additional Fields**
- Inherit models to add association-specific fields
- Create computed fields for complex business rules
- Add related fields for integration

## Development

### Running Tests

```bash
# Run all tests for this module
./odoo-bin -d test_db -i ams_member_types --test-enable --stop-after-init

# Run specific test class
./odoo-bin -d test_db --test-tags ams_member_types.test_member_types
```

### Code Structure

```
ams_member_types/
├── __init__.py                 # Package initialization
├── __manifest__.py            # Module definition
├── models/
│   ├── __init__.py           # Model imports
│   ├── member_type.py        # Member type model
│   └── member_status.py      # Member status model
├── views/
│   ├── member_type_views.xml # Type views and actions
│   └── member_status_views.xml # Status views and actions
├── data/
│   ├── member_type_data.xml  # Default member types
│   └── member_status_data.xml # Default member statuses
├── security/
│   └── ir.model.access.csv   # Access control rules
└── tests/
    └── test_member_types.py  # Unit tests
```

## Contributing

### Code Standards
- Follow Odoo development guidelines
- Include comprehensive docstrings
- Add unit tests for new functionality
- Validate with pylint and odoo-lint

### Submitting Changes
1. Create feature branch from main
2. Implement changes with tests
3. Update documentation as needed
4. Submit pull request with description

## License

LGPL-3

## Support

For issues and questions:
- Check existing GitHub issues
- Review troubleshooting section above
- Contact development team for custom requirements

## Changelog

### Version 1.0.0
- Initial release
- Complete member type and status management
- Pre-configured data for common association types
- Comprehensive validation and business rules
- Full test coverage