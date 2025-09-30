# Membership Management Module for Odoo Community 18

A comprehensive membership management module built from scratch for Odoo Community Edition 18.0. This module provides all the essential features needed to manage memberships, members, and membership-related payments.

## Features

### Core Functionality
- **Member Management**: Complete member registration and profile management
- **Membership Types**: Create different membership plans with varying prices and durations
- **Payment Tracking**: Track membership payments and generate invoices
- **Member Portal**: Self-service portal for members to view their membership status
- **Automated Workflows**: Automatic membership state updates and renewal reminders

### Key Components

#### Membership Types
- Flexible pricing and duration options (yearly, monthly, fixed period, unlimited)
- Auto-renewal capabilities
- Grace period settings
- Integration with product catalog

#### Membership Records
- Complete lifecycle management (draft → active → expired/cancelled)
- Payment status tracking
- Automated end date calculation
- Renewal management

#### Payment Management
- Multiple payment methods support
- Payment confirmation workflow
- Integration with Odoo accounting

#### Member Portal
- Self-service membership viewing
- Membership history
- Payment status visibility

#### Reporting & Analytics
- Membership statistics
- Payment reports
- Member lists and filters

## Installation

1. Copy the `membership_community` folder to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the "Membership Management" module

## Dependencies

- `base` - Core Odoo functionality
- `mail` - Email and chatter functionality
- `portal` - Customer portal access
- `account` - Accounting integration
- `sale` - Sales functionality

## Configuration

### Initial Setup

1. **Create Membership Types**:
   - Go to Membership → Configuration → Membership Types
   - Create different membership plans (Basic, Premium, etc.)
   - Set pricing, duration, and renewal settings

2. **Configure Security**:
   - Assign users to appropriate membership groups
   - Membership User: Can view and manage their own memberships
   - Membership Manager: Full access to all membership functions

3. **Set Up Payment Methods**:
   - Configure payment methods in the system
   - Set up accounting integration if needed

### Member Registration

1. **Create Member Records**:
   - Go to Membership → Memberships → Members
   - Create new member profiles or convert existing contacts

2. **Assign Memberships**:
   - Create membership records for each member
   - Select appropriate membership type
   - Set start dates and payment information

3. **Process Payments**:
   - Record membership payments
   - Generate invoices as needed
   - Track payment status

## Usage

### For Membership Managers

#### Managing Memberships
- View all memberships in the main dashboard
- Filter by status, payment state, expiration dates
- Bulk operations for renewals and invoicing

#### Payment Processing
- Record payments manually or integrate with payment processors
- Generate invoices for unpaid memberships
- Track payment history

#### Reporting
- View membership statistics
- Export member lists
- Monitor renewals and expirations

### For Members (Portal Users)

#### Self-Service Portal
- View current membership status
- Access membership history
- Check payment status and due dates

## Customization

The module is designed to be easily customizable. Common customizations include:

### Adding Custom Fields
```python
# In your custom module, extend the membership model
class Membership(models.Model):
    _inherit = 'membership.membership'
    
    custom_field = fields.Char(string='Custom Field')