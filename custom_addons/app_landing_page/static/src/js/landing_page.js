odoo.define('app_landing_page.landing_page', function (require) {
    'use strict';

    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var ajax = require('web.ajax');

    // Frontend Landing Page JavaScript
    $(document).ready(function() {
        // Handle app tile clicks (for frontend version)
        $('.app-tile').click(function() {
            var url = $(this).data('url');
            if (url && url !== '#') {
                window.location.href = url;
            }
        });

        // Handle backend app card clicks
        $('.app-card').click(function() {
            var menuId = $(this).data('menu-id');
            if (menuId) {
                // Navigate to the menu in Odoo backend
                window.location.href = '/web#menu_id=' + menuId;
            }
        });

        // Add click handler for launch buttons
        $('.app-launch-btn').click(function(e) {
            e.stopPropagation();
            var menuId = $(this).closest('.app-card').data('menu-id');
            if (menuId) {
                window.location.href = '/web#menu_id=' + menuId;
            }
        });
    });

    // Backend Action for integration with Odoo's action system
    var AppLandingPageAction = AbstractAction.extend({
        template: 'app_landing_page.landing_page_backend_template',

        init: function(parent, action) {
            this._super.apply(this, arguments);
            this.action = action;
        },

        start: function() {
            var self = this;
            return this._super().then(function() {
                return self._loadApps();
            });
        },

        _loadApps: function() {
            var self = this;
            return ajax.rpc('/web/dataset/call_kw', {
                model: 'ir.module.module',
                method: 'search_read',
                args: [[['state', '=', 'installed'], ['application', '=', true]]],
                kwargs: {
                    fields: ['name', 'shortdesc', 'summary', 'description']
                }
            }).then(function(apps) {
                self._renderApps(apps);
            });
        },

        _renderApps: function(apps) {
            var self = this;
            var appData = [];
            
            // Process each app and get menu information
            var menuPromises = apps.map(function(app) {
                return ajax.rpc('/web/dataset/call_kw', {
                    model: 'ir.ui.menu',
                    method: 'search_read',
                    args: [[['parent_id', '=', false], ['name', '=', app.shortdesc || app.name]]],
                    kwargs: {
                        fields: ['id', 'name'],
                        limit: 1
                    }
                }).then(function(menus) {
                    var menu = menus.length > 0 ? menus[0] : null;
                    return {
                        'name': app.shortdesc || app.name,
                        'technical_name': app.name,
                        'summary': app.summary || '',
                        'description': app.description || '',
                        'icon': self._getAppIcon(app.name),
                        'menu_id': menu ? menu.id : false,
                        'url': menu ? '/web#menu_id=' + menu.id : '#'
                    };
                });
            });

            Promise.all(menuPromises).then(function(processedApps) {
                // Re-render the template with the app data
                self.$el.html($(core.qweb.render('app_landing_page.landing_page_backend_template', {
                    apps: processedApps
                })));
                
                // Bind click events
                self._bindEvents();
            });
        },

        _getAppIcon: function(moduleName) {
            var iconMapping = {
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
                'mrp': 'fa-industry',
                'fleet': 'fa-truck',
                'calendar': 'fa-calendar',
                'contacts': 'fa-address-book',
                'mail': 'fa-envelope',
                'documents': 'fa-folder',
                'social': 'fa-share-alt',
                'survey': 'fa-list-alt',
                'im_livechat': 'fa-comments'
            };
            
            return iconMapping[moduleName] || 'fa-cube';
        },

        _bindEvents: function() {
            var self = this;
            
            // Handle app card clicks
            this.$('.app-card').click(function() {
                var menuId = $(this).data('menu-id');
                if (menuId) {
                    self.do_action({
                        type: 'ir.actions.client',
                        tag: 'menu',
                        params: {menu_id: menuId}
                    });
                }
            });

            // Handle launch button clicks
            this.$('.app-launch-btn').click(function(e) {
                e.stopPropagation();
                var menuId = $(this).closest('.app-card').data('menu-id');
                if (menuId) {
                    self.do_action({
                        type: 'ir.actions.client', 
                        tag: 'menu',
                        params: {menu_id: menuId}
                    });
                }
            });
        }
    });

    // Register the action
    core.action_registry.add('app_landing_page.action', AppLandingPageAction);

    return {
        AppLandingPageAction: AppLandingPageAction
    };
});

// Additional jQuery for enhanced interactions
$(document).ready(function() {
    // Add loading animation
    $('.app-tile, .app-card').on('click', function() {
        var $this = $(this);
        $this.addClass('loading');
        
        // Remove loading class after navigation
        setTimeout(function() {
            $this.removeClass('loading');
        }, 1000);
    });

    // Add keyboard navigation support
    $(document).on('keydown', function(e) {
        if (e.key === 'Enter' && $('.app-tile:focus, .app-card:focus').length) {
            $('.app-tile:focus, .app-card:focus').click();
        }
    });

    // Make tiles focusable for accessibility
    $('.app-tile, .app-card').attr('tabindex', '0');
});