import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# ── Page config ──────────────────────────────────
st.set_page_config(
    page_title="CashGuard Leak Detector",
    page_icon="🔍",
    layout="wide"
)

# ── Secrets ───────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Login (simple role switch) ────────────────────
st.sidebar.title("🔐 CashGuard Login")
role = st.sidebar.selectbox("Select Role", ["owner", "finance"])
st.sidebar.caption(f"Logged in as: **{role}**")

# ── Header ─────────────────────────────────────────
st.title("🔍 CashGuard — Working Capital Leak Detector")
st.caption("Real-time leak detection • Powered by n8n + DeepSeek + Supabase")

# ── KPI Cards ─────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

try:
    # Total AR Outstanding
    ar_resp = supabase.table("ar_invoices").select("amount,status").execute()
    ar_data = ar_resp.data or []
    total_ar = sum(r["amount"] for r in ar_data if r["status"] in ("outstanding", "overdue"))
except:
    total_ar = 0

try:
    # Total AP Pending
    ap_resp = supabase.table("ap_payments").select("amount,status").execute()
    ap_data = ap_resp.data or []
    total_ap = sum(r["amount"] for r in ap_data if r["status"] == "pending")
except:
    total_ap = 0

try:
    # Current Cash
    cs_resp = supabase.table("cash_settings").select("current_balance").limit(1).execute()
    cs_data = cs_resp.data or []
    current_cash = cs_data[0]["current_balance"] if cs_data else 0
except:
    current_cash = 0

net = current_cash + total_ar - total_ap

col1.metric("💰 Current Cash", f"HKD {current_cash:,.0f}")
col2.metric("📥 Total AR Outstanding", f"HKD {total_ar:,.0f}")
col3.metric("📤 Total AP Pending", f"HKD {total_ap:,.0f}")
col4.metric("📊 Net Position", f"HKD {net:,.0f}")

st.divider()

# ── Leak Flags Table ──────────────────────────────
st.subheader("🚨 Leak Flags")

try:
    leaks_resp = supabase.table("leaks").select("*").order("detected_at", desc=True).execute()
    leaks_data = leaks_resp.data or []

    if len(leaks_data) == 0:
        st.success("✅ No leaks detected! Run n8n Leak Scanner to populate.")
    else:
        leaks_df = pd.DataFrame(leaks_data)

        # Severity color map
        def color_severity(row):
            colors = {
                'critical': 'background-color: #fee2e2; color: #991b1b',
                'high': 'background-color: #ffedd5; color: #9a3412',
                'medium': 'background-color: #fef9c3; color: #854d0e',
                'low': 'background-color: #f3f4f6; color: #374151'
            }
            return colors.get(row.get('severity', ''), '')

        # Show key columns
        display_cols = ['leak_type', 'client_name', 'description', 'amount_at_risk', 'severity', 'status']
        display_cols = [c for c in display_cols if c in leaks_df.columns]
        styled = leaks_df[display_cols].style.apply(color_severity, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"Error loading leaks: {e}")

st.divider()

# ── Action Queue ──────────────────────────────────
st.subheader("📋 Action Queue (Pending Approval)")

try:
    actions_resp = supabase.table("action_logs").select("*").eq("status", "pending_approval").order("created_at", desc=True).execute()
    actions_data = actions_resp.data or []

    if len(actions_data) == 0:
        st.info("No pending actions. n8n will populate this after leak scan.")
    else:
        for row in actions_data:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.write(f"**{row.get('client_name', 'N/A')}** — {row.get('action_type', 'N/A')}")
                    st.caption(row.get('note', ''))
                with c2:
                    if st.button("✅ Approve", key=f"app_{row['id']}"):
                        supabase.table("action_logs").update({"status": "approved"}).eq("id", row['id']).execute()
                        st.rerun()
                with c3:
                    if st.button("😴 Snooze", key=f"snooze_{row['id']}"):
                        supabase.table("action_logs").update({"status": "snoozed"}).eq("id", row['id']).execute()
                        st.rerun()
except Exception as e:
    st.error(f"Error loading actions: {e}")

st.divider()

# ── Finance-only: Full AR Table ───────────────────
if role == "finance":
    st.subheader("📄 Full AR Invoices (Finance View)")
    try:
        ar_resp = supabase.table("ar_invoices").select("*").order("days_overdue", desc=True).execute()
        ar_data = ar_resp.data or []
        if ar_data:
            ar_df = pd.DataFrame(ar_data)
            st.dataframe(ar_df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error loading AR: {e}")

# ── Footer ─────────────────────────────────────────
st.caption("Powered by CashGuard • Built in 1 Day • Zero Monthly Subscriptions")
