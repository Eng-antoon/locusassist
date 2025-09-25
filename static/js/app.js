// Locus Assistant JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

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
window.refreshOrders = function() {
    showToast('Refreshing orders...', 'info');
    location.reload();
};

// Service Worker for offline capabilities (basic)
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/js/sw.js').then(function(registration) {
        console.log('SW registered: ', registration);
    }).catch(function(registrationError) {
        console.log('SW registration failed: ', registrationError);
    });
}