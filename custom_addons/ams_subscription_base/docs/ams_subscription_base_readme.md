AMS Subscription Base Module - User Guide
Overview
The AMS Subscription Base module provides comprehensive subscription management for professional associations, enabling recurring membership billing, payment plans, and subscription lifecycle management.
Key Features

Subscription Plans: Define recurring membership plans with automatic renewal
Payment Plans: Allow members to pay in installments
Subscription Changes: Handle plan changes with proper proration
Automated Renewals: Automatic subscription renewal with invoice generation
Status Management: Track subscription lifecycle (Draft, Active, Grace, Lapsed, Cancelled)
Financial Integration: Full integration with Odoo's accounting system


Getting Started
1. Installation & Setup
After installing the module, you'll find new menu items under Membership > Subscriptions:

Subscription Plans
All Subscriptions
Payment Plans
Installments
Subscription Changes

2. Initial Configuration
Create Your First Subscription Plan

Navigate to Membership > Subscriptions > Subscription Plans
Click Create to add a new plan
Fill in the basic information:

Plan Name: e.g., "Annual Professional Membership"
Code: Short identifier (e.g., "ANN-PROF")
Product: Select or create a service product for billing
Duration: Number of months (default: 12)
Price: Taken from the related product


Configure renewal settings:

Auto Renew: Enable automatic renewal
Renewal Notice Days: Days before expiry to send notice (default: 30)
Grace Period Days: Days after expiry before marking as lapsed (default: 30)



Example Subscription Plans Setup
Basic Professional Membership

Code: BASIC
Duration: 12 months
Auto Renew: Yes
Grace Period: 30 days

Student Membership

Code: STUDENT
Duration: 12 months
Auto Renew: Yes
Grace Period: 60 days (longer for students)

Corporate Membership

Code: CORP
Duration: 12 months
Auto Renew: Yes
Grace Period: 15 days (shorter for corporate)


Core Functionality
Subscription Management
Creating a New Subscription

Go to Membership > Subscriptions > All Subscriptions
Click Create
Fill in the subscription details:

Subscriber: Select the member/contact
Subscription Plan: Choose from your configured plans
Start Date: When the subscription begins
End Date: Automatically calculated based on plan duration
Auto Renew: Inherited from plan but can be overridden


Click Activate to make the subscription active

Subscription States

Draft: Initial state, subscription not yet active
Active: Subscription is current and valid
Grace Period: Subscription expired but still within grace period
Lapsed: Subscription expired beyond grace period
Cancelled: Subscription terminated by user or system

Manual Operations
Renewing a Subscription

Open the subscription record
Click Renew button
System extends the end date by the plan duration

Cancelling a Subscription

Open the subscription record
Click Cancel button
Confirm the cancellation

Payment Plans
Setting Up Payment Plans

Navigate to Membership > Subscriptions > Payment Plans
Click Create to add a new payment plan
Configure the plan:

Plan Name: e.g., "3 Monthly Payments"
Total Amount: Full subscription amount
Number of Installments: How many payments (e.g., 3)
Payment Frequency: Monthly, Quarterly, etc.
Late Fee: Fee for overdue payments
Grace Period: Days before marking overdue



Example Payment Plan Configuration
Quarterly Payment Plan

Name: "4 Quarterly Payments"
Total Amount: $500
Installments: 4
Frequency: Quarterly
Late Fee: $25
Grace Period: 5 days

Using Payment Plans with Subscriptions

Create or edit a subscription
In the Payment Plan field, select your configured payment plan
Save the subscription
Click Setup Payment Plan to generate the installment schedule
View installments in the Payment Plan tab

Managing Installments
Viewing Installments

Go to Membership > Subscriptions > Installments
Filter by status: Pending, Paid, Overdue

Processing Payments

Open an installment record
Click Mark as Paid when payment is received
Enter payment details (method, reference, etc.)

Sending Reminders

Open a pending installment
Click Send Reminder to email the member
System automatically sends reminders 3 days before due date

Subscription Changes
Types of Changes

Plan Change: Upgrade or downgrade subscription plan
Payment Plan Change: Modify payment schedule
Pause: Temporarily suspend subscription
Resume: Reactivate paused subscription
Early Termination: Cancel before expiry
Extension: Extend subscription period

Processing a Plan Change

Open the subscription record
Click Change Subscription
Select change details:

Change Type: Plan Change
New Plan: Select the target plan
Effective Date: When change takes effect
Reason: Why the change is needed


Review the Financial Preview showing proration calculations
Choose Create Request (requires approval) or Process Immediately

Proration Calculations
The system automatically calculates:

Days Remaining: Time left on current subscription
Proration Credit: Refund for unused portion of old plan
Proration Charge: Cost for new plan for remaining period
Net Adjustment: Final amount to charge/credit

Approval Workflow
For subscription changes requiring approval:

Draft: Initial change request created
Submitted: Request submitted for approval
Approved: Manager approves the change
Processed: Change applied to subscription
Rejected/Cancelled: Change denied or cancelled


Member Portal Integration
Subscription Information on Member Records
When viewing a member's record (Partner form):
Subscription Tab

Current subscription status
All historical subscriptions
Payment history and balance due

Subscription Statistics

Active subscription indicator
Payment plan information (if applicable)
Next installment due date
Overdue installment count

Creating Subscriptions from Member Records

Open a member's record
Click Add Subscription button (if no active subscription)
System opens subscription form with member pre-filled
Complete subscription details and activate


Automated Processes
Automatic Renewal
The system includes a scheduled task that runs daily to:

Find subscriptions due for renewal
Check if auto-renew is enabled
Verify payment status (no outstanding balance)
Create renewal invoices
Extend subscription periods
Log renewal activities

Status Updates
Another scheduled task updates subscription statuses:

Move expired active subscriptions to grace period
Move grace period subscriptions to lapsed (after grace period expires)
Log status changes for audit trail

Payment Reminders
Automated reminder system:

Sends payment reminders 3 days before installment due dates
Sends overdue notices for late payments
Tracks reminder history on installment records


Financial Integration
Invoice Generation
Subscription Activation

Creates initial invoice when subscription is activated
Links invoice to subscription record
Uses product and pricing from subscription plan

Renewal Processing

Generates renewal invoices automatically
Maintains relationship between invoices and subscriptions
Updates financial totals on subscription

Level/Plan Changes

Creates adjustment invoices for upgrades (additional charge)
Creates credit notes for downgrades (refund credit)
Handles complex proration calculations

Payment Plans and Invoicing
Installment Invoices

Each installment can generate its own invoice
Click Create Invoice on installment records
Tracks payment status and reconciliation

Financial Reporting
View subscription financial data:

Total invoiced amount
Total payments received
Outstanding balance
Payment history


Reports and Analytics
Subscription Analytics
Subscription Plan Statistics

Active subscription count per plan
Total revenue generated
Renewal rates and trends

Member Subscription Overview

Current subscription status
Payment history and balance
Subscription lifecycle analytics

Financial Reports
Payment Plan Performance

Installment payment rates
Overdue payment statistics
Late fee collection

Revenue Tracking

Subscription revenue by plan
Payment plan vs. full payment comparison
Proration adjustment tracking


Common Workflows
Workflow 1: New Member Enrollment

Create contact record for new member
Navigate to member's record
Click Add Membership (in Membership tab)
Create subscription:

Select appropriate subscription plan
Set start date (usually today)
Enable auto-renew
Choose payment plan if needed


Activate subscription
System generates initial invoice
Process payment when received

Workflow 2: Mid-Year Plan Upgrade

Open member's current subscription
Click Change Subscription
Select:

Change Type: Plan Change
New Plan: Upgraded plan
Effective Date: Today or future date
Reason: Member Request


Review proration calculation
Process change (creates adjustment invoice)
Collect additional payment if required

Workflow 3: Setting Up Payment Plan

Create subscription normally
Select payment plan in subscription form
Save subscription
Click Setup Payment Plan
System generates installment schedule
Member receives first installment invoice
Monitor installment payments in Installments menu
Send reminders for upcoming payments

Workflow 4: Annual Renewal Processing
Automated Process:

System runs daily renewal check
Identifies subscriptions due for renewal
Creates renewal invoices
Extends subscription periods
Logs renewal activities

Manual Process:

Review subscriptions expiring soon
Contact members with outstanding balances
Process manual renewals as needed
Update subscription statuses


Configuration Options
System Parameters
Configure these settings in Settings > Technical > Parameters > System Parameters:

membership.grace_period_days: Default grace period (30)
membership.card_number_prefix: Card number prefix for integration

Email Templates
Customize notification templates:

Installment Reminders: Payment due notifications
Overdue Notices: Late payment alerts
Subscription Changes: Change confirmation emails

Automated Tasks
Review and configure scheduled tasks:

Process Subscription Renewals: Daily at 2 AM
Update Subscription Statuses: Daily at 1 AM
Send Payment Reminders: Daily at 9 AM
Process Overdue Installments: Daily at 10 AM


Troubleshooting
Common Issues
Subscription Won't Renew Automatically

Check if auto-renew is enabled
Verify no outstanding balance
Confirm subscription is in active/grace status
Check system parameters for grace period settings

Payment Plan Setup Fails

Ensure subscription has valid start/end dates
Verify payment plan total amount matches subscription
Check that installment schedule doesn't exist already

Proration Calculations Incorrect

Verify subscription start/end dates are accurate
Check that plan prices are current
Ensure change effective date is within subscription period

Installment Reminders Not Sending

Check email template configuration
Verify member email addresses
Review email server settings
Check scheduled task is active

Data Issues
Missing Financial Data

Ensure proper accounting setup
Verify product categories have income accounts
Check currency settings match company currency

Subscription Status Problems

Run the status update process manually
Check grace period configuration
Verify end dates are set correctly


Best Practices
Subscription Planning

Design Clear Plan Structure

Use descriptive plan names and codes
Set appropriate grace periods
Configure auto-renewal strategically


Payment Plan Strategy

Offer reasonable installment options
Set appropriate late fees
Monitor payment collection rates



Process Management

Regular Monitoring

Review expiring subscriptions weekly
Monitor overdue payments daily
Track renewal success rates monthly


Member Communication

Send renewal notices early
Provide clear payment instructions
Follow up on overdue accounts promptly


Data Maintenance

Keep member contact information current
Archive cancelled subscriptions appropriately
Regular backup of subscription data



Financial Controls

Revenue Tracking

Monitor subscription revenue trends
Track payment plan performance
Analyze proration impact on cash flow


Accounts Receivable

Follow up on overdue balances
Implement dunning procedures
Consider payment plan options for struggling members




Integration with Other Modules
This module works seamlessly with other AMS modules:

Membership Base: Core member management
Membership Levels: Tiered membership with level-specific benefits
Events & Certificates: Member event pricing and CEU tracking
Communications: Automated subscription-related messaging


Support and Updates
For additional support or feature requests:

Review module documentation
Check community forums
Contact your system administrator
Submit enhancement requests for future versions