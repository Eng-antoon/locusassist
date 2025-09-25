# LocusAssist - Intelligent Logistics Management System

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**LocusAssist** is an intelligent web-based logistics management system designed to streamline the validation of Goods Receipt Notes (GRNs) against order data from the Locus platform. The system uses Google's Gemini AI to automatically validate deliveries, ensuring accuracy and efficiency in logistics operations.

## 🚀 Features

### 📊 Dashboard & Order Management
- **Real-time Order Dashboard**: View orders for any selected date with smart caching
- **Advanced Search**: Search by Order ID, Location Name, Rider Name, Vehicle Registration
- **Smart Filtering**: Filter orders by validation status, date, and issues
- **Order Statistics**: At-a-glance metrics with validation summaries
- **Responsive Design**: Mobile-friendly interface with modern UI/UX

### 🔄 Smart Data Management
- **Smart Refresh**: Fetch new orders from Locus API while preserving existing data
- **Database Caching**: Intelligent caching system for optimal performance
- **Automatic Updates**: Real-time order synchronization with conflict resolution
- **Data Export**: Export validation results and order data

### 🤖 AI-Powered Validation
- **Google Gemini AI**: Advanced GRN document analysis and validation
- **Multi-language Support**: Handle Arabic and English product names
- **Image Processing**: Analyze GRN documents with OCR capabilities
- **SKU Matching**: Intelligent product matching across different naming conventions
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
- `GET /dashboard` - Main dashboard interface
- `GET /dashboard?date=YYYY-MM-DD` - Dashboard for specific date
- `POST /api/refresh-orders` - Smart refresh orders from Locus API

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
3. **Search Orders** using the search bar (supports Order ID, Location, Rider, Vehicle)
4. **Filter Orders** by validation status or issues
5. **Refresh Data** to fetch new orders from Locus API

### 2. Order Validation
1. **Click "Validate GRN"** on any order card or in order details
2. **Review Results** showing validation status, matched products, and discrepancies
3. **Export Results** for reporting and analysis
4. **Reprocess** if needed for updated validation

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

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and updates.

---

**Built with ❤️ for efficient logistics management**