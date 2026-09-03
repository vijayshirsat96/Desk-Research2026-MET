import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "desk_research_2026.db"

SECTORS = [
    "Information Technology (IT)", "Pharmaceuticals",
    "BFSI (Banking, Financial Services & Insurance)", "FMCG",
    "Automobile", "Telecom", "Retail",
    "Infrastructure & Construction", "Energy & Power", "Healthcare",
]

ADMIN_USER = "admin_met"
ADMIN_PASS = "DeskResearch@2026"

st.set_page_config(page_title="Desk Research 2026 | MET", page_icon="🎓", layout="wide")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sector TEXT NOT NULL,
            company_num INTEGER NOT NULL,
            company_name TEXT NOT NULL,
            product_num INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            submitted_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def name_exists(name: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM submissions WHERE LOWER(name) = LOWER(?) LIMIT 1", (name.strip(),))
    result = cur.fetchone()
    conn.close()
    return result is not None


def save_submission(name, sector, companies):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ts = datetime.now().isoformat()
    rows = []
    for c_idx, company in enumerate(companies, start=1):
        for p_idx, product in enumerate(company["products"], start=1):
            rows.append((name.strip(), sector, c_idx,
                         company["name"].strip(), p_idx, product.strip(), ts))
    cur.executemany("""
        INSERT INTO submissions
        (name, sector, company_num, company_name, product_num, product_name, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()


def fetch_all_submissions() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM submissions ORDER BY submitted_at DESC", conn)
    conn.close()
    return df


def fetch_pivoted_view() -> pd.DataFrame:
    """One row per student, companies/products as a summary string, for readable dashboard display."""
    df = fetch_all_submissions()
    if df.empty:
        return df

    records = []
    for (name, sector), grp in df.groupby(["name", "sector"], sort=False):
        companies_summary = []
        for c_num, cgrp in grp.groupby("company_num"):
            cname = cgrp["company_name"].iloc[0]
            products = ", ".join(cgrp.sort_values("product_num")["product_name"].tolist())
            companies_summary.append(f"{cname}: [{products}]")
        records.append({
            "Student Name": name,
            "Sector": sector,
            "Companies & Products": "  |  ".join(companies_summary),
            "Submitted At": grp["submitted_at"].iloc[0],
        })
    return pd.DataFrame(records)


def render_header():
    st.markdown("""
        <div style="background-color:#0a2c5c;padding:22px 28px;border-radius:10px;margin-bottom:20px;">
            <p style="color:#a8c4e8;font-size:13px;font-weight:600;letter-spacing:1px;margin:0;">
                MET INSTITUTE OF MANAGEMENT, NASHIK
            </p>
            <h1 style="color:white;font-size:30px;margin:4px 0 0 0;">DESK RESEARCH 2026</h1>
        </div>
    """, unsafe_allow_html=True)


def render_registration_form():
    render_header()
    st.info(
        "Please register for your desk research project. **You may only submit once.** "
        "Select your sector, then identify 5 top companies, and 5 key products for each."
    )

    name = st.text_input("Student Name *", placeholder="Full Name")
    sector = st.selectbox("Select Sector *", [""] + SECTORS)

    companies = []
    if sector:
        st.markdown(f"### Top 5 Companies in {sector}")
        for i in range(5):
            with st.expander(f"Company #{i + 1}", expanded=True):
                cname = st.text_input(f"Company {i + 1} Name", key=f"company_{i}")
                st.caption("Key Products (5)")
                pcols = st.columns(5)
                products = []
                for j in range(5):
                    with pcols[j]:
                        p = st.text_input(f"Product {j + 1}", key=f"product_{i}_{j}", label_visibility="collapsed",
                                           placeholder=f"Product {j + 1}")
                        products.append(p)
                companies.append({"name": cname, "products": products})

    st.markdown("---")
    if st.button("Submit Registration", type="primary", use_container_width=True, disabled=not sector):
        errors = []
        if not name.strip():
            errors.append("Student Name is required.")
        if not sector:
            errors.append("Please select a Sector.")
        if sector:
            for i, c in enumerate(companies, start=1):
                if not c["name"].strip():
                    errors.append(f"Company #{i} name is required.")
                for j, p in enumerate(c["products"], start=1):
                    if not p.strip():
                        errors.append(f"Company #{i} - Product #{j} is required.")

        if errors:
            st.error("Please fix the following:\n\n" + "\n".join(f"- {e}" for e in errors))
        elif name_exists(name):
            st.error(f"⚠️ **{name.strip()}** has already submitted a registration. Duplicate entries are not allowed.")
        else:
            save_submission(name, sector, companies)
            st.success("✅ Registration submitted successfully! Thank you.")
            st.balloons()


def render_admin_dashboard():
    render_header()
    st.subheader("📊 Admin Dashboard — All Submissions")

    df = fetch_pivoted_view()
    st.caption(f"Total students registered: **{len(df)}**")

    if df.empty:
        st.warning("No submissions yet.")
        return

    st.dataframe(df, use_container_width=True, hide_index=True)

    raw_df = fetch_all_submissions()
    csv_data = raw_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download Full Data as CSV",
        data=csv_data,
        file_name="desk_research_2026_submissions.csv",
        mime="text/csv",
        type="primary",
    )


def render_admin_login_sidebar():
    with st.sidebar:
        with st.expander("🔐 Admin Login", expanded=False):
            if st.session_state.get("is_admin"):
                st.success(f"Logged in as **{ADMIN_USER}**")
                if st.button("Logout"):
                    st.session_state["is_admin"] = False
                    st.rerun()
            else:
                with st.form("admin_login_form"):
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Login")
                    if submitted:
                        if username == ADMIN_USER and password == ADMIN_PASS:
                            st.session_state["is_admin"] = True
                            st.rerun()
                        else:
                            st.error("Invalid credentials.")


def main():
    init_db()
    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False

    render_admin_login_sidebar()

    if st.session_state["is_admin"]:
        render_admin_dashboard()
    else:
        render_registration_form()


if __name__ == "__main__":
    main()
