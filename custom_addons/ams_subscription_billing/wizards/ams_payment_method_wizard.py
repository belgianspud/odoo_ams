# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class AMSPaymentMethodWizard(models.TransientModel):
    """Wizard for Setting Up Payment Methods for Subscriptions"""
    _name = 'ams.payment.method.wizard'
    _description = 'AMS Payment Method Setup Wizard'
    
    # =============================================================================
    # BASIC INFORMATION
    # =============================================================================
    
    subscription_id = fields.Many2one(
        'ams.subscription',
        string='Subscription',
        required=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        readonly=True
    )
    
    action_type = fields.Selection([
        ('new', 'Add New Payment Method'),
        ('update', 'Update Existing Payment Method'),
        ('remove', 'Remove Payment Method'),
        ('set_default', 'Set Default Payment Method'),
    ], string='Action', default='new', required=True)
    
    existing_payment_method_id = fields.Many2one(
        'ams.payment.method',
        string='Existing Payment Method',
        domain="[('partner_id', '=', partner_id)]"
    )
    
    # =============================================================================
    # PAYMENT METHOD DETAILS
    # =============================================================================
    
    payment_type = fields.Selection([
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('bank_account', 'Bank Account (ACH)'),
        ('paypal', 'PayPal'),
        ('apple_pay', 'Apple Pay'),
        ('google_pay', 'Google Pay'),
        ('sepa', 'SEPA Direct Debit'),
        ('wire_transfer', 'Wire Transfer'),
        ('check', 'Check'),
        ('other', 'Other'),
    ], string='Payment Type', default='credit_card')
    
    # Credit/Debit Card Information
    card_number = fields.Char(
        string='Card Number',
        help='Credit/Debit card number (will be tokenized)'
    )
    
    card_holder_name = fields.Char(
        string='Card Holder Name'
    )
    
    expiry_month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Expiry Month')
    
    expiry_year = fields.Selection(
        selection='_get_expiry_years',
        string='Expiry Year'
    )
    
    cvv = fields.Char(
        string='CVV',
        help='Card verification value (3-4 digits)'
    )
    
    # Bank Account Information
    bank_name = fields.Char(
        string='Bank Name'
    )
    
    account_number = fields.Char(
        string='Account Number',
        help='Bank account number (will be tokenized)'
    )
    
    routing_number = fields.Char(
        string='Routing Number',
        help='Bank routing number'
    )
    
    account_type = fields.Selection([
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('business_checking', 'Business Checking'),
        ('business_savings', 'Business Savings'),
    ], string='Account Type', default='checking')
    
    account_holder_name = fields.Char(
        string='Account Holder Name'
    )
    
    # Digital Wallet Information
    wallet_email = fields.Char(
        string='Wallet Email',
        help='Email associated with digital wallet'
    )
    
    wallet_account_id = fields.Char(
        string='Wallet Account ID',
        help='Account ID for digital wallet'
    )
    
    # Billing Address
    use_subscription_address = fields.Boolean(
        string='Use Subscription Address',
        default=True,
        help='Use the subscription billing address'
    )
    
    billing_street = fields.Char(string='Street')
    billing_street2 = fields.Char(string='Street 2')
    billing_city = fields.Char(string='City')
    billing_state_id = fields.Many2one('res.country.state', string='State')
    billing_zip = fields.Char(string='ZIP Code')
    billing_country_id = fields.Many2one('res.country', string='Country')
    
    # =============================================================================
    # CONFIGURATION OPTIONS
    # =============================================================================
    
    set_as_default = fields.Boolean(
        string='Set as Default',
        default=True,
        help='Set this as the default payment method for the subscription'
    )
    
    enable_auto_billing = fields.Boolean(
        string='Enable Auto Billing',
        default=True,
        help='Enable automatic billing with this payment method'
    )
    
    send_confirmation = fields.Boolean(
        string='Send Confirmation Email',
        default=True,
        help='Send confirmation email to customer'
    )
    
    # =============================================================================
    # SECURITY AND VALIDATION
    # =============================================================================
    
    terms_accepted = fields.Boolean(
        string='Terms Accepted',
        help='Customer has accepted payment terms and conditions'
    )
    
    authorization_code = fields.Char(
        string='Authorization Code',
        help='Authorization code from payment gateway'
    )
    
    verification_status = fields.Selection([
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('failed', 'Verification Failed'),
    ], string='Verification Status', default='pending')
    
    # =============================================================================
    # GATEWAY INTEGRATION
    # =============================================================================
    
    gateway_provider = fields.Selection([
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('authorize_net', 'Authorize.Net'),
        ('square', 'Square'),
        ('braintree', 'Braintree'),
        ('adyen', 'Adyen'),
        ('manual', 'Manual Processing'),
    ], string='Payment Gateway', default='stripe')
    
    test_mode = fields.Boolean(
        string='Test Mode',
        default=False,
        help='Process in test mode'
    )
    
    # =============================================================================
    # COMPUTED FIELDS
    # =============================================================================
    
    def _get_expiry_years(self):
        """Generate expiry year options"""
        import datetime
        current_year = datetime.datetime.now().year
        years = []
        for i in range(10):  # Next 10 years
            year = current_year + i
            years.append((str(year), str(year)))
        return years
    
    masked_card_number = fields.Char(
        string='Card Number',
        compute='_compute_masked_card_number'
    )
    
    @api.depends('card_number')
    def _compute_masked_card_number(self):
        """Show masked card number for security"""
        for wizard in self:
            if wizard.card_number and len(wizard.card_number) >= 4:
                wizard.masked_card_number = '*' * (len(wizard.card_number) - 4) + wizard.card_number[-4:]
            else:
                wizard.masked_card_number = wizard.card_number
    
    # =============================================================================
    # ONCHANGE METHODS
    # =============================================================================
    
    @api.onchange('action_type')
    def _onchange_action_type(self):
        """Handle action type changes"""
        if self.action_type in ['update', 'remove', 'set_default']:
            # Show existing payment methods
            domain = [('partner_id', '=', self.partner_id.id)]
            return {
                'domain': {
                    'existing_payment_method_id': domain
                }
            }
    
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        """Clear irrelevant fields when payment type changes"""
        if self.payment_type not in ['credit_card', 'debit_card']:
            self.card_number = False
            self.card_holder_name = False
            self.expiry_month = False
            self.expiry_year = False
            self.cvv = False
        
        if self.payment_type != 'bank_account':
            self.bank_name = False
            self.account_number = False
            self.routing_number = False
            self.account_type = False
            self.account_holder_name = False
        
        if self.payment_type not in ['paypal', 'apple_pay', 'google_pay']:
            self.wallet_email = False
            self.wallet_account_id = False
    
    @api.onchange('use_subscription_address')
    def _onchange_use_subscription_address(self):
        """Fill billing address from subscription"""
        if self.use_subscription_address and self.subscription_id:
            partner = self.subscription_id.partner_id
            self.billing_street = partner.street
            self.billing_street2 = partner.street2
            self.billing_city = partner.city
            self.billing_state_id = partner.state_id
            self.billing_zip = partner.zip
            self.billing_country_id = partner.country_id
    
    @api.onchange('existing_payment_method_id')
    def _onchange_existing_payment_method(self):
        """Load existing payment method details"""
        if self.existing_payment_method_id and self.action_type == 'update':
            method = self.existing_payment_method_id
            self.payment_type = method.payment_type
            self.card_holder_name = method.card_holder_name
            self.expiry_month = method.expiry_month
            self.expiry_year = method.expiry_year
            self.bank_name = method.bank_name
            self.account_type = method.account_type
            self.account_holder_name = method.account_holder_name
            # Don't load sensitive data like card numbers
    
    # =============================================================================
    # VALIDATION
    # =============================================================================
    
    @api.constrains('card_number')
    def _check_card_number(self):
        """Validate card number"""
        for wizard in self:
            if wizard.payment_type in ['credit_card', 'debit_card'] and wizard.card_number:
                if not wizard._validate_card_number(wizard.card_number):
                    raise ValidationError(_('Invalid card number'))
    
    @api.constrains('cvv')
    def _check_cvv(self):
        """Validate CVV"""
        for wizard in self:
            if wizard.payment_type in ['credit_card', 'debit_card'] and wizard.cvv:
                if not wizard.cvv.isdigit() or len(wizard.cvv) not in [3, 4]:
                    raise ValidationError(_('CVV must be 3 or 4 digits'))
    
    @api.constrains('account_number')
    def _check_account_number(self):
        """Validate bank account number"""
        for wizard in self:
            if wizard.payment_type == 'bank_account' and wizard.account_number:
                if not wizard.account_number.isdigit() or len(wizard.account_number) < 4:
                    raise ValidationError(_('Invalid account number'))
    
    @api.constrains('routing_number')
    def _check_routing_number(self):
        """Validate routing number"""
        for wizard in self:
            if wizard.payment_type == 'bank_account' and wizard.routing_number:
                if not wizard.routing_number.isdigit() or len(wizard.routing_number) != 9:
                    raise ValidationError(_('Routing number must be 9 digits'))
    
    def _validate_card_number(self, card_number):
        """Validate card number using Luhn algorithm"""
        def luhn_check(card_num):
            """Luhn algorithm for card validation"""
            def digits_of(n):
                return [int(d) for d in str(n)]
            
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10 == 0
        
        # Remove spaces and dashes
        card_clean = ''.join(card_number.split()).replace('-', '')
        
        # Check if all digits
        if not card_clean.isdigit():
            return False
        
        # Check length (most cards are 13-19 digits)
        if len(card_clean) < 13 or len(card_clean) > 19:
            return False
        
        # Run Luhn check
        return luhn_check(card_clean)
    
    # =============================================================================
    # MAIN ACTIONS
    # =============================================================================
    
    def action_save_payment_method(self):
        """Main action to save payment method"""
        self.ensure_one()
        
        if self.action_type == 'new':
            return self._create_new_payment_method()
        elif self.action_type == 'update':
            return self._update_payment_method()
        elif self.action_type == 'remove':
            return self._remove_payment_method()
        elif self.action_type == 'set_default':
            return self._set_default_payment_method()
    
    def _create_new_payment_method(self):
        """Create new payment method"""
        # Validate required fields
        self._validate_payment_method_data()
        
        # Verify with payment gateway
        if not self.test_mode:
            verification_result = self._verify_with_gateway()
            if not verification_result.get('success'):
                raise UserError(_('Payment method verification failed: %s') % 
                              verification_result.get('error', 'Unknown error'))
        
        # Create payment method record
        payment_method_vals = self._prepare_payment_method_values()
        payment_method = self.env['ams.payment.method'].create(payment_method_vals)
        
        # Set as default if requested
        if self.set_as_default:
            self.subscription_id.payment_method_id = payment_method.id
        
        # Enable auto billing if requested
        if self.enable_auto_billing:
            self.subscription_id.enable_auto_payment = True
        
        # Send confirmation email
        if self.send_confirmation:
            self._send_confirmation_email(payment_method)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment Method Created'),
            'res_model': 'ams.payment.method',
            'res_id': payment_method.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _update_payment_method(self):
        """Update existing payment method"""
        if not self.existing_payment_method_id:
            raise UserError(_('Please select a payment method to update'))
        
        # Validate new data
        self._validate_payment_method_data()
        
        # Verify with gateway if sensitive data changed
        if self._has_sensitive_data_changed():
            verification_result = self._verify_with_gateway()
            if not verification_result.get('success'):
                raise UserError(_('Payment method verification failed: %s') % 
                              verification_result.get('error', 'Unknown error'))
        
        # Update payment method
        update_vals = self._prepare_payment_method_update_values()
        self.existing_payment_method_id.write(update_vals)
        
        # Send confirmation email
        if self.send_confirmation:
            self._send_update_confirmation_email(self.existing_payment_method_id)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Payment method updated successfully'),
                'type': 'success',
            }
        }
    
    def _remove_payment_method(self):
        """Remove payment method"""
        if not self.existing_payment_method_id:
            raise UserError(_('Please select a payment method to remove'))
        
        # Check if it's the default payment method
        if self.subscription_id.payment_method_id == self.existing_payment_method_id:
            # Find alternative payment method
            other_methods = self.env['ams.payment.method'].search([
                ('partner_id', '=', self.partner_id.id),
                ('id', '!=', self.existing_payment_method_id.id),
                ('is_active', '=', True),
            ])
            
            if other_methods:
                self.subscription_id.payment_method_id = other_methods[0]
            else:
                self.subscription_id.payment_method_id = False
                self.subscription_id.enable_auto_payment = False
        
        # Deactivate payment method (don't delete for audit trail)
        self.existing_payment_method_id.is_active = False
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Payment method removed successfully'),
                'type': 'success',
            }
        }
    
    def _set_default_payment_method(self):
        """Set default payment method"""
        if not self.existing_payment_method_id:
            raise UserError(_('Please select a payment method to set as default'))
        
        self.subscription_id.payment_method_id = self.existing_payment_method_id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Default payment method updated successfully'),
                'type': 'success',
            }
        }
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    def _validate_payment_method_data(self):
        """Validate payment method data"""
        if self.payment_type in ['credit_card', 'debit_card']:
            if not all([self.card_number, self.card_holder_name, self.expiry_month, self.expiry_year, self.cvv]):
                raise UserError(_('All card fields are required'))
        
        elif self.payment_type == 'bank_account':
            if not all([self.account_number, self.routing_number, self.account_holder_name]):
                raise UserError(_('All bank account fields are required'))
        
        elif self.payment_type in ['paypal', 'apple_pay', 'google_pay']:
            if not self.wallet_email:
                raise UserError(_('Wallet email is required'))
        
        if not self.terms_accepted:
            raise UserError(_('Terms and conditions must be accepted'))
    
    def _verify_with_gateway(self):
        """Verify payment method with payment gateway"""
        # This is a placeholder for actual gateway integration
        # In real implementation, this would:
        # 1. Connect to the payment gateway API
        # 2. Verify the payment method
        # 3. Get a token for future use
        # 4. Return success/failure result
        
        _logger.info(f'Verifying payment method with {self.gateway_provider}')
        
        # Simulate gateway verification
        if self.test_mode:
            return {
                'success': True,
                'token': f'test_token_{self.id}',
                'gateway_customer_id': f'test_customer_{self.partner_id.id}',
            }
        else:
            # In production, make actual API call
            return {
                'success': True,  # Simulated success
                'token': f'prod_token_{self.id}',
                'gateway_customer_id': f'prod_customer_{self.partner_id.id}',
            }
    
    def _prepare_payment_method_values(self):
        """Prepare values for creating payment method"""
        vals = {
            'partner_id': self.partner_id.id,
            'payment_type': self.payment_type,
            'gateway_provider': self.gateway_provider,
            'is_active': True,
            'is_verified': True,  # Assuming verification passed
        }
        
        # Add type-specific fields
        if self.payment_type in ['credit_card', 'debit_card']:
            vals.update({
                'card_holder_name': self.card_holder_name,
                'last_four_digits': self.card_number[-4:] if self.card_number else '',
                'expiry_month': self.expiry_month,
                'expiry_year': self.expiry_year,
                'card_brand': self._detect_card_brand(self.card_number),
            })
        
        elif self.payment_type == 'bank_account':
            vals.update({
                'bank_name': self.bank_name,
                'account_type': self.account_type,
                'account_holder_name': self.account_holder_name,
                'last_four_digits': self.account_number[-4:] if self.account_number else '',
                'routing_number_masked': self.routing_number[:5] + 'XXXX' if self.routing_number else '',
            })
        
        elif self.payment_type in ['paypal', 'apple_pay', 'google_pay']:
            vals.update({
                'wallet_email': self.wallet_email,
                'wallet_account_id': self.wallet_account_id,
            })
        
        # Add billing address
        if not self.use_subscription_address:
            vals.update({
                'billing_street': self.billing_street,
                'billing_street2': self.billing_street2,
                'billing_city': self.billing_city,
                'billing_state_id': self.billing_state_id.id if self.billing_state_id else False,
                'billing_zip': self.billing_zip,
                'billing_country_id': self.billing_country_id.id if self.billing_country_id else False,
            })
        
        return vals
    
    def _prepare_payment_method_update_values(self):
        """Prepare values for updating payment method"""
        vals = {}
        
        # Only update non-sensitive fields that can be changed
        if self.payment_type in ['credit_card', 'debit_card']:
            if self.card_holder_name != self.existing_payment_method_id.card_holder_name:
                vals['card_holder_name'] = self.card_holder_name
            
            # Handle expiry date updates
            if (self.expiry_month != self.existing_payment_method_id.expiry_month or
                self.expiry_year != self.existing_payment_method_id.expiry_year):
                vals.update({
                    'expiry_month': self.expiry_month,
                    'expiry_year': self.expiry_year,
                })
        
        elif self.payment_type == 'bank_account':
            if self.account_holder_name != self.existing_payment_method_id.account_holder_name:
                vals['account_holder_name'] = self.account_holder_name
            if self.bank_name != self.existing_payment_method_id.bank_name:
                vals['bank_name'] = self.bank_name
        
        # Update billing address if changed
        if not self.use_subscription_address:
            address_fields = ['billing_street', 'billing_street2', 'billing_city', 'billing_zip']
            for field in address_fields:
                if getattr(self, field) != getattr(self.existing_payment_method_id, field):
                    vals[field] = getattr(self, field)
            
            if self.billing_state_id != self.existing_payment_method_id.billing_state_id:
                vals['billing_state_id'] = self.billing_state_id.id if self.billing_state_id else False
            
            if self.billing_country_id != self.existing_payment_method_id.billing_country_id:
                vals['billing_country_id'] = self.billing_country_id.id if self.billing_country_id else False
        
        return vals
    
    def _has_sensitive_data_changed(self):
        """Check if sensitive data (requiring re-verification) has changed"""
        if self.payment_type in ['credit_card', 'debit_card']:
            return bool(self.card_number or self.cvv)
        elif self.payment_type == 'bank_account':
            return bool(self.account_number or self.routing_number)
        elif self.payment_type in ['paypal', 'apple_pay', 'google_pay']:
            return self.wallet_email != self.existing_payment_method_id.wallet_email
        
        return False
    
    def _detect_card_brand(self, card_number):
        """Detect card brand from card number"""
        if not card_number:
            return 'unknown'
        
        # Remove spaces and dashes
        card_clean = ''.join(card_number.split()).replace('-', '')
        
        # Basic brand detection based on first digits
        if card_clean.startswith('4'):
            return 'visa'
        elif card_clean.startswith(('51', '52', '53', '54', '55')):
            return 'mastercard'
        elif card_clean.startswith(('34', '37')):
            return 'amex'
        elif card_clean.startswith('6011'):
            return 'discover'
        else:
            return 'unknown'
    
    def _send_confirmation_email(self, payment_method):
        """Send confirmation email for new payment method"""
        template = self.env.ref('ams_subscription_billing.email_template_payment_method_added', False)
        if template:
            template.send_mail(payment_method.id, force_send=True)
    
    def _send_update_confirmation_email(self, payment_method):
        """Send confirmation email for updated payment method"""
        template = self.env.ref('ams_subscription_billing.email_template_payment_method_updated', False)
        if template:
            template.send_mail(payment_method.id, force_send=True)
    
    # =============================================================================
    # SECURITY ACTIONS
    # =============================================================================
    
    def action_test_payment_method(self):
        """Test payment method with small authorization"""
        self.ensure_one()
        
        if not self.terms_accepted:
            raise UserError(_('Terms must be accepted before testing'))
        
        # Perform test authorization
        test_result = self._perform_test_authorization()
        
        if test_result.get('success'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Payment method test successful'),
                    'type': 'success',
                }
            }
        else:
            raise UserError(_('Payment method test failed: %s') % 
                          test_result.get('error', 'Unknown error'))
    
    def _perform_test_authorization(self):
        """Perform test authorization (usually $1.00 that gets voided)"""
        # This would integrate with payment gateway for test authorization
        _logger.info(f'Performing test authorization for payment method')
        
        # Simulate test authorization
        return {
            'success': True,
            'authorization_code': f'TEST_AUTH_{self.id}',
            'amount': 1.00,
        }
    
    def action_verify_micro_deposits(self):
        """Verify micro deposits for bank accounts"""
        self.ensure_one()
        
        if self.payment_type != 'bank_account':
            raise UserError(_('Micro deposit verification is only for bank accounts'))
        
        return {
            'name': _('Verify Micro Deposits'),
            'type': 'ir.actions.act_window',
            'res_model': 'ams.micro.deposit.verification.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_method_wizard_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }