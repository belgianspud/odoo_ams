# -*- coding: utf-8 -*-
#############################################################################
#
#    AMS Accounting - Asset Management Model
#    Complete asset management with depreciation for AMS organizations
#
#############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AccountAssetCategory(models.Model):
    """Asset categories with AMS-specific configurations"""
    _name = 'account.asset.category'
    _description = 'Asset Category'
    _order = 'name'

    name = fields.Char('Category Name', required=True, translate=True)
    code = fields.Char('Code', required=True, size=10)
    
    # Accounting Configuration
    account_asset_id = fields.Many2one(
        'account.account', 
        'Asset Account', 
        required=True,
        domain="[('account_type', '=', 'asset_non_current'), ('deprecated', '=', False)]"
    )
    account_depreciation_id = fields.Many2one(
        'account.account', 
        'Depreciation Account', 
        required=True,
        domain="[('account_type', '=', 'asset_non_current'), ('deprecated', '=', False)]"
    )
    account_depreciation_expense_id = fields.Many2one(
        'account.account', 
        'Expense Account', 
        required=True,
        domain="[('account_type', 'in', ('expense', 'expense_depreciation')), ('deprecated', '=', False)]"
    )
    
    # Journal Configuration
    journal_id = fields.Many2one(
        'account.journal', 
        'Asset Journal', 
        required=True,
        domain="[('type', '=', 'general')]"
    )
    
    # Default Depreciation Settings
    method = fields.Selection([
        ('linear', 'Linear'),
        ('degressive', 'Degressive'),
        ('accelerated', 'Accelerated Degressive'),
    ], string='Computation Method', required=True, default='linear',
    help="Choose the method to use to compute the amount of depreciation lines.")
    
    method_number = fields.Integer('Number of Depreciations', default=5,
        help="The number of depreciations needed to depreciate your asset")
    method_period = fields.Integer('Period Length', default=1,
        help="State here the time between 2 depreciations, in months")
    method_progress_factor = fields.Float('Degressive Factor', default=0.3,
        help="Choose an acceleration factor for the degressive method")
    method_time = fields.Selection([
        ('number', 'Number of Depreciations'),
        ('end', 'Ending Date'),
    ], string='Time Method', required=True, default='number',
    help="Choose the method to use to compute the dates and number of depreciation lines.")
    
    # Date Settings
    prorata = fields.Boolean('Prorata Temporis', default=True,
        help="Indicates that the first depreciation entry will be done from the purchase date instead of the first January")
    date_first_depreciation = fields.Selection([
        ('last_day_period', 'Based on Last Day of Purchase Period'),
        ('manual', 'Manual'),
    ], string='Assets Purchase Date', default='last_day_period', required=True)
    
    # Company
    company_id = fields.Many2one('res.company', 'Company', 
                                default=lambda self: self.env.company, required=True)
    
    # AMS Integration
    is_ams_category = fields.Boolean('AMS Asset Category', default=False,
        help="Mark this as an AMS-specific asset category")
    ams_chapter_ids = fields.Many2many('ams.chapter', 'asset_category_chapter_rel',
                                      'category_id', 'chapter_id', 'AMS Chapters',
                                      help="Chapters that can use this asset category")
    
    # Statistics
    asset_count = fields.Integer('Assets', compute='_compute_asset_count')
    
    @api.depends('asset_ids')
    def _compute_asset_count(self):
        for category in self:
            category.asset_count = self.env['account.asset.asset'].search_count([
                ('category_id', '=', category.id)
            ])
    
    def action_view_assets(self):
        """Action to view assets in this category"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} Assets',
            'res_model': 'account.asset.asset',
            'view_mode': 'tree,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id}
        }
    
    _sql_constraints = [
        ('code_unique', 'unique(code, company_id)', 'Asset category code must be unique per company!'),
    ]


class AccountAssetAsset(models.Model):
    """Asset management with AMS integration and enhanced depreciation"""
    _name = 'account.asset.asset'
    _description = 'Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, name'

    name = fields.Char('Asset Name', required=True, translate=True, tracking=True)
    code = fields.Char('Reference', tracking=True)
    category_id = fields.Many2one('account.asset.category', 'Asset Category', 
                                 required=True, tracking=True)
    
    # Financial Information
    value = fields.Float('Gross Value', required=True, tracking=True,
        help="Gross value of the asset")
    salvage_value = fields.Float('Salvage Value', tracking=True,
        help="Residual value of the asset at the end of its useful life")
    value_residual = fields.Float('Book Value', compute='_compute_residual_value', 
                                 store=True, help="Current book value of the asset")
    
    # Dates
    date = fields.Date('Date', required=True, default=fields.Date.today(), tracking=True,
        help="Date of asset acquisition")
    date_first_depreciation = fields.Date('First Depreciation Date', tracking=True,
        help="Date of the first depreciation")
    
    # Depreciation Configuration
    method = fields.Selection(related='category_id.method', store=True, readonly=False)
    method_number = fields.Integer('Number of Depreciations', 
                                  compute='_compute_method_number', store=True, readonly=False)
    method_period = fields.Integer('Period Length', 
                                  compute='_compute_method_period', store=True, readonly=False)
    method_progress_factor = fields.Float('Degressive Factor', 
                                         compute='_compute_method_progress_factor', store=True, readonly=False)
    method_time = fields.Selection(related='category_id.method_time', store=True, readonly=False)
    method_end = fields.Date('Ending Date')
    prorata = fields.Boolean(related='category_id.prorata', store=True, readonly=False)
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Running'),
        ('close', 'Closed'),
    ], string='Status', default='draft', tracking=True,
    help="When an asset is created, the status is 'Draft'.\n"
         "If the asset is confirmed, the status goes to 'Running' and the depreciation lines can be posted in the accounting.\n"
         "If the asset is sold or scrapped, the status becomes 'Closed'.")
    
    # Relationships
    depreciation_line_ids = fields.One2many('account.asset.depreciation.line', 'asset_id', 
                                           'Depreciation Lines', readonly=True, states={'draft': [('readonly', False)]})
    move_ids = fields.One2many('account.move', 'asset_id', 'Entries', readonly=True)
    
    # Accounts
    account_asset_id = fields.Many2one('account.account', 'Asset Account', 
                                      related='category_id.account_asset_id', store=True, readonly=True)
    account_depreciation_id = fields.Many2one('account.account', 'Depreciation Account',
                                             related='category_id.account_depreciation_id', store=True, readonly=True)
    account_depreciation_expense_id = fields.Many2one('account.account', 'Expense Account',
                                                     related='category_id.account_depreciation_expense_id', store=True, readonly=True)
    
    # Company and Currency
    company_id = fields.Many2one('res.company', 'Company', 
                                default=lambda self: self.env.company, required=True, readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    
    # AMS Integration
    ams_chapter_id = fields.Many2one('ams.chapter', 'AMS Chapter',
        help="Chapter that owns or manages this asset")
    ams_location = fields.Char('AMS Location',
        help="Physical location of the asset")
    ams_responsible_id = fields.Many2one('res.partner', 'AMS Responsible',
        help="Person responsible for this asset")
    
    # Asset Details
    asset_type = fields.Selection([
        ('equipment', 'Equipment'),
        ('furniture', 'Furniture'),
        ('vehicle', 'Vehicle'),
        ('building', 'Building'),
        ('technology', 'Technology'),
        ('other', 'Other')
    ], string='Asset Type', default='equipment')
    
    serial_number = fields.Char('Serial Number')
    manufacturer = fields.Char('Manufacturer')
    model = fields.Char('Model')
    warranty_end_date = fields.Date('Warranty End Date')
    
    # Computed Fields
    depreciation_count = fields.Integer('Depreciation Count', compute='_compute_depreciation_count', store=True)
    move_count = fields.Integer('Move Count', compute='_compute_move_count', store=True)
    depreciated_value = fields.Float('Depreciated Value', compute='_compute_residual_value', store=True)
    remaining_depreciation = fields.Float('Remaining Depreciation', compute='_compute_residual_value', store=True)
    
    @api.depends('category_id', 'category_id.method_number')
    def _compute_method_number(self):
        for asset in self:
            asset.method_number = asset.category_id.method_number

    @api.depends('category_id', 'category_id.method_period')
    def _compute_method_period(self):
        for asset in self:
            asset.method_period = asset.category_id.method_period

    @api.depends('category_id', 'category_id.method_progress_factor')
    def _compute_method_progress_factor(self):
        for asset in self:
            asset.method_progress_factor = asset.category_id.method_progress_factor
    
    @api.depends('depreciation_line_ids', 'depreciation_line_ids.depreciation_value', 'depreciation_line_ids.move_posted')
    def _compute_residual_value(self):
        for asset in self:
            posted_lines = asset.depreciation_line_ids.filtered('move_posted')
            depreciated_value = sum(posted_lines.mapped('depreciation_value'))
            asset.depreciated_value = depreciated_value
            asset.value_residual = asset.value - depreciated_value
            asset.remaining_depreciation = asset.value - asset.salvage_value - depreciated_value
    
    @api.depends('depreciation_line_ids')
    def _compute_depreciation_count(self):
        for asset in self:
            asset.depreciation_count = len(asset.depreciation_line_ids)
    
    @api.depends('move_ids')
    def _compute_move_count(self):
        for asset in self:
            asset.move_count = len(asset.move_ids)
    
    @api.onchange('category_id')
    def _onchange_category_id(self):
        """Update asset configuration when category changes"""
        if self.category_id:
            self.method = self.category_id.method
            self.method_number = self.category_id.method_number
            self.method_period = self.category_id.method_period
            self.method_progress_factor = self.category_id.method_progress_factor
            self.method_time = self.category_id.method_time
            self.prorata = self.category_id.prorata
            self.date_first_depreciation = self._get_first_depreciation_date()
    
    @api.onchange('date', 'category_id')
    def _onchange_date(self):
        """Update first depreciation date when asset date changes"""
        if self.date:
            self.date_first_depreciation = self._get_first_depreciation_date()
    
    def _get_first_depreciation_date(self):
        """Calculate first depreciation date"""
        if not self.date or not self.category_id:
            return False
        
        if self.category_id.date_first_depreciation == 'manual':
            return self.date
        else:
            # Last day of purchase period
            return self.date + relativedelta(day=31)
    
    def action_confirm(self):
        """Confirm the asset and generate depreciation lines"""
        for asset in self:
            if asset.state != 'draft':
                raise UserError(_('Asset must be in draft state to confirm.'))
            
            asset.state = 'open'
            asset._compute_board_amount()
            asset.message_post(body=_("Asset confirmed and depreciation schedule generated."))
    
    def action_close(self):
        """Close the asset"""
        for asset in self:
            asset.state = 'close'
            asset.message_post(body=_("Asset closed."))
    
    def action_revert_to_draft(self):
        """Revert asset to draft state"""
        for asset in self:
            if asset.move_ids:
                raise UserError(_('Cannot revert to draft: Asset has posted depreciation entries.'))
            asset.state = 'draft'
            asset.depreciation_line_ids.unlink()
            asset.message_post(body=_("Asset reverted to draft."))
    
    def _compute_board_amount(self):
        """Generate depreciation schedule"""
        self.ensure_one()
        
        # Clear existing lines in draft state
        self.depreciation_line_ids.filtered(lambda l: not l.move_posted).unlink()
        
        # Calculate depreciation
        depreciation_value = self.value - self.salvage_value
        
        if depreciation_value <= 0:
            return
        
        if self.method_time == 'number':
            number_of_depreciation = self.method_number
        else:
            # Calculate based on end date
            if not self.method_end:
                raise UserError(_('End date is required when using time method "Ending Date".'))
            months = self._get_months_between_dates(self.date_first_depreciation or self.date, self.method_end)
            number_of_depreciation = max(1, months // self.method_period)
        
        # Generate depreciation lines
        depreciation_date = self.date_first_depreciation or self.date
        
        for i in range(number_of_depreciation):
            if self.method == 'linear':
                amount = depreciation_value / number_of_depreciation
            elif self.method == 'degressive':
                # Degressive method calculation
                if i == 0:
                    amount = depreciation_value * self.method_progress_factor
                else:
                    remaining_value = depreciation_value - sum(self.depreciation_line_ids.mapped('depreciation_value'))
                    amount = remaining_value * self.method_progress_factor
                    # Switch to linear if remaining periods would result in higher amount
                    remaining_periods = number_of_depreciation - i
                    linear_amount = remaining_value / remaining_periods
                    amount = min(amount, linear_amount)
            else:  # accelerated
                # Accelerated degressive - similar to degressive but with different factor
                accelerated_factor = self.method_progress_factor * 1.5
                if i == 0:
                    amount = depreciation_value * accelerated_factor
                else:
                    remaining_value = depreciation_value - sum(self.depreciation_line_ids.mapped('depreciation_value'))
                    amount = remaining_value * accelerated_factor
                    remaining_periods = number_of_depreciation - i
                    linear_amount = remaining_value / remaining_periods
                    amount = min(amount, linear_amount)
            
            # Ensure we don't exceed remaining value
            total_depreciated = sum(self.depreciation_line_ids.mapped('depreciation_value'))
            if total_depreciated + amount > depreciation_value:
                amount = depreciation_value - total_depreciated
            
            if amount > 0:
                self.env['account.asset.depreciation.line'].create({
                    'asset_id': self.id,
                    'sequence': i + 1,
                    'name': f"{self.name} - {i + 1:02d}",
                    'depreciation_date': depreciation_date,
                    'depreciation_value': amount,
                    'remaining_value': self.value - total_depreciated - amount,
                })
                
                depreciation_date = depreciation_date + relativedelta(months=self.method_period)
    
    def _get_months_between_dates(self, date_from, date_to):
        """Calculate number of months between two dates"""
        return (date_to.year - date_from.year) * 12 + (date_to.month - date_from.month)
    
    def action_view_depreciation_lines(self):
        """View depreciation lines"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Depreciation Lines',
            'res_model': 'account.asset.depreciation.line',
            'view_mode': 'tree,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id}
        }
    
    def action_view_moves(self):
        """View related moves"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Journal Entries',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id}
        }


class AccountAssetDepreciationLine(models.Model):
    """Asset depreciation lines with enhanced posting capabilities"""
    _name = 'account.asset.depreciation.line'
    _description = 'Asset Depreciation Line'
    _order = 'asset_id, sequence'

    asset_id = fields.Many2one('account.asset.asset', 'Asset', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', required=True)
    name = fields.Char('Depreciation Name', required=True)
    
    # Depreciation Information
    depreciation_date = fields.Date('Depreciation Date', required=True)
    depreciation_value = fields.Float('Amount', required=True)
    remaining_value = fields.Float('Book Value After Depreciation', required=True)
    
    # State
    move_posted = fields.Boolean('Posted', default=False, readonly=True)
    move_id = fields.Many2one('account.move', 'Depreciation Entry', readonly=True)
    
    # Company and Currency
    company_id = fields.Many2one('res.company', related='asset_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='asset_id.currency_id', readonly=True)
    
    def create_move(self):
        """Create journal entry for depreciation"""
        self.ensure_one()
        
        if self.move_posted:
            raise UserError(_('This depreciation is already posted.'))
        
        if not self.asset_id.account_depreciation_expense_id or not self.asset_id.account_depreciation_id:
            raise UserError(_('Asset category must have depreciation accounts configured.'))
        
        # Create journal entry
        move_vals = {
            'date': self.depreciation_date,
            'ref': self.name,
            'asset_id': self.asset_id.id,
            'journal_id': self.asset_id.category_id.journal_id.id,
            'line_ids': [
                (0, 0, {
                    'name': self.name,
                    'account_id': self.asset_id.account_depreciation_expense_id.id,
                    'debit': self.depreciation_value,
                    'credit': 0.0,
                    'asset_id': self.asset_id.id,
                }),
                (0, 0, {
                    'name': self.name,
                    'account_id': self.asset_id.account_depreciation_id.id,
                    'debit': 0.0,
                    'credit': self.depreciation_value,
                    'asset_id': self.asset_id.id,
                }),
            ],
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        self.write({
            'move_id': move.id,
            'move_posted': True,
        })
        
        self.asset_id.message_post(
            body=_("Depreciation entry posted: %s") % move.name
        )
        
        return move
    
    def action_post_depreciation(self):
        """Post depreciation entry"""
        return self.create_move()
    
    def action_reverse_depreciation(self):
        """Reverse posted depreciation entry"""
        self.ensure_one()
        
        if not self.move_posted or not self.move_id:
            raise UserError(_('No posted depreciation entry to reverse.'))
        
        # Create reversal
        reversal = self.move_id._reverse_moves()
        
        self.write({
            'move_posted': False,
            'move_id': False,
        })
        
        self.asset_id.message_post(
            body=_("Depreciation entry reversed: %s") % reversal.name
        )
        
        return reversal
    
    @api.model
    def _cron_generate_depreciation_entries(self):
        """Cron job to automatically generate depreciation entries"""
        today = fields.Date.today()
        
        lines_to_post = self.search([
            ('depreciation_date', '<=', today),
            ('move_posted', '=', False),
            ('asset_id.state', '=', 'open')
        ])
        
        posted_count = 0
        for line in lines_to_post:
            try:
                line.create_move()
                posted_count += 1
            except Exception as e:
                _logger.error(f"Failed to post depreciation for asset {line.asset_id.name}: {str(e)}")
        
        _logger.info(f"Auto-posted {posted_count} depreciation entries")
        
        return posted_count


# Add asset_id field to account.move for tracking
class AccountMove(models.Model):
    _inherit = 'account.move'
    
    asset_id = fields.Many2one('account.asset.asset', 'Related Asset', readonly=True)