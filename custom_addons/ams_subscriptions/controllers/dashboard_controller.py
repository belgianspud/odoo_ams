from odoo import http
from odoo.http import request
import json

class SubscriptionDashboardController(http.Controller):
    
    @http.route('/ams/dashboard/subscription-data', type='json', auth='user')
    def get_subscription_dashboard_data(self):
        """API endpoint for dashboard data"""
        dashboard = request.env['ams.subscription.dashboard']
        return dashboard.get_subscription_dashboard_data()
    
    @http.route('/ams/dashboard/kpis', type='json', auth='user')
    def get_subscription_kpis(self):
        """API endpoint for KPIs"""
        dashboard = request.env['ams.subscription.dashboard']
        return dashboard.get_subscription_kpis()
        
    @http.route('/ams/dashboard/export-data', type='http', auth='user')
    def export_dashboard_data(self, **kwargs):
        """Export dashboard data to Excel/CSV"""
        dashboard = request.env['ams.subscription.dashboard']
        data = dashboard.get_subscription_dashboard_data()
        
        # Convert to Excel using xlsxwriter or pandas
        # This would require additional implementation
        
        return request.make_response(
            json.dumps(data, indent=2, default=str),
            headers=[
                ('Content-Type', 'application/json'),
                ('Content-Disposition', 'attachment; filename="subscription_dashboard.json"')
            ]
        )