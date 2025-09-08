# AMS Subscription Billing (Core)

Core subscription billing functionality for Association Management System (AMS) built on Odoo Community 18.

## Overview

This module provides essential automated billing functionality for AMS subscriptions including:

- 🔄 **Automated Billing Schedules** - Set up recurring billing based on subscription periods
- 📄 **Invoice Generation** - Automatically generate invoices for subscription renewals  
- 💰 **Payment Tracking** - Monitor payment status and identify overdue accounts
- 📧 **Payment Reminders** - Send automated reminders for overdue invoices
- ⚙️ **Manual Billing** - Process billing manually when needed
- 📊 **Basic Analytics** - Track billing performance and outstanding balances

## Dependencies

This module requires:
- `base` (Odoo core)
- `mail` (Email functionality)
- `account` (Accounting/Invoicing)
- `ams_subscriptions` (Core AMS subscription module)

## Installation

1. Place this module in your Odoo addons directory
2. Restart Odoo server
3. Go to Apps menu and install "AMS Subscription Billing (Core)"
4. The module will automatically set up billing for existing active subscriptions

## Configuration

### Basic Setup

1. Go to **Settings > AMS Billing**
2. Configure billing automation settings:
   - Enable/disable automatic invoice sending
   - Set up payment reminder schedules
   - Configure weekend billing adjustments

3. Set default templates:
   - Invoice email template
   - Payment reminder template

### Billing Schedules

Billing schedules are automatically created when subscriptions are activated. Each schedule:
- Follows the subscription's billing frequency (monthly, quarterly, annual)
- Generates invoices on the due date
- Tracks billing history and statistics

## Key Features

### Automated Billing

- **Billing Schedules**: Automatically created for active subscriptions
- **Cron Jobs**: Daily processing of due billing schedules
- **Invoice Generation**: Creates and posts invoices automatically
- **Email Sending**: Optionally sends invoices to customers

### Payment Management

- **Payment Status Tracking**: Current, Pending, or Overdue
- **Overdue Detection**: Automatically marks overdue invoices
- **Payment Reminders**: Configurable reminder schedules (default: 1, 7, 14 days)
- **Manual Actions**: Send payment reminders manually

### Manual Billing

Use the Manual Billing wizard to:
- Bill specific subscriptions outside of schedule
- Force billing for subscriptions not yet due
- Process bulk billing operations

### Monitoring & Analytics

- **Billing Dashboard**: Overview of subscription billing status
- **Failed Events**: Track and resolve billing errors
- **System Health**: Weekly health checks for billing integrity
- **Statistics**: Track total billed amounts and outstanding balances

## Menu Structure

```
AMS > Billing
├── Operations
│   ├── Billing Schedules
│   ├── Billing Events  
│   ├── Failed Events
│   └── Manual Billing
├── Subscriptions
│   ├── Billing Dashboard
│   └── Overdue Subscriptions
├── Invoices
│   ├── All Subscription Invoices
│   └── Overdue Invoices
├── Reports
│   ├── Billing Summary
│   └── Payment Status
└── Configuration
    ├── Billing Settings
    └── Email Templates
```

## Cron Jobs

The module sets up several automated tasks:

- **Daily 2:00 AM**: Process due billing schedules
- **Daily 8:00 AM**: Mark overdue invoices
- **Daily 10:00 AM**: Send payment reminders
- **Daily 12:00 PM**: Process pending billing events
- **Weekly 6:00 AM**: Subscription billing health check

## Integration Points

### With AMS Base Accounting
- Inherits GL account configuration
- Uses AMS revenue/receivable accounts
- Integrates with accounting periods

### With AMS Subscriptions  
- Extends subscription models with billing fields
- Hooks into subscription lifecycle (activate/suspend/terminate)
- Maps subscription periods to billing frequencies

### With AMS Revenue Recognition
- Invoice posting triggers revenue schedules
- Integration through account.move extensions
- Proper revenue recognition for subscription billing

## Security

Two main user groups:
- **AMS Billing User**: View billing information
- **AMS Billing Manager**: Full billing management access

Multi-company support with proper record rules.

## Customization

This is the core billing module. Advanced features are available in extension modules:

- `ams_advanced_dunning` - Multi-step dunning processes
- `ams_payment_retry` - Automated payment retry logic  
- `ams_payment_methods` - Stored payment methods and gateway integration
- `ams_billing_analytics` - Advanced MRR/ARR analytics
- `ams_customer_portal` - Customer self-service portal
- `ams_proration_engine` - Complex proration calculations

## Troubleshooting

### Common Issues

1. **Billing not processing**: Check that cron jobs are active
2. **Emails not sending**: Verify email templates are configured
3. **Missing billing schedules**: Run the health check cron job
4. **Configuration issues**: Use the "Test Configuration" button in settings

### Logs

Check logs under **Settings > Technical > Logging** for:
- `ams_subscription_billing.post_init` - Installation logs
- `ams_subscription_billing.health_check` - Weekly health check results
- Billing processing errors and warnings

## Support

For issues and feature requests, contact your AMS development team.

## License

LGPL-3