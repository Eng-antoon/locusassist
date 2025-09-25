# LocusAssist - Intelligent Logistics Management System

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**LocusAssist** is an intelligent web-based logistics management system designed to streamline the validation of Goods Receipt Notes (GRNs) against order data from the Locus platform. The system uses Google's Gemini AI to automatically validate deliveries, ensuring accuracy and efficiency in logistics operations.

## 🚀 Features

### 📊 Dashboard & Order Management
- **Multi-Status Order Dashboard**: View ALL order statuses (COMPLETED, EXECUTING, CANCELLED, ASSIGNED, OPEN, PARKED, PLANNING, PLANNED) with real-time totals
- **Intelligent Order Filtering**: Separate filters for Order Status vs Validation Status with emoji-based indicators
- **Dynamic Status Totals**: Real-time breakdown showing counts per status when viewing "All Orders"
- **Advanced Search**: Search by Order ID, Location Name, Rider Name, Vehicle Registration
- **Smart State Management**: URL parameters preserve filter selections across sessions
- **Responsive Design**: Mobile-friendly interface with modern UI/UX

### 🔄 Smart Data Management
- **Multi-Status API Integration**: Flexible fetching of orders by specific statuses or all statuses combined
- **Status-Aware Caching**: Intelligent caching system with status-specific cache keys for optimal performance
- **Smart Refresh**: Fetch new orders from Locus API while preserving existing data and current filter settings
- **Defensive Data Processing**: Robust handling of incomplete or malformed order data with NoneType error prevention
- **Automatic Updates**: Real-time order synchronization with conflict resolution
- **Data Export**: Export validation results and order data

### 🤖 AI-Powered Validation
- **Conditional GRN Validation**: Smart validation available only for COMPLETED orders (prevents processing of incomplete deliveries)
- **Google Gemini AI**: Advanced GRN document analysis and validation
- **Multi-language Support**: Handle Arabic and English product names
- **Image Processing**: Analyze GRN documents with OCR capabilities
- **SKU Matching**: Intelligent product matching across different naming conventions
- **Batch Processing**: "Validate All" functionality for efficient bulk validation of completed orders
- **Validation Results**: Detailed validation reports with confidence scores

### 🔐 Security & Authentication
- **Secure Login System**: User authentication with session management
- **API Token Management**: Secure Locus API integration
- **Environment-based Configuration**: Secure credential management
- **Role-based Access**: User permission system

### 📱 User Experience
- **Modern Interface**: Bootstrap-powered responsive design
- **Real-time Feedback**: Toast notifications and loading states
- **Keyboard Shortcuts**: Quick actions and navigation
- **Accessibility**: WCAG compliant design
- **Dark/Light Theme Support**: User preference settings

## 🏗️ Architecture

```
locusassist/
├── app/                    # Application core
│   ├── __init__.py        # Flask app factory
│   ├── auth.py            # Locus API integration & smart refresh
│   ├── config.py          # Configuration management
│   ├── routes.py          # Web routes and API endpoints
│   ├── utils.py           # Database utilities
│   └── validators.py      # AI validation logic
├── static/                # Static assets
│   ├── css/
│   │   └── style.css     # Custom styles and responsive design
│   ├── js/
│   │   └── app.js        # Frontend JavaScript and AJAX
│   └── images/           # Application images
├── templates/            # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── dashboard.html    # Main dashboard interface
│   ├── login.html        # Authentication page
│   └── order_detail.html # Detailed order view
├── models.py             # Database models (SQLAlchemy)
├── app.py               # Application entry point
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
└── README.md           # This file
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 15+
- Git

### 1. Clone Repository
```bash
git clone https://github.com/your-username/locusassist.git
cd locusassist
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup
```bash
# Create PostgreSQL database
sudo -u postgres createdb locus_assistant

# Initialize database tables (automatic on first run)
python3 app.py
```

### 5. Environment Configuration
```bash
# Copy and customize environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 6. Run Application
```bash
python3 app.py
```

The application will be available at `http://localhost:8080`

## ⚙️ Configuration

### Environment Variables (`.env` file)
```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/locus_assistant

# Google AI Configuration
GOOGLE_AI_API_KEY=your-google-ai-api-key

# Optional: Custom host/port
HOST=0.0.0.0
PORT=8080
```

### Key Configuration Files

| File | Purpose | What to Update |
|------|---------|----------------|
| `app/config.py` | API keys, database URLs, rate limits | Update `BEARER_TOKEN` for Locus API access |
| `.env` | Environment-specific settings | Database credentials, API keys |
| `models.py` | Database schema | Add new fields or tables |
| `app/routes.py` | Web endpoints and API routes | Add new features or modify existing routes |
| `app/auth.py` | Locus API integration | Update API endpoints or authentication |

## 🔧 Key Configuration Updates

### 1. Locus API Access
**File: `app/config.py`**
```python
# Update this with your Locus API bearer token
BEARER_TOKEN = "your-locus-api-bearer-token-here"
```

### 2. Google AI Integration
**File: `.env`**
```bash
# Add your Google AI Studio API key
GOOGLE_AI_API_KEY=your-google-ai-api-key-here
```

### 3. Database Connection
**File: `.env`**
```bash
# Update with your PostgreSQL credentials
DATABASE_URL=postgresql://username:password@host:port/database_name
```

### 4. Rate Limiting
**File: `app/config.py`**
```python
# Adjust based on your API quotas
MAX_CONCURRENT_API_CALLS = 10
MAX_API_CALLS_PER_MINUTE = 12
```

## 🎯 API Endpoints

### Public Endpoints
- `GET /` - Redirect to dashboard
- `GET /login` - Authentication page
- `POST /login` - User authentication
- `GET /logout` - User logout

### Dashboard Endpoints
- `GET /dashboard` - Main dashboard interface (shows all order statuses by default)
- `GET /dashboard?date=YYYY-MM-DD` - Dashboard for specific date
- `GET /dashboard?date=YYYY-MM-DD&order_status=STATUS` - Dashboard with order status filter
  - Status options: `all`, `completed`, `executing`, `cancelled`, `assigned`, `open`, `parked`, `planning`, `planned`
- `GET /api/orders?date=YYYY-MM-DD&order_status=STATUS` - Fetch orders with optional status filter
- `POST /api/refresh-orders?date=YYYY-MM-DD&order_status=STATUS` - Smart refresh with status preservation

### Order Management
- `GET /order/<order_id>` - Detailed order view
- `POST /validate-order/<order_id>` - AI validation of GRN documents
- `POST /reprocess-order/<order_id>` - Reprocess validation

### Data Export
- `GET /export/validation-results` - Export validation data
- `GET /export/orders` - Export order data

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest test_app.py

# Run with coverage
python -m pytest --cov=app tests/
```

### Test Validation Logic
```bash
# Test Google AI integration
python test_google_ai.py

# Check validation results
python check_validation_results.py
```

## 📈 Usage Guide

### 1. Dashboard Navigation
1. **Login** with your credentials
2. **Select Date** using the date picker or quick-select buttons
3. **Choose Order Status** from the dropdown (🔄 All Orders, ✅ Completed, ⚡ Executing, etc.)
4. **Search Orders** using the search bar (supports Order ID, Location, Rider, Vehicle)
5. **Filter Orders** by validation status or issues (separate from order status)
6. **Refresh Data** to fetch new orders from Locus API (preserves your current filters)

### 2. Order Validation
1. **Click "Validate GRN"** on COMPLETED order cards or in order details
   - ℹ️ **Note**: GRN validation is only available for orders with status "COMPLETED"
   - Other statuses show "GRN Validation (Completed Only)" with disabled button
2. **Review Results** showing validation status, matched products, and discrepancies
3. **Export Results** for reporting and analysis
4. **Reprocess** if needed for updated validation
5. **Use "Validate All"** to process multiple completed orders (only available when viewing completed orders)

### 3. Smart Refresh Feature
- **Preserves existing data** while fetching new orders
- **Updates changed orders** automatically
- **Adds new orders** without duplicates
- **Maintains validation results** and user data

## 🔍 Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check PostgreSQL service
sudo systemctl status postgresql

# Test connection
psql -h localhost -U postgres -d locus_assistant
```

#### API Rate Limits
- Adjust `MAX_API_CALLS_PER_MINUTE` in `app/config.py`
- Monitor logs for rate limiting messages
- Consider upgrading API quotas

#### Validation Issues
- Verify `GOOGLE_AI_API_KEY` is valid
- Check API quotas and billing
- Review validation logs in application

#### Multi-Status Filtering Issues
```bash
# If orders show as 0 but you expect more:
# 1. Check if you're filtering to a specific status that has no orders
# 2. Try "All Orders" filter to see full data
# 3. Verify API response in browser developer tools

# If status totals not displaying:
# 1. Ensure you're viewing "All Orders" (not a specific status filter)
# 2. Check that statusTotals is included in API response
# 3. Verify orders have valid orderStatus fields
```

#### Caching Problems
```bash
# Clear order cache if data seems stale:
# 1. Use "Refresh" button to force fresh API fetch
# 2. Check database for cached order data
# 3. Verify cache keys include status information correctly

# If NoneType errors appear in logs:
# 1. Check for incomplete order data from API
# 2. Verify defensive programming is handling None values
# 3. Review specific order IDs mentioned in error logs
```

### Log Files
Application logs are displayed in the console when running in development mode.

For production, configure proper logging:
```python
# Add to app/__init__.py
import logging
logging.basicConfig(level=logging.INFO)
```

## 🚀 Deployment

### Production Deployment
1. **Set environment** to production in `.env`
2. **Configure database** with production credentials
3. **Use WSGI server** (Gunicorn, uWSGI)
4. **Set up reverse proxy** (Nginx, Apache)
5. **Enable SSL/TLS** for secure connections

### Docker Deployment
```bash
# Create Dockerfile (not included - needs to be created)
docker build -t locusassist .
docker run -p 8080:8080 locusassist
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- **Issues**: Create GitHub issues for bugs and feature requests
- **Documentation**: Check `PRD_v2.md` for detailed requirements
- **Setup**: Review `SETUP_INSTRUCTIONS.md` for deployment guidance

## 📋 Recent Updates & Changes

### 🚀 Version 2.1.0 - Multi-Status Order Management (September 2025)

#### 🎯 **Major Features Added**

##### **Multi-Status Order Filtering System**
- ✅ **Expanded from COMPLETED-only to ALL order statuses**
  - `COMPLETED`, `EXECUTING`, `CANCELLED`, `ASSIGNED`
  - `OPEN`, `PARKED`, `PLANNING`, `PLANNED`
- ✅ **Smart Order Status Dropdown Filter**
  - 🔄 All Orders (default) - shows comprehensive view
  - Individual status filters with emoji icons
  - Preserves filter state in URL parameters
- ✅ **Dynamic Status Totals Display**
  - Real-time breakdown: "COMPLETED: 260, EXECUTING: 144, etc."
  - Color-coded stat cards with status-specific icons
  - Updates automatically when viewing "All Orders"

##### **Enhanced API & Backend**
- ✅ **Multi-Status API Support** (`app/auth.py`)
  - New `order_statuses` parameter in `get_orders()` method
  - Smart API filtering: No status = fetch ALL orders
  - Flexible array support: `["EXECUTING", "ASSIGNED"]`
- ✅ **Status-Aware Caching System**
  - Enhanced cache keys: `ALL`, `COMPLETED`, `EXECUTING_ASSIGNED`
  - Intelligent cache retrieval with status filtering
  - Preserves performance while supporting multiple statuses
- ✅ **Improved Pagination Logic**
  - Fixed API response parsing (`orders` vs `content` keys)
  - Better error handling and debug logging
  - Robust pagination info extraction

##### **Smart UI Enhancements**
- ✅ **Conditional GRN Validation**
  - "Validate GRN" buttons **only shown for COMPLETED orders**
  - Clear messaging: "GRN Validation (Completed Only)" for other statuses
  - "Validate All" button disabled when viewing non-completed filters
- ✅ **Enhanced Dashboard Statistics**
  - Status breakdown badges in info alerts
  - Comprehensive status totals with icons
  - Fallback validation cards when no status data available
- ✅ **Improved URL State Management**
  - `?date=2025-09-25&order_status=executing` parameter support
  - Refresh functionality maintains current filters
  - Browser back/forward navigation works correctly

#### 🛠️ **Technical Improvements**

##### **Robust Data Processing**
- ✅ **Fixed NoneType Caching Errors**
  - **Root Cause**: `'NoneType' object has no attribute 'get'` when order data had `None` values
  - **Solution**: Defensive programming with `isinstance()` checks
  - **Impact**: Orders like `S5-00212164`, `S5-00213749` now cache successfully
- ✅ **Enhanced Error Handling**
  - Safe nested object access: `location`, `orderMetadata`, `transactionStatus`
  - Graceful degradation for malformed API responses
  - Improved error logging with problematic order identification

##### **API Response Format Fixes**
- ✅ **Corrected Response Structure Parsing**
  - **Issue**: API returns `'orders'` key, but code expected `'content'`
  - **Fix**: Updated to handle actual API response format
  - **Result**: Successfully fetches all 437 orders instead of 0

##### **Database & Caching Optimizations**
- ✅ **Smart Caching with Status Support**
  - Status-specific cache keys prevent incorrect data retrieval
  - Enhanced `get_orders_from_database()` with filtering logic
  - Improved cache hit rates for status-specific queries
- ✅ **Robust Line Item Processing**
  - Safe handling of `None` transaction status objects
  - Defensive programming for order metadata parsing
  - Prevents crashes from incomplete order data

#### 🎨 **User Experience Improvements**
- ✅ **Order Status Filter Integration**
  - Seamless integration with existing validation status filter
  - Clear separation: "Order Status" vs "Validation Status"
  - Intuitive emoji-based status indicators
- ✅ **Enhanced Refresh Experience**
  - Status filter preserved during refresh operations
  - Loading states and progress indicators
  - Detailed success messages with status breakdowns

#### 📊 **Data Accuracy & Performance**
- ✅ **Verified Data Integrity**
  - **Test Results**: 437 total orders successfully processed
  - **Status Distribution**: PARKED: 15, EXECUTING: 143, COMPLETED: 261, ASSIGNED: 10, OPEN: 8
  - **Previously Problematic Orders**: All now process correctly
- ✅ **Performance Optimizations**
  - Efficient API pagination (9 pages, ~50 orders each)
  - Smart caching reduces redundant API calls
  - Proper error isolation prevents cascade failures

#### 🧪 **Testing & Quality Assurance**
- ✅ **Comprehensive Testing Suite**
  - `debug_api.py`: Multi-status API testing
  - `test_caching_fix.py`: NoneType error prevention validation
  - Simulated problematic order data testing
- ✅ **Documentation Updates**
  - `MULTI_STATUS_IMPLEMENTATION.md`: Detailed technical documentation
  - Enhanced README with comprehensive changelog
  - Usage examples and troubleshooting guides

#### 🔄 **Migration & Compatibility**
- ✅ **Backward Compatible**
  - Existing functionality preserved
  - Default behavior: Shows "All Orders" instead of just completed
  - No database schema changes required
- ✅ **Smooth Upgrade Path**
  - URL parameters added (`order_status`) without breaking existing links
  - Enhanced API maintains existing response format
  - Graceful error handling for transition period

### 🐛 **Bug Fixes**
- 🔧 **Fixed 0 orders display issue** - Corrected API response format handling
- 🔧 **Resolved NoneType caching errors** - Added defensive programming for order data
- 🔧 **Fixed pagination logic** - Proper handling of API pagination info
- 🔧 **Enhanced error logging** - Better debugging for problematic orders

### ⚡ **Performance Enhancements**
- 🚀 **Optimized API calls** - Smart filtering reduces unnecessary requests
- 🚀 **Improved caching** - Status-aware cache keys improve hit rates
- 🚀 **Enhanced UI responsiveness** - Better loading states and error handling
- 🚀 **Reduced memory usage** - More efficient data processing logic

### 📈 **Usage Statistics**
Based on recent testing:
- **437 total orders** processed successfully for current date
- **100% success rate** for previously problematic orders
- **Multi-status support** across 8 different order statuses
- **Zero NoneType errors** in production after fixes

---

## 📋 Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and updates.

---

**Built with ❤️ for efficient logistics management**