from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    # Subscription tracking
    subscription_count = fields.Integer(
        'Subscription Count',
        compute='_compute_subscription_count',
        help="Number of subscriptions created from this sale order"
    )
    
    has_subscription_products = fields.Boolean(
        'Has Subscription Products',
        compute='_compute_has_subscription_products',
        store=True,
        help="Whether this order contains subscription products"
    )
    
    @api.depends('order_line.product_id.is_subscription_product')
    def _compute_has_subscription_products(self):
        for order in self:
            order.has_subscription_products = any(
                line.product_id.is_subscription_product for line in order.order_line
            )
    
    def _compute_subscription_count(self):
        for order in self:
            subscriptions = self.env['ams.subscription'].search([
                ('sale_order_line_id', 'in', order.order_line.ids)
            ])
            order.subscription_count = len(subscriptions)
    
    def action_view_subscriptions(self):
        """Action to view subscriptions created from this order"""
        self.ensure_one()
        subscriptions = self.env['ams.subscription'].search([
            ('sale_order_line_id', 'in', self.order_line.ids)
        ])
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Subscriptions'),
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', subscriptions.ids)],
            'context': {
                'default_partner_id': self.partner_id.id,
            }
        }
    
    def _action_confirm(self):
        """Override to create subscriptions when order is confirmed"""
        result = super()._action_confirm()
        
        # Create subscriptions for subscription products
        for order in self:
            order._create_subscriptions_from_order()
        
        return result
    
    def _create_subscriptions_from_order(self):
        """Create subscriptions from order lines with subscription products"""
        for line in self.order_line:
            if line.product_id.is_subscription_product and not line.subscription_id:
                line._create_subscription_from_line()

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        'Created Subscription',
        readonly=True,
        help="Subscription created from this order line"
    )
    
    def _create_subscription_from_line(self):
        """Create a subscription from this sale order line"""
        self.ensure_one()
        
        if not self.product_id.is_subscription_product:
            return
        
        if self.subscription_id:
            # Already has a subscription
            return
        
        # Calculate subscription dates
        start_date = fields.Date.today()
        end_date = self._calculate_subscription_end_date(start_date)
        
        # Prepare subscription values
        subscription_vals = {
            'name': f"{self.product_id.name} - {self.order_id.partner_id.name}",
            'partner_id': self.order_id.partner_id.id,
            'subscription_type_id': self.product_id.subscription_type_id.id,
            'product_id': self.product_id.id,
            'sale_order_line_id': self.id,
            'amount': self.price_unit,
            'start_date': start_date,
            'end_date': end_date,
            'paid_through_date': end_date,
            'is_recurring': self.product_id.is_recurring,
            'recurring_period': self.product_id.recurring_period,
            'auto_renewal': self.product_id.auto_renewal,
            'next_renewal_date': end_date if self.product_id.is_recurring else False,
            'state': 'active',
            'notes': f"Created from sale order {self.order_id.name}",
        }
        
        # Handle membership-specific logic
        if self.product_id.subscription_type_id.code == 'membership':
            subscription_vals.update({
                'membership_number': self._generate_membership_number(),
                'member_since': start_date,
                'voting_rights': True,
                'board_eligible': True,
            })
        
        # Handle chapter-specific logic
        elif self.product_id.subscription_type_id.code == 'chapter':
            # For chapter subscriptions, we need a parent membership
            parent_membership = self._find_or_create_parent_membership()
            if parent_membership:
                subscription_vals.update({
                    'parent_subscription_id': parent_membership.id,
                    'chapter_join_date': start_date,
                })
                
                # Try to determine chapter from product or customer
                chapter = self._determine_chapter_from_context()
                if chapter:
                    subscription_vals['chapter_id'] = chapter.id
        
        # Create the subscription
        subscription = self.env['ams.subscription'].create(subscription_vals)
        
        # Link back to the order line
        self.subscription_id = subscription.id
        
        # Handle auto-creation of chapter subscriptions for memberships
        if (self.product_id.subscription_type_id.code == 'membership' and 
            self.product_id.auto_create_chapters and 
            self.product_id.default_chapter_ids):
            subscription._create_chapter_subscriptions(self.product_id.default_chapter_ids)
        
        # Create invoice link if needed
        if self.order_id.invoice_ids:
            subscription.original_invoice_id = self.order_id.invoice_ids[0].id
        
        _logger.info(f"Created subscription {subscription.name} from sale order line {self.id}")
        
        return subscription
    
    def _calculate_subscription_end_date(self, start_date):
        """Calculate the subscription end date based on the product settings"""
        if not self.product_id.is_recurring:
            # For non-recurring subscriptions, use default duration or 1 year
            duration_months = getattr(self.product_id, 'default_subscription_duration', 12)
            return start_date + relativedelta(months=duration_months)
        
        # For recurring subscriptions, use the recurring period
        if self.product_id.recurring_period == 'monthly':
            return start_date + relativedelta(months=1)
        elif self.product_id.recurring_period == 'quarterly':
            return start_date + relativedelta(months=3)
        elif self.product_id.recurring_period == 'semiannual':
            return start_date + relativedelta(months=6)
        else:  # yearly
            return start_date + relativedelta(years=1)
    
    def _generate_membership_number(self):
        """Generate a unique membership number"""
        sequence = self.env['ir.sequence'].next_by_code('ams.membership.number')
        if not sequence:
            # Fallback if sequence doesn't exist
            sequence = str(self.env['ams.subscription'].search_count([]) + 1).zfill(6)
        return f"MEM{sequence}"
    
    def _find_or_create_parent_membership(self):
        """Find existing membership for the partner or create one if needed"""
        partner = self.order_id.partner_id
        
        # Look for existing active membership
        existing_membership = self.env['ams.subscription'].search([
            ('partner_id', '=', partner.id),
            ('subscription_code', '=', 'membership'),
            ('state', '=', 'active')
        ], limit=1)
        
        if existing_membership:
            return existing_membership
        
        # Check if there's a membership product in the same order
        membership_line = self.order_id.order_line.filtered(
            lambda l: l.product_id.subscription_type_id.code == 'membership' and l != self
        )
        
        if membership_line and membership_line.subscription_id:
            return membership_line.subscription_id
        
        # For now, return None - the chapter subscription will need to be linked manually
        # In a more advanced implementation, you might auto-create a basic membership
        return None
    
    def _determine_chapter_from_context(self):
        """Try to determine which chapter this subscription should belong to"""
        partner = self.order_id.partner_id
        
        # Method 1: Check if product is linked to a specific chapter
        if hasattr(self.product_id, 'chapter_id') and self.product_id.chapter_id:
            return self.product_id.chapter_id
        
        # Method 2: Use partner's address to suggest local chapter
        if partner.country_id and partner.state_id:
            local_chapter = self.env['ams.chapter'].search([
                ('country_id', '=', partner.country_id.id),
                ('state_province', '=', partner.state_id.name),
                ('active', '=', True)
            ], limit=1)
            if local_chapter:
                return local_chapter
        
        # Method 3: Use country-level chapter
        if partner.country_id:
            country_chapter = self.env['ams.chapter'].search([
                ('country_id', '=', partner.country_id.id),
                ('active', '=', True)
            ], limit=1)
            if country_chapter:
                return country_chapter
        
        return None
    
    def action_create_subscription(self):
        """Manual action to create subscription from order line"""
        self.ensure_one()
        
        if not self.product_id.is_subscription_product:
            raise UserError(_("This product is not a subscription product"))
        
        if self.subscription_id:
            raise UserError(_("Subscription already exists for this line"))
        
        subscription = self._create_subscription_from_line()
        
        if subscription:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Created Subscription'),
                'res_model': 'ams.subscription',
                'view_mode': 'form',
                'res_id': subscription.id,
                'target': 'current',
            }
    
    def action_view_subscription(self):
        """Action to view the subscription created from this line"""
        self.ensure_one()
        
        if not self.subscription_id:
            raise UserError(_("No subscription exists for this line"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription'),
            'res_model': 'ams.subscription',
            'view_mode': 'form',
            'res_id': self.subscription_id.id,
            'target': 'current',
        }