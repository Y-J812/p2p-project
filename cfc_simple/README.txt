HEALTH EARTH COACH - DEPLOYABLE MVP
===================================

Windows quick start
-------------------
1. Install Python 3.10+ from https://www.python.org/downloads/
2. Extract this folder.
3. Double-click START.bat.
4. Open http://localhost:8000 if it does not open automatically.

BAT files
---------
START.bat    Start the app and open the browser.
STOP.bat     Stop the app.
RESTART.bat  Restart the app.

Features
--------
- Simple Python backend with zero third-party packages.
- SQLite persistence created automatically.
- Carbon footprint calculation and recommendations.
- Dynamic section/navigation state without the bright green indicator.
- History & Progress section with weekly/monthly snapshots and saved recommendations.
- Earth Progress Agent compares the newest and previous assessment, gives constructive compliments or complaints, and identifies the category with the biggest movement.
- Earth Assistant chatbot can answer carbon-footprint questions and can also compare recent vs previous progress.
- What-if simulator.
- Dockerfile for deployment to a Docker-compatible server.

API
---
GET  /api/health
GET  /api/factors
GET  /api/history
GET  /api/progress
GET  /api/chat/history
GET  /api/assessments/{id}
POST /api/calculate
POST /api/scenario
POST /api/assessments
POST /api/chat

Production note
----------------
The included emission factors are illustrative prototype values. Replace them with documented, versioned factors before making scientific or regulatory claims.
The built-in Earth Progress Agent is a deterministic local analysis agent; it does not require a cloud AI key. A production LLM provider can be connected later if desired.

EARTH ASSISTANT - EXPANDED QUESTION COVERAGE
---------------------------------------------
The assistant now supports a broad carbon/climate/sustainability knowledge set, including:
- Carbon footprint, CO2, CO2e, greenhouse gases, climate change and global warming
- Net zero, carbon neutrality, Scope 1/2/3, offsets, carbon removal and lifecycle assessment
- Cars, bikes, buses, metro, trains, flights, commuting, EVs, hybrids and remote work
- Electricity, AC, refrigerators, LEDs, solar, standby power, cooking and hot water
- Food, meat, vegetarian/vegan diets, dairy, eggs, rice, coffee, organic/local food and food waste
- Plastic, recycling, repair, reuse, fashion, online shopping and consumption
- Trees, forests, biodiversity, water footprint, methane and nitrous oxide
- Smartphones, laptops, internet, streaming, houses, cement, paper, clothing and bottled water
- Personal footprint interpretation, recommendations, what-if scenarios, history and progress comparisons

OUT-OF-SCOPE BEHAVIOR
---------------------
Questions outside the Health Earth Coach spectrum receive a friendly boundary response instead of an invented answer. The visual product and existing dashboard behavior remain unchanged.
