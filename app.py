import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# ── Page config ──────────────────────────────────
st.set_page_config(page_title="CashGuard Leak Detector", page_icon="🔍", layout="wide")

# ── Secrets ───────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]      # e.g. https://lscdsb.....supabase.co
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]      # sb_publish...

# Supabase uses Postgres, anon key goes as password for user "postgres"
conn_str = f"host={SUPABASE_URL.replace('https://','').replace('http://','')} " \
           f"dbname=postgres user=postgres password={SUPABASE_KEY} " \
           f"sslmode=require"

@st.cache_resource
def get_conn():
    return psycopg2.connect(conn_str)

conn = get_conn()

# ── Login (simple role switch) ────────────────────
st.sidebar.title("🔐 CashGuard Login")
role = st.sidebar.selectbox("Select Role", ["owner", "finance"])
st.sidebar.caption(f"Logged in as: **{role}**")

# ── Header ─────────────────────────────────────────
st.title("🔍 CashGuard — Working Capital Leak Detector")
st.caption("Real-time leak detection • Powered by n8n + DeepSeek + Supabase")

# ── KPI Cards ─────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

cur = conn.cursor()

# Current Cash from cash_settings (if exists, else 0)
try:
    cur.execute("SELECT current_balance FROM cash_settings LIMIT 1")
    row = cur.fetchone()
    current_cash = row[0] if row else 0
except:
    current_cash = 0

# Total AR Outstanding
cur.execute("SELECT COALESCE(SUM(amount),0) FROM ar_invoices WHERE status IN ('outstanding','overdue')")
total_ar = cur.fetchone()[0]

# Total AP Pending
try:
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM ap_payments WHERE status='pending'")
    total_ap = cur.fetchone()[0]
except:
    total_ap = 0

# Net Position
net = current_cash + total_ar - total_ap

col1.metric("💰 Current Cash", f"HKD {current_cash:,.0f}")
col2.metric("📥 Total AR Outstanding", f"HKD {total_ar:,.0f}")
col3.metric("📤 Total AP Pending", f"HKD {total_ap:,.0f}")
col4.metric("📊 Net Position", f"HKD {net:,.0f}")

st.divider()

# ── Leak Flags Table ──────────────────────────────
st.subheader("🚨 Leak Flags")

try:
    leaks_df = pd.read_sql("""
        SELECT id, leak_type, client_name, description, 
               amount_at_risk, severity, status, detected_at
        FROM leaks
        ORDER BY 
            CASE severity 
                WHEN 'critical' THEN 1 
                WHEN 'high' THEN 2 
                WHEN 'medium' THEN 3 
                ELSE 4 END,
            detected_at DESC
    """, conn)

    if len(leaks_df) == 0:
        st.success("✅ No leaks detected! Run n8n Leak Scanner to populate.")
    else:
        # Color severity
        def color_severity(val):
            colors = {
                'critical': 'background-color: #fee2e2; color: #991b1b',
                'high': 'background-color: #ffedd5; color: #9a3412',
                'medium': 'background-color: #fef9c3; color: #854d0e',
                'low': 'background-color: #f3f4f6; color: #374151'
            }
            return colors.get(val, '')

        styled = leaks_df.style.map(color_severity, subset=['severity'])
        st.dataframe(styled, use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"Error loading leaks: {e}")
    leaks_df = pd.DataFrame()

st.divider()

# ── Action Queue ──────────────────────────────────
st.subheader("📋 Action Queue (Pending Approval)")

try:
    actions_df = pd.read_sql("""
        SELECT id, leak_id, client_name, action_type, note, status, created_at
        FROM action_logs
        WHERE status = 'pending_approval'
        ORDER BY created_at DESC
    """, conn)

    if len(actions_df) == 0:
        st.info("No pending actions. n8n will populate this after leak scan.")
    else:
        for _, row in actions_df.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.write(f"**{row['client_name']}** — {row['action_type']}")
                    st.caption(row['note'])
                with c2:
                    if st.button("✅ Approve", key=f"app_{row['id']}"):
                        cur.execute("UPDATE action_logs SET status='approved' WHERE id=%s", (row['id'],))
                        conn.commit()
                        st.rerun()
                with c3:
                    if st.button("😴 Snooze", key=f"snooze_{row['id']}"):
                        cur.execute("UPDATE action_logs SET status='snoozed' WHERE id=%s", (row['id'],))
                        conn.commit()
                        st.rerun()
except Exception as e:
    st.error(f"Error loading actions: {e}")

st.divider()

# ── Finance-only: Full AR Table ───────────────────
if role == "finance":
    st.subheader("📄 Full AR Invoices (Finance View)")
    try:
        ar_df = pd.read_sql("""
            SELECT client_name, invoice_no, amount, currency, due_date, days_overdue, status
            FROM ar_invoices
            ORDER BY days_overdue DESC
        """, conn)
        st.dataframe(ar_df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error loading AR: {e}")

# ── Footer ─────────────────────────────────────────
st.caption("Powered by CashGuard • Built in 1 Day • Zero Monthly Subscriptions")