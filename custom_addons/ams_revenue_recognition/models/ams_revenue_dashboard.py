# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import json
import logging

_logger = logging.getLogger(__name__)

class AMSRevenueDashboard(models.Model):
    """AMS Revenue Recognition Dashboard and Analytics"""
    _name = 'ams.revenue.dashboard'
    _description = 'AMS Revenue Recognition Dashboard'
    _rec_name = 'name'
    
    # Add basic fields for the model to work properly
    name = fields.Char(string='Dashboard Name', default='Revenue Recognition Dashboard')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    # Dashboard Data Methods
    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None):
        """Get comprehensive dashboard data for revenue recognition"""
        
        if not date_from:
            date_from = date.today().replace(day=1)  # First day of current month
        if not date_to:
            date_to = date.today()
        
        # Get core metrics
        overview_data = self._get_overview_metrics(date_from, date_to)
        recognition_trends = self._get_recognition_trends(date_from, date_to)
        schedule_status = self._get_schedule_status_breakdown()
        contract_modifications = self._get_modification_metrics(date_from, date_to)
        upcoming_recognitions = self._get_upcoming_recognitions()
        performance_obligations = self._get_performance_obligation_summary()
        
        return {
            'date_from': date_from,
            'date_to': date_to,
            'overview': overview_data,
            'recognition_trends': recognition_trends,
            'schedule_status': schedule_status,
            'contract_modifications': contract_modifications,
            'upcoming_recognitions': upcoming_recognitions,
            'performance_obligations': performance_obligations,
            'generated_at': fields.Datetime.now(),
        }
    
    def _get_overview_metrics(self, date_from, date_to):
        """Get high-level overview metrics"""
        
        # Total Contract Value (TCV)
        active_schedules = self.env['ams.revenue.schedule'].search([
            ('state', 'in', ['active', 'completed']),
            ('company_id', 'in', [self.env.company.id, False])
        ])
        total_contract_value = sum(active_schedules.mapped('total_contract_value'))
        
        # Revenue recognized in period
        period_recognitions = self.env['ams.revenue.recognition'].search([
            ('recognition_date', '>=', date_from),
            ('recognition_date', '<=', date_to),
            ('state', '=', 'posted'),
            ('schedule_id.company_id', 'in', [self.env.company.id, False])
        ])
        period_recognized = sum(period_recognitions.mapped('recognized_amount'))
        
        # Total deferred revenue
        total_deferred = sum(active_schedules.mapped('deferred_revenue_balance'))
        
        # Total recognized to date
        all_recognitions = self.env['ams.revenue.recognition'].search([
            ('state', '=', 'posted'),
            ('schedule_id.company_id', 'in', [self.env.company.id, False])
        ])
        total_recognized = sum(all_recognitions.mapped('recognized_amount'))
        
        # Active subscriptions with revenue recognition (if ams.subscription exists)
        active_subscriptions_count = 0
        if 'ams.subscription' in self.env:
            active_subscriptions = self.env['ams.subscription'].search([
                ('revenue_recognition_status', '=', 'active')
            ])
            active_subscriptions_count = len(active_subscriptions)
        
        # Monthly Recurring Revenue (MRR) - approximation
        monthly_recognition_amount = sum(
            active_schedules.filtered(
                lambda s: s.recognition_frequency == 'monthly'
            ).mapped('monthly_recognition_amount')
        )
        
        # Annual Recurring Revenue (ARR)
        annual_recurring_revenue = monthly_recognition_amount * 12
        
        # Recognition completion rate
        recognition_completion_rate = (
            (total_recognized / total_contract_value * 100) 
            if total_contract_value > 0 else 0
        )
        
        return {
            'total_contract_value': total_contract_value,
            'period_recognized': period_recognized,
            'total_deferred': total_deferred,
            'total_recognized': total_recognized,
            'active_subscriptions_count': active_subscriptions_count,
            'monthly_recurring_revenue': monthly_recognition_amount,
            'annual_recurring_revenue': annual_recurring_revenue,
            'recognition_completion_rate': recognition_completion_rate,
            'active_schedules_count': len(active_schedules.filtered(lambda s: s.state == 'active')),
        }
    
    def _get_recognition_trends(self, date_from, date_to):
        """Get revenue recognition trends over time"""
        
        # Get recognitions in the period
        recognitions = self.env['ams.revenue.recognition'].search([
            ('recognition_date', '>=', date_from),
            ('recognition_date', '<=', date_to),
            ('state', '=', 'posted'),
            ('schedule_id.company_id', 'in', [self.env.company.id, False])
        ])
        
        # Group by month
        monthly_data = {}
        for recognition in recognitions:
            month_key = recognition.recognition_date.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'month': month_key,
                    'month_name': recognition.recognition_date.strftime('%B %Y'),
                    'recognized_amount': 0,
                    'recognition_count': 0,
                    'unique_schedules': set(),
                    'unique_customers': set(),
                }
            
            monthly_data[month_key]['recognized_amount'] += recognition.recognized_amount
            monthly_data[month_key]['recognition_count'] += 1
            monthly_data[month_key]['unique_schedules'].add(recognition.schedule_id.id)
            monthly_data[month_key]['unique_customers'].add(recognition.partner_id.id)
        
        # Convert sets to counts and sort
        trend_data = []
        for month_key in sorted(monthly_data.keys()):
            data = monthly_data[month_key]
            trend_data.append({
                'month': data['month'],
                'month_name': data['month_name'],
                'recognized_amount': data['recognized_amount'],
                'recognition_count': data['recognition_count'],
                'schedule_count': len(data['unique_schedules']),
                'customer_count': len(data['unique_customers']),
            })
        
        # Calculate growth rates
        for i in range(1, len(trend_data)):
            prev_amount = trend_data[i-1]['recognized_amount']
            curr_amount = trend_data[i]['recognized_amount']
            
            if prev_amount > 0:
                growth_rate = ((curr_amount - prev_amount) / prev_amount) * 100
            else:
                growth_rate = 0
            
            trend_data[i]['growth_rate'] = growth_rate
        
        return trend_data
    
    def _get_schedule_status_breakdown(self):
        """Get breakdown of schedule statuses"""
        
        schedules = self.env['ams.revenue.schedule'].search([
            ('company_id', 'in', [self.env.company.id, False])
        ])
        
        status_breakdown = {}
        for status in ['draft', 'active', 'paused', 'completed', 'cancelled']:
            filtered_schedules = schedules.filtered(lambda s: s.state == status)
            status_breakdown[status] = {
                'count': len(filtered_schedules),
                'total_value': sum(filtered_schedules.mapped('total_contract_value')),
                'deferred_balance': sum(filtered_schedules.mapped('deferred_revenue_balance')),
            }
        
        # Method breakdown
        method_breakdown = {}
        for method in ['straight_line', 'milestone', 'usage', 'custom']:
            filtered_schedules = schedules.filtered(lambda s: s.recognition_method == method)
            method_breakdown[method] = {
                'count': len(filtered_schedules),
                'total_value': sum(filtered_schedules.mapped('total_contract_value')),
            }
        
        # Frequency breakdown
        frequency_breakdown = {}
        for frequency in ['daily', 'weekly', 'monthly', 'quarterly']:
            filtered_schedules = schedules.filtered(lambda s: s.recognition_frequency == frequency)
            frequency_breakdown[frequency] = {
                'count': len(filtered_schedules),
                'total_value': sum(filtered_schedules.mapped('total_contract_value')),
            }
        
        return {
            'status_breakdown': status_breakdown,
            'method_breakdown': method_breakdown,
            'frequency_breakdown': frequency_breakdown,
            'total_schedules': len(schedules),
        }
    
    def _get_modification_metrics(self, date_from, date_to):
        """Get contract modification metrics"""
        
        modifications = self.env['ams.contract.modification'].search([
            ('modification_date', '>=', date_from),
            ('modification_date', '<=', date_to),
            ('schedule_id.company_id', 'in', [self.env.company.id, False])
        ])
        
        # Type breakdown
        type_breakdown = {}
        for mod_type in ['upgrade', 'downgrade', 'cancellation', 'extension', 'price_change']:
            filtered_mods = modifications.filtered(lambda m: m.modification_type == mod_type)
            type_breakdown[mod_type] = {
                'count': len(filtered_mods),
                'total_value_impact': sum(filtered_mods.mapped('value_change')),
                'total_adjustment': sum(filtered_mods.mapped('adjustment_amount')),
            }
        
        # Status breakdown
        status_breakdown = {}
        for status in ['draft', 'validated', 'processed', 'cancelled']:
            filtered_mods = modifications.filtered(lambda m: m.state == status)
            status_breakdown[status] = {
                'count': len(filtered_mods),
                'total_value_impact': sum(filtered_mods.mapped('value_change')),
            }
        
        return {
            'total_modifications': len(modifications),
            'total_value_impact': sum(modifications.mapped('value_change')),
            'total_adjustments': sum(modifications.mapped('adjustment_amount')),
            'type_breakdown': type_breakdown,
            'status_breakdown': status_breakdown,
        }
    
    def _get_upcoming_recognitions(self, days_ahead=30):
        """Get upcoming revenue recognitions"""
        
        future_date = date.today() + timedelta(days=days_ahead)
        
        upcoming = self.env['ams.revenue.recognition'].search([
            ('state', '=', 'draft'),
            ('recognition_date', '>=', date.today()),
            ('recognition_date', '<=', future_date),
            ('schedule_id.company_id', 'in', [self.env.company.id, False])
        ], order='recognition_date asc')
        
        # Group by week
        weekly_data = {}
        for recognition in upcoming:
            # Get the start of the week (Monday)
            week_start = recognition.recognition_date - timedelta(
                days=recognition.recognition_date.weekday()
            )
            week_key = week_start.strftime('%Y-%m-%d')
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    'week_start': week_start,
                    'week_label': f"Week of {week_start.strftime('%B %d, %Y')}",
                    'recognition_count': 0,
                    'total_amount': 0,
                    'schedules': set(),
                    'customers': set(),
                }
            
            weekly_data[week_key]['recognition_count'] += 1
            weekly_data[week_key]['total_amount'] += recognition.planned_amount
            weekly_data[week_key]['schedules'].add(recognition.schedule_id.id)
            weekly_data[week_key]['customers'].add(recognition.partner_id.id)
        
        # Convert to list and clean up sets
        upcoming_data = []
        for week_key in sorted(weekly_data.keys()):
            data = weekly_data[week_key]
            upcoming_data.append({
                'week_start': data['week_start'],
                'week_label': data['week_label'],
                'recognition_count': data['recognition_count'],
                'total_amount': data['total_amount'],
                'schedule_count': len(data['schedules']),
                'customer_count': len(data['customers']),
            })
        
        return {
            'upcoming_weeks': upcoming_data,
            'total_upcoming_amount': sum(upcoming.mapped('planned_amount')),
            'total_upcoming_count': len(upcoming),
        }
    
    def _get_performance_obligation_summary(self):
        """Get performance obligation summary (ASC 606 compliance)"""
        
        # Get all active schedules
        schedules = self.env['ams.revenue.schedule'].search([
            ('state', 'in', ['active', 'completed']),
            ('company_id', 'in', [self.env.company.id, False])
        ])
        
        # Group by performance obligation ID
        po_data = {}
        for schedule in schedules:
            po_id = schedule.performance_obligation_id or 'Unknown'
            
            if po_id not in po_data:
                po_data[po_id] = {
                    'performance_obligation_id': po_id,
                    'schedule_count': 0,
                    'total_contract_value': 0,
                    'recognized_amount': 0,
                    'deferred_amount': 0,
                    'customers': set(),
                    'products': set(),
                }
            
            po_data[po_id]['schedule_count'] += 1
            po_data[po_id]['total_contract_value'] += schedule.total_contract_value
            po_data[po_id]['recognized_amount'] += schedule.recognized_revenue
            po_data[po_id]['deferred_amount'] += schedule.deferred_revenue_balance
            po_data[po_id]['customers'].add(schedule.partner_id.id)
            po_data[po_id]['products'].add(schedule.product_id.product_tmpl_id.id)
        
        # Convert to list and clean up sets
        performance_obligations = []
        for po_id, data in po_data.items():
            performance_obligations.append({
                'performance_obligation_id': data['performance_obligation_id'],
                'schedule_count': data['schedule_count'],
                'total_contract_value': data['total_contract_value'],
                'recognized_amount': data['recognized_amount'],
                'deferred_amount': data['deferred_amount'],
                'customer_count': len(data['customers']),
                'product_count': len(data['products']),
                'completion_rate': (
                    (data['recognized_amount'] / data['total_contract_value'] * 100)
                    if data['total_contract_value'] > 0 else 0
                ),
            })
        
        # Sort by total contract value descending
        performance_obligations.sort(key=lambda x: x['total_contract_value'], reverse=True)
        
        return {
            'performance_obligations': performance_obligations,
            'total_pos': len(performance_obligations),
            'distinct_customers': len(set().union(*[
                data['customers'] for data in po_data.values()
            ])) if po_data else 0,
            'distinct_products': len(set().union(*[
                data['products'] for data in po_data.values()  
            ])) if po_data else 0,
        }
    
    # Additional utility methods
    @api.model
    def get_mrr_metrics(self):
        """Get Monthly Recurring Revenue metrics"""
        
        # Get all active schedules with monthly recognition
        monthly_schedules = self.env['ams.revenue.schedule'].search([
            ('state', '=', 'active'),
            ('recognition_frequency', '=', 'monthly'),
            ('company_id', 'in', [self.env.company.id, False])
        ])
        
        current_mrr = sum(monthly_schedules.mapped('monthly_recognition_amount'))
        
        # Calculate MRR for previous month for growth calculation
        last_month = date.today().replace(day=1) - timedelta(days=1)
        last_month_start = last_month.replace(day=1)
        
        # Get schedules that were active last month
        last_month_schedules = self.env['ams.revenue.schedule'].search([
            ('start_date', '<=', last_month),
            '|',
            ('end_date', '>=', last_month_start),
            ('state', '=', 'active'),
            ('company_id', 'in', [self.env.company.id, False])
        ])
        
        last_month_mrr = sum(last_month_schedules.mapped('monthly_recognition_amount'))
        
        # Calculate growth
        mrr_growth = ((current_mrr - last_month_mrr) / last_month_mrr * 100) if last_month_mrr > 0 else 0
        
        return {
            'current_mrr': current_mrr,
            'last_month_mrr': last_month_mrr,
            'mrr_growth': mrr_growth,
            'arr': current_mrr * 12,
            'active_monthly_schedules': len(monthly_schedules),
        }
    
    @api.model
    def export_dashboard_data(self, format='json'):
        """Export dashboard data in various formats"""
        
        dashboard_data = self.get_dashboard_data()
        
        if format == 'json':
            return json.dumps(dashboard_data, default=str, indent=2)
        elif format == 'csv':
            # This would require more complex CSV formatting
            # For now, return JSON
            return json.dumps(dashboard_data, default=str, indent=2)
        else:
            return dashboard_data