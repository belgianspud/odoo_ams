# Seat Management & Organizational Memberships Guide

## Overview

This guide covers the enhanced seat management features for organizational memberships, including seat packs, seat allocation, and organizational settings.

---

## Table of Contents

1. [Seat Product Configuration](#seat-product-configuration)
2. [Organizational Membership Settings](#organizational-membership-settings)
3. [Creating Seat Products](#creating-seat-products)
4. [Seat Allocation Workflow](#seat-allocation-workflow)
5. [Seat Packs vs Individual Seats](#seat-packs-vs-individual-seats)
6. [Quick Setup Wizard](#quick-setup-wizard)
7. [Best Practices](#best-practices)

---

## Seat Product Configuration

### New Product Fields

Seat products are defined using these new fields on `product.template`:

#### Core Seat Fields

| Field | Type | Description |
|-------|------|-------------|
| `provides_seats` | Boolean | This product adds seats to an organizational membership |
| `seat_quantity` | Integer | Number of seats provided per purchase (e.g., 5 for "5-Seat Pack") |
| `is_seat_addon` | Boolean | Computed: True if this is a seat add-on product |
| `parent_membership_product_id` | Many2one | Links to the parent organizational membership product |
| `price_per_seat` | Float | Computed: Price divided by seat quantity |

#### Example: 5-Seat Pack
```xml
<record id="product_org_5seat_pack" model="product.template">
    <field name="name">Organizational Membership - 5 Seat Pack</field>
    <field name="list_price">100.00</field>
    <field name="provides_seats" eval="True"/>
    <field name="seat_quantity">5</field>
    <field name="parent_membership_product_id" ref="product_membership_organizational"/>
</record>
Result: Customers pay $100 for 5 seats = $20 per seat
Example: Individual Seat
xml<record id="product_org_single_seat" model="product.template">
    <field name="name">Organizational Membership - Additional Seat</field>
    <field name="list_price">25.00</field>
    <field name="provides_seats" eval="True"/>
    <field name="seat_quantity">1</field>
    <field name="parent_membership_product_id" ref="product_membership_organizational"/>
</record>
Result: Customers pay $25 for 1 seat = $25 per seat

Organizational Membership Settings
New Organizational Fields
Configure organizational behavior on the parent membership product:
Information Requirements
FieldTypeDefaultDescriptionrequires_organization_infoBooleanTrueCollect detailed organization informationrequires_primary_contactBooleanTrueOrganization must designate a primary contactrequire_org_tax_idBooleanFalseOrganization must provide tax ID (EIN, VAT)require_org_addressBooleanTrueOrganization must provide physical addressmax_org_sizeInteger0Maximum employees/members (0 = unlimited)
Seat Management Settings
FieldTypeDefaultDescriptionallow_multiple_adminsBooleanTrueOrganization can have multiple admin usersseat_allocation_typeSelectionadmin_managedHow seats are assigned to employeesseat_approval_requiredBooleanFalseSeat allocations need admin approval
Seat Allocation Types

Admin Managed (admin_managed)

Organization admins manually allocate seats to employees
Most control, best for smaller organizations
Default and recommended option


Self-Service (self_service)

Employees can request seats themselves
Optional approval workflow
Good for larger organizations


Automatic (automatic)

Seats allocated automatically based on rules
Advanced use case, requires custom logic



Example Configuration
xml<record id="product_membership_org_premium" model="product.template">
    <field name="name">Premium Organizational Membership</field>
    <field name="list_price">1000.00</field>
    <field name="subscription_product_type">organizational_membership</field>
    
    <!-- Information Requirements -->
    <field name="requires_organization_info" eval="True"/>
    <field name="requires_primary_contact" eval="True"/>
    <field name="require_org_tax_id" eval="True"/>
    <field name="require_org_address" eval="True"/>
    <field name="max_org_size">100</field>
    
    <!-- Seat Management -->
    <field name="allow_multiple_admins" eval="True"/>
    <field name="seat_allocation_type">self_service</field>
    <field name="seat_approval_required" eval="True"/>
</record>

Creating Seat Products
Method 1: Quick Setup Wizard (Recommended)
The Quick Setup Wizard creates everything in one step:

Navigate to Membership → 🚀 Quick Setup
Select Membership Type: Organization Membership
Configure Basic Information: Name, Code, Price
Configure Organization Settings:

Included Seats: 5
Maximum Seats: 50 (or 0 for unlimited)
✓ Create Additional Seat Product


Configure Seat Add-on Product:

Seat Add-on Type: Seat Packs
Seats Per Pack: 5
Pack Price: $100 (auto-calculated from individual seat price)


Configure Organization Requirements
Click 🚀 Create Membership

Result: Creates 3 records automatically:

Membership Category
Parent Organizational Product
Subscription Plan (with seat configuration)
Seat Add-on Product (5-Seat Pack)

Method 2: Manual Creation
Step 1: Create Parent Organizational Product
pythonparent_product = self.env['product.template'].create({
    'name': 'Corporate Membership - Annual',
    'list_price': 500.00,
    'is_membership_product': True,
    'subscription_product_type': 'organizational_membership',
    'requires_organization_info': True,
    'requires_primary_contact': True,
    'seat_allocation_type': 'admin_managed',
})
Step 2: Create Subscription Plan with Seats
pythonplan = self.env['subscription.plan'].create({
    'name': 'Corporate Membership - Annual',
    'product_template_id': parent_product.id,
    'price': 500.00,
    'billing_period': 'yearly',
    'supports_seats': True,
    'included_seats': 5,
    'max_seats': 50,
    'additional_seat_price': 24.00,  # Per individual seat
})
Step 3: Create Seat Pack Product
pythonseat_pack = self.env['product.template'].create({
    'name': 'Corporate Membership - 5 Seat Pack',
    'list_price': 100.00,  # $20 per seat
    'is_membership_product': True,
    'provides_seats': True,
    'seat_quantity': 5,
    'parent_membership_product_id': parent_product.id,
})
Step 4: Link Seat Product to Plan
pythonplan.seat_product_id = seat_pack.id

Seat Allocation Workflow
User Interface Workflow

Navigate to Organization Subscription

Membership → Memberships → Active Memberships
Open an organizational subscription


View Seat Management Tab

Click 🪑 Seat Management tab
See: Total seats, Allocated seats, Available seats
View: Utilization percentage and seat list


Allocate Seats

Click 🎯 Allocate Seats button
Choose allocation method:

Single Seat: Allocate to one employee
Multiple Seats: Allocate to multiple employees


Select employee(s)
Set organizational role
✓ Send notification email
Click 🎯 Allocate Seats


Result:

Seat subscription created for employee
Employee linked to organization
Email sent to employee (if enabled)
Employee gets full membership access



Programmatic Allocation
python# Get organizational subscription
org_subscription = self.env['subscription.subscription'].browse(subscription_id)

# Allocate seat to employee
employee = self.env['res.partner'].browse(employee_id)

seat_subscription = org_subscription.action_allocate_seat(employee.id)

# Seat subscription is created and linked
# Employee now has membership access
Deallocation Workflow

Remove Seat

Go to 🪑 Seat Management tab
Find seat in list
Click Remove Seat button or use wizard


Deallocation Wizard

Select seats to remove
Choose reason
✓ Send notification email
Click 🗑️ Remove Seats


Result:

Seat subscription cancelled
Employee loses membership access
Email sent to employee (if enabled)
Seat becomes available for reallocation




Seat Packs vs Individual Seats
When to Use Seat Packs
Seat Packs (seat_quantity > 1) are ideal when:
✅ You want to offer bulk discounts
✅ Organizations typically add multiple seats at once
✅ You want simplified pricing (e.g., "$100 for 5 seats")
✅ You want to encourage larger purchases
Example Pricing Strategy:

Base membership: $500 (includes 5 seats) = $100/seat
5-Seat Pack: $100 = $20/seat (80% discount per seat)
10-Seat Pack: $180 = $18/seat (82% discount per seat)

When to Use Individual Seats
Individual Seats (seat_quantity = 1) are ideal when:
✅ Organizations add seats one at a time as they grow
✅ You want simple, transparent pricing
✅ No bulk discount strategy needed
✅ Maximum flexibility
Example Pricing Strategy:

Base membership: $500 (includes 5 seats)
Additional Seat: $25/seat (no bulk discount)

Mixed Strategy (Recommended)
Offer both seat packs AND individual seats:
xml<!-- Individual Seat: Full Price -->
<record id="product_org_single_seat" model="product.template">
    <field name="name">Additional Seat</field>
    <field name="list_price">25.00</field>
    <field name="seat_quantity">1</field>
</record>

<!-- 5-Seat Pack: Discounted -->
<record id="product_org_5seat_pack" model="product.template">
    <field name="name">5-Seat Pack</field>
    <field name="list_price">100.00</field>
    <field name="seat_quantity">5</field>
</record>

<!-- 10-Seat Pack: More Discounted -->
<record id="product_org_10seat_pack" model="product.template">
    <field name="name">10-Seat Pack</field>
    <field name="list_price">180.00</field>
    <field name="seat_quantity">10</field>
</record>
Pricing Comparison:

1 seat: $25 (100%)
5 seats pack: $100 → $20/seat (20% off)
10 seats pack: $180 → $18/seat (28% off)

Customers choose based on their needs!

Quick Setup Wizard
Seat Configuration in Wizard
The wizard makes seat setup easy:
Step 5: Organization Settings
Included Seats: [5]
Maximum Seats: [50] (0 = unlimited)
☑ Create Additional Seat Product
Step 5-B: Seat Add-on Product
Seat Add-on Type:
  ○ Individual Seats (1 seat per purchase)
  ● Seat Packs (multiple seats per purchase)

Seats Per Add-on Pack: [5]

Pack Pricing:
  Price for Seat Pack: [$100.00]
  
  ℹ️ Seat Pack Pricing:
  • Seats per Pack: 5 seats
  • Pack Price: $100.00
  • Price per Seat in Pack: $20.00
Step 5-C: Organization Requirements
Information Requirements:
  ☑ Require Organization Info
  ☑ Require Primary Contact
  ☐ Require Tax ID
  ☑ Require Organization Address

Management Settings:
  ☑ Allow Multiple Administrators
  ● Admin Allocates Seats
  ○ Users Can Request Seats
  ○ Automatic Allocation
  ☐ Seat Requests Need Approval
  Max Organization Size: [0] (0 = unlimited)
Wizard Output
Creates complete membership configuration:

Category: "Corporate Member"
Parent Product: "Corporate Membership" ($500, includes 5 seats)
Subscription Plan: Yearly billing, supports seats
Seat Product: "Corporate Membership - 5 Seat Pack" ($100 for 5 seats)

All linked and ready to use!

Best Practices
Pricing Strategy

Calculate Base Per-Seat Cost

   Base Price: $500
   Included Seats: 5
   Base Per-Seat: $100

Set Premium for Individual Seats

   Individual Seat: $100 × 1.2 = $120
   (20% premium over base)

Offer Discounts for Packs

   5-Seat Pack: $100 × 5 × 0.8 = $400 ($80/seat)
   10-Seat Pack: $100 × 10 × 0.7 = $700 ($70/seat)
   (20-30% discount for bulk)
Seat Limits
Recommended Settings:

Small Organizations (1-20 employees):

Included: 5 seats
Max: 20 seats
Packs: 5-seat packs


Medium Organizations (20-100 employees):

Included: 10 seats
Max: 100 seats
Packs: 5-seat and 10-seat packs


Large Organizations (100+ employees):

Included: 20 seats
Max: 0 (unlimited)
Packs: 10-seat and 25-seat packs



Allocation Settings
Recommended by Organization Size:
Org SizeAllocation TypeApprovalWhy1-20Admin ManagedNoSimple, direct control20-100Self-ServiceYesBalance between control and efficiency100+Self-ServiceOptionalEfficiency, trust-based
Email Notifications
Always enable email notifications for:

✅ Seat allocation (welcome employees)
✅ Seat deallocation (inform of access removal)
✅ Subscription renewal reminders
✅ Seat limit warnings (approaching max)

Product Naming
Use clear, descriptive names:
✅ Good:

"Corporate Membership - 5 Seat Pack"
"Enterprise Membership - 10 Additional Seats"
"Professional Organization - Seat Add-on (5-pack)"

❌ Bad:

"Seats"
"Add-on"
"Pack #2"

Testing Workflow
Before going live:

✅ Create test organizational subscription
✅ Allocate test seats to test employees
✅ Verify employees receive emails
✅ Verify employees can access portal
✅ Test seat deallocation
✅ Test seat limit enforcement
✅ Test seat pack purchases
✅ Verify billing calculations


Troubleshooting
Common Issues
Issue: Can't allocate seats

✅ Check: Subscription is active or trial
✅ Check: Available seats > 0
✅ Check: Plan supports seats

Issue: Seat product not linked

✅ Check: seat_product_id set on plan
✅ Check: Seat product has provides_seats = True
✅ Check: parent_membership_product_id links to parent

Issue: Wrong per-seat price

✅ Check: seat_quantity is correct
✅ Check: list_price calculation
✅ Formula: list_price / seat_quantity = price_per_seat

Issue: Employees not getting access

✅ Check: Seat subscription state is active
✅ Check: seat_holder_id is set correctly
✅ Check: parent_organization_id links employee to org


Summary
The enhanced seat management system provides:
✅ Flexible Seat Products - Individual seats or seat packs
✅ Comprehensive Org Settings - Requirements, approval, allocation
✅ Easy Setup - Quick Setup Wizard creates everything
✅ Full Lifecycle - Allocation, deallocation, notifications
✅ Smart Pricing - Per-seat calculations, bulk discounts
✅ User-Friendly - Wizards, smart buttons, clear UI
For questions or issues, refer to the main module documentation or contact support.
