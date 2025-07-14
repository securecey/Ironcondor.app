import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import re

st.set_page_config(page_title="Iron Condor Pro Builder", layout="centered")
st.title("🦉 Pro NIFTY Iron Condor Strategy Builder")

uploaded_file = st.file_uploader("📂 Upload NIFTY Option Chain CSV", type="csv")

def extract_expiry_from_filename(name):
    match = re.search(r'(\d{4}-\d{2}-\d{2})', name)
    return match.group(1) if match else "Unknown"

if uploaded_file:
    expiry = extract_expiry_from_filename(uploaded_file.name)
    st.markdown(f"📅 **Detected Expiry Date:** `{expiry}`")

    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()
    ce_col = 'Call LTP'
    pe_col = 'Put LTP'
    strike_col = 'Strike'

    df = df.dropna(subset=[strike_col, ce_col, pe_col])
    df[strike_col] = pd.to_numeric(df[strike_col], errors='coerce')
    df[ce_col] = pd.to_numeric(df[ce_col], errors='coerce')
    df[pe_col] = pd.to_numeric(df[pe_col], errors='coerce')
    df = df.dropna()

    df['diff'] = abs(df[ce_col] - df[pe_col])
    atm_row = df.loc[df['diff'].idxmin()]
    atm_strike = int(atm_row[strike_col])
    st.subheader(f"🎯 Detected ATM Strike: {atm_strike}")

    # 🔍 Multi-strike OI Analyzer (± 3 strikes)
    st.markdown("### 🔍 Open Interest Snapshot (±3 strikes from ATM)")
    oi_cols = ['Strike']
    if 'Put OI' in df.columns and 'Call OI' in df.columns:
        oi_cols += ['Put OI', 'Call OI']
    if 'Put OI Change' in df.columns and 'Call OI Change' in df.columns:
        oi_cols += ['Put OI Change', 'Call OI Change']

    oi_view = df[df[strike_col].between(atm_strike - 3 * 50, atm_strike + 3 * 50)][oi_cols]
    st.dataframe(oi_view.reset_index(drop=True), use_container_width=True)

    # Auto gap detection and optimization
    unique_strikes = sorted(df[strike_col].unique())
    gaps = sorted(list(set([int(unique_strikes[i+1] - unique_strikes[i]) for i in range(len(unique_strikes)-1)])))
    test_gaps = [g for g in gaps if g >= 50 and g <= 250][:3]
    best_strategy = None
    best_credit = 0

    st.markdown("### 🔁 Optimizing Iron Condor...")
    for gap in test_gaps:
        sell_put = atm_strike - gap
        buy_put = atm_strike - 2 * gap
        sell_call = atm_strike + gap
        buy_call = atm_strike + 2 * gap

        def get_ltp(strike, col):
            row = df[df[strike_col] == strike]
            return row[col].values[0] if not row.empty else None

        ce_sell = get_ltp(sell_call, ce_col)
        ce_buy = get_ltp(buy_call, ce_col)
        pe_sell = get_ltp(sell_put, pe_col)
        pe_buy = get_ltp(buy_put, pe_col)

        if None in [ce_sell, ce_buy, pe_sell, pe_buy]:
            continue

        credit = ce_sell + pe_sell - ce_buy - pe_buy
        min_required_credit = 0.25 * gap

        if credit >= min_required_credit and credit > best_credit:
            best_credit = credit
            best_strategy = (gap, credit, sell_put, buy_put, sell_call, buy_call, ce_sell, ce_buy, pe_sell, pe_buy)

    if best_strategy:
        gap, credit, sell_put, buy_put, sell_call, buy_call, ce_sell, ce_buy, pe_sell, pe_buy = best_strategy
        max_loss = gap - credit
        breakeven_low = sell_put - credit
        breakeven_high = sell_call + credit

        st.success(f"✅ Best Strategy: Gap ₹{gap}, Credit ₹{credit:.2f}, Max Loss ₹{max_loss:.2f}")
        st.markdown(f"""
        | Leg         | Strike | Premium |
        |-------------|--------|---------|
        | Sell PE     | {sell_put} | ₹{pe_sell:.2f} |
        | Buy  PE     | {buy_put} | ₹{pe_buy:.2f} |
        | Sell CE     | {sell_call} | ₹{ce_sell:.2f} |
        | Buy  CE     | {buy_call} | ₹{ce_buy:.2f} |
        """)

        # IV logic
        if 'IV' in df.columns:
            iv_avg = round(df['IV'].mean(), 2)
            st.markdown(f"📈 **Average IV in File:** {iv_avg}")
            if iv_avg > 18:
                st.success("🧠 IV is high — Iron Condor is suitable.")
            else:
                st.warning("⚠️ IV is low — Premiums may be unattractive.")

        # 📊 Payoff chart
        st.markdown("### 📊 Payoff Chart")
        spot_range = range(atm_strike - 3 * gap, atm_strike + 3 * gap + 1, 10)
        payoff = []

        for spot in spot_range:
            pe_profit = max(0, buy_put - spot) - max(0, sell_put - spot)
            ce_profit = max(0, spot - buy_call) - max(0, spot - sell_call)
            total_pnl = credit - pe_profit - ce_profit
            payoff.append(total_pnl)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(spot_range), y=payoff, mode='lines+markers', name='Payoff'))
        fig.update_layout(title='Iron Condor Payoff at Expiry',
                          xaxis_title='NIFTY Spot Price',
                          yaxis_title='Profit / Loss',
                          template='plotly_dark')
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("❌ No valid strategy found with sufficient premium.")

else:
    st.info("📁 Please upload a CSV with `Strike`, `Call LTP`, `Put LTP`, and optionally `IV`, `OI`.")

