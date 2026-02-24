import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Mobil başlık ayarı
st.set_page_config(page_title="Kurter Finans Panel", layout="centered")

st.title("💼 Patron Finans Paneli")

# BOŞ DOSYA KONTROLÜ VE ÖRNEK VERİ
def verileri_hazirla():
    try:
        df = pd.read_csv('veriler.csv')
        if df.empty or len(df.columns) < 2:
            raise ValueError
    except:
        # Dosya boşsa patrona ayıp olmasın, örnek veri gösterelim
        data = {
            'Tanim': ['Örnek Mal Alımı', 'Örnek Lojistik'],
            'Tutar': [100000, 50000],
            'Vade': [(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'), 
                     (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')]
        }
        df = pd.DataFrame(data)
    return df

df = verileri_hazirla()
df['Vade'] = pd.to_datetime(df['Vade'])

# HESAPLAMALAR
bugun = datetime.now()
df['Gun'] = (df['Vade'] - bugun).dt.days
toplam = df['Tutar'].sum()
ort_gun = (df['Tutar'] * df['Gun']).sum() / toplam if toplam != 0 else 0
ort_vade = bugun + timedelta(days=ort_gun)

# DASHBOARD KARTLARI
st.divider()
c1, c2 = st.columns(2)
c1.metric("Toplam Borç", f"{toplam:,.2f} TL")
c2.metric("Ortalama Vade", f"{round(ort_gun)} Gün")

st.info(f"📅 **Kritik Ödeme Tarihi:** {ort_vade.strftime('%d.%m.%Y')}")

# GRAFİK
st.write("### 📈 Ödeme Dağılımı")
st.bar_chart(df.set_index('Vade')['Tutar'])

st.caption("Muhasebeci veriler.csv dosyasını doldurduğunda burası otomatik güncellenir.")
