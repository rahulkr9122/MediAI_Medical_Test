# MediScan AI

A Python-powered medical report analyzer with AI-backed recommendations, specialist suggestions, and history tracking.

## What this app does

- Analyze a pasted or uploaded medical report.
- Stream AI-generated findings, severity, next steps, and specialist recommendation.
- Search nearby specialists by city and specialty.
- Keep a history of past analyses.

## Setup

1. Create a Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r src\requirements.txt
```

3. Install and run Ollama locally. For example:

```powershell
ollama run llama2
```

4. Optionally set your local Ollama endpoint and model:

```powershell
$env:OLLAMA_URL = "http://127.0.0.1:11434/v1/completions"
$env:OLLAMA_MODEL = "llama3.2:latest"
```

5. Restart the Flask app after changing environment variables, then run:

```powershell
python src\app.py
```

6. Open http://127.0.0.1:5000 in your browser.

## Notes

- The app uses a local Ollama server by default at `http://127.0.0.1:11434/completions`.
- Override the model using `OLLAMA_MODEL` and the endpoint using `OLLAMA_URL`.
- History is stored in `src/history.json`.
