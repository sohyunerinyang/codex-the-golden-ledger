# The Golden Ledger

The Golden Ledger is a luxury California real estate buyer intelligence platform built with OpenAI Codex. It helps buyers make clearer decisions before writing an offer by estimating three numbers that listing portals usually do not show: the offer price likely required to win, the financial risk of waiving contingencies, and the true monthly carrying cost after California-specific expenses.

## Core Features

### 1. Offer Win-Rate Predictor
Estimates recommended offer targets for 60%, 85%, and 95% win probability using listing price, days on market, sale-to-list pressure, competitor count, and buyer offer price.

### 2. Contingency Waive Risk Analyzer
Models the expected monetary risk of waiving inspection or loan contingencies using home age, construction material, seismic exposure, and wildfire risk.

### 3. Hidden Cost & DTI Tracker
Calculates California-specific carrying cost using Prop 13 property tax baseline, county bonds, Mello-Roos CFD assumptions, fire-zone insurance tiers, mortgage payment, and front-end DTI.

## Why I Built This

California buyers often make high-stakes offer decisions with incomplete information. The Golden Ledger turns scattered market, tax, insurance, and risk signals into a cleaner buyer-side decision system.

## Tech Stack

- OpenAI Codex
- HTML5, CSS3, Vanilla JavaScript
- Leaflet + OpenStreetMap
- FastAPI
- Pydantic
- GitHub Pages-ready static frontend

## Project Structure

```txt
golden-ledger/
  index.html
  pricing.html
  instruments/
    win-rate.html
    contingency-risk.html
    hidden-costs.html
  assets/
    style.css
    main.js

golden_ledger_api.py
requirements.txt
