# Geo Assistant

A geographic assistant that helps answer questions and perform tasks related to locations and geographic data.

## Environment Setup

The project uses environment variables for configuration. Copy `.env.example` to `.env` and customize as needed:

```bash
cp .env.example .env
```

Edit `.env` to set your configuration:

- `OLLAMA_MODEL`: Model name (default: `llama3.2`)
- `OLLAMA_BASE_URL`: Ollama server URL (default: `http://localhost:11434`)
- `API_BASE_URL`: API base URL for the frontend (default: `http://localhost:8000`)

The application will automatically load these variables from the `.env` file.

## Ollama Setup

Install [Ollama](https://ollama.ai/) and download the required models:

```bash
ollama pull ministral-3:14b-cloud
ollama pull gpt-oss:20b-cloud
```

These models are used for agent and satellite image analysis.

## Data Setup

Download Overture Maps place data locally:

```bash
mkdir -p data/overture/places
aws s3 sync s3://overturemaps-us-west-2/release/2025-11-19.0/theme=places/type=place/ data/overture/places/
```

## Development Setup

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality. To set up pre-commit:

1. Install dependencies (including pre-commit):

```bash
uv sync
```

1. Install the git hooks:

```bash
uv run pre-commit install
```

Pre-commit will now automatically run ruff linting and formatting checks before each commit.

To manually run pre-commit on all files:

```bash
uv run pre-commit run --all-files
```

## Running the API

```bash
uv run uvicorn geo_assistant.api.app:app --reload
```

The API will be available at `http://localhost:8000`.

## Running the Frontend

```bash
streamlit run src/geo_assistant/frontend/app.py
```

The frontend will be available at `http://localhost:8501`.
