import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- KUVEYT TÜRK KURLARINI ÇEKME FONKSİYONU ---
def get_kuveyt_kurlar():
    try:
        url = "https://finans.kuveytturk.com.tr/finans-portali"
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Kuveyt Türk sayfa yapısına göre USD ve EUR verilerini ayıklama
        # Not: Banka sayfa yapısını değiştirirse buradaki seçiciler güncellenmelidir.
        kur_dict = {}
        rows = soup.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 0:
                para_birimi = cols[0].text.strip()
                if "USD" in para_birimi:
                    kur_dict['USD'] = {"Alis": cols[1].text.strip(), "Satis": cols[2].text.strip()}
                elif "EUR" in para_birimi:
                    kur_dict['EUR'] = {"Alis": cols[1].text.strip(), "Satis": cols[2].text.strip()}
        return kur_dict
    except:
        return None

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Yapdoksan Finans | Canlı Kur", layout="wide")

# (Giriş ve Veri Çekme bölümleri aynı kalıyor...)
# ... [Giriş Kodları Buraya] ...

if st.session_state.giris_turu == "PATRON":
    # --- CANLI KURLAR BÖLÜMÜ (EN ÜSTTE) ---
    kurlar = get_kuveyt_kurlar()
    if kurlar:
        c1, c2, c3, c4 = st.columns([1,1,1,2]) # Kurlar ve Odaklan filtresi yan yana
        c1.metric("💵 USD (Kuveyt)", f"{kurlar['USD']['Satis']} TL")
        c2.metric("💶 EUR (Kuveyt)", f"{kurlar['EUR']['Satis']} TL")
        
        # Filtreleme (Odaklan yazan yer)
        with c4:
            secili_firma = st.selectbox("🎯 Odaklan (Cari Seç)", ["TÜM PORTFÖY"] + sorted(df['Firma_Adi'].unique().tolist()))
    else:
        st.warning("Canlı kurlar şu an alınamadı, yerel veriye devam ediliyor.")
        secili_firma = st.sidebar.selectbox("🎯 Odaklan", ["TÜM PORTFÖY"] + sorted(df['Firma_Adi'].unique().tolist()))

    # --- RİSK SİMÜLASYONU (PATRONA GÜZELLEME 2.0) ---
    st.markdown("---")
    st.subheader("📉 Kur Şoku Senaryosu")
    
    # Kurları sayısal formata çevirip (örneğin 35.50 gibi) simülasyon yapalım
    try:
        mevcut_usd = float(kurlar['USD']['Satis'].replace(',', '.'))
    except:
        mevcut_usd = 35.0 # Varsayılan
        
    sim_kur = st.slider("Dolar Yarın Ne Olur?", min_value=mevcut_usd, max_value=mevcut_usd + 20.0, value=mevcut_usd + 5.0)
    artis_orani = (sim_kur / mevcut_usd) - 1
    
    # Borçların % kaçı dövizli/dövize duyarlı? (Burada varsayım yapıyoruz veya veriden çekiyoruz)
    # Eğer borçlar TL ise kur artışı aslında reel borcunu düşürür (enflasyon etkisi).
    st.info(f"Dolar {sim_kur:.2f} TL olursa, borç yükünün reel değeri (USD bazında) %{artis_orani*100:.1f} oranında değişecektir.")

    # (Grafikler ve Tablolar aşağıda devam ediyor...)
