<![CDATA[<div align="center">

# 🌵 CACTI Automation

**Enterprise-grade automated network monitoring data extraction system**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

*Automate the extraction, processing, and analysis of network traffic data from CACTI monitoring systems*

[Features](#-features) •
[Quick Start](#-quick-start) •
[Installation](#-installation) •
[Configuration](#-configuration) •
[Usage](#-usage) •
[API Reference](#-api-reference) •
[Docker](#-docker-deployment) •
[Contributing](#-contributing)

</div>

---

## 📋 Overview

CACTI Automation is a comprehensive solution for extracting and processing network monitoring data from CACTI systems. It implements a **3-step pipeline architecture**:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   SCRAPE    │────▶│     OCR     │────▶│    CLEAN    │
│  (Selenium) │     │  (EasyOCR)  │     │  (Pandas)   │
└─────────────┘     └─────────────┘     └─────────────┘
      ▼                   ▼                   ▼
   Screenshots        JSON Data          CSV Reports
```

### Key Capabilities

- **Automated Scraping**: Browser-based data extraction using Selenium WebDriver
- **OCR Processing**: Advanced image-to-text conversion with EasyOCR
- **Data Cleaning**: Intelligent parsing and unit conversion (Gbps, Mbps, Kbps)
- **Web Dashboard**: Flask-based interface for monitoring and data visualization
- **Enterprise Ready**: Docker support, comprehensive logging, and security features

---

## ✨ Features

### Core Features

| Feature | Description |
|---------|-------------|
| 🔄 **3-Step Pipeline** | Scrape → OCR → Clean workflow for complete data processing |
| 🌐 **Web Interface** | Flask-based dashboard with Chart.js visualization |
| 🤖 **Browser Automation** | Headless Chrome/Firefox support via Selenium |
| 📊 **Multi-format Output** | CSV exports in Original, Mbps, and Kbps formats |
| 🔒 **Security** | SSRF protection, URL allowlisting, credential masking |

### Enterprise Features

| Feature | Description |
|---------|-------------|
| 🐳 **Docker Ready** | Production-ready containerization with docker-compose |
| ⚙️ **Type-safe Config** | Pydantic-based settings with environment variable support |
| 📝 **Comprehensive Logging** | Structured logging with rotation and debug levels |
| 🧪 **Testing Suite** | pytest with coverage reporting |
| 🔍 **Code Quality** | Ruff, Black, and MyPy integration |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Chrome/Chromium** browser (for Selenium)
- **Git**

### 30-Second Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/cacti-automation.git
cd cacti-automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your CACTI credentials

# Run the pipeline
python main_pipeline.py
```

---

## 📦 Installation

### Option 1: Standard Installation

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Option 2: Docker Installation

```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Option 3: Development Installation

```bash
# Install with development dependencies
pip install -r requirements.txt

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

### Required Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `CACTI_USERNAME` | CACTI login username | *Required* |
| `CACTI_PASSWORD` | CACTI login password | *Required* |
| `CACTI_BASE_URL` | CACTI server URL | *Required* |

### Optional Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ENV` | Environment mode | `development` |
| `DEBUG` | Enable debug mode | `false` |
| `HOST` | Web server host | `127.0.0.1` |
| `PORT` | Web server port | `5000` |
| `SELENIUM_HEADLESS` | Run browser headless | `false` |
| `SELENIUM_WAIT_TIMEOUT` | Element wait timeout (seconds) | `15` |
| `OCR_GPU_ENABLED` | Enable GPU for OCR | `false` |
| `OCR_BATCH_SIZE` | OCR processing batch size | `4` |
| `OCR_LANGUAGES` | OCR languages (comma-separated) | `en` |

### Security Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `CACTI_ALLOWED_URLS` | Comma-separated allowlist for SSRF protection | *Required* |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5000` |

<details>
<summary>📄 Full Configuration Example</summary>

```ini
# Environment
ENV=production
DEBUG=false

# CACTI
CACTI_BASE_URL=https://your-cacti-server.com/
CACTI_ALLOWED_URLS=https://your-cacti-server.com/
CACTI_USERNAME=your_username
CACTI_PASSWORD=your_secure_password

# Web Server
HOST=0.0.0.0
PORT=5000
CORS_ORIGINS=https://your-domain.com

# Selenium
SELENIUM_HEADLESS=true
SELENIUM_WAIT_TIMEOUT=30
SELENIUM_PAGE_LOAD_TIMEOUT=60

# OCR
OCR_GPU_ENABLED=true
OCR_BATCH_SIZE=8
OCR_LANGUAGES=en,id

# Storage
OUTPUT_DIR=output
LOG_DIR=logs
```

</details>

---

## 📖 Usage

### Running the Pipeline

#### Full Pipeline Execution

```bash
python main_pipeline.py
```

This executes all three steps in sequence:
1. **Step 1**: Scrape images from CACTI dashboard
2. **Step 2**: Process images with OCR
3. **Step 3**: Clean and export to CSV

#### Running Individual Steps

```python
from main_pipeline import step1_scrape_images, step2_ocr_images, step3_clean_csv

# Step 1: Scrape data
step1_scrape_images(
    date1="2025-01-01 00:00",
    date2="2025-01-31 23:59",
    target_url="https://your-cacti-server.example.com/",
    userLogin="your_username",
    userPass="your_password",
    usernames=["device1", "device2"]
)

# Step 2: OCR processing
step2_ocr_images(folder="output/2025-01-15_12-00-00")

# Step 3: Clean CSV
step3_clean_csv(csv_input="output/2025-01-15_12-00-00/raw.csv")
```

### Web Dashboard

Start the Flask web application:

```bash
# Development
python App.py

# Production (with Waitress)
waitress-serve --host=0.0.0.0 --port=5000 web.app:app
```

Access the dashboard at: `http://localhost:5000`

### Output Structure

```
output/
└── 2025-01-15_12-00-00/           # Timestamp folder
    ├── raw_screenshots/            # Raw scraped images
    │   ├── device1_graph1.png
    │   └── device2_graph2.png
    ├── processed_output/           # OCR JSON results
    │   └── ocr_results.json
    ├── hasil_original_*.csv        # Original values
    ├── hasil_mbps_*.csv            # Values in Mbps
    └── hasil_kbps_*.csv            # Values in Kbps
```

---

## 🔌 API Reference

### Web Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard home page |
| `/api/titles` | GET | Get unique device titles |
| `/api/data` | GET | Fetch data by title and date range |
| `/api/add-url` | POST | Add new URL for scraping |

### Python API

```python
from config import settings

# Access configuration
print(settings.CACTI_BASE_URL)
print(settings.is_production)

# Validate URLs (SSRF protection)
from config import validate_cacti_url
is_valid, error = validate_cacti_url("https://example.com")
```

---

## 🐳 Docker Deployment

### Quick Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Docker Compose Configuration

The `docker-compose.yml` includes:
- **Web Application**: Flask app with Waitress server
- **Volume Mounts**: Persistent storage for output and logs
- **Environment Variables**: Loaded from `.env` file

### Building Custom Image

```bash
# Build image
docker build -t cacti-automation:latest .

# Run container
docker run -d \
  --name cacti-automation \
  -p 5000:5000 \
  -v ./output:/app/output \
  --env-file .env \
  cacti-automation:latest
```

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run excluding slow tests
pytest -m "not slow"
```

### Code Quality

```bash
# Linting with Ruff
ruff check .

# Format with Black
black .

# Type checking with MyPy
mypy .

# Security audit
pip-audit
```

---

## 📁 Project Structure

```
cacti-automation/
├── 📄 App.py                  # Flask app entry point
├── 📄 main_pipeline.py        # 3-step pipeline orchestrator
├── 📄 config.py               # Pydantic configuration
├── 📄 Dockerfile              # Container definition
├── 📄 docker-compose.yml      # Docker orchestration
├── 📄 requirements.txt        # Python dependencies
├── 📄 pyproject.toml          # Tool configurations
│
├── 📁 web/                    # Flask web application
│   ├── app.py                 # Flask app factory
│   └── routes.py              # API endpoints
│
├── 📁 scraping/               # Selenium scrapers
│   ├── cacti_scraper.py       # Main scraping logic
│   └── selenium_utils.py      # WebDriver utilities
│
├── 📁 ocr/                    # OCR processing
│   ├── ocr_processor.py       # EasyOCR integration
│   └── parallel_processor.py  # Parallel OCR processing
│
├── 📁 cleaning/               # Data cleaning
│   ├── csv_generator.py       # CSV output generation
│   └── data_parser.py         # Value parsing utilities
│
├── 📁 storage/                # Data storage
│   └── __init__.py
│
├── 📁 models/                 # EasyOCR model files
│
├── 📁 templates/              # Jinja2 HTML templates
├── 📁 static/                 # CSS, JS, images
│
├── 📁 tests/                  # Test suite
│   ├── test_config.py
│   └── test_pipeline.py
│
└── 📁 observability/          # Logging & monitoring
    └── logging_setup.py
```

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### Development Guidelines

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide
- Write tests for new features
- Update documentation as needed
- Run linters before committing

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [CACTI](https://www.cacti.net/) - Network monitoring platform
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) - OCR library
- [Selenium](https://selenium.dev/) - Browser automation
- [Flask](https://flask.palletsprojects.com/) - Web framework

---

<div align="center">

**Made with ❤️ for Network Operations Teams**

[⬆ Back to Top](#-cacti-automation)

</div>
]]>
