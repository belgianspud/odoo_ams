/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { formatCurrency } from "@web/core/utils/numbers";

/**
 * Membership Status Widget
 * Shows membership status with appropriate styling
 */
export class MembershipStatusWidget extends Component {
    static template = "membership_core.MembershipStatusWidget";
    static props = {
        value: { type: String, optional: true },
        readonly: { type: Boolean, optional: true },
    };

    get statusClass() {
        const statusClasses = {
            'active': 'membership_status_active',
            'grace': 'membership_status_grace',
            'suspended': 'membership_status_suspended',
            'terminated': 'membership_status_terminated',
            'cancelled': 'membership_status_cancelled',
            'draft': 'membership_status_draft',
        };
        return statusClasses[this.props.value] || 'membership_status_draft';
    }

    get statusText() {
        const statusTexts = {
            'active': 'Active',
            'grace': 'Grace Period',
            'suspended': 'Suspended',
            'terminated': 'Terminated',
            'cancelled': 'Cancelled',
            'draft': 'Draft',
        };
        return statusTexts[this.props.value] || 'Unknown';
    }
}

/**
 * Membership Expiry Warning Widget
 * Shows expiry warnings with days calculation
 */
export class MembershipExpiryWidget extends Component {
    static template = "membership_core.MembershipExpiryWidget";
    static props = {
        endDate: { type: String, optional: true },
        state: { type: String, optional: true },
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({
            daysUntilExpiry: 0,
            isExpired: false,
            isExpiringSoon: false,
        });
        this.calculateDays();
    }

    calculateDays() {
        if (!this.props.endDate) {
            return; // Lifetime membership
        }

        const today = new Date();
        const endDate = new Date(this.props.endDate);
        const timeDiff = endDate.getTime() - today.getTime();
        const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));

        this.state.daysUntilExpiry = daysDiff;
        this.state.isExpired = daysDiff < 0;
        this.state.isExpiringSoon = daysDiff > 0 && daysDiff <= 30;
    }

    get warningClass() {
        if (this.state.isExpired) {
            return 'membership_expiry_critical';
        } else if (this.state.isExpiringSoon) {
            return 'membership_expiry_warning';
        }
        return 'membership_expiry_good';
    }

    get warningIcon() {
        if (this.state.isExpired) {
            return 'fa-exclamation-triangle';
        } else if (this.state.isExpiringSoon) {
            return 'fa-clock-o';
        }
        return 'fa-check-circle';
    }

    get warningText() {
        if (!this.props.endDate) {
            return 'Lifetime Membership';
        }
        
        if (this.state.isExpired) {
            const daysOverdue = Math.abs(this.state.daysUntilExpiry);
            return `Expired ${daysOverdue} day${daysOverdue !== 1 ? 's' : ''} ago`;
        } else if (this.state.isExpiringSoon) {
            return `Expires in ${this.state.daysUntilExpiry} day${this.state.daysUntilExpiry !== 1 ? 's' : ''}`;
        }
        return `${this.state.daysUntilExpiry} days remaining`;
    }
}

/**
 * Membership Statistics Dashboard
 * Shows membership statistics in a dashboard format
 */
export class MembershipStatsDashboard extends Component {
    static template = "membership_core.MembershipStatsDashboard";
    static props = {
        membershipTypeId: { type: Number, optional: true },
        partnerId: { type: Number, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            stats: {
                totalMembers: 0,
                activeMembers: 0,
                expiringMembers: 0,
                totalRevenue: 0,
                newThisMonth: 0,
                renewalRate: 0,
            },
            loading: true,
        });

        onWillStart(async () => {
            await this.loadStats();
        });
    }

    async loadStats() {
        try {
            let domain = [];
            if (this.props.membershipTypeId) {
                domain.push(['membership_type_id', '=', this.props.membershipTypeId]);
            }
            if (this.props.partnerId) {
                domain.push(['partner_id', '=', this.props.partnerId]);
            }

            // Get total memberships count
            const totalMembers = await this.orm.searchCount("membership.membership", domain);

            // Get active memberships count
            const activeMembers = await this.orm.searchCount("membership.membership", [
                ...domain,
                ['state', 'in', ['active', 'grace']]
            ]);

            // Get expiring memberships (next 30 days)
            const today = new Date();
            const thirtyDaysFromNow = new Date(today.getTime() + (30 * 24 * 60 * 60 * 1000));
            const expiringMembers = await this.orm.searchCount("membership.membership", [
                ...domain,
                ['state', 'in', ['active', 'grace']],
                ['end_date', '>=', today.toISOString().split('T')[0]],
                ['end_date', '<=', thirtyDaysFromNow.toISOString().split('T')[0]]
            ]);

            // Get revenue information
            const memberships = await this.orm.searchRead("membership.membership", domain, ['amount_paid']);
            const totalRevenue = memberships.reduce((sum, membership) => sum + membership.amount_paid, 0);

            // Get new memberships this month
            const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            const newThisMonth = await this.orm.searchCount("membership.membership", [
                ...domain,
                ['start_date', '>=', firstDayOfMonth.toISOString().split('T')[0]]
            ]);

            this.state.stats = {
                totalMembers,
                activeMembers,
                expiringMembers,
                totalRevenue,
                newThisMonth,
                renewalRate: totalMembers > 0 ? Math.round((activeMembers / totalMembers) * 100) : 0,
            };
        } catch (error) {
            console.error('Error loading membership stats:', error);
        } finally {
            this.state.loading = false;
        }
    }

    formatCurrency(amount) {
        return formatCurrency(amount);
    }
}

/**
 * Membership Quick Actions Component
 * Provides quick action buttons for membership management
 */
export class MembershipQuickActions extends Component {
    static template = "membership_core.MembershipQuickActions";
    static props = {
        membershipId: { type: Number },
        state: { type: String },
        canActivate: { type: Boolean, optional: true },
        canRenew: { type: Boolean, optional: true },
        canSuspend: { type: Boolean, optional: true },
        canTerminate: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
    }

    async activateMembership() {
        try {
            await this.orm.call("membership.membership", "action_activate", [this.props.membershipId]);
            this.notification.add("Membership activated successfully", { type: "success" });
            this.reloadView();
        } catch (error) {
            this.notification.add("Error activating membership: " + error.message, { type: "danger" });
        }
    }

    async renewMembership() {
        try {
            await this.action.doAction({
                type: 'ir.actions.act_window',
                name: 'Renew Membership',
                res_model: 'membership.renewal.wizard',
                view_mode: 'form',
                target: 'new',
                context: {
                    default_membership_id: this.props.membershipId,
                },
            });
        } catch (error) {
            this.notification.add("Error opening renewal wizard: " + error.message, { type: "danger" });
        }
    }

    async suspendMembership() {
        const reason = prompt("Enter reason for suspension (optional):");
        if (reason === null) return; // User cancelled

        try {
            await this.orm.call("membership.membership", "action_suspend", [this.props.membershipId], {
                reason: reason || "Manual suspension"
            });
            this.notification.add("Membership suspended successfully", { type: "success" });
            this.reloadView();
        } catch (error) {
            this.notification.add("Error suspending membership: " + error.message, { type: "danger" });
        }
    }

    async terminateMembership() {
        if (!confirm("Are you sure you want to terminate this membership? This action cannot be undone.")) {
            return;
        }

        const reason = prompt("Enter reason for termination:");
        if (reason === null) return; // User cancelled

        try {
            await this.orm.call("membership.membership", "action_terminate", [this.props.membershipId], {
                reason: reason || "Manual termination"
            });
            this.notification.add("Membership terminated successfully", { type: "success" });
            this.reloadView();
        } catch (error) {
            this.notification.add("Error terminating membership: " + error.message, { type: "danger" });
        }
    }

    reloadView() {
        // Trigger a reload of the current view
        window.location.reload();
    }
}

// Register components with field registry
registry.category("fields").add("membership_status", MembershipStatusWidget);
registry.category("fields").add("membership_expiry", MembershipExpiryWidget);

// Define templates as a single template string
import { xml } from "@odoo/owl";

// Register templates
registry.category("web.templates").add("membership_core.templates", xml`
<templates>
    <t t-name="membership_core.MembershipStatusWidget" owl="1">
        <span t-att-class="statusClass" t-esc="statusText"/>
    </t>

    <t t-name="membership_core.MembershipExpiryWidget" owl="1">
        <div t-if="props.endDate" t-att-class="'membership_expiry_indicator ' + warningClass">
            <i t-att-class="'fa ' + warningIcon"/>
            <span t-esc="warningText"/>
        </div>
        <div t-else="" class="membership_expiry_good">
            <i class="fa fa-infinity"/>
            <span>Lifetime Membership</span>
        </div>
    </t>

    <t t-name="membership_core.MembershipStatsDashboard" owl="1">
        <div class="membership_stats_dashboard">
            <div t-if="state.loading" class="membership_loading">
                <i class="fa fa-spinner fa-spin"/>
                <p>Loading statistics...</p>
            </div>
            <div t-else="" class="row">
                <div class="col-md-4">
                    <div class="member_stats_card count">
                        <span class="stats_number" t-esc="state.stats.totalMembers"/>
                        <span class="stats_label">Total Members</span>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="member_stats_card count">
                        <span class="stats_number" t-esc="state.stats.activeMembers"/>
                        <span class="stats_label">Active Members</span>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="member_stats_card expiring">
                        <span class="stats_number" t-esc="state.stats.expiringMembers"/>
                        <span class="stats_label">Expiring Soon</span>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="member_stats_card revenue">
                        <span class="stats_number" t-esc="formatCurrency(state.stats.totalRevenue)"/>
                        <span class="stats_label">Total Revenue</span>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="member_stats_card count">
                        <span class="stats_number" t-esc="state.stats.newThisMonth"/>
                        <span class="stats_label">New This Month</span>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="member_stats_card count">
                        <span class="stats_number" t-esc="state.stats.renewalRate + '%'"/>
                        <span class="stats_label">Renewal Rate</span>
                    </div>
                </div>
            </div>
        </div>
    </t>

    <t t-name="membership_core.MembershipQuickActions" owl="1">
        <div class="membership_quick_actions">
            <button t-if="props.state === 'draft' and props.canActivate" 
                    class="btn btn-primary btn-sm" 
                    t-on-click="activateMembership">
                <i class="fa fa-play"/> Activate
            </button>
            <button t-if="props.state in ['active', 'grace'] and props.canRenew" 
                    class="btn btn-success btn-sm" 
                    t-on-click="renewMembership">
                <i class="fa fa-refresh"/> Renew
            </button>
            <button t-if="props.state in ['active', 'grace'] and props.canSuspend" 
                    class="btn btn-warning btn-sm" 
                    t-on-click="suspendMembership">
                <i class="fa fa-pause"/> Suspend
            </button>
            <button t-if="props.state in ['active', 'grace', 'suspended'] and props.canTerminate" 
                    class="btn btn-danger btn-sm" 
                    t-on-click="terminateMembership">
                <i class="fa fa-stop"/> Terminate
            </button>
        </div>
    </t>
</templates>
`);