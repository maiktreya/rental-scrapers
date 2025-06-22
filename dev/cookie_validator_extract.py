#!/usr/bin/env python3
"""
Complete DataDome Cookie Extraction and Validation Pipeline
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from dev.cookie_validator import OptimizedDataDomeExtractor
from cookie_validator import DataDomeCookieValidator
import json
import time

def extract_and_validate_cookie(
    url="https://www.idealista.com",
    wait_time=20,
    user_data_dir=None,
    bot_profile_path=None,
    validate=True
):
    """Complete pipeline: extract -> validate -> report"""

    print("🔄 DATADOME COOKIE EXTRACTION & VALIDATION PIPELINE")
    print("=" * 70)

    # Step 1: Extract cookie
    print("\n📋 STEP 1: EXTRACTING COOKIE")
    print("-" * 30)

    extractor = OptimizedDataDomeExtractor(user_data_dir, bot_profile_path)
    cookie_data = extractor.extract_datadome_cookie(url, wait_time)

    if not cookie_data:
        print("❌ Cookie extraction failed!")
        return None

    cookie_value = cookie_data['value']
    cookies = {'datadome': cookie_value}

    print(f"✅ Cookie extracted successfully!")
    print(f"   Length: {len(cookie_value)} characters")
    print(f"   Preview: {cookie_value[:50]}...")

    if not validate:
        return {
            'cookie_data': cookie_data,
            'cookies': cookies,
            'valid': True,  # Assume valid if not validating
            'validation_results': None
        }

    # Step 2: Validate cookie
    print(f"\n🔍 STEP 2: VALIDATING COOKIE")
    print("-" * 30)

    validator = DataDomeCookieValidator()
    is_valid, validation_results = validator.comprehensive_validation(cookies, url)

    # Step 3: Final report
    print(f"\n📊 STEP 3: FINAL REPORT")
    print("-" * 30)

    result = {
        'cookie_data': cookie_data,
        'cookies': cookies,
        'valid': is_valid,
        'validation_results': validation_results,
        'ready_to_use': is_valid
    }

    if is_valid:
        print("🎉 SUCCESS! Cookie is valid and ready to use")
        print("\n🐍 For Python requests:")
        print(f"cookies = {cookies}")

        print("\n🌐 For curl:")
        print(f'curl --cookie "datadome={cookie_value}" "{url}"')

        print("\n📡 For HTTP headers:")
        print(f'headers = {{"Cookie": "datadome={cookie_value}"}}')

    else:
        print("⚠️  WARNING: Cookie validation failed!")
        print("This cookie may flag you or get blocked.")
        print("Consider extracting a new cookie or checking your extraction method.")

    return result

def quick_test_cookie(cookie_value, url="https://www.idealista.com"):
    """Quick test for an already extracted cookie"""
    print("🧪 QUICK COOKIE TEST")
    print("=" * 30)

    cookies = {'datadome': cookie_value}
    validator = DataDomeCookieValidator()

    # Just do basic tests
    format_valid = validator.validate_cookie_format(cookie_value)
    basic_success, basic_msg = validator.test_basic_request(url, cookies)

    print(f"\nFormat Valid: {'✅' if format_valid else '❌'}")
    print(f"Basic Request: {'✅' if basic_success else '❌'} ({basic_msg})")

    if format_valid and basic_success:
        print("\n✅ Cookie looks good for immediate use!")
        return True
    else:
        print("\n❌ Cookie may have issues")
        return False

def main():
    """Command line interface"""
    import argparse

    parser = argparse.ArgumentParser(description='Extract and validate DataDome cookies')
    parser.add_argument('--extract', action='store_true', help='Extract new cookie')
    parser.add_argument('--test-cookie', help='Test existing cookie value')
    parser.add_argument('--url', default='https://www.idealista.com', help='URL to test against')
    parser.add_argument('--wait', type=int, default=20, help='Wait time for extraction')
    parser.add_argument('--no-validate', action='store_true', help='Skip validation step')
    parser.add_argument('--user-data-dir', help='Chrome user data directory')
    parser.add_argument('--bot-profile', help='Bot profile path')
    parser.add_argument('--save-results', help='Save results to JSON file')

    args = parser.parse_args()

    if args.test_cookie:
        # Quick test mode
        success = quick_test_cookie(args.test_cookie, args.url)
        return 0 if success else 1

    elif args.extract:
        # Full extraction and validation
        result = extract_and_validate_cookie(
            url=args.url,
            wait_time=args.wait,
            user_data_dir=args.user_data_dir,
            bot_profile_path=args.bot_profile,
            validate=not args.no_validate
        )

        if result and args.save_results:
            with open(args.save_results, 'w') as f:
                # Make results JSON serializable
                save_data = {
                    'cookie_value': result['cookie_data']['value'],
                    'cookie_domain': result['cookie_data']['domain'],
                    'valid': result['valid'],
                    'validation_score': result['validation_results']['overall_score'] if result['validation_results'] else None,
                    'timestamp': time.time()
                }
                json.dump(save_data, f, indent=2)
            print(f"\n💾 Results saved to {args.save_results}")

        return 0 if result and result['valid'] else 1

    else:
        print("Usage examples:")
        print("  Extract and validate:  python extract_and_validate.py --extract")
        print("  Test existing cookie:  python extract_and_validate.py --test-cookie 'your_cookie_here'")
        print("  Extract only:          python extract_and_validate.py --extract --no-validate")
        return 1

if __name__ == "__main__":
    exit(main())