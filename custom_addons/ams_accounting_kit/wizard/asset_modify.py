from lxml import etree

from odoo import api, fields, models, _

# Odoo 18 compatibility: these functions were removed/moved
try:
    from odoo.addons.base.models.ir_ui_view import (
        transfer_field_to_modifiers, transfer_node_to_modifiers, transfer_modifiers_to_node,
    )
except ImportError:
    # Fallback functions for Odoo 18 compatibility
    def transfer_field_to_modifiers(field, modifiers, context=None, in_tree_view=False):
        """Fallback for removed function in Odoo 18"""
        if field.readonly:
            modifiers['readonly'] = True
        if field.required:
            modifiers['required'] = True
        if hasattr(field, 'invisible') and field.invisible:
            modifiers['invisible'] = True
    
    def transfer_node_to_modifiers(node, modifiers, context=None, in_tree_view=False):
        """Fallback for removed function in Odoo 18"""
        if node.get('invisible'):
            modifiers['invisible'] = node.get('invisible')
        if node.get('readonly'):
            modifiers['readonly'] = node.get('readonly')
        if node.get('required'):
            modifiers['required'] = node.get('required')
    
    def transfer_modifiers_to_node(modifiers, node):
        """Fallback for removed function in Odoo 18"""
        for modifier, value in modifiers.items():
            if value:
                node.set(modifier, str(value))


def setup_modifiers(node, field=None, context=None, in_tree_view=False):
    modifiers = {}
    if field is not None:
        transfer_field_to_modifiers(field, modifiers, context=context, in_tree_view=in_tree_view)
    transfer_node_to_modifiers(node, modifiers, context=context, in_tree_view=in_tree_view)
    transfer_modifiers_to_node(modifiers, node)


class AssetModify(models.TransientModel):
    _name = 'asset.modify'
    _description = 'Modify Asset'

    name = fields.Text(string='Reason', required=True)
    method_number = fields.Integer(string='Number of Depreciations', required=True)
    method_period = fields.Integer(string='Period Length')
    method_end = fields.Date(string='Ending date')
    asset_method_time = fields.Char(compute='_get_asset_method_time', string='Asset Method Time', readonly=True)

    @api.depends_context('active_id')
    def _get_asset_method_time(self):
        for record in self:
            if self.env.context.get('active_id'):
                asset = self.env['account.asset.asset'].browse(self.env.context.get('active_id'))
                record.asset_method_time = asset.method_time
            else:
                record.asset_method_time = False

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(AssetModify, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        asset_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        if active_model == 'account.asset.asset' and asset_id:
            asset = self.env['account.asset.asset'].browse(asset_id)
            doc = etree.XML(result['arch'])
            if asset.method_time == 'number' and doc.xpath("//field[@name='method_end']"):
                node = doc.xpath("//field[@name='method_end']")[0]
                node.set('invisible', '1')
                setup_modifiers(node, result['fields']['method_end'])
            elif asset.method_time == 'end' and doc.xpath("//field[@name='method_number']"):
                node = doc.xpath("//field[@name='method_number']")[0]
                node.set('invisible', '1')
                setup_modifiers(node, result['fields']['method_number'])
            result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

    @api.model
    def default_get(self, fields):
        res = super(AssetModify, self).default_get(fields)
        asset_id = self.env.context.get('active_id')
        if asset_id:
            asset = self.env['account.asset.asset'].browse(asset_id)
            if 'name' in fields:
                res.update({'name': asset.name})
            if 'method_number' in fields and asset.method_time == 'number':
                res.update({'method_number': asset.method_number})
            if 'method_period' in fields:
                res.update({'method_period': asset.method_period})
            if 'method_end' in fields and asset.method_time == 'end':
                res.update({'method_end': asset.method_end})
            res['asset_method_time'] = asset.method_time
        return res

    def modify(self):
        """ Modifies the duration of asset for calculating depreciation
        and maintains the history of old values, in the chatter.
        """
        asset_id = self.env.context.get('active_id', False)
        asset = self.env['account.asset.asset'].browse(asset_id)
        old_values = {
            'method_number': asset.method_number,
            'method_period': asset.method_period,
            'method_end': asset.method_end,
        }
        asset_vals = {
            'method_number': self.method_number,
            'method_period': self.method_period,
            'method_end': self.method_end,
        }
        asset.write(asset_vals)
        asset.compute_depreciation_board()
        tracked_fields = self.env['account.asset.asset'].fields_get(['method_number', 'method_period', 'method_end'])
        changes, tracking_value_ids = asset._mail_track(tracked_fields, old_values)
        if changes:
            asset.message_post(subject=_('Depreciation board modified'), body=self.name, tracking_value_ids=tracking_value_ids)
        return {'type': 'ir.actions.act_window_close'}