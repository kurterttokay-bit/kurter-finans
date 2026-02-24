import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Yapdoksan Finans", layout="centered")

# --- GOOGLE SHEETS BAĞLANTISI ---
# URL'deki /edit kısmını sildik, en yalın haliyle kullanıyoruz
sheet_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/export?format=csv"
# Yazma işlemi için edit linki lazım
edit_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- ŞİFRELEME ---
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

# --- VERİ ÇEKME ---
# Veriyi her seferinde en güncel haliyle çekiyoruz
df = conn.read(spreadsheet=edit_url)

# --- PANEL 1: MUHASEBE VE REVİZYON ---
if st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Muhasebe Paneli")
    tab1, tab2 = st.tabs(["➕ Yeni Veri Ekle", "🗑️ Kayıtları Sil"])
    
    with tab1:
        with st.form("ekle_form"):
            t = st.text_input("İşlem Tanımı (Çek/Firma)")
            m = st.number_input("Tutar (TL)", min_value=0.0)
            v = st.date_input("Vade")
            if st.form_submit_button("Sisteme Kaydet"):
                new_row = pd.DataFrame([{"Tanim": t, "Tutar": m, "Vade": str(v)}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                # Burası kritik: Yazma işlemini deniyoruz
                try:
                    conn.update(spreadsheet=edit_url, data=updated_df)
                    st.success("Veri başarıyla Sheets'e işlendi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Yazma Hatası: {e}")
                    st.info("Lütfen Google Sheet dosyasının 'Düzenleyici' olarak paylaşıldığından emin olun.")

    with tab2:
        if not df.empty:
            for index, row in df.iterrows():
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"**{row['Tanim']}**")
                c2.write(f"{row['Tutar']} TL")
                if c3.button("SİL", key=f"d_{index}"):
                    df = df.drop(index)
                    conn.update(spreadsheet=edit_url, data=df)
                    st.rerun()

# --- PANEL 2: PATRON PANELİ ---
elif st.session_state.giris_turu == "PATRON":
    st.title("📈 Yapdoksan Rapor")
    if not df.empty:
        df['Vade'] = pd.to_datetime(df['Vade'])
        bugun = pd.to_datetime(datetime.now().date())
        
        # Sadece Gelecek Vadeler
        aktif_df = df[df['Vade'] >= bugun]
        
        toplam = aktif_df['Tutar'].sum()
        aktif_df['Gun'] = (aktif_df['Vade'] - bugun).dt.days
        ort_gun = (aktif_df['Tutar'] * aktif_df['Gun']).sum() / toplam if toplam != 0 else 0
        
        st.metric("Gelecek Toplam Yük", f"{toplam:,.2f} TL")
        st.metric("Ortalama Vade", f"{round(ort_gun)} Gün")
        st.bar_chart(aktif_df.set_index('Vade')['Tutar'])
    else:
        st.warning("Henüz hiç veri girilmemiş.")

if st.button("Çıkış Yap"):
    st.session_state.giris_turu = None
    st.rerun()
