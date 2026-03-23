# 🔥 SplitFire

> AI-Powered A/B Testing for Digital Products

SplitFire helps you test different headlines and descriptions for your Gumroad, Etsy, or digital product listings. Know exactly which variation converts better.

## Features

- 🎯 **AI Variation Generator** — Generate 4 headline + 4 description variations with one click
- 📊 **Click Tracking** — See which variation gets more clicks
- 📈 **Winner Declaration** — Statistical significance tracking
- 📤 **CSV Export** — Download your test results
- 🌙 **Dark Theme** — Hacker aesthetic, easy on the eyes

## Pricing

| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | 3 products, basic tracking |
| Pro | $9/mo or $79 lifetime | Unlimited products, email reports, CSV export |

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:
```
OPENAI_API_KEY=sk-your-key-here
APPROVED_CODES=your-access-code
```

### 3. Run

```bash
streamlit run app.py
```

The app will run at `http://localhost:8501`

### 4. Expose to Internet (for access outside your network)

**Option A: Cloudflare Tunnel (recommended — free, permanent)**
```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared

# Run tunnel
cloudflared tunnel --url http://localhost:8501
```

**Option B: Ngrok (free, but URL changes each time)**
```bash
ngrok http 8501
```

## Access Codes

Set approved access codes in your `.env` file. Users must enter a valid code to use the app.

Leave `APPROVED_CODES` empty to allow open access (no code required).

## Tech Stack

- **Python 3** + **Streamlit** — Web UI
- **SQLite** — Database
- **OpenAI API** — AI variation generation
- **Cloudflare Tunnel** — Public URL

## Directory Structure

```
splitfire/
├── app.py           # Main Streamlit app
├── requirements.txt # Dependencies
├── .env.example     # Environment template
├── .env             # Your config (gitignored)
├── splitfire.db     # SQLite database (created auto)
└── README.md        # This file
```

## License

Proprietary — All rights reserved
