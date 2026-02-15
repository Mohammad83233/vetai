# VetAI - AI-Enabled Veterinary Clinical Decision Support System

A production-ready, full-stack system that assists veterinarians with multi-species disease prediction, multi-modal input processing, intelligent follow-up questions, treatment recommendations, token-based patient management, and automated SOAP clinical reports.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB 7.0+ (or Docker)

### Option 1: Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Create .env file
copy .env.example .env

# Start MongoDB (must be running)
# Start backend
uvicorn app.main:app --reload
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

## 🏗️ Architecture

```
vetai/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── main.py         # Application entry
│   │   ├── config.py       # Configuration
│   │   ├── database.py     # MongoDB connection
│   │   ├── models/         # Pydantic models
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Business logic
│   │   └── ai/             # ML pipelines
│   └── requirements.txt
├── frontend/                # React Frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API clients
│   │   ├── context/        # State management
│   │   └── styles/         # CSS
│   └── package.json
├── docker-compose.yml
└── mongo-init.js           # DB initialization
```

## 🔧 API Endpoints

| Module | Endpoint | Description |
|--------|----------|-------------|
| Auth | `POST /auth/login` | User login |
| Auth | `POST /auth/register` | User registration |
| Queue | `POST /queue/tokens` | Issue token |
| Queue | `GET /queue/display` | Get queue status |
| Queue | `POST /queue/call` | Call next patient |
| Patients | `POST /patients` | Register patient |
| Patients | `GET /patients` | Search patients |
| Diagnosis | `POST /diagnosis/predict` | AI disease prediction |
| Treatment | `POST /treatment/recommend` | Get treatment plan |
| Treatment | `POST /treatment/dosage` | Calculate dosage |
| Reports | `POST /reports/generate` | Generate SOAP report |
| Reports | `POST /reports/export` | Export PDF/HTML/JSON |

## 🔐 User Roles

- **Admin**: Full system access
- **Doctor**: Diagnosis, treatment, reports
- **Staff**: Patient registration, token management

## 🧠 AI Features

### Disease Prediction
- Multi-species support (dog, cat, bird, rabbit, etc.)
- Probability-ranked predictions
- Follow-up question generation
- Iterative diagnosis refinement

### Treatment Planning
- Evidence-based recommendations
- Auto-calculated dosages (weight, age, species adjusted)
- Contraindication alerts
- Drug interaction warnings

### SOAP Reports
- Auto-generated from clinical data
- PDF export with ReportLab
- Structured S/O/A/P sections

## 📝 License

MIT License
