import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Kurter Finans Mobil", layout="wide")

# --- SOL PANEL: VERİ GİRİŞİ (Muhasebeci İçin) ---
st.sidebar.title("🛠 Muhasebe Paneli")
sifre = st.sidebar.text_input("Giriş Şifresi", type="password")

# Verileri tutmak için session_state kullanalım (Şimdilik tarayıcı bazlı)
if 'finans_verileri' not in st.session_state:
    st.session_state.finans_verileri = []

if sifre == "1234": # Buraya istediğin bir şifreyi koyabilirsin
    st.sidebar.success("Giriş Başarılı")
    with st.sidebar.form("yeni_islem"):
        tanim = st.text_input("İşlem Tanımı")
        tutar = st.number_input("Tutar", min_value=0.0)
        vade = st.date_input("Vade Tarihi")
        ekle = st.form_submit_button("Listeye Ekle")
        
        if ekle:
            st.session_state.finans_verileri.append({
                "Tanim": tanim, "Tutar": tutar, "Vade": vade
            })
    
    if st.sidebar.button("Listeyi Temizle"):
        st.session_state.finans_verileri = []
else:
    st.sidebar.warning("Veri girmek için şifre gereklidir.")

# --- ANA EKRAN: ANALİZ (Patron İçin) ---
st.title("💼 Finansal Durum Özeti")

if st.session_state.finans_verileri:
    df = pd.DataFrame(st.session_state.finans_verileri)
    df['Vade'] = pd.to_datetime(df['Vade'])
    bugun = datetime.now()
    
    # Hesaplamalar
    df['Gun'] = (df['Vade'] - bugun).dt.days
    toplam = df['Tutar'].sum()
    ort_gun = (df['Tutar'] * df['Gun']).sum() / toplam if toplam != 0 else 0
    ort_vade = bugun + timedelta(days=ort_gun)

    # Özet Kartlar
    c1, c2 = st.columns(2)
    c1.metric("Toplam Yük", f"{toplam:,.2f} TL")
    c2.metric("Ortalama Vade", f"{round(ort_gun)} Gün")
    
    st.success(f"🗓 **Ağırlıklı Ödeme Tarihi:** {ort_vade.strftime('%d.%m.%Y')}")

    # Grafik ve Tablo
    st.write("### 📈 Ödeme Takvimi")
    st.bar_chart(df.set_index('Vade')['Tutar'])
    
    with st.expander("Tüm Listeyi Gör"):
        st.table(df[['Tanim', 'Tutar', 'Vade']])
else:
    st.info("Henüz veri girişi yapılmadı. Sol taraftaki Muhasebe Paneli'ni kullanın.")
