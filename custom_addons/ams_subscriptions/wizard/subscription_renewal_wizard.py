from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class SubscriptionRenewalWizard(models.TransientModel):
    _name = 'ams.subscription.renewal.wizard'
    _description = 'Subscription Renewal Wizard'

    # Selection Method
    renewal_method = fields.Selection([
        ('single', 'Single Subscription'),
        ('multiple', 'Multiple Subscriptions'),
        ('bulk_criteria', 'Bulk by Criteria')
    ], string='Renewal Method', default='single', required=True)
    
    # Single Subscription
    subscription_id = fields.Many2one(
        'ams.member.subscription',
        string='Subscription to Renew',
        domain=[('state', 'in', ['active', 'pending_renewal', 'expired'])]
    )
    
    # Multiple Subscriptions
    subscription_ids = fields.Many2many(
        'ams.member.subscription',
        string='Subscriptions to Renew',
        domain=[('state', 'in', ['active', 'pending_renewal', 'expired'])]
    )
    
    # Bulk Criteria
    membership_type_ids = fields.Many2many(
        'ams.membership.type',
        string='Membership Types'
    )
    
    chapter_ids = fields.Many2many(
        'ams.chapter',
        string='Chapters'
    )
    
    expiry_date_from = fields.Date(
        string='Expiry Date From',
        help="Include subscriptions expiring from this date"
    )
    
    expiry_date_to = fields.Date(
        string='Expiry Date To',
        help="Include subscriptions expiring up to this date"
    )
    
    # Renewal Settings
    renewal_start_date = fields.Date(
        string='New Period Start Date',
        default=fields.Date.context_today,
        required=True,
        help="Start date for the renewed subscription period"
    )
    
    renewal_duration_type = fields.Selection([
        ('same', 'Same as Original'),
        ('custom', 'Custom Duration')
    ], string='Duration Type', default='same', required=True)
    
    custom_duration_months = fields.Integer(
        string='Custom Duration (Months)',
        default=12,
        help="Duration in months for custom renewal period"
    )
    
    # Pricing Options
    pricing_option = fields.Selection([
        ('standard', 'Standard Pricing'),
        ('custom', 'Custom Pricing'),
        ('discount', 'Apply Discount')
    ], string='Pricing Option', default='standard', required=True)
    
    custom_price = fields.Float(
        string='Custom Price',
        digits='Product Price',
        help="Custom price for renewal (applies to all selected subscriptions)"
    )
    
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ], string='Discount Type', default='percentage')
    
    discount_percentage = fields.Float(
        string='Discount Percentage',
        digits='Discount',
        help="Discount percentage to apply"
    )
    
    discount_amount = fields.Float(
        string='Discount Amount',
        digits='Product Price',
        help="Fixed discount amount to apply"
    )
    
    # Processing Options
    auto_confirm = fields.Boolean(
        string='Auto-Confirm Orders',
        default=True,
        help="Automatically confirm the created sale orders"
    )
    
    auto_invoice = fields.Boolean(
        string='Auto-Create Invoices',
        default=False,
        help="Automatically create invoices for confirmed orders"
    )
    
    send_notifications = fields.Boolean(
        string='Send Notifications',
        default=True,
        help="Send renewal notifications to members"
    )
    
    # Communication
    renewal_message = fields.Html(
        string='Renewal Message',
        help="Custom message to include in renewal notifications"
    )
    
    # Results
    subscription_count = fields.Integer(
        string='Subscriptions Found',
        compute='_compute_subscription_count',
        help="Number of subscriptions that will be renewed"
    )
    
    preview_subscriptions = fields.Html(
        string='Preview',
        compute='_compute_preview_subscriptions',
        help="Preview of subscriptions to be renewed"
    )
    
    # Processing Results
    created_subscriptions = fields.Text(
        string='Created Subscriptions',
        readonly=True,
        help="List of created renewal subscriptions"
    )
    
    processing_log = fields.Html(
        string='Processing Log',
        readonly=True,
        help="Log of the renewal processing"
    )

    @api.depends('renewal_method', 'subscription_id', 'subscription_ids', 
                 'membership_type_ids', 'chapter_ids', 'expiry_date_from', 'expiry_date_to')
    def _compute_subscription_count(self):
        """Compute number of subscriptions to be renewed"""
        for wizard in self:
            subscriptions = wizard._get_subscriptions_to_renew()
            wizard.subscription_count = len(subscriptions)

    @api.depends('subscription_count')
    def _compute_preview_subscriptions(self):
        """Compute preview of subscriptions to be renewed"""
        for wizard in self:
            if wizard.subscription_count == 0:
                wizard.preview_subscriptions = "<p>No subscriptions found matching the criteria.</p>"
                continue
            
            subscriptions = wizard._get_subscriptions_to_renew()
            
            preview_html = "<table class='table table-sm'>"
            preview_html += "<thead><tr><th>Member</th><th>Membership Type</th><th>Chapter</th><th>Expiry Date</th><th>New Price</th></tr></thead>"
            preview_html += "<tbody>"
            
            for subscription in subscriptions[:10]:  # Show max 10 for preview
                try:
                    new_price = wizard._calculate_renewal_price(subscription)
                    
                    # Safe access to subscription attributes
                    member_name = 'Unknown'
                    membership_name = 'Unknown'
                    chapter_name = '-'
                    expiry_date = 'Unknown'
                    
                    try:
                        if subscription.partner_id:
                            member_name = subscription.partner_id.name or 'Unknown'
                    except AttributeError:
                        pass
                    
                    try:
                        if subscription.membership_type_id:
                            membership_name = subscription.membership_type_id.name or 'Unknown'
                    except AttributeError:
                        pass
                    
                    try:
                        if subscription.chapter_id:
                            chapter_name = subscription.chapter_id.name or '-'
                    except AttributeError:
                        pass
                    
                    try:
                        if subscription.end_date:
                            expiry_date = str(subscription.end_date)
                    except AttributeError:
                        pass
                    
                    preview_html += f"""
                    <tr>
                        <td>{member_name}</td>
                        <td>{membership_name}</td>
                        <td>{chapter_name}</td>
                        <td>{expiry_date}</td>
                        <td>{new_price:.2f}</td>
                    </tr>
                    """
                except Exception as e:
                    _logger.error(f"Error in preview generation: {e}")
                    continue
            
            if len(subscriptions) > 10:
                preview_html += f"<tr><td colspan='5'><em>... and {len(subscriptions) - 10} more</em></td></tr>"
            
            preview_html += "</tbody></table>"
            wizard.preview_subscriptions = preview_html

    @api.onchange('renewal_method')
    def _onchange_renewal_method(self):
        """Clear fields when renewal method changes"""
        if self.renewal_method == 'single':
            self.subscription_ids = [(5, 0, 0)]
            self.membership_type_ids = [(5, 0, 0)]
            self.chapter_ids = [(5, 0, 0)]
        elif self.renewal_method == 'multiple':
            self.subscription_id = False
            self.membership_type_ids = [(5, 0, 0)]
            self.chapter_ids = [(5, 0, 0)]
        elif self.renewal_method == 'bulk_criteria':
            self.subscription_id = False
            self.subscription_ids = [(5, 0, 0)]

    @api.onchange('pricing_option')
    def _onchange_pricing_option(self):
        """Clear pricing fields when option changes"""
        if self.pricing_option != 'custom':
            self.custom_price = 0.0
        if self.pricing_option != 'discount':
            self.discount_percentage = 0.0
            self.discount_amount = 0.0

    @api.constrains('custom_duration_months')
    def _check_custom_duration(self):
        """Validate custom duration"""
        for wizard in self:
            if wizard.renewal_duration_type == 'custom' and wizard.custom_duration_months <= 0:
                raise ValidationError(_("Custom duration must be greater than 0 months."))

    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        """Validate discount percentage"""
        for wizard in self:
            if wizard.discount_percentage < 0 or wizard.discount_percentage > 100:
                raise ValidationError(_("Discount percentage must be between 0 and 100."))

    def _get_subscriptions_to_renew(self):
        """Get subscriptions based on selected criteria"""
        self.ensure_one()
        
        if self.renewal_method == 'single':
            if self.subscription_id:
                return self.subscription_id
            else:
                return self.env['ams.member.subscription'].browse([])
        
        elif self.renewal_method == 'multiple':
            return self.subscription_ids or self.env['ams.member.subscription'].browse([])
        
        elif self.renewal_method == 'bulk_criteria':
            domain = [('state', 'in', ['active', 'pending_renewal', 'expired'])]
            
            # Safely handle Many2many fields
            if self.membership_type_ids:
                domain.append(('membership_type_id', 'in', self.membership_type_ids.ids))
            
            if self.chapter_ids:
                domain.append(('chapter_id', 'in', self.chapter_ids.ids))
            
            if self.expiry_date_from:
                domain.append(('end_date', '>=', self.expiry_date_from))
            
            if self.expiry_date_to:
                domain.append(('end_date', '<=', self.expiry_date_to))
            
            return self.env['ams.member.subscription'].search(domain)
        
        return self.env['ams.member.subscription'].browse([])

    def _calculate_renewal_price(self, subscription):
        """Calculate renewal price for a subscription"""
        self.ensure_one()
        
        if self.pricing_option == 'custom':
            return self.custom_price
        
        # Get base price
        try:
            base_price = subscription.membership_type_id.get_renewal_price(subscription)
        except AttributeError:
            # Fallback if method doesn't exist
            base_price = subscription.membership_type_id.price if subscription.membership_type_id else 0.0
        
        if self.pricing_option == 'discount':
            if self.discount_type == 'percentage':
                discount = base_price * (self.discount_percentage / 100)
                return base_price - discount
            else:  # fixed amount
                return max(0, base_price - self.discount_amount)
        
        return base_price

    def _calculate_renewal_end_date(self, subscription, start_date):
        """Calculate end date for renewal"""
        self.ensure_one()
        
        if self.renewal_duration_type == 'custom':
            return start_date + relativedelta(months=self.custom_duration_months)
        else:
            # Use the same duration as original membership type
            try:
                return subscription.membership_type_id.get_expiration_date(start_date)
            except AttributeError:
                # Fallback: add 1 year
                return start_date + relativedelta(years=1)

    def action_preview_renewals(self):
        """Preview renewals without creating them"""
        self.ensure_one()
        
        subscriptions = self._get_subscriptions_to_renew()
        
        if not subscriptions:
            raise UserError(_("No subscriptions found matching the criteria."))
        
        # Force recompute of preview
        self._compute_preview_subscriptions()
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.renewal.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_preview': True}
        }

    def action_process_renewals(self):
        """Process the subscription renewals"""
        self.ensure_one()
        
        subscriptions = self._get_subscriptions_to_renew()
        
        if not subscriptions:
            raise UserError(_("No subscriptions found matching the criteria."))
        
        # Ensure we have a proper recordset
        if not hasattr(subscriptions, 'filtered'):
            raise UserError(_("Invalid subscription data received."))
        
        # Validate subscriptions can be renewed
        invalid_subscriptions = subscriptions.filtered(
            lambda s: s.state not in ['active', 'pending_renewal', 'expired']
        )
        
        if invalid_subscriptions:
            raise UserError(
                _("Some subscriptions cannot be renewed due to their current state: %s") 
                % ', '.join(invalid_subscriptions.mapped('display_name'))
            )
        
        # Process renewals
        created_subscriptions = []
        processing_log = []
        errors = []
        
        # Ensure subscriptions is a recordset and iterate safely
        for subscription in subscriptions:
            try:
                # Validate subscription is a proper record
                if not hasattr(subscription, 'id') or not subscription.id:
                    _logger.error("Invalid subscription record encountered")
                    continue
                    
                renewal_subscription = self._create_renewal_subscription(subscription)
                created_subscriptions.append(renewal_subscription)
                
                # Safe access to subscription attributes with proper fallbacks
                member_name = 'Unknown'
                membership_name = 'Unknown'
                
                try:
                    if subscription.partner_id:
                        member_name = subscription.partner_id.name or 'Unknown'
                except AttributeError:
                    pass
                    
                try:
                    if subscription.membership_type_id:
                        membership_name = subscription.membership_type_id.name or 'Unknown'
                except AttributeError:
                    pass
                
                processing_log.append(
                    f"✓ Renewed: {member_name} - {membership_name}"
                )
                
                # Send notification if requested
                if self.send_notifications:
                    self._send_renewal_notification(renewal_subscription)
                
            except Exception as e:
                # Safe error handling
                member_name = 'Unknown'
                try:
                    if hasattr(subscription, 'partner_id') and subscription.partner_id:
                        member_name = subscription.partner_id.name or 'Unknown'
                except (AttributeError, TypeError):
                    pass
                
                error_msg = f"✗ Failed to renew {member_name}: {str(e)}"
                errors.append(error_msg)
                processing_log.append(error_msg)
                
                subscription_id = getattr(subscription, 'id', 'unknown')
                _logger.error(f"Renewal failed for subscription {subscription_id}: {e}")
        
        # Update wizard with results
        self.created_subscriptions = '\n'.join([s.display_name for s in created_subscriptions])
        self.processing_log = '<br/>'.join(processing_log)
        
        if errors:
            # Show partial success message
            message = _("Renewal completed with some errors:\n%s successful renewals\n%s errors") % (
                len(created_subscriptions), len(errors)
            )
        else:
            message = _("Successfully renewed %s subscriptions.") % len(created_subscriptions)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.renewal.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'show_results': True,
                'result_message': message
            }
        }

    def _create_renewal_subscription(self, original_subscription):
        """Create a renewal subscription"""
        self.ensure_one()
        
        # Calculate renewal values
        renewal_price = self._calculate_renewal_price(original_subscription)
        renewal_end_date = self._calculate_renewal_end_date(original_subscription, self.renewal_start_date)
        
        # Safe access to chapter_id
        chapter_id = False
        try:
            if original_subscription.chapter_id:
                chapter_id = original_subscription.chapter_id.id
        except AttributeError:
            pass
        
        # Create renewal subscription
        renewal_vals = {
            'partner_id': original_subscription.partner_id.id,
            'membership_type_id': original_subscription.membership_type_id.id,
            'chapter_id': chapter_id,
            'start_date': self.renewal_start_date,
            'end_date': renewal_end_date,
            'unit_price': renewal_price,
            'parent_subscription_id': original_subscription.id,
            'auto_renew': getattr(original_subscription, 'auto_renew', False),
            'payment_method': getattr(original_subscription, 'payment_method', False),
            'notes': f"Renewed via wizard on {fields.Date.today()}",
        }
        
        # Apply discount if applicable
        if self.pricing_option == 'discount':
            if self.discount_type == 'percentage':
                renewal_vals['discount_percent'] = self.discount_percentage
            # For fixed amount discount, we already calculated the reduced price
        
        renewal_subscription = self.env['ams.member.subscription'].create(renewal_vals)
        
        # Create sale order if auto-confirm is enabled
        if self.auto_confirm:
            try:
                if not renewal_subscription.sale_order_id:
                    renewal_subscription._create_sale_order()
                
                if renewal_subscription.sale_order_id:
                    renewal_subscription.sale_order_id.action_confirm()
                    
                    # Create invoice if auto-invoice is enabled
                    if self.auto_invoice:
                        renewal_subscription.sale_order_id._create_invoices()
            except Exception as e:
                _logger.warning(f"Failed to auto-confirm/invoice renewal subscription {renewal_subscription.id}: {e}")
        
        # Update original subscription renewal count
        try:
            original_subscription.renewal_count += 1
        except AttributeError:
            pass
        
        return renewal_subscription

    def _send_renewal_notification(self, renewal_subscription):
        """Send renewal notification to member"""
        try:
            template = self.env.ref(
                'ams_subscriptions.email_template_renewal_created',
                raise_if_not_found=False
            )
            
            if template and renewal_subscription.partner_id.email:
                # Prepare email context
                email_values = {}
                if self.renewal_message:
                    email_values['body_html'] = self.renewal_message
                
                template.send_mail(
                    renewal_subscription.id,
                    force_send=True,
                    email_values=email_values
                )
        except Exception as e:
            _logger.warning(f"Failed to send renewal notification for subscription {renewal_subscription.id}: {e}")

    @api.model
    def create_from_subscription(self, subscription_id):
        """Create wizard pre-filled for a specific subscription"""
        subscription = self.env['ams.member.subscription'].browse(subscription_id)
        
        if not subscription.exists():
            raise UserError(_("Subscription not found."))
        
        # Calculate start date safely
        start_date = fields.Date.today()
        try:
            if subscription.end_date:
                start_date = subscription.end_date + relativedelta(days=1)
        except AttributeError:
            pass
        
        wizard = self.create({
            'renewal_method': 'single',
            'subscription_id': subscription_id,
            'renewal_start_date': start_date,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.renewal.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _('Renew Subscription'),
        }

    @api.model
    def create_bulk_renewal(self, **criteria):
        """Create wizard for bulk renewal with predefined criteria"""
        wizard_vals = {
            'renewal_method': 'bulk_criteria',
        }
        
        # Apply criteria
        if 'membership_type_ids' in criteria:
            wizard_vals['membership_type_ids'] = [(6, 0, criteria['membership_type_ids'])]
        
        if 'chapter_ids' in criteria:
            wizard_vals['chapter_ids'] = [(6, 0, criteria['chapter_ids'])]
        
        if 'expiry_date_from' in criteria:
            wizard_vals['expiry_date_from'] = criteria['expiry_date_from']
        
        if 'expiry_date_to' in criteria:
            wizard_vals['expiry_date_to'] = criteria['expiry_date_to']
        
        wizard = self.create(wizard_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ams.subscription.renewal.wizard',  
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _('Bulk Renewal'),
        }

    def action_close(self):
        """Close the wizard"""
        return {'type': 'ir.actions.act_window_close'}