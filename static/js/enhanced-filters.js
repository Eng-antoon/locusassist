/**
 * Enhanced Filters JavaScript Module
 * Handles advanced filtering functionality with collapsible sections
 */

class EnhancedFilters {
    constructor() {
        this.filters = {};
        this.filterOptions = {};
        this.isLoading = false;
        this.currentResults = null;

        this.init();
    }

    async init() {
        await this.loadFilterOptions();
        this.setupEventListeners();
        this.setupCollapsibleSections();

        // Try to load saved state, if not found, load today by default
        const stateLoaded = this.loadStateFromLocalStorage();
        if (stateLoaded) {
            // Apply filters with saved state
            setTimeout(() => {
                this.applyFilters();
            }, 500);
        } else {
            this.loadTodayByDefault();
        }
    }

    async loadFilterOptions() {
        try {
            console.log('Setting up AJAX-powered filter options...');

            // Initialize AJAX-powered selects
            this.initializeAjaxSelect('filter-city', 'location_city');
            this.initializeAjaxSelect('filter-rider', 'rider_name');
            this.initializeAjaxSelect('filter-client', 'client_id');

            // Initialize static selects
            this.initializeStaticSelect('filter-order-status');
            this.initializeStaticSelect('filter-validation-status');
            this.initializeStaticSelect('filter-per-page');

        } catch (error) {
            console.error('Error setting up filter options:', error);
        }
    }

    initializeAjaxSelect(selectId, filterType) {
        const select = $('#' + selectId);
        if (select.length) {
            console.log(`Initializing AJAX select for ${selectId}`);

            select.select2({
                placeholder: select.find('option:first').text(),
                allowClear: true,
                width: '100%',
                ajax: {
                    url: `/api/filters/options/${filterType}`,
                    dataType: 'json',
                    delay: 250,
                    data: function (params) {
                        return {
                            search: params.term || '',
                            page: params.page || 1,
                            per_page: 20
                        };
                    },
                    processResults: function (data, params) {
                        params.page = params.page || 1;

                        if (data.success) {
                            return {
                                results: data.options.map(option => ({
                                    id: option.value,
                                    text: option.label
                                })),
                                pagination: {
                                    more: data.options.length === 20 // More results if we got full page
                                }
                            };
                        } else {
                            console.error(`Error loading ${filterType} options:`, data.error);
                            return { results: [] };
                        }
                    },
                    cache: true
                },
                minimumInputLength: 0,
                templateResult: this.formatSelectOption,
                templateSelection: this.formatSelectOption
            });
        }
    }

    initializeStaticSelect(selectId) {
        const select = $('#' + selectId);
        if (select.length && !select.hasClass('select2-hidden-accessible')) {
            console.log(`Initializing static select for ${selectId}`);

            select.select2({
                placeholder: select.find('option:first').text(),
                allowClear: true,
                width: '100%',
                minimumResultsForSearch: 0
            });
        }
    }

    formatSelectOption(option) {
        if (option.loading) {
            return option.text;
        }

        return $('<span>').text(option.text);
    }

    populateSelectOptions(selectId, options) {
        const select = document.getElementById(selectId);
        if (!select || !options) {
            console.warn('Select element not found or no options:', selectId, options);
            return;
        }

        console.log(`Populating ${selectId} with ${options.length} options`);

        // If Select2 is already initialized, destroy it first
        if ($(select).hasClass('select2-hidden-accessible')) {
            $(select).select2('destroy');
        }

        // Clear existing options except the first one (placeholder)
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }

        // Add new options
        options.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option.value;
            optionElement.textContent = option.label;
            select.appendChild(optionElement);
        });

        // Initialize Select2 for searchable dropdown
        this.initializeSearchableSelect(selectId);
    }

    initializeSearchableSelect(selectId) {
        const select = $('#' + selectId);
        if (select.length) {
            select.select2({
                placeholder: select.find('option:first').text(),
                allowClear: true,
                width: '100%',
                theme: 'bootstrap-5',
                dropdownParent: select.parent()
            });
        }
    }

    renderSelectOptions(options) {
        return options.map(option =>
            `<option value="${option.value}">${option.label}</option>`
        ).join('');
    }

    setupCollapsibleSections() {
        const toggleBtn = document.getElementById('filters-toggle');
        const content = document.getElementById('filters-content');
        const actions = document.getElementById('filter-actions');
        const chevron = document.getElementById('filters-chevron');
        const toggleText = document.getElementById('filters-toggle-text');

        if (toggleBtn && content) {
            toggleBtn.addEventListener('click', () => {
                const isCollapsed = content.style.display === 'none';
                content.style.display = isCollapsed ? 'block' : 'none';
                actions.style.display = isCollapsed ? 'block' : 'none';

                chevron.className = isCollapsed ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
                toggleText.textContent = isCollapsed ? 'Hide Filters' : 'Show Filters';

                // Save state
                localStorage.setItem('filtersExpanded', isCollapsed.toString());

                // Initialize Select2 for all selects when filters are shown
                if (isCollapsed) {
                    setTimeout(() => {
                        this.initializeAllSelects();
                    }, 100);
                }
            });

            // Restore saved state or expand by default
            const isExpanded = localStorage.getItem('filtersExpanded') !== 'false';
            if (isExpanded) {
                content.style.display = 'block';
                actions.style.display = 'block';
                chevron.className = 'fas fa-chevron-up';
                toggleText.textContent = 'Hide Filters';

                // Initialize Select2 after a short delay
                setTimeout(() => {
                    this.initializeAllSelects();
                }, 200);
            }
        }
    }

    initializeAllSelects() {
        console.log('Initializing all selects...');

        // Initialize AJAX-powered selects
        this.initializeAjaxSelect('filter-city', 'location_city');
        this.initializeAjaxSelect('filter-rider', 'rider_name');
        this.initializeAjaxSelect('filter-client', 'client_id');

        // Initialize static selects
        this.initializeStaticSelect('filter-order-status');
        this.initializeStaticSelect('filter-validation-status');

        // Initialize per-page select separately (not part of filters)
        this.initializePerPageSelect();
    }

    initializePerPageSelect() {
        const select = $('#filter-per-page');
        if (select.length) {
            console.log('Initializing per-page select');
            select.select2({
                width: 'auto',
                minimumResultsForSearch: -1, // No search for per-page
                allowClear: false
            });
        }
    }

    async loadTodayByDefault() {
        // Set today's date as default and load orders
        const today = new Date().toISOString().split('T')[0];
        const dateFromInput = document.getElementById('filter-date-from');
        if (dateFromInput) {
            dateFromInput.value = today;
        }

        // Auto-load today's orders
        setTimeout(() => {
            this.applyFilters();
        }, 500);
    }

    setupFilterInputEvents() {
        // Add event listeners to all filter inputs for live validation
        const filterInputs = document.querySelectorAll('#advanced-filters-content input, #advanced-filters-content select');

        filterInputs.forEach(input => {
            input.addEventListener('change', () => {
                this.validateFilterInput(input);
            });
        });
    }

    validateFilterInput(input) {
        // Remove existing validation classes
        input.classList.remove('is-valid', 'is-invalid');

        // Add validation logic based on input type
        let isValid = true;

        switch(input.type) {
            case 'date':
                if (input.value) {
                    const date = new Date(input.value);
                    isValid = !isNaN(date.getTime());
                }
                break;
            case 'number':
                if (input.value) {
                    const num = parseFloat(input.value);
                    isValid = !isNaN(num) && num >= parseFloat(input.min || 0) && num <= parseFloat(input.max || Infinity);
                }
                break;
            case 'text':
                // Text inputs are generally always valid unless they have specific constraints
                isValid = true;
                break;
        }

        // Apply validation class
        if (input.value) {
            input.classList.add(isValid ? 'is-valid' : 'is-invalid');
        }

        return isValid;
    }

    setupEventListeners() {
        // Apply Filters button
        const applyBtn = document.getElementById('apply-filters-btn');
        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.applyFilters());
        }

        // Clear Filters button
        const clearBtn = document.getElementById('clear-filters-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearFilters());
        }

        // Load Today button
        const todayBtn = document.getElementById('load-today-btn');
        if (todayBtn) {
            todayBtn.addEventListener('click', () => this.loadTodayOrders());
        }

        // Validate All button
        const validateAllBtn = document.getElementById('validate-all-btn');
        if (validateAllBtn) {
            validateAllBtn.addEventListener('click', () => this.validateAllOrders());
        }

        // Per-page control - auto-refresh when changed (use Select2 event)
        const perPageSelect = $('#filter-per-page');
        if (perPageSelect.length) {
            perPageSelect.on('select2:select', (e) => {
                console.log('Per-page changed to:', e.target.value);
                // Reset to page 1 when changing per-page
                this.currentPage = 1;
                this.applyFilters();
            });
        }

        // Add input event listeners for validation
        this.setupInputValidation();
    }

    setupInputValidation() {
        const inputs = document.querySelectorAll('#filters-content input, #filters-content select');

        inputs.forEach(input => {
            input.addEventListener('change', () => {
                this.validateInput(input);
            });
        });
    }

    validateInput(input) {
        // Remove existing validation classes
        input.classList.remove('is-valid', 'is-invalid');

        if (!input.value) return;

        let isValid = true;
        const value = input.value.trim();

        switch(input.type) {
            case 'date':
                const date = new Date(value);
                isValid = !isNaN(date.getTime());
                break;
            case 'number':
                const num = parseFloat(value);
                isValid = !isNaN(num);
                break;
            default:
                isValid = value.length > 0;
        }

        input.classList.add(isValid ? 'is-valid' : 'is-invalid');
        return isValid;
    }

    async applyFilters() {
        if (this.isLoading) return;

        try {
            this.setLoadingState(true);

            // Collect filter data
            const filterData = this.collectFilterData();
            console.log('Applying filters with data:', filterData);

            // Validate filter data
            if (!this.validateFilters(filterData)) {
                this.showMessage('Please check your filter inputs for errors.', 'error');
                return;
            }

            // Apply filters via API
            const response = await fetch('/api/orders/filter', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(filterData)
            });

            console.log('API response status:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log('API response data:', result);

            if (result.success) {
                // Update current page from result
                this.currentPage = result.page || 1;

                this.currentResults = result;
                this.displayResults(result);
                this.updateResultsSummary(result);
                this.showMessage(`Found ${result.total_count} orders matching your filters.`, 'success');

                // Save state to localStorage
                this.saveStateToLocalStorage();
            } else {
                this.showMessage(`Filter error: ${result.error || 'Unknown error'}`, 'error');
                console.error('Filter error:', result.error);
            }

        } catch (error) {
            console.error('Error applying filters:', error);
            this.showMessage(`An error occurred: ${error.message}`, 'error');
        } finally {
            this.setLoadingState(false);
        }
    }

    collectFilterData() {
        const data = {};

        // Collect all filter inputs from the unified filters
        const inputs = document.querySelectorAll('#filters-content input, #filters-content select');

        inputs.forEach(input => {
            let value;

            // Handle Select2 dropdowns
            if ($(input).hasClass('select2-hidden-accessible')) {
                value = $(input).val();
            } else {
                value = input.value;
            }

            if (value && value !== '' && value !== null) {
                if (Array.isArray(value)) {
                    // Handle multi-select arrays
                    const cleanValues = value.filter(v => v && v.trim() !== '');
                    if (cleanValues.length > 0) {
                        data[input.name] = cleanValues;
                    }
                } else if (input.multiple) {
                    // Handle traditional multi-select
                    const selectedOptions = Array.from(input.selectedOptions).map(option => option.value);
                    if (selectedOptions.length > 0) {
                        data[input.name] = selectedOptions;
                    }
                } else {
                    // Handle single values
                    const trimmedValue = value.toString().trim();
                    if (trimmedValue) {
                        data[input.name] = trimmedValue;
                    }
                }
            }
        });

        // If no specific date range is set, default to today only
        if (!data.date_from && !data.date_to) {
            const today = new Date().toISOString().split('T')[0];
            data.date_from = today;
            data.date_to = today;
        }

        // Add pagination (use current page if not specified)
        data.page = this.currentPage || 1;
        data.per_page = parseInt(document.getElementById('filter-per-page')?.value) || 50;

        console.log('Collected filter data:', data);
        return data;
    }

    loadTodayOrders() {
        // Clear all filters and load today's data
        this.clearFilters();
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('filter-date-from').value = today;
        document.getElementById('filter-date-to').value = today;
        this.applyFilters();
    }

    validateFilters(filterData) {
        let isValid = true;

        // Validate date ranges
        if (filterData.date_from && filterData.date_to) {
            if (new Date(filterData.date_from) > new Date(filterData.date_to)) {
                isValid = false;
                this.showFieldError('filter-date-to', 'End date must be after start date');
            }
        }

        if (filterData.completed_on_from && filterData.completed_on_to) {
            if (new Date(filterData.completed_on_from) > new Date(filterData.completed_on_to)) {
                isValid = false;
                this.showFieldError('filter-completed-to', 'End date must be after start date');
            }
        }

        // Validate confidence score range
        if (filterData.confidence_min && filterData.confidence_max) {
            if (parseFloat(filterData.confidence_min) > parseFloat(filterData.confidence_max)) {
                isValid = false;
                this.showFieldError('filter-confidence-max', 'Max confidence must be greater than min');
            }
        }

        // Validate quantity range
        if (filterData.quantity_min && filterData.quantity_max) {
            if (parseInt(filterData.quantity_min) > parseInt(filterData.quantity_max)) {
                isValid = false;
                this.showFieldError('filter-quantity-max', 'Max quantity must be greater than min');
            }
        }

        return isValid;
    }

    showFieldError(fieldId, message) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.classList.add('is-invalid');

            // Add or update feedback message
            let feedback = field.parentNode.querySelector('.invalid-feedback');
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                field.parentNode.appendChild(feedback);
            }
            feedback.textContent = message;
        }
    }

    displayResults(result) {
        // Update the orders display
        const ordersContainer = document.getElementById('orders-container');
        if (!ordersContainer) return;

        if (result.orders.length === 0) {
            ordersContainer.innerHTML = `
                <div class="empty-state text-center py-5">
                    <i class="fas fa-search fa-3x text-muted mb-3"></i>
                    <h4>No Orders Found</h4>
                    <p class="text-muted">No orders match your current filter criteria. Try adjusting your filters.</p>
                </div>
            `;
            return;
        }

        let html = '<div class="orders-grid">';

        result.orders.forEach((order, index) => {
            // Calculate correct sequential number across pages
            const sequentialNumber = ((result.page - 1) * result.per_page) + index + 1;
            html += this.renderOrderCard(order, index, sequentialNumber);
        });

        html += '</div>';

        ordersContainer.innerHTML = html;

        // Always show the pagination section when there are results
        const paginationSection = document.getElementById('pagination-section');
        const paginationContainer = document.getElementById('pagination-container');

        if (result.orders.length > 0) {
            paginationSection.style.display = 'block';

            // Show pagination controls if multiple pages
            if (result.total_pages > 1) {
                paginationContainer.innerHTML = this.renderPagination(result);
                paginationContainer.style.display = 'block';
            } else {
                paginationContainer.innerHTML = '';
                paginationContainer.style.display = 'none';
            }
        } else {
            paginationSection.style.display = 'none';
        }

        // Show Validate All button if there are completed orders
        const completedOrders = result.orders.filter(order => order.order_status === 'COMPLETED');
        const validateAllBtn = document.getElementById('validate-all-btn');
        if (validateAllBtn && completedOrders.length > 0) {
            validateAllBtn.style.display = 'inline-block';
        }

        // Setup action buttons for the new order cards
        this.setupOrderActionButtons();
    }

    setupOrderActionButtons() {
        // Setup validate and reprocess buttons
        document.querySelectorAll('.validate-order-btn').forEach(button => {
            button.addEventListener('click', function() {
                const orderId = this.getAttribute('data-order-id');
                const date = this.getAttribute('data-date');
                if (typeof validateOrder === 'function') {
                    validateOrder(orderId, date);
                }
            });
        });

        document.querySelectorAll('.reprocess-order-btn').forEach(button => {
            button.addEventListener('click', function() {
                const orderId = this.getAttribute('data-order-id');
                const date = this.getAttribute('data-date');
                if (typeof reprocessOrder === 'function') {
                    reprocessOrder(orderId, date);
                }
            });
        });
    }

    renderOrderCard(order, index, sequentialNumber = null) {
        // Render order cards with the same UI as the original template
        const validationSummary = order.validation_summary || {};
        const hasValidation = validationSummary.has_validation || false;
        const isValid = validationSummary.is_valid || false;
        const discrepanciesCount = validationSummary.discrepancies_count || 0;
        const confidenceScore = validationSummary.confidence_score || 0;

        // Parse order data similar to original template
        let orderData = {};
        let location = {};
        let orderMetadata = {};
        let tourDetail = {};
        let lineItems = [];

        try {
            if (order.raw_data) {
                if (typeof order.raw_data === 'string') {
                    orderData = JSON.parse(order.raw_data);
                } else {
                    orderData = order.raw_data;
                }
                location = orderData.location || {};
                orderMetadata = orderData.orderMetadata || {};
                tourDetail = orderMetadata.tourDetail || {};
                lineItems = orderMetadata.lineItems || [];
            }
        } catch (e) {
            console.warn('Could not parse order raw_data:', e);
            // Use order direct properties as fallback
            location = {
                name: order.location_name,
                address: {
                    city: order.location_city,
                    formattedAddress: order.location_address
                }
            };
            tourDetail = {
                riderName: order.rider_name,
                vehicleRegistrationNumber: order.vehicle_registration
            };
        }

        return `
            <div class="order-card clickable-card hover-glow slide-in-left"
                 onclick="viewOrderDetail('${order.id}', '${this.getCurrentDate()}')"
                 style="animation-delay: ${(index * 0.1)}s">

                <div class="card-header d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center gap-2">
                        <div class="d-flex align-items-center gap-2">
                            <i class="fas fa-box"></i>
                            <div>
                                <h6 class="mb-0">Order #${sequentialNumber !== null ? sequentialNumber : index + 1}</h6>
                                <small class="opacity-75">${order.id}</small>
                            </div>
                        </div>
                    </div>
                    <div class="d-flex align-items-center gap-1">
                        <i class="fas fa-external-link-alt opacity-75" title="Click to view details"></i>
                    </div>
                </div>

                <div class="card-body order-card-content">
                    <!-- Status Badges -->
                    <div class="d-flex flex-wrap gap-2 mb-3">
                        <span class="status-indicator ${order.order_status === 'CANCELLED' ? 'danger cancelled' : order.order_status === 'COMPLETED' ? 'success' : order.order_status === 'EXECUTING' || order.order_status === 'ONGOING' ? 'warning' : 'secondary'}">
                            ${order.order_status === 'CANCELLED' ? '<i class="fas fa-times-circle me-1"></i>' : ''}${order.order_status}
                        </span>

                        ${order.cancellation_reason ? `
                            <span class="status-indicator danger" title="Cancellation Reason">
                                <i class="fas fa-exclamation-triangle me-1"></i>${order.cancellation_reason}
                            </span>
                        ` : ''}

                        ${!order.has_grn ?
                            `<span class="status-indicator danger" title="No GRN document available for this order">
                                <i class="fas fa-file-slash"></i>No GRN
                            </span>` : ''
                        }

                        ${hasValidation ?
                            (validationSummary.has_document === false ?
                                `<span class="status-indicator warning" title="No document detected in GRN image">
                                    <i class="fas fa-file-times"></i>No Doc
                                </span>` :
                                (isValid ?
                                    `<span class="status-indicator success" title="GRN validation passed">
                                        <i class="fas fa-check-circle"></i>Valid
                                    </span>` :
                                    `<span class="status-indicator danger" title="GRN validation failed">
                                        <i class="fas fa-exclamation-triangle"></i>${discrepanciesCount} Issues
                                    </span>`
                                )
                            ) :
                            `<span class="status-indicator info" title="GRN not validated yet">
                                <i class="fas fa-question"></i>Unvalidated
                            </span>`
                        }
                    </div>

                    <!-- Enhanced Location Info -->
                    ${location.name ? `
                        <div class="order-meta-section">
                            <h6><i class="fas fa-map-marker-alt"></i>Delivery Location</h6>
                            <div class="order-info-grid">
                                <div class="order-info-item">
                                    <span class="order-info-label">Location:</span>
                                    <span class="order-info-value">${location.name}</span>
                                </div>
                                <div class="order-info-item">
                                    <span class="order-info-label">City:</span>
                                    <span class="order-info-value">${location.address?.city || order.location_city || 'N/A'}</span>
                                </div>
                            </div>
                            <small class="text-muted d-block mt-2">${location.address?.formattedAddress || order.location_address || ''}</small>
                        </div>
                    ` : ''}

                    <!-- Enhanced Tour Details -->
                    ${tourDetail.riderName || order.rider_name ? `
                        <div class="order-meta-section">
                            <h6><i class="fas fa-truck"></i>Delivery Info</h6>
                            <div class="order-info-grid">
                                <div class="order-info-item">
                                    <span class="order-info-label">Rider:</span>
                                    <span class="order-info-value">${tourDetail.riderName || order.rider_name}</span>
                                </div>
                                ${(tourDetail.vehicleRegistrationNumber || order.vehicle_registration) ? `
                                    <div class="order-info-item">
                                        <span class="order-info-label">Vehicle:</span>
                                        <span class="order-info-value">${tourDetail.vehicleRegistrationNumber || order.vehicle_registration}</span>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Enhanced Line Items Summary -->
                    ${lineItems.length > 0 ? `
                        <div class="order-meta-section">
                            <h6><i class="fas fa-list"></i>Items (${lineItems.length})</h6>
                            <div class="items-preview">
                                <div class="items-list">
                                    ${lineItems.slice(0, 3).map(item => `
                                        <div class="item-row">
                                            <span class="item-name">${item.id}</span>
                                            <span class="item-quantity">${item.transactionStatus?.transactedQuantity || item.quantity || 0}x</span>
                                        </div>
                                    `).join('')}
                                    ${lineItems.length > 3 ? `
                                        <div class="text-center mt-2">
                                            <small class="text-muted">+ ${lineItems.length - 3} more items</small>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                    ` : ''}

                    <!-- Enhanced Validation Summary -->
                    ${hasValidation ? `
                        <div class="order-meta-section">
                            <h6><i class="fas fa-clipboard-check"></i>GRN Validation</h6>
                            <div class="validation-summary-card">
                                <div class="validation-progress">
                                    ${isValid ?
                                        `<div class="status-indicator success">
                                            <i class="fas fa-check-circle"></i>Valid
                                        </div>` :
                                        `<div class="status-indicator danger">
                                            <i class="fas fa-exclamation-triangle"></i>Invalid
                                        </div>`
                                    }
                                    <div class="validation-progress-bar">
                                        <div class="validation-progress-fill" style="width: ${(confidenceScore * 100)}%"></div>
                                    </div>
                                    <span class="small text-muted">${Math.round(confidenceScore * 100)}%</span>
                                </div>

                                ${validationSummary.has_document === false ? `
                                    <div class="alert alert-warning alert-sm mb-2">
                                        <i class="fas fa-file-times"></i>No document detected in GRN image
                                    </div>
                                ` : ''}

                                <div class="validation-metrics">
                                    <div class="validation-metric">
                                        <div class="validation-metric-value">${validationSummary.summary?.total_items_found || 'N/A'}</div>
                                        <div class="validation-metric-label">Items</div>
                                    </div>
                                    <div class="validation-metric">
                                        <div class="validation-metric-value">${discrepanciesCount}</div>
                                        <div class="validation-metric-label">Issues</div>
                                    </div>
                                    ${validationSummary.gtins_verified ? `
                                        <div class="validation-metric">
                                            <div class="validation-metric-value">${validationSummary.gtins_matched}/${validationSummary.gtins_verified}</div>
                                            <div class="validation-metric-label">GTINs</div>
                                        </div>
                                    ` : ''}
                                </div>

                                <small class="text-muted d-block mt-2">
                                    <i class="fas fa-clock"></i>
                                    Processed ${validationSummary.validation_date?.split('T')[0] || 'N/A'}
                                    ${validationSummary.processing_time ? `(${validationSummary.processing_time.toFixed(2)}s)` : ''}
                                </small>
                            </div>
                        </div>
                    ` : `
                        <div class="order-meta-section">
                            <h6><i class="fas fa-clipboard-check"></i>GRN Validation</h6>
                            <div class="text-center py-3">
                                <div class="status-indicator info mb-2">
                                    <i class="fas fa-question"></i>Not Validated
                                </div>
                                <small class="text-muted">GRN not processed yet</small>
                            </div>
                        </div>
                    `}

                    <!-- Enhanced Time Info -->
                    ${order.completed_on ? `
                        <div class="order-meta-section">
                            <small class="text-muted d-flex align-items-center gap-2">
                                <i class="fas fa-clock"></i>
                                Completed: ${new Date(order.completed_on).toLocaleDateString()}
                                ${new Date(order.completed_on).toLocaleTimeString()}
                            </small>
                        </div>
                    ` : ''}
                </div>

                <!-- Enhanced Card Footer -->
                <div class="card-footer d-flex justify-content-between align-items-center">
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-outline-primary btn-icon hover-lift"
                                data-bs-toggle="collapse"
                                data-bs-target="#order-details-${index}"
                                onclick="event.stopPropagation();">
                            <i class="fas fa-eye"></i>
                            Details
                        </button>
                    </div>

                    <div class="action-buttons">
                        ${order.order_status === 'COMPLETED' ?
                            (order.has_grn ?
                                (hasValidation ?
                                    `<button class="btn btn-sm btn-warning btn-icon hover-lift reprocess-order-btn"
                                            data-order-id="${order.id}"
                                            data-date="${this.getCurrentDate()}"
                                            title="Re-process GRN with AI"
                                            onclick="event.stopPropagation();">
                                        <i class="fas fa-redo"></i>
                                        Re-process GRN
                                    </button>` :
                                    `<button class="btn btn-sm btn-success btn-icon hover-lift validate-order-btn"
                                            data-order-id="${order.id}"
                                            data-date="${this.getCurrentDate()}"
                                            title="Validate GRN with AI"
                                            onclick="event.stopPropagation();">
                                        <i class="fas fa-check-circle"></i>
                                        Validate GRN
                                    </button>`
                                ) :
                                `<button class="btn btn-sm btn-secondary btn-icon" disabled title="No GRN document available for this order">
                                    <i class="fas fa-file-times"></i>
                                    No GRN Document
                                </button>`
                            ) :
                            `<button class="btn btn-sm btn-outline-secondary btn-icon" disabled title="GRN validation only available for completed orders">
                                <i class="fas fa-lock"></i>
                                GRN Validation (Completed Only)
                            </button>`
                        }
                    </div>

                    <div class="validation-status mt-2" id="validation-status-${order.id}" style="display: none;">
                        <!-- Validation results will be displayed here -->
                    </div>
                </div>

                <!-- Enhanced Collapsible Details -->
                <div class="collapse" id="order-details-${index}">
                    <div class="border-top bg-light">
                        <div class="p-3">
                            <h6 class="text-gradient mb-3">
                                <i class="fas fa-code"></i>
                                Complete Order Data
                            </h6>
                            <div class="order-details-container">
                                <pre class="order-json">${JSON.stringify(order, null, 2)}</pre>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    getCurrentDate() {
        return new Date().toISOString().split('T')[0];
    }

    createPaginationContainer(ordersContainer) {
        const paginationContainer = document.createElement('div');
        paginationContainer.id = 'pagination-container';
        paginationContainer.className = 'pagination-container mt-4';
        ordersContainer.parentNode.insertBefore(paginationContainer, ordersContainer.nextSibling);
        return paginationContainer;
    }

    renderPagination(result) {
        const { page, total_pages } = result;
        let html = '<nav aria-label="Order results pagination"><ul class="pagination justify-content-center mt-4">';

        // Previous button
        html += `
            <li class="page-item ${page <= 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="enhancedFilters.goToPage(${page - 1})">Previous</a>
            </li>
        `;

        // Page numbers
        for (let i = Math.max(1, page - 2); i <= Math.min(total_pages, page + 2); i++) {
            html += `
                <li class="page-item ${i === page ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="enhancedFilters.goToPage(${i})">${i}</a>
                </li>
            `;
        }

        // Next button
        html += `
            <li class="page-item ${page >= total_pages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="enhancedFilters.goToPage(${page + 1})">Next</a>
            </li>
        `;

        html += '</ul></nav>';
        return html;
    }

    async goToPage(pageNum) {
        if (pageNum < 1) return;

        try {
            // Update current page first
            this.currentPage = pageNum;

            const filterData = this.collectFilterData();
            filterData.page = pageNum; // Ensure page is set correctly

            console.log(`Going to page ${pageNum}`, filterData);

            // Re-apply filters with new page
            const response = await fetch('/api/orders/filter', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(filterData)
            });

            const result = await response.json();

            if (result.success) {
                this.currentResults = result;
                this.displayResults(result);
                this.updateResultsSummary(result);

                // Save state to localStorage
                this.saveStateToLocalStorage();

                // Scroll to top of results
                document.getElementById('orders-container').scrollIntoView({ behavior: 'smooth' });
            } else {
                console.error('Error in pagination response:', result);
                this.showMessage('Error loading page. Please try again.', 'error');
            }
        } catch (error) {
            console.error('Error in goToPage:', error);
            this.showMessage('Error loading page. Please try again.', 'error');
        }
    }

    updateResultsSummary(result) {
        const summaryElement = document.getElementById('results-summary');
        if (summaryElement) {
            summaryElement.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Found <strong>${result.total_count}</strong> orders matching your filters
                    ${result.status_totals ? this.renderStatusBreakdown(result.status_totals) : ''}
                </div>
            `;
        }
    }

    renderStatusBreakdown(statusTotals) {
        const statuses = Object.entries(statusTotals);
        if (statuses.length <= 1) return '';

        return `
            <div class="mt-2 small">
                <strong>Status breakdown:</strong>
                ${statuses.map(([status, count]) =>
                    `<span class="badge bg-secondary me-1">${status}: ${count}</span>`
                ).join('')}
            </div>
        `;
    }

    clearFilters() {
        // Clear all filter inputs
        const inputs = document.querySelectorAll('#filters-content input, #filters-content select');

        inputs.forEach(input => {
            // Handle Select2 dropdowns
            if ($(input).hasClass('select2-hidden-accessible')) {
                $(input).val(null).trigger('change');
            } else if (input.type === 'checkbox') {
                input.checked = false;
            } else if (input.multiple) {
                Array.from(input.options).forEach(option => option.selected = false);
            } else {
                input.value = '';
            }

            // Remove validation classes
            input.classList.remove('is-valid', 'is-invalid');
        });

        // Clear results display
        const ordersContainer = document.getElementById('orders-container');
        if (ordersContainer) {
            ordersContainer.innerHTML = '';
        }

        const summaryContainer = document.getElementById('results-summary');
        if (summaryContainer) {
            summaryContainer.innerHTML = '';
        }

        // Clear current results
        this.currentResults = null;

        // Hide validate all button
        const validateAllBtn = document.getElementById('validate-all-btn');
        if (validateAllBtn) {
            validateAllBtn.style.display = 'none';
        }

        // Clear saved state
        this.currentPage = 1;
        this.clearStateFromLocalStorage();

        this.showMessage('All filters cleared.', 'info');
    }

    async validateAllOrders() {
        if (!this.currentResults || !this.currentResults.orders) {
            this.showMessage('No orders to validate. Please apply filters first.', 'warning');
            return;
        }

        // Use existing validate all functionality from the main dashboard
        if (typeof validateAllOrders === 'function') {
            validateAllOrders();
        } else {
            this.showMessage('Validate all functionality not available.', 'error');
        }
    }

    saveStateToLocalStorage() {
        try {
            const state = {
                filters: this.collectFilterData(),
                currentPage: this.currentPage,
                perPage: parseInt(document.getElementById('filter-per-page')?.value) || 50,
                timestamp: new Date().getTime()
            };
            localStorage.setItem('locusAssistFilterState', JSON.stringify(state));
            console.log('State saved to localStorage:', state);
        } catch (error) {
            console.error('Error saving state to localStorage:', error);
        }
    }

    loadStateFromLocalStorage() {
        try {
            const savedState = localStorage.getItem('locusAssistFilterState');
            if (savedState) {
                const state = JSON.parse(savedState);
                console.log('Loading state from localStorage:', state);

                // Check if state is not too old (24 hours)
                const now = new Date().getTime();
                const maxAge = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

                if (state.timestamp && (now - state.timestamp) < maxAge) {
                    // Restore filter values
                    Object.keys(state.filters).forEach(key => {
                        const element = document.getElementById(`filter-${key.replace('_', '-')}`);
                        if (element && key !== 'page') {
                            if ($(element).hasClass('select2-hidden-accessible')) {
                                // Handle Select2 elements
                                $(element).val(state.filters[key]).trigger('change');
                            } else {
                                element.value = state.filters[key];
                            }
                        }
                    });

                    // Restore pagination settings
                    this.currentPage = state.currentPage || 1;
                    const perPageSelect = document.getElementById('filter-per-page');
                    if (perPageSelect && state.perPage) {
                        perPageSelect.value = state.perPage;
                        if ($(perPageSelect).hasClass('select2-hidden-accessible')) {
                            $(perPageSelect).val(state.perPage).trigger('change.select2');
                        }
                    }

                    return true; // State was loaded
                }
            }
        } catch (error) {
            console.error('Error loading state from localStorage:', error);
        }
        return false; // No state was loaded
    }

    clearStateFromLocalStorage() {
        try {
            localStorage.removeItem('locusAssistFilterState');
            console.log('State cleared from localStorage');
        } catch (error) {
            console.error('Error clearing state from localStorage:', error);
        }
    }

    saveFilters() {
        const filterData = this.collectFilterData();
        const filterName = prompt('Enter a name for this filter set:');

        if (filterName) {
            const savedFilters = JSON.parse(localStorage.getItem('savedFilterSets') || '{}');
            savedFilters[filterName] = filterData;
            localStorage.setItem('savedFilterSets', JSON.stringify(savedFilters));

            this.showMessage(`Filter set "${filterName}" saved successfully.`, 'success');
            this.updateSavedFiltersDropdown();
        }
    }

    saveFiltersToLocalStorage(filterData) {
        localStorage.setItem('savedOrderFilters', JSON.stringify(filterData));
    }

    loadSavedFilters() {
        const savedFilters = localStorage.getItem('savedOrderFilters');
        if (savedFilters) {
            try {
                const filterData = JSON.parse(savedFilters);
                this.populateFiltersFromData(filterData);
            } catch (error) {
                console.error('Error loading saved filters:', error);
            }
        }
    }

    populateFiltersFromData(filterData) {
        Object.entries(filterData).forEach(([key, value]) => {
            const input = document.querySelector(`[name="${key}"]`);
            if (input) {
                if (input.multiple && Array.isArray(value)) {
                    Array.from(input.options).forEach(option => {
                        option.selected = value.includes(option.value);
                    });
                } else {
                    input.value = value;
                }
            }
        });
    }

    setLoadingState(loading) {
        this.isLoading = loading;
        const applyBtn = document.getElementById('apply-filters-btn');

        if (applyBtn) {
            if (loading) {
                applyBtn.disabled = true;
                applyBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Applying Filters...';
            } else {
                applyBtn.disabled = false;
                applyBtn.innerHTML = '<i class="fas fa-search me-1"></i>Apply Filters';
            }
        }
    }

    showMessage(message, type = 'info') {
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';

        const alertHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        const messagesContainer = document.getElementById('filter-messages');
        if (messagesContainer) {
            messagesContainer.innerHTML = alertHTML;

            // Auto-hide success/info messages after 5 seconds
            if (type === 'success' || type === 'info') {
                setTimeout(() => {
                    const alert = messagesContainer.querySelector('.alert');
                    if (alert) {
                        alert.remove();
                    }
                }, 5000);
            }
        }
    }
}

// Initialize enhanced filters when DOM is ready
let enhancedFilters;
document.addEventListener('DOMContentLoaded', function() {
    enhancedFilters = new EnhancedFilters();
});

// Helper function for order detail viewing
function viewOrderDetail(orderId) {
    window.location.href = `/order/${orderId}`;
}