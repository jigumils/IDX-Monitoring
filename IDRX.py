
from datetime import datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


st.set_page_config(
    page_title="IDX",
    page_icon="📈",
    initial_sidebar_state="expanded"
)


#Function
def file_named(name, format="xlsx"):
    wib = ZoneInfo("Asia/Jakarta")
    timestamp = datetime.now(tz=wib).strftime("%Y%m%d-%H%M%S")
    file_name = f"[{timestamp}] {name}.{format}"
    return file_name


def generate_download_button(df, file_name="data", sheet_name="Sheet1"):
    bio = BytesIO()
    
    with pd.ExcelWriter(bio, engine='openpyxl') as writer:
        df.to_excel(writer, index=True, sheet_name=sheet_name, index_label="Tanggal")

    bio.seek(0)
    st.download_button(
        label=f'Download {file_name}',
        data=bio,
        key = np.random.randint(2**16),
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def idrx(start_date, end_date):
    ticker = yf.Ticker("IDR=X")
    df = ticker.history(start=start_date, end=end_date, interval="1d")

    # Urutkan dari tanggal terbaru ke terlama dan normalisasi
    df = df.sort_index(ascending=False)
    df.index = df.index.tz_localize(None)
    df.index = df.index.date
    kolom_harga = [c for c in ["Open", "High", "Low", "Close"] if c in df.columns]
    df[kolom_harga] = df[kolom_harga].round(4)

    file_name = file_named("IDRX Yahoo Finance")
    generate_download_button(df=df, file_name=file_name, sheet_name="Data_Harian")

    st.write(f"✅ Data berhasil disimpan ke '{file_name}'")
    st.dataframe(df)


def clear_session_state(cust_except = []):
    if cust_except == '-':
        for key in list(st.session_state.keys()):
            del st.session_state[key]
    
    else:
        exception = ['user_login','form_contents','prev_date', 'daily_activity', 'countest'] + cust_except
        for key in list(st.session_state.keys()):
            if key not in exception:
                del st.session_state[key]



#Main Apps
if "page" not in st.session_state:
    st.session_state.page = "idr=x"

elif st.session_state.page != "idr=x":
    clear_session_state('-')
    st.session_state.page = "idr=x"

# ========== Input Area ==========
st.header("**USD/IDR (IDR=X)**", divider="rainbow")

st.subheader("🗓️ Pilih Rentang Tanggal")
col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30), format="DD/MM/YYYY")

with col2:
    end_date = st.date_input("End Date", datetime.now(), format="DD/MM/YYYY")
    end_date = end_date + timedelta(days=1)

if st.button("Submit"):
    st.success(f'**Data Siap Diunduh!**')
    idrx(start_date, end_date)