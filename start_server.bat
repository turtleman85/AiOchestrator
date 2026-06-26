@echo off
cd /d "c:\Users\LEEJAEJUN\IdeaProjects\aiOrchestrator"
python -m uvicorn server:app --host 127.0.0.1 --port 8000
