import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# Sayfa ayarları
st.set_page_config(page_title="Kurter Finans Sistemi", layout="centered")

# --- GOOGLE SHEETS BAĞLANTISI ---
# Senin verdiğin Sheet ID: 1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA
sheet_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- GÜVENLİK VE GİRİŞ SİSTEMİ ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🔒 Kurter Finans Giriş")
    sifre = st.text_input("Sistem Şifresini Giriniz", type="password")
    
    if st.button("Sisteme Giriş Yap"):
        if sifre == "patron001":
            st.session_state.giris_turu = "PATRON"
            st.rerun()
        elif sifre == "muhasebe001":
            st.session_state.giris_turu = "MUHASEBE"
            st.rerun()
        else:
            st.error("Hatalı Şifre!")
    st.stop()

# --- PANEL 1: MUHASEBE VERİ GİRİŞİ ---
if st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Muhasebe Veri Girişi")
    
    with st.form("veri_formu"):
        t = st.text_input("İşlem Tanımı (Firma/Çek No)")
        m = st.number_input("Meblağ", min_value=0.0, step=100.0)
        v = st.date_input("Vade Tarihi")
        
        if st.form_submit_button("Sisteme İşle"):
            # Mevcut veriyi çek
            existing_data = conn.read(spreadsheet=sheet_url, usecols=[0,1,2])
            # Yeni satırı hazırla
            new_row = pd.DataFrame([{"Tanim": t, "Tutar": m, "Vade": str(v)}])
            # Birleştir ve G-Sheet'e geri yaz
            updated_df = pd.concat([existing_data, new_row], ignore_index=True)
            conn.update(spreadsheet=sheet_url, data=updated_df)
            st.success("Veri 'Muhasebe Data' dosyasına başarıyla kaydedildi!")

    if st.button("Sistemden Çıkış"):
        st.session_state.giris_turu = None
        st.rerun()

# --- PANEL 2: PATRON İZLEME PANELİ ---
elif st.session_state.giris_turu == "PATRON":
    st.title("📈 Finansal Analiz (Patron)")
    
    # Google Sheet'ten verileri canlı oku
    df = conn.read(spreadsheet=sheet_url)
    
    if not df.empty:
        df['Vade'] = pd.to_datetime(df['Vade'])
        bugun = datetime.now()
        df['Gun'] = (df['Vade'] - bugun).dt.days
        
        toplam = df['Tutar'].sum()
        ort_gun = (df['Tutar'] * df['Gun']).sum() / toplam if toplam != 0 else 0
        ort_vade = bugun + timedelta(days=ort_gun)
        
        c1, c2 = st.columns(2)
        c1.metric("Toplam Yük", f"{toplam:,.2f} TL")
        c2.metric("Ağırlıklı Ort. Vade", f"{round(ort_gun)} Gün")
        
        st.success(f"🗓 **Nakit Planlama Tarihi:** {ort_vade.strftime('%d.%m.%Y')}")
        
        st.write("### 📊 Vade Dağılımı")
        st.bar_chart(df.set_index('Vade')['Tutar'])
        
        with st.expander("Tüm Listeyi Gör"):
            st.dataframe(df)
    else:
        st.warning("Google Sheet şu an boş.")

    if st.button("Güvenli Çıkış"):
        st.session_state.giris_turu = None
        st.rerun()
