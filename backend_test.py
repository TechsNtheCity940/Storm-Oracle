#!/usr/bin/env python3
"""
Storm Oracle Backend API Test Suite
Tests all API endpoints for the tornado prediction system
"""

import requests
import sys
import json
from datetime import datetime
import time

class StormOracleAPITester:
    def __init__(self, base_url="https://storm-tracker-9.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details="", response_data=None):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "response_data": response_data
        })

    def run_test(self, name, method, endpoint, expected_status=200, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params, timeout=30)
            
            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            response_data = None
            
            if success:
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                except:
                    response_data = response.text[:200]
                    print(f"   Response: {response_data}...")
            else:
                error_details = f"Expected {expected_status}, got {response.status_code}"
                try:
                    error_response = response.json()
                    error_details += f" - {error_response}"
                except:
                    error_details += f" - {response.text[:100]}"
                print(f"   Error: {error_details}")
            
            self.log_test(name, success, 
                         "" if success else f"Status {response.status_code} != {expected_status}",
                         response_data)
            
            return success, response_data

        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            print(f"   Exception: {error_msg}")
            self.log_test(name, False, error_msg)
            return False, {}

    def test_root_endpoint(self):
        """Test API root endpoint"""
        return self.run_test("API Root", "GET", "")

    def test_radar_stations(self):
        """Test radar stations endpoint"""
        success, data = self.run_test("Get All Radar Stations", "GET", "radar-stations")
        
        if success and data:
            station_count = len(data) if isinstance(data, list) else 0
            print(f"   Found {station_count} radar stations")
            
            # Verify we have the expected 144 stations
            if station_count >= 140:  # Allow some tolerance
                print(f"   ✅ Station count looks good ({station_count})")
            else:
                print(f"   ⚠️  Expected ~144 stations, got {station_count}")
            
            # Test specific station if we have data
            if station_count > 0 and isinstance(data, list):
                test_station = data[0]['station_id'] if 'station_id' in data[0] else None
                if test_station:
                    self.test_specific_radar_station(test_station)
        
        return success, data

    def test_specific_radar_station(self, station_id="KEAX"):
        """Test specific radar station endpoint"""
        return self.run_test(f"Get Radar Station {station_id}", "GET", f"radar-stations/{station_id}")

    def test_radar_data(self, station_id="KEAX"):
        """Test radar data endpoint"""
        return self.run_test(f"Get Radar Data for {station_id}", "GET", 
                           f"radar-data/{station_id}", params={"data_type": "reflectivity"})

    def test_radar_data_comprehensive(self):
        """Comprehensive radar data testing for visualization issue"""
        print("\n🎯 COMPREHENSIVE RADAR DATA VISUALIZATION TESTING")
        print("=" * 60)
        
        # Test stations as specified in the review request
        test_stations = ["KEAX", "KFWS", "KAMA"]
        
        # Test data types as specified in the review request
        data_types = ["base_reflectivity", "hi_res_reflectivity", "base_velocity"]
        
        all_tests_passed = True
        radar_url_tests = []
        
        for station_id in test_stations:
            print(f"\n📡 Testing Station: {station_id}")
            
            for data_type in data_types:
                print(f"\n   🔍 Testing data type: {data_type}")
                
                # Test 1: Basic API response
                success, data = self.run_test(
                    f"Radar Data API - {station_id} - {data_type}", 
                    "GET", 
                    f"radar-data/{station_id}", 
                    params={"data_type": data_type}
                )
                
                if not success:
                    all_tests_passed = False
                    continue
                
                # Test 2: Verify response structure
                required_fields = ["radar_url", "station_id", "data_type", "timestamp", "coordinates"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print(f"   ❌ Missing required fields: {missing_fields}")
                    self.log_test(f"Response Structure - {station_id} - {data_type}", False, 
                                f"Missing fields: {missing_fields}")
                    all_tests_passed = False
                else:
                    print(f"   ✅ Response structure valid")
                    self.log_test(f"Response Structure - {station_id} - {data_type}", True)
                
                # Test 3: Verify radar URL accessibility
                if "radar_url" in data and data["radar_url"]:
                    radar_url = data["radar_url"]
                    print(f"   🌐 Testing radar URL accessibility: {radar_url[:50]}...")
                    
                    try:
                        import requests
                        response = requests.head(radar_url, timeout=10)
                        url_accessible = response.status_code == 200
                        
                        if url_accessible:
                            print(f"   ✅ Radar URL accessible (Status: {response.status_code})")
                            
                            # Check if it's actually an image
                            content_type = response.headers.get('content-type', '')
                            if 'image' in content_type.lower() or radar_url.endswith(('.gif', '.png', '.jpg', '.jpeg')):
                                print(f"   ✅ URL returns image content ({content_type})")
                                self.log_test(f"Radar URL Accessibility - {station_id} - {data_type}", True)
                            else:
                                print(f"   ⚠️  URL accessible but may not be image ({content_type})")
                                self.log_test(f"Radar URL Accessibility - {station_id} - {data_type}", True, 
                                            f"Non-image content type: {content_type}")
                        else:
                            print(f"   ❌ Radar URL not accessible (Status: {response.status_code})")
                            self.log_test(f"Radar URL Accessibility - {station_id} - {data_type}", False, 
                                        f"HTTP {response.status_code}")
                            all_tests_passed = False
                            
                    except Exception as e:
                        print(f"   ❌ Error testing radar URL: {str(e)}")
                        self.log_test(f"Radar URL Accessibility - {station_id} - {data_type}", False, str(e))
                        all_tests_passed = False
                    
                    radar_url_tests.append({
                        "station": station_id,
                        "data_type": data_type,
                        "url": radar_url,
                        "accessible": url_accessible if 'url_accessible' in locals() else False
                    })
                else:
                    print(f"   ❌ No radar_url in response")
                    self.log_test(f"Radar URL Present - {station_id} - {data_type}", False, "No radar_url field")
                    all_tests_passed = False
                
                # Test 4: Test with timestamp parameter
                current_timestamp = int(time.time() * 1000)  # JavaScript timestamp
                success_ts, data_ts = self.run_test(
                    f"Radar Data with Timestamp - {station_id} - {data_type}", 
                    "GET", 
                    f"radar-data/{station_id}", 
                    params={"data_type": data_type, "timestamp": current_timestamp}
                )
                
                if success_ts and data_ts:
                    if "radar_url" in data_ts and data_ts["radar_url"] != data.get("radar_url"):
                        print(f"   ✅ Timestamp parameter affects URL generation")
                    else:
                        print(f"   ℹ️  Timestamp parameter may not affect URL (or same result)")
                
                # Test 5: Response time check
                start_time = time.time()
                try:
                    response = requests.get(f"{self.api_url}/radar-data/{station_id}", 
                                          params={"data_type": data_type}, timeout=30)
                    response_time = time.time() - start_time
                    
                    if response_time < 5.0:
                        print(f"   ✅ Good response time: {response_time:.2f}s")
                        self.log_test(f"Response Time - {station_id} - {data_type}", True, 
                                    f"{response_time:.2f}s")
                    else:
                        print(f"   ⚠️  Slow response time: {response_time:.2f}s")
                        self.log_test(f"Response Time - {station_id} - {data_type}", True, 
                                    f"Slow: {response_time:.2f}s")
                        
                except Exception as e:
                    print(f"   ❌ Response time test failed: {str(e)}")
                    self.log_test(f"Response Time - {station_id} - {data_type}", False, str(e))
        
        # Summary of radar URL tests
        print(f"\n📊 RADAR URL ACCESSIBILITY SUMMARY")
        print("=" * 40)
        accessible_count = sum(1 for test in radar_url_tests if test.get('accessible', False))
        total_count = len(radar_url_tests)
        
        print(f"Total URLs tested: {total_count}")
        print(f"Accessible URLs: {accessible_count}")
        print(f"Success rate: {(accessible_count/total_count*100):.1f}%" if total_count > 0 else "No URLs tested")
        
        if accessible_count == 0:
            print("🚨 CRITICAL: NO RADAR URLS ARE ACCESSIBLE - This explains why no visual radar data appears!")
        elif accessible_count < total_count:
            print(f"⚠️  WARNING: {total_count - accessible_count} radar URLs are not accessible")
        else:
            print("✅ All radar URLs are accessible")
        
        return all_tests_passed

    def test_tornado_analysis(self, station_id="KEAX"):
        """Test AI tornado analysis endpoint (CRITICAL FEATURE)"""
        print(f"\n🎯 CRITICAL TEST: AI Tornado Analysis for {station_id}")
        success, data = self.run_test(f"AI Tornado Analysis for {station_id}", "POST", 
                                    "tornado-analysis", 
                                    params={"station_id": station_id, "data_type": "reflectivity"})
        
        if success and data:
            print("   🤖 AI Analysis Response received!")
            if 'ai_analysis' in data:
                analysis_preview = data['ai_analysis'][:150] + "..." if len(data['ai_analysis']) > 150 else data['ai_analysis']
                print(f"   AI Response Preview: {analysis_preview}")
            
            if 'alert' in data:
                alert = data['alert']
                print(f"   Alert Created: {alert.get('alert_type', 'N/A')} - Confidence: {alert.get('confidence', 'N/A')}%")
        
        return success, data

    def test_tornado_alerts(self):
        """Test tornado alerts endpoint"""
        return self.run_test("Get Tornado Alerts", "GET", "tornado-alerts")

    def test_subscription_system(self):
        """Test subscription system"""
        user_id = "user123"
        
        # Test get subscription
        print(f"\n👤 Testing Subscription System for {user_id}")
        success1, sub_data = self.run_test(f"Get Subscription for {user_id}", "GET", f"subscription/{user_id}")
        
        if success1 and sub_data:
            current_tier = sub_data.get('tier', 'unknown')
            print(f"   Current tier: {current_tier}")
            
            # Test upgrade if currently free
            if current_tier == 'free':
                success2, upgrade_data = self.run_test(f"Upgrade Subscription for {user_id}", "POST", 
                                                     f"subscription/{user_id}/upgrade")
                
                if success2:
                    # Verify upgrade worked
                    time.sleep(1)  # Brief delay
                    success3, new_sub_data = self.run_test(f"Verify Upgrade for {user_id}", "GET", 
                                                         f"subscription/{user_id}")
                    
                    if success3 and new_sub_data:
                        new_tier = new_sub_data.get('tier', 'unknown')
                        print(f"   New tier after upgrade: {new_tier}")
                        
                        if new_tier == 'premium':
                            print("   ✅ Subscription upgrade successful!")
                        else:
                            print("   ⚠️  Subscription upgrade may not have persisted")
                
                return success2, upgrade_data
        
        return success1, sub_data

    def test_ai_chat(self):
        """Test AI chat endpoint"""
        test_message = "What are the current weather conditions and tornado risks?"
        return self.run_test("AI Chat", "POST", "chat", 
                           params={"message": test_message, "user_id": "user123"})

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🌪️  Storm Oracle Backend API Test Suite")
        print("=" * 50)
        
        # Test basic connectivity
        self.test_root_endpoint()
        
        # Test radar station management
        success, stations_data = self.test_radar_stations()
        
        # Get a test station for further tests
        test_station = "KEAX"  # Default
        if success and stations_data and isinstance(stations_data, list) and len(stations_data) > 0:
            test_station = stations_data[0].get('station_id', 'KEAX')
        
        # Test radar data (basic)
        self.test_radar_data(test_station)
        
        # Test COMPREHENSIVE radar data for visualization issue
        self.test_radar_data_comprehensive()
        
        # Test CRITICAL AI tornado analysis
        self.test_tornado_analysis(test_station)
        
        # Test alerts
        self.test_tornado_alerts()
        
        # Test subscription system
        self.test_subscription_system()
        
        # Test AI chat
        self.test_ai_chat()
        
        # Print final results
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Show failed tests
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        # Show critical issues
        critical_failures = [r for r in self.test_results if not r['success'] and 
                           ('tornado-analysis' in r['test'].lower() or 'subscription' in r['test'].lower())]
        
        if critical_failures:
            print(f"\n🚨 CRITICAL FAILURES:")
            for test in critical_failures:
                print(f"   • {test['test']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = StormOracleAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n💥 Test suite crashed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())