# SplitFire — Product Spec

**What it does:** AI-powered A/B testing for digital product listings (Gumroad, Etsy, etc.)

## Tech Stack
- Python 3 + Streamlit
- SQLite (local per-user database)
- OpenAI API (for variation generation at runtime)
- Cloudflare Tunnel (public URL)

## Tiers
- **Free:** 3 products, basic tracking
- **Pro ($9/mo or $79 lifetime):** Unlimited products, email reports, CSV export

## Features
1. **Product Input** — paste title + description
2. **AI Variation Generator** — 4 headlines + 4 descriptions via OpenAI
3. **Link Creator** — generate tracking links per variation
4. **Click Dashboard** — see which variation wins
5. **CSV Export** — download results

## Design
- Dark hacker aesthetic
- Primary: #0f0f0f (bg)
- Accent: #00ff88 (neon green)
- Font: JetBrains Mono or similar

## Flow
1. User creates account (simple: username + access code)
2. Adds product (title, description, Gumroad URL)
3. Clicks "Generate Variations" → AI creates 4 headline + 4 description variants
4. User selects which to test → system creates tracking URLs
5. User shares links → clicks tracked in dashboard
6. Winner declared when statistical significance reached

## Database Schema
```sql
users: id, username, access_code, tier, created_at
products: id, user_id, title, description, gumroad_url, created_at
variations: id, product_id, headline, description, variant_type
tests: id, product_id, variation_ids, status, started_at
clicks: id, test_id, variation_id, clicked_at, source
```

## Security
- Access codes checked against approved list
- Each user sees only their own data
- API key stored server-side, never exposed to client
