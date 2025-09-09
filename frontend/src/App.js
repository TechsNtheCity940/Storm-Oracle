import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";
import { MapPin, AlertTriangle, Bot, Zap, Cloud, Target, Shield, Activity, Crown, User, Settings, CreditCard, LogOut, Menu, X } from "lucide-react";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "./components/ui/alert";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "./components/ui/dialog";
import { Input } from "./components/ui/input";
import { toast } from "sonner"; 
import { Toaster } from "./components/ui/sonner";
import InteractiveRadarMap from "./components/InteractiveRadarMap";
import PaymentPlan from "./components/PaymentPlan";
import PaymentSuccess from "./components/PaymentSuccess"; 

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  // Application state
  const [currentView, setCurrentView] = useState('radar'); // radar, pricing, account, login
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  
  // Login/Register state
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ email: '', password: '', full_name: '' });
  const [showLogin, setShowLogin] = useState(true);
  const [authLoading, setAuthLoading] = useState(false);
  const [radarStations, setRadarStations] = useState([]);
  const [selectedStation, setSelectedStation] = useState(null);
  const [radarData, setRadarData] = useState(null);
  const [tornadoAlerts, setTornadoAlerts] = useState([]);
  const [subscription, setSubscription] = useState({ tier: "free", features: [] });
  const [chatMessage, setChatMessage] = useState("");
  const [chatResponse, setChatResponse] = useState("");
  const [radarType, setRadarType] = useState("reflectivity");
  const [loading, setLoading] = useState(false);
  const [stormCells, setStormCells] = useState([]);
  const [monitoringStatus, setMonitoringStatus] = useState({});
  const [showRadarMap, setShowRadarMap] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  // Check for existing authentication on app load
  useEffect(() => {
    const token = localStorage.getItem('storm_oracle_token');
    if (token) {
      getCurrentUser(token);
    }
    
    // Check for payment success redirect
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('session_id')) {
      setCurrentView('payment-success');
    }
  }, []);

  const getCurrentUser = async (token) => {
    try {
      const response = await axios.get(`${API}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setUser(response.data);
      setIsAuthenticated(true);
    } catch (error) {
      console.error('Error getting current user:', error);
      localStorage.removeItem('storm_oracle_token');
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    try {
      const response = await axios.post(`${API}/auth/login`, loginForm);
      const { access_token, user } = response.data;
      
      localStorage.setItem('storm_oracle_token', access_token);
      setUser(user);
      setIsAuthenticated(true);
      setCurrentView('radar');
      toast.success(`Welcome back, ${user.full_name}!`);
    } catch (error) {
      console.error('Login error:', error);
      toast.error('Login failed. Please check your credentials.');
    }
    setAuthLoading(false);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    try {
      const response = await axios.post(`${API}/auth/register`, registerForm);
      toast.success('Registration successful! Please check your email for verification.');
      setShowLogin(true);
      setRegisterForm({ email: '', password: '', full_name: '' });
    } catch (error) {
      console.error('Registration error:', error);
      toast.error('Registration failed. Please try again.');
    }
    setAuthLoading(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('storm_oracle_token');
    setUser(null);
    setIsAuthenticated(false);
    setCurrentView('login');
    toast.success('Logged out successfully');
  };

  const NavigationHeader = () => (
    <header className="bg-slate-900/95 backdrop-blur-sm border-b border-slate-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-white cursor-pointer" onClick={() => setCurrentView('radar')}>
              🌪️ Storm Oracle
            </h1>
            {user && (
              <Badge variant={user.subscription_type === 'admin' ? 'default' : 'secondary'}>
                {user.subscription_type === 'admin' ? 'Admin' : user.subscription_type?.toUpperCase() || 'FREE'}
              </Badge>
            )}
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-6">
            <Button 
              variant="ghost" 
              className="text-white hover:text-blue-400"
              onClick={() => setCurrentView('radar')}
            >
              Radar
            </Button>
            <Button 
              variant="ghost" 
              className="text-white hover:text-blue-400"
              onClick={() => setCurrentView('pricing')}
            >
              Pricing
            </Button>
            {isAuthenticated ? (
              <div className="flex items-center space-x-4">
                <Button 
                  variant="ghost" 
                  className="text-white hover:text-blue-400 flex items-center space-x-2"
                  onClick={() => setCurrentView('account')}
                >
                  <User className="h-4 w-4" />
                  <span>{user?.full_name || 'Account'}</span>
                </Button>
                <Button 
                  variant="ghost" 
                  className="text-white hover:text-red-400 flex items-center space-x-2"
                  onClick={handleLogout}
                >
                  <LogOut className="h-4 w-4" />
                  <span>Logout</span>
                </Button>
              </div>
            ) : (
              <Button 
                className="bg-blue-600 hover:bg-blue-700"
                onClick={() => setCurrentView('login')}
              >
                Login
              </Button>
            )}
          </nav>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setMenuOpen(!menuOpen)}
              className="text-white"
            >
              {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {menuOpen && (
          <div className="md:hidden border-t border-slate-800 py-4">
            <div className="flex flex-col space-y-2">
              <Button 
                variant="ghost" 
                className="text-left text-white hover:text-blue-400 justify-start"
                onClick={() => { setCurrentView('radar'); setMenuOpen(false); }}
              >
                Radar
              </Button>
              <Button 
                variant="ghost" 
                className="text-left text-white hover:text-blue-400 justify-start"
                onClick={() => { setCurrentView('pricing'); setMenuOpen(false); }}
              >
                Pricing
              </Button>
              {isAuthenticated ? (
                <>
                  <Button 
                    variant="ghost" 
                    className="text-left text-white hover:text-blue-400 justify-start"
                    onClick={() => { setCurrentView('account'); setMenuOpen(false); }}
                  >
                    <User className="h-4 w-4 mr-2" />
                    Account
                  </Button>
                  <Button 
                    variant="ghost" 
                    className="text-left text-white hover:text-red-400 justify-start"
                    onClick={handleLogout}
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Logout
                  </Button>
                </>
              ) : (
                <Button 
                  className="bg-blue-600 hover:bg-blue-700 justify-start"
                  onClick={() => { setCurrentView('login'); setMenuOpen(false); }}
                >
                  Login
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  );

  const LoginPage = () => (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-slate-800/95 border-slate-700">
        <CardHeader className="text-center">
          <CardTitle className="text-white text-2xl">
            🌪️ Storm Oracle
          </CardTitle>
          <CardDescription className="text-slate-300">
            {showLogin ? 'Sign in to your account' : 'Create your account'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={showLogin ? handleLogin : handleRegister} className="space-y-4">
            {!showLogin && (
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Full Name
                </label>
                <Input
                  type="text"
                  value={registerForm.full_name}
                  onChange={(e) => setRegisterForm({...registerForm, full_name: e.target.value})}
                  className="bg-slate-700 border-slate-600 text-white"
                  placeholder="Enter your full name"
                  required
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Email
              </label>
              <Input
                type="email"
                value={showLogin ? loginForm.email : registerForm.email}
                onChange={(e) => showLogin ? 
                  setLoginForm({...loginForm, email: e.target.value}) :
                  setRegisterForm({...registerForm, email: e.target.value})
                }
                className="bg-slate-700 border-slate-600 text-white"
                placeholder="Enter your email"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Password
              </label>
              <Input
                type="password"
                value={showLogin ? loginForm.password : registerForm.password}
                onChange={(e) => showLogin ? 
                  setLoginForm({...loginForm, password: e.target.value}) :
                  setRegisterForm({...registerForm, password: e.target.value})
                }
                className="bg-slate-700 border-slate-600 text-white"
                placeholder="Enter your password"
                required
              />
            </div>
            <Button 
              type="submit" 
              className="w-full bg-blue-600 hover:bg-blue-700"
              disabled={authLoading}
            >
              {authLoading ? 'Processing...' : (showLogin ? 'Sign In' : 'Create Account')}
            </Button>
          </form>
          
          <div className="mt-4 text-center">
            <Button
              variant="ghost"
              className="text-blue-400 hover:text-blue-300"
              onClick={() => setShowLogin(!showLogin)}
            >
              {showLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const AccountPage = () => (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Account Settings</h1>
        <p className="text-slate-400">Manage your Storm Oracle account and subscription</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card className="bg-slate-800/95 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center space-x-2">
              <User className="h-5 w-5" />
              <span>Profile Information</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Full Name</label>
              <p className="text-white">{user?.full_name}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Email</label>
              <p className="text-white">{user?.email}</p>
              <Badge variant={user?.email_verified ? 'default' : 'destructive'} className="mt-1">
                {user?.email_verified ? 'Verified' : 'Unverified'}
              </Badge>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Member Since</label>
              <p className="text-white">
                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/95 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center space-x-2">
              <Crown className="h-5 w-5" />
              <span>Subscription</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Current Plan</label>
              <div className="flex items-center space-x-2">
                <Badge variant={user?.subscription_type === 'admin' ? 'default' : 'secondary'}>
                  {user?.subscription_type === 'admin' ? 'Admin' : 
                   user?.subscription_type === 'premium' ? 'Premium' : 'Free'}
                </Badge>
                {user?.subscription_type === 'admin' && (
                  <span className="text-yellow-400 text-sm">Full Access</span>
                )}
              </div>
            </div>
            {user?.subscription_type === 'free' && (
              <div className="mt-4">
                <Button 
                  className="bg-purple-600 hover:bg-purple-700"
                  onClick={() => setCurrentView('pricing')}
                >
                  Upgrade to Premium
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );

  useEffect(() => {
    loadRadarStations();
    loadTornadoAlerts();
    loadUserSubscription();
    loadActiveStorms();
    loadMonitoringStatus();
    loadNationalRadar(); // Load national radar by default
    
    // Auto-refresh active storms every 2 minutes
    const stormInterval = setInterval(loadActiveStorms, 120000);
    const statusInterval = setInterval(loadMonitoringStatus, 60000);
    const radarInterval = setInterval(loadNationalRadar, 300000); // Refresh national radar every 5 minutes
    
    return () => {
      clearInterval(stormInterval);
      clearInterval(statusInterval);
      clearInterval(radarInterval);
    };
  }, []);

  const loadNationalRadar = async () => {
    if (selectedStation) return; // Don't override if user has selected a station
    
    setLoading(true);
    try {
      const radarResponse = await axios.get(`${API}/radar-data/NATIONAL?data_type=${radarType}`);
      setRadarData(radarResponse.data);
      console.log('National radar data loaded:', radarResponse.data);
    } catch (error) {
      console.error("Error loading national radar:", error);
    }
    setLoading(false);
  };

  const loadActiveStorms = async () => {
    try {
      const response = await axios.get(`${API}/active-storms`);
      setStormCells(response.data.active_storms || []);
    } catch (error) {
      console.error("Error loading active storms:", error);
    }
  };

  const loadMonitoringStatus = async () => {
    try {
      const response = await axios.get(`${API}/monitoring-status`);
      setMonitoringStatus(response.data);
    } catch (error) {
      console.error("Error loading monitoring status:", error);
    }
  };

  const handleStormClick = (storm) => {
    console.log("Storm clicked:", storm);
    toast.info(`🌪️ ${storm.stationName}: ${storm.tornadoProbability}% tornado risk`);
  };

  // Reload national radar when radar type changes (but only if no specific station is selected)
  useEffect(() => {
    if (!selectedStation) {
      loadNationalRadar();
    }
  }, [radarType]);

  const loadRadarStations = async () => {
    try {
      const response = await axios.get(`${API}/radar-stations`);
      setRadarStations(response.data);
      toast.success("Radar stations loaded successfully");
    } catch (error) {
      console.error("Error loading radar stations:", error);
      toast.error("Failed to load radar stations");
    }
  };

  const loadTornadoAlerts = async () => {
    try {
      const response = await axios.get(`${API}/tornado-alerts`);
      setTornadoAlerts(response.data);
    } catch (error) {
      console.error("Error loading tornado alerts:", error);
    }
  };

  const loadUserSubscription = async () => {
    try {
      const response = await axios.get(`${API}/subscription/user123`);
      setSubscription(response.data);
    } catch (error) {
      console.error("Error loading subscription:", error);
    }
  };

  const selectRadarStation = async (stationId) => {
    setLoading(true);
    try {
      // Find the full station object from the stations array
      const station = radarStations.find(s => s.station_id === stationId);
      if (!station) {
        throw new Error(`Station ${stationId} not found`);
      }
      
      setSelectedStation(station);
      
      const radarResponse = await axios.get(`${API}/radar-data/${station.station_id}?data_type=${radarType}`);
      setRadarData(radarResponse.data);
      
      toast.success(`Connected to ${station.name} radar`);
    } catch (error) {
      console.error("Error selecting radar station:", error);
      toast.error("Failed to connect to radar station");
    }
    setLoading(false);
  };

  const analyzeForTornadoes = async () => {
    if (!selectedStation) {
      toast.error("Please select a radar station first");
      return;
    }

    setAnalyzing(true);
    try {
      const response = await axios.post(`${API}/tornado-analysis?station_id=${selectedStation.station_id}&data_type=${radarType}`);
      
      toast.success("AI tornado analysis completed!");
      
      // Refresh alerts
      await loadTornadoAlerts();
      
      // Show analysis in dialog or update UI
      console.log("Analysis result:", response.data);
      
    } catch (error) {
      console.error("Error analyzing tornado risk:", error);
      toast.error("Failed to analyze tornado risk");
    }
    setAnalyzing(false);
  };

  const runAdvancedMLAnalysis = async () => {
    if (!selectedStation) {
      toast.error("Please select a radar station first");
      return;
    }

    setAnalyzing(true);
    try {
      toast.info("🚀 Running advanced ML tornado prediction...");
      
      const response = await axios.post(`${API}/ml-tornado-analysis?station_id=${selectedStation.station_id}&data_type=${radarType}`);
      
      const mlPrediction = response.data["🌪️ ADVANCED_ML_PREDICTION"];
      const aiAnalysis = response.data["🤖 AI_CONTEXTUAL_ANALYSIS"];
      
      toast.success(`🌪️ ML Prediction: ${mlPrediction.tornado_probability} tornado risk | Alert: ${mlPrediction.alert_level}`);
      
      // Refresh alerts
      await loadTornadoAlerts();
      
      // Show detailed results
      console.log("🧠 Advanced ML Analysis:", response.data);
      
    } catch (error) {
      console.error("Error in advanced ML analysis:", error);
      toast.error("Advanced ML analysis failed");
    }
    setAnalyzing(false);
  };

  const handleChatSubmit = async () => {
    if (!chatMessage.trim()) return;
    
    if (subscription.tier === "free" && !subscription.features.includes("ai_chatbot")) {
      toast.error("AI Chatbot is available for Premium subscribers only");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/chat`, null, {
        params: {
          message: chatMessage,
          user_id: "user123",
        }
      });
      setChatResponse(response.data.response);
      setChatMessage("");
      toast.success("AI response received");
    } catch (error) {
      console.error("Error chatting with AI:", error);
      toast.error("Failed to get AI response");
    }
    setLoading(false);
  };

  const upgradeSubscription = async () => {
    try {
      await axios.post(`${API}/subscription/user123/upgrade`);
      await loadUserSubscription();
      toast.success("Upgraded to Premium! 🎉");
    } catch (error) {
      console.error("Error upgrading subscription:", error);
      toast.error("Failed to upgrade subscription");
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const getStormIntensityColor = (severity) => {
    if (severity >= 4) return "text-red-600";
    if (severity >= 3) return "text-orange-500";
    if (severity >= 2) return "text-yellow-500";
    return "text-green-500";
  };

  const isPremiumFeature = (feature) => {
    return !subscription.features.includes(feature);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <Toaster position="top-right" />
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-900/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-600 rounded-lg">
                <Target className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Storm Oracle</h1>
                <p className="text-slate-400 text-sm">AI-Powered Tornado Prediction System</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <Badge variant={subscription.tier === "premium" ? "default" : "secondary"}>
                {subscription.tier.charAt(0).toUpperCase() + subscription.tier.slice(1)}
              </Badge>
              
              {subscription.tier === "free" && (
                <Button onClick={upgradeSubscription} variant="outline" className="border-blue-500 text-blue-400 hover:bg-blue-500 hover:text-white">
                  <Zap className="h-4 w-4 mr-2" />
                  Upgrade to Premium
                </Button>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          
          {/* Live Storm Monitoring */}
          <div className="lg:col-span-1 space-y-6">
            <Card className="bg-slate-800/95 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-white flex items-center">
                  <svg className="w-5 h-5 mr-2 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                  </svg>
                  Storm Monitoring System
                </CardTitle>
                <CardDescription className="text-slate-400">
                  AI-powered live storm tracking and analysis
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  {/* Active Threats Counter */}
                  <div className="bg-slate-700/50 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300 text-sm">Active Threats</span>
                      <span className={`font-bold text-lg ${stormCells.length > 0 ? 'text-red-400' : 'text-green-400'}`}>
                        {stormCells.length}
                      </span>
                    </div>
                  </div>

                  {/* Storm Details */}
                  <div className="max-h-48 overflow-y-auto space-y-2">
                    {stormCells.length > 0 ? (
                      stormCells.map((storm, index) => (
                        <div key={index} className="bg-slate-700/30 rounded-lg p-3 border-l-4 border-orange-400">
                          <div className="flex justify-between items-start mb-1">
                            <h4 className="text-white font-semibold text-sm">
                              Storm Cell #{index + 1}
                            </h4>
                            <span className="text-xs text-slate-400">
                              {new Date(storm.timestamp || Date.now()).toLocaleTimeString()}
                            </span>
                          </div>
                          <div className="space-y-1 text-xs">
                            <div className="flex justify-between">
                              <span className="text-slate-400">Location:</span>
                              <span className="text-white">
                                {storm.latitude?.toFixed(2)}°, {storm.longitude?.toFixed(2)}°
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-400">Intensity:</span>
                              <span className={`font-semibold ${
                                storm.intensity > 50 ? 'text-red-400' : 
                                storm.intensity > 30 ? 'text-orange-400' : 'text-yellow-400'
                              }`}>
                                {storm.intensity?.toFixed(0)} dBZ
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-400">Tornado Risk:</span>
                              <span className={`font-semibold ${
                                storm.tornado_probability > 0.7 ? 'text-red-400' : 
                                storm.tornado_probability > 0.4 ? 'text-orange-400' : 'text-green-400'
                              }`}>
                                {((storm.tornado_probability || 0) * 100).toFixed(0)}%
                              </span>
                            </div>
                            {storm.movement && (
                              <div className="flex justify-between">
                                <span className="text-slate-400">Movement:</span>
                                <span className="text-white">
                                  {storm.movement.direction}° at {storm.movement.speed} mph
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-4">
                        <div className="text-green-400 mb-2">
                          <svg className="w-8 h-8 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        </div>
                        <p className="text-slate-400 text-sm">No active storm threats detected</p>
                        <p className="text-slate-500 text-xs mt-1">AI monitoring nationwide</p>
                      </div>
                    )}
                  </div>

                  {/* Monitoring Status */}
                  <div className="bg-slate-700/30 rounded-lg p-2">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400 text-xs">ML System Status</span>
                      <div className="flex items-center">
                        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-2"></div>
                        <span className="text-green-400 text-xs font-semibold">ACTIVE</span>
                      </div>
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      Last scan: {new Date().toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Tornado Alerts */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center">
                  <AlertTriangle className="h-5 w-5 mr-2 text-red-500" />
                  Recent Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {tornadoAlerts.slice(0, 5).map((alert) => (
                    <Alert key={alert.id} className="bg-slate-700 border-slate-600">
                      <AlertTriangle className={`h-4 w-4 ${getStormIntensityColor(alert.severity)}`} />
                      <AlertTitle className="text-white">
                        {alert.alert_type.toUpperCase()} - {alert.station_id}
                      </AlertTitle>
                      <AlertDescription className="text-slate-300 text-xs">
                        Confidence: {alert.confidence}% | {formatTimestamp(alert.timestamp)}
                      </AlertDescription>
                    </Alert>
                  ))}
                  {tornadoAlerts.length === 0 && (
                    <p className="text-slate-400 text-sm text-center py-4">No recent alerts</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Main Interactive Radar Display */}
          <div className="lg:col-span-3 space-y-6">
            
            {/* Radar Controls */}
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="p-4">
                <div className="flex flex-wrap items-center gap-4">
                  <Select value={radarType} onValueChange={setRadarType}>
                    <SelectTrigger className="w-48 bg-slate-700 border-slate-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-600">
                      <SelectItem value="reflectivity" className="text-white">Reflectivity</SelectItem>
                      <SelectItem value="velocity" className="text-white" disabled={isPremiumFeature("advanced_radar")}>
                        Velocity {isPremiumFeature("advanced_radar") && "(Premium)"}
                      </SelectItem>
                    </SelectContent>
                  </Select>

                  <Button 
                    onClick={analyzeForTornadoes} 
                    disabled={!selectedStation || analyzing}
                    className="bg-red-600 hover:bg-red-700 text-white mr-2"
                  >
                    {analyzing ? (
                      <Activity className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Bot className="h-4 w-4 mr-2" />
                    )}
                    {analyzing ? "Analyzing..." : "AI Tornado Analysis"}
                  </Button>

                  <Button 
                    onClick={runAdvancedMLAnalysis} 
                    disabled={!selectedStation || analyzing}
                    className="bg-purple-600 hover:bg-purple-700 text-white"
                  >
                    {analyzing ? (
                      <Activity className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Zap className="h-4 w-4 mr-2" />
                    )}
                    {analyzing ? "Processing..." : "🌪️ Advanced ML Analysis"}
                  </Button>

                  <div className="flex items-center space-x-2 text-white ml-auto">
                    <div className={`w-2 h-2 rounded-full ${monitoringStatus.system_status?.monitoring_active ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                    <span className="text-sm">
                      {monitoringStatus.system_status?.monitoring_active ? 'Auto-Monitoring Active' : 'Manual Mode'}
                    </span>
                    {stormCells.length > 0 && (
                      <Badge variant="destructive" className="ml-2">
                        {stormCells.length} Active Storms
                      </Badge>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Interactive Radar Map */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center justify-between">
                  <span>🌪️ Live Interactive Radar - Storm Oracle</span>
                  <div className="flex items-center space-x-2">
                    <Badge variant="outline" className="text-green-400 border-green-400">
                      {radarStations.length} NEXRAD Stations
                    </Badge>
                    {monitoringStatus.active_storm_summary && (
                      <Badge variant="destructive">
                        {monitoringStatus.active_storm_summary.total_storms} Active Threats
                      </Badge>
                    )}
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="h-[600px] relative">
                  <InteractiveRadarMap
                    radarStations={radarStations}
                    selectedStation={selectedStation}
                    onStationSelect={selectRadarStation}
                    stormCells={stormCells}
                    onStormClick={handleStormClick}
                  />
                </div>
              </CardContent>
            </Card>

            {/* AI Chat (Premium Feature) */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center justify-between">
                  <div className="flex items-center">
                    <Bot className="h-5 w-5 mr-2" />
                    AI Weather Assistant
                  </div>
                  {isPremiumFeature("ai_chatbot") && (
                    <Badge variant="outline" className="text-orange-400 border-orange-400">Premium</Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex space-x-2">
                  <Input
                    placeholder={isPremiumFeature("ai_chatbot") ? "Upgrade to Premium to chat with AI..." : "Ask about weather conditions..."}
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    disabled={isPremiumFeature("ai_chatbot") || loading}
                    className="bg-slate-700 border-slate-600 text-white placeholder-slate-400"
                    onKeyPress={(e) => e.key === 'Enter' && handleChatSubmit()}
                  />
                  <Button 
                    onClick={handleChatSubmit} 
                    disabled={isPremiumFeature("ai_chatbot") || loading || !chatMessage.trim()}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    <Bot className="h-4 w-4" />
                  </Button>
                </div>
                
                {chatResponse && (
                  <div className="p-4 bg-slate-700 rounded-lg">
                    <p className="text-white text-sm">{chatResponse}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Features Overview */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold text-white mb-6 text-center">Advanced Tornado Prediction Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="bg-slate-800 border-slate-700 text-center">
              <CardContent className="p-6">
                <Target className="h-8 w-8 mx-auto mb-3 text-blue-500" />
                <h3 className="text-white font-semibold">Hook Echo Detection</h3>
                <p className="text-slate-400 text-sm mt-2">AI identifies hook-shaped radar signatures indicating tornado formation</p>
              </CardContent>
            </Card>
            
            <Card className="bg-slate-800 border-slate-700 text-center">
              <CardContent className="p-6">
                <Activity className="h-8 w-8 mx-auto mb-3 text-green-500" />
                <h3 className="text-white font-semibold">Velocity Couplets</h3>
                <p className="text-slate-400 text-sm mt-2">Detect rotating air masses through Doppler velocity analysis</p>
              </CardContent>
            </Card>
            
            <Card className="bg-slate-800 border-slate-700 text-center">
              <CardContent className="p-6">
                <AlertTriangle className="h-8 w-8 mx-auto mb-3 text-red-500" />
                <h3 className="text-white font-semibold">Early Warning System</h3>
                <p className="text-slate-400 text-sm mt-2">Advanced predictions give critical time for safety preparations</p>
              </CardContent>
            </Card>
            
            <Card className="bg-slate-800 border-slate-700 text-center">
              <CardContent className="p-6">
                <Shield className="h-8 w-8 mx-auto mb-3 text-purple-500" />
                <h3 className="text-white font-semibold">Path Prediction</h3>
                <p className="text-slate-400 text-sm mt-2">AI forecasts tornado paths and touchdown locations</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;