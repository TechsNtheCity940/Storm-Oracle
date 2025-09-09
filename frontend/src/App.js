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

  useEffect(() => {
    loadRadarStations();
    loadTornadoAlerts();
    loadUserSubscription();
  }, []);

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
      const stationResponse = await axios.get(`${API}/radar-stations/${stationId}`);
      setSelectedStation(stationResponse.data);
      
      const radarResponse = await axios.get(`${API}/radar-data/${stationId}?data_type=${radarType}`);
      setRadarData(radarResponse.data);
      
      toast.success(`Connected to ${stationResponse.data.name} radar`);
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
          
          {/* Radar Station Selection */}
          <div className="lg:col-span-1 space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center">
                  <MapPin className="h-5 w-5 mr-2" />
                  Radar Stations
                </CardTitle>
                <CardDescription className="text-slate-400">
                  Select a NEXRAD station to monitor
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Select onValueChange={selectRadarStation} disabled={loading}>
                  <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                    <SelectValue placeholder="Choose radar station..." />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-600">
                    {radarStations.map((station) => (
                      <SelectItem key={station.station_id} value={station.station_id} className="text-white hover:bg-slate-700">
                        {station.station_id} - {station.name}, {station.state}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {selectedStation && (
                  <div className="p-4 bg-slate-700 rounded-lg">
                    <h3 className="text-white font-semibold">{selectedStation.name}</h3>
                    <p className="text-slate-300 text-sm">{selectedStation.station_id}</p>
                    <p className="text-slate-400 text-xs">
                      {selectedStation.latitude.toFixed(4)}°, {selectedStation.longitude.toFixed(4)}°
                    </p>
                    <p className="text-slate-400 text-xs">Elevation: {selectedStation.elevation}ft</p>
                  </div>
                )}
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

          {/* Main Radar Display */}
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

                  <div className="flex items-center space-x-2 text-white">
                    <Cloud className="h-4 w-4" />
                    <span className="text-sm">Live Weather Data</span>
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Radar Display */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">
                  {selectedStation ? `${selectedStation.name} - ${radarType.charAt(0).toUpperCase() + radarType.slice(1)} Radar` : "Select a Radar Station"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {radarData ? (
                  <div className="relative">
                    <img 
                      src={radarData.radar_url} 
                      alt={`${radarType} radar`}
                      className="w-full h-96 object-contain bg-black rounded-lg"
                      onError={(e) => {
                        e.target.src = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iIzFhMWExYSIvPgogIDx0ZXh0IHg9IjIwMCIgeT0iMTUwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTYiIGZpbGw9IiM5Y2EzYWYiIHRleHQtYW5jaG9yPSJtaWRkbGUiPk5vIFJhZGFyIERhdGEgQXZhaWxhYmxlPC90ZXh0Pgo8L3N2Zz4K";
                      }}
                    />
                    <div className="absolute top-4 left-4 bg-black/70 text-white px-3 py-1 rounded text-sm">
                      {formatTimestamp(radarData.timestamp || new Date())}
                    </div>
                  </div>
                ) : (
                  <div className="h-96 bg-slate-900 rounded-lg flex items-center justify-center">
                    <div className="text-center text-slate-400">
                      <Cloud className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Select a radar station to view live weather data</p>
                    </div>
                  </div>
                )}
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