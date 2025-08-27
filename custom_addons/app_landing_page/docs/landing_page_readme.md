# Odoo App Landing Page - Installation Guide

## Overview
This module creates a beautiful landing page displaying all installed Odoo apps in an attractive tile format. Users can click on tiles to navigate directly to the respective applications.

## Installation Steps

### 1. Create Module Directory Structure
Create the following directory structure in your Odoo addons path:

```
addons/
└── app_landing_page/
    ├── __init__.py
    ├── __manifest__.py
    ├── controllers/
    │   ├── __init__.py
    │   └── main.py
    ├── models/
    │   └── __init__.py
    ├── security/
    │   └── ir.model.access.csv
    ├── static/
    │   ├── description/
    │   │   └── icon.png
    │   └── src/
    │       ├── css/
    │       │   └── landing_page.css
    │       └── js/
    │           └── landing_page.js
    └── views/
        ├── landing_page_views.xml
        └── landing_page_templates.xml
```

### 2. Create Required Files

#### Create `__init__.py` files:
```python
# app_landing_page/__init__.py
from . import controllers
from . import models

# app_landing_page/controllers/__init__.py  
from . import main

# app_landing_page/models/__init__.py
# Empty file
```

### 3. Add Module Icon
Add an icon file at `static/description/icon.png` (128x128 pixels recommended).

### 4. Install the Module

1. **Restart Odoo server** to recognize the new module
2. **Update App List**: Go to Apps → Update Apps List
3. **Install Module**: Search for "App Landing Page" and click Install

## Usage Options

### Option 1: Standalone Landing Page
- Visit `/apps/landing` in your browser
- This creates a full-page experience outside the standard Odoo interface

### Option 2: Menu Integration
- After installation, you'll see "App Dashboard" in the main menu
- Click on it to access the landing page within Odoo's interface

### Option 3: Set as Home Page
To make this the default landing page when users log in:

1. Go to Settings → Technical → Actions → Window Actions
2. Create a new action:
   - **Name**: App Landing Page
   - **Type**: URL Action  
   - **URL**: `/apps/landing`
   - **Target**: Self
3. Go to Settings → Users & Companies → Users
4. Edit user profiles and set **Action** to your new "App Landing Page" action

## Customization

### Adding Custom Icons
Edit the `_get_app_icon()` method in `controllers/main.py` to add icons for your custom modules:

```python
icon_mapping = {
    'your_custom_module': 'fa-your-icon',
    # Add more mappings here
}
```

### Styling Modifications
Edit `static/src/css/landing_page.css` to customize colors, layout, or animations.

### Template Customization
Modify `views/landing_page_templates.xml` to change the HTML structure or add additional information.

## Features

- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Hover Effects**: Interactive animations when hovering over app tiles
- **Accessibility**: Keyboard navigation support
- **FontAwesome Icons**: Uses FontAwesome icons for app representation
- **Click Navigation**: Direct navigation to apps with single clicks
- **Backend Integration**: Seamless integration with Odoo's menu system

## Troubleshooting

### Module Not Appearing
- Ensure all files are in the correct directory structure
- Restart Odoo server completely
- Update the Apps List from Apps menu
- Check Odoo logs for any import errors

### Icons Not Showing
- Verify FontAwesome is loaded (it's included with Odoo by default)
- Check that icon class names in `_get_app_icon()` are correct
- Ensure CSS file is properly loaded

### Navigation Not Working
- Check that menu IDs are being found correctly
- Verify user has access permissions to the target applications
- Check browser console for JavaScript errors

## Advanced Configuration

### Custom App Information
You can extend the controller to show additional app information by modifying the `app_info` dictionary in `controllers/main.py`.

### Integration with Website Module
If you have the Website module installed, the landing page will automatically use Odoo's website layout for better integration.

### Performance Optimization
For installations with many modules, consider adding caching to the controller to improve page load times.

## Support
This module is designed for Odoo Community Edition 18.0. For issues or customizations, check the module code and adapt as needed for your specific requirements.