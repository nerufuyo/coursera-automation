#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "🤖 Starting Coursera AI Backend on http://localhost:8000"
python ai_backend.py
