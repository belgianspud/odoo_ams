# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class MembershipReport(models.Model):
    _name = 'membership.report'
    _description = 'Membership Analysis Report'
    _auto = False
    _order = 'date desc'

    # ==========================================
    # DIMENSIONS
    # ==========================================
    
    date = fields.Date(string='Date', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Member', readonly=True)
    subscription_id = fields.Many2one('subscription.subscription', string='Subscription', readonly=True)
    product_id = fields.Many2one('product.template', string='Product', readonly=True)
    plan_id = fields.Many2one('subscription.plan', string='Plan', readonly=True)
    
    # Member classification
    membership_category_id = fields.Many2one('membership.category', string='Category', readonly=True)
    category_type = fields.Selection([
        ('individual', 'Individual'),
        ('organizational', 'Organizational'),
        ('student', 'Student'),
        ('honorary', 'Honorary'),
        ('retired', 'Retired'),
        ('emeritus', 'Emeritus'),
        ('affiliate', 'Affiliate'),
        ('associate', 'Associate'),
        ('special', 'Special')
    ], string='Category Type', readonly=True)
    member_tier = fields.Selection([
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('platinum', 'Platinum')
    ], string='Member Tier', readonly=True)
    
    # Subscription status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ], string='Status', readonly=True)
    
    # Dates
    date_start = fields.Date(string='Start Date', readonly=True)
    date_end = fields.Date(string='End Date', readonly=True)
    join_date = fields.Date(string='Join Date', readonly=True)
    
    # Source
    source_type = fields.Selection([
        ('direct', 'Direct Signup'),
        ('renewal', 'Renewal'),
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('transfer', 'Transfer'),
        ('chapter', 'Chapter'),
        ('import', 'Data Import'),
        ('admin', 'Admin Created')
    ], string='Source', readonly=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    
    # ==========================================
    # MEASURES
    # ==========================================
    
    # Counts
    subscription_count = fields.Integer(string='# Subscriptions', readonly=True)
    active_count = fields.Integer(string='# Active', readonly=True)
    new_count = fields.Integer(string='# New', readonly=True)
    renewal_count = fields.Integer(string='# Renewals', readonly=True)
    cancelled_count = fields.Integer(string='# Cancelled', readonly=True)
    
    # Revenue
    price = fields.Float(string='Price', readonly=True, group_operator='avg')
    total_revenue = fields.Float(string='Total Revenue', readonly=True, group_operator='sum')
    recurring_revenue = fields.Float(string='MRR/ARR', readonly=True, group_operator='sum')
    
    # Retention metrics
    retention_rate = fields.Float(string='Retention Rate %', readonly=True, group_operator='avg')
    churn_rate = fields.Float(string='Churn Rate %', readonly=True, group_operator='avg')
    
    # Time metrics
    days_active = fields.Integer(string='Days Active', readonly=True, group_operator='avg')
    days_until_expiry = fields.Integer(string='Days Until Expiry', readonly=True, group_operator='avg')

    # ==========================================
    # SQL VIEW
    # ==========================================

    def init(self):
        """Create or replace the SQL view for membership reporting"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    sub.id AS id,
                    sub.date_start AS date,
                    sub.partner_id,
                    sub.id AS subscription_id,
                    pt.id AS product_id,
                    sub.plan_id,
                    sub.membership_category_id,
                    mc.category_type,
                    mc.member_tier,
                    sub.state,
                    sub.date_start,
                    sub.date_end,
                    sub.join_date,
                    sub.source_type,
                    sub.company_id,
                    
                    -- Counts
                    1 AS subscription_count,
                    CASE WHEN sub.state IN ('active', 'trial') THEN 1 ELSE 0 END AS active_count,
                    CASE WHEN sub.source_type = 'direct' THEN 1 ELSE 0 END AS new_count,
                    CASE WHEN sub.source_type = 'renewal' THEN 1 ELSE 0 END AS renewal_count,
                    CASE WHEN sub.state = 'cancelled' THEN 1 ELSE 0 END AS cancelled_count,
                    
                    -- Revenue
                    sub.price,
                    sub.price AS total_revenue,
                    CASE 
                        WHEN sp.billing_period = 'monthly' THEN sub.price
                        WHEN sp.billing_period = 'quarterly' THEN sub.price / 3
                        WHEN sp.billing_period = 'yearly' THEN sub.price / 12
                        ELSE sub.price
                    END AS recurring_revenue,
                    
                    -- Retention (simplified - actual calculation would be more complex)
                    CASE 
                        WHEN sub.state IN ('active', 'trial') THEN 100.0
                        WHEN sub.state = 'cancelled' THEN 0.0
                        ELSE 50.0
                    END AS retention_rate,
                    
                    CASE 
                        WHEN sub.state = 'cancelled' THEN 100.0
                        ELSE 0.0
                    END AS churn_rate,
                    
                    -- Time metrics
                    CASE 
                        WHEN sub.date_start IS NOT NULL THEN 
                            EXTRACT(DAY FROM (COALESCE(sub.date_end, CURRENT_DATE) - sub.date_start))
                        ELSE 0
                    END AS days_active,
                    
                    CASE 
                        WHEN sub.date_end IS NOT NULL AND sub.state IN ('active', 'trial') THEN 
                            EXTRACT(DAY FROM (sub.date_end - CURRENT_DATE))
                        ELSE 0
                    END AS days_until_expiry
                    
                FROM subscription_subscription sub
                LEFT JOIN subscription_plan sp ON sub.plan_id = sp.id
                LEFT JOIN product_product pp ON sub.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN membership_category mc ON sub.membership_category_id = mc.id
                WHERE pt.is_membership_product = true
            )
        """ % self._table
        
        self.env.cr.execute(query)


class MembershipCategoryReport(models.Model):
    _name = 'membership.category.report'
    _description = 'Membership by Category Report'
    _auto = False
    _order = 'member_count desc'

    # ==========================================
    # DIMENSIONS
    # ==========================================
    
    membership_category_id = fields.Many2one('membership.category', string='Category', readonly=True)
    category_type = fields.Selection([
        ('individual', 'Individual'),
        ('organizational', 'Organizational'),
        ('student', 'Student'),
        ('honorary', 'Honorary'),
        ('retired', 'Retired'),
        ('emeritus', 'Emeritus'),
        ('affiliate', 'Affiliate'),
        ('associate', 'Associate'),
        ('special', 'Special')
    ], string='Category Type', readonly=True)
    member_tier = fields.Selection([
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('platinum', 'Platinum')
    ], string='Member Tier', readonly=True)
    
    # ==========================================
    # MEASURES
    # ==========================================
    
    member_count = fields.Integer(string='Total Members', readonly=True)
    active_count = fields.Integer(string='Active Members', readonly=True)
    trial_count = fields.Integer(string='Trial Members', readonly=True)
    expired_count = fields.Integer(string='Expired Members', readonly=True)
    
    total_revenue = fields.Float(string='Total Revenue', readonly=True)
    avg_price = fields.Float(string='Avg Price', readonly=True)
    
    retention_rate = fields.Float(string='Retention %', readonly=True)

    # ==========================================
    # SQL VIEW
    # ==========================================

    def init(self):
        """Create or replace the SQL view for category analysis"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY mc.id) AS id,
                    mc.id AS membership_category_id,
                    mc.category_type,
                    mc.member_tier,
                    
                    COUNT(sub.id) AS member_count,
                    COUNT(CASE WHEN sub.state = 'active' THEN 1 END) AS active_count,
                    COUNT(CASE WHEN sub.state = 'trial' THEN 1 END) AS trial_count,
                    COUNT(CASE WHEN sub.state = 'expired' THEN 1 END) AS expired_count,
                    
                    SUM(sub.price) AS total_revenue,
                    AVG(sub.price) AS avg_price,
                    
                    CASE 
                        WHEN COUNT(sub.id) > 0 THEN
                            (COUNT(CASE WHEN sub.state IN ('active', 'trial') THEN 1 END)::float / COUNT(sub.id)::float) * 100
                        ELSE 0
                    END AS retention_rate
                    
                FROM membership_category mc
                LEFT JOIN subscription_subscription sub ON sub.membership_category_id = mc.id
                LEFT JOIN product_product pp ON sub.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE pt.is_membership_product = true OR pt.is_membership_product IS NULL
                GROUP BY mc.id, mc.category_type, mc.member_tier
            )
        """ % self._table
        
        self.env.cr.execute(query)


class MembershipRevenueReport(models.Model):
    _name = 'membership.revenue.report'
    _description = 'Membership Revenue Report'
    _auto = False
    _order = 'date desc'

    # ==========================================
    # DIMENSIONS
    # ==========================================
    
    date = fields.Date(string='Date', readonly=True)
    year = fields.Char(string='Year', readonly=True)
    month = fields.Char(string='Month', readonly=True)
    quarter = fields.Char(string='Quarter', readonly=True)
    
    product_id = fields.Many2one('product.template', string='Product', readonly=True)
    membership_category_id = fields.Many2one('membership.category', string='Category', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    
    # ==========================================
    # MEASURES
    # ==========================================
    
    subscription_count = fields.Integer(string='# Subscriptions', readonly=True)
    new_subscriptions = fields.Integer(string='# New', readonly=True)
    renewals = fields.Integer(string='# Renewals', readonly=True)
    
    total_revenue = fields.Float(string='Total Revenue', readonly=True)
    mrr = fields.Float(string='MRR', readonly=True)
    arr = fields.Float(string='ARR', readonly=True)
    
    avg_subscription_value = fields.Float(string='Avg Subscription Value', readonly=True)

    # ==========================================
    # SQL VIEW
    # ==========================================

    def init(self):
        """Create or replace the SQL view for revenue analysis"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY sub.date_start) AS id,
                    sub.date_start AS date,
                    TO_CHAR(sub.date_start, 'YYYY') AS year,
                    TO_CHAR(sub.date_start, 'YYYY-MM') AS month,
                    TO_CHAR(sub.date_start, 'YYYY-Q') AS quarter,
                    
                    pt.id AS product_id,
                    sub.membership_category_id,
                    sub.company_id,
                    
                    COUNT(sub.id) AS subscription_count,
                    COUNT(CASE WHEN sub.source_type = 'direct' THEN 1 END) AS new_subscriptions,
                    COUNT(CASE WHEN sub.source_type = 'renewal' THEN 1 END) AS renewals,
                    
                    SUM(sub.price) AS total_revenue,
                    
                    SUM(
                        CASE 
                            WHEN sp.billing_period = 'monthly' THEN sub.price
                            WHEN sp.billing_period = 'quarterly' THEN sub.price / 3
                            WHEN sp.billing_period = 'yearly' THEN sub.price / 12
                            ELSE sub.price
                        END
                    ) AS mrr,
                    
                    SUM(
                        CASE 
                            WHEN sp.billing_period = 'monthly' THEN sub.price * 12
                            WHEN sp.billing_period = 'quarterly' THEN sub.price * 4
                            WHEN sp.billing_period = 'yearly' THEN sub.price
                            ELSE sub.price * 12
                        END
                    ) AS arr,
                    
                    AVG(sub.price) AS avg_subscription_value
                    
                FROM subscription_subscription sub
                LEFT JOIN subscription_plan sp ON sub.plan_id = sp.id
                LEFT JOIN product_product pp ON sub.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE pt.is_membership_product = true
                    AND sub.date_start IS NOT NULL
                GROUP BY 
                    sub.date_start,
                    TO_CHAR(sub.date_start, 'YYYY'),
                    TO_CHAR(sub.date_start, 'YYYY-MM'),
                    TO_CHAR(sub.date_start, 'YYYY-Q'),
                    pt.id,
                    sub.membership_category_id,
                    sub.company_id
            )
        """ % self._table
        
        self.env.cr.execute(query)


class MembershipChurnReport(models.Model):
    _name = 'membership.churn.report'
    _description = 'Membership Churn Analysis'
    _auto = False
    _order = 'date desc'

    # ==========================================
    # DIMENSIONS
    # ==========================================
    
    date = fields.Date(string='Date', readonly=True)
    year = fields.Char(string='Year', readonly=True)
    month = fields.Char(string='Month', readonly=True)
    
    membership_category_id = fields.Many2one('membership.category', string='Category', readonly=True)
    product_id = fields.Many2one('product.template', string='Product', readonly=True)
    
    # ==========================================
    # MEASURES
    # ==========================================
    
    total_members = fields.Integer(string='Total Members', readonly=True)
    active_members = fields.Integer(string='Active Members', readonly=True)
    churned_members = fields.Integer(string='Churned Members', readonly=True)
    new_members = fields.Integer(string='New Members', readonly=True)
    
    churn_count = fields.Integer(string='Churn Count', readonly=True)
    churn_rate = fields.Float(string='Churn Rate %', readonly=True)
    retention_rate = fields.Float(string='Retention Rate %', readonly=True)
    
    net_growth = fields.Integer(string='Net Growth', readonly=True)
    growth_rate = fields.Float(string='Growth Rate %', readonly=True)

    # ==========================================
    # SQL VIEW
    # ==========================================

    def init(self):
        """Create or replace the SQL view for churn analysis"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY date_month) AS id,
                    date_month AS date,
                    TO_CHAR(date_month, 'YYYY') AS year,
                    TO_CHAR(date_month, 'YYYY-MM') AS month,
                    membership_category_id,
                    product_id,
                    
                    total_members,
                    active_members,
                    churned_members,
                    new_members,
                    
                    churned_members AS churn_count,
                    
                    CASE 
                        WHEN total_members > 0 THEN (churned_members::float / total_members::float) * 100
                        ELSE 0
                    END AS churn_rate,
                    
                    CASE 
                        WHEN total_members > 0 THEN ((total_members - churned_members)::float / total_members::float) * 100
                        ELSE 0
                    END AS retention_rate,
                    
                    (new_members - churned_members) AS net_growth,
                    
                    CASE 
                        WHEN (total_members - new_members) > 0 THEN 
                            ((new_members - churned_members)::float / (total_members - new_members)::float) * 100
                        ELSE 0
                    END AS growth_rate
                    
                FROM (
                    SELECT
                        DATE_TRUNC('month', COALESCE(sub.date_end, sub.date_start))::date AS date_month,
                        sub.membership_category_id,
                        pt.id AS product_id,
                        
                        COUNT(sub.id) AS total_members,
                        COUNT(CASE WHEN sub.state IN ('active', 'trial') THEN 1 END) AS active_members,
                        COUNT(CASE WHEN sub.state = 'cancelled' THEN 1 END) AS churned_members,
                        COUNT(CASE WHEN sub.source_type = 'direct' AND sub.state IN ('active', 'trial') THEN 1 END) AS new_members
                        
                    FROM subscription_subscription sub
                    LEFT JOIN product_product pp ON sub.product_id = pp.id
                    LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    WHERE pt.is_membership_product = true
                    GROUP BY 
                        DATE_TRUNC('month', COALESCE(sub.date_end, sub.date_start))::date,
                        sub.membership_category_id,
                        pt.id
                ) AS subquery
            )
        """ % self._table
        
        self.env.cr.execute(query)