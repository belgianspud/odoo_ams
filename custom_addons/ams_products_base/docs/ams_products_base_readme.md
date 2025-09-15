# AMS Products Base

A simplified integration layer for association product management in Odoo, focusing on essential functionality while leveraging existing AMS modules.

## Overview

The AMS Products Base module serves as a clean integration layer between Odoo's native product system and the Association Management System (AMS) modules. Rather than recreating complex functionality, it focuses on essential integration points that enable powerful association-specific features.

### Design Philosophy

- **Leverage existing modules**: Uses `ams_product_types` for categories and `ams_member_data` for membership
- **Category-driven behavior**: Products automatically inherit configuration from enhanced categories
- **Simple integration**: Provides clean hooks for specialized modules to extend
- **Native Odoo integration**: Works seamlessly with Odoo's product, sales, and inventory systems

## Key Features

### 🏷️ **Category-Driven Configuration**
- Auto-detect AMS products from enhanced categories
- Inherit pricing, digital, and inventory settings automatically
- Simple onchange behavior applies category defaults

### 💰 **Member Pricing Integration**
- Calculate member pricing from category discount percentages
- Partner-specific pricing based on membership status from `ams_member_data`
- Automatic pricing summaries and member savings calculations

### 📱 **Digital Product Support**
- Basic digital content fields (URL and file attachment)
- Digital content availability checking
- Simple validation for digital products

### 👥 **Membership Requirements**
- Auto-detect membership requirements from categories
- Purchase permission checking based on membership status
- Integration hooks for access control

### 🔢 **Simple SKU Management**
- Auto-generate SKUs from product names when needed
- Use Odoo's native `default_code` field
- Legacy system integration support

## Installation

### Prerequisites
- Odoo Community 18.0+
- `ams_member_data` module (for membership integration)
- `ams_product_types` module (for enhanced categories)

### Install Steps

1. **Place module in addons path**:
   ```bash
   cp -r ams_products_base /path/to/odoo/addons/
   ```

2. **Update module list**:
   ```bash
   # From Odoo interface: Apps → Update Apps List
   # Or via command line:
   ./odoo-bin -d your_db --update-list
   ```

3. **Install module**:
   ```bash
   # From Odoo interface: Apps → Search "AMS Products Base" → Install
   # Or via command line:
   ./odoo-bin -d your_db -i ams_products_base
   ```

4. **Verify installation**:
   - Check that AMS products are auto-detected from categories
   - Verify member pricing calculations
   - Test digital content handling

## Quick Start

### 1. Create Enhanced Categories
First, ensure you have AMS categories set up in `ams_product_types`:

```python
# Example: Event category with member pricing
event_category = env['product.category'].create({
    'name': 'Conference Registrations',
    'is_ams_category': True,
    'ams_category_type': 'event',
    'requires_member_pricing': True,
    'member_discount_percent': 20.0,  # 20% member discount
})
```

### 2. Create AMS Products
Products automatically inherit from their category:

```python
# Create product - settings inherited from category
conference = env['product.template'].create({
    'name': 'Annual Conference 2024',
    'categ_id': event_category.id,
    'list_price': 399.00,
})

# Automatically has:
# - is_ams_product = True
# - member_price = 319.20 (20% discount)
# - requires_membership = False (from category)
```

### 3. Test Member Pricing
```python
# Get pricing for different partners
member_price = conference.get_price_for_partner(member_partner)      # $319.20
regular_price = conference.get_price_for_partner(non_member_partner) # $399.00

# Check purchase permissions
can_buy = conference.can_be_purchased_by_partner(partner)  # True/False
```

### 4. Digital Content
For digital products, simply add content:

```python
digital_course = env['product.template'].create({
    'name': 'Online Training Course',
    'categ_id': digital_category.id,  # is_digital_category = True
    'list_price': 99.00,
    'digital_url': 'https://learning.example.com/course-123',
})

# Check digital access
access_info = digital_course.get_digital_content_access(partner)
# Returns: {'is_digital': True, 'has_content': True, 'can_access': True, ...}
```

## Configuration

### Member Pricing Setup
Configure member discounts at the category level:

1. **Go to**: Inventory → Configuration → Product Categories
2. **Find** your AMS category
3. **Set**: `Member Discount Percent` (e.g., 15%)
4. **Products** in this category automatically get member pricing

### Digital Content Requirements
For digital categories, products must have either:
- `digital_url`: Download link
- `digital_attachment_id`: File attachment

### Membership Requirements
Categories with these settings require membership:
- `is_membership_category = True`
- `grants_portal_access = True`

## Usage Examples

### Creating Category-Specific Products

```python
# Membership product (inherits from membership category)
membership = env['product.template'].create({
    'name': 'Annual Individual Membership',
    'categ_id': membership_category.id,
    'list_price': 150.00,
    # Automatically: requires_membership = True, is_ams_product = True
})

# Event product (inherits from event category) 
workshop = env['product.template'].create({
    'name': 'Leadership Workshop',
    'categ_id': workshop_category.id,  # 25% member discount
    'list_price': 200.00,
    # Automatically: member_price = 150.00, requires_membership = False
})

# Digital product (inherits from digital category)
ebook = env['product.template'].create({
    'name': 'Industry Best Practices Guide',
    'categ_id': digital_category.id,
    'list_price': 29.99,
    'digital_url': 'https://downloads.example.com/guide.pdf',
    # Automatically: is_digital_product = True, has_digital_content = True
})
```

### Partner-Specific Pricing

```python
def get_cart_total(products, partner):
    """Calculate cart total with member pricing"""
    total = 0
    for product in products:
        price = product.get_price_for_partner(partner)
        total += price
    return total

# Usage
member_total = get_cart_total(cart_products, member_partner)    # Gets discounts
guest_total = get_cart_total(cart_products, non_member_partner) # Regular pricing
```

### Digital Content Access

```python
def deliver_digital_content(order_line):
    """Handle digital content delivery after purchase"""
    product = order_line.product_id.product_tmpl_id
    partner = order_line.order_id.partner_id
    
    access = product.get_digital_content_access(partner)
    if access['is_digital'] and access['can_access']:
        if access['download_url']:
            # Send download link email
            send_download_email(partner, access['download_url'])
        elif access['attachment_id']:
            # Attach file to email
            send_attachment_email(partner, access['attachment_id'])
```

### Query Methods for Reporting

```python
# Get all AMS products by category type
event_products = env['product.template'].get_ams_products_by_category_type('event')
digital_products = env['product.template'].get_digital_products()
member_pricing_products = env['product.template'].get_member_pricing_products()

# Get product variants with issues
low_stock_variants = env['product.product'].get_low_stock_ams_variants()
missing_content = env['product.product'].get_digital_content_missing_variants()
```

## API Reference

### ProductTemplate Methods

#### Core Integration Methods
```python
def get_price_for_partner(self, partner)
    """Get appropriate price based on partner's membership status"""
    
def can_be_purchased_by_partner(self, partner)  
    """Check if product can be purchased by the partner"""
    
def get_digital_content_access(self, partner=None)
    """Get digital content access information"""
```

#### Query Methods
```python
@api.model
def get_ams_products_by_category_type(self, category_type=None)
    """Get AMS products filtered by category type"""
    
@api.model  
def get_member_pricing_products(self)
    """Get all products that offer member pricing"""
    
@api.model
def get_digital_products(self)
    """Get all digital products"""
```

### ProductProduct Methods

#### Variant Methods
```python
def get_price_for_partner(self, partner)
    """Get variant price - delegates to template"""
    
def can_be_purchased_by_partner(self, partner)
    """Check variant purchase permissions"""
    
def get_member_savings_amount(self, partner)  
    """Calculate member savings for this variant"""
```

#### Query Methods
```python
@api.model
def get_ams_variants_by_category_type(self, category_type=None)
    """Get AMS variants by category type"""
    
@api.model
def get_low_stock_ams_variants(self, threshold=0)
    """Get low stock AMS variants"""
```

### Key Computed Fields

#### ProductTemplate
- `is_ams_product`: Auto-detected from category
- `member_price`: Calculated from category discount
- `member_savings`: Amount saved with member pricing
- `has_digital_content`: Whether digital content is available
- `requires_membership`: Whether membership is required
- `pricing_summary`: Human-readable pricing summary

#### ProductProduct  
- `effective_sku`: Variant or template SKU
- `availability_status`: Current availability status
- `template_*`: Related fields from template for easy access

## Integration Points

### With ams_member_data
- Uses `partner.is_member` and `partner.membership_status` for pricing
- Integrates with membership validation logic
- Respects membership lifecycle states

### With ams_product_types  
- Inherits all behavior from enhanced categories
- Uses category discount percentages for member pricing
- Respects category digital/inventory/subscription settings

### With Odoo Core Modules
- **Sales**: Provides partner-specific pricing methods
- **Inventory**: Respects product types and stock management  
- **Website**: Compatible with eCommerce member pricing
- **Accounting**: Works with standard invoicing and taxation

### Extension Points for Other Modules

#### ams_membership_products
```python
# Extend membership-specific logic
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    membership_duration = fields.Integer()  # Add membership-specific fields
    
    def create_membership_record(self, partner):
        """Create membership from product purchase"""
        if self.categ_id.is_membership_category:
            # Create membership record
            pass
```

#### ams_event_products
```python
# Extend event-specific logic  
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    event_id = fields.Many2one('event.event')  # Link to event
    
    def register_for_event(self, partner):
        """Register partner for event"""
        if self.categ_id.ams_category_type == 'event':
            # Create event registration
            pass
```

#### ams_subscription_products
```python
# Extend subscription-specific logic
class ProductTemplate(models.Model): 
    _inherit = 'product.template'
    
    subscription_template_id = fields.Many2one('sale.subscription.template')
    
    def create_subscription(self, partner):
        """Create subscription from product"""
        if self.categ_id.is_subscription_category:
            # Create subscription
            pass
```

## Troubleshooting

### Common Issues

#### Products Not Detected as AMS Products
**Problem**: `is_ams_product` is False  
**Solution**: Ensure product category has `is_ams_category = True`

#### Member Pricing Not Calculated
**Problem**: `member_price` equals `list_price`  
**Solutions**: 
- Check category has `requires_member_pricing = True`
- Verify `member_discount_percent` is set on category
- Ensure category discount is > 0

#### Digital Content Validation Errors
**Problem**: ValidationError on digital products  
**Solution**: Add either `digital_url` or `digital_attachment_id`

#### SKU Not Auto-Generated
**Problem**: `default_code` is empty  
**Solutions**:
- Ensure product name is provided during creation
- Check category `is_ams_category = True`
- Verify no existing `default_code` provided

### Performance Considerations

#### Large Product Catalogs
- Computed fields are stored for search performance
- Query methods use proper database indexes
- Category-based filtering is efficient

#### Member Pricing Calculations
- Member pricing computed on save, not on-demand
- Uses category-level discounts for consistency
- Pricing summaries cached for display

## Development

### Running Tests
```bash
# Run all AMS Products Base tests
./odoo-bin -d test_db --test-tags ams_products_base --stop-after-init

# Run specific test class
./odoo-bin -d test_db --test-tags ams_products_base.test_ams_products_base
```

### Code Structure
```
ams_products_base/
├── models/
│   ├── product_template.py      # Template extensions (main logic)
│   └── product_product.py       # Variant extensions (delegation)
├── views/
│   ├── product_template_views.xml # Clean template UI
│   └── product_product_views.xml  # Simple variant UI  
├── demo/
│   └── demo_ams_products.xml    # Example products & scenarios
└── tests/
    └── test_ams_products_base.py # Comprehensive test coverage
```

### Adding Custom Fields
Extend the base functionality for association-specific needs:

```python
# In your custom module
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Add association-specific fields
    ceu_credits = fields.Float(string="CEU Credits")
    accreditation_required = fields.Boolean(string="Requires Accreditation")
    
    @api.depends('categ_id.ams_category_type', 'ceu_credits')
    def _compute_grants_ceu(self):
        """Compute if product grants continuing education credits"""
        for product in self:
            product.grants_ceu = (
                product.categ_id.ams_category_type in ['education', 'certification'] 
                and product.ceu_credits > 0
            )
    
    grants_ceu = fields.Boolean(
        string="Grants CEU",
        compute='_compute_grants_ceu',
        store=True
    )
```

### Custom Category Behaviors
Add new category-driven behaviors:

```python
# In ams_product_types module extension
class ProductCategory(models.Model):
    _inherit = 'product.category'
    
    default_ceu_credits = fields.Float(string="Default CEU Credits")
    requires_accreditation = fields.Boolean(string="Requires Accreditation")

# In your product extension  
@api.onchange('categ_id')
def _onchange_categ_id_custom(self):
    """Apply custom category defaults"""
    super()._onchange_categ_id()
    if self.categ_id and self.categ_id.is_ams_category:
        self.ceu_credits = self.categ_id.default_ceu_credits
        self.accreditation_required = self.categ_id.requires_accreditation
```

## Contributing

### Guidelines
- Follow Odoo development best practices
- Maintain simplicity - leverage existing modules
- Add comprehensive tests for new functionality  
- Keep UI clean and focused on essentials
- Document integration points for other modules

### Pull Request Process
1. Create feature branch from main
2. Add/update tests for changes
3. Ensure all tests pass
4. Update documentation if needed
5. Submit pull request with clear description

## Changelog

### Version 1.0.0 - Initial Release
- Simplified integration layer design
- Category-driven product configuration
- Member pricing integration with ams_member_data
- Digital content handling with validation
- Comprehensive test coverage
- Clean UI focused on essentials
- Integration hooks for specialized modules

## License
LGPL-3

## Support
- **Documentation**: This README and inline code comments
- **Tests**: Comprehensive test suite in `tests/` directory
- **Demo Data**: Example products and scenarios in `demo/` directory
- **Issues**: Report bugs or feature requests via project issue tracker

For technical questions about extending this module or integrating with other AMS modules, refer to the API documentation above or examine the test cases for usage examples.