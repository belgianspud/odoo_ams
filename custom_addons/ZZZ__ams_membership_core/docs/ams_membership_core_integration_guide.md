# AMS Membership Core - Odoo 18 Integration Guide

## Overview
The AMS Membership Core module has been updated for full compatibility with Odoo Community 18 and proper integration with the ams_foundation module.

## Key Changes Made

### 1. **Manifest Updates**
- ✅ Added proper dependencies for Odoo 18
- ✅ Added external Python dependencies
- ✅ Added assets configuration for frontend
- ✅ Added pre/post init hooks
- ✅ Proper sequence and application flags

### 2. **Security Integration** 
- ✅ Groups inherit from foundation groups instead of duplicating
- ✅ Portal group extends foundation member group
- ✅ Complete access rights CSV with proper permissions
- ✅ Record rules for data privacy

### 3. **Partner Model Integration**
- ✅ Removed duplicated foundation fields
- ✅ Added membership-specific computed fields
- ✅ Proper synchronization with foundation member status
- ✅ Enhanced portal access logic
- ✅ Benefit management integration

### 4. **Portal Integration for Odoo 18**
- ✅ Updated portal templates with Odoo 18 styling
- ✅ Portal controllers with proper access control
- ✅ Enhanced search and filtering
- ✅ Bootstrap 5 compatible templates
- ✅ Proper breadcrumb navigation

### 5. **Cron Jobs**
- ✅ Automated lifecycle processing
- ✅ Renewal reminder generation
- ✅ Foundation status synchronization
- ✅ Engagement data cleanup

### 6. **Initialization Hooks**
- ✅ Pre-init validation of foundation dependency
- ✅ Post-init setup of defaults and sync
- ✅ Automatic benefit creation
- ✅ Member sync from foundation

## Integration Points with AMS Foundation

### Shared Data Models
```python
# Foundation provides:
- res.partner.is_member
- res.partner.member_status  
- res.partner.member_type_id
- ams.member.type
- ams.settings
- ams.engagement.rule

# Membership Core extends with:
- res.partner.membership_ids
- res.partner.subscription_ids
- res.partner.current_membership_id
- ams.membership
- ams.subscription
- ams.benefit
```

### Status Synchronization
The module includes bidirectional sync between:
- Foundation `member_status` ↔ Membership Core `membership.state`
- Foundation member data ↔ Active membership records
- Portal access ↔ Product configurations

### Security Groups Hierarchy
```
ams_foundation.group_ams_admin
├── ams_foundation.group_ams_manager
│   ├── group_membership_manager
│   └── ams_foundation.group_ams_staff
│       └── group_membership_user
└── ams_foundation.group_ams_member
    └── group_membership_portal (+ portal.group_portal)
```

## Installation Requirements

### Prerequisites
1. **Odoo Community 18.0+**
2. **ams_foundation module** (must be installed first)
3. Standard Odoo modules: `sale_management`, `account`, `portal`, `mail`

### Installation Order
1. Install `ams_foundation`
2. Install `ams_membership_core`  
3. Run post-init sync (automatic)

## Key Features

### For Members (Portal)
- ✅ View memberships and subscriptions
- ✅ Access renewal functionality  
- ✅ Manage subscription status (pause/resume)
- ✅ View active benefits
- ✅ Odoo 18 responsive design

### For Staff
- ✅ Complete membership lifecycle management
- ✅ Subscription management (publications, chapters)
- ✅ Benefit configuration and tracking
- ✅ Mass renewal processing
- ✅ Automated status transitions
- ✅ Integration with sales and accounting

### For Managers  
- ✅ Product configuration for memberships/subscriptions
- ✅ Benefit configuration and rules
- ✅ Advanced reporting and analytics
- ✅ System configuration and settings

## Product Types Supported

### Membership Products
- Individual memberships (1 active per member)
- Automatic portal access
- Benefit assignment
- Renewal workflows

### Subscription Products  
- Publications (digital/print)
- Chapter memberships
- Event access
- Multiple active subscriptions allowed

### Benefits System
- Discount benefits (percentage/fixed)
- Access benefits (portal/content)
- Usage tracking and limits
- Automatic application

## Technical Architecture

### Models
```
ams.membership          # Core membership records
├── ams.renewal         # Renewal tracking
├── ams.benefit         # Benefit definitions  
│   └── ams.benefit.usage # Usage tracking
└── ams.subscription    # Non-membership subscriptions
    ├── Publication subscriptions
    ├── Chapter memberships  
    └── Event access
```

### Controllers
- `/my/memberships` - Portal membership list/detail
- `/my/subscriptions` - Portal subscription management
- Renewal and payment integration

### Automation
- Daily lifecycle processing
- Renewal reminder generation  
- Foundation status sync
- Portal access management

## Configuration Steps

### 1. Configure AMS Settings
Navigate to: **Association Management > Configuration > AMS Settings**
- Set member number format
- Configure grace periods  
- Enable portal user creation
- Set renewal reminder days

### 2. Create Member Types (Foundation)
Navigate to: **Association Management > Configuration > Member Types**
- Define membership categories
- Set pricing and duration
- Configure approval workflows

### 3. Configure Subscription Products
Navigate to: **Association Management > Configuration > Subscription Products**
- Enable "Subscription Product" toggle
- Select product type (membership/publication/chapter)
- Configure benefits and portal access
- Set renewal parameters

### 4. Set Up Benefits
Navigate to: **Association Management > Configuration > Member Benefits**
- Create discount benefits
- Configure access benefits
- Set usage limits and rules

## Troubleshooting

### Common Issues
1. **Foundation not installed**: Install ams_foundation first
2. **Portal access issues**: Check product portal access settings
3. **Status sync problems**: Run sync cron job manually
4. **Missing benefits**: Run post-init hook or create manually

### Validation Commands
```python
# Check foundation integration
env['ams.settings'].search([('active', '=', True)])

# Sync member statuses  
env['res.partner']._compute_current_membership()

# Validate product configurations
products = env['product.template'].search([('is_subscription_product', '=', True)])
```

## Migration Notes

If upgrading from previous versions:
1. Backup data before upgrade
2. Install ams_foundation if not present
3. Run post-init hook for data sync
4. Validate member status sync
5. Test portal access functionality

## Support

For issues or questions:
1. Check Odoo logs for error messages
2. Validate module dependencies
3. Ensure proper security group assignments
4. Test with simple membership/subscription creation

This integration provides a robust, scalable membership management system that leverages both Odoo Community 18's features and the ams_foundation module's core functionality.