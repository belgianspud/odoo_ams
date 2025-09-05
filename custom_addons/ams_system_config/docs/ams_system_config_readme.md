# AMS System Configuration Module

## Overview

The AMS System Configuration module provides centralized configuration management for the Association Management System (AMS). It serves as the control center for global settings, feature toggles, and system-wide defaults that affect all other AMS modules.

## Features

### Global Configuration Management
- Centralized settings for all AMS modules
- Feature toggle management for optional functionality
- System-wide defaults and policies
- Configuration validation and constraints

### Member ID Management
- Auto-generation settings for member IDs
- Configurable prefix and padding formats
- Sequence management and reset capabilities
- Test generation functionality

### Membership Lifecycle Defaults
- Grace period configuration
- Renewal window settings
- Auto-renewal preferences
- Reminder frequency settings

### Portal and Communication Settings
- Portal access configuration
- Email verification requirements
- Communication tracking preferences
- Default template settings

### Financial Configuration
- Fiscal year start month
- Default currency settings
- Multi-currency support toggle
- Chapter revenue sharing configuration

### Feature Toggles
- Enterprise subscription features
- Event member pricing
- Continuing education requirements
- Fundraising capabilities
- Data quality features

## Installation

1. Install via Odoo Apps interface or command line:
   ```bash./odoo-bin -d <database> -i ams_system_config

2. Access configuration via Settings > AMS Settings > AMS Configuration

## Dependencies

- base (Odoo core)
- base_setup (Odoo base setup)
- ams_member_data (for member ID sequence integration)

## Configuration Access

### Via Web Interface
1. Go to Settings menu
2. Navigate to AMS Settings
3. Click AMS Configuration
4. Modify settings as needed
5. Click Save to apply changes

### Via Code
```pythonGet configuration parameter
value = self.env['ir.config_parameter'].sudo().get_param('ams.grace_period_days')Set configuration parameter
self.env['ir.config_parameter'].sudo().set_param('ams.portal_enabled', 'True')Use configuration settings model
config = self.env['ams.config.settings'].create({})
config.grace_period_days = 45
config.execute()

## Key Configuration Parameters

### Member Management
- `ams.auto_member_id`: Enable automatic member ID generation
- `ams.member_id_prefix`: Prefix for member IDs (default: "M")
- `ams.member_id_padding`: Number of digits for sequence (default: 6)
- `ams.grace_period_days`: Default grace period in days (default: 30)
- `ams.renewal_window_days`: Renewal notice period (default: 90)

### Portal Settings
- `ams.portal_enabled`: Enable member portal (default: True)
- `ams.portal_registration_enabled`: Allow self-registration (default: False)
- `ams.email_verification_required`: Require email verification (default: True)

### Financial Settings
- `ams.fiscal_year_start`: Fiscal year start month (default: "january")
- `ams.default_currency_id`: Default currency for transactions
- `ams.multi_currency_enabled`: Enable multi-currency support (default: False)

### Feature Toggles
- `ams.enterprise_subscriptions_enabled`: Enterprise features (default: True)
- `ams.event_member_pricing`: Member event pricing (default: True)
- `ams.fundraising_enabled`: Fundraising features (default: True)
- `ams.continuing_education_required`: CE requirements (default: False)

### Data Management
- `ams.duplicate_detection_enabled`: Duplicate detection (default: True)
- `ams.audit_trail_enabled`: Change tracking (default: True)
- `ams.data_retention_years`: Data retention period (default: 7)

## API Reference

### AMSConfigSettings Model

#### Key Methods
- `get_fiscal_year_dates(date=None)`: Calculate fiscal year dates
- `action_reset_member_sequence()`: Reset member ID sequence
- `action_test_member_id_generation()`: Test member ID generation

#### Validation Methods
- `_check_member_id_padding()`: Validate member ID padding (3-10 digits)
- `_check_grace_period_days()`: Validate grace period (0-365 days)
- `_check_renewal_window_days()`: Validate renewal window (7-365 days)
- `_check_chapter_percentage()`: Validate chapter percentage (0-100%)
- `_check_data_retention_years()`: Validate retention period (1-50 years)

## Integration with Other Modules

### Layer 2 Modules
- **ams_member_types**: Uses feature toggles for member classification
- **ams_billing_periods**: Uses fiscal year and currency settings
- **ams_products_base**: Uses pricing and currency configuration

### Layer 3 Modules
- **ams_membership_lifecycle**: Uses grace period and renewal settings
- **ams_subscription_enterprise**: Uses enterprise feature toggles
- **ams_event_pricing**: Uses member pricing feature toggle
- **ams_fundraising**: Uses fundraising feature toggle

### Layer 4 Modules
- **ams_portal_core**: Uses portal configuration settings
- **ams_analytics**: Uses fiscal year settings for reporting

## Testing

Run tests with:
```bash./odoo-bin -d <database> -i ams_system_config --test-enable --stop-after-init

### Test Coverage
- Configuration parameter validation
- Default value setting and retrieval
- Fiscal year calculation
- Member sequence management
- Feature toggle functionality
- Integration with ir.config_parameter

## Security

### Access Rights
- **System Administrators**: Full read/write access to all settings
- **Regular Users**: Read-only access to view current configuration
- **Portal Users**: No access to configuration settings

### Configuration Parameters
- All parameters are stored in `ir.config_parameter` with appropriate access controls
- Sensitive settings require system administrator privileges
- Changes are logged in the audit trail when enabled

## Best Practices

### Configuration Management
1. **Test Changes**: Use test database before applying to production
2. **Document Changes**: Keep track of configuration modifications
3. **Backup Settings**: Export configuration before major changes
4. **Validate Settings**: Ensure settings are appropriate for your association

### Performance Considerations
1. **Cache Timeout**: Adjust cache timeout based on system load
2. **Batch Processing**: Set batch size appropriate for server resources
3. **Feature Toggles**: Disable unused features to improve performance

### Security Recommendations
1. **Access Control**: Limit configuration access to trusted administrators
2. **Regular Review**: Periodically review and audit configuration settings
3. **Change Management**: Implement approval process for configuration changes

## Troubleshooting

### Common Issues

#### Configuration Not Saving
- Check user permissions for system administration
- Verify database write access
- Check for validation errors in server logs

#### Feature Toggles Not Working
- Ensure dependent modules are installed
- Check for caching issues (restart server if needed)
- Verify configuration parameters are properly set

#### Member ID Generation Issues
- Check sequence configuration and permissions
- Verify member ID format settings
- Test generation using built-in test function

### Error Messages

#### "Member ID padding must be between 3 and 10 digits"
- Adjust member_id_padding to valid range
- Use reasonable padding for your member count

#### "Grace period must be between 0 and 365 days"
- Set grace_period_days to valid range
- Consider your association's renewal policies

## Contributing

This module follows Odoo development best practices:
- Configuration settings use res.config.settings pattern
- All parameters stored in ir.config_parameter
- Comprehensive validation and error handling
- Full test coverage with realistic scenarios

## License

LGPL-3

## Support

For support and documentation, see the main AMS project repository.