#!/usr/bin/env python3
"""
DataDome Cookie Validator
Validates extracted cookies to ensure they won't flag you
"""
import sys
import requests
import time
import json
import re
from urllib.parse import urlparse
import random

class DataDomeCookieValidator:
    def __init__(self):
        self.session = requests.Session()
        self.validation_results = {}

        # Common headers to appear legitimate
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }

    def validate_cookie_format(self, cookie_value):
        """Check if the cookie format looks legitimate"""
        print("🔍 Validating cookie format...")

        checks = {
            'length': len(cookie_value) > 50,  # DataDome cookies are typically long
            'base64_like': bool(re.match(r'^[A-Za-z0-9_-]+$', cookie_value)),
            'not_empty': cookie_value.strip() != '',
            'not_placeholder': cookie_value not in ['', 'null', 'undefined', 'test']
        }

        print(f"   Length: {len(cookie_value)} chars - {'✅' if checks['length'] else '❌'}")
        print(f"   Base64-like format: {'✅' if checks['base64_like'] else '❌'}")
        print(f"   Not empty: {'✅' if checks['not_empty'] else '❌'}")
        print(f"   Not placeholder: {'✅' if checks['not_placeholder'] else '❌'}")

        return all(checks.values())

    def test_basic_request(self, url, cookies):
        """Test basic request with the cookie"""
        print("🌐 Testing basic request...")

        try:
            response = self.session.get(
                url,
                cookies=cookies,
                headers=self.headers,
                timeout=10,
                allow_redirects=True
            )

            print(f"   Status Code: {response.status_code}")
            print(f"   Response Size: {len(response.content)} bytes")

            # Check for common DataDome challenge indicators
            challenge_indicators = [
                'DataDome',
                'geo.captcha-delivery.com',
                'Please enable JavaScript',
                'challenge-platform',
                'interstitial',
                'blocked',
                'suspicious'
            ]

            content_lower = response.text.lower()
            challenges_found = [indicator for indicator in challenge_indicators
                             if indicator.lower() in content_lower]

            if challenges_found:
                print(f"   ⚠️  Challenge indicators found: {challenges_found}")
                return False, f"Challenge detected: {challenges_found}"

            if response.status_code == 200:
                print("   ✅ Basic request successful")
                return True, "Success"
            elif response.status_code == 403:
                print("   ❌ Request blocked (403)")
                return False, "Blocked"
            else:
                print(f"   ⚠️  Unexpected status: {response.status_code}")
                return False, f"Status {response.status_code}"

        except Exception as e:
            print(f"   ❌ Request failed: {e}")
            return False, str(e)

    def test_multiple_requests(self, url, cookies, num_requests=5):
        """Test multiple requests to check for rate limiting or flagging"""
        print(f"🔄 Testing {num_requests} consecutive requests...")

        results = []
        for i in range(num_requests):
            try:
                response = self.session.get(
                    url,
                    cookies=cookies,
                    headers=self.headers,
                    timeout=10
                )

                results.append({
                    'request': i + 1,
                    'status': response.status_code,
                    'size': len(response.content),
                    'blocked': response.status_code in [403, 429, 503]
                })

                print(f"   Request {i+1}: {response.status_code} ({len(response.content)} bytes)")

                # Small delay between requests
                time.sleep(random.uniform(1, 3))

            except Exception as e:
                results.append({
                    'request': i + 1,
                    'status': 'ERROR',
                    'error': str(e),
                    'blocked': True
                })
                print(f"   Request {i+1}: ERROR - {e}")

        blocked_count = sum(1 for r in results if r.get('blocked', False))
        success_rate = (num_requests - blocked_count) / num_requests * 100

        print(f"   Success rate: {success_rate:.1f}% ({num_requests - blocked_count}/{num_requests})")

        return success_rate > 80, results

    def test_different_endpoints(self, base_url, cookies):
        """Test cookie against different endpoints"""
        print("🎯 Testing different endpoints...")

        # Common Idealista endpoints to test
        endpoints = [
            '/',
            '/alquiler-viviendas/',
            '/venta-viviendas/',
            '/inmueble/',
            '/profesionales/',
        ]

        results = {}
        for endpoint in endpoints:
            url = base_url.rstrip('/') + endpoint
            try:
                response = self.session.get(
                    url,
                    cookies=cookies,
                    headers=self.headers,
                    timeout=10
                )

                status = response.status_code
                blocked = status in [403, 429, 503] or 'datadome' in response.text.lower()

                results[endpoint] = {
                    'status': status,
                    'blocked': blocked,
                    'size': len(response.content)
                }

                print(f"   {endpoint}: {status} - {'❌ BLOCKED' if blocked else '✅ OK'}")

                time.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                results[endpoint] = {
                    'status': 'ERROR',
                    'blocked': True,
                    'error': str(e)
                }
                print(f"   {endpoint}: ERROR - {e}")

        blocked_endpoints = sum(1 for r in results.values() if r.get('blocked', False))
        success_rate = (len(endpoints) - blocked_endpoints) / len(endpoints) * 100

        return success_rate > 70, results

    def check_cookie_freshness(self, cookie_value):
        """Analyze if the cookie appears fresh/valid"""
        print("🕐 Checking cookie freshness...")

        # DataDome cookies often encode timestamp or session info
        # This is a heuristic check

        checks = {
            'reasonable_length': 50 < len(cookie_value) < 200,
            'has_variety': len(set(cookie_value)) > 10,  # Should have character variety
            'not_repeated': len(cookie_value) != len(set(cookie_value)) * 2,  # Not just repeated pattern
        }

        for check, result in checks.items():
            print(f"   {check}: {'✅' if result else '❌'}")

        return all(checks.values())

    def comprehensive_validation(self, cookies, base_url="https://www.idealista.com"):
        """Run comprehensive validation"""
        print("🚀 Starting comprehensive cookie validation...")
        print("=" * 60)

        if not cookies or 'datadome' not in cookies:
            print("❌ No DataDome cookie provided")
            return False, "No cookie"

        cookie_value = cookies['datadome']

        # 1. Format validation
        format_valid = self.validate_cookie_format(cookie_value)

        # 2. Freshness check
        fresh = self.check_cookie_freshness(cookie_value)

        # 3. Basic request test
        basic_success, basic_msg = self.test_basic_request(base_url, cookies)

        # 4. Multiple requests test
        multi_success, multi_results = self.test_multiple_requests(base_url, cookies, 3)

        # 5. Different endpoints test
        endpoints_success, endpoint_results = self.test_different_endpoints(base_url, cookies)

        # Compile results
        results = {
            'format_valid': format_valid,
            'freshness': fresh,
            'basic_request': basic_success,
            'multiple_requests': multi_success,
            'endpoints_test': endpoints_success,
            'overall_score': 0,
            'details': {
                'basic_message': basic_msg,
                'multi_results': multi_results,
                'endpoint_results': endpoint_results
            }
        }

        # Calculate overall score
        score_weights = {
            'format_valid': 1,
            'freshness': 1,
            'basic_request': 3,
            'multiple_requests': 2,
            'endpoints_test': 3
        }

        total_score = sum(score_weights[k] for k, v in results.items()
                         if k in score_weights and v)
        max_score = sum(score_weights.values())
        results['overall_score'] = (total_score / max_score) * 100

        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)

        print(f"Format Valid: {'✅' if format_valid else '❌'}")
        print(f"Cookie Fresh: {'✅' if fresh else '❌'}")
        print(f"Basic Request: {'✅' if basic_success else '❌'}")
        print(f"Multiple Requests: {'✅' if multi_success else '❌'}")
        print(f"Endpoints Test: {'✅' if endpoints_success else '❌'}")
        print(f"\nOverall Score: {results['overall_score']:.1f}%")

        # Final recommendation
        if results['overall_score'] >= 80:
            recommendation = "✅ COOKIE APPEARS VALID - Safe to use"
        elif results['overall_score'] >= 60:
            recommendation = "⚠️  COOKIE QUESTIONABLE - Use with caution"
        else:
            recommendation = "❌ COOKIE LIKELY INVALID - Do not use"

        print(f"\n🎯 RECOMMENDATION: {recommendation}")

        return results['overall_score'] >= 60, results

def main():
    """Main function for command line usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Validate DataDome cookies')
    parser.add_argument('--cookie', required=True, help='DataDome cookie value to validate')
    parser.add_argument('--url', default='https://www.idealista.com', help='Base URL to test against')
    parser.add_argument('--json-output', help='Save results to JSON file')

    args = parser.parse_args()

    # Create validator
    validator = DataDomeCookieValidator()

    # Prepare cookies
    cookies = {'datadome': args.cookie}

    # Run validation
    is_valid, results = validator.comprehensive_validation(cookies, args.url)

    # Save results if requested
    if args.json_output:
        with open(args.json_output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to {args.json_output}")

    return 0 if is_valid else 1

if __name__ == "__main__":
    # Example usage if run directly
    if len(sys.argv) == 1:
        print("Example usage:")
        print("python cookie_validator.py --cookie 'your_cookie_value_here'")
    else:
        exit(main())