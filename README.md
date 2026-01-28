# Shine & Roll AI Operations Agent (V1)

Free, cloud-hosted AI-style operations dashboard for a car wash.

Features:
- Upload CSV of car wash transactions
- Cleans and parses time in America/Chicago
- Aggregates hourly volume
- Builds baseline hourly profile by weekday
- Pulls free weather forecast from Open-Meteo
- Adjusts forecast heuristically for rain + traffic index
- Suggests staffing plan per hour
- Suggests low-impact maintenance window
- Classifies new vs returning customers and members
- Shows new customer patterns by day and by hour
- Generates a natural-language summary

## How to run locally

```bash
pip install -r requirements.txt
streamlit run app.py
