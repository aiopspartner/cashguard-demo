# ── Leak Flags Table ──────────────────────────────
st.subheader("🚨 Leak Flags")

try:
    # 修正：用 created_at 排序（原表無 detected_at），select("*") 避免欄位缺失
    leaks_resp = supabase.table("leaks").select("*").order("created_at", desc=True).execute()
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

        # 修正：優先用 description，兼容 note；優先用 amount_at_risk，兼容 amount
        display_cols = ['leak_type', 'client_name', 'description', 'amount_at_risk', 'severity', 'status']
        # 如果 df 沒有 description，用 note 代替
        if 'description' not in leaks_df.columns and 'note' in leaks_df.columns:
            leaks_df['description'] = leaks_df['note']
        if 'amount_at_risk' not in leaks_df.columns and 'amount' in leaks_df.columns:
            leaks_df['amount_at_risk'] = leaks_df['amount']
            
        display_cols = [c for c in display_cols if c in leaks_df.columns]
        styled = leaks_df[display_cols].style.apply(color_severity, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"Error loading leaks: {e}")
