# AMS Subscription System - Complete Setup Guide

## 🎯 What This Guide Covers

This step-by-step guide will walk you through setting up your Association Management System (AMS) to manage memberships, chapters, and publications. By the end, you'll be able to:

- Create subscription tiers and products
- Sell memberships through your website and POS
- Automatically generate subscriptions from sales
- Manage member lifecycles and renewals

---

## 📋 Before You Start

**Prerequisites:**
- AMS Subscriptions module is installed and upgraded
- You have Admin or AMS Subscription User permissions
- You know your association's membership structure (tiers, pricing, benefits)

**What You'll Need:**
- List of membership types (Individual, Enterprise, Chapter, Publication)
- Pricing for each membership type
- Lifecycle rules (grace periods, suspension rules)

---

## Step 1: Configure Global Settings

**Why:** Set up default lifecycle rules that apply to all subscriptions.

### 🔧 How To:

1. **Go to:** AMS → Configuration → Lifecycle Settings
2. **Set Default Periods:**
   - **Grace Period:** 30 days (members can still access benefits after expiration)
   - **Suspension Period:** 60 days (benefits suspended but membership recoverable)
   - **Termination Period:** 30 days (membership permanently ended)
3. **Configure Renewals:**
   - ✅ **Auto-Create Renewal Invoices:** Checked
   - **Renewal Notice:** 14 days before expiration
4. **Communication:**
   - ✅ **Send Lifecycle Emails:** Checked (when available)
5. **Click:** Apply Settings

**✅ Result:** Global defaults are now configured for all new tiers.

---

## Step 2: Create Subscription Tiers

**Why:** Tiers define the rules and benefits for different membership levels.

### 🏆 Individual Membership Example

1. **Go to:** AMS → Configuration → Subscription Tiers
2. **Click:** Create
3. **Fill in:**
   - **Name:** "Professional Member"
   - **Subscription Type:** Membership - Individual
   - **Description:** "Full professional membership with all benefits"
   - **Billing Period:** Annual
   - **Grace Days:** 30
   - **Suspension Days:** 60  
   - **Termination Days:** 30
   - ✅ **Auto Renew By Default:** Checked
   - ❌ **Free Tier:** Unchecked

4. **Optional - Add Benefits:**
   - In **Included Benefits:** Select products that come free with this tier
   - Example: Free access to digital publications

5. **Click:** Save

### 🏢 Enterprise Membership Example

1. **Create New Tier:**
   - **Name:** "Corporate Membership"
   - **Subscription Type:** Membership - Enterprise
   - **Default Seats:** 5 (number of employee seats included)
   - **Same lifecycle settings as above**

### 📚 Chapter/Publication Tiers

Repeat the process for:
- **Chapter Membership:** For regional groups
- **Publication Subscription:** For journals/magazines

**✅ Result:** You now have tiers that define membership rules and benefits.

---

## Step 3: Create Subscription Products

**Why:** Products are what customers actually purchase. They connect to tiers to create subscriptions.

### 💳 Create an Individual Membership Product

1. **Go to:** AMS → Products → Create Product
2. **Fill in Basic Info:**
   - **Product Name:** "Professional Membership - Annual"
   - **Sales Price:** $150.00
   - **Product Category:** Will auto-set to "Individual Memberships"

3. **Configure AMS Settings:**
   - **AMS Product Type:** Membership - Individual
   - **Subscription Period:** Annual
   - **Default Subscription Tier:** Select "Professional Member" (created above)

4. **Lifecycle Settings:** (Will inherit from tier, but can customize)
   - **Grace Days:** 30
   - **Suspend Days:** 60
   - **Terminate Days:** 30

5. **Make it Sellable:**
   - ✅ **Can be Sold:** Checked (auto-set)
   - ✅ **Published on Website:** Checked (auto-set)

6. **Click:** Save

**🎉 Magic Happens:** The system automatically:
- Sets product type to "Service" 
- Creates appropriate product category
- Makes it available for online sales

### 🏢 Create Enterprise Membership Product

1. **Same process as above, but:**
   - **AMS Product Type:** Membership - Enterprise
   - **Default Subscription Tier:** Select your enterprise tier
   - **Price:** $750.00 (example)

### 📖 Create Chapter/Publication Products

1. **For Chapters:**
   - **AMS Product Type:** Chapter
   - **Price:** $50.00 (example)

2. **For Publications:**
   - **AMS Product Type:** Publication
   - ✅ **Digital Publication:** Check if it's digital
   - **Publication Type:** Journal, Magazine, etc.

**✅ Result:** You now have products customers can purchase that automatically create subscriptions.

---

## Step 4: Create Enterprise Seat Add-On Products

**Why:** Allow enterprise customers to buy additional employee seats.

### 💺 Additional Seats Product

1. **Go to:** AMS → Products → Create Product
2. **Fill in:**
   - **Product Name:** "Additional Enterprise Seat"
   - **Sales Price:** $25.00
   - **AMS Product Type:** Enterprise
   - ✅ **Enterprise Seat Add-On:** Checked

3. **Click:** Save

**✅ Result:** When purchased, this adds seats to existing enterprise subscriptions instead of creating new ones.

---

## Step 5: Test Your Setup

**Why:** Ensure everything works before going live.

### 🧪 Create a Test Subscription

1. **Go to:** Sales → Orders → Create
2. **Select a Customer**
3. **Add Product:** Select your "Professional Membership - Annual"
4. **Confirm Sale**

**What Should Happen:**
- Sale order is confirmed
- Subscription is automatically created
- Subscription shows as "Active"
- Customer gains membership benefits

### ✅ Verify the Subscription

1. **Go to:** AMS → Members → Active Subscriptions
2. **Find your test subscription**
3. **Check:**
   - Status: Active
   - Start Date: Today
   - Paid Through Date: Set correctly
   - Tier: Correctly linked

**✅ Result:** Your system is working! Subscriptions are automatically created from sales.

---

## Step 6: Set Up Your Website Shop

**Why:** Let customers purchase memberships online.

### 🌐 Publish Products

1. **Go to:** Website → Shop
2. **Your AMS products should appear automatically**
3. **If not visible:**
   - Go to product → Edit
   - ✅ **Published on Website:** Check
   - Save

### 🛒 Test Online Purchase

1. **Visit your website shop**
2. **Add membership to cart**
3. **Complete checkout**
4. **Verify subscription created in AMS**

**✅ Result:** Customers can now buy memberships online!

---

## Step 7: Daily Management

### 📊 Monitor Active Subscriptions

**Go to:** AMS → Members → Active Subscriptions

**Use the Kanban view to see:**
- Subscriptions by status (Active, Grace, Suspended, Terminated)
- Quick overview of member details
- Enterprise seat usage

### 🔄 Manage Enterprise Seats

**For Enterprise Subscriptions:**

1. **Go to:** AMS → Members → Seat Assignments
2. **Assign seats to employees:**
   - Select subscription
   - Add contact
   - Set assigned date
3. **Track seat usage** in subscription record

### 📈 View Reports and Statistics

1. **Product Performance:**
   - AMS → Products → All AMS Products
   - See "Active Subscriptions Count" column

2. **Member Types:**
   - AMS → Memberships → Individual Memberships
   - AMS → Memberships → Enterprise Memberships

3. **Regional Activity:**
   - AMS → Chapters → Chapter Subscriptions

---

## Step 8: Handle Common Scenarios

### 🆕 New Member Signs Up

**Automatic Process:**
1. Customer purchases membership online/POS
2. Sale is confirmed
3. Subscription automatically created
4. Member gets benefits immediately

**Manual Process (if needed):**
1. AMS → Members → All Subscriptions → Create
2. Fill in member details
3. Select product and tier
4. Set dates and activate

### 💳 Member Renewals

**Automatic Process:**
1. System creates renewal invoice 14 days before expiration
2. Member pays invoice
3. Subscription is automatically extended

**Manual Renewal:**
1. Find expiring subscription
2. Create new sale order for same product
3. Confirm sale to extend subscription

### 🏢 Enterprise Adds Seats

**Automatic Process:**
1. Customer purchases "Additional Enterprise Seat" product
2. Seats are automatically added to existing subscription

**Manual Process:**
1. Find enterprise subscription
2. Increase "Extra Seats" number
3. Assign new seats to employees

### ⚠️ Handle Expired Memberships

**System automatically moves subscriptions through:**
1. **Active** → **Grace** (after paid-through date)
2. **Grace** → **Suspended** (after grace period)
3. **Suspended** → **Terminated** (after suspension period)

**To manually manage:**
1. Find subscription in appropriate status
2. Use action buttons: Activate, Suspend, Terminate
3. Update paid-through date if payment received

---

## 🆘 Troubleshooting Guide

### ❓ Product doesn't show AMS fields

**Solution:**
1. Check AMS Product Type is not "None"
2. Save and refresh the form
3. AMS Subscription tab should appear

### ❓ Subscription not created after sale

**Check:**
1. Product has AMS Product Type set
2. Product has Default Subscription Tier
3. Sale order was confirmed (not just quoted)

### ❓ Can't see AMS menu

**Solution:**
1. Check user has "AMS Subscription User" permission
2. Ask admin to add you to AMS security group

### ❓ Renewal invoices not generating

**Check:**
1. AMS → Configuration → Lifecycle Settings
2. Ensure "Auto-Create Renewal Invoices" is checked
3. Check subscription has "Auto Renew" enabled
4. Verify paid-through date is set

---

## 🎊 Congratulations!

You've successfully set up your AMS subscription system! Your association can now:

- ✅ Sell memberships online and in-person
- ✅ Automatically create and manage subscriptions  
- ✅ Handle individual and enterprise memberships
- ✅ Manage chapters and publications
- ✅ Track member lifecycles and renewals
- ✅ Generate automatic renewal invoices

### 🚀 Next Steps

1. **Import existing members** (if needed)
2. **Set up email templates** for lifecycle notifications
3. **Create member portal access** for self-service
4. **Integrate with accounting** for revenue recognition
5. **Add reporting dashboards** for insights

### 📞 Need Help?

- Check the subscription kanban view for visual status overview
- Use filters in list views to find specific subscriptions
- Statistics show on product records (Active Subscriptions Count)
- All lifecycle changes are logged with timestamps

**Your AMS system is now ready to manage your association's membership lifecycle efficiently!** 🎉