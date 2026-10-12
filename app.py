import zipfile
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

# Konfigurasi halaman Streamlit
st.set_page_config(
    page_title="PDRD Data Hub", page_icon="📊", layout="wide"
)

st.title("📊 PDRD Data Hub")
st.markdown("PDRD Data Insight Window - Agregat Provinsi & Pemda.")


# Fungsi untuk memuat data ZIP / CSV dengan aman
@st.cache_data
def load_data():
  zip_path = "Dataset PAD 2021-2025.zip"  # Nama file ZIP di GitHub
  csv_filename = "Dataset PAD 2021-2025.csv"  # Nama file CSV di dalam ZIP

  with zipfile.ZipFile(zip_path, "r") as z:
    with z.open(csv_filename) as f:
      try:
        df = pd.read_csv(f, sep=";", on_bad_lines="skip")
      except Exception:
        df = pd.read_csv(f, sep=",", on_bad_lines="skip")

  # Membersihkan spasi ekstra pada nama kolom
  df.columns = df.columns.str.strip()

  # Membersihkan dan mengonversi kolom numerik 'sum'
  if "sum" in df.columns:
    df["sum"] = pd.to_numeric(
        df["sum"].astype(str).str.replace(",", ".").str.strip(), errors="coerce"
    )

  # Membersihkan dan mengonversi kolom 'Tahun' menjadi integer
  if "Tahun" in df.columns:
    df["Tahun"] = pd.to_numeric(df["Tahun"], errors="coerce")
    df = df.dropna(subset=["Tahun"])
    df["Tahun"] = df["Tahun"].astype(int)

  return df


try:
  df = load_data()
except Exception as e:
  st.error(
      "Gagal memuat file dataset. Pastikan 'Dataset.zip' sudah di-upload ke"
      f" GitHub.\nError: {e}"
  )
  st.stop()

# --- VALIDASI KOLOM ---
kolom_provinsi = (
    "Provinsi"
    if "Provinsi" in df.columns
    else [c for c in df.columns if "prov" in c.lower()][0]
)
kolom_pemda = (
    "Nama Pemda"
    if "Nama Pemda" in df.columns
    else [c for c in df.columns if "pemda" in c.lower()][0]
)

# --- SIDEBAR FILTER ---
st.sidebar.header("🎛️ Filter Data")

provinsi_list = sorted(df[kolom_provinsi].dropna().unique())
selected_provinsi = st.sidebar.selectbox(
    "Pilih Provinsi", options=provinsi_list, index=0
)

# Filter Pemda berdasarkan Provinsi yang dipilih
filtered_pemda_df = df[df[kolom_provinsi] == selected_provinsi]
pemda_list = sorted(filtered_pemda_df[kolom_pemda].dropna().unique())
selected_pemda = st.sidebar.selectbox(
    "Pilih Nama Pemda / Kabupaten / Kota", options=pemda_list
)

# Filter Data Berdasarkan Pilihan User
df_filtered = df[
    (df[kolom_provinsi] == selected_provinsi)
    & (df[kolom_pemda] == selected_pemda)
]

# --- KONTEN UTAMA ---
st.markdown(f"### 📍 Menampilkan Data untuk: **{selected_pemda}**")

# --- TABEL AGREGAT BERBASIS Objek_Lv1 (Tahun 2021 - 2026) ---
st.markdown("#### 📋 Tabel Agregat Jenis PDRD (dalam Miliar Rupiah)")
try:
  if "Objek_Lv1" in df_filtered.columns and "Tahun" in df_filtered.columns:
    # Membuat Pivot Table dengan kolom Tahun tersusun ke samping
    pivot_summary = (
        df_filtered.pivot_table(
            index="Objek_Lv1", columns="Tahun", values="sum", aggfunc="sum"
        )
        .fillna(0)
        / 1e9
    )  # Dikonversi ke Miliar Rupiah

    st.dataframe(pivot_summary.style.format("{,.2f}"), use_container_width=True)
  else:
    st.error("Kolom 'Objek_Lv1' atau 'Tahun' tidak ditemukan di dataset.")
except Exception as err:
  st.warning(
      f"Gagal membentuk tabel agregat: {err}. Menampilkan data mentah:"
  )
  st.dataframe(df_filtered.head())

# --- BAGIAN VISUALISASI GRAFIK ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
  st.subheader("📊 Kontribusi Pajak Utama")
  try:
    df_pajak = df_filtered[
        df_filtered["standarjenismap"].str.contains(
            "Pajak", case=False, na=False
        )
    ]
    if not df_pajak.empty:
      pajak_summary = df_pajak.groupby("Objek_Lv1")["sum"].sum().reset_index()
      pajak_summary = pajak_summary.sort_values(by="sum", ascending=False).head(
          5
      )

      fig, ax = plt.subplots(figsize=(8, 4))
      sns.barplot(
          data=pajak_summary,
          x="Objek_Lv1",
          y="sum",
          palette="Blues_r",
          ax=ax,
      )
      ax.set_title(f"Top 5 Kontributor Objek Pajak di {selected_pemda}")
      ax.set_xlabel("Objek Pajak (Lv1)")
      ax.set_ylabel("Nilai (Rp)")
      plt.xticks(rotation=30, ha="right")
      st.pyplot(fig)
    else:
      st.info("Data pajak tidak tersedia.")
  except Exception:
    st.info("Grafik kontribusi pajak belum dapat dirender.")

with col2:
  st.subheader("📈 Tren PAD per Tahun")
  try:
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
  except Exception:
    st.info("Grafik tren PAD belum dapat dirender.")

st.markdown("---")
st.caption("💡 Dashboard PDRD Data Hub - Berbasis Objek Level 1.")