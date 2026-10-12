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


# Fungsi untuk memuat data CSV
@st.cache_data
def load_data():
  file_path = "Dataset PAD 2021-2025.csv"  # Pastikan nama file CSV sesuai di GitHub
  try:
    df = pd.read_csv(file_path, sep=";", on_bad_lines="skip")
  except Exception:
    df = pd.read_csv(file_path, sep=",", on_bad_lines="skip")

  # Membersihkan spasi ekstra pada nama kolom
  df.columns = df.columns.str.strip()

  # Memastikan kolom 'sum' bertipe numerik
  if "sum" in df.columns:
    df["sum"] = pd.to_numeric(
        df["sum"].astype(str).str.replace(",", "."), errors="coerce"
    )

  return df


try:
  df = load_data()
except Exception as e:
  st.error(f"Gagal memuat file dataset. Error: {e}")
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

# --- TABEL AGREGAT BERBASIS Objek_Lv1 ---
st.markdown("#### 📋 Tabel Agregat Jenis PDRD (dalam Miliar Rupiah)")
try:
  if "Objek_Lv1" in df_filtered.columns and "Tahun" in df_filtered.columns:
    # Cek jumlah unique tahun. Jika hanya 1 tahun, gunakan groupby agar tidak error pivot
    if df_filtered["Tahun"].nunique() > 1:
      pivot_summary = (
          df_filtered.pivot_table(
              index="Objek_Lv1", columns="Tahun", values="sum", aggfunc="sum"
          )
          .fillna(0)
          / 1e9
      )
      st.dataframe(
          pivot_summary.style.format("{,.2f}"), use_container_width=True
      )
    else:
      # Jika hanya ada 1 tahun, tampilkan sebagai ringkasan kolom tunggal
      pivot_summary = (
          df_filtered.groupby("Objek_Lv1")["sum"].sum().reset_index()
      )
      pivot_summary["Nilai (Miliar Rp)"] = pivot_summary["sum"] / 1e9
      pivot_summary = pivot_summary[["Objek_Lv1", "Nilai (Miliar Rp)"]]
      st.dataframe(
          pivot_summary.style.format({"Nilai (Miliar Rp)": "{:,.2f}"}),
          use_container_width=True,
      )
  else:
    st.error("Kolom 'Objek_Lv1' atau 'Tahun' tidak ditemukan di dataset.")
except Exception as err:
  st.warning(f"Gagal membentuk tabel agregat: {err}")
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
    if not df_pad.empty and df_pad["Tahun"].nunique() > 1:
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
      st.info(
          "Tren PAD memerlukan data lebih dari satu tahun di file CSV Anda."
      )
  except Exception:
    st.info("Grafik tren PAD belum dapat dirender.")

st.markdown("---")
st.caption("💡 Dashboard PDRD Data Hub - Berbasis Objek Level 1.")