Membership Chapter Module - User Guide
Overview
The Membership Chapter module enables professional associations to organize members into regional chapters or special interest groups. This module provides comprehensive chapter management including meetings, financial tracking, and member organization.
Key Features:

Create hierarchical chapter structures (regional, special interest groups)
Schedule and manage chapter meetings with RSVP system
Track chapter finances with budgets and transactions
Assign members to chapters with roles
Email notifications and automated reminders


Getting Started
Installation & Setup

Install the Module

Go to Apps menu
Search for "Membership Chapter"
Click Install


Initial Configuration

Navigate to Membership > Chapters
The module is ready to use immediately



User Permissions
The module uses two permission levels:

Membership User: Can view chapters, create meetings, submit expenses
Membership Manager: Full access to create/edit chapters, approve budgets, manage finances


Chapter Management
Creating Your First Chapter

Navigate to Chapters

Go to Membership > Chapters
Click Create


Basic Information

Chapter Name: e.g., "Southern California Chapter"
Code: Short identifier (e.g., "SOCAL")
Chapter Type: Choose from:

Regional (geographic-based)
Special Interest (topic-based)
Professional (career-focused)
Student (student groups)
Other




Location & Contact

Fill in address information
Add contact email and phone
Set website if available


Management Structure

Chapter Manager: Select the primary leader/president
Officers: Add board members and key volunteers



Chapter Hierarchy
Creating Sub-Chapters:

When creating a chapter, select a Parent Chapter
This creates hierarchical relationships like:

California Chapter

Northern California Chapter
Southern California Chapter





Benefits of Hierarchy:

Consolidated member counts roll up to parent chapters
Simplified reporting and management
Clear organizational structure

Managing Chapter Members
Assign Members to Chapters:
Method 1: From Member Record

Open a member's contact record
Go to the Membership tab
Set Chapter field
Choose Chapter Role (Member, Officer, Manager/President)

Method 2: From Chapter Record

Open chapter record
Go to Members tab
Add members directly

Chapter Roles:

Member: Standard chapter member
Officer: Board member or committee chair
Manager/President: Chapter leader with full permissions


Meeting Management
Scheduling Meetings

Create Meeting

From Chapter record: Click Schedule Meeting
Or go to Membership > Chapter Meetings > Create


Meeting Details

Meeting Title: e.g., "Monthly Board Meeting"
Chapter: Select organizing chapter
Meeting Type: Board, General, Special, etc.
Date & Time: Set meeting date/time
Duration: Expected length in hours


Location Setup

Physical Meeting: Enter location and address
Virtual Meeting: Check box and add meeting URL/access code


Meeting Content

Agenda: Add meeting agenda (HTML formatting supported)
Materials: Upload presentations or documents



Managing Attendees
Invite Members:

In meeting record, go to Attendees tab
Click Invite All Chapter Members for automatic invitation
Or manually select Invited Members

RSVP System:

Members receive email invitations with RSVP links
Track responses: Yes, No, Maybe, Pending
View RSVP summary in meeting statistics

Meeting Workflow

Draft: Create and prepare meeting details
Published: Send invitations to members

Click Publish & Send Invites
Email invitations sent automatically


Confirmed: Finalize meeting arrangements
Completed: Record attendance and minutes
Cancelled: Cancel if needed (sends cancellation notices)

Post-Meeting Activities
Record Meeting Results:

Mark meeting as Completed
Minutes & Actions tab becomes available
Add Meeting Minutes (HTML formatted)
Record Action Items for follow-up
Set Next Meeting Date if scheduled

Track Attendance:

Add actual Attendees from invited list
System calculates attendance statistics
View attendance trends in chapter statistics


Financial Management
Budget Creation

Create Chapter Budget

From Chapter record: Click Create Budget
Or go to Membership > Chapter Finance > Budgets


Budget Setup

Fiscal Year: e.g., "2024" or "2024-2025"
Start/End Dates: Define budget period
Chapter: Select owning chapter


Income Planning

Go to Income Budget tab
Add line items:

Membership Dues
Event Revenue
Sponsorship
Donations
Grants




Expense Planning

Go to Expense Budget tab
Add line items:

Venue Costs
Catering
Speakers/Presenters
Marketing
Supplies
Travel
Administration





Budget Approval Process

Draft: Create and edit budget
Approved: Manager approves budget

Click Approve button


Active: Budget becomes operational

Click Activate button


Closed: End of fiscal period

Transaction Management
Recording Chapter Expenses:

Go to Membership > Chapter Finance > Transactions
Click Create
Fill in details:

Description: What was purchased/paid
Chapter: Owning chapter
Amount: Transaction amount
Category: Select appropriate category
Payment Method: How it was paid
Receipt: Upload supporting documents



Transaction Approval:

Draft: Enter transaction details
Submitted: Click Submit for Approval
Approved/Rejected: Manager reviews and decides

Link Transactions to Meetings:

In transaction record, select Related Meeting
Helps track meeting-specific costs

Financial Reporting
Budget Variance Analysis:

Compare budgeted vs actual amounts
View variance by category
Track budget performance over time

Chapter Financial Summary:

Current year income/expenses
Budget vs actual performance
Transaction history


Email Communications
Automatic Notifications
Meeting Invitations:

Sent when meeting is published
Includes meeting details, agenda, RSVP links
Professional HTML formatting

Meeting Reminders:

Sent 24 hours before meeting (configurable)
Automatic via scheduled job
Reminds about meeting details

Cancellation Notices:

Sent when meetings are cancelled
Informs about cancellation and next meeting

Customizing Email Templates

Go to Settings > Technical > Email Templates
Find chapter-related templates:

Chapter Meeting Invitation
Chapter Meeting Reminder
Chapter Meeting Cancellation


Customize subject lines and content
Use variables like {{ object.name }} for dynamic content


Best Practices
Chapter Organization
For Regional Chapters:

Use geographic hierarchy (State > Metro Area > Local)
Set clear boundaries to avoid overlap
Consider member density and travel distances

For Special Interest Groups:

Focus on professional specialties or interests
Allow members to join multiple special interest chapters
Create focused meeting content

Meeting Management
Effective Meetings:

Send invitations 1-2 weeks in advance
Include detailed agendas
For virtual meetings, test technology beforehand
Follow up with action items and minutes

Engagement Tips:

Rotate meeting locations for regional chapters
Include networking time
Feature guest speakers
Provide continuing education credits when applicable

Financial Management
Budget Planning:

Plan budgets annually
Include all expected income sources
Account for meeting costs, venue rentals, catering
Set aside funds for special events

Expense Tracking:

Require receipts for all expenses
Set approval limits (e.g., $500+ requires approval)
Review budgets quarterly
Track costs by meeting/event


Common Workflows
New Chapter Setup

Create chapter with basic information
Assign chapter manager and officers
Set up initial budget
Import or assign members
Schedule first meeting
Send welcome communications

Monthly Meeting Cycle

Week 3 of Previous Month: Schedule next month's meeting
Week 1: Finalize agenda, publish meeting
Day Before: System sends automatic reminders
Meeting Day: Record attendance
Within 1 Week: Publish minutes and action items

Annual Budget Process

Q4: Begin budget planning for next year
Year-End: Create new budget record
January: Get budget approvals
Quarterly: Review budget performance
Year-End: Close budget and analyze results


Troubleshooting
Common Issues
Members Not Receiving Meeting Invitations:

Check member email addresses are valid
Verify email template is active
Check spam/junk folders
Ensure meeting is in "Published" status

RSVP Links Not Working:

Email templates may need adjustment
Check system base URL configuration
Verify RSVP records are created properly

Budget Totals Not Calculating:

Check if transactions are in "Approved" status
Verify transaction categories match budget line categories
Refresh browser or check computed field updates

Permission Issues:

Verify user has proper membership permissions
Check if user is assigned to correct security groups
Contact system administrator for access rights

Getting Help
System Administration:

Check system logs for error details
Review email queue for delivery issues
Verify cron jobs are running properly

User Support:

Provide training on meeting workflow
Create chapter-specific procedures
Document local customizations


Advanced Features
Integration with Other Modules
With Membership Levels:

Different member levels can have chapter access
Level-based meeting pricing (if events module added)
Officer roles may require certain membership levels

With Communications Module:

Targeted emails to chapter members
Newsletter campaigns by chapter
Event announcements

Customization Options
Email Templates:

Customize invitation designs
Add organization branding
Include chapter-specific content

Categories:

Add custom transaction categories
Create organization-specific meeting types
Customize budget line item categories

Workflows:

Modify approval processes
Add custom meeting statuses
Create automated notifications