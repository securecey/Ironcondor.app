import streamlit as st
import pandas as pd
import plotly.graph_objs as go

st.set_page_config(page_title="Iron Condor Strategy Builder", layout="centered")
st.title("🦉 NIFTY Iron Condor Strategy Builder")

uploaded_file = st.file_uploader("📂 Upload NIFTY Option Chain CSV", type="csv")

if uploaded_file:
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

    # Detect available gaps
    unique_strikes = sorted(df[strike_col].unique())
    gaps = sorted(list(set([int(unique_strikes[i+1] - unique_strikes[i]) for i in range(len(unique_strikes)-1)])))
    selected_gap = st.selectbox("📏 Select Strike Gap (₹)", gaps, index=0)

    # Find ATM Strike
    df['diff'] = abs(df[ce_col] - df[pe_col])
    atm_row = df.loc[df['diff'].idxmin()]
    atm_strike = int(atm_row[strike_col])
    sell_put = atm_strike - selected_gap
    buy_put = atm_strike - 2 * selected_gap
    sell_call = atm_strike + selected_gap
    buy_call = atm_strike + 2 * selected_gap

    def get_ltp(strike, col):
        row = df[df[strike_col] == strike]
        return row[col].values[0] if not row.empty else None

    ce_sell = get_ltp(sell_call, ce_col)
    ce_buy = get_ltp(buy_call, ce_col)
    pe_sell = get_ltp(sell_put, pe_col)
    pe_buy = get_ltp(buy_put, pe_col)

    if None in [ce_sell, ce_buy, pe_sell, pe_buy]:
        st.error("❌ One or more strike prices not found.")
    else:
        credit = ce_sell + pe_sell - ce_buy - pe_buy
        max_loss = selected_gap - credit
        breakeven_low = sell_put - credit
        breakeven_high = sell_call + credit

        st.subheader(f"🎯 ATM Strike: {atm_strike}")
        st.markdown(f"""
        | Leg         | Strike | Premium |
        |-------------|--------|---------|
        | Sell PE     | {sell_put} | ₹{pe_sell:.2f} |
        | Buy  PE     | {buy_put} | ₹{pe_buy:.2f} |
        | Sell CE     | {sell_call} | ₹{ce_sell:.2f} |
        | Buy  CE     | {buy_call} | ₹{ce_buy:.2f} |
        """)

        st.success(f"💰 **Net Credit Collected:** ₹{credit:.2f}")
        st.warning(f"❗ **Max Loss:** ₹{max_loss:.2f}")
        st.info(f"📉 **Breakeven Range:** {breakeven_low:.2f} to {breakeven_high:.2f}")

        # AI-style explanation
        st.markdown("### 🤖 Trade Explanation")
        st.markdown(f"""
        This Iron Condor is built around the ATM strike of **{atm_strike}**, using a gap of **₹{selected_gap}** on both sides.
        - You are selling options at {sell_put} (PE) and {sell_call} (CE) to collect premium.
        - You’re protected by buying wings at {buy_put} and {buy_call}.
        - This results in a net credit of ₹{credit:.2f}, with a max loss of ₹{max_loss:.2f}.
        - You profit if NIFTY stays between **{breakeven_low:.2f} and {breakeven_high:.2f}** by expiry.
        """)

        # Payoff Chart
        st.markdown("### 📊 Payoff Chart")

        spot_range = range(atm_strike - 3 * selected_gap, atm_strike + 3 * selected_gap + 1, 10)
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
    st.info("📁 Please upload a CSV file with columns: `Strike`, `Call LTP`, and `Put LTP`.")
