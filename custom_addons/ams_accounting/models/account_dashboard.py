import calendar
import datetime
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import models, api, fields
from odoo.http import request


class AMSAccountingDashboard(models.Model):
    """
    Enhanced accounting dashboard with AMS integration features
    """
    _inherit = 'account.move'

    # AMS Integration fields
    ams_subscription_id = fields.Many2one('ams.subscription', 'Related AMS Subscription', readonly=True)
    ams_member_id = fields.Many2one('res.partner', 'AMS Member', readonly=True)
    ams_chapter_id = fields.Many2one('ams.chapter', 'AMS Chapter', readonly=True)
    is_ams_subscription_invoice = fields.Boolean('Is AMS Subscription Invoice', default=False)
    is_ams_renewal_invoice = fields.Boolean('Is AMS Renewal Invoice', default=False)
    is_ams_donation = fields.Boolean('Is AMS Donation', default=False)

    @api.model
    def get_income_this_year(self, *post):
        """Get income data for this year with AMS enhancements"""
        company_id = self.get_current_company_value()

        month_list = []
        for i in range(11, -1, -1):
            l_month = datetime.now() - relativedelta(months=i)
            text = format(l_month, '%B')
            month_list.append(text)

        states_arg = ""
        if post != ('posted',):
            states_arg = """ move_id.state in ('posted', 'draft')"""
        else:
            states_arg = """ move_id.state = 'posted'"""

        # Updated query for Odoo 18 account structure
        self._cr.execute(('''
            SELECT 
                SUM(debit) - SUM(credit) as income,
                TO_CHAR(account_move_line.date, 'Month') as month,
                account_account.account_type
            FROM account_move_line 
            LEFT JOIN account_account ON account_move_line.account_id = account_account.id 
            LEFT JOIN account_move ON account_move_line.move_id = account_move.id
            WHERE account_account.account_type LIKE 'income%%'
                AND TO_CHAR(DATE(NOW()), 'YY') = TO_CHAR(account_move_line.date, 'YY')
                AND account_move_line.company_id IN %s
                AND %s
            GROUP BY account_account.account_type, month
        ''') % (tuple(company_id), states_arg))
        
        income_records = self._cr.dictfetchall()

        # Get expenses with similar structure
        self._cr.execute(('''
            SELECT 
                SUM(debit) - SUM(credit) as expense,
                TO_CHAR(account_move_line.date, 'Month') as month,
                account_account.account_type
            FROM account_move_line 
            LEFT JOIN account_account ON account_move_line.account_id = account_account.id 
            LEFT JOIN account_move ON account_move_line.move_id = account_move.id
            WHERE account_account.account_type LIKE 'expense%%'
                AND TO_CHAR(DATE(NOW()), 'YY') = TO_CHAR(account_move_line.date, 'YY')
                AND account_move_line.company_id IN %s
                AND %s
            GROUP BY account_account.account_type, month
        ''') % (tuple(company_id), states_arg))
        
        expense_records = self._cr.dictfetchall()

        # Process and combine data
        records = []
        for month in month_list:
            month_income = list(filter(lambda m: m['month'].strip() == month, income_records))
            month_expense = list(filter(lambda m: m['month'].strip() == month, expense_records))
            
            income_amount = sum(rec['income'] for rec in month_income) if month_income else 0.0
            expense_amount = sum(rec['expense'] for rec in month_expense) if month_expense else 0.0
            
            # Handle negative values properly
            income_amount = abs(income_amount) if income_amount < 0 else income_amount
            expense_amount = abs(expense_amount) if expense_amount < 0 else expense_amount
            
            records.append({
                'month': month,
                'income': income_amount,
                'expense': expense_amount,
                'profit': income_amount - expense_amount,
            })

        income = [rec['income'] for rec in records]
        expense = [rec['expense'] for rec in records]
        month = [rec['month'] for rec in records]
        profit = [rec['profit'] for rec in records]
        
        return {
            'income': income,
            'expense': expense,
            'month': month,
            'profit': profit,
        }

    @api.model
    def get_total_invoice_current_year(self, *post):
        """Get total invoice data for current year"""
        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""

        # Customer invoices (Odoo 18 compatible)
        self._cr.execute(('''
            SELECT SUM(amount_total_signed) as customer_invoice 
            FROM account_move 
            WHERE move_type = 'out_invoice'
                AND %s
                AND EXTRACT(YEAR FROM account_move.date) = EXTRACT(YEAR FROM DATE(NOW()))
                AND account_move.company_id IN %s
        ''') % (states_arg, tuple(company_id)))
        customer_invoices = self._cr.dictfetchall()

        # Supplier invoices
        self._cr.execute(('''
            SELECT SUM(ABS(amount_total_signed)) as supplier_invoice 
            FROM account_move 
            WHERE move_type = 'in_invoice'
                AND %s
                AND EXTRACT(YEAR FROM account_move.date) = EXTRACT(YEAR FROM DATE(NOW()))
                AND account_move.company_id IN %s
        ''') % (states_arg, tuple(company_id)))
        supplier_invoices = self._cr.dictfetchall()

        # Paid customer invoices
        self._cr.execute(('''
            SELECT SUM(amount_total_signed) - SUM(amount_residual_signed) as customer_invoice_paid 
            FROM account_move 
            WHERE move_type = 'out_invoice'
                AND %s
                AND payment_state = 'paid'
                AND EXTRACT(YEAR FROM account_move.date) = EXTRACT(YEAR FROM DATE(NOW()))
                AND account_move.company_id IN %s
        ''') % (states_arg, tuple(company_id)))
        paid_customer_invoices = self._cr.dictfetchall()

        # Paid supplier invoices
        self._cr.execute(('''
            SELECT SUM(ABS(amount_total_signed)) - SUM(ABS(amount_residual_signed)) as supplier_invoice_paid 
            FROM account_move 
            WHERE move_type = 'in_invoice'
                AND %s
                AND payment_state = 'paid'
                AND EXTRACT(YEAR FROM account_move.date) = EXTRACT(YEAR FROM DATE(NOW()))
                AND account_move.company_id IN %s
        ''') % (states_arg, tuple(company_id)))
        paid_supplier_invoices = self._cr.dictfetchall()

        customer_invoice_current_year = [item['customer_invoice'] or 0 for item in customer_invoices]
        supplier_invoice_current_year = [item['supplier_invoice'] or 0 for item in supplier_invoices]
        paid_customer_invoice_current_year = [item['customer_invoice_paid'] or 0 for item in paid_customer_invoices]
        paid_supplier_invoice_current_year = [item['supplier_invoice_paid'] or 0 for item in paid_supplier_invoices]

        return (
            customer_invoice_current_year,
            [0.0],  # credit_note_current_year placeholder
            supplier_invoice_current_year,
            [0.0],  # refund_current_year placeholder
            paid_customer_invoice_current_year,
            paid_supplier_invoice_current_year,
            [0.0],  # paid_customer_credit_current_year placeholder
            [0.0],  # paid_supplier_refund_current_year placeholder
        )

    @api.model
    def get_overdues(self, *post):
        """Get overdue invoices with AMS member information"""
        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ account_move.state in ('posted', 'draft')"""
        else:
            states_arg = """ account_move.state = 'posted'"""

        # Enhanced query with AMS member information
        self._cr.execute(('''
            SELECT 
                res_partner.name as partner,
                res_partner.id as partner_id,
                SUM(account_move.amount_total) as amount,
                COUNT(CASE WHEN account_move.is_ams_subscription_invoice THEN 1 END) as subscription_invoices,
                COUNT(CASE WHEN account_move.is_ams_renewal_invoice THEN 1 END) as renewal_invoices
            FROM account_move
            LEFT JOIN res_partner ON account_move.partner_id = res_partner.id
            WHERE account_move.move_type = 'out_invoice'
                AND account_move.payment_state = 'not_paid'
                AND %s
                AND account_move.company_id IN %s
                AND account_move.invoice_date_due < NOW()
            GROUP BY res_partner.id, res_partner.name
            ORDER BY amount DESC
        ''') % (states_arg, tuple(company_id)))
        
        records = self._cr.dictfetchall()
        
        # Limit to top 10 and aggregate others
        due_partner = [item['partner'] for item in records[:9]]
        due_amount = [item['amount'] for item in records[:9]]
        
        if len(records) > 9:
            others_amount = sum(item['amount'] for item in records[9:])
            due_amount.append(others_amount)
            due_partner.append("Others")
        
        return {
            'due_partner': due_partner,
            'due_amount': due_amount,
            'result': records,
        }

    @api.model
    def bank_balance(self, *post):
        """Get bank balance information"""
        company_id = self.get_current_company_value()

        states_arg = ""
        if post != ('posted',):
            states_arg = """ move_id.state in ('posted', 'draft')"""
        else:
            states_arg = """ move_id.state = 'posted'"""

        # Updated for Odoo 18 account types
        self._cr.execute(('''
            SELECT 
                account_account.name as name,
                SUM(balance) as balance,
                MIN(account_account.id) as id
            FROM account_move_line
            LEFT JOIN account_account ON account_account.id = account_move_line.account_id
            WHERE account_account.account_type IN ('asset_cash', 'asset_current')
                AND %s
                AND account_move_line.company_id IN %s
            GROUP BY account_account.name
        ''') % (states_arg, tuple(company_id)))

        records = self._cr.dictfetchall()
        
        banks = [item['name'] for item in records]
        banking = [item['balance'] for item in records]
        bank_ids = [item['id'] for item in records]

        return {
            'banks': banks,
            'banking': banking,
            'bank_ids': bank_ids
        }

    @api.model
    def get_ams_subscription_revenue(self, period='this_month'):
        """Get AMS subscription revenue analytics"""
        company_id = self.get_current_company_value()
        
        if period == 'this_month':
            time_filter = """
                AND EXTRACT(month FROM account_move.date) = EXTRACT(month FROM DATE(NOW()))
                AND EXTRACT(YEAR FROM account_move.date) = EXTRACT(YEAR FROM DATE(NOW()))
            """
        elif period == 'this_year':
            time_filter = """
                AND EXTRACT(YEAR FROM account_move.date) = EXTRACT(YEAR FROM DATE(NOW()))
            """
        else:
            time_filter = ""
        
        self._cr.execute(('''
            SELECT 
                ast.name as subscription_type,
                COUNT(am.id) as invoice_count,
                SUM(am.amount_total) as total_revenue,
                AVG(am.amount_total) as avg_revenue
            FROM account_move am
            LEFT JOIN ams_subscription sub ON am.ams_subscription_id = sub.id
            LEFT JOIN ams_subscription_type ast ON sub.subscription_type_id = ast.id
            WHERE am.is_ams_subscription_invoice = true
                AND am.state = 'posted'
                AND am.company_id IN %s
                %s
            GROUP BY ast.name
            ORDER BY total_revenue DESC
        ''') % (tuple(company_id), time_filter))
        
        return self._cr.dictfetchall()

    @api.model
    def get_ams_chapter_revenue(self, period='this_month'):
        """Get revenue by AMS chapter"""
        company_id = self.get_current_company_value()
        
        if period == 'this_month':
            time_filter = """
                AND EXTRACT(month FROM account_move.date) = EXTRACT(month FROM DATE(NOW()))
                AND EXTRACT(YEAR FROM account_move.date) = EXTRACT(YEAR FROM DATE(NOW()))
            """
        elif period == 'this_year':
            time_filter = """
                AND EXTRACT(YEAR FROM account_move.date) = EXTRACT(YEAR FROM DATE(NOW()))
            """
        else:
            time_filter = ""
        
        self._cr.execute(('''
            SELECT 
                ac.name as chapter_name,
                COUNT(am.id) as invoice_count,
                SUM(am.amount_total) as total_revenue,
                AVG(am.amount_total) as avg_revenue
            FROM account_move am
            LEFT JOIN ams_chapter ac ON am.ams_chapter_id = ac.id
            WHERE am.ams_chapter_id IS NOT NULL
                AND am.state = 'posted'
                AND am.company_id IN %s
                %s
            GROUP BY ac.name
            ORDER BY total_revenue DESC
        ''') % (tuple(company_id), time_filter))
        
        return self._cr.dictfetchall()

    @api.model
    def get_ams_renewal_pipeline(self):
        """Get AMS renewal pipeline data"""
        company_id = self.get_current_company_value()
        
        self._cr.execute(('''
            SELECT 
                DATE_TRUNC('month', s.next_renewal_date) as renewal_month,
                COUNT(s.id) as renewal_count,
                SUM(s.amount) as expected_revenue,
                COUNT(CASE WHEN s.auto_renewal THEN 1 END) as auto_renewal_count
            FROM ams_subscription s
            WHERE s.state = 'active'
                AND s.is_recurring = true
                AND s.next_renewal_date >= NOW()
                AND s.next_renewal_date <= NOW() + INTERVAL '12 months'
                AND s.partner_id IN (
                    SELECT DISTINCT partner_id 
                    FROM account_move 
                    WHERE company_id IN %s
                )
            GROUP BY DATE_TRUNC('month', s.next_renewal_date)
            ORDER BY renewal_month
        ''') % (tuple(company_id),))
        
        return self._cr.dictfetchall()

    def get_current_company_value(self):
        """Get current company values from context"""
        if request and hasattr(request, 'httprequest') and request.httprequest.cookies.get('cids'):
            cookies_cids = [int(r) for r in request.httprequest.cookies.get('cids').split(",")]
        else:
            cookies_cids = [self.env.company.id]

        # Validate company access
        for company_id in cookies_cids[:]:
            if company_id not in self.env.user.company_ids.ids:
                cookies_cids.remove(company_id)
        
        if not cookies_cids:
            cookies_cids = [self.env.company.id]
        
        if len(cookies_cids) == 1:
            cookies_cids.append(0)
        
        return cookies_cids

    @api.model
    def get_currency(self):
        """Get currency information for dashboard"""
        company_ids = self.get_current_company_value()
        if 0 in company_ids:
            company_ids.remove(0)
        
        current_company_id = company_ids[0]
        current_company = self.env['res.company'].browse(current_company_id)
        default_currency = current_company.currency_id
        
        lang = self.env.user.lang or 'en_US'
        lang = lang.replace("_", '-')
        
        return {
            'position': default_currency.position,
            'symbol': default_currency.symbol,
            'language': lang
        }

    @api.model
    def click_invoice_year(self, *post):
        """Click through to yearly invoices"""
        company_id = self.get_current_company_value()
        states_arg = """ account_move.state = 'posted' """ if post == ('posted',) else """ account_move.state in ('posted', 'draft') """
        
        self._cr.execute(('''
            SELECT account_move.id  
            FROM account_move 
            WHERE move_type = 'out_invoice'
                AND %s
                AND EXTRACT(YEAR FROM account_move.date) = EXTRACT(YEAR FROM DATE(NOW()))
                AND account_move.company_id IN %s
        ''') % (states_arg, tuple(company_id)))
        
        return [row[0] for row in self._cr.fetchall()]

    @api.model
    def click_invoice_month(self, *post):
        """Click through to monthly invoices"""
        company_id = self.get_current_company_value()
        states_arg = """ account_move.state = 'posted' """ if post == ('posted',) else """ account_move.state in ('posted', 'draft') """
        
        self._cr.execute(('''
            SELECT account_move.id 
            FROM account_move 
            WHERE move_type = 'out_invoice'
                AND %s
                AND EXTRACT(month FROM account_move.date) = EXTRACT(month FROM DATE(NOW()))
                AND EXTRACT(YEAR FROM account_move.date) = EXTRACT(YEAR FROM DATE(NOW()))
                AND account_move.company_id IN %s
        ''') % (states_arg, tuple(company_id)))
        
        return [row[0] for row in self._cr.fetchall()]