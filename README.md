# 🚀 AI Crypto Analyst

A sophisticated multi-agent system for comprehensive cryptocurrency market analysis using LangChain and LangGraph. This system provides automated narrative analysis, fundamental analysis, and technical analysis of cryptocurrency markets through AI-powered agents.

## 🏗️ Project Structure
```
/agents                 - AI agent implementations
    /graphs            - LangGraph workflow definitions
        main_graph.py  - Main orchestration graph
        /sub_graphs    - Specialized analysis sub-graphs
    /schemas           - Pydantic data models and schemas
    /tools             - Specialized tools for agents
        /databases     - MongoDB and InfluxDB connectors
        /narrative_data_getter - News and social media scrapers
        /token_data_getter - Token data and price fetchers
        /technical_calculator - Technical analysis indicators
    llm_model.py       - LLM configuration and setup
/logs                  - Application logs
/mongodb_data         - MongoDB persistent data
/influxdb_data        - InfluxDB time-series data
run.py                - Main entry point and CLI
requirements.txt      - Python dependencies
docker-compose.yml    - Database services configuration
.env                  - Environment variables
analysis_report.md    - Generated analysis reports
graph.png            - Visual workflow representation
```

## ✨ Features

- **🔍 Narrative Analysis**: Automated scraping and analysis of crypto news and social media sentiment
- **📊 Fundamental Analysis**: Deep-dive analysis of token economics, technology, and team information  
- **📈 Technical Analysis**: Price trend analysis with EMA, SMA, RSI, and volume indicators
- **🤖 Multi-Agent Architecture**: Coordinated AI agents using LangGraph workflows
- **📝 Markdown Reports**: Professionally formatted analysis reports
- **🗄️ Persistent Storage**: MongoDB for analysis data, InfluxDB for time-series data
- **⚙️ Configurable**: Command-line options for customized analysis

## 🚀 Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- Docker and Docker Compose
- Git

### 2. Virtual Environment

```bash
# Clone the repository
git clone <repository-url>
cd ai-crypto-analyst

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\Activate

# Activate virtual environment (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup with Docker

The project uses MongoDB for storing analytical results and InfluxDB for time-series data.

```bash
# Start the database services
docker-compose up -d

# Check if services are running
docker-compose ps

# Stop services when done
docker-compose down
```

Access points:
- MongoDB: mongodb://localhost:27017
- InfluxDB UI: http://localhost:8086

### 4. Environment Variables

Copy and configure your `.env` file with the required API keys:

```bash
# Required API Keys for data sources
CRYPTO_PANIC_AUTH_TOKEN=your_crypto_panic_token
COIN_DESK_API_KEY=your_coindesk_api_key
COINMARKETCAP_API_KEY=your_coinmarketcap_key
COINGECKO_API_KEY=your_coingecko_key
VERTEX_API_KEY=your_google_vertex_ai_key

# Database Configuration
INFLUXDB_USERNAME=admin
INFLUXDB_PASSWORD=your_secure_password
INFLUXDB_ORG=crypto_org
INFLUXDB_BUCKET=crypto_data
INFLUXDB_TOKEN=your_influxdb_token

# Optional: Twitter credentials for social sentiment
TWITTER_EMAIL_MAIN=your_twitter_email
# ... other Twitter API keys
```

### 5. Running the Application

```bash
# Basic analysis
python run.py

# Run with debug logging
python run.py --debug

# Limit analysis to specific number of tokens
python run.py --max-tokens 50

# Skip data scraping and use existing data only
python run.py --skip-scraping

# Custom report filename
python run.py --save-report my_custom_report.md

# View all options
python run.py --help
```

## 📊 Usage Examples

### Basic Analysis
```bash
python run.py
```

### Advanced Usage
```bash
# Debug mode with limited tokens
python run.py --debug --max-tokens 100

# Quick analysis using existing data
python run.py --skip-scraping --save-report quick_analysis.md
```

## 📋 Output

The system generates a comprehensive Markdown report (`analysis_report.md`) containing:

1. **Narrative Analysis**: Current market trends and emerging narratives
2. **Fundamental Analysis**: Token-by-token deep analysis including:
   - Project summaries and technology reviews
   - Tokenomics and team analysis
   - Market positioning and competitive analysis
3. **Technical Analysis**: Price trend analysis with:
   - Moving averages (EMA/SMA) and crossover signals
   - RSI momentum indicators
   - Volume analysis and trend confirmation
4. **Investment Insights**: Data-driven recommendations based on comprehensive analysis

## 🗄️ Database Information

### MongoDB
- **URL**: mongodb://localhost:27017
- **Database**: crypto_analytics
- **Collections**:
  - `narrative_data` - News articles and social media posts
  - `token_identities` - Token metadata and identifiers
  - `analysis_results` - Stored analysis outputs

### InfluxDB
- **URL**: http://localhost:8086
- **Organization**: crypto_org
- **Bucket**: crypto_data
- **Use Case**: Time-series price data and technical indicators

⚠️ **Security Note**: Update default credentials in `docker-compose.yml` and `.env` for production use.

## 🛠️ Architecture Overview

The system uses a multi-agent architecture built on LangGraph:

1. **Main Graph (`main_graph.py`)**: Orchestrates the entire analysis pipeline
2. **Narrative Analysis Sub-graph**: Processes news and social data to identify market trends
3. **Fundamental Analysis Sub-graph**: Analyzes token fundamentals and project metrics
4. **Technical Analysis Sub-graph**: Performs price trend and momentum analysis
5. **Report Generation**: Compiles all analyses into a comprehensive Markdown report

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   ```bash
   # Ensure Docker services are running
   docker-compose ps
   docker-compose up -d
   ```

2. **Missing API Keys**:
   - Check your `.env` file has all required API keys
   - Verify API key validity with respective providers

3. **Import Errors**:
   ```bash
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

4. **Memory Issues with Large Analysis**:
   ```bash
   # Use token limits to reduce scope
   python run.py --max-tokens 50
   ```

### Debug Mode
```bash
# Get detailed error information
python run.py --debug
```

## 📚 Dependencies

Key dependencies include:
- `langchain` - LLM framework
- `langgraph` - Multi-agent workflows  
- `pymongo` - MongoDB integration
- `influxdb-client` - Time-series database
- `beautifulsoup4` - Web scraping
- `requests` - HTTP client

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the terms specified in the LICENSE file.
