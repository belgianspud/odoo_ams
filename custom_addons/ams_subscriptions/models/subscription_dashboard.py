from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import json

class AMSSubscriptionDashboard(models.Model):
    """Dashboard model for subscription analytics"""
    _name = 'ams.subscription.dashboard'
    _description = 'Subscription Dashboard'

    @api.model
    def get_subscription_dashboard_data(self):
        """Get comprehensive dashboard data"""
        today = date.today()
        
        return {
            'mrr_data': self._get_mrr_data(),
            'churn_data': self._get_churn_data(), 
            'cohort_data': self._get_cohort_data(),
            'revenue_forecast': self._get_revenue_forecast(),
            'subscription_metrics': self._get_subscription_metrics(),
            'payment_health': self._get_payment_health(),
            'chapter_performance': self._get_chapter_performance(),
            'membership_type_analysis': self._get_membership_type_analysis()
        }

    def _get_mrr_data(self):
        """Calculate MRR trends and metrics"""
        # Get current MRR
        active_subscriptions = self.env['ams.member.subscription'].search([
            ('state', 'in', ['active', 'pending_renewal'])
        ])
        
        current_mrr = sum(active_subscriptions.mapped('mrr_amount'))
        current_arr = sum(active_subscriptions.mapped('arr_amount'))
        
        # Get MRR trend for last 12 months
        mrr_trend = []
        for i in range(12):
            month_date = date.today() - relativedelta(months=i)
            month_start = month_date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            # Get subscriptions active during this month
            month_subscriptions = self.env['ams.member.subscription'].search([
                ('start_date', '<=', month_end),
                '|', ('end_date', '>=', month_start), ('end_date', '=', False),
                ('state', 'in', ['active', 'pending_renewal', 'expired', 'lapsed'])
            ])
            
            month_mrr = sum(month_subscriptions.mapped('mrr_amount'))
            
            mrr_trend.append({
                'month': month_date.strftime('%Y-%m'),
                'month_name': month_date.strftime('%B %Y'),
                'mrr': month_mrr,
                'subscribers': len(month_subscriptions)
            })
        
        # Calculate growth rates
        if len(mrr_trend) >= 2:
            current_month_mrr = mrr_trend[0]['mrr']
            previous_month_mrr = mrr_trend[1]['mrr']
            mrr_growth_rate = ((current_month_mrr - previous_month_mrr) / previous_month_mrr * 100) if previous_month_mrr > 0 else 0
        else:
            mrr_growth_rate = 0
        
        return {
            'current_mrr': current_mrr,
            'current_arr': current_arr,
            'mrr_growth_rate': mrr_growth_rate,
            'mrr_trend': list(reversed(mrr_trend)),  # Reverse to show chronological order
            'total_subscribers': len(active_subscriptions)
        }

    def _get_churn_data(self):
        """Calculate churn rate and analysis"""
        today = date.today()
        
        # Current month churn
        month_start = today.replace(day=1)
        
        # Subscriptions that were active at start of month
        active_start_month = self.env['ams.member.subscription'].search([
            ('start_date', '<', month_start),
            ('state', 'in', ['active', 'pending_renewal', 'expired', 'lapsed', 'cancelled'])
        ])
        
        # Subscriptions that churned this month
        churned_this_month = active_start_month.filtered(
            lambda s: s.state in ['lapsed', 'cancelled'] and 
            s.end_date and s.end_date >= month_start
        )
        
        # Calculate churn rate
        if len(active_start_month) > 0:
            churn_rate = (len(churned_this_month) / len(active_start_month)) * 100
        else:
            churn_rate = 0
        
        # Churn reasons (this would need to be captured in the subscription model)
        churn_reasons = {}
        
        # Retention rate
        retention_rate = 100 - churn_rate
        
        return {
            'current_churn_rate': churn_rate,
            'retention_rate': retention_rate,
            'churned_this_month': len(churned_this_month),
            'churn_reasons': churn_reasons,
            'at_risk_subscribers': self._get_at_risk_subscribers()
        }

    def _get_at_risk_subscribers(self):
        """Get subscribers at risk of churning"""
        today = date.today()
        
        # Subscriptions expiring in next 30 days without renewal
        at_risk = self.env['ams.member.subscription'].search([
            ('state', '=', 'active'),
            ('end_date', '<=', today + timedelta(days=30)),
            ('auto_renew', '=', False),
            ('renewal_sent', '=', False)
        ])
        
        # Subscriptions with payment issues
        payment_issues = self.env['ams.member.subscription'].search([
            ('state', '=', 'active'),
            ('dunning_level', 'in', ['2', '3', '4'])
        ])
        
        return {
            'expiring_soon': len(at_risk),
            'payment_issues': len(payment_issues),
            'total_at_risk': len(at_risk) + len(payment_issues)
        }

    def _get_cohort_data(self):
        """Generate cohort analysis data"""
        # This is a simplified cohort analysis
        # In production, you might want to pre-calculate this data
        
        cohorts = {}
        cohort_months = []
        
        # Get last 12 months for cohort analysis
        for i in range(12):
            cohort_date = date.today() - relativedelta(months=i)
            cohort_month = cohort_date.strftime('%Y-%m')
            cohort_months.append(cohort_month)
            
            # Get new subscriptions for this cohort month
            new_subs = self.env['ams.member.subscription'].search([
                ('start_date', '>=', cohort_date.replace(day=1)),
                ('start_date', '<', (cohort_date + relativedelta(months=1)).replace(day=1)),
                ('parent_subscription_id', '=', False)  # Only new, not renewals
            ])
            
            if new_subs:
                cohorts[cohort_month] = {
                    'initial_count': len(new_subs),
                    'retention_by_month': {}
                }
                
                # Calculate retention for each subsequent month
                for j in range(min(i + 1, 12)):  # Don't go beyond current date
                    retention_month = cohort_date + relativedelta(months=j)
                    
                    still_active = new_subs.filtered(
                        lambda s: s.state in ['active', 'pending_renewal'] or 
                        (s.end_date and s.end_date >= retention_month.replace(day=1))
                    )
                    
                    retention_rate = (len(still_active) / len(new_subs)) * 100
                    cohorts[cohort_month]['retention_by_month'][j] = retention_rate
        
        return {
            'cohorts': cohorts,
            'cohort_months': list(reversed(cohort_months))
        }

    def _get_revenue_forecast(self):
        """Generate revenue forecast"""
        # Simple forecast based on current MRR and growth trends
        mrr_data = self._get_mrr_data()
        current_mrr = mrr_data['current_mrr']
        growth_rate = mrr_data['mrr_growth_rate']
        
        forecast = []
        for i in range(12):  # 12 month forecast
            forecast_date = date.today() + relativedelta(months=i)
            
            # Apply growth rate (simplified model)
            forecasted_mrr = current_mrr * ((1 + (growth_rate / 100)) ** i)
            
            forecast.append({
                'month': forecast_date.strftime('%Y-%m'),
                'month_name': forecast_date.strftime('%B %Y'),
                'forecasted_mrr': forecasted_mrr,
                'forecasted_arr': forecasted_mrr * 12
            })
        
        return forecast

    def _get_subscription_metrics(self):
        """Get key subscription metrics"""
        total_subs = self.env['ams.member.subscription'].search_count([])
        active_subs = self.env['ams.member.subscription'].search_count([
            ('state', 'in', ['active', 'pending_renewal'])
        ])
        pending_approval = self.env['ams.member.subscription'].search_count([
            ('state', '=', 'pending_approval')
        ])
        
        # New subscriptions this month
        month_start = date.today().replace(day=1)
        new_this_month = self.env['ams.member.subscription'].search_count([
            ('start_date', '>=', month_start),
            ('parent_subscription_id', '=', False)
        ])
        
        return {
            'total_subscriptions': total_subs,
            'active_subscriptions': active_subs,
            'pending_approval': pending_approval,
            'new_this_month': new_this_month,
            'activation_rate': (active_subs / total_subs * 100) if total_subs > 0 else 0
        }

    def _get_payment_health(self):
        """Analyze payment health metrics"""
        # Payment success rates
        total_invoices = self.env['account.move'].search_count([
            ('is_membership_invoice', '=', True),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date.today() - timedelta(days=30))
        ])
        
        paid_invoices = self.env['account.move'].search_count([
            ('is_membership_invoice', '=', True),
            ('state', '=', 'posted'),
            ('payment_state', '=', 'paid'),
            ('invoice_date', '>=', date.today() - timedelta(days=30))
        ])
        
        # Dunning statistics
        dunning_stats = {}
        for level in ['1', '2', '3', '4']:
            count = self.env['ams.member.subscription'].search_count([
                ('dunning_level', '=', level)
            ])
            dunning_stats[f'level_{level}'] = count
        
        return {
            'payment_success_rate': (paid_invoices / total_invoices * 100) if total_invoices > 0 else 0,
            'total_invoices_30d': total_invoices,
            'paid_invoices_30d': paid_invoices,
            'dunning_statistics': dunning_stats,
            'auto_pay_enabled': self.env['ams.member.subscription'].search_count([
                ('auto_payment', '=', True),
                ('state', 'in', ['active', 'pending_renewal'])
            ])
        }

    def _get_chapter_performance(self):
        """Analyze performance by chapter"""
        chapters = self.env['ams.chapter'].search([('active', '=', True)])
        
        chapter_data = []
        for chapter in chapters:
            chapter_subs = self.env['ams.member.subscription'].search([
                ('chapter_id', '=', chapter.id),
                ('state', 'in', ['active', 'pending_renewal'])
            ])
            
            chapter_mrr = sum(chapter_subs.mapped('mrr_amount'))
            
            chapter_data.append({
                'chapter_id': chapter.id,
                'chapter_name': chapter.name,
                'subscriber_count': len(chapter_subs),
                'mrr': chapter_mrr,
                'arr': chapter_mrr * 12
            })
        
        # Sort by MRR descending
        chapter_data.sort(key=lambda x: x['mrr'], reverse=True)
        
        return chapter_data

    def _get_membership_type_analysis(self):
        """Analyze performance by membership type"""
        membership_types = self.env['ams.membership.type'].search([('active', '=', True)])
        
        type_data = []
        for mtype in membership_types:
            type_subs = self.env['ams.member.subscription'].search([
                ('membership_type_id', '=', mtype.id),
                ('state', 'in', ['active', 'pending_renewal'])
            ])
            
            type_mrr = sum(type_subs.mapped('mrr_amount'))
            
            type_data.append({
                'type_id': mtype.id,
                'type_name': mtype.name,
                'subscriber_count': len(type_subs),
                'mrr': type_mrr,
                'arr': type_mrr * 12,
                'avg_price': mtype.price
            })
        
        # Sort by subscriber count descending
        type_data.sort(key=lambda x: x['subscriber_count'], reverse=True)
        
        return type_data

    @api.model
    def get_subscription_kpis(self):
        """Get key performance indicators for subscriptions"""
        data = self.get_subscription_dashboard_data()
        
        return {
            'mrr': data['mrr_data']['current_mrr'],
            'arr': data['mrr_data']['current_arr'],
            'total_subscribers': data['mrr_data']['total_subscribers'],
            'churn_rate': data['churn_data']['current_churn_rate'],
            'growth_rate': data['mrr_data']['mrr_growth_rate'],
            'payment_success_rate': data['payment_health']['payment_success_rate'],
            'new_subscriptions': data['subscription_metrics']['new_this_month'],
            'at_risk_count': data['churn_data']['at_risk_subscribers']['total_at_risk']
        }