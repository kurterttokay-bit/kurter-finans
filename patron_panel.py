import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Sayfa ayarları
st.set_page_config(page_title="Kurter Finans Sistemi", layout="centered")

# --- GÜVENLİK VE GİRİŞ SİSTEMİ ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🔒 Kurter Finans Giriş")
    sifre = st.text_input("Sistem Şifresini Giriniz", type="password")
    
    if st.button("Sisteme Giriş Yap"):
        if sifre == "Mustafa125": # Patron Şifresi
            st.session_state.giris_turu = "PATRON"
            st.rerun()
        elif sifre == "muhasebe007": # Muhasebe Şifresi
            st.session_state.giris_turu = "MUHASEBE"
            st.rerun()
        else:
            st.error("Hatalı Şifre!")
    st.stop()

# --- VERİ ALTYAPISI (Google Sheets Entegrasyonu Hazır) ---
# Buraya Google Sheets bağlandığında kod eklenecek, şimdilik kalıcı olması için veriler.csv kullanalım
def verileri_oku():
    try:
        return pd.read_csv('veriler.csv')
    except:
        return pd.DataFrame(columns=['Tanim', 'Tutar', 'Vade'])

def veri_kaydet(yeni_df):
    yeni_df.to_csv('veriler.csv', index=False)

# --- PANEL 1: MUHASEBE GİRİŞ PANELİ ---
if st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Muhasebe Veri Girişi")
    st.info("Buradan girilen veriler anlık olarak Patron Paneli'ne yansır.")
    
    with st.form("veri_formu"):
        t = st.text_input("İşlem Tanımı (Örn: Çek No / Firma)")
        m = st.number_input("Meblağ", min_value=0.0, step=100.0)
        v = st.date_input("Vade Tarihi")
        
        if st.form_submit_button("Sisteme İşle"):
            mevcut_df = verileri_oku()
            yeni_satir = pd.DataFrame([[t, m, v]], columns=['Tanim', 'Tutar', 'Vade'])
            guncel_df = pd.concat([mevcut_df, yeni_satir], ignore_index=True)
            veri_kaydet(guncel_df)
            st.success("Veri başarıyla işlendi ve Patron Paneli güncellendi!")

    if st.button("Sistemden Çıkış"):
        st.session_state.giris_turu = None
        st.rerun()

# --- PANEL 2: PATRON İZLEME PANELİ ---
elif st.session_state.giris_turu == "PATRON":
    st.title("📈 Finansal Analiz (Patron)")
    
    df = verileri_oku()
    if not df.empty:
        df['Vade'] = pd.to_datetime(df['Vade'])
        bugun = datetime.now()
        df['Gun'] = (df['Vade'] - bugun).dt.days
        
        toplam = df['Tutar'].sum()
        ort_gun = (df['Tutar'] * df['Gun']).sum() / toplam if toplam != 0 else 0
        ort_vade = bugun + timedelta(days=ort_gun)
        
        # Patron Kartları
        c1, c2 = st.columns(2)
        c1.metric("Toplam Yük", f"{toplam:,.2f} TL")
        c2.metric("Ağırlıklı Ort. Vade", f"{round(ort_gun)} Gün")
        
        st.success(f"🗓 **Nakit Planlama Tarihi:** {ort_vade.strftime('%d.%m.%Y')}")
        
        st.write("### 📊 Vade Dağılımı")
        st.bar_chart(df.set_index('Vade')['Tutar'])
    else:
        st.warning("Henüz muhasebe tarafından veri girişi yapılmamış.")

    if st.button("Güvenli Çıkış"):
        st.session_state.giris_turu = None
        st.rerun()
