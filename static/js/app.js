// Enhanced Locus Assistant - Modern JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap components
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize modern features
    initializeEnhancements();
    updateTimestamp();
    setInterval(updateTimestamp, 1000); // Update every second

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            if (alert.classList.contains('alert-success') || alert.classList.contains('alert-info')) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        });
    }, 5000);

    // Add loading state to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<span class="loading"></span> Loading...';

                // Re-enable after 10 seconds as fallback
                setTimeout(function() {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }, 10000);
            }
        });
    });

    // Copy to clipboard functionality
    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(function() {
            showToast('Copied to clipboard!', 'success');
        }, function(err) {
            console.error('Could not copy text: ', err);
            showToast('Failed to copy', 'error');
        });
    }

    // Show toast messages
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type} position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 250px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        document.body.appendChild(toast);

        // Auto remove after 3 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 3000);
    }

    // Add copy buttons to JSON sections
    const jsonElements = document.querySelectorAll('.order-json');
    jsonElements.forEach(function(element, index) {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn btn-sm btn-outline-secondary position-absolute';
        copyBtn.style.cssText = 'top: 5px; right: 5px;';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.onclick = function() {
            copyToClipboard(element.textContent);
        };

        element.parentElement.style.position = 'relative';
        element.parentElement.appendChild(copyBtn);
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Real-time search functionality
    const searchInput = document.querySelector('#order-search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const orderCards = document.querySelectorAll('.order-card');

            orderCards.forEach(function(card) {
                const cardText = card.textContent.toLowerCase();
                if (cardText.includes(searchTerm)) {
                    card.style.display = 'block';
                    card.classList.add('animate-in');
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // Date picker enhancement
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        // Set max date to today
        const today = new Date().toISOString().split('T')[0];
        input.setAttribute('max', today);

        // Add quick date buttons
        const quickDates = document.createElement('div');
        quickDates.className = 'mt-2';
        quickDates.innerHTML = `
            <small class="text-muted d-block mb-1">Quick select:</small>
            <button type="button" class="btn btn-sm btn-outline-secondary me-1" data-date="today">Today</button>
            <button type="button" class="btn btn-sm btn-outline-secondary me-1" data-date="yesterday">Yesterday</button>
            <button type="button" class="btn btn-sm btn-outline-secondary" data-date="week">Last Week</button>
        `;

        input.parentElement.appendChild(quickDates);

        quickDates.addEventListener('click', function(e) {
            if (e.target.hasAttribute('data-date')) {
                const dateType = e.target.getAttribute('data-date');
                const date = new Date();

                switch(dateType) {
                    case 'today':
                        break;
                    case 'yesterday':
                        date.setDate(date.getDate() - 1);
                        break;
                    case 'week':
                        date.setDate(date.getDate() - 7);
                        break;
                }

                input.value = date.toISOString().split('T')[0];
                input.form.submit();
            }
        });
    });
});

// Global functions
window.refreshOrders = async function() {
    const refreshButton = document.querySelector('button[onclick="refreshOrders()"]');
    const refreshIcon = document.getElementById('refresh-icon');

    try {
        // Show loading state
        refreshButton.disabled = true;
        if (refreshIcon) {
            refreshIcon.classList.add('fa-spin');
        }
        showToast('Fetching new orders from Locus...', 'info');

        // Get current parameters from URL
        const urlParams = new URLSearchParams(window.location.search);
        const currentDate = urlParams.get('date') || new Date().toISOString().split('T')[0];
        const dateFrom = urlParams.get('date_from');
        const dateTo = urlParams.get('date_to');
        const currentOrderStatus = urlParams.get('order_status') || 'all';

        // Build request body with date range parameters
        const requestBody = {
            order_status: currentOrderStatus
        };

        // Add date parameters based on what's available
        if (dateFrom && dateTo) {
            requestBody.date_from = dateFrom;
            requestBody.date_to = dateTo;
        } else if (dateFrom) {
            requestBody.date = dateFrom;
        } else {
            requestBody.date = currentDate;
        }

        // Call refresh endpoint with current filters including date range
        // Add cache-busting parameter to prevent cached responses
        const response = await fetch(`/api/refresh-orders?_cb=${Date.now()}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
            },
            body: JSON.stringify(requestBody)
        });

        const result = await response.json();

        if (result.success) {
            const message = result.message || `✅ Refreshed! Found ${result.total_orders_count} orders`;
            showToast(message, 'success');

            // Force cache-busting reload to show updated orders
            setTimeout(() => {
                // Add multiple cache-busting parameters and force complete reload
                const currentUrl = new URL(window.location);
                currentUrl.searchParams.set('_refresh', Date.now());
                currentUrl.searchParams.set('_cb', Math.random());

                // Clear any potential cached redirects and force hard reload
                if ('caches' in window) {
                    caches.keys().then(function(names) {
                        names.forEach(function(name) {
                            caches.delete(name);
                        });
                    });
                }

                // Force complete page reload
                window.location.replace(currentUrl.toString());
            }, 1500);
        } else {
            showToast(`❌ Error: ${result.message}`, 'error');
        }

    } catch (error) {
        console.error('Error refreshing orders:', error);
        showToast('❌ Failed to refresh orders. Please try again.', 'error');
    } finally {
        // Remove loading state
        refreshButton.disabled = false;
        if (refreshIcon) {
            refreshIcon.classList.remove('fa-spin');
        }
    }
};

// Modern enhancement functions
function initializeEnhancements() {
    // Add loading states to cards
    addLoadingStates();

    // Enhanced search functionality with debouncing
    setupEnhancedSearch();

    // Intersection Observer for animations
    setupScrollAnimations();

    // Enhanced form validations
    setupFormEnhancements();
}

function updateTimestamp() {
    const timestampEl = document.getElementById('last-updated');
    if (timestampEl) {
        const now = new Date();
        timestampEl.textContent = now.toLocaleTimeString();
    }
}

function addLoadingStates() {
    // Add skeleton loading states during data operations
    document.addEventListener('click', function(e) {
        if (e.target.matches('[data-loading]') || e.target.closest('[data-loading]')) {
            const card = e.target.closest('.order-card');
            if (card) {
                card.classList.add('loading-card');
                setTimeout(() => card.classList.remove('loading-card'), 2000);
            }
        }
    });
}

function setupEnhancedSearch() {
    const searchInput = document.getElementById('orderSearch');
    if (!searchInput) return;

    let searchTimeout;

    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performSearch(this.value);
        }, 300); // Debounce for 300ms
    });
}

function performSearch(searchTerm) {
    const searchValue = searchTerm.toLowerCase().trim();
    const orderCards = document.querySelectorAll('.order-card');
    let visibleCount = 0;

    orderCards.forEach((card, index) => {
        const cardText = card.textContent.toLowerCase();
        const shouldShow = searchValue === '' || cardText.includes(searchValue);

        if (shouldShow) {
            card.style.display = 'block';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });

    // Update search results count
    updateSearchResults(visibleCount, orderCards.length, searchValue);
}

function updateSearchResults(visible, total, searchTerm) {
    let resultIndicator = document.querySelector('.search-results-indicator');

    if (searchTerm && visible < total) {
        if (!resultIndicator) {
            resultIndicator = document.createElement('div');
            resultIndicator.className = 'alert alert-info search-results-indicator mt-3';
            const filtersContainer = document.querySelector('.search-filters-container');
            if (filtersContainer) {
                filtersContainer.appendChild(resultIndicator);
            }
        }

        resultIndicator.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <span>
                    <i class="fas fa-search me-2"></i>
                    Found <strong>${visible}</strong> of <strong>${total}</strong> orders
                </span>
                <button class="btn btn-sm btn-outline-info" onclick="clearAllFilters()">
                    <i class="fas fa-times"></i> Clear
                </button>
            </div>
        `;
    } else if (resultIndicator) {
        resultIndicator.remove();
    }
}

function setupScrollAnimations() {
    // Disabled scroll animations to prevent refresh-like behavior
    // Order cards will use their initial CSS animations only
}

function setupFormEnhancements() {
    // Enhanced form field focus states
    document.querySelectorAll('.form-control, .form-select').forEach(field => {
        field.addEventListener('focus', function() {
            this.classList.add('focus-ring');
        });

        field.addEventListener('blur', function() {
            this.classList.remove('focus-ring');
        });
    });
}

// Enhanced global functions
window.clearAllFilters = function() {
    const searchInput = document.getElementById('orderSearch');
    const issueFilter = document.getElementById('issueFilter');

    if (searchInput) searchInput.value = '';
    if (issueFilter) issueFilter.value = 'all';

    performSearch('');
    if (window.filterByIssues) filterByIssues();

    // Remove result indicator
    const resultIndicator = document.querySelector('.search-results-indicator');
    if (resultIndicator) resultIndicator.remove();
};

// Removed duplicate refreshOrders function - using the async version above that calls the API

// Enhanced toast system
function showToast(message, type = 'info', duration = 4000) {
    // Remove existing toasts
    document.querySelectorAll('.toast-notification').forEach(toast => toast.remove());

    const toast = document.createElement('div');
    toast.className = `toast-notification alert alert-${type === 'error' ? 'danger' : type} position-fixed`;
    toast.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 500px;
        box-shadow: var(--shadow-lg);
        border: none;
        animation: slideInRight 0.3s ease-out;
    `;

    const icon = {
        'success': 'fas fa-check-circle',
        'error': 'fas fa-exclamation-circle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle'
    }[type] || 'fas fa-info-circle';

    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="${icon} me-3"></i>
            <span>${message}</span>
            <button type="button" class="btn-close ms-auto" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;

    document.body.appendChild(toast);

    // Auto remove
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

// Add CSS animations for toasts
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }

    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }

    .loading {
        cursor: wait;
    }

    .animate-in {
        animation: slideInUp 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }
`;
document.head.appendChild(style);