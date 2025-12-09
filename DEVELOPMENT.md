# Development Guide

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### Installation

1. **Clone the repository** (if not already done)
   ```bash
   git clone <repository-url>
   cd fintech-risk-agent
   ```

2. **Set up Python virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate virtual environment**
   - Windows: `.venv\Scripts\activate`
   - Unix/Linux: `source .venv/bin/activate`

4. **Install Python dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

5. **Install Node.js dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

### Running the Application

#### Option 1: Using Startup Scripts (Recommended)

**Windows:**
```bash
start.bat
```

**Unix/Linux:**
```bash
./start.sh
```

This will start both backend and frontend servers automatically.

#### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd fintech-risk-agent
.venv\Scripts\activate  # or source .venv/bin/activate
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd fintech-risk-agent/frontend
npm run dev
```

### Access Points

- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation (Swagger)**: http://localhost:8000/api-docs
- **API Documentation (ReDoc)**: http://localhost:8000/api-redoc

## Project Structure

```
fintech-risk-agent/
├── backend/                    # Python FastAPI Backend
│   ├── app/
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── api/routes/        # API endpoint routes
│   │   │   ├── health.py      # Health check endpoint
│   │   │   ├── scoring.py     # Transaction scoring endpoints
│   │   │   ├── analytics.py   # Analytics endpoints
│   │   │   ├── dashboard.py   # Dashboard data endpoints
│   │   │   ├── file_upload.py # File upload & analysis
│   │   │   └── advanced_analytics_routes.py
│   │   ├── core/
│   │   │   ├── config.py      # Configuration management
│   │   │   └── decision_engine.py # Risk decision engine
│   │   ├── models/
│   │   │   └── schemas.py     # Pydantic data models
│   │   └── services/          # Business logic services
│   ├── config/
│   │   └── model_config.yaml  # Model configuration
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # Vite + Vanilla JS Frontend
│   ├── src/
│   │   ├── css/               # Stylesheets
│   │   └── js/                # JavaScript modules
│   ├── index.html             # Main dashboard
│   ├── classic.html           # Classic dashboard view
│   ├── enhanced.html          # Enhanced analytics view
│   ├── package.json           # Node dependencies
│   └── vite.config.js         # Vite configuration
│
├── deployment/                 # Deployment configurations
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── render.yaml
│   └── Procfile
│
├── start.bat                   # Windows startup script
├── start.sh                    # Unix/Linux startup script
└── README.md                   # Project documentation
```

## API Endpoints

### Health & Status
- `GET /health` - Health check

### Transaction Scoring
- `POST /score` - Score a single transaction
- `POST /batch-score` - Score multiple transactions

### Analytics
- `GET /metrics` - Get system metrics
- `GET /history` - Get scoring history
- `GET /analytics` - Get analytics data

### File Processing
- `POST /upload-and-analyze` - Upload and analyze transaction file (CSV/JSON/Excel)
- `POST /analyze-transactions` - Analyze transactions from JSON payload

### Dashboard
- Dashboard routes for serving frontend

## Features

### Real-Time Fraud Detection
- Multi-dimensional risk profiling
- Anomaly detection using Isolation Forest and Local Outlier Factor
- Fraud network detection using graph analysis
- Money laundering pattern detection
- Comprehensive entity risk scoring

### File Upload Support
- CSV files
- JSON/JSONL files
- Excel files (XLSX/XLS)

### Advanced Analytics
- Risk distribution visualization
- Pattern detection
- Entity profiling
- Network analysis
- Red flag identification

## Development Tips

### Backend Development

1. **Hot Reload**: The backend runs with `--reload` flag, so changes are automatically detected
2. **API Testing**: Use the Swagger UI at http://localhost:8000/api-docs
3. **Logging**: Check console output for API logs

### Frontend Development

1. **Hot Reload**: Vite provides instant hot module replacement
2. **Proxy**: Frontend proxies API calls to backend automatically
3. **Build**: Run `npm run build` to create production build

### Testing

```bash
# Backend tests
cd backend
pytest

# Frontend build test
cd frontend
npm run build
```

## Common Issues

### Port Already in Use
If ports 8000 or 3000 are already in use:
- Change backend port in `backend/app/main.py` (line 86)
- Change frontend port in `frontend/vite.config.js` (line 18)

### Module Not Found
Ensure all dependencies are installed:
```bash
pip install -r backend/requirements.txt
cd frontend && npm install
```

### python-multipart Missing
If you see "python-multipart" error:
```bash
pip install python-multipart
```

## Deployment

### Using Docker
```bash
cd deployment
docker-compose up
```

### Using Render
Deploy using the `deployment/render.yaml` configuration.

### Manual Deployment
1. Build frontend: `cd frontend && npm run build`
2. Deploy backend with Procfile command
3. Set environment variables as needed

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

Proprietary - Fintech Risk & Insights Agent
