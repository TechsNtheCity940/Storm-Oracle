import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";
import { MapPin, AlertTriangle, Bot, Zap, Cloud, Target, Shield, Activity } from "lucide-react";
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

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
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

  useEffect(() => {
    loadRadarStations();
    loadTornadoAlerts();
    loadUserSubscription();
    loadActiveStorms();
    loadMonitoringStatus();
    
    // Auto-refresh active storms every 2 minutes
    const stormInterval = setInterval(loadActiveStorms, 120000);
    const statusInterval = setInterval(loadMonitoringStatus, 60000);
    
    return () => {
      clearInterval(stormInterval);
      clearInterval(statusInterval);
    };
  }, []);

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

  const selectRadarStation = async (station) => {
    setLoading(true);
    try {
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
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-100">
      <Toaster position="top-right" />
      {/* Modern Header */}
      <header className="border-b border-blue-100 bg-white/90 backdrop-blur-md shadow-sm">
        <div className="container mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-gradient-to-br from-blue-500 to-sky-600 rounded-2xl shadow-lg">
                <Target className="h-7 w-7 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-sky-700 bg-clip-text text-transparent">
                  Storm Oracle
                </h1>
                <p className="text-slate-600 text-sm font-medium">AI-Powered Tornado Prediction System</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <Badge 
                variant={subscription.tier === "premium" ? "default" : "secondary"}
                className={`px-3 py-1 rounded-full font-medium ${
                  subscription.tier === "premium" 
                    ? "bg-gradient-to-r from-blue-500 to-sky-600 text-white" 
                    : "bg-slate-100 text-slate-700"
                }`}
              >
                {subscription.tier.charAt(0).toUpperCase() + subscription.tier.slice(1)}
              </Badge>
              
              {subscription.tier === "free" && (
                <Button 
                  onClick={upgradeSubscription} 
                  className="bg-gradient-to-r from-blue-500 to-sky-600 hover:from-blue-600 hover:to-sky-700 text-white rounded-xl px-6 py-2 shadow-lg hover:shadow-xl transition-all duration-300"
                >
                  <Zap className="h-4 w-4 mr-2" />
                  Upgrade to Premium
                </Button>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          
          {/* Radar Station Selection */}
          <div className="lg:col-span-1 space-y-8">
            <Card className="bg-white/80 backdrop-blur-sm border border-blue-100 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300">
              <CardHeader className="pb-4">
                <CardTitle className="text-slate-700 flex items-center text-lg font-semibold">
                  <div className="p-2 bg-gradient-to-br from-blue-100 to-sky-100 rounded-xl mr-3">
                    <MapPin className="h-5 w-5 text-blue-600" />
                  </div>
                  Radar Stations
                </CardTitle>
                <CardDescription className="text-slate-500 font-medium">
                  Select a NEXRAD station to monitor
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <Select onValueChange={selectRadarStation} disabled={loading}>
                  <SelectTrigger className="bg-white border-blue-200 text-slate-700 rounded-xl hover:border-blue-300 focus:ring-2 focus:ring-blue-200 transition-all">
                    <SelectValue placeholder="Choose radar station..." />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-blue-100 rounded-xl shadow-xl">
                    {radarStations.map((station) => (
                      <SelectItem key={station.station_id} value={station.station_id} className="text-slate-700 hover:bg-blue-50 rounded-lg">
                        {station.station_id} - {station.name}, {station.state}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {selectedStation && (
                  <div className="p-5 bg-gradient-to-br from-blue-50 to-sky-50 border border-blue-100 rounded-2xl">
                    <h3 className="text-slate-700 font-bold text-lg">{selectedStation.name}</h3>
                    <p className="text-blue-600 text-sm font-semibold">{selectedStation.station_id}</p>
                    <p className="text-slate-500 text-sm mt-2">
                      📍 {selectedStation.latitude.toFixed(4)}°, {selectedStation.longitude.toFixed(4)}°
                    </p>
                    <p className="text-slate-500 text-sm">⛰️ Elevation: {selectedStation.elevation}ft</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Tornado Alerts */}
            <Card className="bg-white/80 backdrop-blur-sm border border-red-100 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300">
              <CardHeader className="pb-4">
                <CardTitle className="text-slate-700 flex items-center text-lg font-semibold">
                  <div className="p-2 bg-gradient-to-br from-red-100 to-orange-100 rounded-xl mr-3">
                    <AlertTriangle className="h-5 w-5 text-red-600" />
                  </div>
                  Recent Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-72 overflow-y-auto custom-scrollbar">
                  {tornadoAlerts.slice(0, 5).map((alert) => (
                    <Alert key={alert.id} className="bg-gradient-to-r from-red-50 to-orange-50 border-red-200 rounded-xl">
                      <AlertTriangle className={`h-4 w-4 ${getStormIntensityColor(alert.severity)}`} />
                      <AlertTitle className="text-slate-700 font-semibold">
                        {alert.alert_type.toUpperCase()} - {alert.station_id}
                      </AlertTitle>
                      <AlertDescription className="text-slate-600 text-sm">
                        Confidence: {alert.confidence}% | {formatTimestamp(alert.timestamp)}
                      </AlertDescription>
                    </Alert>
                  ))}
                  {tornadoAlerts.length === 0 && (
                    <div className="text-center py-8">
                      <div className="p-4 bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl">
                        <Shield className="h-8 w-8 text-green-500 mx-auto mb-2" />
                        <p className="text-slate-600 text-sm font-medium">All Clear</p>
                        <p className="text-slate-500 text-xs">No recent tornado alerts</p>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Main Interactive Radar Display */}
          <div className="lg:col-span-3 space-y-8">
            
            {/* Modern Radar Controls */}
            <Card className="bg-white/80 backdrop-blur-sm border border-blue-100 rounded-2xl shadow-lg">
              <CardContent className="p-6">
                <div className="flex flex-wrap items-center gap-4">
                  <Select value={radarType} onValueChange={setRadarType}>
                    <SelectTrigger className="w-48 bg-white border-blue-200 text-slate-700 rounded-xl hover:border-blue-300 focus:ring-2 focus:ring-blue-200 transition-all">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-white border-blue-100 rounded-xl shadow-xl">
                      <SelectItem value="reflectivity" className="text-slate-700 hover:bg-blue-50 rounded-lg">Reflectivity</SelectItem>
                      <SelectItem value="velocity" className="text-slate-700 hover:bg-blue-50 rounded-lg" disabled={isPremiumFeature("advanced_radar")}>
                        Velocity {isPremiumFeature("advanced_radar") && "(Premium)"}
                      </SelectItem>
                    </SelectContent>
                  </Select>

                  <Button 
                    onClick={analyzeForTornadoes} 
                    disabled={!selectedStation || analyzing}
                    className="bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-600 hover:to-rose-700 text-white rounded-xl px-6 py-2 shadow-lg hover:shadow-xl transition-all duration-300 mr-2"
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
                    className="bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700 text-white rounded-xl px-6 py-2 shadow-lg hover:shadow-xl transition-all duration-300"
                  >
                    {analyzing ? (
                      <Activity className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Zap className="h-4 w-4 mr-2" />
                    )}
                    {analyzing ? "Processing..." : "🌪️ Advanced ML Analysis"}
                  </Button>

                  <div className="flex items-center space-x-3 ml-auto">
                    <div className="flex items-center space-x-2">
                      <div className={`w-3 h-3 rounded-full shadow-lg ${monitoringStatus.system_status?.monitoring_active ? 'bg-green-400 animate-pulse shadow-green-200' : 'bg-orange-400 shadow-orange-200'}`}></div>
                      <span className="text-slate-700 text-sm font-medium">
                        {monitoringStatus.system_status?.monitoring_active ? 'Auto-Monitoring Active' : 'Manual Mode'}
                      </span>
                    </div>
                    {stormCells.length > 0 && (
                      <Badge className="bg-gradient-to-r from-red-500 to-rose-600 text-white rounded-full px-3 py-1 shadow-lg">
                        {stormCells.length} Active Storms
                      </Badge>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Interactive Radar Map */}
            <Card className="bg-white/80 backdrop-blur-sm border border-blue-100 rounded-2xl shadow-xl overflow-hidden">
              <CardHeader className="bg-gradient-to-r from-blue-50 to-sky-50 border-b border-blue-100 pb-4">
                <CardTitle className="text-slate-700 flex items-center justify-between text-xl font-bold">
                  <span className="flex items-center">
                    <div className="p-2 bg-gradient-to-br from-blue-100 to-sky-100 rounded-xl mr-3">
                      🌪️
                    </div>
                    Live Interactive Radar - Storm Oracle
                  </span>
                  <div className="flex items-center space-x-3">
                    <Badge className="bg-gradient-to-r from-green-400 to-emerald-500 text-white rounded-full px-3 py-1 shadow-lg">
                      {radarStations.length} NEXRAD Stations
                    </Badge>
                    {monitoringStatus.active_storm_summary && (
                      <Badge className="bg-gradient-to-r from-red-500 to-rose-600 text-white rounded-full px-3 py-1 shadow-lg animate-pulse">
                        {monitoringStatus.active_storm_summary.total_storms} Active Threats
                      </Badge>
                    )}
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="h-[600px] relative bg-gradient-to-br from-blue-50 to-sky-100">
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
            <Card className="bg-white/80 backdrop-blur-sm border border-blue-100 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300">
              <CardHeader className="pb-4">
                <CardTitle className="text-slate-700 flex items-center justify-between text-lg font-semibold">
                  <div className="flex items-center">
                    <div className="p-2 bg-gradient-to-br from-blue-100 to-sky-100 rounded-xl mr-3">
                      <Bot className="h-5 w-5 text-blue-600" />
                    </div>
                    AI Weather Assistant
                  </div>
                  {isPremiumFeature("ai_chatbot") && (
                    <Badge className="bg-gradient-to-r from-amber-400 to-orange-500 text-white rounded-full px-3 py-1 shadow-lg">
                      Premium
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex space-x-3">
                  <Input
                    placeholder={isPremiumFeature("ai_chatbot") ? "Upgrade to Premium to chat with AI..." : "Ask about weather conditions..."}
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    disabled={isPremiumFeature("ai_chatbot") || loading}
                    className="bg-white border-blue-200 text-slate-700 placeholder-slate-400 rounded-xl hover:border-blue-300 focus:ring-2 focus:ring-blue-200 transition-all"
                    onKeyPress={(e) => e.key === 'Enter' && handleChatSubmit()}
                  />
                  <Button 
                    onClick={handleChatSubmit} 
                    disabled={isPremiumFeature("ai_chatbot") || loading || !chatMessage.trim()}
                    className="bg-gradient-to-r from-blue-500 to-sky-600 hover:from-blue-600 hover:to-sky-700 text-white rounded-xl px-4 shadow-lg hover:shadow-xl transition-all duration-300"
                  >
                    <Bot className="h-4 w-4" />
                  </Button>
                </div>
                
                {chatResponse && (
                  <div className="p-5 bg-gradient-to-br from-blue-50 to-sky-50 border border-blue-100 rounded-2xl">
                    <div className="flex items-start space-x-3">
                      <div className="p-2 bg-blue-100 rounded-xl">
                        <Bot className="h-4 w-4 text-blue-600" />
                      </div>
                      <p className="text-slate-700 text-sm leading-relaxed flex-1">{chatResponse}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Modern Features Overview */}
        <div className="mt-16">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-sky-700 bg-clip-text text-transparent mb-4">
              Advanced Tornado Prediction Features
            </h2>
            <p className="text-slate-600 text-lg max-w-2xl mx-auto">
              Cutting-edge AI technology combined with real-time radar data for unprecedented storm prediction accuracy
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="bg-white/80 backdrop-blur-sm border border-blue-100 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 text-center group hover:-translate-y-2">
              <CardContent className="p-8">
                <div className="p-4 bg-gradient-to-br from-blue-100 to-sky-100 rounded-2xl w-fit mx-auto mb-6 group-hover:scale-110 transition-transform duration-300">
                  <Target className="h-8 w-8 text-blue-600" />
                </div>
                <h3 className="text-slate-700 font-bold text-lg mb-3">Hook Echo Detection</h3>
                <p className="text-slate-600 text-sm leading-relaxed">AI identifies hook-shaped radar signatures indicating tornado formation with 95% accuracy</p>
              </CardContent>
            </Card>
            
            <Card className="bg-white/80 backdrop-blur-sm border border-green-100 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 text-center group hover:-translate-y-2">
              <CardContent className="p-8">
                <div className="p-4 bg-gradient-to-br from-green-100 to-emerald-100 rounded-2xl w-fit mx-auto mb-6 group-hover:scale-110 transition-transform duration-300">
                  <Activity className="h-8 w-8 text-green-600" />
                </div>
                <h3 className="text-slate-700 font-bold text-lg mb-3">Velocity Couplets</h3>
                <p className="text-slate-600 text-sm leading-relaxed">Detect rotating air masses through advanced Doppler velocity analysis and pattern recognition</p>
              </CardContent>
            </Card>
            
            <Card className="bg-white/80 backdrop-blur-sm border border-red-100 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 text-center group hover:-translate-y-2">
              <CardContent className="p-8">
                <div className="p-4 bg-gradient-to-br from-red-100 to-rose-100 rounded-2xl w-fit mx-auto mb-6 group-hover:scale-110 transition-transform duration-300">
                  <AlertTriangle className="h-8 w-8 text-red-600" />
                </div>
                <h3 className="text-slate-700 font-bold text-lg mb-3">Early Warning System</h3>
                <p className="text-slate-600 text-sm leading-relaxed">Advanced predictions provide critical lead time for safety preparations and evacuation</p>
              </CardContent>
            </Card>
            
            <Card className="bg-white/80 backdrop-blur-sm border border-purple-100 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 text-center group hover:-translate-y-2">
              <CardContent className="p-8">
                <div className="p-4 bg-gradient-to-br from-purple-100 to-violet-100 rounded-2xl w-fit mx-auto mb-6 group-hover:scale-110 transition-transform duration-300">
                  <Shield className="h-8 w-8 text-purple-600" />
                </div>
                <h3 className="text-slate-700 font-bold text-lg mb-3">Path Prediction</h3>
                <p className="text-slate-600 text-sm leading-relaxed">AI forecasts precise tornado paths, touchdown locations, and intensity levels</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;