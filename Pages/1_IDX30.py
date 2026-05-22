from datetime import datetime, timedelta
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import re
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
        df.to_excel(writer, index=True, sheet_name=sheet_name, index_label="Row")

    bio.seek(0)
    st.download_button(
        label=f'Download {file_name}',
        data=bio,
        key = np.random.randint(2**16),
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


#Inisiasi driver
def get_firefox_options():
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-gpu")
    firefox_options.set_preference("intl.accept_languages", "id")
    return firefox_options


def init_driver():
    firefox_options = get_firefox_options()  # Get Firefox options
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.cache.disk.enable", False)
    profile.set_preference("browser.cache.memory.enable", False)
    profile.set_preference("browser.cache.offline.enable", False)
    firefox_options.profile = profile
    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=firefox_options)        
    driver.set_window_size(1920, 1080)
    return driver


# Fungsi bantu untuk parsing teks menjadi list of dict
def parse_json_text(json_text):
    records = re.split(r'\nNo \d+\n', json_text)[1:]  # skip bagian sebelum No 1
    data_list = []

    for rec in records:
        lines = rec.split('\n')
        record = {}
        for line in lines:
            if ' ' in line:
                key, value = line.split(' ', 1)
                value = value.replace("JS:", "")
                try:
                    value = float(value)
                except:
                    value = value.strip('"')  # bersihkan tanda kutip jika string
                record[key] = value
        data_list.append(record)
    return data_list


def scrape_idx_data(start_date, end_date):
    driver = init_driver()
    all_data = []
    current_date = start_date
    current_tab = None

    try:
        progress = st.progress(0)
        total_days = (end_date - start_date).days + 1
        done = 0

        while current_date <= end_date:
            date_str_url = current_date.strftime('%Y%m%d')
            url = f"https://idx.co.id/primary/TradingSummary/GetIndexSummary?date={date_str_url}&length=9999&start=0"

            if current_tab is None:
                driver.get(url)
                current_tab = driver.current_window_handle
            else:
                driver.execute_script("window.open('');")
                new_tab = driver.window_handles[-1]
                driver.switch_to.window(new_tab)
                driver.get(url)
                driver.switch_to.window(current_tab)
                driver.close()
                driver.switch_to.window(new_tab)
                current_tab = new_tab

            json_text = driver.find_element(By.TAG_NAME, "body").text
            if json_text:
                records = parse_json_text(json_text)
                for r in records:
                    r['Date'] = current_date.strftime('%Y-%m-%d')
                all_data.extend(records)

            done += 1
            progress.progress(done / total_days)
            current_date += timedelta(days=1)

    finally:
        driver.quit()

    return pd.DataFrame(all_data) if all_data else pd.DataFrame()


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
    st.session_state.page = "idx-bei"

elif st.session_state.page != "idx-bei":
    clear_session_state('-')
    st.session_state.page = "idx-bei"


# ========== Input Area ==========
st.header("**IDX Bursa Efek Indonesia**", divider="rainbow")
st.subheader("🗓️ Pilih Rentang Tanggal")
col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30), format="DD/MM/YYYY")

with col2:
    end_date = st.date_input("End Date", datetime.now(), format="DD/MM/YYYY")

st.write(f'{start_date}${end_date}')

if 'prev_date' not in st.session_state:
    st.session_state.prev_date = f'{start_date}${end_date}'

elif st.session_state.prev_date != f'{start_date}${end_date}':
    clear_session_state('-')


if "get_data" not in st.session_state:
    st.session_state.get_data = st.button("🚀 Ambil Data IDX")
    if st.session_state.get_data:
        st.rerun()

else:
    if "df" not in st.session_state:
        with st.spinner("Sedang mengambil data dari IDX, harap tunggu..."):
            st.session_state.df = scrape_idx_data(start_date, end_date)
            df = st.session_state.df

    else:
        df = st.session_state.df

    if not df.empty:
        st.success(f"✅ Berhasil mengambil {len(df)} baris data!")
        df = df.sort_values("Date", ascending=False)

        all_codes = sorted(df["IndexCode"].unique())
        selected_codes = st.multiselect(
            "🎯 Pilih Index Code yang ingin disimpan:",
            options=all_codes,
            help="Kamu bisa pilih satu, beberapa, atau semua kode indeks."
        )

        if "filter_button" not in st.session_state:
            st.session_state.filter_button = st.button("Filter Data")
            if st.session_state.filter_button:
                st.rerun()

        else:
            filtered_df = df[df["IndexCode"].isin(selected_codes)]

            # Nama file
            if len(selected_codes) < 4 and len(selected_codes) > 0:
                file_name = file_named(f'{", ".join(selected_codes)} - IDX BEI')

            else:
                file_name = file_named(f'Filtered - IDX BEI')

            st.success(f'**Data Siap Diunduh!**')
            generate_download_button(filtered_df, file_name, sheet_name="IDX_Data")
            st.dataframe(filtered_df, use_container_width=True)

    else:
        st.warning("⚠️ Tidak ada data ditemukan untuk rentang tanggal tersebut.")