# Locus Assistant

A Flask web application for connecting to Locus dashboard and visualizing order data with an intuitive, user-friendly interface.

## Features

- **Locus Authentication**: Complete OAuth2 flow implementation
- **Orders Visualization**: Clean, responsive display of order data
- **Demo Mode**: Test the application with sample data
- **Responsive Design**: Bootstrap-based UI with custom styling
- **Real-time Updates**: Auto-refresh functionality
- **Order Details**: Expandable views with complete order information
- **Date Filtering**: Filter orders by specific dates

## Quick Start

### Run the Application

1. **Install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start the application:**
   ```bash
   python app.py
   ```

3. **Access the application:**
   - Open http://localhost:8080 in your browser
   - Click "Try Demo" to see sample data
   - Or enter real Locus credentials to connect

## Demo Mode

The application includes a demo mode with sample Locus order data. Click the "Try Demo" button on the login page to explore the interface without real authentication.

## Authentication Flow

The app implements the complete Locus authentication flow:

1. **Personnel Info**: `GET /v1/minimal-personnel`
2. **Login**: `POST /usernamepassword/login`
3. **Token Exchange**: `POST /oauth/token`
4. **Orders API**: `POST /v1/client/{client-id}/order-search`

## Project Structure

```
locusassist/
├── app.py                 # Main Flask application
├── demo_data.py          # Sample data for demo mode
├── test_app.py           # Test suite
├── requirements.txt      # Python dependencies
├── templates/
│   ├── base.html         # Base template
│   ├── login.html        # Login page
│   └── dashboard.html    # Orders dashboard
└── static/
    ├── css/
    │   └── style.css     # Custom styles
    └── js/
        └── app.js        # JavaScript functionality
```

## API Endpoints

- `GET /` - Login page
- `POST /login` - Handle authentication
- `GET /demo` - Enable demo mode
- `GET /dashboard` - Orders dashboard
- `GET /api/orders` - Orders API endpoint
- `GET /logout` - Clear session

## Testing

Run the test suite:
```bash
python test_app.py
```

All tests pass including:
- Home page loading
- Authentication flows
- Session management
- API endpoints
- Static file serving
- Responsive design elements

## Technologies Used

- **Backend**: Flask, Python
- **Frontend**: Bootstrap 5, Font Awesome, Custom CSS/JS
- **Authentication**: OAuth2 flow with Locus APIs
- **Testing**: Python unittest framework

## Features Demonstrated

1. ✅ Locus login authentication
2. ✅ Orders data fetching and display
3. ✅ Beautiful, responsive UI
4. ✅ User-friendly interface
5. ✅ Demo mode for testing
6. ✅ Comprehensive test coverage
7. ✅ Production-ready Flask app