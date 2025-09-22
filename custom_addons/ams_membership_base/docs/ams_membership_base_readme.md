AMS Membership Base - User Guide
Overview
The AMS Membership Base module is a comprehensive membership management system designed for professional associations like AIAA, ACEP, and similar organizations. This module provides core functionality for managing member records, tracking membership lifecycles, maintaining a member directory, and issuing digital membership cards.
Table of Contents

Getting Started
Membership Management
Member Directory
Digital Membership Cards
Financial Management
Administration & Configuration
Automated Workflows
User Roles & Permissions


Getting Started
Installation Requirements
Before installing, ensure the following Python packages are available:

qrcode - For generating QR codes on membership cards
Pillow - For image processing

Install these packages:
bashpip install qrcode[pil] Pillow
Initial Setup

Install the Module: Go to Apps → Search for "Membership Base" → Install
Access the Module: Navigate to the "Membership" menu in the main Odoo interface
Configure Settings: Go to Membership → Configuration to set up basic parameters

Navigation
The module adds a new "Membership" menu with the following sub-sections:

Memberships - Core membership records
Directory - Member networking directory
Membership Cards - Digital card management
Configuration - System settings


Membership Management
Creating a New Membership

From Membership Menu:

Go to Memberships → All Memberships
Click "Create"
Fill in required information:

Member (select from contacts)
Start Date
End Date
Currency




From Contact Record:

Open any contact record
Go to the "Membership" tab
Click "Add Membership" button
Fill in membership details



Membership Lifecycle
States

Draft: Newly created, not yet active
Active: Current, valid membership
Grace Period: Expired but within grace period (default 30 days)
Lapsed: Expired beyond grace period
Cancelled: Manually cancelled membership

State Transitions

Activate: Draft → Active (manual)
Renew: Any state → Active (manual, extends end date by 1 year)
Cancel: Any state → Cancelled (manual)
Auto-transitions: Active ↔ Grace ↔ Lapsed (automated daily)

Managing Membership Records
Key Fields

Member: The contact this membership belongs to
Start/End Dates: Membership validity period
Paid Through Date: Date through which dues are paid
Days Until Expiry: Calculated field showing time remaining
Status: Current membership state

Financial Tracking
Each membership automatically tracks:

Total Invoiced: Sum of all related invoices
Total Paid: Amount actually received
Balance Due: Outstanding amount owed

Bulk Operations
Filtering & Searching
Use the search bar and filters to find memberships:

By Status: Active, Grace, Lapsed, etc.
By Date: This year, last 30 days, expiring soon
By Payment: Overdue payments
By Member: Search by member name

Views Available

List View: Table format with key information
Kanban View: Card-based view with visual status indicators
Calendar View: Shows membership expiry dates
Form View: Detailed individual record


Member Directory
The member directory enables networking between members while respecting privacy preferences.
Directory Entries
Creating Directory Entries

From Contact Record:

Open a contact with an active membership
Click "Add to Directory" button
Configure privacy and display settings


Direct Creation:

Go to Directory → Member Directory
Click "Create"
Select member and configure settings



Privacy Controls
Each directory entry has granular privacy settings:

Include in Directory: Show in public directory
Allow Contact: Let other members contact this person
Show Email/Phone: Display contact information
Show Company: Display organization
Show Address: Display location

Professional Information
Members can add:

Professional Bio: HTML-formatted biography
Skills/Expertise: Areas of specialization
Industries: Industry experience
Social Links: LinkedIn, website, Twitter

Directory Categories
Purpose
Categories help organize members by:

Professional specialties (e.g., "Software Engineers", "Project Managers")
Industries (e.g., "Healthcare", "Aerospace")
Interests (e.g., "Sustainability", "Innovation")

Managing Categories

Go to Directory → Directory Categories
Create hierarchical category structures
Assign colors for visual organization
Set display order with sequence numbers

Category Features

Hierarchical: Support parent/child relationships
Color Coding: Visual organization
Statistics: Track member counts per category
Active/Inactive: Enable/disable categories

Directory Views
Kanban View (Default)

Card-based layout showing member profiles
Visual status indicators
Quick access to contact options
Profile view counts

List View

Tabular format
Sort by various criteria
Bulk operations support

Search & Filtering

Search by name, skills, industries
Filter by privacy settings, membership status
Group by categories, chapters, or status


Digital Membership Cards
Card Generation
Automatic Generation
When a membership is created, the system automatically generates:

Unique Card Number: Prefix + Year + Member ID + Membership ID
QR Code: Contains verification data
Digital Card URL: Web-accessible card link

Manual Card Issuance

Open a membership record
Go to "Membership Card" tab
Click "Issue New Card"
System generates QR code and sets issue date

Card Features
Information Displayed

Organization name
Member name and ID
Card number
Validity dates
QR code for verification

QR Code Contents
The QR code contains encrypted data including:

Card number
Member name
Expiry date
Membership status
Verification ID

Sending Digital Cards
Email Distribution

Open membership record
Click "Email Card" button
System sends professional email with:

Digital card display
QR code
Usage instructions
Support contact information



Email Templates
Three built-in templates:

Digital Card: Sends the membership card
Welcome New Member: Onboarding email
Renewal Reminder: Expiration notices

Card Verification
Using the Verification Tool

Go to Membership Cards → Verify Card
Enter card number OR QR code data
System validates and shows:

Member name
Membership status
Expiry date
Validity status



Verification Results

✅ Valid Card: Active membership, not expired
❌ Invalid Card: Reasons include:

Card not found
Membership expired
Card suspended/replaced
Invalid format



Card Templates
Template Management

Go to Membership Cards → Card Templates
Create custom templates with:

Color schemes (background, text, accent)
Logo positioning
Feature toggles (QR code, photo)
Usage tracking



Design Options

Background Color: Card background
Text Color: Primary text color
Accent Color: Highlights and borders
Logo Position: Top-left, center, etc.
QR Code: Show/hide QR code
Member Photo: Include photo (future feature)


Financial Management
Invoice Integration
Automatic Linking

Link invoices to specific memberships
Track payment status per membership
Calculate outstanding balances

Financial Dashboard
Each membership shows:

Total Invoiced: All related invoice amounts
Total Paid: Actual payments received
Balance Due: Outstanding amount (red if > 0)

Payment Tracking
Payment Status Indicators

Paid Through Date: Date through which dues are current
Days Until Expiry: Visual countdown with color coding:

Green: > 30 days remaining
Orange: 1-30 days remaining
Red: Expired



Overdue Management

Filter by "Overdue Payment" to find outstanding balances
Automated renewal reminders via email
Grace period management (configurable)

Reporting
Built-in Reports

Membership statistics (active, grace, lapsed counts)
Financial summaries
Expiration reports
Payment status reports

Export Options

Export membership lists to Excel/CSV
Financial data export for accounting
Directory exports for communications


Administration & Configuration
System Parameters
Grace Period Settings

Default: 30 days after expiration
Configuration Path: Settings → Technical → Parameters
Key: membership.grace_period_days

Renewal Notices

Default: 30 days before expiration
Configuration Path: Settings → Technical → Parameters
Key: membership.renewal_notice_days

Card Number Format

Default Prefix: "MC"
Configuration Path: Settings → Technical → Parameters
Key: membership.card_number_prefix
Format: Prefix + Year + Member ID + Membership ID

Email Templates
Customization
All email templates are fully customizable:

Go to Settings → Technical → Email Templates
Search for "membership" templates
Edit HTML content, subject lines, recipients

Available Templates

Digital Membership Card: Card delivery email
Membership Renewal Reminder: Expiration notice
Welcome New Member: Onboarding email

Template Features

Dynamic content (member names, dates, etc.)
Organization branding
Professional styling
Multi-language support ready

Security Groups
Membership User

Read/write access to memberships and directory
Can issue cards and send emails
Cannot delete records or modify configuration

Membership Manager

Full access to all membership functionality
Can delete records and modify settings
Access to configuration and templates
User management capabilities


Automated Workflows
Daily Status Updates
Cron Job: Membership Status Update

Frequency: Daily at midnight
Function: Updates membership states based on expiry dates
Actions:

Active → Grace (if expired within grace period)
Grace → Lapsed (if expired beyond grace period)
Logs changes to membership records



Renewal Notifications
Cron Job: Renewal Notices

Frequency: Daily at 1 AM
Function: Sends renewal reminders
Trigger: 30 days before expiration (configurable)
Actions:

Sends email using renewal template
Logs communication to membership record
Handles email failures gracefully



Statistics Updates
Cron Job: Membership Statistics

Frequency: Weekly
Function: Updates computed fields and statistics
Actions:

Refreshes financial totals
Updates current membership flags
Logs summary statistics to system log



Error Handling
All automated processes include:

Exception Handling: Graceful failure recovery
Logging: Detailed error and success logging
Transaction Safety: Database consistency protection
Manual Override: Admin can run processes manually


User Roles & Permissions
Public Users

Directory Access: Can view public directory entries
Limited Information: Only see information marked as public
No Modification: Read-only access

Membership Users

Full Directory Access: Can view all directory entries they have permission for
Membership Management: Create, edit membership records
Card Operations: Issue cards, send emails, verify cards
Financial Tracking: View payment status, link invoices

Membership Managers

Complete Access: All membership functionality
Configuration: Modify system settings and templates
User Management: Assign roles and permissions
Data Management: Import/export capabilities
System Administration: Access to technical settings

Permission Matrix
FeaturePublicUserManagerView Public Directory✓✓✓View All Directory Entries❌✓✓Create Memberships❌✓✓Issue Cards❌✓✓Send Emails❌✓✓Verify Cards❌✓✓Delete Records❌❌✓Modify Configuration❌❌✓Manage Templates❌❌✓

Best Practices
Data Management

Regular Backups: Ensure membership data is backed up regularly
Data Cleanup: Periodically review and clean old records
Privacy Compliance: Respect member privacy preferences
Contact Updates: Keep member contact information current

Communication

Template Consistency: Maintain professional email templates
Timely Notices: Send renewal reminders with adequate lead time
Support Channels: Provide clear support contact information
Member Education: Help members understand digital card usage

Security

Role Management: Assign appropriate access levels
Regular Audits: Review user permissions periodically
QR Code Security: Monitor card verification logs for unusual activity
Data Protection: Follow organizational data protection policies

Performance

Regular Maintenance: Run cron jobs at off-peak hours
Index Optimization: Monitor database performance
Archive Old Data: Move inactive records to archives
Monitor Logs: Review system logs for issues


Troubleshooting
Common Issues
QR Code Not Generating
Problem: QR codes appear blank or missing
Solution:

Check that qrcode and Pillow packages are installed
Verify card number is generated
Check system logs for errors

Email Templates Not Working
Problem: Emails not sending or formatting incorrectly
Solution:

Verify email server configuration
Check template syntax for errors
Test with simple templates first

Membership Status Not Updating
Problem: Expired memberships stay "Active"
Solution:

Check if cron jobs are running
Verify grace period configuration
Run status update manually from memberships list

Directory Permissions Issues
Problem: Members can't see directory entries
Solution:

Check user group assignments
Verify privacy settings on directory entries
Review record rules configuration

Getting Help
System Logs

Go to Settings → Technical → Logging
Filter by "membership" to find relevant errors
Check cron job execution logs

Support Contacts

Module documentation and updates
Community forums for user questions
Professional support for customizations

Backup and Recovery

Always backup before making configuration changes
Test new features in a development environment
Have a rollback plan for major updates