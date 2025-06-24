# AI Crypto Analyst

A multi-agent system for cryptocurrency analysis using LangChain and LangGraph.

## Project Structure
```
/agents            - Agent implementations
    /tools         - Tools used by agents
    /data          - Local data files
/utils             - Utility functions
main.py            - Main entry point
requirements.txt   - Python dependencies
docker-compose.yml - Database services
.env              - Environment variables
.gitignore        - Git ignore rules
```

## Setup Instructions

### 1. Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\Activate

# Activate virtual environment (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup with Docker

The project uses MongoDB for storing analytical results and InfluxDB for time-series data.

```bash
# Start the database services
docker-compose up -d

# Check if services are running
docker-compose ps
```

Access points:
- MongoDB: mongodb://localhost:27017
- InfluxDB UI: http://localhost:8086

### 3. Environment Variables

Copy the `.env.example` file to `.env` and fill in your API keys:

```bash
# API Keys
OPENAI_API_KEY=your_openai_api_key_here

# ... other configuration
```

### 4. Running the application

```bash
python main.py
```

## Database Information

### MongoDB

- **URL**: mongodb://admin:admin_password@localhost:27017/crypto_analytics
- **Database**: crypto_analytics
- **Default User**: admin
- **Default Password**: admin_password

### InfluxDB

- **URL**: http://localhost:8086
- **Organization**: crypto_org
- **Bucket**: crypto_data
- **Token**: your-super-secret-token (replace with a secure token)

Remember to update the credentials in both the docker-compose.yml and .env files for production use.
