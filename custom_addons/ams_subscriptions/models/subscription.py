from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AMSSubscription(models.Model):
    _name = 'ams.subscription'
    _description = 'AMS Subscription'
    _order = 'create_date desc'
    
    name = fields.Char(string='Subscription Name', required=True)
    partner_id = fields.Many2one('res.partner', string='Member', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.today)
    end_date = fields.Date(string='End Date', required=False)
    
    # Updated subscription_type to maintain backward compatibility
    subscription_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),        
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime')
    ], string='Billing Cycle', default='yearly')
    
    # NEW: Subscription Type (membership, chapter, publication)
    subscription_type_id = fields.Many2one('ams.subscription.type', 'Subscription Type', required=True)
    subscription_code = fields.Selection(related='subscription_type_id.code', store=True, string='Type Code')
    
    amount = fields.Float(string='Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 default=lambda self: self.env.company.currency_id)
    
    notes = fields.Text(string='Notes')
    
    # NEW: Product Integration
    product_id = fields.Many2one('product.product', 'Related Product')
    sale_order_line_id = fields.Many2one('sale.order.line', 'Source Sale Line')
    
    # NEW: Invoice Integration
    invoice_ids = fields.One2many('account.move', 'subscription_id', 'Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoice Count')
    
    # NEW: Hierarchy for chapters
    parent_subscription_id = fields.Many2one('ams.subscription', 'Parent Subscription',
                                           domain="[('subscription_code', '=', 'membership'), ('partner_id', '=', partner_id)]")
    child_subscription_ids = fields.One2many('ams.subscription', 'parent_subscription_id', 'Child Subscriptions')
    
    # UPDATED: Chapter-specific fields with lookup
    chapter_id = fields.Many2one('ams.chapter', 'Chapter', 
                                domain="[('active', '=', True)]",
                                help="Select the chapter for this subscription")
    chapter_region = fields.Char(related='chapter_id.region', store=True, readonly=True, string='Chapter Region')
    
    # NEW: Publication-specific fields
    publication_format = fields.Selection([
        ('print', 'Print'),
        ('digital', 'Digital'),
        ('both', 'Print + Digital')
    ], 'Publication Format')
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)
    
    @api.model_create_multi
    def create(self, vals_list):
        # Auto-generate subscription name if not provided
        for vals in vals_list:
            if not vals.get('name'):
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                subscription_type = self.env['ams.subscription.type'].browse(vals.get('subscription_type_id'))
                vals['name'] = f"{subscription_type.name} - {partner.name}"
        
        subscriptions = super().create(vals_list)
        
        # Handle subscription type-specific creation logic
        for subscription in subscriptions:
            subscription._handle_subscription_creation()
        
        return subscriptions
    
    def _handle_subscription_creation(self):
        """Handle subscription type-specific creation logic"""
        if self.subscription_code == 'membership':
            self._handle_membership_creation()
        elif self.subscription_code == 'chapter':
            self._handle_chapter_creation()
        elif self.subscription_code == 'publication':
            self._handle_publication_creation()
    
    def _handle_membership_creation(self):
        """Handle membership-specific logic"""
        if self.subscription_type_id.creates_invoice and not self.sale_order_line_id:
            self._create_subscription_invoice()
    
    def _handle_chapter_creation(self):
        """Handle chapter-specific logic"""
        if not self.parent_subscription_id:
            raise UserError("Chapter subscriptions must have a parent membership.")
        
        # Validate parent subscription is active
        if self.parent_subscription_id.state not in ['active']:
            raise UserError("Parent membership must be active to add a chapter.")
        
        # Auto-set chapter fee if chapter is selected and no amount is set
        if self.chapter_id and not self.amount:
            chapter = self.chapter_id  # Get the actual record
            if chapter.chapter_fee > 0:
                self.amount = chapter.chapter_fee
        
        # Try to add to existing draft invoice of parent
        parent_invoice = self.parent_subscription_id._get_active_draft_invoice()
        if parent_invoice:
            self._add_to_existing_invoice(parent_invoice)
        elif self.subscription_type_id.creates_invoice:
            self._create_subscription_invoice()
    
    def _handle_publication_creation(self):
        """Handle publication-specific logic"""
        if self.subscription_type_id.creates_invoice and not self.sale_order_line_id:
            self._create_subscription_invoice()
    
    def _create_subscription_invoice(self):
        """Create invoice for subscription"""
        if not self.product_id:
            # Try to get product from subscription type or chapter
            if self.subscription_code == 'chapter' and self.chapter_id:
                chapter = self.chapter_id  # Get the actual record
                if chapter.product_template_id:
                    self.product_id = chapter.product_template_id.product_variant_id
            elif self.subscription_type_id.product_template_id:
                self.product_id = self.subscription_type_id.product_template_id.product_variant_id
            
            if not self.product_id:
                return
        
        # Prepare invoice description
        description = f"{self.subscription_type_id.name}: {self.name}"
        if self.subscription_code == 'chapter' and self.chapter_id:
            description += f" ({self.chapter_id.name})"
        
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'subscription_id': self.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'quantity': 1,
                'price_unit': self.amount or self.product_id.list_price,
                'name': description,
            })]
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        return invoice
    
    def _get_active_draft_invoice(self):
        """Get active draft invoice for this subscription"""
        return self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
    
    def _add_to_existing_invoice(self, invoice):
        """Add this subscription to an existing draft invoice"""
        if not self.product_id:
            return
            
        # Prepare line description
        description = f"{self.subscription_type_id.name}: {self.name}"
        if self.subscription_code == 'chapter' and self.chapter_id:
            description += f" ({self.chapter_id.name})"
            
        invoice.write({
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'quantity': 1,
                'price_unit': self.amount or self.product_id.list_price,
                'name': description,
            })]
        })
    
    def action_view_invoices(self):
        """Action to view related invoices"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'context': {'default_partner_id': self.partner_id.id}
        }
    
    @api.constrains('parent_subscription_id', 'subscription_code')
    def _check_parent_subscription(self):
        """Validate parent subscription requirements"""
        for record in self:
            if record.subscription_type_id.requires_parent and not record.parent_subscription_id:
                raise ValidationError(f"{record.subscription_type_id.name} subscriptions require a parent membership.")
            
            if record.parent_subscription_id and record.parent_subscription_id.subscription_code != 'membership':
                raise ValidationError("Parent subscription must be a membership type.")
    
    @api.constrains('chapter_id', 'subscription_code')
    def _check_chapter_requirements(self):
        """Validate chapter requirements for chapter subscriptions"""
        for record in self:
            if record.subscription_code == 'chapter' and not record.chapter_id:
                raise ValidationError("Chapter subscriptions must have a chapter selected.")
    
    @api.onchange('chapter_id')
    def _onchange_chapter_id(self):
        """Auto-populate amount and product when chapter is selected"""
        if self.chapter_id and self.subscription_code == 'chapter':
            chapter = self.chapter_id  # Get the actual record
            if chapter.chapter_fee > 0:
                self.amount = chapter.chapter_fee
            if chapter.product_template_id:
                self.product_id = chapter.product_template_id.product_variant_id
    
    @api.onchange('subscription_type_id')
    def _onchange_subscription_type_id(self):
        """Clear fields that don't apply to the selected subscription type"""
        if self.subscription_type_id:
            if self.subscription_type_id.code != 'chapter':
                self.chapter_id = False
                self.parent_subscription_id = False
            if self.subscription_type_id.code != 'publication':
                self.publication_format = False
    
    # Keep existing methods
    def action_activate(self):
        self.state = 'active'
    
    def action_cancel(self):
        self.state = 'cancelled'
    
    def action_renew(self):
        self.state = 'active'
        # Extend end date based on subscription type
        if self.subscription_type == 'monthly':
            self.end_date = fields.Date.add(self.end_date or fields.Date.today(), months=1)
        elif self.subscription_type == 'yearly':
            self.end_date = fields.Date.add(self.end_date or fields.Date.today(), years=1)