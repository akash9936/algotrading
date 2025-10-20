"""
Simple Zerodha Authentication Helper
=====================================

This script helps you get an access token for Zerodha KiteConnect API
"""

import json
import os
from kiteconnect import KiteConnect

def authenticate():
    """Simple authentication flow"""

    print("=" * 80)
    print("ZERODHA AUTHENTICATION HELPER")
    print("=" * 80)
    print()

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')

    if not os.path.exists(config_path):
        print("❌ config.json not found!")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)

    api_key = config['api_key']
    api_secret = config['api_secret']

    # Initialize KiteConnect
    kite = KiteConnect(api_key=api_key)

    # Generate login URL
    login_url = kite.login_url()

    print("STEP 1: ENABLE YOUR APP")
    print("-" * 80)
    print("Before logging in, make sure your app is enabled:")
    print()
    print("1. Visit: https://console.zerodha.com/")
    print("2. Login with your Zerodha credentials")
    print("3. Go to 'Apps' section")
    print("4. Find your app and ENABLE it (toggle ON)")
    print("5. Wait 5 minutes for changes to take effect")
    print()
    input("Press Enter after you've enabled your app...")
    print()

    print("STEP 2: LOGIN AND AUTHORIZE")
    print("-" * 80)
    print("1. Open this URL in your browser:")
    print()
    print(f"   {login_url}")
    print()
    print("2. Login with your Zerodha credentials")
    print("3. Click 'Authorize' or 'Allow'")
    print()
    print("4. You'll be redirected to a URL like:")
    print("   http://127.0.0.1:5000/callback?request_token=XXXXXX&action=login&status=success")
    print()
    print("5. Copy the 'request_token' value (the XXXXXX part)")
    print()

    # Get request token
    request_token = input("Enter the request_token: ").strip()

    if not request_token:
        print("❌ No request token provided")
        return

    print()
    print("STEP 3: GENERATING ACCESS TOKEN")
    print("-" * 80)

    try:
        # Generate session
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]

        print("✓ Access token generated successfully!")
        print()
        print(f"Access Token: {access_token}")
        print()

        # Save to config
        config['access_token'] = access_token
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)

        print("✓ Access token saved to config.json")
        print()

        # Test the token
        print("STEP 4: TESTING CONNECTION")
        print("-" * 80)

        kite.set_access_token(access_token)
        profile = kite.profile()

        print(f"✓ Successfully connected!")
        print(f"✓ Name: {profile['user_name']}")
        print(f"✓ Email: {profile['email']}")
        print(f"✓ User ID: {profile['user_id']}")
        print()

        # Get margins
        margins = kite.margins()
        equity = margins.get('equity', {})
        available = equity.get('available', {}).get('cash', 0)
        print(f"✓ Available cash: ₹{available:,.2f}")

        print()
        print("=" * 80)
        print("✅ AUTHENTICATION SUCCESSFUL!")
        print("=" * 80)
        print()
        print("You can now run the live trading script:")
        print("  python3 src/live_trading/live_ma_crossover.py")
        print()

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}")
        print()

        if "user is not enabled" in error_msg.lower():
            print("=" * 80)
            print("⚠️  YOUR APP IS NOT ENABLED")
            print("=" * 80)
            print()
            print("This error means you need to enable API access in Zerodha.")
            print()
            print("SOLUTIONS:")
            print()
            print("Option 1: Enable via Zerodha Console")
            print("  1. Go to https://console.zerodha.com/")
            print("  2. Login and navigate to 'Apps'")
            print("  3. Find your app and click 'Enable'")
            print("  4. Wait 5-10 minutes")
            print("  5. Run this script again")
            print()
            print("Option 2: Contact Zerodha Support")
            print("  If the app doesn't appear or can't be enabled:")
            print("  - Email: kiteconnect@zerodha.com")
            print("  - Support: https://support.zerodha.com/")
            print("  - Ask them to enable API access for your account")
            print()
        elif "token" in error_msg.lower() or "invalid" in error_msg.lower():
            print("⚠️  The request token might be invalid or expired.")
            print("   Request tokens expire quickly (few minutes).")
            print("   Try the login process again from Step 2.")
            print()
        else:
            print("⚠️  Unexpected error occurred.")
            print("   Please check:")
            print("   - Your API Key and Secret are correct")
            print("   - Your Zerodha account has API access enabled")
            print("   - You've subscribed to Kite Connect")
            print()

if __name__ == "__main__":
    authenticate()
