"""
🌪️ STORM ORACLE - AUTOMATED STORM MONITORING SYSTEM
Continuously monitors all radar stations and generates automatic tornado predictions
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import json
from .tornado_predictor import tornado_prediction_engine
from .data_processor import ml_data_pipeline
import httpx

logger = logging.getLogger(__name__)

class AutomatedStormMonitor:
    """Continuously monitors all storm cells and generates automatic tornado predictions"""
    
    def __init__(self, db_connection, claude_chat):
        self.db = db_connection
        self.claude_chat = claude_chat
        self.monitoring_active = False
        self.scan_interval = 300  # 5 minutes
        self.active_storms = {}
        self.prediction_history = {}
        
        # High-priority monitoring for tornado-prone regions
        self.priority_stations = [
            'KTLX', 'KFDR', 'KINX', 'KEAX', 'KICT', 'KGLD', 'KDDC', 'KTWX',  # Tornado Alley
            'KBMX', 'KHTX', 'KGWX', 'KNQA', 'KOHX', 'KPAH', 'KLZK',  # Southeast
            'KLOT', 'KILX', 'KDVN', 'KDMX', 'KARX', 'KMPX', 'KFSD'   # Midwest
        ]
        
        logger.info("🌪️ Automated Storm Monitor initialized")
    
    async def start_monitoring(self):
        """Start continuous storm monitoring"""
        if self.monitoring_active:
            logger.warning("Storm monitoring already active")
            return
            
        self.monitoring_active = True
        logger.info("🚀 Starting automated storm monitoring for all US radar stations")
        
        # Start monitoring tasks
        monitoring_tasks = [
            asyncio.create_task(self._continuous_storm_scan()),
            asyncio.create_task(self._priority_station_monitor()),
            asyncio.create_task(self._cleanup_old_predictions()),
            asyncio.create_task(self._generate_national_summary())
        ]
        
        try:
            await asyncio.gather(*monitoring_tasks)
        except Exception as e:
            logger.error(f"Error in storm monitoring: {str(e)}")
            self.monitoring_active = False
    
    async def stop_monitoring(self):
        """Stop storm monitoring"""
        self.monitoring_active = False
        logger.info("🛑 Stopped automated storm monitoring")
    
    async def _continuous_storm_scan(self):
        """Continuously scan all radar stations for storm activity"""
        
        while self.monitoring_active:
            try:
                logger.info("🔍 Scanning all radar stations for storm activity...")
                
                # Get all radar stations
                stations = await self.db.radar_stations.find().to_list(1000)
                
                # Process stations in batches for efficiency
                batch_size = 10
                for i in range(0, len(stations), batch_size):
                    batch = stations[i:i + batch_size]
                    
                    # Process batch concurrently
                    batch_tasks = [
                        self._scan_station_for_storms(station) 
                        for station in batch
                    ]
                    
                    await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Small delay between batches to prevent overwhelming the system
                    await asyncio.sleep(1)
                
                logger.info(f"✅ Completed scan of {len(stations)} stations")
                
                # Wait before next scan
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in continuous storm scan: {str(e)}")
                await asyncio.sleep(60)  # Retry after 1 minute
    
    async def _scan_station_for_storms(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """Scan individual station for storm activity"""
        
        try:
            station_id = station['station_id']
            
            # Remove MongoDB ObjectId
            if "_id" in station:
                del station["_id"]
            
            station_location = {
                'latitude': station['latitude'],
                'longitude': station['longitude'],
                'elevation': station['elevation']
            }
            
            # Prepare ML data
            ml_data = await ml_data_pipeline.prepare_prediction_data(station_id, station_location)
            
            # Get ML prediction
            ml_prediction = tornado_prediction_engine.predict_tornado_comprehensive(
                radar_data=ml_data['radar_sequence'],
                atmospheric_data=ml_data['atmospheric_data'],
                station_location=station_location
            )
            
            # Check if this is a significant tornado threat
            tornado_probability = ml_prediction.tornado_probability
            alert_level = ml_prediction.alert_level
            
            # Generate alert for significant threats
            if tornado_probability > 0.3 or alert_level not in ['NORMAL_CONDITIONS']:
                await self._generate_automatic_alert(station, ml_prediction, ml_data)
            
            # Update active storms tracking
            if tornado_probability > 0.2:
                self.active_storms[station_id] = {
                    'station': station,
                    'prediction': ml_prediction,
                    'last_updated': datetime.now(timezone.utc),
                    'tornado_probability': tornado_probability,
                    'alert_level': alert_level
                }
            elif station_id in self.active_storms and tornado_probability < 0.1:
                # Remove from active storms if threat diminished
                del self.active_storms[station_id]
            
            return {
                'station_id': station_id,
                'tornado_probability': tornado_probability,
                'alert_level': alert_level,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error scanning station {station.get('station_id', 'unknown')}: {str(e)}")
            return {
                'station_id': station.get('station_id', 'unknown'),
                'status': 'error',
                'error': str(e)
            }
    
    async def _generate_automatic_alert(self, station: Dict[str, Any], ml_prediction, ml_data: Dict[str, Any]):
        """Generate automatic tornado alert"""
        
        try:
            station_id = station['station_id']
            
            # Check if we've recently generated an alert for this station
            recent_threshold = datetime.now(timezone.utc) - timedelta(minutes=15)
            recent_alert = await self.db.tornado_alerts.find_one({
                'station_id': station_id,
                'alert_type': 'AUTOMATED_ML_ANALYSIS',
                'timestamp': {'$gte': recent_threshold.isoformat()}
            })
            
            if recent_alert:
                logger.debug(f"Skipping alert for {station_id} - recent alert exists")
                return
            
            # Generate contextual AI analysis
            claude_prompt = f"""
            🚨 AUTOMATED TORNADO THREAT DETECTED
            
            Station: {station['name']} ({station_id})
            Location: {station['latitude']:.4f}°N, {station['longitude']:.4f}°W
            
            🌪️ ML DETECTION:
            - Tornado Probability: {ml_prediction.tornado_probability:.1%}
            - Alert Level: {ml_prediction.alert_level}
            - EF Scale Prediction: EF{max(ml_prediction.ef_scale_prediction, key=ml_prediction.ef_scale_prediction.get)[-1]}
            - Confidence: {ml_prediction.confidence_score:.1%}
            
            📊 CONDITIONS:
            - Data Quality: {ml_data.get('data_quality', 'Unknown')}
            - Time: {datetime.now(timezone.utc).strftime('%H:%M UTC')}
            
            Provide a brief automated alert message focusing on:
            1. Immediate threat assessment
            2. Recommended actions for affected areas
            3. Key meteorological factors
            
            Keep response under 200 words for automated alert system.
            """
            
            # Get AI analysis
            from emergentintegrations.llm.chat import UserMessage
            claude_message = UserMessage(text=claude_prompt)
            ai_analysis = await self.claude_chat.send_message(claude_message)
            
            # Create automated alert
            from tornado_predictor import TornadoAlert
            
            alert = TornadoAlert(
                station_id=station_id,
                alert_type="AUTOMATED_ML_ANALYSIS",
                severity=min(5, max(1, int(ml_prediction.tornado_probability * 5) + 1)),
                predicted_location={
                    "lat": ml_prediction.touchdown_location['latitude'],
                    "lng": ml_prediction.touchdown_location['longitude']
                },
                predicted_path=[
                    {"lat": point['latitude'], "lng": point['longitude']}
                    for point in ml_prediction.path_trajectory[:3]
                ],
                confidence=ml_prediction.confidence_score * 100,
                message=f"🤖 AUTOMATED ALERT\n\n{ai_analysis}",
                timestamp=datetime.now(timezone.utc),
                estimated_touchdown_time=datetime.now(timezone.utc) + timedelta(
                    minutes=ml_prediction.timing_predictions.get('time_to_touchdown_minutes', 60)
                ) if ml_prediction.timing_predictions.get('time_to_touchdown_minutes', 0) > 0 else None
            )
            
            # Store alert
            alert_dict = alert.dict()
            if 'timestamp' in alert_dict and alert_dict['timestamp']:
                alert_dict['timestamp'] = alert_dict['timestamp'].isoformat()
            if 'estimated_touchdown_time' in alert_dict and alert_dict['estimated_touchdown_time']:
                alert_dict['estimated_touchdown_time'] = alert_dict['estimated_touchdown_time'].isoformat()
            
            await self.db.tornado_alerts.insert_one(alert_dict)
            
            logger.info(f"🚨 Generated automated alert for {station['name']} - {ml_prediction.tornado_probability:.1%} tornado risk")
            
        except Exception as e:
            logger.error(f"Error generating automatic alert: {str(e)}")
    
    async def _priority_station_monitor(self):
        """Enhanced monitoring for high-priority tornado-prone stations"""
        
        while self.monitoring_active:
            try:
                logger.info("🎯 Enhanced monitoring of priority tornado-prone stations")
                
                # Get priority stations
                priority_stations = await self.db.radar_stations.find({
                    'station_id': {'$in': self.priority_stations}
                }).to_list(100)
                
                # Monitor priority stations more frequently
                for station in priority_stations:
                    try:
                        scan_result = await self._scan_station_for_storms(station)
                        
                        # Enhanced alerting for priority stations
                        if scan_result.get('tornado_probability', 0) > 0.15:  # Lower threshold
                            logger.warning(f"🌪️ Enhanced monitoring alert: {station['name']} - {scan_result['tornado_probability']:.1%} tornado risk")
                    
                    except Exception as e:
                        logger.error(f"Error in priority monitoring for {station.get('station_id')}: {str(e)}")
                
                # Priority stations checked every 2 minutes
                await asyncio.sleep(120)
                
            except Exception as e:
                logger.error(f"Error in priority station monitoring: {str(e)}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_predictions(self):
        """Clean up old predictions and maintain system performance"""
        
        while self.monitoring_active:
            try:
                # Clean up predictions older than 24 hours
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                
                result = await self.db.tornado_alerts.delete_many({
                    'alert_type': 'AUTOMATED_ML_ANALYSIS',
                    'timestamp': {'$lt': cutoff_time.isoformat()}
                })
                
                if result.deleted_count > 0:
                    logger.info(f"🧹 Cleaned up {result.deleted_count} old automated alerts")
                
                # Clean up active storms tracking
                current_time = datetime.now(timezone.utc)
                expired_storms = [
                    station_id for station_id, storm_data in self.active_storms.items()
                    if (current_time - storm_data['last_updated']).seconds > 3600  # 1 hour
                ]
                
                for station_id in expired_storms:
                    del self.active_storms[station_id]
                
                if expired_storms:
                    logger.info(f"🧹 Removed {len(expired_storms)} expired storm trackings")
                
                # Run cleanup every hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in cleanup: {str(e)}")
                await asyncio.sleep(3600)
    
    async def _generate_national_summary(self):
        """Generate periodic national tornado threat summary"""
        
        while self.monitoring_active:
            try:
                # Generate summary every 30 minutes
                await asyncio.sleep(1800)
                
                if not self.active_storms:
                    continue
                
                # Create national summary
                high_threat_storms = [
                    storm for storm in self.active_storms.values()
                    if storm['tornado_probability'] > 0.5
                ]
                
                moderate_threat_storms = [
                    storm for storm in self.active_storms.values()
                    if 0.2 < storm['tornado_probability'] <= 0.5
                ]
                
                if high_threat_storms or len(moderate_threat_storms) > 5:
                    summary_prompt = f"""
                    🇺🇸 NATIONAL TORNADO THREAT SUMMARY
                    
                    Time: {datetime.now(timezone.utc).strftime('%H:%M UTC on %B %d, %Y')}
                    
                    HIGH THREAT AREAS ({len(high_threat_storms)}):
                    {chr(10).join([f"- {storm['station']['name']}: {storm['tornado_probability']:.1%}" for storm in high_threat_storms[:5]])}
                    
                    MODERATE THREAT AREAS ({len(moderate_threat_storms)}):
                    {chr(10).join([f"- {storm['station']['name']}: {storm['tornado_probability']:.1%}" for storm in moderate_threat_storms[:10]])}
                    
                    Provide a brief national tornado outlook and key areas of concern.
                    """
                    
                    from emergentintegrations.llm.chat import UserMessage
                    claude_message = UserMessage(text=summary_prompt)
                    national_summary = await self.claude_chat.send_message(claude_message)
                    
                    logger.info(f"📊 Generated national tornado summary: {len(high_threat_storms)} high threats, {len(moderate_threat_storms)} moderate threats")
                
            except Exception as e:
                logger.error(f"Error generating national summary: {str(e)}")
    
    def get_active_storms(self) -> List[Dict[str, Any]]:
        """Get current active storm cells"""
        
        active_storm_list = []
        for station_id, storm_data in self.active_storms.items():
            prediction = storm_data['prediction']
            station = storm_data['station']
            
            active_storm_list.append({
                'stationId': station_id,
                'stationName': station['name'],
                'latitude': station['latitude'],
                'longitude': station['longitude'],
                'tornadoProbability': int(storm_data['tornado_probability'] * 100),
                'alertLevel': storm_data['alert_level'],
                'predictedEFScale': f"EF{max(prediction.ef_scale_prediction, key=prediction.ef_scale_prediction.get)[-1]}",
                'confidence': int(prediction.confidence_score * 100),
                'lastUpdated': storm_data['last_updated'].isoformat(),
                'touchdownTime': prediction.timing_predictions.get('time_to_touchdown_minutes', 'Unknown')
            })
        
        return sorted(active_storm_list, key=lambda x: x['tornadoProbability'], reverse=True)
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring system status"""
        
        return {
            'monitoring_active': self.monitoring_active,
            'active_storms_count': len(self.active_storms),
            'high_threat_storms': len([s for s in self.active_storms.values() if s['tornado_probability'] > 0.5]),
            'moderate_threat_storms': len([s for s in self.active_storms.values() if 0.2 < s['tornado_probability'] <= 0.5]),
            'scan_interval_minutes': self.scan_interval // 60,
            'priority_stations_count': len(self.priority_stations),
            'last_scan_time': datetime.now(timezone.utc).isoformat()
        }

# Global storm monitor instance will be initialized in server.py
storm_monitor = None