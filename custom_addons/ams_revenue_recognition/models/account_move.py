# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    """Extend Account Move to integrate with AMS Revenue Recognition"""
    _inherit = 'account.move'
    
    # Revenue Recognition Fields
    revenue_schedule_ids = fields.One2many(
        'ams.revenue.schedule',
        'invoice_id',
        string='Revenue Recognition Schedules',
        help='Revenue recognition schedules created from this invoice'
    )
    
    has_revenue_recognition = fields.Boolean(
        string='Has Revenue Recognition',
        compute='_compute_revenue_recognition_status',
        store=True,
        help='This invoice has revenue recognition schedules'
    )
    
    total_deferred_revenue = fields.Monetary(
        string='Total Deferred Revenue',
        compute='_compute_revenue_recognition_amounts',
        search='_search_total_deferred_revenue',
        currency_field='currency_id',
        store=True,
        help='Total deferred revenue from this invoice'
    )
    
    total_recognized_revenue = fields.Monetary(
        string='Total Recognized Revenue',
        compute='_compute_revenue_recognition_amounts',
        search='_search_total_recognized_revenue',
        currency_field='currency_id', 
        store=True,
        help='Total recognized revenue from this invoice'
    )
    
    revenue_recognition_status = fields.Selection([
        ('none', 'No Recognition Required'),
        ('pending', 'Recognition Schedules Pending'),
        ('active', 'Recognition Active'),
        ('completed', 'Recognition Completed'),
    ], string='Revenue Recognition Status',
    compute='_compute_revenue_recognition_status',
    store=True,
    help='Overall revenue recognition status for this invoice')

    # Search methods for computed fields
    def _search_total_deferred_revenue(self, operator, value):
        """Search method for total_deferred_revenue computed field"""
        schedules = self.env['ams.revenue.schedule'].search([
            ('deferred_amount', operator, value)
        ])
        return [('id', 'in', schedules.mapped('invoice_id').ids)]
    
    def _search_total_recognized_revenue(self, operator, value):
        """Search method for total_recognized_revenue computed field"""
        schedules = self.env['ams.revenue.schedule'].search([
            ('recognized_amount', operator, value)
        ])
        return [('id', 'in', schedules.mapped('invoice_id').ids)]

    @api.depends('revenue_schedule_ids')
    def _compute_revenue_recognition_status(self):
        """Compute revenue recognition status"""
        for move in self:
            schedules = move.revenue_schedule_ids
            
            if not schedules:
                # Check if any lines need revenue recognition
                needs_recognition = any(
                    line.product_id.is_subscription_product and 
                    line.product_id.use_ams_accounting and
                    line.product_id.revenue_recognition_method != 'immediate'
                    for line in move.invoice_line_ids
                )
                
                move.has_revenue_recognition = False
                move.revenue_recognition_status = 'pending' if needs_recognition else 'none'
            else:
                move.has_revenue_recognition = True
                
                # Analyze schedule states
                active_schedules = schedules.filtered(lambda s: s.state == 'active')
                completed_schedules = schedules.filtered(lambda s: s.state == 'completed')
                draft_schedules = schedules.filtered(lambda s: s.state == 'draft')
                
                if active_schedules:
                    move.revenue_recognition_status = 'active'
                elif completed_schedules and not active_schedules and not draft_schedules:
                    move.revenue_recognition_status = 'completed'
                else:
                    move.revenue_recognition_status = 'pending'
    
    @api.depends('revenue_schedule_ids.deferred_amount', 'revenue_schedule_ids.recognized_amount')
    def _compute_revenue_recognition_amounts(self):
        """Compute revenue recognition amounts"""
        for move in self:
            move.total_deferred_revenue = sum(move.revenue_schedule_ids.mapped('deferred_amount'))
            move.total_recognized_revenue = sum(move.revenue_schedule_ids.mapped('recognized_amount'))
    
    def _post(self, soft=True):
        """Override posting to handle revenue recognition schedule creation"""
        # FIXED: Add safety checks and better error handling
        result = super()._post(soft=soft)
        
        # Process AMS revenue recognition for posted invoices
        # FIXED: Add try/catch to prevent interference with other operations
        for move in self.filtered(lambda m: m.move_type == 'out_invoice' and m.state == 'posted'):
            try:
                # FIXED: Only process if we're in a safe context (not during payment operations)
                if not self.env.context.get('skip_revenue_recognition', False):
                    move._process_ams_revenue_recognition()
            except Exception as e:
                # FIXED: Log error but don't fail the posting operation
                move.message_post(
                    body=_('Warning: Revenue recognition processing failed: %s') % str(e),
                    message_type='comment'
                )
        
        return result
    
    def _process_ams_revenue_recognition(self):
        """Process revenue recognition for AMS subscription products"""
        self.ensure_one()
        
        # FIXED: Add safety checks
        if self.move_type != 'out_invoice' or self.state != 'posted':
            return
        
        # FIXED: Skip if already processed or in unsafe context
        if (self.env.context.get('skip_revenue_recognition', False) or 
            self.env.context.get('payment_processing', False)):
            return
        
        created_schedules = self.env['ams.revenue.schedule']
        
        # Process each invoice line with error handling
        for line in self.invoice_line_ids:
            try:
                if not line.product_id:
                    continue
                
                product_template = line.product_id.product_tmpl_id
                
                # Check if this product needs revenue recognition
                if not self._line_needs_revenue_recognition(line):
                    continue
                
                # Check if schedule already exists
                existing_schedule = self.env['ams.revenue.schedule'].search([
                    ('invoice_line_id', '=', line.id)
                ], limit=1)
                
                if existing_schedule:
                    continue  # Schedule already exists
                
                # Create revenue recognition schedule
                schedule = product_template.create_recognition_schedule(line)
                if schedule:
                    created_schedules |= schedule
                    
            except Exception as e:
                # FIXED: Log error but continue with other lines
                self.message_post(
                    body=_('Error creating revenue recognition schedule for line %s: %s') % (line.id, str(e)),
                    message_type='comment'
                )
        
        # Log creation of schedules
        if created_schedules:
            self.message_post(
                body=_('Created %d revenue recognition schedule(s)') % len(created_schedules)
            )
        
        return created_schedules
    
    def _line_needs_revenue_recognition(self, line):
        """Check if an invoice line needs revenue recognition"""
        if not line.product_id:
            return False
        
        product_template = line.product_id.product_tmpl_id
        
        # Must be subscription product
        if not product_template.is_subscription_product:
            return False
        
        # Must have AMS accounting enabled
        if not product_template.use_ams_accounting:
            return False
        
        # Must have auto-create recognition enabled
        if not getattr(product_template, 'auto_create_recognition', False):
            return False
        
        # Must not be immediate recognition (immediate doesn't need schedules)
        if getattr(product_template, 'revenue_recognition_method', 'immediate') == 'immediate':
            return False
        
        return True
    
    def action_create_revenue_recognition_schedules(self):
        """Manual action to create revenue recognition schedules"""
        self.ensure_one()
        
        if self.state != 'posted':
            raise UserError(_('Invoice must be posted before creating revenue recognition schedules'))
        
        # FIXED: Set context to prevent interference
        schedules = self.with_context(skip_revenue_recognition=False)._process_ams_revenue_recognition()
        
        if schedules:
            return {
                'name': 'Created Revenue Recognition Schedules',
                'type': 'ir.actions.act_window',
                'res_model': 'ams.revenue.schedule',
                'view_mode': 'list,form',
                'domain': [('id', 'in', schedules.ids)],
                'context': {'search_default_group_by_product': 1},
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No revenue recognition schedules created. Schedules may already exist or products may not require recognition.',
                    'type': 'info',
                }
            }
    
    def action_view_revenue_schedules(self):
        """View revenue recognition schedules for this invoice"""
        self.ensure_one()
        
        return {
            'name': _('Revenue Recognition - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.schedule',
            'view_mode': 'list,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {
                'default_invoice_id': self.id,
                'search_default_group_by_product': 1,
            },
        }
    
    def action_process_revenue_recognition(self):
        """Process revenue recognition for schedules from this invoice"""
        self.ensure_one()
        
        processed_count = 0
        errors = []
        
        for schedule in self.revenue_schedule_ids.filtered(lambda s: s.state == 'active'):
            try:
                initial_recognized = schedule.recognized_amount
                schedule.process_due_recognitions()
                
                if schedule.recognized_amount > initial_recognized:
                    processed_count += 1
            except Exception as e:
                errors.append(_('Schedule %s: %s') % (schedule.id, str(e)))
        
        # Prepare message
        if processed_count > 0:
            message = _('Processed revenue recognition for %d schedule(s)') % processed_count
            if errors:
                message += _('\nErrors: %s') % ', '.join(errors)
            message_type = 'success'
        elif errors:
            message = _('Errors processing recognition: %s') % ', '.join(errors)
            message_type = 'warning'
        else:
            message = 'No revenue recognition entries were due for processing'
            message_type = 'info'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': message_type,
            }
        }
    
    def get_revenue_recognition_summary(self):
        """Get revenue recognition summary for this invoice"""
        self.ensure_one()
        
        return {
            'invoice_id': self.id,
            'invoice_name': self.name,
            'partner_name': self.partner_id.name,
            'invoice_amount': self.amount_total,
            'has_revenue_recognition': self.has_revenue_recognition,
            'recognition_status': self.revenue_recognition_status,
            'total_deferred_revenue': self.total_deferred_revenue,
            'total_recognized_revenue': self.total_recognized_revenue,
            'schedules_count': len(self.revenue_schedule_ids),
            'schedules': [
                {
                    'id': schedule.id,
                    'product_name': schedule.product_id.name,
                    'total_amount': schedule.total_amount,
                    'recognized_amount': schedule.recognized_amount,
                    'deferred_amount': schedule.deferred_amount,
                    'state': schedule.state,
                    'next_recognition_date': schedule.next_recognition_date,
                }
                for schedule in self.revenue_schedule_ids
            ]
        }

    # Bulk processing methods for better performance
    @api.model
    def process_invoices_revenue_recognition(self, invoice_ids=None, cutoff_date=None):
        """Bulk process revenue recognition for multiple invoices"""
        if not cutoff_date:
            cutoff_date = fields.Date.today()
        
        if invoice_ids:
            invoices = self.browse(invoice_ids)
        else:
            invoices = self.search([
                ('revenue_recognition_status', '=', 'active'),
                ('state', '=', 'posted')
            ])
        
        processed_invoices = 0
        total_recognitions = 0
        errors = []
        
        for invoice in invoices:
            try:
                initial_total = invoice.total_recognized_revenue
                invoice.action_process_revenue_recognition()
                
                if invoice.total_recognized_revenue > initial_total:
                    processed_invoices += 1
                    total_recognitions += 1
                    
            except Exception as e:
                errors.append(_('Invoice %s: %s') % (invoice.name, str(e)))
        
        return {
            'processed_invoices': processed_invoices,
            'total_recognitions': total_recognitions,
            'total_invoices_checked': len(invoices),
            'errors': errors
        }
    
    @api.model
    def get_revenue_recognition_dashboard_data(self, date_from=None, date_to=None):
        """Get dashboard data for revenue recognition analysis"""
        if not date_from:
            date_from = fields.Date.today().replace(day=1)
        if not date_to:
            date_to = fields.Date.today()
        
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('has_revenue_recognition', '=', True),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ]
        
        invoices = self.search(domain)
        
        # Aggregate data
        total_invoices = len(invoices)
        total_invoice_amount = sum(invoices.mapped('amount_total'))
        total_deferred = sum(invoices.mapped('total_deferred_revenue'))
        total_recognized = sum(invoices.mapped('total_recognized_revenue'))
        
        # Status breakdown
        status_breakdown = {}
        for status in ['none', 'pending', 'active', 'completed']:
            count = len(invoices.filtered(lambda i: i.revenue_recognition_status == status))
            status_breakdown[status] = count
        
        return {
            'date_from': date_from,
            'date_to': date_to,
            'total_invoices': total_invoices,
            'total_invoice_amount': total_invoice_amount,
            'total_deferred_revenue': total_deferred,
            'total_recognized_revenue': total_recognized,
            'status_breakdown': status_breakdown,
            'recognition_percentage': (total_recognized / total_invoice_amount * 100) if total_invoice_amount > 0 else 0,
        }


class AccountMoveLine(models.Model):
    """Extend Account Move Line for revenue recognition integration"""
    _inherit = 'account.move.line'
    
    # Revenue Recognition Fields
    revenue_schedule_id = fields.Many2one(
        'ams.revenue.schedule',
        string='Revenue Schedule',
        help='Revenue recognition schedule for this line'
    )
    
    has_revenue_recognition = fields.Boolean(
        string='Has Revenue Recognition',
        compute='_compute_has_revenue_recognition',
        store=True,
        help='This line has revenue recognition'
    )
    
    needs_revenue_recognition = fields.Boolean(
        string='Needs Revenue Recognition',
        compute='_compute_needs_revenue_recognition',
        help='This line needs revenue recognition but schedule not yet created'
    )

    @api.depends('revenue_schedule_id')
    def _compute_has_revenue_recognition(self):
        """Compute if line has revenue recognition"""
        for line in self:
            line.has_revenue_recognition = bool(line.revenue_schedule_id)
    
    @api.depends('product_id.is_subscription_product', 'product_id.use_ams_accounting', 
                 'product_id.revenue_recognition_method', 'revenue_schedule_id')
    def _compute_needs_revenue_recognition(self):
        """Compute if line needs revenue recognition"""
        for line in self:
            if not line.product_id:
                line.needs_revenue_recognition = False
                continue
            
            product_template = line.product_id.product_tmpl_id
            
            # Check all the conditions for needing revenue recognition
            needs_recognition = (
                product_template.is_subscription_product and
                product_template.use_ams_accounting and
                getattr(product_template, 'auto_create_recognition', False) and
                getattr(product_template, 'revenue_recognition_method', 'immediate') != 'immediate' and
                not line.revenue_schedule_id and
                line.move_id.move_type == 'out_invoice'
            )
            
            line.needs_revenue_recognition = needs_recognition
    
    def action_create_revenue_schedule(self):
        """Create revenue recognition schedule for this line"""
        self.ensure_one()
        
        if self.revenue_schedule_id:
            raise UserError(_('Revenue recognition schedule already exists for this line'))
        
        if not self.needs_revenue_recognition:
            raise UserError(_('This line does not need revenue recognition'))
        
        product_template = self.product_id.product_tmpl_id
        schedule = product_template.create_recognition_schedule(self)
        
        if schedule:
            self.revenue_schedule_id = schedule.id
            return {
                'name': 'Revenue Recognition Schedule',
                'type': 'ir.actions.act_window',
                'res_model': 'ams.revenue.schedule',
                'res_id': schedule.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise UserError(_('Failed to create revenue recognition schedule'))
    
    def action_view_revenue_schedule(self):
        """View revenue recognition schedule for this line"""
        self.ensure_one()
        
        if not self.revenue_schedule_id:
            raise UserError(_('No revenue recognition schedule exists for this line'))
        
        return {
            'name': 'Revenue Recognition Schedule',
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.schedule',
            'res_id': self.revenue_schedule_id.id,
            'view_mode': 'form',
            'target': 'current',
        }