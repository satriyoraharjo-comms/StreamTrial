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
      "Gagal memuat file Excel. Pastikan file Excel dan openpyxl sudah"
      f" terinstal.\nError: {e}"
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

# Filter Data Berdasarkan Pilihan User & Hanya Ambil Komponen PAD (Kode 41)
df_filtered = df[
    (df[kolom_provinsi] == selected_provinsi)
    & (df[kolom_pemda] == selected_pemda)
]

if "standarjenismap" in df_filtered.columns:
  df_filtered = df_filtered[
      df_filtered["standarjenismap"].astype(str).str.startswith("41")
  ]

# --- KONTEN UTAMA ---
st.markdown(f"### 📍 Menampilkan Data PAD untuk: **{selected_pemda}**")

# --- TABEL AGREGAT HIERARKI KUSTOM (PBJT, PAJAK, RETRIBUSI, & TOTAL PDRD) ---
st.markdown(
    "#### 📋 Tabel Agregat Pendapatan Asli Daerah (PAD) - Struktur Kustom"
    " (dalam Miliar Rupiah)"
)
try:
  if (
      "Objek_Lv1" in df_filtered.columns
      and "Objek_Lv2" in df_filtered.columns
      and "Tahun" in df_filtered.columns
  ):

    tahun_cols = [2021, 2022, 2023, 2024, 2025, 2026]
    df_work = df_filtered.copy()


    def is_pbjt(val):
      if pd.isna(val):
        return False
      return "PBJT" in str(val) or "Pajak Barang" in str(val)


    grouped_raw = (
        df_work.groupby(["Objek_Lv1", "Objek_Lv2", "Tahun"])["sum"]
        .sum()
        .unstack(fill_value=0)
        / 1e9
    )

    for thn in tahun_cols:
      if thn not in grouped_raw.columns:
        grouped_raw[thn] = 0.0
    grouped_raw = grouped_raw[tahun_cols]

    hierarchical_rows = []
    style_metadata = []
    current_idx = 0

    # Helper aman untuk mengambil Series dari dataframe subset
    def get_row_series(sub_df, key):
      res = sub_df.loc[key]
      if isinstance(res, pd.DataFrame):
        return res.sum(axis=0)
      return res


    # 1. PAJAK DAERAH
    pajak_data_sum = pd.Series(0.0, index=tahun_cols)
    pajak_rows = []

    if "Pajak Daerah" in grouped_raw.index.get_level_values(0):
      pajak_sub = grouped_raw.loc["Pajak Daerah"]

      pbjt_items = []
      other_pajak_items = []

      for idx_val in pajak_sub.index:
        lv2_name = idx_val[0] if isinstance(idx_val, tuple) else idx_val
        if is_pbjt(lv2_name):
          if lv2_name not in pbjt_items:
            pbjt_items.append(lv2_name)
        else:
          if lv2_name not in other_pajak_items:
            other_pajak_items.append(lv2_name)

      for p_item in other_pajak_items:
        item_data = get_row_series(pajak_sub, p_item)
        pajak_rows.append(
            {
                "Jenis PAD": f"{p_item}",
                **item_data.to_dict(),
            }
        )
        style_metadata.append("sub_header")
        current_idx += 1

      if pbjt_items:
        pbjt_sum_val = pd.Series(0.0, index=tahun_cols)
        pbjt_sub_rows = []
        for pbjt_item in pbjt_items:
          item_data = get_row_series(pajak_sub, pbjt_item)
          pbjt_sum_val += item_data
          pbjt_sub_rows.append(
              {
                  "Jenis PAD": f"\u00A0\u00A0\u00A0\u00A0{pbjt_item}",
                  **item_data.to_dict(),
              }
          )

        pajak_rows.append(
            {
                "Jenis PAD": "PBJT (Pajak Barang dan Jasa Tertentu)",
                **pbjt_sum_val.to_dict(),
            }
        )
        style_metadata.append("sub_header")
        current_idx += 1

        for sub_r in pbjt_sub_rows:
          pajak_rows.append(sub_r)
          style_metadata.append("italic")
          current_idx += 1

      pajak_data_sum = pajak_sub.sum(axis=0)

    for r in pajak_rows:
      hierarchical_rows.append(r)

    subtotal_pajak_row = {
        "Jenis PAD": "TOTAL PAJAK DAERAH",
        **pajak_data_sum.to_dict(),
    }
    hierarchical_rows.append(subtotal_pajak_row)
    style_metadata_full = style_metadata + ["subtotal"]
    current_idx += 1

    # 2. RETRIBUSI DAERAH
    retribusi_data_sum = pd.Series(0.0, index=tahun_cols)
    retribusi_rows = []
    retribusi_style = []

    if "Retribusi Daerah" in grouped_raw.index.get_level_values(0):
      ret_sub = grouped_raw.loc["Retribusi Daerah"]
      retribusi_data_sum = ret_sub.sum(axis=0)

      for r_item in ret_sub.index:
        r_name = r_item[0] if isinstance(r_item, tuple) else r_item
        r_data = get_row_series(ret_sub, r_name)
        retribusi_rows.append(
            {
                "Jenis PAD": f"\u00A0\u00A0\u00A0\u00A0{r_name}",
                **r_data.to_dict(),
            }
        )
        retribusi_style.append("italic")

    for r, sm in zip(retribusi_rows, retribusi_style):
      hierarchical_rows.append(r)
      style_metadata_full.append(sm)

    subtotal_ret_row = {
        "Jenis PAD": "TOTAL RETRIBUSI DAERAH",
        **retribusi_data_sum.to_dict(),
    }
    hierarchical_rows.append(subtotal_ret_row)
    style_metadata_full.append("subtotal")

# 2b. TOTAL PDRD
    total_pdrd_sum = pajak_data_sum + retribusi_data_sum
    total_pdrd_row = {
        "Jenis PAD": "TOTAL PDRD",
        **total_pdrd_sum.to_dict(),
    }
    hierarchical_rows.append(total_pdrd_row)
    style_metadata_full.append("total_pdrd")

    df_hierarki = pd.DataFrame(hierarchical_rows)

    def style_hierarchy(row):
      idx = row.name
      st_type = (
          style_metadata_full[idx]
          if idx < len(style_metadata_full)
          else "normal"
      )
      styles = []
      for col in row.index:
        if col == "Jenis PAD":
          if st_type == "italic":
            styles.append("font-style: italic; color: #d0d0d0;")
          elif st_type == "subtotal":
            styles.append(
                "font-weight: bold; background-color: rgba(255, 255, 255,"
                " 0.05); border-top: 1px solid #444;"
            )
          elif st_type == "total_pdrd":
            styles.append(
                "font-weight: bold; background-color: rgba(0, 150, 255, 0.15);"
                " border-top: 2px solid #00aaff; color: #00aaff;"
            )
          else:
            styles.append("font-weight: bold;")
        else:
          if st_type in ["subtotal", "total_pdrd"]:
            styles.append("font-weight: bold;")
          else:
            styles.append("")
      return styles

    # 3. HPKPD & LLPAD
    hpkpd_sum = (
        grouped_raw.loc["HPKPD"].sum(axis=0)
        if "HPKPD" in grouped_raw.index.get_level_values(0)
        else pd.Series(0.0, index=tahun_cols)
    )
    llpad_sum = (
        grouped_raw.loc["LLPAD"].sum(axis=0)
        if "LLPAD" in grouped_raw.index.get_level_values(0)
        else pd.Series(0.0, index=tahun_cols)
    )

    if "HPKPD" in grouped_raw.index.get_level_values(0):
      hierarchical_rows.append(
          {"Jenis PAD": "HPKPD", **hpkpd_sum.to_dict()}
      )
      style_metadata_full.append("header")

    if "LLPAD" in grouped_raw.index.get_level_values(0):
      hierarchical_rows.append(
          {"Jenis PAD": "LLPAD", **llpad_sum.to_dict()}
      )
      style_metadata_full.append("header")

    # 4. TOTAL PAD
    total_pad_sum = pajak_data_sum + retribusi_data_sum + hpkpd_sum + llpad_sum
    total_pad_row = {
        "Jenis PAD": "TOTAL PAD",
        **total_pad_sum.to_dict(),
    }
    hierarchical_rows.append(total_pad_row)
    style_metadata_full.append("total_pad")

    df_hierarki = pd.DataFrame(hierarchical_rows)


    def style_hierarchy(row):
      idx = row.name
      st_type = (
          style_metadata_full[idx]
          if idx < len(style_metadata_full)
          else "normal"
      )
      styles = []
      for col in row.index:
        if col == "Jenis PAD":
          if st_type == "italic":
            styles.append("font-style: italic; color: #d0d0d0;")
          elif st_type == "subtotal":
            styles.append(
                "font-weight: bold; background-color: rgba(255, 255, 255,"
                " 0.05); border-top: 1px solid #444;"
            )
          elif st_type == "total_pad":
            styles.append(
                "font-weight: bold; background-color: rgba(0, 150, 255, 0.15);"
                " border-top: 2px solid #00aaff; color: #00aaff;"
            )
          else:
            styles.append("font-weight: bold;")
        else:
          if st_type in ["subtotal", "total_pad"]:
            styles.append("font-weight: bold;")
          else:
            styles.append("")
      return styles


    if not df_hierarki.empty:
      formatted_df = df_hierarki.style.apply(style_hierarchy, axis=1).format(
          {thn: "{:,.2f}" for thn in tahun_cols}
      )
      st.dataframe(formatted_df, use_container_width=True, hide_index=True)
    else:
      st.warning("Tidak ada data PAD untuk kombinasi wilayah tersebut.")
  else:
    st.error("Kolom yang diperlukan tidak ditemukan di dataset.")
    st.dataframe(df_filtered.head())

except Exception as err:
  st.warning(f"Gagal membentuk tabel agregat hierarki: {str(err)}")
  st.dataframe(df_filtered.head())

# --- BAGIAN VISUALISASI GRAFIK ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
  st.subheader("📊 Top 5 Komponen PAD")
  try:
    if not df_filtered.empty:
      pajak_summary = (
          df_filtered.groupby("standarobjekmap")["sum"].sum().reset_index()
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
      ax.set_title(f"Top 5 Komponen di {selected_pemda}")
      ax.set_xlabel("Objek Map")
      ax.set_ylabel("Nilai (Rp)")
      plt.xticks(rotation=30, ha="right")
      st.pyplot(fig)
    else:
      st.info("Data PAD tidak tersedia.")
  except Exception:
    st.info("Grafik komponen PAD belum dapat dirender.")

with col2:
  st.subheader("📈 Tren Total PDRD per Tahun")
  try:
    if not df_filtered.empty:
      pad_trend = df_filtered.groupby("Tahun")["sum"].sum().reset_index()
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
      ax.set_title("Tren Pertumbuhan PDRD")
      ax.set_xlabel("Tahun")
      ax.set_ylabel("Total PDRD (Triliun Rp)")
      st.pyplot(fig)
    else:
      st.info("Data tren PDRD tidak tersedia.")
  except Exception:
    st.info("Grafik tren PDRD belum dapat dirender.")

st.markdown("---")
st.caption("💡 Dashboard PDRD Data Hub - Struktur PBJT, Sub Total, & Total PDRD.")