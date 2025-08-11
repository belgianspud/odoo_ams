# AMS Revenue Recognition - Complete User Guide

## 🎯 What This Guide Covers

This step-by-step guide will walk you through setting up and managing revenue recognition for your Association Management System (AMS). By the end, you'll be able to:

- Understand ASC 606/IFRS 15 compliant revenue recognition
- Configure products for proper revenue recognition
- Monitor and process deferred revenue schedules
- Generate revenue recognition reports
- Handle subscription lifecycle revenue changes

---

## 📋 Before You Start

**Prerequisites:**
- AMS Base Accounting module is installed and configured
- AMS Subscriptions module is installed and configured
- You have AMS Revenue Recognition Manager permissions
- Your subscription products are properly set up with AMS accounting

**What You'll Need:**
- Understanding of your revenue recognition requirements
- Knowledge of your subscription billing cycles
- Access to your chart of accounts configuration

---

## Step 1: Verify Foundation Setup

**Why:** Revenue recognition builds on your existing AMS accounting setup.

### 🔧 Check Your Foundation:

1. **Go to:** AMS → Accounting → Chart of Accounts
2. **Verify these accounts exist:**
   - **Revenue Accounts** (4100, 4110, 4200, etc.)
   - **Deferred Revenue Account** (2300 - Deferred Membership Revenue)
   - **Accounts Receivable** (1200 - A/R Memberships)

3. **Go to:** AMS → Products → All AMS Products
4. **Verify your subscription products have:**
   - ✅ **AMS Accounting** enabled
   - ✅ **Revenue Account** assigned
   - ✅ **Deferred Revenue Account** assigned (for annual subscriptions)

**✅ Result:** Your foundation is ready for revenue recognition.

---

## Step 2: Configure Revenue Recognition for Products

**Why:** Each product needs to know HOW revenue should be recognized.

### 💳 Configure Individual Membership Product

1. **Go to:** AMS → Products → All AMS Products
2. **Select:** Your individual membership product
3. **Click:** Revenue Recognition tab

**Configure Recognition Method:**
- **Recognition Method:** Deferred (computed automatically)
- **Recognition Period:** Monthly (for annual subscriptions)
- ✅ **Auto-Create Recognition Schedules:** Checked
- ✅ **Auto-Process Recognition:** Checked

4. **Review Recognition Rules:**
   - **Annual Subscriptions** → Deferred and recognized monthly
   - **Monthly Subscriptions** → Immediate recognition
   - **Quarterly Subscriptions** → Deferred and recognized monthly

5. **Click:** Save

### 🏢 Configure Enterprise Membership Product

1. **Same process, but verify:**
   - **Recognition Method:** Deferred
   - **Recognition Period:** Monthly
   - **Auto-Processing:** Enabled

### 📚 Configure Publication Products

1. **For Digital Publications:**
   - **Recognition Method:** Immediate (typically)
   - **Auto-Processing:** Enabled

**✅ Result:** Products are configured for proper revenue recognition.

---

## Step 3: Understanding the Revenue Recognition Workflow

**Why:** Know how the system works so you can monitor and troubleshoot.

### 🔄 The Automated Process

```
1. Customer Pays Invoice (Annual Membership)
   ↓
2. System Creates Revenue Recognition Schedule
   ↓  
3. Recognition Lines Generated (12 monthly periods)
   ↓
4. Daily Cron Job Processes Due Recognition
   ↓
5. Journal Entries: Deferred Revenue → Revenue Account
   ↓
6. Dashboard Shows Progress
```

### 📊 Recognition Methods Explained

**Immediate Recognition (Monthly Subscriptions):**
```
Payment Received → Revenue Account (same day)
```

**Deferred Recognition (Annual Subscriptions):**
```
Payment Received → Deferred Revenue Account
Monthly Processing → Revenue Account (1/12 each month)
```

**✅ Result:** You understand how revenue flows through the system.

---

## Step 4: Monitor Revenue Recognition

**Why:** Stay on top of your deferred revenue and recognition processing.

### 📈 Daily Monitoring

1. **Go to:** AMS → Accounting → Recognition Dashboard
2. **Review Key Metrics:**
   - **Recognition Due Today:** Entries ready to process
   - **Total Deferred Revenue:** Outstanding unrecognized revenue
   - **Recognition Status:** Active vs completed schedules

### 📋 Review Active Schedules

1. **Go to:** AMS → Accounting → Revenue Schedules
2. **Use Kanban View to see:**
   - **Draft:** New schedules waiting activation
   - **Active:** Schedules currently processing
   - **Completed:** Fully recognized schedules

3. **Focus on Active Schedules:**
   - Check next recognition dates
   - Monitor recognition progress
   - Review any processing errors

### 🔍 Check Due Recognition Entries

1. **Go to:** AMS → Accounting → Recognition Due
2. **Process Due Entries:**
   - Review entries due today
   - Click "Recognize Revenue" for manual processing
   - Monitor automated processing results

**✅ Result:** You're actively monitoring revenue recognition health.

---

## Step 5: Process Revenue Recognition

**Why:** Ensure revenue is recognized on schedule for accurate financials.

### ⚡ Automated Processing (Default)

**Daily Cron Job Automatically:**
1. Finds recognition entries due today
2. Creates journal entries (Deferred → Revenue)
3. Updates recognition status
4. Logs processing results

**Monitor Automation:**
- Check AMS → Accounting → Recognition Entries
- Filter by "Recognized" to see processed entries
- Review any "Pending" entries that should be processed

### ✋ Manual Processing (When Needed)

**Process Individual Entry:**
1. **Go to:** AMS → Accounting → Recognition Entries
2. **Filter:** Pending entries
3. **Select entry** and click **"Recognize Revenue"**
4. **Verify** journal entry was created

**Bulk Process Due Recognition:**
1. **Go to:** AMS → Accounting → Recognition Due
2. **Select multiple entries**
3. **Actions** → **"Process Due Recognitions"**

**Process Schedule:**
1. **Go to:** Revenue schedule record
2. **Click:** "Process Due Recognition" button
3. **Review** results in recognition lines

**✅ Result:** Revenue is being recognized according to schedule.

---

## Step 6: Handle Common Scenarios

### 🆕 New Annual Membership Sale

**What Happens Automatically:**
1. Customer purchases $1,200 annual membership
2. Invoice posted and paid
3. **Journal Entry:** Cash $1,200 / Deferred Revenue $1,200
4. **Recognition Schedule Created:** 12 monthly periods of $100 each
5. **Monthly Processing:** Deferred Revenue $100 / Revenue $100

**What You Should Monitor:**
- Schedule appears in "Active" status
- First recognition entry created for current month
- Next recognition date set for next month

### 💳 Monthly Membership Sale

**What Happens Automatically:**
1. Customer purchases $25 monthly membership
2. Invoice posted and paid
3. **Journal Entry:** Cash $25 / Revenue $25 (immediate)
4. **No Schedule Created** (immediate recognition)

### 🔄 Mid-Year Membership Change

**Example:** Customer upgrades from $1,200 to $1,800 annual membership mid-year

**What Happens:**
1. System calculates remaining period (6 months left)
2. **Proration Invoice:** $300 additional (($1,800-$1,200) × 6/12)
3. **New Recognition Schedule:** For additional $300 over remaining 6 months
4. **Original Schedule:** Continues as planned

**Your Action:** Monitor both schedules are processing correctly

### 📅 Year-End Processing

**What to Check:**
1. **Deferred Revenue Balance:** Should match active schedules
2. **Completed Schedules:** Annual memberships ending should be "Completed"
3. **New Renewals:** Should create new schedules for next year

**✅ Result:** You can handle any revenue recognition scenario.

---

## Step 7: Generate Reports and Analysis

### 📊 Standard Reports

**Monthly Revenue Recognition Report:**
1. **Go to:** AMS → Accounting → Reports → Monthly Revenue Recognition
2. **Select Date Range**
3. **Review:** Recognized revenue by month and product
4. **Export:** For financial reporting

**Deferred Revenue Report:**
1. **Go to:** AMS → Accounting → Reports → Deferred Revenue Report
2. **Review:** Outstanding deferred revenue by product and customer
3. **Use for:** Balance sheet reporting

### 📈 Dashboard Analysis

**Revenue Recognition Dashboard:**
1. **Go to:** AMS → Accounting → Recognition Dashboard
2. **Use Pivot Tables:** Group by product, customer, or month
3. **Create Graphs:** Track recognition trends
4. **Filter Data:** Focus on specific products or time periods

### 💰 Financial Integration

**Chart of Accounts View:**
1. **Go to:** AMS → Accounting → Chart of Accounts
2. **Check Account Balances:**
   - **Deferred Revenue Account:** Should decrease as revenue is recognized
   - **Revenue Accounts:** Should increase with recognition
3. **Drill Down:** Click account to see transactions

**✅ Result:** You have comprehensive reporting and analysis tools.

---

## Step 8: Troubleshooting Guide

### ❓ Revenue Recognition Schedule Not Created

**Check:**
1. Product has "Auto-Create Recognition" enabled
2. Product has valid deferred revenue account
3. Invoice is posted and paid
4. Product recognition method is not "immediate"

**Solution:**
1. Edit product → Revenue Recognition tab
2. Enable auto-create recognition
3. Manually create schedule if needed

### ❓ Recognition Not Processing Automatically

**Check:**
1. Schedule is in "Active" status (not "Draft")
2. Recognition entry is due today or earlier
3. Cron job is running (ask system admin)
4. No errors in recognition entry

**Solution:**
1. Activate draft schedules manually
2. Process due recognition manually
3. Check system logs for cron job errors

### ❓ Wrong Recognition Amount

**Check:**
1. Product price matches schedule total amount
2. Recognition periods are calculated correctly
3. No proration adjustments needed

**Solution:**
1. Review schedule settings
2. Check for mid-cycle changes
3. Adjust recognition entry if needed

### ❓ Deferred Revenue Balance Doesn't Match

**Check:**
1. All schedules are properly activated
2. Recognition entries are processing correctly
3. No manual journal entries affecting accounts

**Solution:**
1. Run deferred revenue report
2. Compare to active schedules total
3. Investigate discrepancies

**✅ Result:** You can diagnose and resolve common issues.

---

## 🎊 Congratulations!

You've successfully set up and learned to manage AMS revenue recognition! Your association can now:

- ✅ Automatically recognize subscription revenue per ASC 606/IFRS 15
- ✅ Handle both immediate and deferred recognition scenarios  
- ✅ Monitor revenue recognition health with dashboards
- ✅ Generate compliance reports for financial statements
- ✅ Process recognition entries automatically or manually
- ✅ Handle subscription changes and proration correctly

### 🚀 Next Steps

1. **Train your team** on monitoring recognition dashboards
2. **Set up email alerts** for recognition processing issues (if available)
3. **Integrate with financial reporting** for month-end close
4. **Consider ams_subscription_billing** for automated invoice generation
5. **Review monthly** to ensure recognition is accurate

### 📞 Need Help?

- **Recognition Dashboard:** Quick overview of all recognition activity
- **Due Recognition View:** Process pending entries
- **Schedule Kanban:** Visual status of all schedules
- **Revenue Reports:** Detailed analysis and exports

### 💡 Pro Tips

1. **Monitor Daily:** Check recognition due entries each morning
2. **Month-End:** Run deferred revenue report for accounting
3. **Year-End:** Review completed schedules for audit trail
4. **Troubleshooting:** Start with product configuration, then schedule status
5. **Reporting:** Use pivot tables to analyze trends and patterns

**Your AMS system now provides professional-grade revenue recognition that meets accounting standards and automates complex subscription revenue scenarios!** 🎉

---

## 📚 Quick Reference

### Menu Locations
- **Dashboard:** AMS → Accounting → Recognition Dashboard
- **Schedules:** AMS → Accounting → Revenue Schedules  
- **Entries:** AMS → Accounting → Recognition Entries
- **Due Processing:** AMS → Accounting → Recognition Due
- **Product Config:** AMS → Products → [Product] → Revenue Recognition tab

### Recognition Methods
| Product Type | Billing Period | Recognition Method | Journal Entry |
|--------------|----------------|-------------------|---------------|
| Individual Annual | Annual | Deferred | Monthly: DR Deferred, CR Revenue |
| Individual Monthly | Monthly | Immediate | At Payment: DR Cash, CR Revenue |
| Enterprise Annual | Annual | Deferred | Monthly: DR Deferred, CR Revenue |
| Publication Monthly | Monthly | Immediate | At Payment: DR Cash, CR Revenue |

### Key Accounts
| Account | Code | Purpose |
|---------|------|---------|
| Membership Revenue | 4100/4110 | Where recognized revenue posts |
| Deferred Revenue | 2300 | Holding unearned revenue |
| A/R Memberships | 1200 | Outstanding invoices |

### Processing Schedule
- **Daily:** Automated recognition processing (cron job)
- **Weekly:** Monitor recognition dashboard
- **Monthly:** Run deferred revenue reports
- **Quarterly:** Review completed schedules
- **Annually:** Audit recognition compliance