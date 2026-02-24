import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="Yapdoksan Finans", layout="centered")

# --- GOOGLE SHEETS BAĞLANTISI ---
edit_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- GÜVENLİK ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🔒 Yapdoksan Giriş")
    sifre = st.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if sifre == "patron125": st.session_state.giris_turu = "PATRON"
        elif sifre == "muhasebe007": st.session_state.giris_turu = "MUHASEBE"
        else: st.error("Hatalı Şifre!")
        st.rerun()
    st.stop()

# --- VERİ ÇEKME (Her iki panel için de güncel veri) ---
try:
    df = conn.read(spreadsheet=edit_url, ttl=0)
except:
    df = pd.DataFrame(columns=['Tanim', 'Tutar', 'Vade'])

# --- MUHASEBE PANELİ ---
if st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Muhasebe Veri Girişi")
    
    with st.form("yeni_kayit_formu"):
        t = st.text_input("İşlem Tanımı (Çek/Firma)")
        m = st.number_input("Meblağ", min_value=0.0)
        v = st.date_input("Vade")
        submit = st.form_submit_button("Sisteme Kaydet")
        
        if submit:
            # Mevcut veriyi al, yeniyi altına ekle (Üzerine yazmayı önleyen kısım)
            new_row = pd.DataFrame([{"Tanim": t, "Tutar": m, "Vade": str(v)}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            
            try:
                conn.update(spreadsheet=edit_url, data=updated_df)
                st.success("Başarıyla eklendi! Sayfa yenileniyor...")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Kayıt Hatası: {e}")

    # Silme İşlemi (Hatalı girişler için)
    if not df.empty:
        with st.expander("Kayıtlı Verileri Gör / Sil"):
            for index, row in df.iterrows():
                col1, col2 = st.columns([4, 1])
                col1.write(f"{row['Tanim']} - {row['Tutar']} TL")
                if col2.button("SİL", key=f"del_{index}"):
                    df = df.drop(index)
                    conn.update(spreadsheet=edit_url, data=df)
                    st.rerun()

# --- PATRON PANELİ ---
elif st.session_state.giris_turu == "PATRON":
    st.title("📈 Yapdoksan Analiz")
    
    if not df.empty:
        df['Vade'] = pd.to_datetime(df['Vade'])
        bugun = pd.to_datetime(datetime.now().date())
        aktif_df = df[df['Vade'] >= bugun].copy()
        
        if not aktif_df.empty:
            toplam = aktif_df['Tutar'].sum()
            aktif_df['Gun'] = (aktif_df['Vade'] - bugun).dt.days
            ort_gun = (aktif_df['Tutar'] * aktif_df['Gun']).sum() / toplam
            
            c1, c2 = st.columns(2)
            c1.metric("Gelecek Toplam Yük", f"{toplam:,.2f} TL")
            c2.metric("Ağırlıklı Ort. Vade", f"{round(ort_gun)} Gün")
            
            st.bar_chart(aktif_df.set_index('Vade')['Tutar'])
        else:
            st.info("Gelecekte vadesi olan bir ödeme bulunamadı.")
    else:
        st.warning("Sistemde henüz veri yok.")

if st.button("Çıkış Yap"):
    st.session_state.giris_turu = None
    st.rerun()
