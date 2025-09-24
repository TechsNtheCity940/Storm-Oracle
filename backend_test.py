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
    def __init__(self, base_url="https://weather-radar-ai.preview.emergentagent.com"):
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

    def test_active_storms(self):
        """Test active storms monitoring endpoint"""
        return self.run_test("Get Active Storms", "GET", "active-storms")

    def test_monitoring_status(self):
        """Test monitoring status endpoint"""
        return self.run_test("Get Monitoring Status", "GET", "monitoring-status")

    def test_ml_tornado_analysis(self, station_id="KEAX"):
        """Test advanced ML tornado analysis endpoint (PREMIUM FEATURE)"""
        print(f"\n🚀 PREMIUM TEST: Advanced ML Tornado Analysis for {station_id}")
        success, data = self.run_test(f"Advanced ML Tornado Analysis for {station_id}", "POST", 
                                    "ml-tornado-analysis", 
                                    params={"station_id": station_id, "data_type": "reflectivity"})
        
        if success and data:
            print("   🧠 Advanced ML Analysis Response received!")
            if '🌪️ ADVANCED_ML_PREDICTION' in data:
                ml_prediction = data['🌪️ ADVANCED_ML_PREDICTION']
                print(f"   Tornado Probability: {ml_prediction.get('tornado_probability', 'N/A')}")
                print(f"   Most Likely EF Scale: {ml_prediction.get('most_likely_ef_scale', 'N/A')}")
                print(f"   Alert Level: {ml_prediction.get('alert_level', 'N/A')}")
            
            if '🤖 AI_CONTEXTUAL_ANALYSIS' in data:
                ai_analysis = data['🤖 AI_CONTEXTUAL_ANALYSIS']
                analysis_preview = ai_analysis[:150] + "..." if len(ai_analysis) > 150 else ai_analysis
                print(f"   AI Contextual Analysis Preview: {analysis_preview}")
        
        return success, data

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
        
        # Test radar data
        self.test_radar_data(test_station)
        
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