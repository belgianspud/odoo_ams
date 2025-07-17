from odoo import models, fields, api

class AMSChapter(models.Model):
    _name = 'ams.chapter'
    _description = 'AMS Chapter'
    _order = 'name'
    _rec_name = 'name'
    
    name = fields.Char('Chapter Name', required=True)
    code = fields.Char('Chapter Code', required=True, help="Unique identifier for the chapter")
    region = fields.Char('Region')
    state_province = fields.Char('State/Province')
    country_id = fields.Many2one('res.country', 'Country')
    city = fields.Char('City')
    
    # Contact Information
    contact_person = fields.Char('Contact Person')
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    website = fields.Char('Website')
    address = fields.Text('Address')
    
    # Chapter Details
    description = fields.Html('Description')
    active = fields.Boolean('Active', default=True)
    member_count = fields.Integer('Member Count', compute='_compute_member_count', store=True)
    founding_date = fields.Date('Founding Date')
    
    # Product Integration
    product_template_id = fields.Many2one('product.template', 'Chapter Product')
    chapter_fee = fields.Float('Chapter Fee', default=0.0, help="Additional fee for joining this chapter")
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                 default=lambda self: self.env.company.currency_id)
    
    # Relationships
    subscription_ids = fields.One2many('ams.subscription', 'chapter_id', 'Chapter Subscriptions')
    
    # Computed Fields
    active_member_count = fields.Integer('Active Members', compute='_compute_member_count', store=True)
    
    @api.depends('subscription_ids', 'subscription_ids.state')
    def _compute_member_count(self):
        for chapter in self:
            all_subscriptions = chapter.subscription_ids
            chapter.member_count = len(all_subscriptions)
            chapter.active_member_count = len(all_subscriptions.filtered(lambda s: s.state == 'active'))
    
    @api.model
    def create(self, vals):
        chapter = super().create(vals)
        # Auto-create chapter product if chapter fee is set
        if chapter.chapter_fee > 0 and not chapter.product_template_id:
            chapter._create_chapter_product()
        return chapter
    
    def write(self, vals):
        result = super().write(vals)
        # Update or create product if chapter fee changes
        if 'chapter_fee' in vals:
            for chapter in self:
                if chapter.chapter_fee > 0 and not chapter.product_template_id:
                    chapter._create_chapter_product()
                elif chapter.product_template_id and chapter.chapter_fee > 0:
                    chapter.product_template_id.list_price = chapter.chapter_fee
        return result
    
    def _create_chapter_product(self):
        """Create a product for this chapter"""
        if not self.product_template_id and self.chapter_fee > 0:
            # Find or create chapter subscription type
            chapter_type = self.env['ams.subscription.type'].search([('code', '=', 'chapter')], limit=1)
            if not chapter_type:
                chapter_type = self.env.ref('ams_subscriptions.subscription_type_chapter', False)
            
            product_vals = {
                'name': f"Chapter Membership - {self.name}",
                'type': 'service',
                'categ_id': self.env.ref('product.product_category_all').id,
                'list_price': self.chapter_fee,
                'standard_price': self.chapter_fee,
                'description_sale': f"Membership fee for {self.name} chapter",
                'is_subscription_product': True,
                'subscription_type_id': chapter_type.id if chapter_type else False,
            }
            
            product_template = self.env['product.template'].create(product_vals)
            self.product_template_id = product_template.id
    
    def action_view_members(self):
        """Action to view chapter members"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} Members',
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form',
            'domain': [('chapter_id', '=', self.id), ('subscription_code', '=', 'chapter')],
            'context': {
                'default_chapter_id': self.id,
                'default_subscription_code': 'chapter',
            }
        }
    
    def action_view_active_members(self):
        """Action to view active chapter members"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} Active Members',
            'res_model': 'ams.subscription',
            'view_mode': 'tree,form',
            'domain': [('chapter_id', '=', self.id), ('subscription_code', '=', 'chapter'), ('state', '=', 'active')],
            'context': {
                'default_chapter_id': self.id,
                'default_subscription_code': 'chapter',
                'search_default_active': 1,
            }
        }
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Chapter code must be unique!'),
        ('name_unique', 'unique(name)', 'Chapter name must be unique!'),
    ]