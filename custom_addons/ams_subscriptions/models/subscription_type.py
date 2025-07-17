from odoo import models, fields, api

class AMSSubscriptionType(models.Model):
    _name = 'ams.subscription.type'
    _description = 'AMS Subscription Type'
    _order = 'sequence, name'
    
    name = fields.Char('Type Name', required=True)
    code = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication')
    ], string='Type Code', required=True)
    
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    description = fields.Html('Description')
    
    # Product Integration
    is_product = fields.Boolean('Is Product', default=True, 
                               help="Can this subscription type be sold as a product?")
    product_template_id = fields.Many2one('product.template', 'Related Product Template')
    auto_create_product = fields.Boolean('Auto Create Product', default=True)
    
    # Invoicing Settings
    creates_invoice = fields.Boolean('Creates Invoice', default=True)
    invoice_policy = fields.Selection([
        ('immediate', 'Immediate'),
        ('monthly', 'Monthly Billing'),
        ('yearly', 'Yearly Billing')
    ], 'Invoice Policy', default='immediate')
    
    # Hierarchy Settings (for chapters)
    can_have_children = fields.Boolean('Can Have Children', default=False)
    requires_parent = fields.Boolean('Requires Parent Subscription', default=False)
    parent_type_ids = fields.Many2many('ams.subscription.type', 'subscription_type_parent_rel',
                                      'child_id', 'parent_id', 'Allowed Parent Types')
    
    # E-commerce Settings
    website_published = fields.Boolean('Published on Website', default=False)
    pos_available = fields.Boolean('Available in POS', default=False)
    
    # Chapter-specific fields
    is_regional = fields.Boolean('Is Regional', help="For chapter subscriptions")
    
    # Publication-specific fields
    publication_format = fields.Selection([
        ('print', 'Print Only'),
        ('digital', 'Digital Only'),
        ('both', 'Print + Digital')
    ], 'Available Formats')
    
    @api.model
    def create(self, vals):
        subscription_type = super().create(vals)
        if vals.get('auto_create_product', True) and vals.get('is_product', True):
            subscription_type._create_related_product()
        return subscription_type
    
    def _create_related_product(self):
        """Create related product template"""
        if not self.product_template_id and self.is_product:
            product_vals = {
                'name': self.name,
                'type': 'service',
                'categ_id': self.env.ref('product.product_category_all').id,
                'subscription_type_id': self.id,
                'website_published': self.website_published,
                'available_in_pos': self.pos_available,
                'is_subscription_product': True,
                'list_price': 0.0,  # To be set manually
                'description_sale': self.description,
            }
            
            product_template = self.env['product.template'].create(product_vals)
            self.product_template_id = product_template.id
    
    @api.onchange('code')
    def _onchange_code(self):
        """Set default values based on subscription type code"""
        if self.code == 'membership':
            self.can_have_children = True
            self.requires_parent = False
            self.is_regional = False
        elif self.code == 'chapter':
            self.can_have_children = False
            self.requires_parent = True
            self.is_regional = True
            # Set allowed parent types to membership
            membership_types = self.search([('code', '=', 'membership')])
            self.parent_type_ids = [(6, 0, membership_types.ids)]
        elif self.code == 'publication':
            self.can_have_children = False
            self.requires_parent = False
            self.is_regional = False