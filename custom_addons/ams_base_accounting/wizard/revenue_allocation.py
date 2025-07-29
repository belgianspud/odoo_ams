from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class RevenueAllocation(models.TransientModel):
    """Wizard to allocate revenue across chapters or categories"""
    _name = 'ams.revenue.allocation'
    _description = 'Revenue Allocation Wizard'
    
    allocation_type = fields.Selection([
        ('category', 'Allocate by Category'),
        ('custom', 'Custom Allocation'),
    ], string='Allocation Type', required=True, default='category')
    
    total_amount = fields.Monetary(
        string='Total Amount to Allocate',
        required=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
    
    allocation_date = fields.Date(
        string='Allocation Date',
        required=True,
        default=fields.Date.today
    )
    
    description = fields.Text(
        string='Description',
        required=True,
        help="Describe the reason for this revenue allocation"
    )
    
    # Allocation lines
    allocation_line_ids = fields.One2many(
        'ams.revenue.allocation.line',
        'allocation_id',
        string='Allocation Lines'
    )
    
    @api.model
    def default_get(self, fields_list):
        """Set default allocation lines based on type"""
        result = super().default_get(fields_list)
        
        if 'allocation_line_ids' in fields_list:
            allocation_type = result.get('allocation_type', 'category')
            lines = []
            
            if allocation_type == 'category':
                # Create lines for all revenue categories
                categories = self.env['ams.revenue.category'].search([('active', '=', True)])
                for category in categories:
                    lines.append((0, 0, {
                        'revenue_category_id': category.id,
                        'percentage': 0.0,
                        'amount': 0.0,
                    }))
            
            result['allocation_line_ids'] = lines
        
        return result
    
    @api.onchange('total_amount', 'allocation_line_ids.percentage')
    def _onchange_calculate_amounts(self):
        """Calculate amounts based on percentages"""
        for line in self.allocation_line_ids:
            line.amount = (line.percentage / 100.0) * self.total_amount
    
    def action_allocate_revenue(self):
        """Execute the revenue allocation"""
        self.ensure_one()
        
        # Validate allocation
        self._validate_allocation()
        
        # Create financial transactions for each allocation
        transactions = []
        for line in self.allocation_line_ids.filtered(lambda l: l.amount > 0):
            transaction_vals = {
                'name': f"Revenue Allocation: {self.description}",
                'date': self.allocation_date,
                'amount': line.amount,
                'transaction_type': 'income',
                'revenue_category_id': line.revenue_category_id.id,
                'state': 'confirmed',
                'notes': f"Allocated from total: {self.total_amount} ({line.percentage}%)",
            }
            transaction = self.env['ams.financial.transaction'].create(transaction_vals)
            transactions.append(transaction)
        
        # Return action to view created transactions
        return {
            'type': 'ir.actions.act_window',
            'name': 'Allocated Revenue Transactions',
            'res_model': 'ams.financial.transaction',
            'view_mode': 'list,form',
            'domain': [('id', 'in', [t.id for t in transactions])],
        }
    
    def _validate_allocation(self):
        """Validate the allocation before processing"""
        if not self.allocation_line_ids:
            raise UserError(_("Please add at least one allocation line"))
        
        total_percentage = sum(self.allocation_line_ids.mapped('percentage'))
        if abs(total_percentage - 100.0) > 0.01:  # Allow small rounding differences
            raise UserError(_("Total allocation percentage must equal 100%% (currently: %.2f%%)") % total_percentage)
        
        total_amount = sum(self.allocation_line_ids.mapped('amount'))
        if abs(total_amount - self.total_amount) > 0.01:
            raise UserError(_("Sum of allocation amounts must equal total amount"))

class RevenueAllocationLine(models.TransientModel):
    """Lines for revenue allocation wizard"""
    _name = 'ams.revenue.allocation.line'
    _description = 'Revenue Allocation Line'
    
    allocation_id = fields.Many2one('ams.revenue.allocation', required=True, ondelete='cascade')
    
    # Removed chapter_id reference since ams.chapter doesn't exist
    # chapter_id = fields.Many2one('ams.chapter', string='Chapter')
    revenue_category_id = fields.Many2one('ams.revenue.category', string='Revenue Category')
    
    percentage = fields.Float(
        string='Percentage (%)',
        required=True,
        help="Percentage of total amount to allocate to this item"
    )
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        help="Calculated amount based on percentage"
    )
    currency_id = fields.Many2one(
        related='allocation_id.currency_id',
        store=True
    )
    
    @api.onchange('percentage')
    def _onchange_percentage(self):
        """Calculate amount when percentage changes"""
        if self.allocation_id:
            self.amount = (self.percentage / 100.0) * self.allocation_id.total_amount
    
    @api.onchange('amount')
    def _onchange_amount(self):
        """Calculate percentage when amount changes"""
        if self.allocation_id and self.allocation_id.total_amount:
            self.percentage = (self.amount / self.allocation_id.total_amount) * 100.0