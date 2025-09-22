Membership Level Module - User Guide
Overview
The Membership Level module extends the base membership system with tiered membership functionality, allowing you to create different membership levels with varying prices, benefits, and upgrade/downgrade workflows.
Key Features

Multiple Membership Tiers: Create Individual, Student, Organization, Premium, etc.
Level Changes: Handle upgrades and downgrades with automatic proration
Member Benefits: Track and manage benefits available to each level
Automated Workflows: Email notifications and approval processes
Financial Integration: Automatic invoice generation for level changes


Getting Started
1. Installation & Setup
After installing the module, you'll find new menu items under Membership:

Membership Levels
Level Changes
Member Benefits

2. Initial Configuration
Create Your First Membership Level

Navigate to Membership > Membership Levels
Click Create to add a new level
Fill in the basic information:

Level Name: e.g., "Individual Member"
Code: Short identifier (e.g., "IND")
Duration: Number of months (default: 12)
Price: Annual membership fee
Sequence: Display order (lower numbers appear first)



Configure Level Types

Individual Membership: Check this for personal memberships
Organization Membership: Check this for corporate memberships

Set Max Members if there's a limit per organization



Set Benefits & Features

Event Discount %: Discount percentage for events (0-100)
Voting Rights: Whether members can vote
Benefits: Free-text description of level benefits


Working with Membership Levels
Creating Multiple Levels
Example Setup for a Professional Association:

Student Member

Code: STU
Price: $50
Duration: 12 months
Event Discount: 25%


Individual Member

Code: IND
Price: $150
Duration: 12 months
Event Discount: 15%


Premium Member

Code: PREM
Price: $300
Duration: 12 months
Event Discount: 30%


Corporate Member

Code: CORP
Price: $1000
Duration: 12 months
Organization Membership: ✓
Max Members: 10



Product Integration
The module automatically creates products for billing:

Auto Create Product: Enabled by default
Products are created in the "Membership" category
Product prices sync with level prices
Used for invoice generation


Managing Member Level Changes
Creating a Level Change Request
Method 1: From Membership Record

Open a membership record
Click Change Level button
Select the new level
Choose effective date
Select reason for change
Add notes if needed
Click Create Request or Process Immediately

Method 2: Direct Creation

Go to Membership > Level Changes
Click Create
Select the membership to change
Choose old and new levels
Set change date and reason

Level Change Process
Draft → Approved → Processed

Draft: Initial request created
Approved: Manager approval received
Processed: Change applied to membership

Automatic Calculations
The system automatically calculates:

Change Type: Upgrade, Downgrade, or Lateral
Price Difference: Cost difference between levels
Proration Amount: Prorated charge/credit based on remaining days
Days Remaining: Time left on current membership

Processing Level Changes
When a level change is processed:

Membership level is updated
Adjustment invoice created (if needed)
Email notification sent to member
Activity logged in membership record


Member Benefits System
Creating Benefits

Navigate to Membership > Member Benefits
Click Create
Configure the benefit:

Basic Information

Benefit Name: e.g., "Free Webinar Access"
Code: Short identifier
Benefit Type: Discount, Access, Service, Product, Event, Other
Description: Detailed explanation

Usage Limits

Usage Limit: Max uses per period (0 = unlimited)
Usage Period: Yearly, Monthly, Per Membership, Lifetime

Financial Tracking

Cost per Use: Organization's cost
Member Price: What members pay (if any)
Non-Member Price: Regular price for comparison

Availability

Available to Levels: Which membership levels get this benefit
Available to Chapters: Chapter restrictions (if applicable)

Tracking Benefit Usage
Recording Usage

Go to Member Benefits > Benefit Usage
Click Create
Select member and benefit
Enter usage count and description
System auto-populates member info

Verification Process

Usage records can be marked as "Verified"
Track who verified and when
Useful for auditing and compliance

Benefit Statistics
View comprehensive statistics:

Total Usage Count: How many times used
Unique Users: Number of different members
Total Cost: Organization's total cost
Usage Trends: Track over time


Common Workflows
New Member Onboarding

Create membership with appropriate level
System auto-sets end date based on level duration
Member receives welcome email (if configured)
Benefits become available immediately

Mid-Year Level Upgrade

Member requests upgrade to Premium
Create level change request
System calculates prorated charge
Approve and process change
Adjustment invoice generated
Member notified of change

Annual Renewal with Level Change

Member wants to downgrade during renewal
Create new membership at lower level
System handles transition smoothly
Credit applied for level difference

Corporate Membership Management

Create Organization-type membership level
Set max members limit
Track individual employees under corporate account
Monitor benefit usage across organization


Reports & Analytics
Membership Level Statistics
Each level shows:

Active Member Count: Current members
Total Revenue: Generated income
Growth Trends: Member acquisition over time

Level Change Analytics
Track patterns:

Most common upgrade paths
Seasonal change trends
Financial impact of changes
Member retention by level

Benefit Usage Reports
Monitor:

Most popular benefits
Usage by membership level
Cost analysis per benefit
Member engagement metrics


Email Templates & Notifications
Automatic Notifications
The system sends emails for:

Level Change Confirmation: Details of change processed
Welcome Messages: For new members (if configured)
Renewal Reminders: Before expiration

Customizing Email Templates

Go to Settings > Technical > Email Templates
Find "Membership Level Change Notification"
Customize subject and content
Use variables like {{ object.partner_id.name }}


Troubleshooting
Common Issues
Level Change Not Processing

Check if membership dates are valid
Verify approval workflow status
Ensure accounting setup is complete

Proration Calculations Wrong

Verify membership start/end dates
Check level price configurations
Review change effective date

Benefits Not Showing

Confirm benefit is active
Check level assignments
Verify member's current level

Email Notifications Not Sending

Check email template configuration
Verify member email addresses
Review server email settings

Data Integrity Checks
Regular maintenance:

Review orphaned level change requests
Verify membership level assignments
Check benefit usage limits
Monitor financial calculations


Best Practices
Level Design

Keep level names clear and descriptive
Use logical pricing progression
Set appropriate benefit differences
Consider member value proposition

Change Management

Establish clear approval processes
Train staff on proration calculations
Monitor change patterns for insights
Communicate changes to members clearly

Benefit Management

Set reasonable usage limits
Track costs accurately
Review benefit popularity regularly
Adjust offerings based on data

Financial Controls

Review proration calculations
Monitor adjustment invoices
Reconcile level change impacts
Maintain audit trails


Advanced Features
API Integration

External system integration possible
Benefit verification endpoints
Usage tracking from other systems
Automated member level changes

Custom Workflows

Additional approval steps
Complex proration rules
Custom notification triggers
Integration with other modules

Reporting Extensions

Custom report development
Dashboard integrations
Automated analytics
Member portal integration

