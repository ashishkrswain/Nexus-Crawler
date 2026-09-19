# Nexus Crawler

A highly scalable asynchronous pipeline for discovering new domains in real-time and scraping their content using Jina AI's Reader API.

## Architecture

1. **Discovery**: Listens to the global Certificate Transparency (CT) logs via `certstream` to detect new domains as soon as their SSL certificates are registered.
2. **Extraction**: An asynchronous worker pool pulls discovered domains and passes them to `r.jina.ai` to extract clean, LLM-ready markdown content.
3. **Storage**: Extracted data is saved as JSON lines (`.jsonl`) files in the `data/` directory for downstream processing.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the pipeline:
   ```bash
   python main.py
   ```
