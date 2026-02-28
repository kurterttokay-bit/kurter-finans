import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="Yapdoksan Finans Pro", layout="wide")

# --- BAĞLANTI ---
edit_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- GÜVENLİK ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🔒 Yapdoksan Giriş")
    sifre = st.text_input("Şifre", type="password")
    if st.button("Sistemi Aç"):
        if sifre == "patron125": st.session_state.giris_turu = "PATRON"
        elif sifre == "muhasebe007": st.session_state.giris_turu = "MUHASEBE"
        else: st.error("Hatalı Şifre!")
        st.rerun()
    st.stop()

# --- VERİ ÇEKME VE FORMATLAMA ---
@st.cache_data(ttl=0)
def get_clean_data():
    try:
        data = conn.read(spreadsheet=edit_url, ttl=0)
        data.columns = [c.strip().replace(" ", "_") for c in data.columns]
        
        if not data.empty:
            # Arka planda tarih objesine çeviriyoruz (Hesaplamalar için)
            data['Vade_Obj'] = pd.to_datetime(data['Vade'], errors='coerce').dt.date
            # Ekranda görünecek format: GG.AA.YYYY
            data['Vade_TR'] = pd.to_datetime(data['Vade'], errors='coerce').dt.strftime('%d.%m.%Y')
            data['Tutar'] = pd.to_numeric(data['Tutar'], errors='coerce').fillna(0)
        return data
    except:
        return pd.DataFrame()

df = get_clean_data()
bugun = datetime.now().date()

# --- PATRON PANELİ ---
if st.session_state.giris_turu == "PATRON":
    st.title("👑 Yönetim Paneli")
    
    with st.sidebar:
        if st.button("🔴 Oturumu Kapat", use_container_width=True):
            st.session_state.giris_turu = None
            st.rerun()
        st.divider()
        firmalar = ["TÜMÜ"] + sorted(df['Firma_Adi'].dropna().unique().tolist()) if not df.empty else ["TÜMÜ"]
        secili_firma = st.selectbox("🎯 Cari Seç", firmalar)

    # --- ALERT SİSTEMİ (3 GÜN KALA KIRMIZI) ---
    if not df.empty:
        yaklasanlar = df[(df['Vade_Obj'] >= bugun) & (df['Vade_Obj'] <= bugun + timedelta(days=7))].copy()
        if not yaklasanlar.empty:
            for _, row in yaklasanlar.iterrows():
                kalan_gun = (row['Vade_Obj'] - bugun).days
                if kalan_gun == 3:
                    st.error(f"🚨 **KRİTİK UYARI:** {row['Firma_Adi']} ödemesine son **3 GÜN**! | Vade: {row['Vade_TR']} | Tutar: {row['Tutar']:,.2f} TL")
                elif kalan_gun <= 7:
                    st.warning(f"⚠️ **Yaklaşan:** {row['Firma_Adi']} - **{kalan_gun} gün** kaldı. | Tarih: {row['Vade_TR']}")

    # --- ANALİZ ---
    if not df.empty:
        f_df = df if secili_firma == "TÜMÜ" else df[df['Firma_Adi'] == secili_firma]
        aktif_df = f_df[f_df['Vade_Obj'] >= bugun].copy()
        
        if not aktif_df.empty:
            st.plotly_chart(px.area(aktif_df.sort_values('Vade_Obj'), x='Vade_Obj', y='Tutar', title="Ödeme Akışı"), use_container_width=True)
            
            # Tabloyu Türkiye formatıyla gösteriyoruz
            display_df = aktif_df.sort_values('Vade_Obj')[['Firma_Adi', 'Evrak_Tipi', 'Banka', 'Tutar', 'Vade_TR', 'Aciklama']]
            display_df.columns = ['Firma Adı', 'Evrak Tipi', 'Banka', 'Tutar', 'Vade Tarihi', 'Açıklama']
            st.dataframe(display_df, use_container_width=True)

# --- MUHASEBE PANELİ ---
elif st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Veri Girişi")
    
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_in = c1.text_input("Firma Adı").upper()
        b_in = c1.text_input("Banka").upper()
        e_in = c2.selectbox("Evrak Tipi", ["Çek", "Senet", "Fatura"])
        t_in = c2.number_input("Tutar", min_value=0.0)
        v_in = st.date_input("Vade Seç (GG/AA/YYYY)") # Takvim arayüzü
        
        if st.form_submit_button("Sisteme Kaydet"):
            # Sheets'e YYYY-MM-DD olarak kaydediyoruz (Standart bozulmasın)
            new_row = pd.DataFrame([{
                "Firma_Adi": f_in,
                "Evrak_Tipi": e_in,
                "Banka": b_in,
                "Tutar": t_in,
                "Vade": v_in.isoformat(), # Saatsiz saf tarih (2026-03-03 gibi)
                "Aciklama": ""
            }])
            updated = pd.concat([df, new_row], ignore_index=True)
            conn.update(spreadsheet=edit_url, data=updated)
            st.success(f"Kayıt Başarılı! Vade: {v_in.strftime('%d.%m.%Y')}")
            st.rerun()
