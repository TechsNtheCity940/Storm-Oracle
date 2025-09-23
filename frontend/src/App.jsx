import 'leaflet/dist/leaflet.css';
import React, { useEffect, useMemo, useState, useCallback } from "react";
import "leaflet/dist/leaflet.css";
import "./App.css";
import axios from "axios";

import {
  MapPin,
  AlertTriangle,
  User,
  LogOut,
  Menu,
  X,
  Crown,
} from "lucide-react";

import { Button } from "./components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { toast } from "sonner";
import { Toaster } from "./components/ui/sonner";

import InteractiveRadarMap from "./components/InteractiveRadarMap";
import PaymentPlan from "./components/PaymentPlan";
import PaymentSuccess from "./components/PaymentSuccess";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8001";
const API = `${BACKEND_URL}/api`;

function App() {
  // top-level UI state
  const [currentView, setCurrentView] = useState("radar"); // "radar" | "pricing" | "account" | "login" | "payment-success"
  const [menuOpen, setMenuOpen] = useState(false);

  // auth state
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [showLogin, setShowLogin] = useState(true);
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [registerForm, setRegisterForm] = useState({
    email: "",
    password: "",
    full_name: "",
  });

  // data state
  const [radarStations, setRadarStations] = useState([]);
  const [selectedStation, setSelectedStation] = useState(null);
  const [radarData, setRadarData] = useState(null);
  const [tornadoAlerts, setTornadoAlerts] = useState([]);
  const [subscription, setSubscription] = useState({
    tier: "free",
    features: [],
  });
  const [stormCells, setStormCells] = useState([]);
  const [monitoringStatus, setMonitoringStatus] = useState(null);

  // UI helpers
  const [radarType, setRadarType] = useState("reflectivity");
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  // --- Auth bootstrap ---
  useEffect(() => {
    try {
      const token = localStorage.getItem("storm_oracle_token");
      if (token) {
        axios
          .get(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          })
          .then((res) => {
            setUser(res.data || null);
            setIsAuthenticated(true);
          })
          .catch(() => {
            localStorage.removeItem("storm_oracle_token");
            setIsAuthenticated(false);
            setUser(null);
          });
      }
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get("session_id")) {
        setCurrentView("payment-success");
      }
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Initial data loads + polling ---
  const loadRadarStations = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/radar-stations`);
      setRadarStations(res.data || []);
    } catch (e) {
      console.error("radar-stations error", e);
      toast.error("Failed to load radar stations");
    }
  }, []);

  const loadTornadoAlerts = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/tornado-alerts`);
      setTornadoAlerts(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      console.error("tornado-alerts error", e);
    }
  }, []);

  const loadActiveStorms = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/active-storms`);
      setStormCells(res.data?.active_storms || []);
    } catch (e) {
      console.error("active-storms error", e);
    }
  }, []);

  const loadMonitoringStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/monitoring-status`);
      setMonitoringStatus(res.data || null);
    } catch (e) {
      console.error("monitoring-status error", e);
    }
  }, []);

  const loadUserSubscription = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/subscription/user123`);
      setSubscription(res.data || { tier: "free", features: [] });
    } catch (e) {
      console.error("subscription error", e);
    }
  }, []);

  const loadNationalRadar = useCallback(async () => {
    if (selectedStation) return; // don’t override user-selected station
    setLoading(true);
    try {
      const res = await axios.get(
        `${API}/radar-data/NATIONAL?data_type=${radarType}`
      );
      setRadarData(res.data || null);
    } catch (e) {
      console.error("national radar error", e);
    } finally {
      setLoading(false);
    }
  }, [radarType, selectedStation]);

  useEffect(() => {
    loadRadarStations();
    loadTornadoAlerts();
    loadUserSubscription();
    loadActiveStorms();
    loadMonitoringStatus();
    loadNationalRadar();

    const stormIv = setInterval(loadActiveStorms, 120000);
    const statusIv = setInterval(loadMonitoringStatus, 60000);
    const radarIv = setInterval(loadNationalRadar, 300000);

    return () => {
      clearInterval(stormIv);
      clearInterval(statusIv);
      clearInterval(radarIv);
    };
  }, [
    loadRadarStations,
    loadTornadoAlerts,
    loadUserSubscription,
    loadActiveStorms,
    loadMonitoringStatus,
    loadNationalRadar,
  ]);

  // reload national view when radar type changes (if no station selected)
  useEffect(() => {
    if (!selectedStation) {
      loadNationalRadar();
    }
  }, [radarType, selectedStation, loadNationalRadar]);

  // --- Auth handlers ---
  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    try {
      const { data } = await axios.post(`${API}/auth/login`, loginForm);
      localStorage.setItem("storm_oracle_token", data.access_token);
      setUser(data.user);
      setIsAuthenticated(true);
      setCurrentView("radar");
      toast.success(`Welcome back, ${data.user?.full_name || "user"}!`);
    } catch (err) {
      toast.error("Login failed. Check your credentials.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    try {
      await axios.post(`${API}/auth/register`, registerForm);
      toast.success("Registration successful! Please check your email.");
      setShowLogin(true);
      setRegisterForm({ email: "", password: "", full_name: "" });
    } catch {
      toast.error("Registration failed. Please try again.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("storm_oracle_token");
    setUser(null);
    setIsAuthenticated(false);
    setCurrentView("login");
    toast.success("Logged out");
  };

  // --- Radar station selection ---
  const selectRadarStation = async (stationId) => {
    setLoading(true);
    try {
      const station = radarStations.find((s) => s.station_id === stationId);
      if (!station) throw new Error(`Station ${stationId} not found`);
      setSelectedStation(station);

      const res = await axios.get(
        `${API}/radar-data/${station.station_id}?data_type=${radarType}`
      );
      setRadarData(res.data || null);
      toast.success(`Connected to ${station.name} radar`);
    } catch (e) {
      console.error("select station error", e);
      toast.error("Failed to connect to radar station");
    } finally {
      setLoading(false);
    }
  };

  // --- ML actions ---
  const analyzeForTornadoes = async () => {
    if (!selectedStation) {
      toast.error("Please select a radar station first");
      return;
    }
    setAnalyzing(true);
    try {
      await axios.post(
        `${API}/tornado-analysis?station_id=${selectedStation.station_id}&data_type=${radarType}`
      );
      toast.success("AI tornado analysis completed!");
      await loadTornadoAlerts();
    } catch (e) {
      console.error("basic analysis error", e);
      toast.error("Failed to analyze tornado risk");
    } finally {
      setAnalyzing(false);
    }
  };

  const runAdvancedMLAnalysis = async () => {
    if (!selectedStation) {
      toast.error("Please select a radar station first");
      return;
    }
    setAnalyzing(true);
    try {
      toast.info("🚀 Running advanced ML tornado prediction...");
      const res = await axios.post(
        `${API}/ml-tornado-analysis?station_id=${selectedStation.station_id}&data_type=${radarType}`
      );
      const mlPrediction = res.data?.["🌪️ ADVANCED_ML_PREDICTION"];
      if (mlPrediction) {
        toast.success(
          `🌪️ ML: ${mlPrediction.tornado_probability} | ${mlPrediction.alert_level}`
        );
      } else {
        toast.success("Advanced ML analysis completed");
      }
      await loadTornadoAlerts();
    } catch (e) {
      console.error("advanced analysis error", e);
      toast.error("Advanced ML analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const upgradeSubscription = async () => {
    try {
      await axios.post(`${API}/subscription/user123/upgrade`);
      await loadUserSubscription();
      toast.success("Upgraded to Premium! 🎉");
    } catch {
      toast.error("Failed to upgrade subscription");
    }
  };

  // --- Small utils ---
  const formatTime = (ts) => {
    if (!ts) return "—";
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return String(ts);
    }
  };

  const threatBadge = (level) => {
    if (!level) return <Badge variant="secondary">Normal</Badge>;
    const t = String(level).toUpperCase();
    if (t.includes("EMERGENCY"))
      return <Badge variant="destructive">Emergency</Badge>;
    if (t.includes("WARNING"))
      return <Badge className="bg-orange-600 hover:bg-orange-600">Warning</Badge>;
    if (t.includes("WATCH"))
      return <Badge className="bg-yellow-600 hover:bg-yellow-600">Watch</Badge>;
    return <Badge variant="secondary">Normal</Badge>;
  };

  // --- Views ---
  const NavigationHeader = useMemo(
    () => (
      <header className="bg-slate-900/95 backdrop-blur-sm border-b border-slate-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <h1
                className="text-2xl font-bold text-white cursor-pointer"
                onClick={() => setCurrentView("radar")}
              >
                🌪️ Storm Oracle
              </h1>
              {user && (
                <Badge
                  variant={
                    user.subscription_type === "admin" ? "default" : "secondary"
                  }
                >
                  {user.subscription_type === "admin"
                    ? "Admin"
                    : user.subscription_type?.toUpperCase() || "FREE"}
                </Badge>
              )}
            </div>

            {/* Desktop nav */}
            <nav className="hidden md:flex items-center space-x-6">
              <Button
                variant="ghost"
                className="text-white hover:text-blue-400"
                onClick={() => setCurrentView("radar")}
              >
                Radar
              </Button>
              <Button
                variant="ghost"
                className="text-white hover:text-blue-400"
                onClick={() => setCurrentView("pricing")}
              >
                Pricing
              </Button>
              {isAuthenticated ? (
                <div className="flex items-center space-x-4">
                  <Button
                    variant="ghost"
                    className="text-white hover:text-blue-400 flex items-center space-x-2"
                    onClick={() => setCurrentView("account")}
                  >
                    <User className="h-4 w-4" />
                    <span>{user?.full_name || "Account"}</span>
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
                  onClick={() => setCurrentView("login")}
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
                onClick={() => setMenuOpen((s) => !s)}
                className="text-white"
              >
                {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </Button>
            </div>
          </div>

          {/* Mobile nav */}
          {menuOpen && (
            <div className="md:hidden border-t border-slate-800 py-4">
              <div className="flex flex-col space-y-2">
                <Button
                  variant="ghost"
                  className="text-left text-white hover:text-blue-400 justify-start"
                  onClick={() => {
                    setCurrentView("radar");
                    setMenuOpen(false);
                  }}
                >
                  Radar
                </Button>
                <Button
                  variant="ghost"
                  className="text-left text-white hover:text-blue-400 justify-start"
                  onClick={() => {
                    setCurrentView("pricing");
                    setMenuOpen(false);
                  }}
                >
                  Pricing
                </Button>
                {isAuthenticated ? (
                  <>
                    <Button
                      variant="ghost"
                      className="text-left text-white hover:text-blue-400 justify-start"
                      onClick={() => {
                        setCurrentView("account");
                        setMenuOpen(false);
                      }}
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
                    onClick={() => {
                      setCurrentView("login");
                      setMenuOpen(false);
                    }}
                  >
                    Login
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>
      </header>
    ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user, isAuthenticated, menuOpen]
  );

  const LoginPage = (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-slate-800/95 border-slate-700">
        <CardHeader className="text-center">
          <CardTitle className="text-white text-2xl">🌪️ Storm Oracle</CardTitle>
          <CardDescription className="text-slate-300">
            {showLogin ? "Sign in to your account" : "Create your account"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={showLogin ? handleLogin : handleRegister}
            className="space-y-4"
            noValidate
            autoComplete="on"
          >
            {!showLogin && (
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  value={registerForm.full_name}
                  onChange={(e) =>
                    setRegisterForm((p) => ({ ...p, full_name: e.target.value }))
                  }
                  className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white"
                  placeholder="Enter your full name"
                  required
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Email
              </label>
              <input
                type="email"
                value={showLogin ? loginForm.email : registerForm.email}
                onChange={(e) => {
                  const v = e.target.value;
                  if (showLogin) setLoginForm((p) => ({ ...p, email: v }));
                  else setRegisterForm((p) => ({ ...p, email: v }));
                }}
                className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white"
                placeholder="you@example.com"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Password
              </label>
              <input
                type="password"
                value={showLogin ? loginForm.password : registerForm.password}
                onChange={(e) => {
                  const v = e.target.value;
                  if (showLogin) setLoginForm((p) => ({ ...p, password: v }));
                  else setRegisterForm((p) => ({ ...p, password: v }));
                }}
                className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white"
                placeholder="Enter your password"
                required
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-700"
              disabled={authLoading}
            >
              {authLoading
                ? "Processing..."
                : showLogin
                ? "Sign In"
                : "Create Account"}
            </Button>
          </form>

          <div className="mt-4 text-center">
            <Button
              variant="ghost"
              className="text-blue-400 hover:text-blue-300"
              onClick={() => {
                setShowLogin((s) => !s);
                setLoginForm({ email: "", password: "" });
                setRegisterForm({ email: "", password: "", full_name: "" });
              }}
            >
              {showLogin
                ? "Don't have an account? Sign up"
                : "Already have an account? Sign in"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const AccountPage = (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Account Settings</h1>
        <p className="text-slate-400">Manage your Storm Oracle account</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card className="bg-slate-800/95 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center space-x-2">
              <User className="h-5 w-5" />
              <span>Profile</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Full Name
              </label>
              <p className="text-white">{user?.full_name || "—"}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Email
              </label>
              <p className="text-white">{user?.email || "—"}</p>
              <Badge
                variant={user?.email_verified ? "default" : "destructive"}
                className="mt-1"
              >
                {user?.email_verified ? "Verified" : "Unverified"}
              </Badge>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Member Since
              </label>
              <p className="text-white">
                {user?.created_at
                  ? new Date(user.created_at).toLocaleDateString()
                  : "N/A"}
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
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Current Plan
              </label>
              <div className="flex items-center space-x-2">
                <Badge
                  variant={
                    user?.subscription_type === "admin" ? "default" : "secondary"
                  }
                >
                  {user?.subscription_type === "admin"
                    ? "Admin"
                    : user?.subscription_type === "premium"
                    ? "Premium"
                    : "Free"}
                </Badge>
              </div>
            </div>
            {subscription?.tier !== "premium" && (
              <div className="mt-4">
                <Button
                  className="bg-purple-600 hover:bg-purple-700"
                  onClick={upgradeSubscription}
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

  // --- Main radar view ---
  const RadarView = (
    <div className="flex-1 overflow-hidden">
      <div className="h-full flex">
        {/* Left sidebar */}
        <div className="w-96 bg-slate-900/95 backdrop-blur-sm border-r border-slate-800 overflow-y-auto">
          <div className="p-4 space-y-6">
            {/* Monitoring card */}
            <Card className="bg-slate-800/95 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-white flex items-center">
                  <svg
                    className="w-5 h-5 mr-2 text-yellow-400"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Storm Monitoring
                </CardTitle>
                <CardDescription className="text-slate-400">
                  AI-powered live tracking & analysis
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-slate-700/50 rounded-lg p-3 flex items-center justify-between">
                  <span className="text-slate-300 text-sm">Active Threats</span>
                  <span
                    className={`font-bold text-lg ${
                      (stormCells?.length || 0) > 0
                        ? "text-red-400"
                        : "text-green-400"
                    }`}
                  >
                    {stormCells?.length || 0}
                  </span>
                </div>

                {/* storms list */}
                <div className="max-h-48 overflow-y-auto space-y-2">
                  {(stormCells || []).length > 0 ? (
                    stormCells.map((s, idx) => (
                      <div
                        key={`${s.stationId}-${idx}`}
                        className="bg-slate-700/30 rounded-lg p-3 border-l-4 border-orange-400"
                      >
                        <div className="flex justify-between items-start mb-1">
                          <h4 className="text-white font-semibold text-sm">
                            {s.stationName || s.stationId || `Storm #${idx + 1}`}
                          </h4>
                          <span className="text-xs text-slate-400">
                            {formatTime(s.lastUpdated)}
                          </span>
                        </div>
                        <div className="space-y-1 text-xs">
                          <div className="flex justify-between">
                            <span className="text-slate-400">Location:</span>
                            <span className="text-white">
                              {Number(s.latitude)?.toFixed(2)}°,{" "}
                              {Number(s.longitude)?.toFixed(2)}°
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-400">Tornado Risk:</span>
                            <span
                              className={`font-semibold ${
                                s.tornadoProbability >= 70
                                  ? "text-red-400"
                                  : s.tornadoProbability >= 40
                                  ? "text-orange-400"
                                  : "text-green-400"
                              }`}
                            >
                              {s.tornadoProbability ?? 0}%
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-400">Alert:</span>
                            <span className="text-white">
                              {threatBadge(s.alertLevel)}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-4">
                      <div className="text-green-400 mb-2">
                        <svg className="w-8 h-8 mx-auto" viewBox="0 0 20 20" fill="currentColor">
                          <path
                            fillRule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                      <p className="text-slate-400 text-sm">
                        No active storm threats detected
                      </p>
                      <p className="text-slate-500 text-xs mt-1">
                        AI monitoring nationwide
                      </p>
                    </div>
                  )}
                </div>

                {/* system status */}
                <div className="bg-slate-700/30 rounded-lg p-2">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 text-xs">ML System</span>
                    <div className="flex items-center">
                      <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-2"></div>
                      <span className="text-green-400 text-xs font-semibold">
                        {monitoringStatus?.system_status?.monitoring_active
                          ? "ACTIVE"
                          : "STANDBY"}
                      </span>
                    </div>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    Last check: {new Date().toLocaleTimeString()}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recent alerts */}
            <Card className="bg-slate-800/95 border-slate-700 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-white flex items-center">
                  <AlertTriangle className="w-5 h-5 mr-2 text-red-400" />
                  Recent Alerts
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {(tornadoAlerts || []).length > 0 ? (
                  tornadoAlerts.slice(0, 5).map((a, i) => (
                    <div key={`${a.station_id}-${i}`} className="bg-slate-700/30 rounded-lg p-3">
                      <div className="flex justify-between items-start mb-1">
                        <span className="text-white font-semibold text-sm">
                          {a.station_id}
                        </span>
                        <span className="text-xs">{threatBadge(a.alert_type)}</span>
                      </div>
                      <p className="text-slate-300 text-xs mb-2">
                        {a.message || "Automated alert"}
                      </p>
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-400">Confidence:</span>
                        <span className="text-yellow-400">
                          {Math.round(Number(a.confidence) || 0)}%
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-slate-400 text-sm">No recent alerts</p>
                )}
              </CardContent>
            </Card>

            {/* Actions */}
            <div className="space-y-2">
              <Button
                className="w-full bg-blue-600 hover:bg-blue-700"
                disabled={!selectedStation || analyzing}
                onClick={analyzeForTornadoes}
              >
                Run AI Tornado Analysis
              </Button>
              <Button
                className="w-full bg-purple-600 hover:bg-purple-700"
                disabled={!selectedStation || analyzing}
                onClick={runAdvancedMLAnalysis}
              >
                Advanced ML Prediction
              </Button>
            </div>
          </div>
        </div>

        {/* Map / main panel */}
        <div className="flex-1 relative">
          <InteractiveRadarMap
            selectedStation={selectedStation}
            onStationSelect={selectRadarStation}
            stormCells={stormCells}
            onStormClick={(s) =>
              toast.info(
                `🌪️ ${s.stationName || s.stationId}: ${s.tornadoProbability}% risk`
              )
            }
            radarStations={radarStations}
            radarData={radarData}
            tornadoData={tornadoAlerts}
            onTornadoClick={(t) =>
              toast.info(
                `🌪️ ${t.alert_type}: severity ${t.severity || 1} ${
                  t.confirmed ? "confirmed" : "predicted"
                }`
              )
            }
          />
          {/* Simple radar type toggle (optional) */}
          <div className="absolute top-4 right-4 bg-slate-900/80 border border-slate-700 rounded-lg p-2 flex gap-2">
            <Button
              size="sm"
              variant={radarType === "reflectivity" ? "default" : "secondary"}
              onClick={() => setRadarType("reflectivity")}
            >
              Reflectivity
            </Button>
            <Button
              size="sm"
              variant={radarType === "velocity" ? "default" : "secondary"}
              onClick={() => setRadarType("velocity")}
            >
              Velocity
            </Button>
          </div>

          {loading && (
            <div className="absolute inset-0 bg-black/30 grid place-items-center">
              <div className="text-slate-200">Loading radar…</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // --- View router ---
  let body = null;
  if (currentView === "payment-success") body = <PaymentSuccess />;
  else if (!isAuthenticated && currentView !== "pricing") body = LoginPage;
  else {
    switch (currentView) {
      case "pricing":
        body = <PaymentPlan user={user} onSubscriptionUpdate={() => {}} />;
        break;
      case "account":
        body = AccountPage;
        break;
      case "radar":
      default:
        body = RadarView;
        break;
    }
  }

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      {NavigationHeader}
      {body}
      <Toaster />
    </div>
  );
}

export default App;