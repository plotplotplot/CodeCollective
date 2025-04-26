#!/usr/bin/env python3
"""
Google OAuth2 Setup for Postfix

This script handles the OAuth2 authentication flow with Google Workspace,
stores the credentials securely, and configures Postfix to use these
credentials for sending email.

Usage:
  python3 google_oauth_postfix.py setup --client-id CLIENT_ID --client-secret CLIENT_SECRET --email EMAIL
  python3 google_oauth_postfix.py refresh
  python3 google_oauth_postfix.py status

Requirements:
  - Python 3.6+
  - requests
  - google-auth
  - google-auth-oauthlib
"""

import os
import sys
import json
import base64
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Configuration
TOKEN_FILE = '/etc/postfix/google_oauth_token.json'
SASL_PASSWD_FILE = '/etc/postfix/sasl_passwd'
SCOPES = ['https://mail.google.com/']
POSTFIX_CONFIG_FILE = '/etc/postfix/main.cf'

def setup_oauth(client_id, client_secret, email):
    """Set up OAuth2 authentication with Google."""
    print("Starting OAuth2 authentication flow...")
    
    # Create credentials config
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
        }
    }
    
    flow = InstalledAppFlow.from_client_config(
        client_config, SCOPES)
    
    # Run the OAuth flow
    credentials = flow.run_local_server(port=0)
    
    # Save the credentials
    token_data = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
        'expiry': credentials.expiry.isoformat(),
        'email': email
    }
    
    with open(TOKEN_FILE, 'w') as token_file:
        json.dump(token_data, token_file)
    
    # Set proper permissions
    os.chmod(TOKEN_FILE, 0o600)
    
    print(f"Credentials saved to {TOKEN_FILE}")
    return credentials

def refresh_token():
    """Refresh the OAuth2 token if needed."""
    if not os.path.exists(TOKEN_FILE):
        print(f"Error: Token file not found at {TOKEN_FILE}")
        print("Please run setup first.")
        sys.exit(1)
    
    with open(TOKEN_FILE, 'r') as token_file:
        token_data = json.load(token_file)
    
    credentials = Credentials(
        token=token_data['token'],
        refresh_token=token_data['refresh_token'],
        token_uri=token_data['token_uri'],
        client_id=token_data['client_id'],
        client_secret=token_data['client_secret'],
        scopes=token_data['scopes']
    )
    
    if token_data['expiry']:
        credentials.expiry = datetime.fromisoformat(token_data['expiry'])
    
    # Check if token needs to be refreshed
    if not credentials.valid:
        print("Token expired, refreshing...")
        credentials.refresh(Request())
        
        # Update the saved token
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat(),
            'email': token_data['email']
        }
        
        with open(TOKEN_FILE, 'w') as token_file:
            json.dump(token_data, token_file)
        
        print(f"Token refreshed and saved to {TOKEN_FILE}")
    else:
        print("Token is still valid.")
    
    return credentials, token_data['email']

def generate_xoauth2_string(user, access_token):
    """Generate the XOAUTH2 authentication string."""
    auth_string = f"user={user}\1auth=Bearer {access_token}\1\1"
    return base64.b64encode(auth_string.encode()).decode()

def update_postfix_config(email, xoauth2_string):
    """Update the Postfix configuration to use XOAUTH2."""
    # Update sasl_passwd file
    with open(SASL_PASSWD_FILE, 'w') as f:
        f.write(f"smtp.gmail.com:587 {email}:xoauth2={xoauth2_string}\n")
    
    # Set proper permissions
    os.chmod(SASL_PASSWD_FILE, 0o600)
    
    # Create the hash database file
    subprocess.run(['postmap', SASL_PASSWD_FILE], check=True)
    
    # Check if Postfix is already configured for OAuth2
    with open(POSTFIX_CONFIG_FILE, 'r') as f:
        config_content = f.read()
    
    # Required configuration settings
    required_settings = {
        'relayhost': 'smtp.gmail.com:587',
        'smtp_sasl_auth_enable': 'yes',
        'smtp_sasl_security_options': 'noanonymous',
        'smtp_sasl_mechanism_filter': 'xoauth2',
        'smtp_use_tls': 'yes',
        'smtp_tls_security_level': 'encrypt',
        'smtp_tls_CAfile': '/etc/ssl/certs/ca-certificates.crt',
        'smtp_sasl_password_maps': f'hash:{SASL_PASSWD_FILE}'
    }
    
    # Check and update configuration settings
    updated = False
    for key, value in required_settings.items():
        if f"{key} = {value}" not in config_content:
            # Setting is missing or incorrect, need to update
            updated = True
            break
    
    if updated:
        # Backup the current configuration
        backup_file = f"{POSTFIX_CONFIG_FILE}.bak.{int(time.time())}"
        subprocess.run(['cp', POSTFIX_CONFIG_FILE, backup_file], check=True)
        print(f"Backed up current configuration to {backup_file}")
        
        # Update the configuration file
        with open(POSTFIX_CONFIG_FILE, 'a') as f:
            f.write("\n# Google OAuth2 Configuration - Added by script\n")
            for key, value in required_settings.items():
                f.write(f"{key} = {value}\n")
        
        print("Updated Postfix configuration")
    else:
        print("Postfix configuration is already up to date")
    
    # Restart Postfix
    subprocess.run(['systemctl', 'restart', 'postfix'], check=True)
    print("Restarted Postfix service")

def show_status():
    """Display the current status of the OAuth2 setup."""
    if not os.path.exists(TOKEN_FILE):
        print("Status: Not configured")
        print(f"Token file not found at {TOKEN_FILE}")
        return
    
    with open(TOKEN_FILE, 'r') as token_file:
        token_data = json.load(token_file)
    
    expiry = datetime.fromisoformat(token_data['expiry'])
    now = datetime.now()
    
    print("OAuth2 Configuration Status:")
    print(f"Email: {token_data['email']}")
    print(f"Token expiry: {expiry}")
    print(f"Token valid: {'Yes' if expiry > now else 'No'}")
    print(f"Time until expiry: {expiry - now if expiry > now else 'Expired'}")
    
    # Check Postfix configuration
    try:
        with open(POSTFIX_CONFIG_FILE, 'r') as f:
            config_content = f.read()
        
        if 'smtp_sasl_mechanism_filter = xoauth2' in config_content:
            print("Postfix configuration: Found OAuth2 settings")
        else:
            print("Postfix configuration: OAuth2 settings not found")
            
        if os.path.exists(SASL_PASSWD_FILE):
            print(f"SASL password file: Found ({SASL_PASSWD_FILE})")
        else:
            print(f"SASL password file: Not found ({SASL_PASSWD_FILE})")
            
        if os.path.exists(SASL_PASSWD_FILE + ".db"):
            print(f"SASL password database: Found ({SASL_PASSWD_FILE}.db)")
        else:
            print(f"SASL password database: Not found ({SASL_PASSWD_FILE}.db)")
    
    except Exception as e:
        print(f"Error checking Postfix configuration: {e}")

def main():
    """Main function to parse arguments and run the appropriate action."""
    parser = argparse.ArgumentParser(description='Google OAuth2 Setup for Postfix')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Set up OAuth2 with Google')
    setup_parser.add_argument('--client-id', required=True, help='Google OAuth2 Client ID')
    setup_parser.add_argument('--client-secret', required=True, help='Google OAuth2 Client Secret')
    setup_parser.add_argument('--email', required=True, help='Your Google Workspace email address')
    
    # Refresh command
    refresh_parser = subparsers.add_parser('refresh', help='Refresh the OAuth2 token')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show current OAuth2 status')
    
    args = parser.parse_args()
    
    # Check for root privileges
    if os.geteuid() != 0:
        print("This script must be run as root because it modifies Postfix configuration files.")
        print("Please run with sudo:")
        print(f"  sudo {sys.argv[0]} {' '.join(sys.argv[1:])}")
        sys.exit(1)
    
    # Execute the requested command
    if args.command == 'setup':
        credentials = setup_oauth(args.client_id, args.client_secret, args.email)
        xoauth2_string = generate_xoauth2_string(args.email, credentials.token)
        update_postfix_config(args.email, xoauth2_string)
        print("\nSetup completed successfully!")
        print("\nTo test your configuration, send a test email:")
        print('echo -e "Subject: Test Email\\n\\nThis is a test email sent via Google OAuth2." | sendmail recipient@example.com')
        
    elif args.command == 'refresh':
        credentials, email = refresh_token()
        xoauth2_string = generate_xoauth2_string(email, credentials.token)
        update_postfix_config(email, xoauth2_string)
        print("\nToken refreshed and Postfix configuration updated successfully!")
        
    elif args.command == 'status':
        show_status()
        
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
