from odoo import http
from odoo.http import request

class LandingPageController(http.Controller):
    
    @http.route('/apps/landing', type='http', auth='user', website=True)
    def landing_page(self):
        # Get all installed apps (modules with application=True)
        apps = request.env['ir.module.module'].sudo().search([
            ('state', '=', 'installed'),
            ('application', '=', True)
        ])
        
        app_data = []
        for app in apps:
            # Get menu items for this app
            menus = request.env['ir.ui.menu'].sudo().search([
                ('parent_id', '=', False),
                ('name', '=', app.shortdesc or app.name)
            ], limit=1)
            
            app_info = {
                'name': app.shortdesc or app.name,
                'technical_name': app.name,
                'summary': app.summary or '',
                'description': app.description or '',
                'icon': self._get_app_icon(app.name),
                'menu_id': menus.id if menus else False,
                'url': f'/web#menu_id={menus.id}' if menus else '#'
            }
            app_data.append(app_info)
        
        return request.render('app_landing_page.landing_page_template', {
            'apps': app_data
        })
    
    def _get_app_icon(self, module_name):
        """Get the icon for a module"""
        # Default icons mapping for common modules
        icon_mapping = {
            'sale': 'fa-shopping-cart',
            'purchase': 'fa-shopping-bag',
            'account': 'fa-calculator',
            'stock': 'fa-cubes',
            'crm': 'fa-handshake-o',
            'project': 'fa-tasks',
            'hr': 'fa-users',
            'website': 'fa-globe',
            'point_of_sale': 'fa-credit-card',
            'manufacturing': 'fa-cogs',
            'inventory': 'fa-archive',
            'invoicing': 'fa-file-text',
        }
        
        return icon_mapping.get(module_name, 'fa-cube')