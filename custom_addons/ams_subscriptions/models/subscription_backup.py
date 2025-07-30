from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SubscriptionBackup(models.Model):
    """Model for subscription backups"""
    _name = 'ams.subscription.backup'
    _description = 'Subscription Backup'
    _order = 'backup_date desc'
    _inherit = ['mail.thread']

    original_subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Original Subscription',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Member',
        related='original_subscription_id.partner_id',
        store=True,
        readonly=True
    )
    
    membership_type_id = fields.Many2one(
        'ams.membership.type',
        string='Original Membership Type',
        required=True
    )
    
    chapter_id = fields.Many2one(
        'ams.chapter',
        string='Original Chapter'
    )
    
    unit_price = fields.Float(
        string='Original Price',
        digits='Product Price'
    )
    
    start_date = fields.Date(
        string='Original Start Date'
    )
    
    end_date = fields.Date(
        string='Original End Date'
    )
    
    state = fields.Char(
        string='Original State',
        help="State of subscription when backup was created"
    )
    
    backup_date = fields.Date(
        string='Backup Date',
        required=True,
        default=fields.Date.context_today
    )
    
    backup_type = fields.Selection([
        ('transfer', 'Transfer Backup'),
        ('upgrade', 'Upgrade Backup'),
        ('change', 'General Change Backup'),
        ('manual', 'Manual Backup')
    ], string='Backup Type', required=True, default='manual')
    
    change_reason = fields.Char(
        string='Change Reason',
        help="Reason for the change that triggered this backup"
    )
    
    notes = fields.Html(
        string='Backup Notes',
        help="Additional notes about this backup"
    )
    
    restored = fields.Boolean(
        string='Restored',
        default=False,
        help="Check if this backup has been restored"
    )
    
    restored_date = fields.Date(
        string='Restored Date'
    )
    
    restored_by = fields.Many2one(
        'res.users',
        string='Restored By'
    )
    
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    # Additional backup fields for comprehensive restore
    subscription_notes = fields.Html(
        string='Original Subscription Notes'
    )
    
    discount_percent = fields.Float(
        string='Original Discount %',
        digits='Discount'
    )
    
    auto_renew = fields.Boolean(
        string='Original Auto-Renew Setting'
    )
    
    payment_method = fields.Char(
        string='Original Payment Method'
    )

    @api.model
    def create_backup(self, subscription, backup_type='manual', reason=None, notes=None):
        """Create a backup of a subscription"""
        backup_vals = {
            'original_subscription_id': subscription.id,
            'membership_type_id': subscription.membership_type_id.id,
            'chapter_id': subscription.chapter_id.id if subscription.chapter_id else False,
            'unit_price': subscription.unit_price,
            'start_date': subscription.start_date,
            'end_date': subscription.end_date,
            'state': subscription.state,
            'backup_type': backup_type,
            'change_reason': reason,
            'notes': notes,
            'subscription_notes': subscription.notes,
            'discount_percent': getattr(subscription, 'discount_percent', 0.0),
            'auto_renew': getattr(subscription, 'auto_renew', False),
            'payment_method': getattr(subscription, 'payment_method', ''),
        }
        
        backup = self.create(backup_vals)
        
        # Log backup creation
        subscription.message_post(
            body=_("Backup created: %s") % backup_type.replace('_', ' ').title()
        )
        
        _logger.info(f"Created subscription backup {backup.id} for subscription {subscription.id}")
        
        return backup

    def action_restore_backup(self):
        """Restore subscription from this backup"""
        self.ensure_one()
        
        if self.restored:
            raise ValidationError(_("This backup has already been restored"))
        
        if not self.original_subscription_id.exists():
            raise ValidationError(_("Original subscription no longer exists"))
        
        # Confirm restoration
        return {
            'type': 'ir.actions.act_window',
            'name': _('Confirm Restore'),
            'res_model': 'ams.subscription.restore.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_backup_id': self.id,
                'default_subscription_id': self.original_subscription_id.id
            }
        }

    def _perform_restore(self):
        """Perform the actual restore operation"""
        self.ensure_one()
        
        if self.restored:
            raise ValidationError(_("This backup has already been restored"))
        
        subscription = self.original_subscription_id
        
        # Create current state backup before restoring
        self.create_backup(
            subscription,
            backup_type='manual',
            reason='Pre-restore backup',
            notes=f"Automatic backup before restoring from backup {self.id}"
        )
        
        # Restore subscription to backup state
        restore_vals = {
            'membership_type_id': self.membership_type_id.id,
            'chapter_id': self.chapter_id.id if self.chapter_id else False,
            'unit_price': self.unit_price,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'notes': self.subscription_notes,
            'discount_percent': self.discount_percent,
            'auto_renew': self.auto_renew,
            'payment_method': self.payment_method,
        }
        
        subscription.write(restore_vals)
        
        # Mark as restored
        self.write({
            'restored': True,
            'restored_date': fields.Date.today(),
            'restored_by': self.env.user.id
        })
        
        # Log restoration
        subscription.message_post(
            body=_("Subscription restored from backup created on %s") % self.backup_date
        )
        
        self.message_post(
            body=_("Backup restored by %s") % self.env.user.name
        )
        
        _logger.info(f"Restored subscription {subscription.id} from backup {self.id}")

    def action_view_subscription(self):
        """View the original subscription"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Original Subscription'),
            'res_model': 'ams.member.subscription',
            'res_id': self.original_subscription_id.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def action_compare_with_current(self):
        """Compare backup with current subscription state"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Compare Backup'),
            'res_model': 'ams.subscription.compare.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_backup_id': self.id,
                'default_subscription_id': self.original_subscription_id.id
            }
        }

    @api.model
    def cleanup_old_backups(self, days_to_keep=365):
        """Clean up old backups (cron job)"""
        cutoff_date = fields.Date.today() - relativedelta(days=days_to_keep)
        
        old_backups = self.search([
            ('backup_date', '<', cutoff_date),
            ('restored', '=', False)
        ])
        
        if old_backups:
            count = len(old_backups)
            old_backups.unlink()
            _logger.info(f"Cleaned up {count} old subscription backups")
            return count
        
        return 0

    def name_get(self):
        """Custom name for backup records"""
        result = []
        for backup in self:
            name = f"{backup.partner_id.name if backup.partner_id else 'Unknown'} - {backup.backup_date}"
            if backup.backup_type:
                name += f" ({backup.backup_type.replace('_', ' ').title()})"
            if backup.restored:
                name += " [RESTORED]"
            result.append((backup.id, name))
        return result


class SubscriptionRestoreWizard(models.TransientModel):
    """Wizard for restoring subscription backups"""
    _name = 'ams.subscription.restore.wizard'
    _description = 'Subscription Restore Wizard'

    backup_id = fields.Many2one(
        'ams.subscription.backup',
        string='Backup to Restore',
        required=True,
        readonly=True
    )
    
    subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Target Subscription',
        required=True,
        readonly=True
    )
    
    backup_date = fields.Date(
        string='Backup Date',
        related='backup_id.backup_date',
        readonly=True
    )
    
    backup_type = fields.Selection(
        string='Backup Type',
        related='backup_id.backup_type',
        readonly=True
    )
    
    create_pre_restore_backup = fields.Boolean(
        string='Create Pre-Restore Backup',
        default=True,
        help="Create backup of current state before restoring"
    )
    
    restore_notes = fields.Text(
        string='Restore Notes',
        help="Notes about this restore operation"
    )
    
    comparison_data = fields.Html(
        string='Comparison',
        compute='_compute_comparison_data',
        help="Comparison between current state and backup"
    )

    @api.depends('backup_id', 'subscription_id')
    def _compute_comparison_data(self):
        """Compute comparison between backup and current state"""
        for wizard in self:
            if not wizard.backup_id or not wizard.subscription_id:
                wizard.comparison_data = ""
                continue
            
            backup = wizard.backup_id
            current = wizard.subscription_id
            
            comparison_html = "<table class='table table-sm'>"
            comparison_html += "<thead><tr><th>Field</th><th>Current</th><th>Backup</th></tr></thead>"
            comparison_html += "<tbody>"
            
            # Compare key fields
            fields_to_compare = [
                ('Membership Type', current.membership_type_id.name, backup.membership_type_id.name),
                ('Chapter', current.chapter_id.name if current.chapter_id else 'None', 
                 backup.chapter_id.name if backup.chapter_id else 'None'),
                ('Price', f"${current.unit_price:.2f}", f"${backup.unit_price:.2f}"),
                ('Start Date', str(current.start_date), str(backup.start_date)),
                ('End Date', str(current.end_date), str(backup.end_date)),
                ('State', current.state, backup.state),
            ]
            
            for field_name, current_val, backup_val in fields_to_compare:
                row_class = "" if current_val == backup_val else "table-warning"
                comparison_html += f"<tr class='{row_class}'>"
                comparison_html += f"<td><strong>{field_name}</strong></td>"
                comparison_html += f"<td>{current_val}</td>"
                comparison_html += f"<td>{backup_val}</td>"
                comparison_html += "</tr>"
            
            comparison_html += "</tbody></table>"
            
            if any(current_val != backup_val for _, current_val, backup_val in fields_to_compare):
                comparison_html = "<div class='alert alert-warning mb-3'>⚠️ The backup differs from the current subscription state</div>" + comparison_html
            else:
                comparison_html = "<div class='alert alert-info mb-3'>ℹ️ The backup matches the current subscription state</div>" + comparison_html
            
            wizard.comparison_data = comparison_html

    def action_confirm_restore(self):
        """Confirm and perform the restore"""
        self.ensure_one()
        
        try:
            # Add restore notes to backup
            if self.restore_notes:
                self.backup_id.notes = (self.backup_id.notes or '') + f"\n\nRestore Notes: {self.restore_notes}"
            
            # Perform restore
            self.backup_id._perform_restore()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Subscription restored successfully from backup'),
                    'type': 'success'
                }
            }
            
        except Exception as e:
            raise ValidationError(_("Restore failed: %s") % str(e))

    def action_cancel(self):
        """Cancel the restore operation"""
        return {'type': 'ir.actions.act_window_close'}