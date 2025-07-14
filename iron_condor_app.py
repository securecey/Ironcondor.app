import streamlit as st
import pandas as pd

st.set_page_config(page_title="Iron Condor Builder", layout="centered")
st.title("🦉 NIFTY Iron Condor Strategy Builder")

uploaded_file = st.file_uploader("📂 Upload NIFTY Option Chain CSV", type="csv")

gap = st.number_input("📏 Strike Gap (₹)", min_value=50, max_value=500, value=100, step=50)

if uploaded_file:
    try:
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

        sell_put = atm_strike - gap
        buy_put = atm_strike - 2 * gap
        sell_call = atm_strike + gap
        buy_call = atm_strike + 2 * gap

        def get_ltp(strike, col_name):
            match = df.loc[df[strike_col] == strike]
            return match[col_name].values[0] if not match.empty else None

        ce_sell = get_ltp(sell_call, ce_col)
        ce_buy = get_ltp(buy_call, ce_col)
        pe_sell = get_ltp(sell_put, pe_col)
        pe_buy = get_ltp(buy_put, pe_col)

        if None in [ce_sell, ce_buy, pe_sell, pe_buy]:
            st.error("⚠️ One or more required strikes not found in file.")
        else:
            credit = ce_sell + pe_sell - ce_buy - pe_buy
            max_loss = gap - credit

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
            st.info(f"📉 **Breakeven Range:** {sell_put - credit:.2f} to {sell_call + credit:.2f}")

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
else:
    st.info("Upload a CSV file with columns: `Strike`, `Call LTP`, and `Put LTP`.")
