# AMS Foundation Module - User Guide

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Member Types Management](#member-types-management)
4. [Member Management](#member-management)
5. [System Settings](#system-settings)
6. [Portal User Management](#portal-user-management)
7. [Engagement Rules](#engagement-rules)
8. [Common Workflows](#common-workflows)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The AMS Foundation module provides the core functionality for managing association members, including:

- **Member Data Management**: Complete member profiles with professional information
- **Member Types**: Configurable membership categories with different benefits and pricing
- **Automated Status Management**: Automatic transitions between member statuses based on dates
- **Portal Access**: Self-service member portal with automatic user creation
- **Engagement Scoring**: Framework for tracking member engagement activities
- **Comprehensive Settings**: Global configuration for all AMS operations

---

## Getting Started

### Initial Setup

1. **Install the Module**
   - Go to Apps menu
   - Search for "AMS Foundation"
   - Click Install

2. **Configure Basic Settings**
   - Navigate to `Association Management > Configuration > AMS Settings`
   - Review and update default settings
   - Set member number prefix and format
   - Configure grace periods and status transitions

3. **Set Up Member Types**
   - Go to `Association Management > Configuration > Member Types`
   - Create your membership categories (Regular, Student, Corporate, etc.)
   - Configure pricing, benefits, and eligibility requirements

4. **Configure Security**
   - Assign users to appropriate AMS groups:
     - **AMS: Administrator** - Full system access
     - **AMS: Manager** - Management functions
     - **AMS: Staff** - Day-to-day operations
     - **AMS: Member** - Portal access only

---

## Member Types Management

### Creating Member Types

1. Navigate to `Association Management > Configuration > Member Types`
2. Click **Create**
3. Fill in basic information:
   - **Name**: Full member type name
   - **Code**: Short identifier (e.g., REG, STU, CORP)
   - **Description**: Detailed description
   - **Base Annual Fee**: Standard membership fee

### Configuring Member Type Features

#### Basic Settings
- **Sequence**: Order for display
- **Active**: Enable/disable the member type
- **Membership Duration**: Days the membership is valid (default: 365)

#### Membership Features
- **Requires Approval**: Manual approval needed for applications
- **Auto Renewal**: Members can set up automatic renewal
- **Voting Rights**: Can participate in elections
- **Directory Access**: Can view member directory
- **Event Discounts**: Eligible for member pricing on events

#### Eligibility Requirements
- **Requires License**: Professional license needed
- **Minimum Experience**: Years of experience required
- **Education Requirements**: Educational prerequisites
- **Age Restrictions**: Age-based limitations

#### Advanced Configuration

**Geographic Restrictions**
- Enable to limit by country/state
- Select allowed countries and states
- Useful for regional memberships

**Member Limits**
- Set maximum number of members
- Enable waiting list when limit reached
- Useful for exclusive membership types

**Application Process** (when approval required)
- **Application Fee**: One-time application cost
- **Reference Letters**: Number of references needed
- **Interview Required**: Face-to-face interview needed

### Best Practices

- Use clear, descriptive names for member types
- Keep codes short but meaningful (3-4 characters)
- Set realistic eligibility requirements
- Review and update pricing annually
- Use sequences to order types logically

---

## Member Management

### Adding New Members

#### Individual Members
1. Go to `Association Management > Members > Member Directory`
2. Click **Create**
3. Fill in basic contact information
4. Check **Is Association Member**
5. Select **Member Type**
6. Set **Membership Start Date**
7. Fill in professional information as needed
8. Save

#### Bulk Import
- Use Odoo's import feature with prepared CSV files
- Include all required fields
- Set `is_member = True` for all records
- Assign appropriate member types

### Member Status Management

#### Status Workflow
Members progress through these statuses:

1. **Prospective** → New member, not yet activated
2. **Active** → Full member with all benefits
3. **Grace Period** → Expired but within grace period
4. **Lapsed** → Grace period expired
5. **Suspended** → Temporarily suspended
6. **Terminated** → Permanently terminated

#### Manual Status Changes
Use the action buttons on member records:
- **Activate**: Move prospective to active
- **Suspend**: Temporarily suspend member
- **Terminate**: Permanently terminate membership
- **Reinstate**: Restore suspended/terminated member

#### Automatic Status Transitions
The system automatically processes status changes daily:
- Active members become Grace when membership expires
- Grace members become Lapsed when grace period ends
- Suspended members become Lapsed when suspension period ends

### Member Information Management

#### Professional Information
- **Professional Designation**: Certifications, titles
- **License Number**: Professional license
- **Specialty Area**: Area of expertise
- **Years Experience**: Professional experience
- **Employer/Job Title**: Current employment

#### Communication Preferences
- **Communication Preference**: Email, mail, both, or minimal
- **Newsletter Subscription**: Opt in/out of newsletters
- **Directory Listing**: Include in member directory
- **Preferred Language**: For communications

#### Engagement Tracking
- **Engagement Score**: Automatically calculated
- **Portal Login Stats**: Last login, login count
- **Membership Notes**: Internal notes about the member

---

## System Settings

### Accessing Settings
Navigate to `Association Management > Configuration > AMS Settings`

### Core Configuration

#### Member Numbering
- **Prefix**: Characters before number (e.g., "M")
- **Padding**: Total length including prefix (e.g., 6 = M00001)
- **Next Number**: Shows next number to be assigned

#### Status Management
- **Auto Status Transitions**: Enable automatic status changes
- **Grace Period Days**: Days after expiration before lapsed (default: 30)
- **Suspend Period Days**: Days a member can remain suspended (default: 60)
- **Terminate Period Days**: Days before final termination (default: 90)

#### Portal Settings
- **Auto Create Portal Users**: Automatically create portal access
- **Welcome Email Enabled**: Send welcome emails to new members
- **Default Communication Preference**: Default for new members
- **Default Newsletter Subscription**: Auto-subscribe new members
- **Default Directory Listing**: Include new members in directory

#### Communication Settings
- **Renewal Reminder Enabled**: Send automated renewal reminders
- **Renewal Reminder Days**: Days before expiration to send reminder (default: 30)
- **Expiration Warning Days**: Days before expiration for final warning (default: 7)

#### Engagement Scoring
- **Engagement Scoring Enabled**: Enable the scoring system
- **Default Engagement Score**: Starting score for new members
- **Recalc Frequency**: How often to recalculate scores

### Advanced Settings

#### Data Management
- **Data Retention Years**: How long to keep member data after termination
- **Auto Cleanup Enabled**: Automatically remove old data

#### Integration
- **API Enabled**: Enable REST API access
- **Webhook Enabled**: Enable outbound webhooks

### Best Practices

- Only have one active settings record
- Test changes in a staging environment first
- Document any custom settings
- Review settings quarterly
- Back up settings before major changes

---

## Portal User Management

### Automatic Portal User Creation

The system can automatically create portal users for members:

1. **Enable in Settings**: Turn on "Auto Create Portal Users"
2. **Email Required**: Members must have valid email addresses
3. **Automatic Groups**: Users get Member and Portal access
4. **Welcome Emails**: Invitation emails sent automatically

### Manual Portal User Creation

#### Individual Members
1. Open member record
2. Go to **Membership** tab
3. Click **Create Portal User** button
4. System creates user and sends invitation email

#### Bulk Creation
1. Go to `Association Management > Tools > Create Portal Users`
2. Set selection criteria:
   - Member types
   - Member status
   - Date ranges
   - Email requirements
3. Preview eligible members
4. Click **Create Portal Users**
5. Review results and download log

### Managing Existing Portal Users

#### Reset Passwords
1. Open member record
2. Go to **Membership** tab
3. Click **Reset Portal Password**
4. New invitation email sent

#### Update User Groups
Use the bulk wizard to ensure all portal users have correct groups

#### Deactivate Portal Access
1. Go to `Association Management > Tools > Portal User Management`
2. Find the user
3. Uncheck **Active** or remove from Portal group

### Troubleshooting Portal Issues

**Member Can't Login**
- Verify email address is correct
- Check if portal user exists
- Ensure user is active
- Verify user has Portal and Member groups

**Email Not Received**
- Check spam folders
- Verify email server configuration
- Check member's email preferences
- Manually reset password

---

## Engagement Rules

### Overview
Engagement rules define how member activities are scored and tracked. This creates a comprehensive system for measuring member engagement.

### Rule Types

#### Event Participation
- **Event Attendance**: Points for attending events
- **Event Speaking**: Points for speaking at events  
- **Event Organizing**: Points for organizing events

#### Portal Activity
- **Portal Login**: Points for logging into member portal
- **Profile Update**: Points for updating member profile
- **Document Access**: Points for accessing member resources

#### Communication Engagement
- **Email Engagement**: Points for opening/clicking emails
- **Newsletter Engagement**: Points for newsletter interaction
- **Survey Participation**: Points for completing surveys

#### Professional Development
- **Continuing Education**: Points for CE activities
- **Certification Earned**: Points for earning certifications

#### Association Involvement
- **Committee Participation**: Points for committee involvement
- **Volunteer Activity**: Points for volunteer work
- **Member Referral**: Points for referring new members

### Creating Engagement Rules

1. Go to `Association Management > Configuration > Engagement Rules`
2. Click **Create**
3. Configure rule settings:
   - **Name** and **Rule Type**
   - **Points Value**: Base points awarded
   - **Sequence**: Order of rule evaluation

#### Frequency Limits
- Enable to prevent point farming
- Set time period (daily, weekly, monthly, yearly)
- Set maximum points per period
- Choose reset frequency

#### Conditions
- **Member Types**: Which member types eligible
- **Minimum Membership Duration**: Days as member required
- **Date Range**: When rule is active
- **Requires Approval**: Manual approval needed

#### Advanced Configuration
- **Custom Formulas**: Python code for complex calculations
- **External Integration**: API endpoints for data sync
- **Webhook Triggers**: Notify external systems

### Best Practices

- Start with simple, clear rules
- Set reasonable point values
- Use frequency limits to prevent abuse
- Test rules thoroughly before activation
- Review and adjust rules regularly
- Document rule purposes and calculations

---

## Common Workflows

### New Member Onboarding

1. **Member Application**
   - Receive application (online or paper)
   - Create member record with status "Prospective"
   - Assign appropriate member type

2. **Approval Process** (if required)
   - Review eligibility requirements
   - Check references and documentation
   - Use approval workflow if configured

3. **Member Activation**
   - Change status to "Active"
   - Set membership start/end dates
   - Portal user automatically created
   - Welcome email sent

4. **Follow-up**
   - Verify portal access works
   - Send orientation materials
   - Add to relevant committees/chapters

### Membership Renewal Process

1. **Renewal Reminders** (Automated)
   - System sends reminder 30 days before expiration
   - Follow-up reminders at configured intervals
   - Final warning 7 days before expiration

2. **Member Renewal**
   - Member renews through portal or staff processes
   - Payment processed
   - Membership end date extended
   - Status remains "Active"

3. **Non-Renewal Processing** (Automated)
   - Status changes to "Grace" on expiration date
   - Grace period reminders sent
   - Status changes to "Lapsed" after grace period

### Member Status Management

#### Suspension Process
1. **Initiate Suspension**
   - Review reason for suspension
   - Document in member record
   - Change status to "Suspended"

2. **During Suspension**
   - Portal access may be restricted
   - Benefits suspended
   - Regular review of suspension

3. **Resolution**
   - **Reinstate**: Change status back to "Active"
   - **Terminate**: Change status to "Terminated"
   - **Auto-lapse**: System changes to "Lapsed" after suspension period

#### Termination Process
1. **Termination Decision**
   - Document reason thoroughly
   - Follow association bylaws/policies
   - Change status to "Terminated"

2. **Post-Termination**
   - Portal access removed
   - Benefits terminated
   - Data retained per retention policy

### Data Management

#### Regular Maintenance
- **Weekly**: Review new members and applications
- **Monthly**: Check engagement scores and portal usage
- **Quarterly**: Review member types and pricing
- **Annually**: Audit member data and clean up old records

#### Data Quality
- **Duplicate Detection**: Regular checks for duplicate members
- **Email Validation**: Verify email addresses are valid
- **Address Updates**: Keep contact information current
- **Professional Info**: Update professional designations and licenses

---

## Troubleshooting

### Common Issues

#### Member Numbers Not Generating
**Symptoms**: New members don't get member numbers
**Solutions**:
- Check if sequence exists: `Association Management > Configuration > AMS Settings`
- Click "Update Sequence" button
- Verify settings have correct prefix and padding

#### Portal Users Not Created Automatically
**Symptoms**: New members don't get portal access
**Solutions**:
- Check "Auto Create Portal Users" in AMS Settings
- Verify member has valid email address
- Check if email is already used by another user
- Review system logs for errors

#### Status Transitions Not Working
**Symptoms**: Members don't automatically move to grace/lapsed status
**Solutions**:
- Verify "Auto Status Transitions" is enabled in settings
- Check cron jobs are running: `Settings > Technical > Automation > Scheduled Actions`
- Review member dates (start/end dates must be set)
- Check grace period configuration

#### Engagement Scores Not Updating
**Symptoms**: Member engagement scores stay at zero
**Solutions**:
- Enable "Engagement Scoring" in AMS Settings
- Verify engagement rules are active
- Check rule conditions are met
- Review rule application logs

#### Email Invitations Not Sent
**Symptoms**: Portal users created but no email received
**Solutions**:
- Check outgoing email server configuration
- Verify member email address is correct
- Check email templates exist and are configured
- Review email server logs

### Performance Issues

#### Slow Member Directory
**Symptoms**: Member directory loads slowly
**Solutions**:
- Add database indexes if needed
- Limit search results
- Use filters to narrow results
- Consider archiving old members

#### Long Processing Times
**Symptoms**: Bulk operations take too long
**Solutions**:
- Process in smaller batches
- Run during off-peak hours
- Check database performance
- Consider background processing

### Data Issues

#### Duplicate Members
**Detection**: Search for members with same email or name
**Prevention**: 
- Use import validation
- Train staff on proper data entry
- Regular duplicate detection reports

**Resolution**:
- Merge duplicate records carefully
- Update related records (payments, activities)
- Consider data deduplication tools

#### Inconsistent Data
**Common Issues**:
- Members without member types
- Invalid email formats
- Missing required information
- Incorrect status transitions

**Solutions**:
- Regular data quality reports
- Validation rules on data entry
- Staff training on data standards
- Automated data cleanup procedures

### Getting Help

#### Documentation
- User guides and technical documentation
- Video tutorials (if available)
- System help pages

#### Support Channels
- Internal IT support
- Vendor support (if applicable)
- User community forums
- Professional services

#### Escalation Process
1. Check documentation and troubleshooting guides
2. Contact internal support team
3. Gather system information and error logs
4. Contact vendor support if needed
5. Consider professional services for complex issues

---

## Appendices

### Appendix A: Default Member Types

The system includes these default member types:

| Type | Code | Description | Annual Fee |
|------|------|-------------|------------|
| Regular Member | REG | Full professional membership | $250.00 |
| Student Member | STU | Discounted for students | $50.00 |
| Associate Member | ASC | Entry-level membership | $150.00 |
| Retired Member | RET | Reduced rate for retirees | $75.00 |
| Corporate Member | CORP | Organizational membership | $1,500.00 |
| International Member | INTL | Outside primary region | $200.00 |
| Honorary Member | HON | Complimentary recognition | $0.00 |

### Appendix B: Status Transition Rules

| From Status | To Status | Trigger | Days |
|-------------|-----------|---------|------|
| Prospective | Active | Manual activation | - |
| Active | Grace | Membership expiration | 0 |
| Grace | Lapsed | Grace period end | 30 |
| Active/Grace | Suspended | Manual suspension | - |
| Suspended | Lapsed | Suspension period end | 60 |
| Any | Terminated | Manual termination | - |
| Suspended/Terminated | Active | Manual reinstatement | - |

### Appendix C: Default Engagement Rules

Common engagement rules you might configure:

| Activity | Points | Frequency Limit |
|----------|--------|-----------------|
| Portal Login | 1 | 1 per day |
| Profile Update | 5 | 1 per month |
| Event Attendance | 10 | No limit |
| Email Click | 0.5 | 5 per day |
| Survey Completion | 15 | No limit |
| Early Renewal | 25 | 1 per year |
| Member Referral | 50 | No limit |

### Appendix D: Security Groups

| Group | Description | Permissions |
|-------|-------------|-------------|
| AMS: Member | Basic member access | View own data only |
| AMS: Staff | Staff operations | View/edit member data |
| AMS: Manager | Management functions | Full member management |
| AMS: Administrator | System administration | All functions + configuration |

---

*This user guide covers AMS Foundation Module v18.0.1.0.0. For the latest updates and additional modules, please refer to the complete AMS documentation.*