#!/usr/bin/env python3
"""
Amazon Photos API Authentication Setup
This script helps set up authentication for the Amazon Photos API
"""

import os
import sys
import json
import logging
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('amazon_auth_setup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants
AUTH_ENDPOINT = "https://www.amazon.com/ap/oa"
TOKEN_ENDPOINT = "https://api.amazon.com/auth/o2/token"
REDIRECT_URI = "https://localhost:8000/callback"
SCOPES = ["clouddrive:read", "clouddrive:write"]

class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback"""
    
    def do_GET(self):
        """Handle GET request to callback URL"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Parse the query parameters
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        if 'code' in params:
            # Store the authorization code
            self.server.authorization_code = params['code'][0]
            response = """
            <html>
            <head><title>Authorization Successful</title></head>
            <body>
                <h1>Authorization Successful!</h1>
                <p>You can now close this window and return to the application.</p>
            </body>
            </html>
            """
        else:
            # Handle error
            error = params.get('error', ['Unknown error'])[0]
            error_description = params.get('error_description', ['No description'])[0]
            self.server.authorization_code = None
            response = f"""
            <html>
            <head><title>Authorization Failed</title></head>
            <body>
                <h1>Authorization Failed</h1>
                <p>Error: {error}</p>
                <p>Description: {error_description}</p>
            </body>
            </html>
            """
        
        self.wfile.write(response.encode('utf-8'))

def get_authorization_code(client_id):
    """Get the authorization code via web browser"""
    # Prepare the authorization URL
    auth_params = {
        'client_id': client_id,
        'scope': ' '.join(SCOPES),
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI
    }
    
    auth_url = f"{AUTH_ENDPOINT}?{'&'.join([f'{k}={v}' for k, v in auth_params.items()])}"
    
    # Open the browser for the user to authenticate
    logger.info(f"Opening browser for Amazon authorization...")
    webbrowser.open(auth_url)
    
    # Start a local server with HTTPS to receive the callback
    import ssl
    server = HTTPServer(('localhost', 8000), CallbackHandler)
    # Set up SSL for HTTPS
    if os.path.exists('key.pem') and os.path.exists('cert.pem'):
        server.socket = ssl.wrap_socket(
            server.socket,
            keyfile='key.pem',
            certfile='cert.pem',
            server_side=True
        )
    else:
        logger.warning("SSL certificates not found. Using HTTP instead of HTTPS.")
        logger.warning("Run generate_certificates.py to create SSL certificates.")
    server.authorization_code = None
    
    logger.info("Waiting for authorization callback...")
    server.handle_request()
    
    if not server.authorization_code:
        logger.error("Failed to get authorization code")
        return None
    
    logger.info("Successfully received authorization code")
    return server.authorization_code

def exchange_code_for_tokens(client_id, client_secret, authorization_code):
    """Exchange the authorization code for access and refresh tokens"""
    token_params = {
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': REDIRECT_URI
    }
    
    try:
        response = requests.post(TOKEN_ENDPOINT, data=token_params)
        response.raise_for_status()
        
        tokens = response.json()
        logger.info("Successfully exchanged authorization code for tokens")
        
        return tokens
    
    except Exception as e:
        logger.error(f"Error exchanging authorization code for tokens: {str(e)}")
        return None

def update_env_file(env_file, tokens):
    """Update the .env file with the tokens"""
    # Load the current .env file
    load_dotenv(env_file)
    
    # Read the current content
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Update or add the refresh token
    refresh_token_line = f"AMAZON_REFRESH_TOKEN={tokens['refresh_token']}\n"
    
    refresh_token_found = False
    for i, line in enumerate(lines):
        if line.startswith('AMAZON_REFRESH_TOKEN='):
            lines[i] = refresh_token_line
            refresh_token_found = True
            break
    
    if not refresh_token_found:
        # Find the Amazon section
        amazon_section_index = -1
        for i, line in enumerate(lines):
            if '# Amazon Photos API credentials' in line:
                amazon_section_index = i
                break
        
        if amazon_section_index >= 0:
            # Insert after the Amazon client secret
            for i in range(amazon_section_index, len(lines)):
                if lines[i].startswith('AMAZON_CLIENT_SECRET='):
                    lines.insert(i + 1, refresh_token_line)
                    break
        else:
            # Just append to the end
            lines.append("\n# Amazon Photos API credentials\n")
            lines.append(f"AMAZON_CLIENT_ID={os.getenv('AMAZON_CLIENT_ID', '')}\n")
            lines.append(f"AMAZON_CLIENT_SECRET={os.getenv('AMAZON_CLIENT_SECRET', '')}\n")
            lines.append(refresh_token_line)
    
    # Write back to the file
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    logger.info(f"Updated {env_file} with refresh token")

def main():
    """Main function to set up Amazon Photos API authentication"""
    # Load environment variables
    load_dotenv()
    
    # Get client credentials
    client_id = os.getenv('AMAZON_CLIENT_ID')
    client_secret = os.getenv('AMAZON_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        logger.error("Amazon client credentials not found in .env file")
        print("\nPlease add your Amazon client credentials to the .env file:")
        print("AMAZON_CLIENT_ID=your_client_id")
        print("AMAZON_CLIENT_SECRET=your_client_secret")
        return 1
    
    # Get authorization code
    authorization_code = get_authorization_code(client_id)
    if not authorization_code:
        return 1
    
    # Exchange for tokens
    tokens = exchange_code_for_tokens(client_id, client_secret, authorization_code)
    if not tokens:
        return 1
    
    # Save the refresh token to .env file
    update_env_file('.env', tokens)
    
    print("\nAmazon Photos API authentication setup complete!")
    print(f"Access token expires in {tokens['expires_in']} seconds")
    print("Refresh token has been saved to .env file")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
