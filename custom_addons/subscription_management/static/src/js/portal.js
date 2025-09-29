/* Subscription Management Portal JavaScript */

(function() {
    'use strict';

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        initSubscriptionPortal();
    });

    /**
     * Initialize subscription portal features
     */
    function initSubscriptionPortal() {
        initUsageMeters();
        initSubscriptionActions();
        initPlanComparison();
        initTooltips();
    }

    /**
     * Initialize usage meters with animations
     */
    function initUsageMeters() {
        const usageMeters = document.querySelectorAll('.usage-progress-fill');
        
        usageMeters.forEach(function(meter) {
            const percentage = meter.getAttribute('data-percentage') || 0;
            const currentWidth = parseFloat(percentage);
            
            // Animate the progress bar
            setTimeout(function() {
                meter.style.width = currentWidth + '%';
                
                // Change color based on usage
                if (currentWidth >= 100) {
                    meter.classList.add('danger');
                } else if (currentWidth >= 80) {
                    meter.classList.add('warning');
                }
            }, 300);
        });
    }

    /**
     * Initialize subscription action buttons
     */
    function initSubscriptionActions() {
        // Confirm before cancellation
        const cancelButtons = document.querySelectorAll('[data-action="cancel"]');
        cancelButtons.forEach(function(button) {
            button.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to cancel your subscription?')) {
                    e.preventDefault();
                    return false;
                }
            });
        });

        // Confirm before suspension
        const suspendButtons = document.querySelectorAll('[data-action="suspend"]');
        suspendButtons.forEach(function(button) {
            button.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to suspend your subscription?')) {
                    e.preventDefault();
                    return false;
                }
            });
        });

        // Handle plan changes
        const changePlanButtons = document.querySelectorAll('[data-action="change-plan"]');
        changePlanButtons.forEach(function(button) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                showPlanSelector();
            });
        });
    }

    /**
     * Initialize plan comparison features
     */
    function initPlanComparison() {
        const planCards = document.querySelectorAll('.plan-selection-card');
        
        planCards.forEach(function(card) {
            card.addEventListener('mouseenter', function() {
                this.classList.add('highlighted');
            });
            
            card.addEventListener('mouseleave', function() {
                this.classList.remove('highlighted');
            });
        });

        // Plan feature comparison toggle
        const compareButton = document.getElementById('compare-plans-btn');
        if (compareButton) {
            compareButton.addEventListener('click', function() {
                togglePlanComparison();
            });
        }
    }

    /**
     * Initialize Bootstrap tooltips
     */
    function initTooltips() {
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(
                document.querySelectorAll('[data-bs-toggle="tooltip"]')
            );
            tooltipTriggerList.map(function(tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }

    /**
     * Show plan selector modal
     */
    function showPlanSelector() {
        const modal = document.getElementById('planSelectorModal');
        if (modal) {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        }
    }

    /**
     * Toggle plan comparison view
     */
    function togglePlanComparison() {
        const comparisonTable = document.getElementById('plan-comparison-table');
        if (comparisonTable) {
            comparisonTable.classList.toggle('d-none');
        }
    }

    /**
     * Format currency
     */
    function formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    }

    /**
     * Format date
     */
    function formatDate(dateString) {
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        }).format(date);
    }

    /**
     * Add usage via AJAX
     */
    window.addSubscriptionUsage = function(subscriptionId, usageType, quantity, description) {
        return fetch('/subscription/usage/' + subscriptionId, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: {
                    usage_type: usageType,
                    quantity: quantity,
                    description: description
                }
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.result && data.result.success) {
                showNotification('Usage recorded successfully', 'success');
                updateUsageDisplay(data.result);
                return data.result;
            } else {
                throw new Error(data.result.error || 'Failed to record usage');
            }
        })
        .catch(error => {
            console.error('Error recording usage:', error);
            showNotification('Error recording usage: ' + error.message, 'danger');
            throw error;
        });
    };

    /**
     * Update usage display
     */
    function updateUsageDisplay(usageData) {
        const currentUsageEl = document.getElementById('current-usage');
        const usageOverageEl = document.getElementById('usage-overage');
        const progressBar = document.querySelector('.usage-progress-fill');

        if (currentUsageEl) {
            currentUsageEl.textContent = usageData.current_usage;
        }

        if (usageOverageEl) {
            usageOverageEl.textContent = usageData.usage_overage;
            usageOverageEl.style.color = usageData.usage_overage > 0 ? 'red' : 'green';
        }

        if (progressBar && usageData.usage_limit > 0) {
            const percentage = (usageData.current_usage / usageData.usage_limit) * 100;
            progressBar.style.width = Math.min(100, percentage) + '%';
            
            progressBar.classList.remove('normal', 'warning', 'danger');
            if (percentage >= 100) {
                progressBar.classList.add('danger');
            } else if (percentage >= 80) {
                progressBar.classList.add('warning');
            } else {
                progressBar.classList.add('normal');
            }
        }
    }

    /**
     * Show notification
     */
    function showNotification(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show subscription-notification`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        const container = document.querySelector('.container') || document.body;
        container.insertBefore(alertDiv, container.firstChild);

        // Auto dismiss after 5 seconds
        setTimeout(function() {
            alertDiv.classList.remove('show');
            setTimeout(function() {
                alertDiv.remove();
            }, 150);
        }, 5000);
    }

    /**
     * Refresh subscription data
     */
    window.refreshSubscriptionData = function(subscriptionId) {
        window.location.reload();
    };

    /**
     * Handle payment method update
     */
    window.updatePaymentMethod = function(subscriptionId) {
        // Redirect to payment method update page
        window.location.href = '/my/payment_method?subscription_id=' + subscriptionId;
    };

    /**
     * Export functions for external use
     */
    window.SubscriptionPortal = {
        addUsage: window.addSubscriptionUsage,
        refresh: window.refreshSubscriptionData,
        updatePaymentMethod: window.updatePaymentMethod,
        formatCurrency: formatCurrency,
        formatDate: formatDate,
        showNotification: showNotification
    };

})();