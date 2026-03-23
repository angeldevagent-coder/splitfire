"""
SplitFire — AI-Powered A/B Testing for Digital Products
Run with: streamlit run app.py
"""

import streamlit as st
import sqlite3
import uuid
import hashlib
import os
from datetime import datetime
from urllib.parse import urlparse
import openai
import requests
import csv
import io

# =============================================================================
# CONFIG
# =============================================================================

DATABASE = "splitfire.db"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
APPROVED_CODES = os.environ.get("APPROVED_CODES", "").split(",")

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
    return sqlite3.connect(DATABASE)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            access_code TEXT,
            tier TEXT DEFAULT 'free',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            description TEXT,
            gumroad_url TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS variations (
            id TEXT PRIMARY KEY,
            product_id TEXT,
            headline TEXT,
            description TEXT,
            variant_type TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS tests (
            id TEXT PRIMARY KEY,
            product_id TEXT,
            status TEXT DEFAULT 'active',
            started_at TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS test_variations (
            id TEXT PRIMARY KEY,
            test_id TEXT,
            variation_id TEXT,
            tracking_link TEXT,
            clicks INTEGER DEFAULT 0,
            FOREIGN KEY (test_id) REFERENCES tests(id),
            FOREIGN KEY (variation_id) REFERENCES variations(id)
        );
        CREATE TABLE IF NOT EXISTS clicks (
            id TEXT PRIMARY KEY,
            test_variation_id TEXT,
            clicked_at TEXT,
            source TEXT,
            FOREIGN KEY (test_variation_id) REFERENCES test_variations(id)
        );
    """)
    conn.commit()
    return conn

# =============================================================================
# AI VARIATION GENERATOR
# =============================================================================

def generate_variations(title, description):
    """Use OpenAI to generate headline and description variations."""
    if not OPENAI_API_KEY:
        return None, "OpenAI API key not configured"
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
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
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.8
        )
        return response.choices[0].message.content, None
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
    """Verify access code."""
    if not APPROVED_CODES or APPROVED_CODES == [""]:
        return True  # No codes configured = open access
    return access_code in [c.strip() for c in APPROVED_CODES if c.strip()]

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
        st.markdown("*Don't have access? Get one at [splitfire.tools](https://splitfire.tools)*")


def dashboard_page():
    st.set_page_config(page_title="SplitFire — Dashboard", page_icon="🔥")
    apply_dark_theme()
    
    user_id = st.session_state.get("user_id")
    
    # Header
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown("# 🔥 SplitFire")
    with cols[1]:
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    init_db()
    conn = get_db()
    
    # Stats
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products WHERE user_id = ?", (user_id,))
    total_products = c.fetchone()[0]
    
    c.execute("""
        SELECT COUNT(*) FROM clicks cl 
        JOIN test_variations tv ON cl.test_variation_id = tv.id
        JOIN products p ON tv.test_id IN (SELECT id FROM tests WHERE product_id = p.id)
        WHERE p.user_id = ?
    """, (user_id,))
    total_clicks = c.fetchone()[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Products", total_products)
    col2.metric("Total Clicks", total_clicks)
    col3.metric("Tests", c.execute("SELECT COUNT(*) FROM tests").fetchone()[0])
    
    st.divider()
    
    # Products list
    st.markdown("## Your Products")
    
    c.execute("SELECT id, title, gumroad_url, created_at FROM products WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    products = c.fetchall()
    
    if not products:
        st.info("No products yet. Add one below to get started!")
    else:
        for pid, title, url, created in products:
            with st.expander(f"📦 {title}"):
                st.write(f"**URL:** {url}")
                st.write(f"**Added:** {created}")
                
                # Show tests for this product
                c.execute("SELECT id, status, started_at FROM tests WHERE product_id = ?", (pid,))
                tests = c.fetchall()
                if tests:
                    st.write("**Tests:**")
                    for tid, status, started in tests:
                        st.write(f"  - Test {tid[:8]}... | Status: {status} | Started: {started}")
                else:
                    st.write("No tests yet")
                
                if st.button(f"Delete", key=f"del_{pid}"):
                    c.execute("DELETE FROM products WHERE id = ?", (pid,))
                    conn.commit()
                    st.rerun()
    
    st.divider()
    
    # Add product
    st.markdown("## Add Product")
    with st.form("add_product"):
        title = st.text_input("Product Title", placeholder="The Ultimate FL Studio Guide")
        description = st.text_area("Product Description", placeholder="Describe your product...")
        gumroad_url = st.text_input("Gumroad URL", placeholder="https://yourshop.gumroad.com/l/...")
        
        submitted = st.form_submit_button("Add Product")
        if submitted:
            if title and gumroad_url:
                pid = str(uuid.uuid4())
                c.execute("""
                    INSERT INTO products (id, user_id, title, description, gumroad_url, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
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
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT title, description, gumroad_url FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    
    if not product:
        st.error("Product not found")
        return
    
    title, description, gumroad_url = product
    st.markdown(f"## 📦 {title}")
    st.write(f"**URL:** {gumroad_url}")
    
    st.divider()
    
    # Generate variations
    st.markdown("### Generate AI Variations")
    
    if "variations" not in st.session_state:
        st.session_state["variations"] = None
    
    if st.button("🎯 Generate with AI"):
        if not OPENAI_API_KEY:
            st.error("OpenAI API not configured on server")
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
        
        # Create test
        st.markdown("### Create A/B Test")
        
        selected_headline = st.selectbox("Choose headline", ["None"] + data["headlines"])
        selected_desc = st.selectbox("Choose description", ["None"] + data["descriptions"])
        
        if st.button("🚀 Create Test"):
            # Create variations
            h_var_id = str(uuid.uuid4())
            d_var_id = str(uuid.uuid4())
            
            c.execute("INSERT INTO variations (id, product_id, headline, description, variant_type) VALUES (?, ?, ?, ?, ?)",
                     (h_var_id, product_id, selected_headline if selected_headline != "None" else "", "headline"))
            c.execute("INSERT INTO variations (id, product_id, headline, description, variant_type) VALUES (?, ?, ?, ?, ?)",
                     (d_var_id, product_id, selected_desc if selected_desc != "None" else "", selected_desc if selected_desc != "None" else "", "description"))
            
            # Create test
            test_id = str(uuid.uuid4())
            c.execute("INSERT INTO tests (id, product_id, started_at) VALUES (?, ?, ?)",
                     (test_id, product_id, datetime.now().isoformat()))
            
            # Create test variations with tracking links
            base_url = gumroad_url
            tv1_id = str(uuid.uuid4())
            tv2_id = str(uuid.uuid4())
            
            link1 = f"{base_url}?utm_source=splitfire&utm_medium=a_b&utm_content={h_var_id[:8]}"
            link2 = f"{base_url}?utm_source=splitfire&utm_medium=a_b&utm_content={d_var_id[:8]}"
            
            c.execute("INSERT INTO test_variations (id, test_id, variation_id, tracking_link) VALUES (?, ?, ?, ?)",
                     (tv1_id, test_id, h_var_id, link1))
            c.execute("INSERT INTO test_variations (id, test_id, variation_id, tracking_link) VALUES (?, ?, ?, ?)",
                     (tv2_id, test_id, d_var_id, link2))
            
            conn.commit()
            st.success("Test created!")
            st.markdown("#### Share these links:")
            st.code(link1)
            st.code(link2)
            st.rerun()
    
    # Show existing tests
    st.divider()
    st.markdown("### Tests")
    
    c.execute("SELECT id, status, started_at FROM tests WHERE product_id = ?", (product_id,))
    tests = c.fetchall()
    
    if not tests:
        st.info("No tests yet. Generate variations above to create one.")
    else:
        for tid, status, started in tests:
            with st.expander(f"Test {tid[:8]}... | {status}"):
                c.execute("""
                    SELECT tv.id, v.headline, v.description, v.variant_type, tv.tracking_link, tv.clicks
                    FROM test_variations tv
                    JOIN variations v ON tv.variation_id = v.id
                    WHERE tv.test_id = ?
                """, (tid,))
                variations = c.fetchall()
                
                for tvid, headline, desc, vtype, link, clicks in variations:
                    st.write(f"**Type:** {vtype}")
                    if headline:
                        st.write(f"**Headline:** {headline}")
                    if desc:
                        st.write(f"**Description:** {desc}")
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
