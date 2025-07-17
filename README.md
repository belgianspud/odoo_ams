# Odoo AMS (Association Management System)

A customized Odoo Community Edition setup specifically designed for Association Management, featuring a clean, focused Apps interface without Enterprise promotional clutter.

## Overview

This project transforms Odoo Community Edition into a purpose-built Association Management System by:
- Filtering out irrelevant modules from the Apps menu
- Hiding Enterprise promotional cards and upgrade pressure
- Providing a clean, professional interface focused on association needs
- Maintaining full functionality of essential business modules

## Features

### **Clean Apps Interface**
- Only 21 carefully selected modules visible in Apps menu
- No Enterprise promotional cards or upgrade prompts
- Professional, distraction-free user experience

### **Included Modules**
The system includes these essential modules for association management:

**Core Business**
- Sales Management
- CRM (Customer/Member Relationship Management)
- Invoicing & Accounting
- Purchase Management
- Inventory Management

**Digital Presence**
- Website Builder
- eCommerce Platform
- Email Marketing
- SMS Marketing
- Live Chat Support

**Organization & Events**
- Project Management
- Event Management
- Calendar Integration
- Surveys & Feedback

**Communication & Data**
- Contact Management
- Discussion/Chat (Discuss)
- Data Management Tools
- Custom AMS Module Manager

## Installation

### Prerequisites
- Odoo Community Edition 18.0
- PostgreSQL database
- Python 3.11+
- Git

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/belgianspud/odoo_ams.git
   cd odoo_ams
   ```

2. **Install Odoo Community Edition:**
   ```bash
   # Follow Odoo Community installation guide for your OS
   # https://www.odoo.com/documentation/18.0/administration/on_premise/source.html
   ```

3. **Configure Odoo:**
   Create/update your `odoo.conf` file:
   ```ini
   [options]
   admin_passwd = your_admin_password
   db_host = localhost
   db_port = 5432
   db_user = odoo
   db_password = your_db_password
   addons_path = /path/to/odoo/addons,/path/to/odoo/odoo/addons,/path/to/custom_addons
   xmlrpc_port = 8069
   dbfilter = ^your_database_name$
   db_name = your_database_name
   list_db = False
   logfile = /path/to/odoo.log
   log_level = info
   ```

4. **Start Odoo:**
   ```bash
   python odoo-bin -c odoo.conf
   ```

5. **Install AMS Module Manager:**
   - Go to Apps menu
   - Enable Developer Mode (Settings → Activate Developer Mode)
   - Update Apps List
   - Search for "AMS Module Manager"
   - Click Install

## Project Structure

```
odoo_ams/
├── custom_addons/
│   └── ams_module_manager/
│       ├── __init__.py
│       ├── __manifest__.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── ir_module_module.py
│       ├── data/
│       │   └── ir_module_data.xml
│       └── views/
│           └── apps_menu_views.xml
├── odoo.conf
└── README.md
```

## How It Works

### AMS Module Manager
The custom `ams_module_manager` module provides intelligent filtering of the Odoo Apps menu by:

1. **Allow-List Filtering**: Only displays pre-approved modules relevant to association management
2. **Search Override**: Intercepts module search queries to apply filtering
3. **Web Interface Filter**: Filters the web-based Apps interface in real-time
4. **Logging**: Provides detailed logs for troubleshooting and monitoring

### Technical Implementation
- **Python Override**: Custom `ir.module.module` model inheritance
- **Domain Filtering**: Uses Odoo's domain syntax to filter module lists
- **Context-Aware**: Only applies filtering in Apps menu context
- **Flexible Configuration**: Easy to modify allowed modules list

## Configuration

### Adding/Removing Modules
To modify which modules appear in the Apps menu, edit the `ALLOWED_MODULES` list in:
`custom_addons/ams_module_manager/models/ir_module_module.py`

```python
ALLOWED_MODULES = [
    'sale_management',      # Sales
    'crm',                  # CRM
    'account',              # Invoicing
    # Add or remove module technical names here
]
```

### Temporarily Disable Filtering
To see all available modules (for configuration purposes), comment out the filtering logic in the search methods.

## Use Cases

This AMS setup is perfect for:

- **Community Organizations**: Managing members, events, and communications
- **Professional Associations**: Member services, certification tracking, events
- **Non-Profits**: Donor management, volunteer coordination, fundraising
- **Clubs & Societies**: Member engagement, event planning, communications
- **Educational Organizations**: Course management, member tracking, events

## Troubleshooting

### Common Issues

1. **Module Not Loading**: Check file permissions and Python imports
2. **Filtering Not Working**: Verify module upgrade and restart Odoo
3. **Missing Modules**: Check if module technical names are correct

### Debug Mode
Enable detailed logging by setting `log_level = debug` in odoo.conf to see filtering activity.

### Support
Check the logs for detailed filtering information:
```bash
tail -f /path/to/odoo.log | grep "AMS Module Manager"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under LGPL-3 - see the Odoo Community Edition license for details.

## Acknowledgments

- Built on Odoo Community Edition
- Leverages Odoo's modular architecture
- Community-driven development approach

## Version History

- **v1.0.0**: Initial release with 21-module AMS focus
- Clean Apps interface implementation
- Enterprise filtering functionality

---

**Ready to manage your association with a clean, professional interface!** 

For support or questions, please check the project issues on GitHub.