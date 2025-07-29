/* AMS Financial Dashboard Widgets */

odoo.define('ams_accounting.financial_widgets', function (require) {
    "use strict";
    
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var Widget = require('web.Widget');
    
    var QWeb = core.qweb;
    var _t = core._t;
    
    // Financial Dashboard Widget
    var FinancialDashboard = AbstractAction.extend({
        template: 'ams_accounting.FinancialDashboard',
        
        init: function(parent, context) {
            this._super(parent, context);
            this.dashboards_templates = ['ams_accounting.FinancialDashboard'];
        },
        
        willStart: function() {
            var self = this;
            return this._super().then(function() {
                return self.fetch_data();
            });
        },
        
        start: function() {
            var self = this;
            return this._super().then(function() {
                self.render_dashboard();
            });
        },
        
        fetch_data: function() {
            var self = this;
            return rpc.query({
                model: 'ams.financial.transaction',
                method: 'search_read',
                domain: [['state', '=', 'confirmed']],
                fields: ['amount', 'transaction_type', 'revenue_category_id', 'date'],
                limit: 1000
            }).then(function(transactions) {
                self.transaction_data = transactions;
                return self.process_data();
            });
        },
        
        process_data: function() {
            var self = this;
            var current_year = new Date().getFullYear();
            
            // Initialize totals
            self.dashboard_data = {
                total_revenue: 0,
                total_expenses: 0,
                net_income: 0,
                revenue_by_category: {},
                monthly_data: {},
                current_year: current_year
            };
            
            // Process transactions
            self.transaction_data.forEach(function(transaction) {
                var transaction_date = new Date(transaction.date);
                var transaction_year = transaction_date.getFullYear();
                
                // Only process current year data
                if (transaction_year === current_year) {
                    if (transaction.transaction_type === 'income') {
                        self.dashboard_data.total_revenue += transaction.amount;
                        
                        // Group by category
                        var category = transaction.revenue_category_id ? transaction.revenue_category_id[1] : 'Other';
                        if (!self.dashboard_data.revenue_by_category[category]) {
                            self.dashboard_data.revenue_by_category[category] = 0;
                        }
                        self.dashboard_data.revenue_by_category[category] += transaction.amount;
                    } else if (transaction.transaction_type === 'expense') {
                        self.dashboard_data.total_expenses += transaction.amount;
                    }
                }
            });
            
            // Calculate net income
            self.dashboard_data.net_income = self.dashboard_data.total_revenue - self.dashboard_data.total_expenses;
            
            return Promise.resolve();
        },
        
        render_dashboard: function() {
            var self = this;
            var $dashboard = $(QWeb.render('ams_accounting.FinancialDashboard', {
                widget: self,
                data: self.dashboard_data
            }));
            this.$el.append($dashboard);
        },
        
        format_currency: function(amount) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
            }).format(amount);
        }
    });
    
    // Register the dashboard action
    core.action_registry.add('ams_financial_dashboard', FinancialDashboard);
    
    return {
        FinancialDashboard: FinancialDashboard
    };
});

// Dashboard Templates
odoo.define('ams_accounting.dashboard_templates', function (require) {
    "use strict";
    
    var core = require('web.core');
    var QWeb = core.qweb;
    
    QWeb.add_template(`
        <t t-name="ams_accounting.FinancialDashboard">
            <div class="ams_financial_dashboard">
                <div class="ams_dashboard_header">
                    <h1 class="ams_dashboard_title">Financial Dashboard</h1>
                    <p class="ams_dashboard_subtitle">Current Year: <t t-esc="data.current_year"/></p>
                </div>
                
                <div class="row">
                    <div class="col-md-4">
                        <div class="ams_financial_card">
                            <div class="ams_financial_metric">
                                <div class="metric_value" t-esc="widget.format_currency(data.total_revenue)"/>
                                <div class="metric_label">Total Revenue</div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="ams_financial_card">
                            <div class="ams_financial_metric">
                                <div class="metric_value" t-esc="widget.format_currency(data.total_expenses)"/>
                                <div class="metric_label">Total Expenses</div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="ams_financial_card">
                            <div class="ams_financial_metric">
                                <div class="metric_value" t-esc="widget.format_currency(data.net_income)"/>
                                <div class="metric_label">Net Income</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-8">
                        <div class="ams_financial_card">
                            <h3>Revenue by Category</h3>
                            <div class="ams_revenue_breakdown">
                                <t t-foreach="Object.keys(data.revenue_by_category)" t-as="category">
                                    <div class="ams_revenue_item">
                                        <span class="ams_revenue_category" t-esc="category"/>
                                        <span class="ams_revenue_amount" t-esc="widget.format_currency(data.revenue_by_category[category])"/>
                                    </div>
                                </t>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="ams_financial_card">
                            <h3>Quick Actions</h3>
                            <div>
                                <a href="#" class="ams_action_button primary" data-action="ams_accounting.action_ams_financial_transaction">
                                    View Transactions
                                </a>
                                <a href="#" class="ams_action_button" data-action="ams_accounting.action_ams_revenue_category">
                                    Manage Categories
                                </a>
                                <a href="#" class="ams_action_button" data-action="ams_accounting.action_ams_financial_summary">
                                    Financial Reports
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </t>
    `);
    
    return {};
});