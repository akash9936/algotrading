"""
Zerodha Setup Verification Tool
================================

This script helps diagnose connection issues with Zerodha KiteConnect API
"""

import json
import os
from kiteconnect import KiteConnect

def verify_setup():
    """Verify Zerodha API setup"""

    print("=" * 80)
    print("ZERODHA KITECONNECT SETUP VERIFICATION")
    print("=" * 80)
    print()

    # Step 1: Check config file
    print("Step 1: Checking config file...")
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')

    if not os.path.exists(config_path):
        print("❌ FAIL: config.json not found")
        print("   Create config.json from config_template.json")
        return

    print("✓ config.json exists")

    # Step 2: Load credentials
    print("\nStep 2: Loading credentials...")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        api_key = config.get('api_key')
        api_secret = config.get('api_secret')
        access_token = config.get('access_token')

        if not api_key or api_key == "YOUR_ZERODHA_API_KEY":
            print("❌ FAIL: API Key not set in config.json")
            return

        if not api_secret or api_secret == "YOUR_ZERODHA_API_SECRET":
            print("❌ FAIL: API Secret not set in config.json")
            return

        print(f"✓ API Key found: {api_key[:4]}...{api_key[-4:]}")
        print(f"✓ API Secret found: {api_secret[:4]}...{api_secret[-4:]}")

        if access_token:
            print(f"✓ Access Token found: {access_token[:4]}...{access_token[-4:]}")
        else:
            print("⚠ Access Token not found (will need to login)")

    except json.JSONDecodeError:
        print("❌ FAIL: config.json is not valid JSON")
        return
    except Exception as e:
        print(f"❌ FAIL: Error reading config: {str(e)}")
        return

    # Step 3: Test KiteConnect initialization
    print("\nStep 3: Testing KiteConnect initialization...")
    try:
        kite = KiteConnect(api_key=api_key)
        print("✓ KiteConnect initialized successfully")
    except Exception as e:
        print(f"❌ FAIL: Error initializing KiteConnect: {str(e)}")
        return

    # Step 4: Generate login URL
    print("\nStep 4: Generating login URL...")
    try:
        login_url = kite.login_url()
        print("✓ Login URL generated successfully")
        print(f"\n{login_url}\n")
    except Exception as e:
        print(f"❌ FAIL: Error generating login URL: {str(e)}")
        return

    # Step 5: Check if we can test with access token
    if access_token:
        print("\nStep 5: Testing access token...")
        try:
            kite.set_access_token(access_token)
            profile = kite.profile()
            print("✓ Access token is valid!")
            print(f"✓ Connected as: {profile['user_name']} ({profile['email']})")
            print(f"✓ User ID: {profile['user_id']}")

            # Test margins
            print("\nStep 6: Testing margin access...")
            margins = kite.margins()
            equity = margins.get('equity', {})
            available = equity.get('available', {}).get('cash', 0)
            print(f"✓ Available cash: ₹{available:,.2f}")

            print("\n" + "=" * 80)
            print("✅ ALL CHECKS PASSED! Your setup is working correctly.")
            print("=" * 80)
            return

        except Exception as e:
            error_msg = str(e)
            print(f"❌ FAIL: Access token test failed")
            print(f"   Error: {error_msg}")

            if "user is not enabled" in error_msg.lower():
                print("\n" + "=" * 80)
                print("⚠️  ERROR: User is not enabled for the app")
                print("=" * 80)
                print("\nThis means your Zerodha account needs to enable API access.")
                print("\nFOLLOW THESE STEPS:")
                print("1. Login to https://kite.zerodha.com/")
                print("2. Go to Profile/Settings → Apps")
                print("3. Find your app and ENABLE it")
                print("\nOR")
                print("1. Visit https://console.zerodha.com/")
                print("2. Login and go to 'Apps' section")
                print("3. Enable your app")
                print("\nAfter enabling, wait 5-10 minutes and run this script again.")
                print("=" * 80)
            elif "token" in error_msg.lower():
                print("\n⚠️  Access token expired. You need to login again.")
                print("   Run: python3 src/live_trading/live_ma_crossover.py")

            return
    else:
        print("\nStep 5: Access token not available")
        print("   You'll need to complete the login flow to get an access token")

    # Final summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\n✓ Config file is set up correctly")
    print("✓ API credentials are present")
    print("\n⚠️  Next step: Complete the login flow")
    print("\nTO LOGIN:")
    print("1. Open the login URL shown above in a browser")
    print("2. Login with your Zerodha credentials")
    print("3. Authorize the app")
    print("4. Copy the request_token from redirect URL")
    print("5. Run: python3 src/live_trading/live_ma_crossover.py")
    print("   and paste the request_token when asked")
    print("=" * 80)

if __name__ == "__main__":
    verify_setup()
