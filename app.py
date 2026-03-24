"""
SplitFire — AI-Powered A/B Testing for Digital Products
Run with: streamlit run app.py
"""

import os
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
import hashlib
from datetime import datetime
import requests

# =============================================================================
# CONFIG
# =============================================================================

# PostgreSQL on Railway (DATABASE_URL set automatically when you add PostgreSQL)
DATABASE_URL = os.environ.get("DATABASE_URL", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
APPROVED_CODES = [c.strip() for c in os.environ.get("APPROVED_CODES", "").split(",") if c.strip()]

# Dark theme colors
PRIMARY_BG = "#0f0f0f"
SECONDARY_BG = "#1a1a1a"
ACCENT = "#00ff88"
TEXT = "#e0e0e0"
MUTED = "#666666"

# =============================================================================
# DATABASE
# =============================================================================

def get_db():
    if not DATABASE_URL:
        return None
    try:
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

def init_db():
    conn = get_db()
    if conn is None:
        return None, None
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            access_code TEXT,
            tier TEXT DEFAULT 'free',
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            description TEXT,
            gumroad_url TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS variations (
            id TEXT PRIMARY KEY,
            product_id TEXT,
            headline TEXT,
            description TEXT,
            variant_type TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id TEXT PRIMARY KEY,
            product_id TEXT,
            status TEXT DEFAULT 'active',
            started_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS test_variations (
            id TEXT PRIMARY KEY,
            test_id TEXT,
            variation_id TEXT,
            tracking_link TEXT,
            clicks INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clicks (
            id TEXT PRIMARY KEY,
            test_variation_id TEXT,
            clicked_at TEXT,
            source TEXT
        )
    """)
    conn.commit()
    return conn, cur

# =============================================================================
# AI VARIATION GENERATOR
# =============================================================================

def generate_variations(title, description):
    """Use Groq (free) to generate headline and description variations."""
    if not GROQ_API_KEY:
        return None, "Groq API key not configured. Add GROQ_API_KEY to Railway environment variables."
    
    prompt = f"""You are a conversion rate expert for digital products on Gumroad/Etsy.

Generate exactly 4 headline variations and 4 description variations for this product:

Title: {title}
Description: {description}

Rules:
- Headlines: Max 8 words each, punchy, benefit-focused
- Descriptions: 2-3 sentences each, different angles (benefits, urgency, social proof, features)
- Vary the emotional appeal: some urgent, some educational, some social proof

Format your response EXACTLY like this (no preamble):

HEADLINES:
1. [headline 1]
2. [headline 2]
3. [headline 3]
4. [headline 4]

DESCRIPTIONS:
1. [description 1]
2. [description 2]
3. [description 3]
4. [description 4]"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.8
            },
            timeout=30
        )
        if response.status_code != 200:
            return None, f"Groq error: {response.status_code}"
        data = response.json()
        return data["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, str(e)

def parse_variations(text):
    """Parse the AI response into structured data."""
    headlines = []
    descriptions = []
    lines = text.strip().split("\n")
    current_section = None
    for line in lines:
        line = line.strip()
        if "HEADLINES" in line.upper():
            current_section = "headlines"
        elif "DESCRIPTIONS" in line.upper():
            current_section = "descriptions"
        elif line.startswith(("1.", "2.", "3.", "4.")) and current_section:
            content = line[2:].strip()
            if current_section == "headlines":
                headlines.append(content)
            else:
                descriptions.append(content)
    return headlines, descriptions

# =============================================================================
# UI HELPERS
# =============================================================================

def apply_dark_theme():
    st.markdown(f"""
    <style>
    .stApp {{ background-color: {PRIMARY_BG}; color: {TEXT}; }}
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {{
        background-color: {SECONDARY_BG}; color: {TEXT}; border: 1px solid {MUTED};
    }}
    .stButton > button {{
        background-color: {ACCENT}; color: #000; font-weight: bold; border: none;
    }}
    .stButton > button:hover {{ background-color: #00cc6a; }}
    h1, h2, h3 {{ color: {ACCENT}; }}
    .css-1d391kg {{ background-color: {SECONDARY_BG}; }}
    .stMetric {{ background-color: {SECONDARY_BG}; padding: 10px; border-radius: 8px; }}
    .stExpander {{ background-color: {SECONDARY_BG}; }}
    </style>
    """, unsafe_allow_html=True)

def check_access(access_code):
    if not APPROVED_CODES:
        return True
    return access_code in APPROVED_CODES

# =============================================================================
# PAGES
# =============================================================================

def login_page():
    st.set_page_config(page_title="SplitFire — Login", page_icon="🔥")
    apply_dark_theme()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("# 🔥 SplitFire")
        st.markdown("*AI-Powered Product Testing*")
        st.divider()
        access_code = st.text_input("Access Code", type="password", placeholder="Enter your access code")
        if st.button("Enter"):
            if check_access(access_code):
                st.session_state["access_code"] = access_code
                st.session_state["user_id"] = hashlib.sha256(access_code.encode()).hexdigest()[:16]
                st.rerun()
            else:
                st.error("Invalid access code")
        st.markdown("---")
        st.markdown("*Don't have access? Get one at [splitfiretools.cc](https://splitfiretools.cc)*")

def dashboard_page():
    st.set_page_config(page_title="SplitFire — Dashboard", page_icon="🔥")
    apply_dark_theme()
    
    user_id = st.session_state.get("user_id")
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown("# 🔥 SplitFire")
    with cols[1]:
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    result = init_db()
    if result[0] is None:
        st.error("Database not ready. Please refresh.")
        return
    conn, cur = result
    
    cur.execute("SELECT COUNT(*) FROM products WHERE user_id = %s", (user_id,))
    total_products = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM clicks")
    total_clicks = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tests")
    total_tests = cur.fetchone()[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Products", total_products)
    col2.metric("Total Clicks", total_clicks)
    col3.metric("Tests", total_tests)
    
    st.divider()
    st.markdown("## Your Products")
    
    cur.execute("SELECT id, title, gumroad_url, created_at FROM products WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
    products = cur.fetchall()
    
    if not products:
        st.info("No products yet. Add one below to get started!")
    else:
        for row in products:
            pid, title, url, created = row
            with st.expander(f"📦 {title}"):
                st.write(f"**URL:** {url}")
                st.write(f"**Added:** {created}")
                cur.execute("SELECT id, status, started_at FROM tests WHERE product_id = %s", (pid,))
                tests = cur.fetchall()
                if tests:
                    st.write("**Tests:**")
                    for tid, status, started in tests:
                        st.write(f"  - Test {tid[:8]}... | Status: {status} | Started: {started}")
                else:
                    st.write("No tests yet")
                if st.button("Delete", key=f"del_{pid}"):
                    cur.execute("DELETE FROM products WHERE id = %s", (pid,))
                    conn.commit()
                    st.rerun()
    
    st.divider()
    st.markdown("## Add Product")
    with st.form("add_product"):
        title = st.text_input("Product Title", placeholder="The Ultimate FL Studio Guide")
        description = st.text_area("Product Description", placeholder="Describe your product...")
        gumroad_url = st.text_input("Gumroad URL", placeholder="https://yourshop.gumroad.com/l/...")
        submitted = st.form_submit_button("Add Product")
        if submitted:
            if title and gumroad_url:
                pid = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO products (id, user_id, title, description, gumroad_url, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (pid, user_id, title, description, gumroad_url, datetime.now().isoformat()))
                conn.commit()
                st.success("Product added!")
                st.rerun()
            else:
                st.error("Title and URL required")

def product_page(product_id):
    st.set_page_config(page_title="SplitFire — Product", page_icon="🔥")
    apply_dark_theme()
    
    if st.button("← Back to Dashboard"):
        del st.session_state["current_product"]
        st.rerun()
    
    result = init_db()
    if result[0] is None:
        st.error("Database not ready.")
        return
    conn, cur = result
    
    cur.execute("SELECT title, description, gumroad_url FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()
    
    if not product:
        st.error("Product not found")
        return
    
    title, description, gumroad_url = product
    st.markdown(f"## 📦 {title}")
    st.write(f"**URL:** {gumroad_url}")
    st.divider()
    
    st.markdown("### Generate AI Variations")
    if "variations" not in st.session_state:
        st.session_state["variations"] = None
    
    if st.button("🎯 Generate with AI"):
        if not GROQ_API_KEY:
            st.error("Groq API not configured on server")
        else:
            with st.spinner("Generating variations..."):
                raw, err = generate_variations(title, description)
                if err:
                    st.error(f"Error: {err}")
                else:
                    headlines, descriptions = parse_variations(raw)
                    st.session_state["variations"] = {"headlines": headlines, "descriptions": descriptions}
                    st.success("Variations generated!")
                    st.rerun()
    
    if st.session_state["variations"]:
        data = st.session_state["variations"]
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Headlines")
            for i, h in enumerate(data["headlines"], 1):
                st.write(f"{i}. {h}")
        with col2:
            st.markdown("#### Descriptions")
            for i, d in enumerate(data["descriptions"], 1):
                st.write(f"{i}. {d}")
        st.divider()
        st.markdown("### Create A/B Test")
        selected_headline = st.selectbox("Choose headline", ["None"] + data["headlines"])
        selected_desc = st.selectbox("Choose description", ["None"] + data["descriptions"])
        if st.button("🚀 Create Test"):
            h_var_id = str(uuid.uuid4())
            d_var_id = str(uuid.uuid4())
            cur.execute("INSERT INTO variations (id, product_id, headline, description, variant_type) VALUES (%s, %s, %s, %s, %s)",
                       (h_var_id, product_id, selected_headline if selected_headline != "None" else "", "headline"))
            cur.execute("INSERT INTO variations (id, product_id, headline, description, variant_type) VALUES (%s, %s, %s, %s, %s)",
                       (d_var_id, product_id, selected_desc if selected_desc != "None" else "", selected_desc if selected_desc != "None" else "", "description"))
            test_id = str(uuid.uuid4())
            cur.execute("INSERT INTO tests (id, product_id, started_at) VALUES (%s, %s, %s)",
                       (test_id, product_id, datetime.now().isoformat()))
            base_url = gumroad_url
            tv1_id = str(uuid.uuid4())
            tv2_id = str(uuid.uuid4())
            link1 = f"{base_url}?utm_source=splitfire&utm_medium=a_b&utm_content={h_var_id[:8]}"
            link2 = f"{base_url}?utm_source=splitfire&utm_medium=a_b&utm_content={d_var_id[:8]}"
            cur.execute("INSERT INTO test_variations (id, test_id, variation_id, tracking_link) VALUES (%s, %s, %s, %s)",
                       (tv1_id, test_id, h_var_id, link1))
            cur.execute("INSERT INTO test_variations (id, test_id, variation_id, tracking_link) VALUES (%s, %s, %s, %s)",
                       (tv2_id, test_id, d_var_id, link2))
            conn.commit()
            st.success("Test created!")
            st.markdown("#### Share these links:")
            st.code(link1)
            st.code(link2)
            st.rerun()
    
    st.divider()
    st.markdown("### Tests")
    cur.execute("SELECT id, status, started_at FROM tests WHERE product_id = %s", (product_id,))
    tests = cur.fetchall()
    if not tests:
        st.info("No tests yet. Generate variations above to create one.")
    else:
        for tid, status, started in tests:
            with st.expander(f"Test {tid[:8]}... | {status}"):
                cur.execute("""
                    SELECT tv.id, v.headline, v.description, v.variant_type, tv.tracking_link, tv.clicks
                    FROM test_variations tv
                    JOIN variations v ON tv.variation_id = v.id
                    WHERE tv.test_id = %s
                """, (tid,))
                variations = cur.fetchall()
                for tvid, headline, desc, vtype, link, clicks in variations:
                    st.write(f"**Type:** {vtype}")
                    if headline: st.write(f"**Headline:** {headline}")
                    if desc: st.write(f"**Description:** {desc}")
                    st.write(f"**Link:** {link}")
                    st.write(f"**Clicks:** {clicks}")
                    st.divider()

def main():
    init_db()
    if "user_id" not in st.session_state:
        login_page()
        return
    if "current_product" in st.session_state:
        product_page(st.session_state["current_product"])
        return
    dashboard_page()

if __name__ == "__main__":
    main()
