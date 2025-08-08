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
    _auto = False  # This is a reporting model, no database table needed

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
            ('state', 'in', ['active', 'completed'])
        ])
        total_contract_value = sum(active_schedules.mapped('total_contract_value'))
        
        # Revenue recognized in period
        period_recognitions = self.env['ams.revenue.recognition'].search([
            ('recognition_date', '>=', date_from),
            ('recognition_date', '<=', date_to),
            ('state', '=', 'posted')
        ])
        period_recognized = sum(period_recognitions.mapped('recognized_amount'))
        
        # Total deferred revenue
        total_deferred = sum(active_schedules.mapped('deferred_revenue_balance'))
        
        # Total recognized to date
        all_recognitions = self.env['ams.revenue.recognition'].search([
            ('state', '=', 'posted')
        ])
        total_recognized = sum(all_recognitions.mapped('recognized_amount'))
        
        # Active subscriptions with revenue recognition
        active_subscriptions = self.env['ams.subscription'].search([
            ('revenue_recognition_status', '=', 'active')
        ])
        
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
            'active_subscriptions_count': len(active_subscriptions),
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
            ('state', '=', 'posted')
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
        
        schedules = self.env['ams.revenue.schedule'].search([])
        
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
            ('modification_date', '<=', date_to)
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
            ('recognition_date', '<=', future_date)
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
            ('state', 'in', ['active', 'completed'])
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
    
    # Specific Metric Methods
    @api.model
    def get_mrr_metrics(self):
        """Get Monthly Recurring Revenue metrics"""
        
        # Get all active schedules with monthly recognition
        monthly_schedules = self.env['ams.revenue.schedule'].search([
            ('state', '=', 'active'),
            ('recognition_frequency', '=', 'monthly')
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
            ('state', '=', 'active')
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
    def get_deferred_revenue_aging(self):
        """Get deferred revenue aging analysis"""
        
        active_schedules = self.env['ams.revenue.schedule'].search([
            ('state', '=', 'active'),
            ('deferred_revenue_balance', '>', 0)
        ])
        
        aging_buckets = {
            '0-30': {'count': 0, 'amount': 0},
            '31-90': {'count': 0, 'amount': 0}, 
            '91-180': {'count': 0, 'amount': 0},
            '181-365': {'count': 0, 'amount': 0},
            '365+': {'count': 0, 'amount': 0},
        }
        
        today = date.today()
        
        for schedule in active_schedules:
            if not schedule.end_date:
                continue
                
            days_to_completion = (schedule.end_date - today).days
            
            if days_to_completion <= 30:
                bucket = '0-30'
            elif days_to_completion <= 90:
                bucket = '31-90'
            elif days_to_completion <= 180:
                bucket = '91-180'
            elif days_to_completion <= 365:
                bucket = '181-365'
            else:
                bucket = '365+'
            
            aging_buckets[bucket]['count'] += 1
            aging_buckets[bucket]['amount'] += schedule.deferred_revenue_balance
        
        return aging_buckets
    
    @api.model
    def get_customer_revenue_concentration(self, limit=10):
        """Get top customers by revenue concentration"""
        
        # Get all schedules grouped by customer
        schedules = self.env['ams.revenue.schedule'].search([
            ('state', 'in', ['active', 'completed'])
        ])
        
        customer_data = {}
        for schedule in schedules:
            partner_id = schedule.partner_id.id
            
            if partner_id not in customer_data:
                customer_data[partner_id] = {
                    'customer_name': schedule.partner_id.name,
                    'total_contract_value': 0,
                    'recognized_amount': 0,
                    'deferred_amount': 0,
                    'schedule_count': 0,
                }
            
            customer_data[partner_id]['total_contract_value'] += schedule.total_contract_value
            customer_data[partner_id]['recognized_amount'] += schedule.recognized_revenue
            customer_data[partner_id]['deferred_amount'] += schedule.deferred_revenue_balance
            customer_data[partner_id]['schedule_count'] += 1
        
        # Convert to list and sort by total contract value
        customers = list(customer_data.values())
        customers.sort(key=lambda x: x['total_contract_value'], reverse=True)
        
        # Calculate percentages
        total_contract_value = sum(c['total_contract_value'] for c in customers)
        
        for customer in customers:
            customer['percentage'] = (
                (customer['total_contract_value'] / total_contract_value * 100)
                if total_contract_value > 0 else 0
            )
        
        return {
            'top_customers': customers[:limit],
            'total_customers': len(customers),
            'total_contract_value': total_contract_value,
        }
    
    @api.model
    def get_recognition_accuracy_metrics(self):
        """Get metrics on recognition accuracy and adjustments"""
        
        # Get all recognitions with adjustments
        recognitions = self.env['ams.revenue.recognition'].search([
            ('state', '=', 'posted')
        ])
        
        total_recognitions = len(recognitions)
        recognitions_with_adjustments = recognitions.filtered(lambda r: abs(r.adjustment_amount) > 0.01)
        adjustments_count = len(recognitions_with_adjustments)
        
        # Calculate accuracy rate
        accuracy_rate = ((total_recognitions - adjustments_count) / total_recognitions * 100) if total_recognitions > 0 else 100
        
        # Get contract modifications
        modifications = self.env['ams.contract.modification'].search([
            ('state', '=', 'processed')
        ])
        
        return {
            'total_recognitions': total_recognitions,
            'adjustments_count': adjustments_count,
            'accuracy_rate': accuracy_rate,
            'total_adjustment_amount': sum(recognitions_with_adjustments.mapped('adjustment_amount')),
            'contract_modifications_count': len(modifications),
            'total_modification_impact': sum(modifications.mapped('adjustment_amount')),
        }
    
    # Chart Data Methods
    @api.model
    def get_recognition_timeline_chart(self, months=12):
        """Get data for recognition timeline chart"""
        
        start_date = date.today() - relativedelta(months=months)
        
        recognitions = self.env['ams.revenue.recognition'].search([
            ('recognition_date', '>=', start_date),
            ('state', '=', 'posted')
        ])
        
        # Group by month
        chart_data = {}
        current = start_date.replace(day=1)
        
        while current <= date.today():
            month_key = current.strftime('%Y-%m')
            chart_data[month_key] = {
                'month': month_key,
                'month_label': current.strftime('%b %Y'),
                'recognized_amount': 0,
                'planned_amount': 0,
                'count': 0,
            }
            current += relativedelta(months=1)
        
        # Fill with actual data
        for recognition in recognitions:
            month_key = recognition.recognition_date.strftime('%Y-%m')
            if month_key in chart_data:
                chart_data[month_key]['recognized_amount'] += recognition.recognized_amount
                chart_data[month_key]['planned_amount'] += recognition.planned_amount
                chart_data[month_key]['count'] += 1
        
        return list(chart_data.values())
    
    @api.model
    def get_product_revenue_chart(self, limit=10):
        """Get data for product revenue breakdown chart"""
        
        schedules = self.env['ams.revenue.schedule'].search([
            ('state', 'in', ['active', 'completed'])
        ])
        
        product_data = {}
        for schedule in schedules:
            product_name = schedule.product_id.name
            
            if product_name not in product_data:
                product_data[product_name] = {
                    'product_name': product_name,
                    'total_contract_value': 0,
                    'recognized_amount': 0,
                    'schedule_count': 0,
                }
            
            product_data[product_name]['total_contract_value'] += schedule.total_contract_value
            product_data[product_name]['recognized_amount'] += schedule.recognized_revenue
            product_data[product_name]['schedule_count'] += 1
        
        # Convert to list and sort
        products = list(product_data.values())
        products.sort(key=lambda x: x['total_contract_value'], reverse=True)
        
        return products[:limit]
    
    # Export Methods
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