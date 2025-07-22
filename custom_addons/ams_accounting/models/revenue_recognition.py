from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AMSRevenueRecognition(models.Model):
    _name = 'ams.revenue.recognition'
    _description = 'AMS Revenue Recognition'
    _order = 'recognition_date desc'
    _rec_name = 'description'
    
    # Basic fields that don't depend on external models
    name = fields.Char('Name', compute='_compute_name', store=True)
    description = fields.Char('Description', required=True)
    recognition_date = fields.Date('Recognition Date', required=True)
    amount = fields.Float('Amount', required=True)
    
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('processed', 'Processed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='scheduled')
    
    # Company and currency - set directly, not as related fields
    company_id = fields.Many2one('res.company', 'Company', 
                                default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                 default=lambda self: self.env.company.currency_id, required=True)
    
    # Journal entry
    move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True)
    
    # Optional subscription reference (only if ams_subscriptions is available)
    subscription_id = fields.Many2one('ams.subscription', 'Subscription', ondelete='cascade')
    
    # Partner and product - can be set directly or computed
    partner_id = fields.Many2one('res.partner', 'Partner')
    product_id = fields.Many2one('product.product', 'Product')
    
    @api.depends('description', 'recognition_date')
    def _compute_name(self):
        for rec in self:
            if rec.description and rec.recognition_date:
                rec.name = f"{rec.description} - {rec.recognition_date}"
            elif rec.description:
                rec.name = rec.description
            else:
                rec.name = f"Revenue Recognition #{rec.id or 'New'}"
    
    def process_recognition(self):
        """Process the revenue recognition entry"""
        if self.state != 'scheduled':
            return
        
        # Basic processing - mark as processed
        self.write({'state': 'processed'})
        
        _logger.info(f"Revenue recognition processed: {self.name} - {self.amount}")
        
        return True
    
    def action_process(self):
        """Action to process this recognition entry"""
        self.process_recognition()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Revenue Recognized',
                'message': f'Revenue of {self.amount} has been recognized.',
                'type': 'success',
            }
        }
    
    def action_cancel(self):
        """Cancel this recognition entry"""
        if self.state == 'processed':
            raise UserError("Cannot cancel a processed revenue recognition entry.")
        
        self.state = 'cancelled'
    
    def action_view_journal_entry(self):
        """View the journal entry for this recognition"""
        if not self.move_id:
            raise UserError("No journal entry found for this recognition.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Revenue Recognition Entry',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }
    
    @api.model
    def cron_process_due_recognitions(self):
        """Cron job to process due revenue recognitions"""
        today = fields.Date.today()
        
        due_recognitions = self.search([
            ('state', '=', 'scheduled'),
            ('recognition_date', '<=', today)
        ])
        
        processed_count = 0
        for recognition in due_recognitions:
            try:
                recognition.process_recognition()
                processed_count += 1
            except Exception as e:
                _logger.error(f"Failed to process revenue recognition {recognition.id}: {str(e)}")
        
        _logger.info(f"Processed {processed_count} revenue recognition entries")
        return processed_count