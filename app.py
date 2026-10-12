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


# Fungsi untuk memuat data langsung dari file Excel
@st.cache_data
def load_data():
  file_path = "Dataset PAD 2021-2025.xlsx"
  df = pd.read_excel(file_path, sheet_name="Dataset PAD 2021-2025")

  # Membersihkan spasi ekstra pada nama kolom
  df.columns = df.columns.str.strip()

  # Membersihkan dan mengonversi kolom numerik 'sum' secara aman
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
      "Gagal memuat file Excel. Pastikan file Excel sudah di-upload ke"
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

# --- TABEL AGREGAT HIERARKI (OBJEK LV1 & LV2) ---
st.markdown(
    "#### 📋 Tabel Agregat Jenis Pdrd (Hierarki Objek Lv1 & Lv2 dalam Miliar"
    " Rupiah)"
)
try:
  if (
      "Objek_Lv1" in df_filtered.columns
      and "Objek_Lv2" in df_filtered.columns
      and "Tahun" in df_filtered.columns
  ):

    # 1. Agregasi berdasarkan Lv1 dan Lv2 terhadap Tahun
    grouped = (
        df_filtered.groupby(["Objek_Lv1", "Objek_Lv2", "Tahun"])["sum"]
        .sum()
        .unstack(fill_value=0)
        / 1e9
    )

    # Memastikan seluruh rentang tahun (2021 s.d. 2026) ada
    for thn in [2021, 2022, 2023, 2024, 2025, 2026]:
      if thn not in grouped.columns:
        grouped[thn] = 0.0

    tahun_cols = [
        c for c in [2021, 2022, 2023, 2024, 2025, 2026] if c in grouped.columns
    ]
    grouped = grouped[tahun_cols]

    # 2. Menyusun baris hirarki: Total Lv1 di atas, diikuti sub-baris Lv2 yang menjorok dan italic
    hierarchical_rows = []

    for lv1 in sorted(grouped.index.get_level_values(0).unique()):
      # Baris Total / Agregat Objek_Lv1 (Tampil Normal / Bold secara visual)
      lv1_data = grouped.loc[lv1].sum()
      lv1_row = {"Jenis / Objek PDRD": f"**{lv1}**"}
      for thn in tahun_cols:
        lv1_row[thn] = lv1_data[thn]
      hierarchical_rows.append(lv1_row)

      # Baris Rincian Objek_Lv2 (Menjorok ke dalam menggunakan spasi khusus & berhuruf miring)
      lv2_sub = grouped.loc[lv1]
      if isinstance(lv2_sub.index, pd.MultiIndex) or len(lv2_sub.shape) > 1:
        lv2_items = lv2_sub.index.unique()
      else:
        lv2_items = [lv2_sub.name] if hasattr(lv2_sub, "name") else lv2_sub.index

      for lv2 in lv2_sub.index:
        lv2_data = lv2_sub.loc[lv2]
        # Menggunakan karakter spasi tak terputus Unicode (\u00A0) untuk efek menjorok
        indent_name = f"\u00A0\u00A0\u00A0\u00A0*{lv2}*"
        lv2_row = {"Jenis / Objek PDRD": indent_name}
        for thn in tahun_cols:
          lv2_row[thn] = lv2_data[thn]
        hierarchical_rows.append(lv2_row)

    df_hierarki = pd.DataFrame(hierarchical_rows)

    if not df_hierarki.empty:
      st.dataframe(df_hierarki, use_container_width=True, hide_index=True)
    else:
      st.warning("Tidak ada data untuk kombinasi wilayah tersebut.")
  else:
    st.error(
        "Kolom 'Objek_Lv1', 'Objek_Lv2', atau 'Tahun' tidak ditemukan di"
        " dataset."
    )
    st.dataframe(df_filtered.head())

except Exception as err:
  st.warning(f"Gagal membentuk tabel agregat hierarki: {str(err)}")
  st.dataframe(df_filtered.head())

# --- BAGIAN VISUALISASI GRAFIK ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
  st.subheader("📊 Kontribusi Pajak Utama")
  try:
    df_pajak = df_filtered[
        df_filtered["standarkelompokmap"].str.contains(
            "Pajak|PAD", case=False, na=False
        )
    ]
    if not df_pajak.empty:
      pajak_summary = (
          df_pajak.groupby("standarobjekmap")["sum"].sum().reset_index()
      )
      pajak_summary = pajak_summary.sort_values(by="sum", ascending=False).head(
          5
      )

      fig, ax = plt.subplots(figsize=(8, 4))
      sns.barplot(
          data=pajak_summary,
          x="standarobjekmap",
          y="sum",
          palette="Blues_r",
          ax=ax,
      )
      ax.set_title(f"Top 5 Objek di {selected_pemda}")
      ax.set_xlabel("Objek Map")
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
      pad_trend = df_pad.groupby("Tahun")["sum"].sum().reset_index()
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
st.caption("💡 Dashboard PDRD Data Hub - Hierarki Objek Lv1 & Lv2.")