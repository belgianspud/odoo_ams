def post_load_hook(env):
    """
    Post-load hook to filter which modules appear in the Apps store
    """
    # List of modules that should be visible in the Apps store
    # Format: (technical_name, display_name)
    allowed_modules = [
        # Core Odoo modules
        ('sale', 'Sales'),
        ('sale_management', 'Sales'),
        ('account', 'Invoicing'),
        ('crm', 'CRM'),
        ('website', 'Website'),
        ('stock', 'Inventory'),
        ('purchase', 'Purchase'),
        ('point_of_sale', 'Point of Sale'),
        ('project', 'Project'),
        ('website_sale', 'eCommerce'),
        ('mass_mailing', 'Email Marketing'),
        ('website_slides', 'eLearning'),
        ('website_event', 'Events'),
        ('mail', 'Discuss'),
        ('contacts', 'Contacts'),
        ('calendar', 'Calendar'),
        ('im_livechat', 'Live Chat'),
        ('survey', 'Surveys'),
        ('mass_mailing_sms', 'SMS Marketing'),
        
        # Custom AMS modules
        ('ams_module_manager', 'AMS Module Manager'),
        ('data_recycle', 'Data Recycle'),
        ('marketing_card', 'Marketing Card'),
        ('ams_subscriptions', 'AMS Subscriptions'),
    ]
    
    # Extract just the technical names for filtering
    allowed_module_names = [module[0] for module in allowed_modules]
    
    try:
        # Get all modules
        all_modules = env['ir.module.module'].search([])
        
        # Hide modules that are not in the allowed list
        modules_to_hide = all_modules.filtered(
            lambda m: m.name not in allowed_module_names and m.state != 'uninstalled'
        )
        
        # Mark modules as to be excluded from Apps view
        for module in modules_to_hide:
            # We can't directly hide them, but we can mark them with a special category
            # or modify their summary to indicate they're hidden
            if not module.summary or 'Hidden' not in module.summary:
                try:
                    module.write({
                        'summary': f"Hidden - {module.summary or module.shortdesc or ''}"
                    })
                except Exception:
                    # Silently continue if we can't modify the module
                    continue
        
        # Ensure allowed modules are visible and have correct display names
        for tech_name, display_name in allowed_modules:
            module_records = all_modules.filtered(lambda m: m.name == tech_name)
            for module in module_records:
                try:
                    updates = {}
                    
                    # Remove 'Hidden' prefix if it exists
                    if module.summary and 'Hidden' in module.summary:
                        new_summary = module.summary.replace('Hidden - ', '')
                        updates['summary'] = new_summary
                    
                    # Update display name if it doesn't match
                    if module.shortdesc != display_name:
                        updates['shortdesc'] = display_name
                    
                    if updates:
                        module.write(updates)
                        
                except Exception:
                    continue
                    
    except Exception as e:
        # Log the error but don't fail the module installation
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning(f"Could not apply module filtering: {e}")
        pass