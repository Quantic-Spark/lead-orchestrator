# Lead Orchestrator

Automated lead pipeline that enriches prospect data via ZoomInfo, manages leads in Google Sheets, and sends outreach emails through Gmail.

## Setup

1. **Clone and install dependencies:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. **Configure environment variables:**

```bash
cp .env.example .env
# Edit .env with your actual values
```

3. **Add credentials files:**
   - Place your Google Sheets service account JSON as `credentials.json`
   - Place your Gmail service account JSON as `gmail_credentials.json`
   - **Never commit credentials files to version control**

## Usage

```bash
python run_all.py
```

Set `DRY_RUN=true` in `.env` to preview actions without making changes.

## Architecture

| Module              | Purpose                                    |
|---------------------|--------------------------------------------|
| `config.py`         | Loads and validates environment variables   |
| `models.py`         | Pydantic data models with input validation  |
| `sheets_client.py`  | Google Sheets read/write operations         |
| `gmail_agent.py`    | Email composition and sending via Gmail API |
| `zoominfo_agent.py` | Lead enrichment via ZoomInfo API            |
| `brain.py`          | Pipeline orchestration logic                |
| `run_all.py`        | CLI entry point                             |
