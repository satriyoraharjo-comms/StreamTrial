import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

# Konfigurasi halaman Streamlit
st.set_page_config(
    page_title="PDRD Data Hub", page_icon="📊", layout="wide"
)

st.title("📊 PDRD Data Hub")
st.markdown("PDRD Data Insight Window.")


# Fungsi untuk memuat data CSV
@st.cache_data
def load_data():
  file_path = "Dataset PAD 2021-2025.csv"  # Sesuaikan dengan nama file CSV di GitHub Anda

  # Mencoba membaca dengan delimiter koma, jika gagal coba titik koma (sep=';')
  try:
    df = pd.read_csv(file_path, on_bad_lines="skip")
  except Exception:
    df = pd.read_csv(file_path, sep=";", on_bad_lines="skip")

  return df


try:
  df = load_data()
except Exception as e:
  st.error(
      "Gagal memuat file dataset. Pastikan file CSV sudah di-upload ke GitHub"
      f" di folder yang sama dengan app.py.\nError: {e}"
  )
  st.stop()

# --- SIDEBAR FILTER ---
st.sidebar.header("🎛️ Filter Data")

# Pastikan nama kolom sesuai dengan isi header file CSV Anda
provinsi_list = sorted(df["Provinsi"].dropna().unique())
selected_provinsi = st.sidebar.selectbox(
    "Pilih Provinsi", options=provinsi_list, index=0
)

# Filter Pemda berdasarkan Provinsi yang dipilih
filtered_pemda_df = df[df["Provinsi"] == selected_provinsi]
pemda_list = sorted(filtered_pemda_df["Nama Pemda"].dropna().unique())
selected_pemda = st.sidebar.selectbox(
    "Pilih Nama Pemda / Kabupaten / Kota", options=pemda_list
)

# Filter Data Berdasarkan Pilihan User
df_filtered = df[
    (df["Provinsi"] == selected_provinsi)
    & (df["Nama Pemda"] == selected_pemda)
]

# --- KONTEN UTAMA ---
st.markdown(f"### 📍 Menampilkan Data untuk: **{selected_pemda}**")

# Ringkasan Tabel Agregat
pivot_summary = (
    df_filtered.pivot_table(
        index=["standarjenismap"],
        columns="Tahun",
        values="sum",
        aggfunc="sum",
    )
    .fillna(0)
    / 1e9
)  # Dalam Miliar Rupiah

st.markdown("#### 📋 Tabel Agregat Jenis PDRD (dalam Miliar Rupiah)")
if not pivot_summary.empty:
  st.dataframe(pivot_summary.style.format("{,.2f}"), use_container_width=True)
else:
  st.warning("Tidak ada data untuk pilihan pemda tersebut.")

# --- BAGIAN VISUALISASI GRAFIK ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
  st.subheader("📊 Kontribusi Pajak Utama")
  df_pajak = df_filtered[
      df_filtered["standarjenismap"].str.contains("Pajak", case=False, na=False)
  ]
  if not df_pajak.empty:
    pajak_summary = (
        df_pajak.groupby("standarobjekmap")["sum"].sum().reset_index()
    )
    pajak_summary = pajak_summary.sort_values(by="sum", ascending=False).head(5)

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.barplot(
        data=pajak_summary,
        x="standarobjekmap",
        y="sum",
        palette="Blues_r",
        ax=ax,
    )
    ax.set_title(f"Top 5 Kontributor Pajak di {selected_pemda}")
    ax.set_xlabel("Objek Pajak")
    ax.set_ylabel("Nilai (Rp)")
    plt.xticks(rotation=30, ha="right")
    st.pyplot(fig)
  else:
    st.info("Data pajak tidak tersedia.")

with col2:
  st.subheader("📈 Tren PAD per Tahun (Triliun Rp)")
  df_pad = df_filtered[
      df_filtered["standarkelompokmap"].str.contains(
          "PAD|PENDAPATAN ASLI", case=False, na=False
      )
  ]
  if not df_pad.empty:
    pad_trend = (
        df_pad.groupby("Tahun")["sum"].sum().reset_index()
    )
    pad_trend["sum_triliun"] = pad_trend["sum"] / 1e12

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.lineplot(
        data=pad_trend,
        x="Tahun",
        y="sum_triliun",
        marker="o",
        color="orange",
        linewidth=2.5,
        ax=ax,
    )
    ax.set_title("Tren Pertumbuhan PAD")
    ax.set_xlabel("Tahun")
    ax.set_ylabel("Total PAD (Triliun Rp)")
    st.pyplot(fig)
  else:
    st.info("Data tren PAD tidak tersedia.")

st.markdown("---")
st.caption(
    "💡 Dashboard PDRD Data Hub - Diperbarui secara otomatis dari file CSV."
)