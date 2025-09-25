import unittest
import json
from app import app, locus_auth

class LocusAssistantTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client"""
        self.app = app.test_client()
        self.app.testing = True
        app.config['SECRET_KEY'] = 'test-secret-key'

    def test_home_page(self):
        """Test that home page loads correctly"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login to Locus', response.data)
        self.assertIn(b'Locus Assistant', response.data)

    def test_login_page_structure(self):
        """Test login page has required form elements"""
        response = self.app.get('/')
        self.assertIn(b'name="username"', response.data)
        self.assertIn(b'name="password"', response.data)
        self.assertIn(b'type="submit"', response.data)

    def test_dashboard_redirect_without_login(self):
        """Test that dashboard redirects to login when not authenticated"""
        response = self.app.get('/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn(b'Redirecting', response.data)

    def test_api_orders_without_auth(self):
        """Test API endpoint returns 401 without authentication"""
        response = self.app.get('/api/orders')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_logout_clears_session(self):
        """Test logout functionality"""
        # First set a session
        with self.app.session_transaction() as sess:
            sess['access_token'] = 'test-token'
            sess['username'] = 'test-user'

        # Then logout
        response = self.app.get('/logout')
        self.assertEqual(response.status_code, 302)

        # Check session is cleared
        with self.app.session_transaction() as sess:
            self.assertNotIn('access_token', sess)

    def test_login_post_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.app.post('/login', data={
            'username': 'invalid-user',
            'password': 'invalid-pass'
        })
        self.assertEqual(response.status_code, 302)

    def test_static_files_accessible(self):
        """Test that static files are accessible"""
        response = self.app.get('/static/css/style.css')
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/static/js/app.js')
        self.assertEqual(response.status_code, 200)

    def test_locus_auth_class(self):
        """Test LocusAuth class methods"""
        auth = locus_auth

        # Test that methods exist
        self.assertTrue(hasattr(auth, 'get_personnel_info'))
        self.assertTrue(hasattr(auth, 'authenticate'))
        self.assertTrue(hasattr(auth, 'get_access_token'))
        self.assertTrue(hasattr(auth, 'get_orders'))

    def test_responsive_design_elements(self):
        """Test that responsive design elements are present"""
        response = self.app.get('/')

        # Check for Bootstrap classes
        self.assertIn(b'container', response.data)
        self.assertIn(b'row', response.data)
        self.assertIn(b'col-', response.data)

        # Check for viewport meta tag
        self.assertIn(b'viewport', response.data)

if __name__ == '__main__':
    unittest.main()