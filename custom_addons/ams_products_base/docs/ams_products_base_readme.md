# AMS Products Base - Enhanced Product Behavior Management

A comprehensive product behavior management system for Association Management Systems (AMS), providing intuitive employee UX and powerful integration capabilities for downstream modules.

## 🌟 Key Features

### Product Behavior Types (Radio Button Selection)
- **Membership Products**: Recurring memberships with portal access and benefit management
- **Subscription Products**: Flexible billing cycles with term configuration
- **Event Products**: Event registration with automatic enrollment and member pricing
- **Publication Products**: Magazines, newsletters, and reports with subscription options
- **Merchandise Products**: Physical goods with inventory tracking and member discounts
- **Certification Products**: Digital certificates with portal access and renewal management
- **Digital Downloads**: Instant file/URL delivery with access control
- **Donation Products**: Tax-deductible contributions with automatic receipt generation

### Enhanced Employee User Experience
- **Intuitive Product Behavior Tab**: Contextual fields based on product type selection
- **Smart Defaults**: Behavior-based automatic configuration with override capability
- **Visual Status Indicators**: Clear configuration status and issue identification
- **One-Click Testing**: Built-in tools for member pricing and behavior validation
- **Guided Configuration**: Tooltips and help text eliminate technical complexity

### Category-Driven Configuration
- Products inherit comprehensive settings from enhanced AMS categories
- Employee override capability for product-specific requirements
- Smart onchange behavior applies appropriate defaults automatically
- Behavior-based SKU generation with meaningful prefixes (MEM-, EVT-, DIG-, etc.)

## 📋 Installation & Setup

### Prerequisites
- Odoo Community 18.0+
- `ams_member_data` module for membership integration
- `ams_product_types` module for enhanced categories

### Installation Steps

1. **Install Dependencies**:
```bash
   # Install required AMS modules first
   ./odoo-bin -d your_db -i ams_member_data,ams_product_types

Install AMS Products Base:

bash   ./odoo-bin -d your_db -i ams_products_base

Verify Installation:

Navigate to Sales → AMS Products
Create a test product and verify behavior selection works
Check demo data is loaded correctly



🚀 Quick Start Guide
Creating Your First AMS Product

Navigate to Products: Go to Sales → AMS Products → Create
Basic Information:

Enter product name (SKU will auto-generate)
Set price
Select appropriate AMS category
Toggle "AMS Product" to enable enhanced features


Select Product Behavior:

Choose behavior type from radio buttons
Watch contextual fields appear automatically
Smart defaults populate based on selection


Configure Behavior-Specific Settings:

Membership: Set subscription term, portal access, benefits
Event: Configure event registration, member-only access
Digital: Add download URL or file attachment
Subscription: Set billing cycle and portal access
Donation: Configure tax deductibility and receipt template


Test Configuration:

Use "Test Product Behavior" button to verify setup
Test member pricing with "Test Member Pricing" button



Example: Creating a Conference Registration
python# Via UI or programmatically
conference = env['product.template'].create({
    'name': 'Annual Industry Conference 2024',
    'list_price': 499.00,
    'is_ams_product': True,
    'ams_product_behavior': 'event',
    # Auto-populated by behavior selection:
    # creates_event_registration = True
    # type = 'service'
    # SKU = 'EVT-ANNUAL...'
})
💰 Member Pricing System
Automatic Discount Calculation
python# Products inherit member discounts from categories
event_product = env['product.template'].create({
    'name': 'Workshop Registration',
    'categ_id': event_category.id,  # Has 20% member discount
    'list_price': 200.00,
    # Automatically computed:
    # member_price = 160.00
    # member_savings = 40.00
})

# Get partner-specific pricing
member_price = event_product.get_price_for_partner(member_partner)  # $160.00
regular_price = event_product.get_price_for_partner(guest_partner)  # $200.00
Pricing Display

List View: Shows both regular and member prices
Product Form: Displays savings calculation and pricing summary
Sales Orders: Automatically applies appropriate pricing based on customer membership

🔄 Subscription Management
Flexible Terms
pythonsubscription_product = env['product.template'].create({
    'name': 'Professional Journal',
    'ams_product_behavior': 'subscription',
    'subscription_term': 24,
    'subscription_term_type': 'months',
    'grants_portal_access': True,
})

# Get subscription details
details = subscription_product.get_subscription_details()
# Returns: {'is_subscription': True, 'term': 24, 'term_type': 'months', 'term_display': '24 Months'}
Integration Hooks

Subscription Module: Use get_subscription_details() for billing cycle setup
Portal Access: Automatic permission granting based on grants_portal_access
Renewal Management: Built-in renewal tracking and notification support

💾 Digital Content Delivery
Content Configuration
pythondigital_product = env['product.template'].create({
    'name': 'Industry Report 2024',
    'ams_product_behavior': 'digital',
    'digital_url': 'https://secure.example.com/download/report-2024',
    # OR
    'digital_attachment_id': attachment.id,
})
Access Management
python# Check content availability and access permissions
access_info = digital_product.get_digital_content_access(partner)
# Returns: {
#     'is_digital': True,
#     'has_content': True,
#     'can_access': True,
#     'download_url': 'https://...',
#     'attachment_id': 123
# }
Delivery Workflow

Purchase Completion: Product automatically identified as digital
Access Validation: Membership requirements checked if applicable
Content Delivery: URL/file provided based on access permissions
Tracking: Download events logged for analytics

🎫 Event Integration
Automatic Registration
pythonevent_product = env['product.template'].create({
    'name': 'Leadership Workshop',
    'ams_product_behavior': 'event',
    'creates_event_registration': True,
    'default_event_template_id': event_template.id,
})

# Get event configuration
event_details = event_product.get_event_integration_details()
# Returns: {'creates_registration': True, 'default_event': 'Workshop Template', ...}
Member-Only Events

Set requires_membership = True for exclusive events
Automatic purchase validation based on membership status
Integration with event module for seamless registration workflow

🏛️ Portal Access Management
Automatic Permission Granting
pythonmembership_product = env['product.template'].create({
    'name': 'Premium Membership',
    'ams_product_behavior': 'membership',
    'grants_portal_access': True,
    'portal_group_ids': [(4, premium_group.id), (4, member_group.id)],
})
Integration Workflow

Product Purchase: Portal access product identified
Group Assignment: Customer automatically added to specified portal groups
Access Activation: Portal permissions granted immediately
Management: Integration hooks for access lifecycle management

💝 Donation & Tax Management
Tax-Deductible Contributions
pythondonation_product = env['product.template'].create({
    'name': 'General Fund Donation',
    'ams_product_behavior': 'donation',
    'donation_tax_deductible': True,
    'donation_receipt_template_id': receipt_template.id,
})
Receipt Generation

Automatic receipt creation upon donation processing
Customizable email templates with donation details
Tax compliance tracking and reporting
Integration with accounting for proper categorization

📊 Accounting Integration
Multiple GL Account Types
pythonproduct.get_accounting_configuration()
# Returns: {
#     'deferred_revenue_account': '2400',
#     'cash_account': '1100', 
#     'refund_account': '2500',
#     'membership_revenue_account': '4100'
# }
Revenue Recognition

Immediate: Standard product sales
Deferred: Subscriptions and prepaid services
Membership: Specialized membership revenue accounts
Event-Based: Revenue recognition on event occurrence

🔍 Search & Filtering
Advanced Search Capabilities

Behavior-Based Filtering: Find products by behavior type
Feature Filtering: Member pricing, portal access, digital content
Status Filtering: Available, missing content, configuration issues
Member Benefits: Products granting specific benefits or access

Issue Tracking

Missing Digital Content: Digital products without URLs/files
Missing Event Templates: Event products without linked templates
Configuration Issues: Automatic validation and issue detection
Out of Stock: Merchandise variants needing replenishment

🔧 API Reference
Core Product Methods
Business Logic Methods
python# Pricing
product.get_price_for_partner(partner)                    # Get member/regular price
product.can_be_purchased_by_partner(partner)              # Check purchase permissions
product.get_member_savings_amount(partner)                # Calculate savings

# Behavior-Specific Details
product.get_subscription_details()                        # Subscription configuration
product.get_portal_access_details()                       # Portal access settings
product.get_donation_details()                            # Tax deductibility info
product.get_event_integration_details()                   # Event registration config
product.get_digital_content_access(partner)               # Digital content access
product.get_accounting_configuration()                    # GL account setup
Query Methods
python# Template Queries
ProductTemplate.get_products_by_behavior_type('membership')
ProductTemplate.get_subscription_products()
ProductTemplate.get_digital_products()
ProductTemplate.get_donation_products()
ProductTemplate.get_portal_access_products()
ProductTemplate.get_event_products()

# Variant Queries  
ProductProduct.get_ams_variants_by_behavior_type('event')
ProductProduct.get_subscription_variants()
ProductProduct.get_portal_access_variants()
ProductProduct.get_variants_with_issues()
Variant-Specific Methods
python# Enhanced Variant Information
variant.get_comprehensive_variant_summary()               # Complete variant details
variant.get_variant_issues()                             # Configuration problems
variant.get_member_savings_amount(partner)               # Variant-specific savings

# Testing and Validation
variant.action_test_variant_behavior()                   # Test configuration
variant.action_test_variant_access()                     # Test partner access
🏗️ Extension and Integration
Extending for Specialized Modules
Adding Custom Behavior Types
python# In your custom module
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    ams_product_behavior = fields.Selection(
        selection_add=[
            ('custom_behavior', 'Custom Product Type'),
        ]
    )
    
    @api.onchange('ams_product_behavior')
    def _onchange_ams_product_behavior(self):
        result = super()._onchange_ams_product_behavior()
        
        if self.ams_product_behavior == 'custom_behavior':
            # Set custom defaults
            self.custom_field = True
            self.type = 'service'
            
        return result
Integration Hooks
python# Subscription Module Integration
def create_subscription_from_product(product, partner):
    """Create subscription from product purchase"""
    if product.is_subscription_product:
        details = product.get_subscription_details()
        subscription = env['sale.subscription'].create({
            'partner_id': partner.id,
            'template_id': product.subscription_template_id.id,
            'recurring_rule_type': details['term_type'],
            'recurring_interval': details['term'],
        })
        return subscription

# Event Module Integration
def register_for_event(product, partner):
    """Register partner for event product"""
    if product.creates_event_registration:
        event_details = product.get_event_integration_details()
        if event_details['default_event_id']:
            registration = env['event.registration'].create({
                'event_id': event_details['default_event_id'],
                'partner_id': partner.id,
                'state': 'open',
            })
            return registration

# Portal Access Integration
def grant_portal_access(product, partner):
    """Grant portal access from product purchase"""
    if product.grants_portal_access:
        portal_details = product.get_portal_access_details()
        for group_id in portal_details['portal_group_ids']:
            partner.user_ids.write({'groups_id': [(4, group_id)]})
Category Enhancement
python# Extend categories for specialized behavior
class ProductCategory(models.Model):
    _inherit = 'product.category'
    
    # Add organization-specific category attributes
    custom_category_field = fields.Boolean('Custom Category Feature')
    default_benefits = fields.Text('Default Benefits Description')
    
    @api.onchange('ams_category_type')
    def _onchange_ams_category_type(self):
        result = super()._onchange_ams_category_type()
        
        # Add custom defaults based on category type
        if self.ams_category_type == 'custom_type':
            self.custom_category_field = True
            
        return result
📈 Reporting and Analytics
Built-in Reports

Product Behavior Analysis: Distribution of products by behavior type
Member Pricing Impact: Savings analysis and member benefit tracking
Digital Content Usage: Access patterns and delivery statistics
Subscription Revenue: Recurring revenue tracking by product
Configuration Issues: Products needing attention or fixes

Custom Analytics
python# Get comprehensive product statistics
def get_ams_product_analytics():
    templates = env['product.template'].search([('is_ams_product', '=', True)])
    
    analytics = {
        'total_products': len(templates),
        'by_behavior': {},
        'member_pricing_enabled': len(templates.filtered('member_savings')),
        'subscription_products': len(templates.filtered('is_subscription_product')),
        'portal_access_products': len(templates.filtered('grants_portal_access')),
        'digital_products': len(templates.filtered('has_digital_content')),
    }
    
    # Behavior distribution
    for behavior in ['membership', 'event', 'subscription', 'digital', 'donation']:
        behavior_products = templates.filtered(lambda p: p.ams_product_behavior == behavior)
        analytics['by_behavior'][behavior] = len(behavior_products)
    
    return analytics
Performance Monitoring

Query Performance: Optimized database queries with proper indexing
Member Pricing Calculation: Cached computations for large product catalogs
Digital Content Access: Efficient access validation and delivery
Configuration Validation: Automated issue detection and notification

🧪 Testing and Quality Assurance
Comprehensive Test Suite
bash# Run all AMS Products Base tests
./odoo-bin -d test_db --test-tags ams_products_base --stop-after-init

# Run specific test categories
./odoo-bin -d test_db --test-tags ams_products_base.test_behavior_management
./odoo-bin -d test_db --test-tags ams_products_base.test_member_pricing
./odoo-bin -d test_db --test-tags ams_products_base.test_digital_content
Test Coverage

✅ Product Behavior Selection: All behavior types and defaults
✅ Member Pricing: Calculation accuracy and partner-specific logic
✅ Subscription Management: Term configuration and integration hooks
✅ Digital Content: Access control and delivery validation
✅ Event Integration: Registration creation and member-only events
✅ Portal Access: Permission granting and group management
✅ Donation Processing: Tax deductibility and receipt generation
✅ Variant Inheritance: Template behavior propagation to variants
✅ Validation Rules: Data integrity and business logic enforcement
✅ Query Methods: Search performance and result accuracy

Demo Data Testing
python# Test with comprehensive demo data
def test_demo_data_scenarios():
    """Test real-world scenarios using demo data"""
    
    # Member vs non-member pricing
    member = env.ref('ams_products_base.demo_member_jane_active')
    non_member = env.ref('ams_products_base.demo_non_member_prospect')
    conference = env.ref('ams_products_base.demo_event_annual_conference')
    
    member_price = conference.get_price_for_partner(member)
    regular_price = conference.get_price_for_partner(non_member)
    
    assert member_price < regular_price, "Member should get discounted price"
    
    # Digital content access
    ebook = env.ref('ams_products_base.demo_digital_ebook_collection')
    access = ebook.get_digital_content_access(member)
    
    assert access['is_digital'], "Should be digital product"
    assert access['has_content'], "Should have download content"
    assert access['can_access'], "Member should have access"
🚨 Troubleshooting
Common Issues and Solutions
Issue: Product Behavior Not Applying Defaults
Symptoms: Selecting behavior type doesn't populate expected fields
Solutions:

Ensure is_ams_product is set to True
Check that ams_product_behavior is properly selected
Verify category has appropriate AMS configuration
Clear browser cache and refresh form

Issue: Member Pricing Not Calculating
Symptoms: Member price equals regular price
Solutions:

Verify category has requires_member_pricing = True
Check member_discount_percent is set on category
Ensure partner has is_member = True and membership_status = 'active'
Confirm ams_member_data module is installed and configured

Issue: Digital Content Access Denied
Symptoms: Digital products showing as missing content
Solutions:

Add either digital_url or digital_attachment_id to product
Ensure URL starts with http:// or https://
Verify file attachment is properly uploaded
Check partner permissions and membership requirements

Issue: SKU Not Auto-Generating
Symptoms: Products created without default_code
Solutions:

Ensure product name is provided during creation
Verify is_ams_product = True
Check ams_product_behavior is selected
Confirm uniqueness constraints aren't preventing generation

Performance Optimization
Large Product Catalogs

Use database indexes on behavior and category fields
Implement batch processing for bulk product operations
Cache frequently accessed computed fields
Optimize member pricing calculations with stored fields

High-Volume Transactions

Pre-compute member pricing for performance
Use efficient query methods for product filtering
Implement proper caching for digital content access validation
Optimize variant inheritance calculations

Data Migration
From Legacy Systems
python# Example migration script
def migrate_legacy_products():
    """Migrate products from legacy AMS system"""
    
    legacy_products = get_legacy_product_data()
    
    for legacy_product in legacy_products:
        # Map legacy type to behavior
        behavior_mapping = {
            'MEMBERSHIP': 'membership',
            'EVENT_REG': 'event', 
            'PUBLICATION': 'publication',
            'MERCHANDISE': 'merchandise',
            'DONATION': 'donation',
        }
        
        behavior = behavior_mapping.get(legacy_product['type'], 'merchandise')
        
        # Create with behavior-specific configuration
        product = env['product.template'].create({
            'name': legacy_product['name'],
            'list_price': legacy_product['price'],
            'is_ams_product': True,
            'ams_product_behavior': behavior,
            'legacy_product_id': legacy_product['id'],
            # Behavior defaults will be applied automatically
        })
        
        # Apply legacy-specific overrides
        if legacy_product.get('member_discount'):
            # Override category default if needed
            product.member_discount_override = legacy_product['member_discount']
📚 Additional Resources
Documentation

API Reference: Complete method documentation with examples
Integration Guide: Step-by-step integration with other modules
Best Practices: Recommended patterns for AMS product management
Performance Guide: Optimization strategies for large installations

Training Materials

Employee Training: User guide for product configuration
Developer Training: Technical guide for module extension
Video Tutorials: Step-by-step product setup demonstrations
Webinar Series: Advanced configuration and integration topics

Community Support

GitHub Repository: Source code and issue tracking
Community Forum: Questions and discussion
Documentation Wiki: Community-maintained guides and examples
Bug Reports: Issue submission and resolution tracking

Professional Services

Custom Development: Specialized behavior types and integrations
Data Migration: Legacy system migration and cleanup
Performance Optimization: Large-scale deployment optimization
Training and Support: On-site training and ongoing support


📄 License
This module is licensed under LGPL-3. See LICENSE file for details.
🤝 Contributing
We welcome contributions! Please see CONTRIBUTING.md for guidelines on:

Code standards and best practices
Testing requirements and procedures
Documentation expectations
Pull request process and review guidelines

📞 Support
For technical support, feature requests, or questions:

Documentation: This README and inline code documentation
Issue Tracker: GitHub issues for bugs and feature requests
Community Forum: Discussion and community support
Professional Support: Commercial support and custom development