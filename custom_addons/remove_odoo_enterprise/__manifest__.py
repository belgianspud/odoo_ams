# Copyright 2018 Eska Yazılım ve Danışmanlık A.Ş (www.eskayazilim.com.tr)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Remove Odoo Enterprise",
    "summary": "Remove enterprise modules and setting items",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "author": "Eska, Onestein, Odoo Community Association (OCA)",
    "contributors": [
        "Benedito Monteiro (19.0 migration)",
    ],
    "website": "https://github.com/OCA/server-brand",
    "license": "AGPL-3",
    "depends": ["base_setup"],
    "data": ["views/res_config_settings_views.xml"],
    "installable": True,
    "auto_install": False,
    "application": False,
}
