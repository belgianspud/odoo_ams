from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class AMSSubscriptionAnalytics(models.Model):
    _name = 'ams.subscription.analytics'
    _description = 'AMS Subscription Analytics'
    _auto = False
    _order = 'date desc'
    
    # Dimensions
    date = fields.Date('Date', readonly=True)
    subscription_id = fields.Many2one('ams.subscription', 'Subscription', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Member', readonly=True)
    subscription_type_id = fields.Many2one('ams.subscription.type', 'Subscription Type', readonly=True)
    chapter_id = fields.Many2one('ams.chapter', 'Chapter', readonly=True)
    subscription_code = fields.Selection([
        ('membership', 'Membership'),
        ('chapter', 'Chapter'),
        ('publication', 'Publication')
    ], string='Type Code', readonly=True)
    
    # States
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('terminated', 'Terminated'),
        ('pending_renewal', 'Pending Renewal')
    ], string='Status', readonly=True)
    
    # Financial Measures
    amount = fields.Monetary('Amount', currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    
    # Count Measures  
    subscription_count = fields.Integer('Subscription Count', readonly=True)
    new_subscriptions = fields.Integer('New Subscriptions', readonly=True)
    renewed_subscriptions = fields.Integer('Renewed Subscriptions', readonly=True)
    cancelled_subscriptions = fields.Integer('Cancelled Subscriptions', readonly=True)
    
    # Revenue Measures
    subscription_revenue = fields.Monetary('Subscription Revenue', currency_field='currency_id', readonly=True)
    renewal_revenue = fields.Monetary('Renewal Revenue', currency_field='currency_id', readonly=True)
    total_revenue = fields.Monetary('Total Revenue', currency_field='currency_id', readonly=True)
    
    # Duration Measures
    avg_subscription_duration = fields.Float('Avg Duration (Days)', readonly=True)
    
    # Geographic Dimensions
    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    state_id = fields.Many2one('res.country.state', 'State', readonly=True)
    
    # Temporal Dimensions
    year = fields.Char('Year', readonly=True)
    quarter = fields.Char('Quarter', readonly=True) 
    month = fields.Char('Month', readonly=True)
    week = fields.Char('Week', readonly=True)
    
    def init(self):
        """Create the view"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () AS id,
                    s.create_date::date AS date,
                    s.id AS subscription_id,
                    s.partner_id,
                    s.subscription_type_id,
                    s.chapter_id,
                    st.code AS subscription_code,
                    s.state,
                    s.amount,
                    s.currency_id,
                    
                    -- Count measures
                    1 AS subscription_count,
                    CASE WHEN s.create_date::date = s.start_date THEN 1 ELSE 0 END AS new_subscriptions,
                    CASE WHEN s.last_renewal_date IS NOT NULL THEN 1 ELSE 0 END AS renewed_subscriptions,
                    CASE WHEN s.state IN ('cancelled', 'terminated') THEN 1 ELSE 0 END AS cancelled_subscriptions,
                    
                    -- Revenue measures
                    CASE WHEN s.state = 'active' THEN s.amount ELSE 0 END AS subscription_revenue,
                    CASE WHEN s.last_renewal_date IS NOT NULL THEN s.amount ELSE 0 END AS renewal_revenue,
                    s.amount AS total_revenue,
                    
                    -- Duration measures
                    CASE 
                        WHEN s.end_date IS NOT NULL AND s.start_date IS NOT NULL 
                        THEN EXTRACT(days FROM (s.end_date - s.start_date))
                        ELSE 0 
                    END AS avg_subscription_duration,
                    
                    -- Geographic dimensions
                    p.country_id,
                    p.state_id,
                    
                    -- Temporal dimensions
                    EXTRACT(year FROM s.create_date) AS year,
                    'Q' || EXTRACT(quarter FROM s.create_date) AS quarter,
                    TO_CHAR(s.create_date, 'YYYY-MM') AS month,
                    EXTRACT(week FROM s.create_date) AS week
                    
                FROM ams_subscription s
                LEFT JOIN ams_subscription_type st ON s.subscription_type_id = st.id
                LEFT JOIN res_partner p ON s.partner_id = p.id
                WHERE s.create_date IS NOT NULL
            )
        """ % self._table)

class AMSSubscriptionKPI(models.Model):
    _name = 'ams.subscription.kpi'
    _description = 'AMS Subscription KPIs'
    _rec_name = 'kpi_name'
    
    kpi_name = fields.Char('KPI Name', required=True)
    kpi_value = fields.Float('KPI Value')
    kpi_date = fields.Date('Date', default=fields.Date.today)
    kpi_type = fields.Selection([
        ('count', 'Count'),
        ('percentage', 'Percentage'),
        ('amount', 'Amount'),
        ('duration', 'Duration')
    ], string='KPI Type', required=True)
    
    @api.model
    def calculate_subscription_kpis(self, date_from=None, date_to=None):
        """Calculate and store subscription KPIs"""
        if not date_from:
            date_from = fields.Date.today() - relativedelta(months=1)
        if not date_to:
            date_to = fields.Date.today()
        
        # Get subscription data for the period
        subscriptions = self.env['ams.subscription'].search([
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to)
        ])
        
        # Calculate KPIs
        kpis = []
        
        # Total Active Subscriptions
        total_active = len(subscriptions.filtered(lambda s: s.state == 'active'))
        kpis.append({
            'kpi_name': 'Total Active Subscriptions',
            'kpi_value': total_active,
            'kpi_type': 'count',
            'kpi_date': date_to
        })
        
        # Monthly Recurring Revenue (MRR)
        monthly_revenue = sum(subscriptions.filtered(
            lambda s: s.state == 'active' and s.recurring_period == 'monthly'
        ).mapped('amount'))
        kpis.append({
            'kpi_name': 'Monthly Recurring Revenue',
            'kpi_value': monthly_revenue,
            'kpi_type': 'amount',
            'kpi_date': date_to
        })
        
        # Annual Recurring Revenue (ARR)
        yearly_subs = subscriptions.filtered(
            lambda s: s.state == 'active' and s.recurring_period == 'yearly'
        )
        quarterly_subs = subscriptions.filtered(
            lambda s: s.state == 'active' and s.recurring_period == 'quarterly'
        )
        arr = (sum(yearly_subs.mapped('amount')) + 
               sum(quarterly_subs.mapped('amount')) * 4 + 
               monthly_revenue * 12)
        kpis.append({
            'kpi_name': 'Annual Recurring Revenue',
            'kpi_value': arr,
            'kpi_type': 'amount',
            'kpi_date': date_to
        })
        
        # Churn Rate
        if total_active > 0:
            churned = len(subscriptions.filtered(
                lambda s: s.state in ('cancelled', 'terminated')
            ))
            churn_rate = (churned / (total_active + churned)) * 100
        else:
            churn_rate = 0
        kpis.append({
            'kpi_name': 'Churn Rate',
            'kpi_value': churn_rate,
            'kpi_type': 'percentage',
            'kpi_date': date_to
        })
        
        # Average Revenue Per User (ARPU)
        if total_active > 0:
            total_revenue = sum(subscriptions.filtered(
                lambda s: s.state == 'active'
            ).mapped('amount'))
            arpu = total_revenue / total_active
        else:
            arpu = 0
        kpis.append({
            'kpi_name': 'Average Revenue Per User',
            'kpi_value': arpu,
            'kpi_type': 'amount',
            'kpi_date': date_to
        })
        
        # Renewal Rate
        renewable_subs = subscriptions.filtered('is_recurring')
        if renewable_subs:
            renewed_count = len(renewable_subs.filtered('last_renewal_date'))
            renewal_rate = (renewed_count / len(renewable_subs)) * 100
        else:
            renewal_rate = 0
        kpis.append({
            'kpi_name': 'Renewal Rate',
            'kpi_value': renewal_rate,
            'kpi_type': 'percentage',
            'kpi_date': date_to
        })
        
        # Customer Lifetime Value (CLV)
        # Simplified calculation: ARPU / Churn Rate * 12 (months)
        if churn_rate > 0:
            clv = (arpu / (churn_rate / 100)) * 12
        else:
            clv = arpu * 24  # Assume 2 year lifetime if no churn
        kpis.append({
            'kpi_name': 'Customer Lifetime Value',
            'kpi_value': clv,
            'kpi_type': 'amount',
            'kpi_date': date_to
        })
        
        # Store KPIs
        for kpi_data in kpis:
            existing_kpi = self.search([
                ('kpi_name', '=', kpi_data['kpi_name']),
                ('kpi_date', '=', kpi_data['kpi_date'])
            ])
            
            if existing_kpi:
                existing_kpi.kpi_value = kpi_data['kpi_value']
            else:
                self.create(kpi_data)
        
        return len(kpis)
    
    @api.model
    def get_dashboard_data(self):
        """Get dashboard data for frontend display"""
        today = fields.Date.today()
        
        # Get latest KPIs
        latest_kpis = {}
        for kpi_name in ['Total Active Subscriptions', 'Monthly Recurring Revenue', 
                        'Annual Recurring Revenue', 'Churn Rate', 'Renewal Rate']:
            kpi = self.search([
                ('kpi_name', '=', kpi_name)
            ], order='kpi_date desc', limit=1)
            
            if kpi:
                latest_kpis[kpi_name.lower().replace(' ', '_')] = {
                    'value': kpi.kpi_value,
                    'type': kpi.kpi_type,
                    'date': kpi.kpi_date
                }
        
        # Get subscription counts by status
        subscription_counts = {}
        for state in ['active', 'grace', 'suspended', 'expired', 'cancelled']:
            count = self.env['ams.subscription'].search_count([('state', '=', state)])
            subscription_counts[state] = count
        
        # Get revenue by subscription type
        revenue_by_type = {}
        for sub_type in self.env['ams.subscription.type'].search([]):
            revenue = sum(self.env['ams.subscription'].search([
                ('subscription_type_id', '=', sub_type.id),
                ('state', '=', 'active')
            ]).mapped('amount'))
            if revenue > 0:
                revenue_by_type[sub_type.name] = revenue
        
        # Get monthly trends (last 12 months)
        monthly_trends = []
        for i in range(12):
            month_date = today - relativedelta(months=i)
            month_start = month_date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - relativedelta(days=1)
            
            new_subs = self.env['ams.subscription'].search_count([
                ('create_date', '>=', month_start),
                ('create_date', '<=', month_end)
            ])
            
            monthly_trends.insert(0, {
                'month': month_date.strftime('%Y-%m'),
                'new_subscriptions': new_subs
            })
        
        return {
            'kpis': latest_kpis,
            'subscription_counts': subscription_counts,
            'revenue_by_type': revenue_by_type,
            'monthly_trends': monthly_trends,
            'last_updated': fields.Datetime.now()
        }

class AMSRevenueReport(models.TransientModel):
    _name = 'ams.revenue.report'
    _description = 'AMS Revenue Report Generator'
    
    date_from = fields.Date('From Date', required=True, 
                           default=lambda self: fields.Date.today() - relativedelta(months=1))
    date_to = fields.Date('To Date', required=True, default=fields.Date.today)
    
    subscription_type_ids = fields.Many2many(
        'ams.subscription.type', 
        string='Subscription Types',
        help="Leave empty to include all types"
    )
    
    chapter_ids = fields.Many2many(
        'ams.chapter',
        string='Chapters', 
        help="Leave empty to include all chapters"
    )
    
    include_cancelled = fields.Boolean('Include Cancelled', default=False)
    group_by = fields.Selection([
        ('type', 'Subscription Type'),  
        ('chapter', 'Chapter'),
        ('month', 'Month'),
        ('partner', 'Member')
    ], string='Group By', default='type')
    
    def generate_report(self):
        """Generate revenue report"""
        domain = [
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to)
        ]
        
        if not self.include_cancelled:
            domain.append(('state', 'not in', ['cancelled', 'terminated']))
        
        if self.subscription_type_ids:
            domain.append(('subscription_type_id', 'in', self.subscription_type_ids.ids))
            
        if self.chapter_ids:
            domain.append(('chapter_id', 'in', self.chapter_ids.ids))
        
        subscriptions = self.env['ams.subscription'].search(domain)
        
        # Generate report data based on grouping
        report_data = {}
        
        for subscription in subscriptions:
            if self.group_by == 'type':
                key = subscription.subscription_type_id.name
            elif self.group_by == 'chapter':
                key = subscription.chapter_id.name if subscription.chapter_id else 'No Chapter'
            elif self.group_by == 'month':
                key = subscription.create_date.strftime('%Y-%m')
            else:  # partner
                key = subscription.partner_id.name
            
            if key not in report_data:
                report_data[key] = {
                    'count': 0,
                    'revenue': 0,
                    'active_count': 0
                }
            
            report_data[key]['count'] += 1
            report_data[key]['revenue'] += subscription.amount
            if subscription.state == 'active':
                report_data[key]['active_count'] += 1
        
        # Create report display
        return {
            'name': _('Revenue Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.revenue.report.line',
            'view_mode': 'tree',
            'target': 'new',
            'context': {
                'default_report_data': report_data,
                'default_date_from': self.date_from,
                'default_date_to': self.date_to
            }
        }

class AMSRevenueReportLine(models.TransientModel):
    _name = 'ams.revenue.report.line'
    _description = 'Revenue Report Line'
    
    name = fields.Char('Group', required=True)
    subscription_count = fields.Integer('Subscriptions')
    active_count = fields.Integer('Active')
    revenue = fields.Monetary('Revenue', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)