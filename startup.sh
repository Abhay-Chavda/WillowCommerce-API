#!/bin/bash
python -m uvicorn making_api:app --host 0.0.0.0 --port 8000
