# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class MergeContactsWizard(models.TransientModel):
    """Wizard for safely merging AMS contacts with validation."""
    
    _name = 'merge.contacts.wizard'
    _description = 'Merge AMS Contacts Wizard'
    
    # === Selection Fields ===
    source_partner_ids = fields.Many2many(
        'res.partner',
        'merge_wizard_partner_rel',
        'wizard_id',
        'partner_id',
        string='Contacts to Merge',
        help='Select contacts to be merged (2 or more required)'
    )
    
    target_partner_id = fields.Many2one(
        'res.partner',
        string='Target Contact',
        required=True,
        help='Contact that will survive the merge - all others will be merged into this one'
    )
    
    # === Merge Options ===
    merge_mode = fields.Selection([
        ('safe', 'Safe Merge (with validation)'),
        ('force', 'Force Merge (override warnings)')
    ], string='Merge Mode', default='safe', required=True)
    
    preserve_member_id = fields.Boolean(
        string='Preserve Member ID',
        default=True,
        help='Keep the target contact\'s member ID'
    )
    
    merge_addresses = fields.Boolean(
        string='Merge Addresses',
        default=True,
        help='Merge addresses from source contacts'
    )
    
    merge_relationships = fields.Boolean(
        string='Merge Relationships',
        default=True,
        help='Transfer relationships to target contact'
    )
    
    merge_activities = fields.Boolean(
        string='Merge Activities',
        default=True,
        help='Transfer activities and notes to target contact'
    )
    
    # === Validation Results ===
    validation_passed = fields.Boolean(
        string='Validation Passed',
        default=False,
        compute='_compute_validation_results'
    )
    
    validation_warnings = fields.Text(
        string='Validation Warnings',
        compute='_compute_validation_results',
        help='Warnings found during validation'
    )
    
    validation_errors = fields.Text(
        string='Validation Errors',
        compute='_compute_validation_results',
        help='Errors that prevent merging'
    )
    
    # === Merge Preview ===
    preview_data = fields.Text(
        string='Merge Preview',
        compute='_compute_merge_preview',
        help='Preview of what will be merged'
    )
    
    # === State Management ===
    state = fields.Selection([
        ('select', 'Select Contacts'),
        ('validate', 'Validate Merge'),
        ('preview', 'Preview Changes'),
        ('confirm', 'Confirm Merge')
    ], string='State', default='select')
    
    @api.depends('source_partner_ids', 'target_partner_id', 'merge_mode')
    def _compute_validation_results(self):
        """Validate the merge operation and identify potential issues."""
        for wizard in self:
            warnings = []
            errors = []
            
            # Basic validation
            if len(wizard.source_partner_ids) < 2:
                errors.append('At least 2 contacts must be selected for merging.')
            
            if not wizard.target_partner_id:
                errors.append('Target contact must be selected.')
            
            if wizard.target_partner_id and wizard.target_partner_id not in wizard.source_partner_ids:
                errors.append('Target contact must be one of the selected contacts.')
            
            if errors:
                wizard.validation_passed = False
                wizard.validation_warnings = ''
                wizard.validation_errors = '\n'.join(errors)
                continue
            
            # AMS-specific validations
            source_contacts = wizard.source_partner_ids - wizard.target_partner_id
            target = wizard.target_partner_id
            
            # Check for active memberships
            active_members = source_contacts.filtered('is_ams_member')
            if active_members and target.is_ams_member:
                warnings.append(f'Multiple active members being merged: {", ".join(active_members.mapped("name"))}')
            
            # Check for multiple member IDs
            member_ids = source_contacts.filtered('member_id').mapped('member_id')
            if member_ids and target.member_id:
                warnings.append(f'Multiple Member IDs found: {", ".join(member_ids + [target.member_id])}')
            
            # Check for relationships that might be duplicated
            relationship_conflicts = []
            for source in source_contacts:
                for rel in source.relationship_ids:
                    existing = target.relationship_ids.filtered(
                        lambda r: r.related_partner_id == rel.related_partner_id and 
                                 r.relationship_type_id == rel.relationship_type_id
                    )
                    if existing:
                        relationship_conflicts.append(
                            f'{source.name} -> {rel.related_partner_id.name} ({rel.relationship_type_id.name})'
                        )
            
            if relationship_conflicts:
                warnings.append(f'Duplicate relationships will be consolidated: {"; ".join(relationship_conflicts)}')
            
            # Check for email conflicts
            email_conflicts = []
            target_emails = [target.email] if target.email else []
            for source in source_contacts:
                if source.email and source.email in target_emails:
                    email_conflicts.append(source.email)
            
            if email_conflicts:
                warnings.append(f'Duplicate email addresses: {", ".join(email_conflicts)}')
            
            # Check for user accounts
            user_accounts = source_contacts.filtered('user_ids')
            if user_accounts and target.user_ids:
                warnings.append(f'Multiple user accounts found - will need manual resolution')
            
            # Final validation
            if wizard.merge_mode == 'safe' and len(warnings) > 0:
                wizard.validation_passed = False
                wizard.validation_warnings = '\n'.join(warnings)
                wizard.validation_errors = 'Warnings found in safe mode. Use force mode to proceed anyway.'
            else:
                wizard.validation_passed = True
                wizard.validation_warnings = '\n'.join(warnings) if warnings else 'No warnings found.'
                wizard.validation_errors = ''
    
    @api.depends('source_partner_ids', 'target_partner_id')
    def _compute_merge_preview(self):
        """Generate preview of merge operation."""
        for wizard in self:
            if not wizard.target_partner_id or len(wizard.source_partner_ids) < 2:
                wizard.preview_data = 'Please select contacts to merge first.'
                continue
            
            preview_lines = []
            source_contacts = wizard.source_partner_ids - wizard.target_partner_id
            target = wizard.target_partner_id
            
            preview_lines.append(f'TARGET CONTACT: {target.name} (ID: {target.id})')
            if target.member_id:
                preview_lines.append(f'  Member ID: {target.member_id}')
            preview_lines.append('')
            
            preview_lines.append('CONTACTS TO BE MERGED:')
            for source in source_contacts:
                preview_lines.append(f'  • {source.name} (ID: {source.id})')
                if source.member_id:
                    preview_lines.append(f'    Member ID: {source.member_id}')
                if source.email:
                    preview_lines.append(f'    Email: {source.email}')
                if source.relationship_ids:
                    preview_lines.append(f'    Relationships: {len(source.relationship_ids)}')
                preview_lines.append('')
            
            wizard.preview_data = '\n'.join(preview_lines)
    
    def action_validate(self):
        """Move to validation step."""
        self.ensure_one()
        
        if len(self.source_partner_ids) < 2:
            raise ValidationError(_('Please select at least 2 contacts to merge.'))
        
        if not self.target_partner_id:
            raise ValidationError(_('Please select a target contact.'))
        
        self.state = 'validate'
        return self._return_wizard()
    
    def action_preview(self):
        """Move to preview step."""
        self.ensure_one()
        self.state = 'preview'
        return self._return_wizard()
    
    def action_confirm_merge(self):
        """Perform the actual merge operation."""
        self.ensure_one()
        
        if not self.validation_passed and self.merge_mode == 'safe':
            raise UserError(_('Validation failed. Please fix errors or use force mode.'))
        
        return self._perform_merge()
    
    def _perform_merge(self):
        """Execute the merge operation."""
        self.ensure_one()
        
        source_contacts = self.source_partner_ids - self.target_partner_id
        target = self.target_partner_id
        merge_log = []
        
        try:
            with self.env.cr.savepoint():
                # Log the merge operation
                merge_log.append(f'Merging {len(source_contacts)} contacts into {target.name}')
                
                # 1. Merge Member IDs (preserve target if requested)
                if not self.preserve_member_id:
                    member_ids = source_contacts.filtered('member_id').mapped('member_id')
                    if member_ids:
                        merge_log.append(f'Member IDs consolidated: {", ".join(member_ids)}')
                
                # 2. Merge Addresses
                if self.merge_addresses:
                    merged_addresses = 0
                    for source in source_contacts:
                        for addr in source.address_type_ids:
                            # Check if target already has this address type
                            existing = target.address_type_ids.filtered(
                                lambda a: a.address_type_id == addr.address_type_id
                            )
                            if not existing:
                                addr.partner_id = target.id
                                merged_addresses += 1
                    
                    if merged_addresses > 0:
                        merge_log.append(f'Merged {merged_addresses} additional addresses')
                
                # 3. Merge Relationships
                if self.merge_relationships:
                    merged_relationships = 0
                    for source in source_contacts:
                        for rel in source.relationship_ids:
                            # Check for duplicate relationships
                            existing = target.relationship_ids.filtered(
                                lambda r: r.related_partner_id == rel.related_partner_id and
                                         r.relationship_type_id == rel.relationship_type_id
                            )
                            if not existing:
                                rel.partner_id = target.id
                                merged_relationships += 1
                            else:
                                # Keep the more recent relationship
                                if rel.start_date and existing.start_date:
                                    if rel.start_date > existing.start_date:
                                        existing.unlink()
                                        rel.partner_id = target.id
                                        merged_relationships += 1
                                    else:
                                        rel.unlink()
                                else:
                                    rel.unlink()
                    
                    if merged_relationships > 0:
                        merge_log.append(f'Merged {merged_relationships} relationships')
                
                # 4. Merge Activities and Messages
                if self.merge_activities:
                    merged_activities = 0
                    for source in source_contacts:
                        # Move mail messages
                        messages = self.env['mail.message'].search([
                            ('res_id', '=', source.id),
                            ('model', '=', 'res.partner')
                        ])
                        messages.write({'res_id': target.id})
                        merged_activities += len(messages)
                        
                        # Move activities
                        activities = self.env['mail.activity'].search([
                            ('res_id', '=', source.id),
                            ('res_model', '=', 'res.partner')
                        ])
                        activities.write({'res_id': target.id})
                        merged_activities += len(activities)
                    
                    if merged_activities > 0:
                        merge_log.append(f'Merged {merged_activities} activities and messages')
                
                # 5. Update references in other models
                self._update_references(source_contacts, target)
                
                # 6. Merge user accounts (if any)
                user_conflicts = []
                for source in source_contacts:
                    if source.user_ids:
                        if target.user_ids:
                            user_conflicts.extend(source.user_ids.mapped('login'))
                        else:
                            source.user_ids.write({'partner_id': target.id})
                
                if user_conflicts:
                    merge_log.append(f'User account conflicts (manual resolution needed): {", ".join(user_conflicts)}')
                
                # 7. Consolidate professional information
                self._consolidate_professional_data(source_contacts, target)
                
                # 8. Add merge note to target
                merge_note = f"Contact merged from: {', '.join(source_contacts.mapped('name'))} on {fields.Datetime.now()}"
                target.message_post(body=merge_note, subject="Contact Merge")
                
                # 9. Mark source contacts as merged and inactive
                source_contacts.write({
                    'active': False,
                    'member_status': 'merged',
                    'name': lambda rec: f'[MERGED] {rec.name}'
                })
                
                # Log successful merge
                _logger.info(f'Contact merge completed: {"; ".join(merge_log)}')
                
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'res.partner',
                    'res_id': target.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
        
        except Exception as e:
            _logger.error(f'Contact merge failed: {str(e)}')
            raise UserError(_('Merge failed: %s') % str(e))
    
    def _update_references(self, source_contacts, target):
        """Update references to source contacts in other models."""
        # This is a placeholder for updating references in other AMS modules
        # Each module should implement its own reference updates
        
        # Example: Update invoice references
        invoices = self.env['account.move'].search([
            ('partner_id', 'in', source_contacts.ids)
        ])
        invoices.write({'partner_id': target.id})
        
        # Example: Update sale order references  
        sales = self.env['sale.order'].search([
            ('partner_id', 'in', source_contacts.ids)
        ])
        sales.write({'partner_id': target.id})
    
    def _consolidate_professional_data(self, source_contacts, target):
        """Consolidate professional information from source contacts."""
        # Consolidate designations
        all_designations = target.designation_ids
        for source in source_contacts:
            all_designations |= source.designation_ids
        target.designation_ids = all_designations.ids
        
        # Consolidate practice areas
        all_practice_areas = target.practice_area_ids
        for source in source_contacts:
            all_practice_areas |= source.practice_area_ids
        target.practice_area_ids = all_practice_areas.ids
        
        # Use highest engagement score
        max_engagement = max([target.engagement_score] + source_contacts.mapped('engagement_score'))
        if max_engagement > target.engagement_score:
            target.engagement_score = max_engagement
    
    def _return_wizard(self):
        """Return the wizard view."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'merge.contacts.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_back(self):
        """Go back to previous step."""
        self.ensure_one()
        
        if self.state == 'validate':
            self.state = 'select'
        elif self.state == 'preview':
            self.state = 'validate'
        elif self.state == 'confirm':
            self.state = 'preview'
        
        return self._return_wizard()
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from context."""
        defaults = super().default_get(fields_list)
        
        # Get partner IDs from context
        if self.env.context.get('active_model') == 'res.partner':
            partner_ids = self.env.context.get('active_ids', [])
            if partner_ids:
                defaults['source_partner_ids'] = [(6, 0, partner_ids)]
                # Set first partner as default target
                if len(partner_ids) > 0:
                    defaults['target_partner_id'] = partner_ids[0]
        
        return defaults