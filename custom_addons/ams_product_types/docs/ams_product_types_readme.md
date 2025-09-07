# AMS Product Types

A foundational module for the Association Management System (AMS) that provides product classification and categorization for all association products and services.

## Overview

The AMS Product Types module enables associations to define and classify different categories of products and services they offer. This includes memberships, events, educational content, publications, merchandise, certifications, and digital downloads. The module serves as a foundation for pricing, inventory, and billing systems.

## Features

### Product Classification
- **7 Core Categories**: Membership, Event, Education, Publication, Merchandise, Certification, Digital Download
- **Flexible Attributes**: Member pricing, subscription model, digital delivery, inventory tracking
- **Business Logic**: Smart defaults based on category selection
- **Extensible Design**: Easy to add new categories and attributes

### Product Attributes
- **Member Pricing Support**: Flag products that offer member vs non-member pricing
- **Subscription Products**: Identify recurring revenue products
- **Digital Products**: Track products delivered electronically
- **Inventory Requirements**: Configure which products need stock tracking

### Pre-configured Data
- **17+ Product Types**: Ready-to-use types covering common association offerings
- **Smart Defaults**: Category-based attribute defaults that make sense
- **Real-world Examples**: Based on actual association product catalogs

## Installation

### Prerequisites
- Odoo Community 18.0 or later
- No additional dependencies required

### Install Steps

1. **Copy Module**: Place the `ams_product_types` folder in your Odoo custom addons directory:
   ```
   /path/to/odoo/custom_addons/ams_product_types/
   ```

2. **Update Apps List**: In Odoo, go to Apps → Update Apps List

3. **Install Module**: Search for "AMS Product Types" and click Install

4. **Verify Installation**: Check that the module appears in Settings → Apps → Installed Apps

## Quick Start

### Accessing Product Types
1. Navigate to **Settings → Product Types**
2. Review the pre-configured product types
3. Customize existing types or create new ones as needed

### Basic Configuration
1. **Review Categories**: Ensure the pre-defined categories match your offerings
2. **Customize Attributes**: Adjust member pricing and subscription settings
3. **Set Inventory Rules**: Configure which products need inventory tracking
4. **Add Custom Types**: Create association-specific product classifications

## Product Categories

### Membership
Products related to membership fees and renewals:
- Annual/monthly membership dues
- Lifetime memberships
- Membership upgrades
- Student/senior discounts

**Default Attributes**: Subscription-based, no separate member pricing needed

### Event
Event-related products and registrations:
- Conference registrations
- Workshop tickets
- Webinar access
- Gala tickets

**Default Attributes**: Member pricing enabled, no inventory tracking

### Education
Educational content and training:
- Continuing education courses
- Online training modules
- Professional development
- Certification prep courses

**Default Attributes**: Member pricing, may require inventory for materials

### Publication
Published materials and subscriptions:
- Magazine subscriptions
- Technical manuals
- Research reports
- Newsletters

**Default Attributes**: Often subscription-based, inventory tracking for physical items

### Merchandise
Branded items and promotional materials:
- Apparel (shirts, hats, jackets)
- Promotional items (pens, mugs, bags)
- Professional accessories
- Gift items

**Default Attributes**: Member pricing, inventory tracking required

### Certification
Professional certifications and credentials:
- Certification exams
- Credential renewals
- Digital badges
- Continuing education credits

**Default Attributes**: Member pricing, digital delivery, no inventory

### Digital Download
Digital-only products:
- E-books and reports
- Software licenses
- Resource libraries
- Digital tools

**Default Attributes**: Member pricing, digital delivery, no inventory

## Pre-configured Product Types

### Membership Types
| Type | Code | Subscription | Description |
|------|------|-------------|-------------|
| Annual Membership | ANNUAL_MEMBERSHIP | Yes | Standard annual membership |
| Lifetime Membership | LIFETIME_MEMBERSHIP | No | One-time permanent membership |
| Student Membership | STUDENT_MEMBERSHIP | Yes | Discounted student rates |

### Event Types
| Type | Code | Member Pricing | Description |
|------|------|----------------|-------------|
| Conference Registration | CONFERENCE_REG | Yes | Major conference attendance |
| Workshop Registration | WORKSHOP_REG | Yes | Training workshops |
| Webinar Access | WEBINAR_ACCESS | Yes | Online webinar sessions |
| Gala Ticket | GALA_TICKET | Yes | Special event tickets |

### Education Types
| Type | Code | Digital | Description |
|------|------|---------|-------------|
| Continuing Education Course | CONT_ED_COURSE | No | Professional development |
| Online Course | ONLINE_COURSE | Yes | Self-paced learning |
| Consulting Services | CONSULTING | No | Professional advisory |

### Publication Types
| Type | Code | Subscription | Description |
|------|------|-------------|-------------|
| Magazine Subscription | MAGAZINE_SUB | Yes | Physical publication |
| Digital Publication | DIGITAL_PUB | Yes | Digital-only access |
| Technical Manual | TECH_MANUAL | No | Reference materials |

### Merchandise Types
| Type | Code | Inventory | Description |
|------|------|-----------|-------------|
| Apparel | APPAREL | Yes | Branded clothing |
| Promotional Items | PROMO_ITEMS | Yes | Marketing materials |

### Certification Types
| Type | Code | Digital | Description |
|------|------|---------|-------------|
| Professional Certification | PROF_CERT | Yes | Credential exams |
| Certification Renewal | CERT_RENEWAL | Yes | Renewal fees |

### Digital Types
| Type | Code | Subscription | Description |
|------|------|-------------|-------------|
| Digital Resource | DIGITAL_RESOURCE | No | Downloadable materials |
| Software License | SOFTWARE_LICENSE | Yes | Licensed software |
| E-Book | EBOOK | No | Digital publications |
| Member Directory Access | MEMBER_DIRECTORY | Yes | Online directory |

## Usage Examples

### Creating a Custom Product Type

```python
# Create a new product type for consulting services
consulting_type = env['ams.product.type'].create({
    'name': 'Strategic Consulting',
    'code': 'STRATEGIC_CONSULTING',
    'category': 'education',
    'description': 'High-level strategic planning and advisory services',
    'requires_member_pricing': True,
    'is_subscription': False,
    'is_digital': False,
    'requires_inventory': False,
})
```

### Using Category-based Defaults

```python
# Create new type and let category set defaults
workshop_type = env['ams.product.type'].new({
    'name': 'Advanced Workshop',
    'category': 'event'
})

# Trigger onchange to set defaults
workshop_type._onchange_category()

# Result: requires_member_pricing=True, is_subscription=False, 
# is_digital=False, requires_inventory=False
```

### Filtering Product Types

```python
# Get all digital product types
digital_types = env['ams.product.type'].get_digital_types()

# Get types by category
membership_types = env['ams.product.type'].get_types_by_category('membership')

# Get subscription products
subscription_types = env['ams.product.type'].get_subscription_types()

# Get types that support member pricing
member_pricing_types = env['ams.product.type'].get_member_pricing_types()
```

### Getting Product Type Summary

```python
product_type = env.ref('ams_product_types.product_type_conference_registration')
summary = product_type.get_type_summary()
# Returns: "Category: Event • Member Pricing • Physical"
```

## Configuration

### Basic Configuration

**Name & Code**
- **Name**: Human-readable display name
- **Code**: Unique identifier (auto-generated from name)

**Category**
- **Primary Classification**: One of 7 core categories
- **Affects Defaults**: Automatically sets appropriate attribute defaults

**Status**
- **Active**: Whether type is available for new products

### Attribute Configuration

**Member Pricing**
- Enable for products with member vs non-member pricing
- Disabled by default for membership products (members already get membership pricing)

**Subscription Products**
- Enable for recurring revenue products
- Affects billing cycles and renewal processes

**Digital Products**
- Enable for electronically delivered products
- Automatically disables inventory tracking

**Inventory Tracking**
- Enable for physical products requiring stock management
- Automatically disabled for digital products

### Smart Defaults by Category

| Category | Member Pricing | Subscription | Digital | Inventory |
|----------|----------------|-------------|---------|-----------|
| Membership | No | Yes | No | No |
| Event | Yes | No | No | No |
| Education | Yes | No | No | Yes |
| Publication | Yes | Yes | No | Yes |
| Merchandise | Yes | No | No | Yes |
| Certification | Yes | No | Yes | No |
| Digital | Yes | No | Yes | No |

## API Reference

### ams.product.type

#### Methods

**get_type_summary()**
- Get human-readable summary of product type attributes
- Returns: string

**get_types_by_category(category=None)**
- Get product types filtered by category
- Returns: recordset

**get_digital_types()** (static)
- Get all digital product types
- Returns: recordset

**get_subscription_types()** (static)
- Get all subscription product types
- Returns: recordset

**get_member_pricing_types()** (static)
- Get types that support member pricing
- Returns: recordset

**action_view_products()**
- Open view of products using this type
- Returns: action dictionary

**action_create_product()**
- Create new product with this type's defaults
- Returns: action dictionary

**toggle_active()**
- Toggle active status

#### Fields

**Core Fields**
- `name` (Char): Product type name
- `code` (Char): Unique code
- `category` (Selection): Primary category
- `description` (Text): Detailed description
- `active` (Boolean): Is active

**Attributes**
- `requires_member_pricing` (Boolean): Supports member pricing
- `is_subscription` (Boolean): Is recurring product
- `is_digital` (Boolean): Digital delivery
- `requires_inventory` (Boolean): Needs inventory tracking

**Odoo Integration**
- `product_category_id` (Many2one): Default Odoo product category
- `default_uom_id` (Many2one): Default unit of measure

**Computed**
- `product_count` (Integer): Number of products using this type
- `category_display` (Char): Human-readable category name

### product.template (Extended)

#### AMS Methods

**get_member_price()**
- Get member price or regular price if no member pricing
- Returns: float

**get_price_for_member_type(is_member=False)**
- Get price based on member status
- Args: is_member (bool)
- Returns: float

**get_products_by_ams_category(category)** (static)
- Get products by AMS category
- Args: category (str)
- Returns: recordset

**action_view_ams_product_type()**
- Open associated AMS product type form
- Returns: action dictionary

#### AMS Fields

**Classification**
- `ams_product_type_id` (Many2one): AMS product type
- `ams_category` (Selection): AMS category (related)
- `is_digital` (Boolean): Digital product (related)
- `requires_member_pricing` (Boolean): Member pricing (related)
- `is_subscription` (Boolean): Subscription product (related)

**Member Pricing**
- `member_list_price` (Float): Member price
- `member_standard_price` (Float): Member cost

#### Constraints

**Code Format**
- Only alphanumeric, underscore, hyphen allowed
- Maximum 20 characters
- Must be unique

**Name Uniqueness**
- Product type names must be unique

## Data Management

### Importing Product Types

```xml
<record id="custom_product_type" model="ams.product.type">
    <field name="name">Custom Product</field>
    <field name="code">CUSTOM</field>
    <field name="category">merchandise</field>
    <field name="requires_member_pricing">True</field>
    <field name="is_subscription">False</field>
    <field name="is_digital">False</field>
    <field name="requires_inventory">True</field>
</record>
```

### CSV Import Format

```csv
name,code,category,requires_member_pricing,is_subscription,is_digital,requires_inventory
Custom Training,CUSTOM_TRAINING,education,True,False,True,False
Premium Support,PREMIUM_SUPPORT,education,True,True,False,False
```

## Integration

### With Other AMS Modules

This module provides foundation data for:
- **ams_billing_core**: Product pricing and member discounts
- **ams_inventory**: Inventory tracking for physical products
- **ams_portal_core**: Digital product access and downloads
- **ams_events**: Event registration products
- **ams_membership_lifecycle**: Membership renewal products

### Extension Points

**Custom Categories**
- Add new categories to the selection field
- Implement category-specific business logic

**Additional Attributes**
- Inherit model to add association-specific attributes
- Create computed fields for complex business rules

**Integration Fields**
- Add Many2one fields linking to other system objects
- Create related fields for enhanced functionality

## Troubleshooting

### Common Issues

**Product Type Not Appearing**
- Check that `active` field is True
- Verify category is correctly set
- Ensure code is unique and properly formatted

**Category Defaults Not Working**
- Trigger `_onchange_category()` method manually
- Check that category is in the onchange method logic
- Verify no custom logic is overriding defaults

**Validation Errors**
- Code format: only alphanumeric, underscore, hyphen allowed
- Code length: maximum 20 characters
- Uniqueness: names and codes must be unique

### Performance Considerations

**Product Count Fields**
- Computed on-demand when product model is available
- Consider caching for high-traffic installations

**Category Filtering**
- Uses database indexes on category field
- Efficient for large product type datasets

## Development

### Running Tests

```bash
# Run all tests for this module
./odoo-bin -d test_db -i ams_product_types --test-enable --stop-after-init

# Run specific test class
./odoo-bin -d test_db --test-tags ams_product_types.test_product_types
```

### Code Structure

```
ams_product_types/
├── __init__.py                 # Package initialization
├── __manifest__.py            # Module definition
├── models/
│   ├── __init__.py           # Model imports
│   └── product_type.py       # Product type model
├── views/
│   └── product_type_views.xml # Views and actions
├── data/
│   └── product_type_data.xml # Default product types
├── security/
│   └── ir.model.access.csv   # Access control rules
└── tests/
    └── test_product_types.py # Unit tests
```

## Contributing

### Code Standards
- Follow Odoo development guidelines
- Include comprehensive docstrings
- Add unit tests for new functionality
- Validate with pylint and odoo-lint

### Adding New Categories
1. Add to category selection field
2. Update `_onchange_category()` method with defaults
3. Add test cases for new category
4. Update documentation

## License

LGPL-3

## Support

For issues and questions:
- Check existing GitHub issues
- Review troubleshooting section above
- Contact development team for custom requirements

## Changelog

### Version 1.0.0
- Initial release
- Complete product type classification system
- 17 pre-configured product types across 7 categories
- Smart category-based defaults
- Comprehensive validation and business rules
- Full test coverage
- Integration-ready design