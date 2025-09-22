from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class CommunicationAnalytics(models.Model):
    _name = 'communication.analytics'
    _description = 'Communication Analytics'
    _auto = False
    _rec_name = 'campaign_name'

    # Dimensions
    campaign_id = fields.Many2one('membership.communication.campaign', string='Campaign')
    campaign_name = fields.Char(string='Campaign')
    campaign_type = fields.Selection([
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification')
    ], string='Type')
    send_date = fields.Date(string='Send Date')
    partner_id = fields.Many2one('res.partner', string='Recipient')
    membership_level_id = fields.Many2one('membership.level', string='Membership Level')
    chapter_id = fields.Many2one('membership.chapter', string='Chapter')
    
    # Metrics
    sent_count = fields.Integer(string='Sent')
    delivered_count = fields.Integer(string='Delivered')
    opened_count = fields.Integer(string='Opened')
    clicked_count = fields.Integer(string='Clicked')
    bounced_count = fields.Integer(string='Bounced')
    unsubscribed_count = fields.Integer(string='Unsubscribed')
    
    # Calculated Rates
    delivery_rate = fields.Float(string='Delivery Rate %')
    open_rate = fields.Float(string='Open Rate %')
    click_rate = fields.Float(string='Click Rate %')
    bounce_rate = fields.Float(string='Bounce Rate %')
    unsubscribe_rate = fields.Float(string='Unsubscribe Rate %')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY mcc.id, rp.id) AS id,
                    mcc.id AS campaign_id,
                    mcc.name AS campaign_name,
                    mcc.communication_type AS campaign_type,
                    mcc.send_date::date AS send_date,
                    rp.id AS partner_id,
                    mm.level_id AS membership_level_id,
                    mm.chapter_id AS chapter_id,
                    CASE WHEN cl.id IS NOT NULL THEN 1 ELSE 0 END AS sent_count,
                    CASE WHEN cl.status IN ('delivered', 'opened', 'clicked') THEN 1 ELSE 0 END AS delivered_count,
                    CASE WHEN cl.status IN ('opened', 'clicked') THEN 1 ELSE 0 END AS opened_count,
                    CASE WHEN cl.status = 'clicked' THEN 1 ELSE 0 END AS clicked_count,
                    CASE WHEN cl.status = 'bounced' THEN 1 ELSE 0 END AS bounced_count,
                    CASE WHEN cl.status = 'unsubscribed' THEN 1 ELSE 0 END AS unsubscribed_count,
                    CASE 
                        WHEN cl.id IS NOT NULL AND cl.status IN ('delivered', 'opened', 'clicked') THEN 100.0
                        WHEN cl.id IS NOT NULL THEN 0.0
                        ELSE NULL 
                    END AS delivery_rate,
                    CASE 
                        WHEN cl.id IS NOT NULL AND cl.status IN ('opened', 'clicked') THEN 100.0
                        WHEN cl.id IS NOT NULL THEN 0.0
                        ELSE NULL 
                    END AS open_rate,
                    CASE 
                        WHEN cl.id IS NOT NULL AND cl.status = 'clicked' THEN 100.0
                        WHEN cl.id IS NOT NULL THEN 0.0
                        ELSE NULL 
                    END AS click_rate,
                    CASE 
                        WHEN cl.id IS NOT NULL AND cl.status = 'bounced' THEN 100.0
                        WHEN cl.id IS NOT NULL THEN 0.0
                        ELSE NULL 
                    END AS bounce_rate,
                    CASE 
                        WHEN cl.id IS NOT NULL AND cl.status = 'unsubscribed' THEN 100.0
                        WHEN cl.id IS NOT NULL THEN 0.0
                        ELSE NULL 
                    END AS unsubscribe_rate
                FROM membership_communication_campaign mcc
                LEFT JOIN membership_communication_log cl ON cl.campaign_id = mcc.id
                LEFT JOIN res_partner rp ON rp.id = cl.partner_id
                LEFT JOIN membership_membership mm ON mm.partner_id = rp.id AND mm.state = 'active'
                WHERE cl.id IS NOT NULL
            )
        """ % self._table)


class CommunicationPerformance(models.Model):
    _name = 'communication.performance'
    _description = 'Communication Performance Dashboard'
    _auto = False

    # Time Dimensions
    period_type = fields.Selection([
        ('day', 'Daily'),
        ('week', 'Weekly'),
        ('month', 'Monthly'),
        ('quarter', 'Quarterly')
    ], string='Period')
    period_date = fields.Date(string='Period Date')
    
    # Campaign Dimensions
    campaign_type = fields.Selection([
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification')
    ], string='Communication Type')
    
    # Performance Metrics
    campaigns_sent = fields.Integer(string='Campaigns Sent')
    total_messages = fields.Integer(string='Total Messages')
    total_delivered = fields.Integer(string='Total Delivered')
    total_opened = fields.Integer(string='Total Opened')
    total_clicked = fields.Integer(string='Total Clicked')
    total_bounced = fields.Integer(string='Total Bounced')
    
    # Aggregated Rates
    avg_delivery_rate = fields.Float(string='Avg Delivery Rate %')
    avg_open_rate = fields.Float(string='Avg Open Rate %')
    avg_click_rate = fields.Float(string='Avg Click Rate %')
    avg_bounce_rate = fields.Float(string='Avg Bounce Rate %')
    
    # Engagement Score
    engagement_score = fields.Float(string='Engagement Score')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY period_date, campaign_type) AS id,
                    'month' AS period_type,
                    DATE_TRUNC('month', mcc.send_date)::date AS period_date,
                    mcc.communication_type AS campaign_type,
                    COUNT(DISTINCT mcc.id) AS campaigns_sent,
                    COUNT(cl.id) AS total_messages,
                    SUM(CASE WHEN cl.status IN ('delivered', 'opened', 'clicked') THEN 1 ELSE 0 END) AS total_delivered,
                    SUM(CASE WHEN cl.status IN ('opened', 'clicked') THEN 1 ELSE 0 END) AS total_opened,
                    SUM(CASE WHEN cl.status = 'clicked' THEN 1 ELSE 0 END) AS total_clicked,
                    SUM(CASE WHEN cl.status = 'bounced' THEN 1 ELSE 0 END) AS total_bounced,
                    AVG(CASE WHEN cl.status IN ('delivered', 'opened', 'clicked') THEN 100.0 ELSE 0.0 END) AS avg_delivery_rate,
                    AVG(CASE WHEN cl.status IN ('opened', 'clicked') THEN 100.0 ELSE 0.0 END) AS avg_open_rate,
                    AVG(CASE WHEN cl.status = 'clicked' THEN 100.0 ELSE 0.0 END) AS avg_click_rate,
                    AVG(CASE WHEN cl.status = 'bounced' THEN 100.0 ELSE 0.0 END) AS avg_bounce_rate,
                    (AVG(CASE WHEN cl.status IN ('opened', 'clicked') THEN 100.0 ELSE 0.0 END) * 0.6 +
                     AVG(CASE WHEN cl.status = 'clicked' THEN 100.0 ELSE 0.0 END) * 0.4) AS engagement_score
                FROM membership_communication_campaign mcc
                LEFT JOIN membership_communication_log cl ON cl.campaign_id = mcc.id
                WHERE mcc.send_date IS NOT NULL AND cl.id IS NOT NULL
                GROUP BY DATE_TRUNC('month', mcc.send_date), mcc.communication_type
            )
        """ % self._table)


class CommunicationSegmentPerformance(models.Model):
    _name = 'communication.segment.performance'
    _description = 'Communication Performance by Segment'
    _auto = False

    # Segment Dimensions
    membership_level_id = fields.Many2one('membership.level', string='Membership Level')
    chapter_id = fields.Many2one('membership.chapter', string='Chapter')
    is_member = fields.Boolean(string='Is Member')
    member_age_group = fields.Selection([
        ('18-25', '18-25'),
        ('26-35', '26-35'),
        ('36-45', '36-45'),
        ('46-55', '46-55'),
        ('56-65', '56-65'),
        ('65+', '65+')
    ], string='Age Group')
    
    # Performance Metrics
    total_messages = fields.Integer(string='Messages Sent')
    avg_open_rate = fields.Float(string='Avg Open Rate %')
    avg_click_rate = fields.Float(string='Avg Click Rate %')
    engagement_score = fields.Float(string='Engagement Score')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY mm.level_id, mm.chapter_id) AS id,
                    mm.level_id AS membership_level_id,
                    mm.chapter_id,
                    rp.is_member,
                    CASE 
                        WHEN EXTRACT(YEAR FROM AGE(rp.birth_date)) BETWEEN 18 AND 25 THEN '18-25'
                        WHEN EXTRACT(YEAR FROM AGE(rp.birth_date)) BETWEEN 26 AND 35 THEN '26-35'
                        WHEN EXTRACT(YEAR FROM AGE(rp.birth_date)) BETWEEN 36 AND 45 THEN '36-45'
                        WHEN EXTRACT(YEAR FROM AGE(rp.birth_date)) BETWEEN 46 AND 55 THEN '46-55'
                        WHEN EXTRACT(YEAR FROM AGE(rp.birth_date)) BETWEEN 56 AND 65 THEN '56-65'
                        WHEN EXTRACT(YEAR FROM AGE(rp.birth_date)) > 65 THEN '65+'
                        ELSE NULL
                    END AS member_age_group,
                    COUNT(cl.id) AS total_messages,
                    AVG(CASE WHEN cl.status IN ('opened', 'clicked') THEN 100.0 ELSE 0.0 END) AS avg_open_rate,
                    AVG(CASE WHEN cl.status = 'clicked' THEN 100.0 ELSE 0.0 END) AS avg_click_rate,
                    (AVG(CASE WHEN cl.status IN ('opened', 'clicked') THEN 100.0 ELSE 0.0 END) * 0.6 +
                     AVG(CASE WHEN cl.status = 'clicked' THEN 100.0 ELSE 0.0 END) * 0.4) AS engagement_score
                FROM membership_communication_log cl
                LEFT JOIN res_partner rp ON rp.id = cl.partner_id
                LEFT JOIN membership_membership mm ON mm.partner_id = rp.id AND mm.state = 'active'
                WHERE cl.send_date >= (CURRENT_DATE - INTERVAL '12 months')
                GROUP BY mm.level_id, mm.chapter_id, rp.is_member, 
                         CASE 
                            WHEN EXTRACT(YEAR FROM AGE(rp.birth_date)) BETWEEN 18 AND 25 THEN '18-25'
                            WHEN EXTRACT(YEAR FROM AGE(rp.birth_date)) BETWEEN 26 AND 35 THEN '26-35'
                            WHEN EXTRACT(YEAR FROM AGE(rp.birth_date)) BETWEEN 36 AND 45 THEN '36-45'
                            WHEN EXTRACT(YEAR FROM AGE(rp.birth_date)) BETWEEN 46 AND 55 THEN '46-55'
                            WHEN EXTRACT(YEAR FROM AGE(rp.birth_date)) BETWEEN 56 AND 65 THEN '56-65'
                            WHEN EXTRACT(YEAR FROM AGE(rp.birth_date)) > 65 THEN '65+'
                            ELSE NULL
                         END
                HAVING COUNT(cl.id) > 0
            )
        """ % self._table)


class CommunicationReport(models.TransientModel):
    _name = 'communication.report.wizard'
    _description = 'Communication Report Wizard'

    # Report Configuration
    report_type = fields.Selection([
        ('campaign_performance', 'Campaign Performance'),
        ('channel_comparison', 'Channel Comparison'),
        ('segment_analysis', 'Segment Analysis'),
        ('engagement_trends', 'Engagement Trends'),
        ('roi_analysis', 'ROI Analysis')
    ], string='Report Type', required=True, default='campaign_performance')
    
    # Date Range
    date_from = fields.Date(
        string='From Date',
        required=True,
        default=lambda self: fields.Date.today() - timedelta(days=30)
    )
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=fields.Date.today
    )
    
    # Filters
    campaign_ids = fields.Many2many(
        'membership.communication.campaign',
        string='Campaigns'
    )
    campaign_types = fields.Selection([
        ('all', 'All Types'),
        ('email', 'Email Only'),
        ('sms', 'SMS Only'),
        ('push', 'Push Notifications Only')
    ], string='Communication Types', default='all')
    
    membership_level_ids = fields.Many2many(
        'membership.level',
        string='Membership Levels'
    )
    chapter_ids = fields.Many2many(
        'membership.chapter',
        string='Chapters'
    )
    
    # Output Options
    include_charts = fields.Boolean(
        string='Include Charts',
        default=True
    )
    export_format = fields.Selection([
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV')
    ], string='Export Format', default='pdf')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise ValidationError(_("From date cannot be after to date."))

    def action_generate_report(self):
        """Generate communication report"""
        self.ensure_one()
        
        # Get report data based on type
        if self.report_type == 'campaign_performance':
            return self._generate_campaign_performance_report()
        elif self.report_type == 'channel_comparison':
            return self._generate_channel_comparison_report()
        elif self.report_type == 'segment_analysis':
            return self._generate_segment_analysis_report()
        elif self.report_type == 'engagement_trends':
            return self._generate_engagement_trends_report()
        elif self.report_type == 'roi_analysis':
            return self._generate_roi_analysis_report()

    def _generate_campaign_performance_report(self):
        """Generate campaign performance report"""
        domain = [
            ('send_date', '>=', self.date_from),
            ('send_date', '<=', self.date_to)
        ]
        
        if self.campaign_ids:
            domain.append(('campaign_id', 'in', self.campaign_ids.ids))
        
        if self.campaign_types != 'all':
            domain.append(('campaign_type', '=', self.campaign_types))
        
        analytics_data = self.env['communication.analytics'].read_group(
            domain,
            ['campaign_name', 'sent_count', 'delivered_count', 'opened_count', 'clicked_count'],
            ['campaign_name']
        )
        
        # Create report context
        context = {
            'report_type': 'Campaign Performance Report',
            'date_range': f"{self.date_from} to {self.date_to}",
            'data': analytics_data,
            'charts': self.include_charts
        }
        
        return self._render_report(context)

    def _generate_channel_comparison_report(self):
        """Generate channel comparison report"""
        domain = [
            ('send_date', '>=', self.date_from),
            ('send_date', '<=', self.date_to)
        ]
        
        channel_data = self.env['communication.analytics'].read_group(
            domain,
            ['campaign_type', 'sent_count', 'delivered_count', 'opened_count', 'clicked_count', 'delivery_rate', 'open_rate', 'click_rate'],
            ['campaign_type']
        )
        
        context = {
            'report_type': 'Channel Comparison Report',
            'date_range': f"{self.date_from} to {self.date_to}",
            'data': channel_data,
            'charts': self.include_charts
        }
        
        return self._render_report(context)

    def _generate_segment_analysis_report(self):
        """Generate segment analysis report"""
        domain = []
        
        if self.membership_level_ids:
            domain.append(('membership_level_id', 'in', self.membership_level_ids.ids))
        
        if self.chapter_ids:
            domain.append(('chapter_id', 'in', self.chapter_ids.ids))
        
        segment_data = self.env['communication.segment.performance'].search_read(domain)
        
        context = {
            'report_type': 'Segment Analysis Report',
            'data': segment_data,
            'charts': self.include_charts
        }
        
        return self._render_report(context)

    def _generate_engagement_trends_report(self):
        """Generate engagement trends report"""
        domain = [
            ('period_date', '>=', self.date_from),
            ('period_date', '<=', self.date_to)
        ]
        
        if self.campaign_types != 'all':
            domain.append(('campaign_type', '=', self.campaign_types))
        
        trends_data = self.env['communication.performance'].search_read(
            domain,
            ['period_date', 'campaign_type', 'avg_open_rate', 'avg_click_rate', 'engagement_score'],
            order='period_date'
        )
        
        context = {
            'report_type': 'Engagement Trends Report',
            'date_range': f"{self.date_from} to {self.date_to}",
            'data': trends_data,
            'charts': self.include_charts
        }
        
        return self._render_report(context)

    def _generate_roi_analysis_report(self):
        """Generate ROI analysis report"""
        # This would calculate ROI based on campaign costs and results
        # For now, provide basic engagement metrics
        
        domain = [
            ('send_date', '>=', self.date_from),
            ('send_date', '<=', self.date_to)
        ]
        
        roi_data = self.env['communication.analytics'].read_group(
            domain,
            ['campaign_name', 'sent_count', 'opened_count', 'clicked_count', 'open_rate', 'click_rate'],
            ['campaign_name']
        )
        
        context = {
            'report_type': 'ROI Analysis Report',
            'date_range': f"{self.date_from} to {self.date_to}",
            'data': roi_data,
            'charts': self.include_charts
        }
        
        return self._render_report(context)

    def _render_report(self, context):
        """Render report based on export format"""
        if self.export_format == 'pdf':
            return self._generate_pdf_report(context)
        elif self.export_format == 'excel':
            return self._generate_excel_report(context)
        elif self.export_format == 'csv':
            return self._generate_csv_report(context)

    def _generate_pdf_report(self, context):
        """Generate PDF report"""
        return {
            'type': 'ir.actions.report',
            'report_name': 'membership_comms.communication_report_pdf',
            'report_type': 'qweb-pdf',
            'context': context,
        }

    def _generate_excel_report(self, context):
        """Generate Excel report"""
        # Would implement Excel generation using xlsxwriter or similar
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Excel report generation not implemented yet'),
                'type': 'info',
            }
        }

    def _generate_csv_report(self, context):
        """Generate CSV report"""
        # Would implement CSV generation
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('CSV report generation not implemented yet'),
                'type': 'info',
            }
        }


class CommunicationDashboard(models.Model):
    _name = 'communication.dashboard'
    _description = 'Communication Dashboard'

    @api.model
    def get_dashboard_data(self, period='month'):
        """Get dashboard data for specified period"""
        
        # Calculate date range
        today = fields.Date.today()
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'quarter':
            start_date = today - timedelta(days=90)
        else:
            start_date = today - timedelta(days=30)

        # Get campaign statistics
        campaigns = self.env['membership.communication.campaign'].search([
            ('send_date', '>=', start_date),
            ('send_date', '<=', today)
        ])
        
        # Get communication logs
        logs = self.env['membership.communication.log'].search([
            ('send_date', '>=', start_date),
            ('send_date', '<=', today)
        ])
        
        # Calculate metrics
        total_campaigns = len(campaigns)
        total_messages = len(logs)
        delivered_messages = len(logs.filtered(lambda l: l.status in ['delivered', 'opened', 'clicked']))
        opened_messages = len(logs.filtered(lambda l: l.status in ['opened', 'clicked']))
        clicked_messages = len(logs.filtered(lambda l: l.status == 'clicked'))
        
        delivery_rate = (delivered_messages / total_messages * 100) if total_messages > 0 else 0
        open_rate = (opened_messages / total_messages * 100) if total_messages > 0 else 0
        click_rate = (clicked_messages / total_messages * 100) if total_messages > 0 else 0
        
        # Get channel breakdown
        channel_breakdown = {}
        for campaign_type in ['email', 'sms', 'push']:
            type_logs = logs.filtered(lambda l: l.campaign_id.communication_type == campaign_type)
            if type_logs:
                channel_breakdown[campaign_type] = {
                    'count': len(type_logs),
                    'delivered': len(type_logs.filtered(lambda l: l.status in ['delivered', 'opened', 'clicked'])),
                    'opened': len(type_logs.filtered(lambda l: l.status in ['opened', 'clicked'])),
                    'clicked': len(type_logs.filtered(lambda l: l.status == 'clicked'))
                }
        
        # Get recent campaigns
        recent_campaigns = campaigns.sorted('send_date', reverse=True)[:10]
        recent_campaign_data = []
        for campaign in recent_campaigns:
            campaign_logs = logs.filtered(lambda l: l.campaign_id.id == campaign.id)
            recent_campaign_data.append({
                'id': campaign.id,
                'name': campaign.name,
                'type': campaign.communication_type,
                'send_date': campaign.send_date,
                'recipients': len(campaign_logs),
                'delivered': len(campaign_logs.filtered(lambda l: l.status in ['delivered', 'opened', 'clicked'])),
                'opened': len(campaign_logs.filtered(lambda l: l.status in ['opened', 'clicked'])),
                'clicked': len(campaign_logs.filtered(lambda l: l.status == 'clicked'))
            })
        
        # Get engagement trends (daily data for chart)
        engagement_trends = []
        for i in range(7):  # Last 7 days
            date = today - timedelta(days=i)
            day_logs = logs.filtered(lambda l: l.send_date.date() == date)
            
            if day_logs:
                engagement_trends.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'sent': len(day_logs),
                    'opened': len(day_logs.filtered(lambda l: l.status in ['opened', 'clicked'])),
                    'clicked': len(day_logs.filtered(lambda l: l.status == 'clicked'))
                })
        
        engagement_trends.reverse()  # Chronological order
        
        return {
            'summary': {
                'total_campaigns': total_campaigns,
                'total_messages': total_messages,
                'delivery_rate': round(delivery_rate, 1),
                'open_rate': round(open_rate, 1),
                'click_rate': round(click_rate, 1),
                'period': period
            },
            'channel_breakdown': channel_breakdown,
            'recent_campaigns': recent_campaign_data,
            'engagement_trends': engagement_trends
        }

    @api.model
    def get_segment_performance(self):
        """Get performance by member segments"""
        segments = self.env['communication.segment.performance'].search([
            ('total_messages', '>', 0)
        ], order='engagement_score desc')
        
        segment_data = []
        for segment in segments:
            segment_name = "Unknown Segment"
            if segment.membership_level_id:
                segment_name = segment.membership_level_id.name
            elif segment.chapter_id:
                segment_name = f"Chapter: {segment.chapter_id.name}"
            elif segment.member_age_group:
                segment_name = f"Age: {segment.member_age_group}"
            elif segment.is_member:
                segment_name = "Members" if segment.is_member else "Non-Members"
            
            segment_data.append({
                'name': segment_name,
                'messages': segment.total_messages,
                'open_rate': round(segment.avg_open_rate, 1),
                'click_rate': round(segment.avg_click_rate, 1),
                'engagement_score': round(segment.engagement_score, 1)
            })
        
        return segment_data[:10]  # Top 10 segments


# Enhanced Communication Campaign with analytics integration
class MembershipCommunicationCampaign(models.Model):
    _inherit = 'membership.communication.campaign'

    # Analytics Fields
    engagement_score = fields.Float(
        string='Engagement Score',
        compute='_compute_engagement_metrics',
        help="Overall engagement score (0-100)"
    )
    performance_rating = fields.Selection([
        ('poor', 'Poor (0-25)'),
        ('fair', 'Fair (26-50)'),
        ('good', 'Good (51-75)'),
        ('excellent', 'Excellent (76-100)')
    ], string='Performance Rating', compute='_compute_engagement_metrics')

    @api.depends('delivery_rate', 'open_rate', 'click_rate')
    def _compute_engagement_metrics(self):
        for campaign in self:
            # Calculate engagement score based on weighted metrics
            if campaign.delivery_rate > 0:
                engagement_score = (
                    campaign.delivery_rate * 0.2 +
                    campaign.open_rate * 0.5 +
                    campaign.click_rate * 0.3
                )
                campaign.engagement_score = engagement_score
                
                # Determine performance rating
                if engagement_score >= 76:
                    campaign.performance_rating = 'excellent'
                elif engagement_score >= 51:
                    campaign.performance_rating = 'good'
                elif engagement_score >= 26:
                    campaign.performance_rating = 'fair'
                else:
                    campaign.performance_rating = 'poor'
            else:
                campaign.engagement_score = 0
                campaign.performance_rating = 'poor'

    def action_view_analytics(self):
        """View detailed analytics for this campaign"""
        self.ensure_one()
        return {
            'name': f"Analytics - {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'communication.analytics',
            'view_mode': 'pivot,graph,tree',
            'domain': [('campaign_id', '=', self.id)],
            'context': {
                'search_default_group_by_status': 1,
                'search_default_group_by_membership_level': 1
            }
        }

    def get_campaign_insights(self):
        """Get AI-powered insights for campaign performance"""
        self.ensure_one()
        
        insights = []
        
        # Performance insights
        if self.open_rate < 15:
            insights.append({
                'type': 'warning',
                'title': 'Low Open Rate',
                'message': f'Your open rate of {self.open_rate:.1f}% is below industry average. Consider improving your subject line or send time.',
                'action': 'Improve subject lines and test send times'
            })
        elif self.open_rate > 25:
            insights.append({
                'type': 'success',
                'title': 'Great Open Rate',
                'message': f'Your open rate of {self.open_rate:.1f}% is above industry average!',
                'action': 'Continue using similar subject line strategies'
            })
        
        if self.click_rate < 2:
            insights.append({
                'type': 'warning',
                'title': 'Low Click Rate',
                'message': f'Your click rate of {self.click_rate:.1f}% suggests content may not be engaging.',
                'action': 'Review content relevance and call-to-action placement'
            })
        
        # Timing insights
        send_hour = self.send_date.hour if self.send_date else 0
        if send_hour < 9 or send_hour > 17:
            insights.append({
                'type': 'info',
                'title': 'Send Time Analysis',
                'message': 'Campaign sent outside typical business hours. This may affect engagement.',
                'action': 'Test different send times to optimize engagement'
            })
        
        # Segment insights
        analytics = self.env['communication.analytics'].search([('campaign_id', '=', self.id)])
        if analytics:
            member_analytics = analytics.filtered('membership_level_id')
            if member_analytics:
                best_performing = member_analytics.sorted('open_rate', reverse=True)[:1]
                if best_performing:
                    insights.append({
                        'type': 'info',
                        'title': 'Best Performing Segment',
                        'message': f'{best_performing.membership_level_id.name} members had the highest engagement.',
                        'action': 'Consider targeting similar segments in future campaigns'
                    })
        
        return insights