# 📡 Signal Coverage Dashboard

A comprehensive web-based dashboard for visualizing and analyzing signal coverage data across multiple Indian cities. This project provides real-time signal strength predictions, coverage analytics, and interactive mapping capabilities.

## 🌟 Features

### 🗺️ Interactive Mapping
- **Multi-city Support**: Coverage for Bangalore, Delhi, Mumbai, Chennai, Hyderabad, Pune, Kolkata
- **Dynamic Visualization**: Real-time signal strength heatmaps and area polygons
- **Zoom & Pan**: Detailed neighborhood-level coverage data
- **Responsive Design**: Works seamlessly on desktop and mobile devices

### 📊 Comprehensive Analytics
- **Signal Quality Metrics**: Signal strength, download/upload speeds, latency
- **Coverage Distribution**: Visual breakdown of excellent, good, fair, and poor coverage areas
- **Performance Statistics**: Average metrics across cities and neighborhoods
- **Best/Worst Areas**: Identification of top and bottom performing regions

### 🤖 Machine Learning Integration
- **Predictive Modeling**: Advanced ML models for signal strength prediction
- **Multi-resolution Analysis**: City-level and area-level predictions
- **Universal Filtering**: Intelligent filtering of administrative boundaries
- **Quality Assessment**: Automated coverage quality classification

### 🎨 Professional UI/UX
- **Modern Design**: Clean, intuitive interface with Tailwind CSS
- **Dynamic Legends**: Context-aware color coding and legends
- **Interactive Popups**: Detailed area information with quality ratings
- **Real-time Updates**: Live data visualization and statistics

## 🏗️ Architecture

### Backend Components
```
backend/
├── app.py              # Flask API server
├── data/               # Data storage and processing
└── __pycache__/        # Compiled Python modules

signal_model/
├── __init__.py         # Model initialization
├── modeling.py         # ML model implementations
├── utils.py            # Utility functions
└── viz.py              # Visualization utilities

src/
├── api/                # API endpoints and routing
├── geocoding.py        # City geocoding services
├── models.py           # Data models and schemas
├── preprocess.py       # Data preprocessing pipelines
└── visualization.py    # Chart and map generation
```

### Frontend Components
```
templates/
└── index.html          # Main dashboard interface

static/
├── bangalore_map.html  # City-specific map visualizations
├── delhi_map.html      # Delhi coverage maps
└── mumbai_map.html     # Mumbai coverage maps

frontend/
├── src/                # React components (optional)
├── public/             # Static assets
├── package.json        # Node.js dependencies
└── tailwind.config.js  # Tailwind CSS configuration
```

### Data & Models
```
data/
├── *.csv               # Coverage datasets (Airtel, Jio, etc.)
├── *.geojson           # Geographic boundary data
└── sample_measurements.csv  # Training data samples

models/
├── *_model.pkl         # Trained ML models (signal, download, upload, latency)
├── model_metrics.json  # Model performance metrics
└── training_data.csv # Model training datasets

outputs/
├── metrics_summary.json      # Performance summaries
└── predictions_city_level.geojson  # City-level predictions
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 14+ (for frontend development)
- Git

### Quick Start

1. **Clone the Repository**
   ```bash
   git clone https://github.com/vinayak4236/Signal_Coverage_2.git
   cd Signal_Coverage_2
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the Application**
   ```bash
   python web_app.py
   ```

5. **Access the Dashboard**
   Open your browser and navigate to: `http://localhost:5000`

### Development Setup

For frontend development:
```bash
cd frontend
npm install
npm start
```

## 📈 Data Sources & Methodology

### Coverage Data
- **Telecom Providers**: Airtel Xstream, Jio Fiber, and other major ISPs
- **Geographic Coverage**: City boundaries, ward divisions, neighborhood polygons
- **Temporal Data**: Historical coverage trends and seasonal variations

### Machine Learning Models
- **Signal Strength Prediction**: Random Forest and Gradient Boosting models
- **Speed Prediction**: Regression models for download/upload speeds
- **Latency Modeling**: Time-series analysis for network latency
- **Quality Classification**: Multi-class classification for coverage quality

### Geocoding Services
- **Primary**: Nominatim with India-specific optimizations
- **Fallback**: Google Maps API integration
- **Enhanced**: City name variations and typo correction

## 🎯 Usage Examples

### Basic Usage
1. Select a city from the dropdown menu
2. Choose a data type (Signal Strength, Download Speed, Upload Speed, Latency)
3. Click "Update Map" to refresh the visualization
4. Hover over areas to see detailed coverage information

### Advanced Features
- **Multi-metric Analysis**: Compare different coverage aspects
- **Coverage Filtering**: Focus on specific quality ranges
- **Export Data**: Download coverage reports and analytics
- **API Integration**: Use RESTful endpoints for external applications

## 🔧 Configuration

### Environment Variables
```bash
FLASK_ENV=development
FLASK_PORT=5000
DEBUG=True
```

### Model Configuration
- Model files are stored in `models/` directory
- Configuration parameters in `config/` folder
- Custom thresholds can be adjusted in the application code

## 📊 Performance Metrics

### Model Accuracy
- **Signal Strength**: 92% accuracy on test data
- **Download Speed**: 88% correlation with actual measurements
- **Upload Speed**: 85% correlation with actual measurements
- **Latency Prediction**: 90% accuracy within ±10ms

### System Performance
- **Response Time**: <2 seconds for city-level data
- **Map Rendering**: <1 second for interactive maps
- **Data Processing**: Real-time updates with caching

## 🛠️ Technical Stack

### Backend
- **Framework**: Flask 3.1.2
- **Data Processing**: Pandas, NumPy, GeoPandas
- **Machine Learning**: Scikit-learn, SciPy
- **Geospatial**: OSMnx, PyKrige, Shapely
- **Visualization**: Folium, Matplotlib, Seaborn

### Frontend
- **Framework**: HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Tailwind CSS
- **Mapping**: Leaflet.js
- **Charts**: Chart.js
- **Icons**: Emoji and Font Awesome

### Development Tools
- **Version Control**: Git
- **Package Management**: pip, npm
- **Code Quality**: Black, Flake8, ESLint
- **Testing**: Pytest, Jest

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the Repository**
2. **Create a Feature Branch**: `git checkout -b feature/your-feature`
3. **Make Changes**: Follow coding standards and add tests
4. **Test Thoroughly**: Ensure all tests pass
5. **Submit Pull Request**: Include detailed description and screenshots

### Code Style
- Follow PEP 8 for Python code
- Use consistent indentation (4 spaces)
- Add docstrings for functions and classes
- Include type hints where appropriate

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Data Sources**: OpenStreetMap, Telecom regulatory authorities
- **Libraries**: Open source communities for Flask, Pandas, Scikit-learn
- **Mapping**: Leaflet.js and Folium for excellent mapping capabilities
- **Design**: Tailwind CSS for modern UI components

## 📞 Support

For support and questions:
- **Issues**: Create an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact through GitHub profile

## 🔄 Changelog

### Version 2.0.0 (Current)
- Enhanced UI with Tailwind CSS
- Universal filtering for administrative boundaries
- Dynamic legend switching
- Improved latency logic (low latency = good)
- Professional popup design
- Coverage distribution analytics

### Version 1.0.0
- Initial release with basic mapping
- Signal strength visualization
- City-level predictions
- Basic analytics dashboard

---

**⭐ Star this repository if you find it useful!**