# 🌪️ Storm Oracle - Advanced Weather Radar Intelligence

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18+](https://img.shields.io/badge/react-18.0+-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-4.4+-47A248.svg)](https://www.mongodb.com/)

**Storm Oracle** is a state-of-the-art weather radar monitoring application that provides real-time weather visualization, AI-powered storm prediction, and comprehensive tornado analysis. Built with modern web technologies and featuring professional-grade radar visualization similar to industry-standard tools like Radar Omega.

## 🌟 Key Features

### 🎯 **Real-Time Weather Radar**
- **National Coverage**: Live weather radar data across the entire United States
- **139 NEXRAD Stations**: Complete coverage of all National Weather Service radar sites
- **Smooth Animation**: Seamless 30-second interval updates showing storm movement like watching clouds in real-time
- **Multiple Data Types**: Base Reflectivity, Hi-Res Reflectivity, Base Velocity, Storm-Relative Velocity
- **Circular Coverage**: Authentic 230km NEXRAD radar range visualization

### 🤖 **AI-Powered Storm Analysis**
- **Dual AI System**: Custom PyTorch ML model + Claude Sonnet integration
- **Tornado Prediction**: Advanced neural network for tornado formation prediction
- **Real-Time Monitoring**: Continuous scanning and threat assessment
- **Storm Cell Tracking**: Automated detection and analysis of severe weather
- **Risk Assessment**: Probability calculations for tornado development

### 🗺️ **Interactive Visualization**
- **Professional UI**: Meteorologist-grade interface with customizable controls
- **Full-Screen Mode**: Immersive weather monitoring experience
- **Animation Controls**: Play/pause, speed adjustment, frame-by-frame analysis
- **Color Palettes**: Multiple radar color schemes for different data types
- **Zoom & Pan**: Seamless map navigation with responsive controls

### 👤 **User Management**
- **Secure Authentication**: JWT-based login system with email verification
- **Subscription Tiers**: Free, Premium, and Admin access levels
- **Password Recovery**: Email-based password reset functionality
- **Profile Management**: User settings and preferences

### 📧 **Smart Notifications**
- **Email Alerts**: Automated severe weather notifications
- **Storm Tracking**: Real-time updates on developing weather systems
- **Custom Zones**: Personalized alert areas (Premium feature)

## 🚀 Technology Stack

### **Frontend**
- **React 18+** with modern hooks and context
- **Tailwind CSS** for responsive styling
- **Leaflet Maps** for interactive geographic visualization
- **Axios** for API communication
- **Shadcn/ui** for professional UI components

### **Backend**
- **FastAPI** for high-performance API development
- **PyART** for professional weather radar data processing
- **PyTorch** for custom ML tornado prediction models
- **MongoDB** for flexible data storage
- **JWT Authentication** for secure user sessions
- **FastAPI-Mail** for email notifications

### **AI & Machine Learning**
- **Custom TornadoSuperPredictor**: Multi-modal deep learning model
- **Claude Sonnet Integration**: Advanced natural language weather analysis
- **Emergent LLM**: Seamless AI integration for contextual insights
- **Real-time Data Processing**: Continuous ML-powered threat assessment

### **Infrastructure**
- **Docker** containerization
- **Kubernetes** for orchestration and scaling
- **MongoDB Atlas** for cloud database
- **Email Services** for user communications

## 💰 Pricing Plans

### 🆓 **Free Tier**
**$0/month**
- National weather radar view
- Basic storm alerts
- 139 NEXRAD station access
- Standard radar data types
- Community support

### ⭐ **Premium Monthly**
**$19.99/month**
- Everything in Free tier
- Real-time tornado tracking
- Advanced storm predictions
- Historical radar data access
- Custom alert zones
- Priority email support
- API access (1000 calls/month)
- Advanced radar data types
- Full-screen mode
- Animation controls

### 💎 **Premium Annual**
**$199.99/year** *(Save $39.89 - 17% discount)*
- Everything in Premium Monthly
- Extended API access (5000 calls/month)
- Priority customer support
- Advanced ML insights
- Historical weather data
- Custom notification settings
- Early access to new features

### 🏢 **Enterprise**
**Contact for Pricing**
- Everything in Premium Annual
- Unlimited API access
- White-label solutions
- Custom integrations
- 24/7 priority support
- Advanced analytics
- Multi-user management
- Custom ML model training

## 🛠️ Installation

### Prerequisites
- **Node.js** 18+ and npm/yarn
- **Python** 3.11+
- **MongoDB** 4.4+
- **Docker** (optional but recommended)

### Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/yourusername/storm-oracle.git
cd storm-oracle

# Start with Docker Compose
docker-compose up -d

# Access the application
open http://localhost:3000
```

### Manual Installation

#### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Start the backend server
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

#### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
# or
yarn install

# Set environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start the development server
npm start
# or
yarn start
```

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=storm_oracle
JWT_SECRET_KEY=your-super-secret-jwt-key
EMERGENT_LLM_KEY=your-emergent-llm-key
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
ADMIN_SECRET_CODE=your-admin-secret
ADMIN_EMAILS=admin@example.com,admin2@example.com
```

#### Frontend (.env.local)
```env
REACT_APP_BACKEND_URL=http://localhost:8001
REACT_APP_APP_NAME=Storm Oracle
```

## 📚 API Documentation

### Authentication Endpoints
```
POST   /api/auth/register          # Register new user
POST   /api/auth/login             # User login
POST   /api/auth/verify-email      # Verify email address
POST   /api/auth/forgot-password   # Request password reset
POST   /api/auth/reset-password    # Reset password
GET    /api/auth/me               # Get current user info
```

### Weather Data Endpoints
```
GET    /api/radar-stations         # Get all NEXRAD stations
GET    /api/radar-data/{station}   # Get radar data for station
GET    /api/radar-image/{station}  # Get radar image
GET    /api/radar-image/national   # Get national radar composite
GET    /api/active-storms          # Get current storm cells
```

### AI Analysis Endpoints
```
POST   /api/analyze/tornado        # AI tornado analysis
POST   /api/analyze/storm          # Storm analysis
GET    /api/monitoring/status      # Get monitoring status
```

### Premium Features
```
GET    /api/premium/advanced-features  # Premium feature access
GET    /api/premium/historical-data    # Historical weather data
POST   /api/premium/custom-alerts      # Custom alert zones
```

## 🎮 Usage Examples

### Basic Radar Data Access
```javascript
// Get national radar data
const response = await fetch('/api/radar-data/NATIONAL?data_type=base_reflectivity');
const radarData = await response.json();

// Get specific station data
const stationData = await fetch('/api/radar-data/KEAX?data_type=base_velocity');
```

### User Authentication
```javascript
// Register new user
const registerResponse = await fetch('/api/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'securepassword',
    full_name: 'John Doe'
  })
});

// Login user
const loginResponse = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'securepassword'
  })
});
```

### AI Analysis
```javascript
// Request tornado analysis
const analysis = await fetch('/api/analyze/tornado', {
  method: 'POST',
  headers: { 
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    station_id: 'KEAX',
    latitude: 38.8103,
    longitude: -94.2645
  })
});
```

## 🖼️ Screenshots

### National Weather Radar View
- Real-time weather patterns across the United States
- All 139 NEXRAD stations displayed as interactive markers
- Smooth animation showing storm movement

### Interactive Station Selection
- Click any radar station for detailed local coverage
- Circular 230km NEXRAD coverage area
- Professional radar color schemes

### AI Storm Analysis
- Real-time tornado prediction and tracking
- Storm cell identification and intensity analysis
- Risk probability calculations

### Premium Dashboard
- Advanced features for premium subscribers
- Historical data access and custom alert zones
- Enhanced visualization tools

## 🤝 Contributing

We welcome contributions from the community! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting pull requests.

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- **Frontend**: ESLint + Prettier configuration
- **Backend**: Black formatter + flake8 linting
- **Commits**: Conventional commit format

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
# or
yarn test
```

### Integration Tests
```bash
# Run full test suite
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **National Weather Service** for providing NEXRAD radar data
- **PyART Community** for radar data processing tools
- **OpenWeather** for additional weather data sources
- **Leaflet** for excellent mapping capabilities
- **FastAPI** for the incredible web framework

## 📞 Support

### Community Support (Free Tier)
- GitHub Issues for bug reports
- Community discussions
- Documentation and guides

### Premium Support
- Email support: support@stormoracle.com
- Priority issue resolution
- Feature requests

### Enterprise Support
- 24/7 dedicated support
- Custom integrations
- Phone and video support
- Account management

## 🔗 Links

- **Live Demo**: [https://demo.stormoracle.com](https://demo.stormoracle.com)
- **Documentation**: [https://docs.stormoracle.com](https://docs.stormoracle.com)
- **API Reference**: [https://api.stormoracle.com/docs](https://api.stormoracle.com/docs)
- **Status Page**: [https://status.stormoracle.com](https://status.stormoracle.com)

## 🚀 Roadmap

### Q4 2024
- [ ] Mobile app development (iOS/Android)
- [ ] Advanced weather models integration
- [ ] Real-time collaboration features
- [ ] Enhanced AI predictions

### Q1 2025
- [ ] European weather radar support
- [ ] Advanced analytics dashboard
- [ ] API rate limiting improvements
- [ ] Multi-language support

### Q2 2025
- [ ] Machine learning model improvements
- [ ] Satellite imagery integration
- [ ] Climate change tracking features
- [ ] Advanced notification system

---

**Built with ❤️ by the Storm Oracle Team**

*Bringing professional-grade weather intelligence to everyone*
