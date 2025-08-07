# AMS Base Accounting - User Guide

## Overview

The AMS Base Accounting module provides specialized accounting functionality for associations and membership organizations. It extends Odoo's standard accounting with features specifically designed for subscription-based membership revenue, deferred revenue recognition, and association-specific chart of accounts.

## Key Features

- **Product-Specific GL Accounts**: Assign specific revenue, expense, and receivable accounts to each subscription product
- **AMS Chart of Accounts**: Pre-configured accounts for membership organizations
- **Revenue Recognition**: Handle immediate and deferred revenue for subscriptions
- **Integration**: Seamless integration with standard Odoo accounting and your AMS subscription system

## Initial Setup

### Step 1: Run the AMS Accounting Setup Wizard

1. Navigate to **AMS → Configuration → Accounting Setup**
2. The wizard will show:
   - Option to create AMS-specific chart of accounts
   - Configure existing subscription products
   - Setup default journals

3. Click **Run Setup** to:
   - Create accounts like "Membership Revenue", "Deferred Revenue", etc.
   - Auto-configure existing subscription products
   - Set up AMS-specific journals

### Step 2: Review Your Chart of Accounts

1. Go to **AMS → Accounting → Chart of Accounts**
2. You'll see new accounts with AMS categories:
   - **4100**: Membership Revenue - Individual
   - **4110**: Membership Revenue - Enterprise  
   - **4200**: Publication Revenue
   - **4300**: Chapter Revenue
   - **1200**: Accounts Receivable - Memberships
   - **2300**: Deferred Membership Revenue

## Configuring Products

### Setting Up AMS Accounting for Products

1. Go to **AMS → Products → Subscription Products**
2. Edit any subscription product
3. Click the **AMS Accounting** tab

### Product Configuration Options

#### For New Products:
- **Use AMS Accounting**: Enable this to use AMS-specific accounting
- Products will auto-configure based on their subscription type

#### Manual Configuration:
**Revenue Accounts:**
- **Revenue Account**: Where subscription revenue is recorded
- **Deferred Revenue Account**: For prepaid annual subscriptions

**Asset Accounts:**
- **A/R Account**: Accounts receivable for outstanding invoices
- **Cash Account**: Where payments are deposited

**Expense Accounts:**
- **Expense Account**: Costs related to this product/service

### Auto-Configuration

The system automatically suggests accounts based on product type:
- **Individual Memberships** → Membership Revenue accounts
- **Enterprise Memberships** → Membership Revenue accounts  
- **Publications** → Publication Revenue accounts
- **Chapter Memberships** → Chapter Revenue accounts

## Day-to-Day Usage

### Creating Invoices

When you create invoices for subscription products:

1. **Standard Invoicing**: Works exactly like normal Odoo invoicing
2. **AMS Enhancement**: Invoices with subscription products get tagged as "AMS Invoices"
3. **Account Assignment**: Revenue automatically posts to the product's assigned account

### Viewing AMS Transactions

1. **AMS Invoices**: Go to **AMS → Accounting → AMS Invoices**
   - Shows only invoices containing AMS subscription products
   - Filter by transaction type (membership payments, publication payments, etc.)

2. **Chart of Accounts**: Go to **AMS → Accounting → Chart of Accounts**
   - View all AMS-specific accounts
   - See how many products use each account
   - Click account names to see related transactions

### Revenue Recognition Workflow

#### Immediate Recognition (Monthly Subscriptions):
```
Customer Payment → Cash Account
                → Membership Revenue Account
```

#### Deferred Recognition (Annual Subscriptions):
```
Customer Payment → Cash Account
                → Deferred Revenue Account

Monthly Recognition → Deferred Revenue Account  
                   → Membership Revenue Account
```

## Common Scenarios

### Scenario 1: Setting Up Individual Membership Product

1. **Product Configuration:**
   - Product Type: Individual Membership
   - Subscription Period: Annual
   - Price: $120/year

2. **AMS Accounting Setup:**
   - Revenue Account: "4100 - Membership Revenue - Individual"
   - Deferred Account: "2300 - Deferred Membership Revenue" (for annual)
   - A/R Account: "1200 - Accounts Receivable - Memberships"

3. **Result:**
   - Annual payment creates deferred revenue
   - Monthly recognition transfers to revenue account

### Scenario 2: Enterprise Membership with Seats

1. **Product Configuration:**
   - Product Type: Enterprise Membership  
   - Has seat add-ons
   - Price: $500 base + $50/seat/month

2. **AMS Accounting Setup:**
   - Revenue Account: "4110 - Membership Revenue - Enterprise"
   - A/R Account: "1200 - Accounts Receivable - Memberships"

3. **Result:**
   - Base membership and seat charges post to enterprise revenue
   - Proper tracking of enterprise vs individual revenue

### Scenario 3: Publication Subscription

1. **Product Configuration:**
   - Product Type: Publication
   - Subscription Period: Monthly
   - Price: $25/month

2. **AMS Accounting Setup:**
   - Revenue Account: "4200 - Publication Revenue"
   - A/R Account: "1200 - Accounts Receivable - Memberships"

3. **Result:**
   - Monthly charges immediately recognized as publication revenue
   - Separate tracking from membership revenue

## Reports and Analysis

### Financial Reports

Use standard Odoo financial reports with AMS account filtering:

1. **Profit & Loss**: Filter by AMS account categories
2. **Balance Sheet**: See deferred revenue liabilities
3. **Aged Receivables**: Track outstanding membership payments

### AMS-Specific Analysis

1. **Revenue by Type**: Compare membership vs publication revenue
2. **Subscription Performance**: Track revenue by subscription tier
3. **Deferred Revenue**: Monitor unearned revenue balances

## Troubleshooting

### Common Issues

**Problem**: Products not showing AMS Accounting tab
- **Solution**: Ensure product is marked as "Subscription Product"

**Problem**: Accounts not auto-configuring  
- **Solution**: Check product has proper AMS Product Type set

**Problem**: Revenue posting to wrong account
- **Solution**: Verify product's assigned revenue account in AMS Accounting tab

### Configuration Validation

The system validates that:
- Subscription products have required accounts assigned
- Revenue accounts are income type
- A/R accounts are receivable type
- Product accounting is properly configured

## Advanced Features

### Custom Account Categories

You can extend account categories by:
1. Adding new selections to `ams_account_category` field
2. Creating custom account mapping logic
3. Extending the setup wizard

### Integration Points

The module integrates with:
- **Standard Odoo Accounting**: Uses native journal entries
- **AMS Subscriptions**: Reads product types and subscription data
- **Sales Module**: Enhances invoice processing

### API and Customization

Key methods for customization:
- `get_ams_journal_entry_data()`: Customize account assignment logic
- `_set_default_ams_accounts()`: Modify auto-configuration rules
- `create_ams_account_structure()`: Extend default chart of accounts

## Best Practices

### Account Organization
- Use consistent account numbering (4xxx for revenue, 2xxx for liabilities)
- Create separate accounts for different membership tiers
- Use descriptive account names

### Product Setup
- Always enable AMS Accounting for subscription products
- Review auto-configured accounts before going live
- Test invoice creation and posting

### Ongoing Management
- Regularly review AMS Invoices for proper categorization
- Monitor deferred revenue balances for annual subscriptions
- Use AMS Chart of Accounts to track product-specific performance

## Getting Help

### Support Resources
- Check product configuration in AMS Accounting tab
- Review Chart of Accounts for proper setup
- Use AMS Invoices view to verify transaction posting

### Technical Support
For issues with account assignment, revenue recognition, or integration problems, check the module logs or contact your system administrator.

---

## Quick Reference

### Menu Locations
- **Setup**: AMS → Configuration → Accounting Setup
- **Chart of Accounts**: AMS → Accounting → Chart of Accounts  
- **AMS Invoices**: AMS → Accounting → AMS Invoices
- **Product Configuration**: AMS → Products → [Product] → AMS Accounting tab

### Account Types
| Code | Name | Type | Purpose |
|------|------|------|---------|
| 4100 | Membership Revenue - Individual | Income | Individual member revenue |
| 4110 | Membership Revenue - Enterprise | Income | Enterprise member revenue |
| 4200 | Publication Revenue | Income | Publication subscription revenue |
| 4300 | Chapter Revenue | Income | Chapter membership revenue |
| 1200 | A/R - Memberships | Receivable | Outstanding membership invoices |
| 2300 | Deferred Revenue | Liability | Unearned prepaid subscriptions |