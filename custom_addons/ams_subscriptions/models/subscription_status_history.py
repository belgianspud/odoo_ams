from odoo import models, fields, api, _

class AMSSubscriptionStatusHistory(models.Model):
    _name = 'ams.subscription.status.history'
    _description = 'AMS Subscription Status History'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'
    
    subscription_id = fields.Many2one(
        'ams.subscription', 
        'Subscription', 
        required=True, 
        ondelete='cascade',
        index=True
    )
    
    date = fields.Datetime(
        'Change Date', 
        required=True, 
        default=fields.Datetime.now,
        index=True
    )
    
    from_status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('terminated', 'Terminated'),
        ('pending_renewal', 'Pending Renewal')
    ], string='From Status', help="Previous status before the change")
    
    to_status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('terminated', 'Terminated'),
        ('pending_renewal', 'Pending Renewal')
    ], string='To Status', required=True, help="New status after the change")
    
    reason = fields.Text('Reason for Change', help="Explanation for the status change")
    
    user_id = fields.Many2one(
        'res.users', 
        'Changed By', 
        required=True, 
        default=lambda self: self.env.user,
        help="User who initiated the status change"
    )
    
    automatic = fields.Boolean(
        'Automatic Change', 
        default=False,
        help="Whether this change was made automatically by the system"
    )
    
    rule_id = fields.Many2one(
        'ams.subscription.rule',
        'Applied Rule',
        help="Rule that triggered this status change (if automatic)"
    )
    
    # Related fields for easier reporting
    partner_id = fields.Many2one(
        related='subscription_id.partner_id',
        string='Member',
        store=True,
        readonly=True
    )
    
    subscription_type_id = fields.Many2one(
        related='subscription_id.subscription_type_id',
        string='Subscription Type',
        store=True,
        readonly=True
    )
    
    chapter_id = fields.Many2one(
        related='subscription_id.chapter_id',
        string='Chapter',
        store=True,
        readonly=True
    )
    
    # Computed fields
    display_name = fields.Char(
        'Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    duration_in_status = fields.Integer(
        'Duration in Previous Status (Days)',
        compute='_compute_duration_in_status',
        store=True,
        help="Number of days the subscription was in the previous status"
    )
    
    @api.depends('subscription_id', 'to_status', 'from_status', 'date')
    def _compute_display_name(self):
        for record in self:
            if record.from_status:
                record.display_name = f"{record.from_status.title()} → {record.to_status.title()}"
            else:
                record.display_name = f"Initial: {record.to_status.title()}"
    
    @api.depends('subscription_id', 'date', 'from_status')
    def _compute_duration_in_status(self):
        for record in self:
            if not record.from_status or not record.subscription_id:
                record.duration_in_status = 0
                continue
            
            # Find the previous status change
            previous_change = self.search([
                ('subscription_id', '=', record.subscription_id.id),
                ('date', '<', record.date),
                ('to_status', '=', record.from_status)
            ], order='date desc', limit=1)
            
            if previous_change:
                delta = record.date - previous_change.date
                record.duration_in_status = delta.days
            else:
                # Calculate from subscription start date
                if record.subscription_id.start_date:
                    start_datetime = fields.Datetime.from_string(
                        record.subscription_id.start_date.strftime('%Y-%m-%d 00:00:00')
                    )
                    delta = record.date - start_datetime
                    record.duration_in_status = delta.days
                else:
                    record.duration_in_status = 0
    
    @api.model
    def create_status_change(self, subscription, from_status, to_status, reason=None, automatic=False, rule_id=None):
        """Utility method to create a status history entry"""
        vals = {
            'subscription_id': subscription.id,
            'from_status': from_status,
            'to_status': to_status,
            'reason': reason or f"Status changed from {from_status or 'None'} to {to_status}",
            'automatic': automatic,
            'rule_id': rule_id,
        }
        return self.create(vals)
    
    def action_revert_status_change(self):
        """Action to revert to the previous status"""
        self.ensure_one()
        if not self.from_status:
            raise UserError(_("Cannot revert initial status setting"))
        
        # Update subscription status
        self.subscription_id.write({
            'state': self.from_status,
            'status_change_reason': f"Reverted from {self.to_status} to {self.from_status}"
        })
        
        # Create new history entry for the reversion
        self.create_status_change(
            self.subscription_id,
            self.to_status,
            self.from_status,
            f"Reverted status change made on {self.date}",
            automatic=False
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Status Reverted'),
                'message': _('Subscription status has been reverted to %s') % self.from_status,
                'type': 'success',
            }
        }
    
    @api.model
    def get_status_statistics(self, subscription_type_id=None, date_from=None, date_to=None):
        """Get statistics about status changes"""
        domain = []
        
        if subscription_type_id:
            domain.append(('subscription_type_id', '=', subscription_type_id))
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        
        records = self.search(domain)
        
        # Count by status transitions
        transitions = {}
        for record in records:
            key = f"{record.from_status or 'new'} → {record.to_status}"
            transitions[key] = transitions.get(key, 0) + 1
        
        # Count by final status
        final_statuses = {}
        for record in records:
            final_statuses[record.to_status] = final_statuses.get(record.to_status, 0) + 1
        
        # Average duration in each status
        avg_durations = {}
        for status in ['draft', 'active', 'grace', 'suspended', 'expired']:
            status_records = records.filtered(lambda r: r.from_status == status and r.duration_in_status > 0)
            if status_records:
                avg_durations[status] = sum(status_records.mapped('duration_in_status')) / len(status_records)
            else:
                avg_durations[status] = 0
        
        return {
            'transitions': transitions,
            'final_statuses': final_statuses,
            'average_durations': avg_durations,
            'total_changes': len(records)
        }
    
    def action_view_subscription(self):
        """Action to view the related subscription"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription'),
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'res_id': self.subscription_id.id,
            'target': 'current',
        }
    
    def action_view_partner(self):
        """Action to view the related partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Member'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.partner_id.id,
            'target': 'current',
        }