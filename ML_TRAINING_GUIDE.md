# 🤖 Storm Oracle ML Model Training Guide

## Current Model Status
The `TornadoSuperPredictor` is currently a **demonstration model** that generates realistic predictions but isn't trained on real data. For production use, you need proper training with historical tornado and weather data.

## 📊 Data Requirements

### Primary Datasets Needed:
1. **NEXRAD Radar Data**
   - Source: NOAA/NWS Archive
   - Format: Level II radar data files
   - Time Range: 10+ years for robust training
   - Size: ~100TB+ of historical radar data

2. **Tornado Database**
   - Source: SPC (Storm Prediction Center) tornado database
   - Format: CSV with tornado tracks, intensity, timing
   - Variables: Lat/lon, EF-scale, path width, damage

3. **Atmospheric Data**
   - Source: NOAA/NCEP reanalysis data
   - Variables: Temperature, pressure, humidity, wind shear
   - Resolution: 0.25° x 0.25° grid
   - Temporal: Hourly data

4. **Environmental Data**
   - CAPE (Convective Available Potential Energy)
   - Wind shear measurements
   - Helicity values
   - Storm-relative parameters

## 🔧 Training Infrastructure Setup

### Hardware Requirements:
```bash
# Minimum Training Setup
- GPU: NVIDIA RTX 4090 or A100 (24GB+ VRAM)
- RAM: 64GB+ system memory
- Storage: 10TB+ NVMe SSD for data pipeline
- CPU: 16+ cores for data preprocessing

# Production Training Setup
- Multiple A100/H100 GPUs (distributed training)
- 256GB+ RAM
- 50TB+ high-speed storage
- High-bandwidth network for data loading
```

### Software Environment:
```bash
# Install training dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install pytorch-lightning wandb tensorboard
pip install xarray netcdf4 h5py
pip install scikit-learn matplotlib seaborn
pip install pyart wradlib  # Radar data processing
```

## 📥 Data Collection Pipeline

### 1. NEXRAD Data Collection:
```python
# Example data collection script
import boto3
import os
from datetime import datetime, timedelta

def download_nexrad_data(start_date, end_date, station_ids):
    """Download NEXRAD Level II data from AWS"""
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket = 'noaa-nexrad-level2'
    
    for station_id in station_ids:
        for date in daterange(start_date, end_date):
            key = f"{date.year}/{date.month:02d}/{date.day:02d}/{station_id}/"
            # Download radar files for this date
            # Process and store in training format
```

### 2. Tornado Event Correlation:
```python
def correlate_tornado_events():
    """Match tornado events with radar data"""
    # Load SPC tornado database
    # For each tornado event:
    #   - Find corresponding radar data (±2 hours)
    #   - Extract radar volume scans
    #   - Create training labels (tornado/no-tornado)
    #   - Generate atmospheric feature vectors
```

## 🏋️ Training Process

### 1. Data Preprocessing:
```python
# /app/backend/ml_models/data_preparation.py
class TornadoDatasetPreparator:
    def __init__(self, data_path):
        self.data_path = data_path
        
    def prepare_radar_features(self, radar_file):
        """Extract radar features for ML training"""
        # Load radar data using PyART
        # Compute derived products (VIL, mesocyclone detection)
        # Create 3D radar volume features
        # Return normalized feature tensor
        
    def prepare_atmospheric_features(self, timestamp, location):
        """Extract atmospheric environment features"""
        # Load reanalysis data for time/location
        # Compute wind shear, CAPE, helicity
        # Create environmental feature vector
        
    def create_training_labels(self, tornado_database):
        """Create binary labels for tornado occurrence"""
        # 1 = Tornado occurred within next 30 minutes
        # 0 = No tornado in next 30 minutes
```

### 2. Model Training Script:
```python
# /app/backend/ml_models/train_tornado_model.py
import pytorch_lightning as pl
import torch
import wandb

class TornadoTrainer(pl.LightningModule):
    def __init__(self, model, learning_rate=1e-4):
        super().__init__()
        self.model = model
        self.lr = learning_rate
        
    def training_step(self, batch, batch_idx):
        radar_data, atmos_data, labels = batch
        predictions = self.model(radar_data, atmos_data)
        loss = F.binary_cross_entropy_with_logits(predictions, labels)
        
        # Log metrics
        self.log('train_loss', loss)
        return loss
        
    def validation_step(self, batch, batch_idx):
        radar_data, atmos_data, labels = batch
        predictions = self.model(radar_data, atmos_data)
        loss = F.binary_cross_entropy_with_logits(predictions, labels)
        
        # Calculate metrics
        accuracy = self.calculate_accuracy(predictions, labels)
        precision = self.calculate_precision(predictions, labels)
        recall = self.calculate_recall(predictions, labels)
        
        self.log('val_loss', loss)
        self.log('val_accuracy', accuracy)
        self.log('val_precision', precision)
        self.log('val_recall', recall)

# Training execution
def train_model():
    # Initialize model
    model = TornadoSuperPredictor()
    
    # Setup data loaders
    train_loader = create_training_dataloader()
    val_loader = create_validation_dataloader()
    
    # Initialize trainer
    trainer = pl.Trainer(
        max_epochs=100,
        gpus=torch.cuda.device_count(),
        strategy='ddp' if torch.cuda.device_count() > 1 else None,
        callbacks=[
            pl.callbacks.ModelCheckpoint(monitor='val_loss'),
            pl.callbacks.EarlyStopping(monitor='val_loss', patience=10)
        ]
    )
    
    # Train model
    trainer.fit(model, train_loader, val_loader)
```

### 3. Model Evaluation:
```python
# /app/backend/ml_models/evaluate_model.py
class TornadoModelEvaluator:
    def __init__(self, model_path):
        self.model = torch.load(model_path)
        
    def evaluate_on_test_set(self, test_loader):
        """Comprehensive model evaluation"""
        metrics = {
            'accuracy': [],
            'precision': [],
            'recall': [],
            'f1_score': [],
            'auc_roc': [],
            'false_alarm_rate': [],
            'probability_of_detection': []
        }
        
        # Run evaluation
        # Calculate meteorological verification metrics
        # Generate performance reports
        
    def generate_performance_report(self):
        """Generate detailed performance analysis"""
        # Confusion matrix
        # ROC curves
        # Feature importance analysis
        # Case study examples
```

## 🚀 Training Execution Commands

### Start Training Process:
```bash
# Navigate to ML directory
cd /app/backend/ml_models

# Start training with monitoring
python -m wandb login  # Login to Weights & Biases for monitoring
python train_tornado_model.py --config config/training_config.yaml

# Monitor training progress
wandb dashboard  # View training metrics in browser
tensorboard --logdir lightning_logs/
```

### Training Configuration Example:
```yaml
# config/training_config.yaml
model:
  radar_channels: 8
  atmospheric_features: 25
  hidden_dim: 512
  num_layers: 6
  dropout: 0.2

training:
  batch_size: 32
  learning_rate: 1e-4
  max_epochs: 100
  patience: 10
  
data:
  radar_data_path: "/data/nexrad/"
  tornado_db_path: "/data/tornado_database.csv"
  atmospheric_data_path: "/data/reanalysis/"
  train_split: 0.7
  val_split: 0.15
  test_split: 0.15

hardware:
  num_gpus: 4
  num_workers: 16
  pin_memory: true
```

## 📈 Continuous Learning Setup

### Real-time Model Updates:
```python
# /app/backend/ml_models/continuous_learning.py
class ContinuousLearner:
    def __init__(self, model_path):
        self.model = torch.load(model_path)
        self.update_frequency = timedelta(days=7)  # Weekly updates
        
    async def collect_new_data(self):
        """Collect new radar/tornado data for model updates"""
        # Download latest NEXRAD data
        # Check for new tornado reports
        # Validate and clean new data
        
    async def retrain_model(self):
        """Incremental model retraining"""
        # Add new data to training set
        # Fine-tune model with new examples
        # Validate performance on holdout set
        # Deploy updated model if performance improves
        
    async def schedule_updates(self):
        """Schedule automatic model updates"""
        while True:
            await asyncio.sleep(self.update_frequency.total_seconds())
            await self.collect_new_data()
            await self.retrain_model()
```

## 🎯 Performance Targets

### Meteorological Verification Metrics:
- **Probability of Detection (POD)**: >0.85
- **False Alarm Rate (FAR)**: <0.15
- **Critical Success Index (CSI)**: >0.70
- **Lead Time**: 10-30 minutes average
- **Spatial Accuracy**: ±5km tornado location

### Technical Performance:
- **Inference Speed**: <100ms per prediction
- **Model Size**: <500MB for deployment
- **Memory Usage**: <2GB GPU memory
- **CPU Usage**: <50% on inference servers

## 📊 Monitoring and Maintenance

### Model Performance Monitoring:
```python
# Real-time performance tracking
def monitor_model_performance():
    """Track model performance in production"""
    # Compare predictions vs actual tornado reports
    # Calculate skill scores daily/weekly/monthly
    # Alert if performance degrades
    # Generate automated performance reports
```

### Model Versioning:
```bash
# Model version control
git lfs track "*.pt"  # Track model files with Git LFS
mlflow models serve -m models:/tornado_predictor/production
```

## 🔄 Training Pipeline Automation

### Complete Training Pipeline:
```python
# /app/backend/ml_models/training_pipeline.py
class TornadoTrainingPipeline:
    def __init__(self):
        self.data_collector = DataCollector()
        self.preprocessor = DataPreprocessor()
        self.trainer = ModelTrainer()
        self.evaluator = ModelEvaluator()
        
    async def run_full_pipeline(self):
        """Execute complete training pipeline"""
        # 1. Data Collection
        await self.data_collector.download_nexrad_data()
        await self.data_collector.fetch_tornado_database()
        
        # 2. Data Preprocessing
        train_data = self.preprocessor.prepare_training_data()
        val_data = self.preprocessor.prepare_validation_data()
        
        # 3. Model Training
        model = await self.trainer.train_model(train_data, val_data)
        
        # 4. Model Evaluation
        metrics = self.evaluator.evaluate_model(model)
        
        # 5. Model Deployment (if performance acceptable)
        if metrics['csi'] > 0.70:
            await self.deploy_model(model)
            
        return model, metrics
```

This training pipeline will create a production-ready tornado prediction model with real meteorological skill and validation.