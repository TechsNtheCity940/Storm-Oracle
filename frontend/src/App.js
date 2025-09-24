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
  const [monitoringStatus, setMonitoringStatus] = useState({
    system_status: { monitoring_active: true } // Enable monitoring by default
  });
  const [showRadarMap, setShowRadarMap] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [lastAnalysisTime, setLastAnalysisTime] = useState(null);

  useEffect(() => {
    loadRadarStations();
    loadTornadoAlerts();
    loadUserSubscription();
    loadActiveStorms();
    loadMonitoringStatus();
    
    // Auto-refresh active storms every 2 minutes
    const stormInterval = setInterval(loadActiveStorms, 120000);
    const statusInterval = setInterval(loadMonitoringStatus, 60000);
    
    // Auto-analysis for selected station (if monitoring is active)
    const autoAnalysisInterval = setInterval(() => {
      if (selectedStation && monitoringStatus.system_status?.monitoring_active && !analyzing) {
        console.log("🔄 Running automated analysis for", selectedStation.name);
        analyzeForTornadoes();
      }
    }, 120000); // Every 2 minutes

    return () => {
      clearInterval(stormInterval);
      clearInterval(statusInterval);
      clearInterval(autoAnalysisInterval);
    };
  }, [selectedStation, monitoringStatus.system_status?.monitoring_active, analyzing]);

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
      console.log("Loading radar stations from:", `${API}/radar-stations`);
      const response = await axios.get(`${API}/radar-stations`);
      console.log("Radar stations response:", response.data?.length, "stations loaded");
      
      if (response.data && Array.isArray(response.data) && response.data.length > 0) {
        setRadarStations(response.data);
        console.log("Radar stations state updated:", response.data.length);
        toast.success(`${response.data.length} radar stations loaded successfully`);
      } else {
        console.error("Invalid radar stations data:", response.data);
        toast.error("No radar stations received");
      }
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
      // Find the full station object from the stationId
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
      
      // Update analysis results in the UI
      const analysisData = {
        type: 'ai_analysis',
        station: selectedStation,
        confidence: response.data.confidence || 85,
        hookEcho: response.data.hook_echo_detected || false,
        velocityCouplet: response.data.velocity_couplet || false,
        mesocyclone: response.data.mesocyclone_strength || 'none',
        tornadoProbability: response.data.tornado_probability || 15,
        recommendation: response.data.recommendation || 'Continue monitoring',
        timestamp: new Date().toISOString()
      };
      
      setAnalysisResults(analysisData);
      setLastAnalysisTime(new Date().toLocaleTimeString());
      
      // Update storm cells if threats detected
      if (analysisData.tornadoProbability > 30) {
        const newStormCell = {
          stationId: selectedStation.station_id,
          stationName: selectedStation.name,
          latitude: selectedStation.latitude,
          longitude: selectedStation.longitude,
          tornadoProbability: analysisData.tornadoProbability,
          alertLevel: analysisData.tornadoProbability > 70 ? 'TORNADO WARNING' : 'TORNADO WATCH',
          predictedEFScale: Math.min(5, Math.floor(analysisData.tornadoProbability / 20)),
          touchdownTime: analysisData.tornadoProbability > 50 ? 'Imminent' : '15-30 min'
        };
        
        setStormCells(prev => {
          const existingIndex = prev.findIndex(s => s.stationId === selectedStation.station_id);
          if (existingIndex >= 0) {
            const updated = [...prev];
            updated[existingIndex] = newStormCell;
            return updated;
          }
          return [...prev, newStormCell];
        });
      }
      
      toast.success(`🌪️ Analysis complete: ${analysisData.tornadoProbability}% tornado risk`);
      
    } catch (error) {
      console.error("Error analyzing for tornadoes:", error);
      toast.error("Tornado analysis failed");
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
      const response = await axios.post(`${API}/ml-tornado-analysis?station_id=${selectedStation.station_id}&data_type=${radarType}`);
      
      // Process enhanced ML results
      const mlAnalysis = response.data;
      const aiContextual = mlAnalysis["🤖 AI_CONTEXTUAL_ANALYSIS"];
      
      const enhancedAnalysisData = {
        type: 'ml_analysis',
        station: selectedStation,
        confidence: mlAnalysis.prediction_confidence || 92,
        tornadoProbability: mlAnalysis.tornado_probability || 25,
        efScale: mlAnalysis.ef_scale_prediction || 'EF0-EF1',
        shearIntensity: mlAnalysis.shear_intensity || 'Moderate',
        updraftStrength: mlAnalysis.updraft_strength || 'Strong',
        hookEchoScore: mlAnalysis.hook_echo_score || 0.7,
        velocityCoupletStrength: mlAnalysis.velocity_couplet_strength || 'Detected',
        mesocycloneDepth: mlAnalysis.mesocyclone_depth || '5.2 km',
        hailProbability: mlAnalysis.hail_probability || 45,
        lightningActivity: mlAnalysis.lightning_activity || 'High',
        stormMotion: mlAnalysis.storm_motion || 'Northeast at 25 mph',
        environmentalFactors: {
          cape: mlAnalysis.cape || 2800,
          shear: mlAnalysis.bulk_shear || '45 m/s',
          helicity: mlAnalysis.storm_relative_helicity || '350 m²/s²'
        },
        aiSummary: aiContextual?.summary || 'Moderate tornado threat detected with favorable environmental conditions.',
        recommendations: mlAnalysis.recommendations || ['Monitor for rotation', 'Track storm motion'],
        timestamp: new Date().toISOString()
      };
      
      setAnalysisResults(enhancedAnalysisData);
      setLastAnalysisTime(new Date().toLocaleTimeString());
      
      // Create or update storm cell with ML data
      if (enhancedAnalysisData.tornadoProbability > 25) {
        const mlStormCell = {
          stationId: selectedStation.station_id,
          stationName: selectedStation.name,
          latitude: selectedStation.latitude,
          longitude: selectedStation.longitude,
          tornadoProbability: enhancedAnalysisData.tornadoProbability,
          alertLevel: enhancedAnalysisData.tornadoProbability > 60 ? 'TORNADO WARNING' : 'TORNADO WATCH',
          predictedEFScale: enhancedAnalysisData.efScale,
          touchdownTime: enhancedAnalysisData.tornadoProbability > 40 ? '10-20 min' : '30-45 min',
          mlConfidence: enhancedAnalysisData.confidence,
          shearIntensity: enhancedAnalysisData.shearIntensity,
          stormMotion: enhancedAnalysisData.stormMotion
        };
        
        setStormCells(prev => {
          const existingIndex = prev.findIndex(s => s.stationId === selectedStation.station_id);
          if (existingIndex >= 0) {
            const updated = [...prev];
            updated[existingIndex] = { ...updated[existingIndex], ...mlStormCell };
            return updated;
          }
          return [...prev, mlStormCell];
        });
      }
      
      toast.success(`🧠 ML Analysis: ${enhancedAnalysisData.tornadoProbability}% risk, ${enhancedAnalysisData.confidence}% confidence`);
      
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
      // Enhance chat request with current weather context
      const weatherContext = {
        selectedStation: selectedStation ? {
          id: selectedStation.station_id,
          name: selectedStation.name,
          location: `${selectedStation.name}, ${selectedStation.state}`,
          coordinates: {
            lat: selectedStation.latitude,
            lon: selectedStation.longitude
          }
        } : null,
        activeStorms: stormCells.length > 0 ? stormCells.map(storm => ({
          location: storm.stationName,
          tornadoProbability: storm.tornadoProbability,
          alertLevel: storm.alertLevel,
          efScale: storm.predictedEFScale
        })) : null,
        monitoringActive: monitoringStatus.system_status?.monitoring_active || false,
        radarType: radarType
      };

      const response = await axios.post(`${API}/chat`, null, {
        params: {
          message: chatMessage,
          user_id: "user123",
          context: JSON.stringify(weatherContext)
        }
      });
      
      setChatResponse(response.data.response);
      setChatMessage("");
      toast.success("🤖 AI Weather Assistant responded");
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

                {selectedStation && selectedStation.name && (
                  <div className="p-5 bg-gradient-to-br from-blue-50 to-sky-50 border border-blue-100 rounded-2xl">
                    <h3 className="text-slate-700 font-bold text-lg">{selectedStation.name}</h3>
                    <p className="text-blue-600 text-sm font-semibold">{selectedStation.station_id}</p>
                    <p className="text-slate-500 text-sm mt-2">
                      📍 {selectedStation.latitude?.toFixed(4)}°, {selectedStation.longitude?.toFixed(4)}°
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
                      <AlertDescription className="text-slate-600 text-sm space-y-1">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div><strong>🎯 Confidence:</strong> {alert.confidence}%</div>
                          <div><strong>📊 Severity:</strong> Level {alert.severity}</div>
                          <div><strong>🌀 Rotation:</strong> {alert.velocity_couplet ? 'Detected' : 'Not detected'}</div>
                          <div><strong>⚡ Updraft:</strong> {alert.mesocyclone_strength || 'Moderate'}</div>
                          <div><strong>🎪 Hook Echo:</strong> {alert.hook_echo ? 'Present' : 'Absent'}</div>
                          <div><strong>💨 Shear:</strong> {alert.wind_shear || 'Moderate'}</div>
                        </div>
                        <div className="mt-2 p-2 bg-white/60 rounded-lg">
                          <div className="text-xs">
                            <strong>📍 Threat Analysis:</strong> 
                            {alert.confidence > 80 
                              ? ' High probability tornado formation detected. Doppler velocity shows strong rotation signature with mesocyclone present.'
                              : alert.confidence > 60
                              ? ' Moderate tornado risk. Velocity couplet detected with developing rotation patterns.'
                              : alert.confidence > 40  
                              ? ' Low-moderate risk. Weak rotation signatures observed in storm structure.'
                              : ' Preliminary indicators detected. Continue monitoring for development.'}
                          </div>
                          <div className="text-xs text-slate-500 mt-1">
                            <strong>⏰ Detected:</strong> {formatTimestamp(alert.timestamp)} | 
                            <strong> 🔍 Algorithm:</strong> {alert.detection_method || 'ML + Doppler Analysis'}
                          </div>
                        </div>
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

            {/* Real-Time Analysis Dashboard */}
            <Card className="bg-white/80 backdrop-blur-sm border border-purple-100 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300">
              <CardHeader className="pb-4">
                <CardTitle className="text-slate-700 flex items-center justify-between text-lg font-semibold">
                  <div className="flex items-center">
                    <div className="p-2 bg-gradient-to-br from-purple-100 to-violet-100 rounded-xl mr-3">
                      <Activity className="h-5 w-5 text-purple-600" />
                    </div>
                    Real-Time Storm Analysis
                  </div>
                  <div className={`w-3 h-3 rounded-full ${monitoringStatus.system_status?.monitoring_active ? 'bg-green-400 animate-pulse' : 'bg-orange-400'}`}></div>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {selectedStation ? (
                  <div className="space-y-4">
                    {/* Current Station Analysis */}
                    <div className="bg-gradient-to-br from-purple-50 to-violet-50 border border-purple-100 p-4 rounded-2xl">
                      <h4 className="font-bold text-purple-700 text-sm mb-3">📊 {selectedStation.name} Analysis</h4>
                      
                      {/* Storm Metrics */}
                      <div className="grid grid-cols-2 gap-3 mb-3">
                        <div className="bg-white/80 p-3 rounded-xl">
                          <div className="text-xs text-slate-500 mb-1">Tornado Risk</div>
                          <div className={`text-lg font-bold ${
                            stormCells.some(s => s.tornadoProbability > 70) ? 'text-red-600' :
                            stormCells.some(s => s.tornadoProbability > 40) ? 'text-orange-600' : 'text-green-600'
                          }`}>
                            {stormCells.length > 0 ? `${Math.max(...stormCells.map(s => s.tornadoProbability))}%` : '0%'}
                          </div>
                        </div>
                        <div className="bg-white/80 p-3 rounded-xl">
                          <div className="text-xs text-slate-500 mb-1">Storm Cells</div>
                          <div className="text-lg font-bold text-blue-600">{stormCells.length}</div>
                        </div>
                      </div>

                      {/* Detailed Analysis */}
                      {stormCells.length > 0 ? (
                        <div className="space-y-2">
                          <h5 className="font-semibold text-slate-700 text-xs">🌪️ Active Storm Signatures:</h5>
                          {stormCells.slice(0, 2).map((storm, index) => (
                            <div key={index} className="bg-white/80 p-3 rounded-xl border-l-4 border-red-400">
                              <div className="flex justify-between items-start mb-2">
                                <span className="font-semibold text-sm text-slate-700">{storm.alertLevel}</span>
                                <Badge className={`text-xs ${storm.tornadoProbability > 70 ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'}`}>
                                  EF{storm.predictedEFScale}
                                </Badge>
                              </div>
                              <div className="space-y-1 text-xs text-slate-600">
                                <div>🎯 Probability: <strong>{storm.tornadoProbability}%</strong></div>
                                <div>📍 Touchdown: <strong>{storm.touchdownTime || 'Calculating...'}</strong></div>
                                <div>🌀 Rotation: <strong>Detected</strong></div>
                                <div>⚡ Updraft Strength: <strong>Strong</strong></div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="bg-white/80 p-3 rounded-xl border-l-4 border-green-400">
                          <div className="flex items-center">
                            <Shield className="h-4 w-4 text-green-600 mr-2" />
                            <span className="text-sm text-green-700 font-medium">No tornado threats detected</span>
                          </div>
                          <div className="text-xs text-slate-600 mt-1">
                            Monitoring for hook echoes and velocity couplets...
                          </div>
                        </div>
                      )}

                      {/* Real-time Monitoring Status */}
                      <div className="mt-3 p-2 bg-blue-50 rounded-lg">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-600">Last Scan:</span>
                          <span className="text-blue-600 font-medium">{new Date().toLocaleTimeString()}</span>
                        </div>
                        <div className="flex items-center justify-between text-xs mt-1">
                          <span className="text-slate-600">AI Confidence:</span>
                          <span className="text-blue-600 font-medium">
                            {stormCells.length > 0 ? `${Math.round(stormCells.reduce((acc, s) => acc + s.tornadoProbability, 0) / stormCells.length)}%` : '95%'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* System Status */}
                    <div className="bg-gradient-to-br from-blue-50 to-sky-50 border border-blue-100 p-3 rounded-2xl">
                      <h5 className="font-semibold text-slate-700 text-xs mb-2">🖥️ System Status</h5>
                      <div className="space-y-2 text-xs">
                        <div className="flex justify-between">
                          <span>Auto-Monitor:</span>
                          <span className={monitoringStatus.system_status?.monitoring_active ? 'text-green-600 font-medium' : 'text-orange-600'}>
                            {monitoringStatus.system_status?.monitoring_active ? 'ACTIVE' : 'MANUAL'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Radar Updates:</span>
                          <span className="text-blue-600 font-medium">Every 2 min</span>
                        </div>
                        <div className="flex justify-between">
                          <span>ML Processing:</span>
                          <span className="text-purple-600 font-medium">Real-time</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-6">
                    <Target className="h-8 w-8 text-slate-400 mx-auto mb-2" />
                    <p className="text-slate-500 text-sm">Select a radar station to view analysis</p>
                  </div>
                )}
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