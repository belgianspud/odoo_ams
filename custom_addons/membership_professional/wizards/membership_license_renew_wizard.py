from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class LicenseRenewWizard(models.TransientModel):
    _name = 'membership.license.renew.wizard'
    _description = 'License Renewal Wizard'

    license_id = fields.Many2one('membership.license', required=True)
    new_expiration_date = fields.Date(required=True)
    
    def action_renew(self):
        self.license_id.write({
            'expiration_date': self.new_expiration_date,
            'last_renewal_date': fields.Date.today(),
        })
        return {'type': 'ir.actions.act_window_close'}