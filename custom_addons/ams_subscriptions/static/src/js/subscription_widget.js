odoo.define('ams_subscriptions.subscription_widget', function (require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');
var utils = require('web.utils');

var _t = core._t;

/**
 * Subscription Price Calculator Widget
 */
var SubscriptionPriceCalculator = Widget.extend({
    template: 'SubscriptionPriceCalculator',
    
    events: {
        'change input[name="billing_period"]': '_onBillingPeriodChange',
        'change input[name="billing_interval"]': '_onBillingIntervalChange',
        'click .btn-calculate': '_calculatePrice',
    },
    
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.basePrice = options.basePrice || 0;
        this.billingPeriod = options.billingPeriod || 'annual';
        this.billingInterval = options.billingInterval || 1;
    },
    
    start: function () {
        this._super.apply(this, arguments);
        this._updatePriceDisplay();
    },
    
    _onBillingPeriodChange: function (event) {
        this.billingPeriod = event.target.value;
        this._updatePriceDisplay();
    },
    
    _onBillingIntervalChange: function (event) {
        this.billingInterval = parseInt(event.target.value) || 1;
        this._updatePriceDisplay();
    },
    
    _calculatePrice: function () {
        var multipliers = {
            'daily': 365,
            'weekly': 52,
            'monthly': 12,
            'quarterly': 4,
            'semi_annual': 2,
            'annual': 1,
            'biennial': 0.5
        };
        
        var multiplier = multipliers[this.billingPeriod] || 1;
        var periodPrice = this.basePrice / multiplier * this.billingInterval;
        
        this._updatePriceDisplay(periodPrice);
    },
    
    _updatePriceDisplay: function (price) {
        price = price || this.basePrice;
        this.$('.price-display').text('$' + price.toFixed(2));
        
        var periodText = this.billingPeriod.replace('_', ' ');
        if (this.billingInterval > 1) {
            periodText = 'every ' + this.billingInterval + ' ' + periodText + 's';
        } else {
            periodText = 'per ' + periodText;
        }
        this.$('.period-display').text(periodText);
    }
});

/**
 * Subscription Status Widget
 */
var SubscriptionStatusWidget = Widget.extend({
    template: 'SubscriptionStatusWidget',
    
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.subscription = options.subscription || {};
        this.showActions = options.showActions !== false;
    },
    
    start: function () {
        this._super.apply(this, arguments);
        this._updateStatusDisplay();
        this._setupCountdown();
    },
    
    _updateStatusDisplay: function () {
        var $status = this.$('.subscription-status');
        var $badge = this.$('.status-badge');
        
        $badge.removeClass('badge-success badge-warning badge-danger badge-secondary');
        
        switch (this.subscription.state) {
            case 'active':
                $badge.addClass('badge-success').text(_t('Active'));
                break;
            case 'trial':
                $badge.addClass('badge-info').text(_t('Trial'));
                break;
            case 'expired':
                $badge.addClass('badge-danger').text(_t('Expired'));
                break;
            case 'cancelled':
                $badge.addClass('badge-secondary').text(_t('Cancelled'));
                break;
            default:
                $badge.addClass('badge-light').text(this.subscription.state || _t('Unknown'));
        }
        
        // Show expiry warning
        if (this.subscription.days_until_expiry <= 30 && this.subscription.days_until_expiry >= 0) {
            this.$('.expiry-warning').removeClass('d-none');
            this.$('.days-until-expiry').text(this.subscription.days_until_expiry);
        }
        
        // Show grace period info
        if (this.subscription.in_grace_period) {
            this.$('.grace-period-info').removeClass('d-none');
        }
    },
    
    _setupCountdown: function () {
        if (this.subscription.end_date && this.subscription.state === 'active') {
            var endDate = new Date(this.subscription.end_date);
            var now = new Date();
            var timeLeft = endDate - now;
            
            if (timeLeft > 0) {
                this._startCountdown(timeLeft);
            }
        }
    },
    
    _startCountdown: function (timeLeft) {
        var self = this;
        var $countdown = this.$('.countdown-timer');
        
        if ($countdown.length === 0) return;
        
        var updateCountdown = function () {
            var days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
            var hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            var minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
            
            $countdown.html(
                '<span class="countdown-days">' + days + '</span>d ' +
                '<span class="countdown-hours">' + hours + '</span>h ' +
                '<span class="countdown-minutes">' + minutes + '</span>m'
            );
            
            timeLeft -= 60000; // Subtract 1 minute
            
            if (timeLeft <= 0) {
                $countdown.html('<span class="text-danger">Expired</span>');
                return;
            }
            
            setTimeout(updateCountdown, 60000); // Update every minute
        };
        
        updateCountdown();
    }
});

// Export widgets
return {
    SubscriptionPriceCalculator: SubscriptionPriceCalculator,
    SubscriptionStatusWidget: SubscriptionStatusWidget,
};

});