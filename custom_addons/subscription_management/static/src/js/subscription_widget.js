/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Subscription Dashboard Widget
 */
export class SubscriptionDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            totalSubscriptions: 0,
            activeSubscriptions: 0,
            trialSubscriptions: 0,
            monthlyRecurringRevenue: 0,
            churnRate: 0,
            loading: true
        });

        onMounted(() => {
            this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;
            
            // Load subscription metrics
            const subscriptionData = await this.orm.searchRead(
                "subscription.subscription",
                [],
                ["state", "price", "currency_id"]
            );

            // Calculate metrics
            this.state.totalSubscriptions = subscriptionData.length;
            this.state.activeSubscriptions = subscriptionData.filter(s => s.state === 'active').length;
            this.state.trialSubscriptions = subscriptionData.filter(s => s.state === 'trial').length;
            
            // Calculate MRR
            this.state.monthlyRecurringRevenue = subscriptionData
                .filter(s => ['active', 'trial'].includes(s.state))
                .reduce((sum, s) => sum + (s.price || 0), 0);
            
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.notification.add("Error loading dashboard data", { type: "danger" });
            this.state.loading = false;
        }
    }
}

SubscriptionDashboard.template = "subscription_management.SubscriptionDashboard";

/**
 * Usage Tracker Widget
 */
export class UsageTracker extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.props = this.props || {};
        this.state = useState({
            currentUsage: this.props.currentUsage || 0,
            usageLimit: this.props.usageLimit || 0,
            usageType: this.props.usageType || 'API calls',
            subscriptionId: this.props.subscriptionId
        });
    }

    get usagePercentage() {
        if (this.state.usageLimit === 0) return 0;
        return Math.min(100, (this.state.currentUsage / this.state.usageLimit) * 100);
    }

    get usageStatus() {
        const percentage = this.usagePercentage;
        if (percentage >= 100) return 'danger';
        if (percentage >= 80) return 'warning';
        return 'normal';
    }
}

UsageTracker.template = "subscription_management.UsageTracker";

// Register components
registry.category("subscription_widgets").add("SubscriptionDashboard", SubscriptionDashboard);
registry.category("subscription_widgets").add("UsageTracker", UsageTracker);