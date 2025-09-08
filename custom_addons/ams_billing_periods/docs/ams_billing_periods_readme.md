# AMS Billing Periods

A foundational module for the Association Management System (AMS) that provides billing period definitions for subscription cycles, membership renewals, and recurring billing.

## Overview

The AMS Billing Periods module enables associations to define and manage different billing cycles for their products and services. This includes standard periods like monthly, quarterly, and annual billing, as well as custom periods for specific organizational needs.

## Features

### Billing Period Management
- **Flexible Duration Configuration**: Support for days, weeks, months, and years
- **Automatic Calculations**: Total days computation for easy comparison
- **Default Period Designation**: One period can be marked as default for new subscriptions
- **Display Ordering**: Sequence control for consistent presentation

### Pre-configured Periods
- **Standard Periods**: Daily, Weekly, Monthly, Quarterly, Semi-Annual, Annual, Biennial
- **Trial Periods**: 7-day and 30-day trial options (inactive by default)
- **Academic Periods**: Academic year and fiscal year options
- **Custom Periods**: Extensible for organization-specific needs

### Business Logic
- **Date Calculations**: Methods to calculate next billing date and period end
- **Period Validation**: Constraints to ensure valid duration configurations
- **Default Management**: Automatic handling of default period logic

## Installation

### Prerequisites
- Odoo Community 18.0 or later
- No additional dependencies required

### Install Steps

1. **Copy Module**: Place the `ams_billing_periods` folder in your Odoo custom addons directory
2. **Update Apps List**: In Odoo, go to Apps → Update Apps List
3. **Install Module**: Search for "AMS Billing Periods" and click Install

## Configuration

### Accessing Billing Periods
1. Navigate to **Settings → Billing Periods**
2. Review the pre-configured periods
3. Customize existing periods or create new ones as needed

### Setting Default Period
1. Open any billing period
2. Check the "Default Period" checkbox
3. Or use the "Set as Default" button in the form header

## Pre-configured Billing Periods

| Period | Duration | Total Days | Default | Status |
|--------|----------|------------|---------|---------|
| Daily | 1 day | 1 | No | Active |
| Weekly | 1 week | 7 | No | Active |
| Bi-Weekly | 2 weeks | 14 | No | Active |
| Monthly | 1 month | ~30 | No | Active |
| Quarterly | 3 months | ~91 | No | Active |
| Semi-Annual | 6 months | ~183 | No | Active |
| **Annual** | 12 months | ~365 | **Yes** | Active |
| Biennial | 24 months | ~730 | No | Active |
| Triennial | 36 months | ~1095 | No | Active |

### Trial Periods (Inactive by default)
| Period | Duration | Purpose |
|--------|----------|---------|
| 7-Day Trial | 7 days | Short evaluation period |
| 30-Day Trial | 30 days | Extended evaluation period |

### Special Periods (Inactive by default)
| Period | Duration | Purpose |
|--------|----------|---------|
| Academic Year | 10 months | Educational associations |
| Fiscal Year | 12 months | Government-aligned billing |
| Conference Season | 18 months | Event-based memberships |

## Usage Examples

### Creating a Custom Billing Period

```python
# Create a custom 18-month period
period = env['ams.billing.period'].create({
    'name': 'Conference Season',
    'code': 'CONF_SEASON',
    'duration_value': 18,
    'duration_unit': 'months',
    'description': 'Membership spanning major conference seasons',
    'sequence': 85,
})
```

### Getting the Default Period

```python
# Get default billing period
default_period = env['ams.billing.period'].get_default_period()
```

### Calculating Next Billing Date

```python
# Calculate next billing date from today
period = env.ref('ams_billing_periods.billing_period_monthly')
next_date = period.calculate_next_date()

# Calculate from specific date
from datetime import date
start_date = date(2024, 1, 1)
next_date = period.calculate_next_date(start_date)
```

### Getting Period Date Range

```python
# Get full period range
period = env.ref('ams_billing_periods.billing_period_quarterly')
start_date, end_date = period.get_period_range(date(2024, 1, 1))
# Returns: (date(2024, 1, 1), date(2024, 3, 31))
```

## API Reference

### ams.billing.period

#### Methods

**get_default_period()** (static)
- Get the default billing period
- Returns: recordset

**calculate_next_date(start_date=None)**
- Calculate next billing date from start date
- Returns: date

**calculate_period_end(start_date=None)**
- Calculate end date of billing period
- Returns: date

**get_period_range(start_date=None)**
- Get start and end dates for period
- Returns: tuple (start_date, end_date)

**get_periods_by_duration(duration_unit=None)**
- Filter periods by duration unit
- Returns: recordset

**get_shortest_period()** / **get_longest_period()** (static)
- Get periods by duration length
- Returns: recordset

**action_set_as_default()**
- Set period as default (unsets others)
- Returns: notification action

#### Fields

**Core Fields**
- `name` (Char): Period name (e.g., "Monthly")
- `code` (Char): Unique code (e.g., "MONTHLY")
- `duration_value` (Integer): Numeric duration (e.g., 1, 3, 12)
- `duration_unit` (Selection): Time unit (days/weeks/months/years)
- `sequence` (Integer): Display order
- `is_default` (Boolean): Default period flag
- `description` (Text): Optional description
- `active` (Boolean): Active status

**Computed Fields**
- `total_days` (Integer): Approximate total days
- `period_summary` (Char): Human-readable summary (e.g., "3 Months (~91 days)")

#### Constraints

**Validation Rules**
- Code must be unique and alphanumeric (with _ and -)
- Name must be unique
- Duration value must be positive
- Only one period can be default
- Reasonable duration limits enforced

## Integration

### With Other AMS Modules

This module provides foundation data for:
- **ams_subscription_products**: Billing cycle configuration
- **ams_membership_lifecycle**: Renewal period management
- **ams_billing_core**: Invoice scheduling and recurring billing
- **ams_pricing_engine**: Period-based pricing calculations

### Extension Points

**Custom Duration Units**
- Extend selection field for additional time units
- Implement custom calculation logic

**Additional Attributes**
- Add period-specific configurations
- Create computed fields for business rules

**Integration Hooks**
- Override calculation methods for custom logic
- Add related fields for external system integration

## Data Management

### Importing Custom Periods

```xml
<record id="custom_billing_period" model="ams.billing.period">
    <field name="name">Custom Period</field>
    <field name="code">CUSTOM</field>
    <field name="duration_value">15</field>
    <field name="duration_unit">months</field>
    <field name="sequence">77</field>
    <field name="is_default">False</field>
    <field name="description">Custom 15-month billing cycle</field>
</record>
```

### CSV Import Format

```csv
name,code,duration_value,duration_unit,sequence,is_default,description
Custom Quarterly,CUSTOM_Q,4,months,52,False,4-month custom period
```

## Troubleshooting

### Common Issues

**Multiple Default Periods**
- Only one period can be marked as default
- Use "Set as Default" action to automatically handle switching

**Cannot Deactivate Default Period**
- Default periods cannot be archived
- Set another period as default first

**Duration Validation Errors**
- Check that duration value is positive
- Ensure duration doesn't exceed reasonable limits (10 years max)

### Performance Considerations

**Period Calculations**
- Date calculations use efficient dateutil library
- Total days are stored for quick comparisons

**Default Period Lookups**
- Default period queries use database index
- Consider caching for high-frequency access

## Testing

### Running Tests

```bash
# Run all tests for this module
./odoo-bin -d test_db -i ams_billing_periods --test-enable --stop-after-init

# Run specific test class
./odoo-bin -d test_db --test-tags ams_billing_periods.test_billing_periods
```

### Test Coverage

The module includes comprehensive tests for:
- Billing period creation and validation
- Duration calculations and date arithmetic
- Default period management
- Business logic and constraints
- Edge cases and error conditions

## Contributing

### Code Standards
- Follow Odoo development guidelines
- Include comprehensive docstrings
- Add unit tests for new functionality
- Validate with pylint and odoo-lint

### Adding New Features
1. Create feature in models/billing_period.py
2. Add corresponding views if needed
3. Include test cases
4. Update documentation

## License

LGPL-3

## Support

For issues and questions:
- Check existing documentation
- Review test cases for usage examples
- Contact development team for enhancements

## Changelog

### Version 1.0.0
- Initial release
- Complete billing period management system
- 15+ pre-configured billing periods
- Comprehensive date calculation methods
- Full validation and business rules
- Complete test coverage
- Integration-ready design