import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Kurter Finans Sistemi", layout="centered")

# --- BAĞLANTI ---
sheet_url = "https://docs.google.com/spreadsheets/d/1gow0J5IA0GaB-BjViSKGbIxoZije0klFGgvDWYHdcNA/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ŞİFRELEME ---
if 'giris_turu' not in st.session_state:
    st.session_state.giris_turu = None

if st.session_state.giris_turu is None:
    st.title("🔒 Kurter Finans Giriş")
    sifre = st.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if sifre == "patron125": st.session_state.giris_turu = "PATRON"
        elif sifre == "muhasebe007": st.session_state.giris_turu = "MUHASEBE"
        st.rerun()
    st.stop()

# --- VERİ ÇEKME ---
df = conn.read(spreadsheet=sheet_url)
df['Vade'] = pd.to_datetime(df['Vade'])
bugun = pd.to_datetime(datetime.now().date())

# --- MUHASEBE PANELİ (Revizyon Özellikli) ---
if st.session_state.giris_turu == "MUHASEBE":
    st.title("📝 Muhasebe ve Revizyon")
    
    tab1, tab2 = st.tabs(["Yeni Veri Ekle", "Kayıtları Düzenle/Sil"])
    
    with tab1:
        with st.form("ekle_form"):
            t = st.text_input("İşlem Tanımı")
            m = st.number_input("Meblağ", min_value=0.0)
            v = st.date_input("Vade")
            if st.form_submit_button("Kaydet"):
                new_row = pd.DataFrame([{"Tanim": t, "Tutar": m, "Vade": str(v), "Revize": False}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=sheet_url, data=updated_df)
                st.success("Kaydedildi!")
                st.rerun()

    with tab2:
        st.write("Silmek istediğiniz işlemin yanındaki kutuyu işaretleyin.")
        for index, row in df.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            col1.write(f"{row['Tanim']} ({row['Tutar']:.2f} TL)")
            col2.write(f"Vade: {row['Vade'].strftime('%d.%m.%Y')}")
            if col3.button("SİL", key=f"del_{index}"):
                df = df.drop(index)
                # Revize Alert bilgisini gizli bir hücreye yazabiliriz (opsiyonel)
                conn.update(spreadsheet=sheet_url, data=df)
                st.warning("İşlem silindi, Patron paneli güncellendi.")
                st.rerun()

# --- PATRON PANELİ (Alert Özellikli) ---
elif st.session_state.giris_turu == "PATRON":
    st.title("📈 Finansal Rapor")
    
    # VADESİ GEÇENLERİ AYIKLA
    vadesi_gecenler = df[df['Vade'] < bugun]
    aktif_df = df[df['Vade'] >= bugun]
    
    if not vadesi_gecenler.empty:
        st.error(f"⚠️ Dikkat: Vadesi geçmiş {len(vadesi_gecenler)} adet ödeme/çek kaydı var!")
        with st.expander("Vadesi Geçenleri Gör"):
            st.table(vadesi_gecenler[['Tanim', 'Tutar', 'Vade']])

    # ANALİZ (Sadece Gelecek Vadeler)
    if not aktif_df.empty:
        toplam = aktif_df['Tutar'].sum()
        aktif_df['Gun'] = (aktif_df['Vade'] - bugun).dt.days
        ort_gun = (aktif_df['Tutar'] * aktif_df['Gun']).sum() / toplam
        
        c1, c2 = st.columns(2)
        c1.metric("Gelecek Toplam Yük", f"{toplam:,.2f} TL")
        c2.metric("Ortalama Vade", f"{round(ort_gun)} Gün")
        
        st.success(f"🗓 Tahmini Ödeme Günü: {(bugun + timedelta(days=ort_gun)).strftime('%d.%m.%Y')}")
        st.bar_chart(aktif_df.set_index('Vade')['Tutar'])
    else:
        st.info("Gelecek vadeli ödeme kaydı bulunamadı.")
