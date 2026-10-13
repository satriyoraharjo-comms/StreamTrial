import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

# Konfigurasi halaman Streamlit
st.set_page_config(
    page_title="PDRD Data Hub", page_icon="📊", layout="wide"
)

st.title("📊 PDRD Data Hub")
st.markdown("Your One Stop PDRD Data Insight")


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

options_pemda = ["🌐 Seluruh Wilayah (Agregat Provinsi)"] + pemda_list
selected_pemda = st.selectbox(
    "Pilih Nama Pemda / Kabupaten / Kota", options_pemda
)

# Logika penarikan data berdasarkan pilihan user
if selected_pemda == "🌐 Seluruh Wilayah (Agregat Provinsi)":
  # Agregat se-provinsi: ambil semua data yang ada di provinsi tersebut
  df_pemda_all = df[df[kolom_provinsi] == selected_provinsi]
  display_title_wilayah = f"Provinsi {selected_provinsi} (Agregat)"
else:
  # Filter spesifik untuk kabupaten/kota tertentu
  df_pemda_all = df[
      (df[kolom_provinsi] == selected_provinsi)
      & (df[kolom_pemda] == selected_pemda)
  ]
  display_title_wilayah = selected_pemda

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
st.markdown(f"### 📍 Realisasi PAD **{selected_pemda}**")

# --- TABEL AGREGAT HIERARKI KUSTOM (PBJT, PAJAK, RETRIBUSI, & TOTAL PDRD) ---
st.markdown(
    "#### 📋 Realisasi Per Jenis PAD 2021 s.d. TW II 2026"
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
            style_metadata_full[idx] if idx < len(style_metadata_full) else "normal"
        )
        styles = []
        for col in row.index:
            if col == "Jenis PAD":
                if st_type == "italic":
                    styles.append("font-style: italic; color: #d0d0d0;")
                else:
                    styles.append("font-weight: bold;")
            elif st_type == "total_pdrd":
                styles.append(
                    "font-weight: bold; background-color: rgba(0, 150, 255, 0.25);"
                    " color: #00aaff;"
                )
            elif st_type == "subtotal":
                styles.append(
                    "font-weight: bold; background-color: rgba(255, 255, 255, 0.05);"
                )
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
  st.markdown(
      f"<div style='text-align: center;'><h5>Kontributor Utama Pajak Daerah"
      f"<br>{selected_pemda}</h5></div>",
      unsafe_allow_html=True,
  )
  try:
    if not df_filtered.empty:
      # Pastikan nama kolom objek map sesuai dengan kolom yang ada di dataset Anda
      # Cek apakah menggunakan 'standarobjekmap' atau 'Objek_Lv2'
      kolom_objek = (
          "Objek_Lv2"
          if "Objek_Lv2" in df_filtered.columns
          else "Objek_Lv2"
      )

      df_pajak_saja = df_filtered[
          (df_filtered["Objek_Lv1"] == "Pajak Daerah")
          | (
              df_filtered["standarjenismap"]
              .astype(str)
              .str.startswith("4101")
          )
      ]

      if not df_pajak_saja.empty:
        df_chart = df_pajak_saja.copy()
        
        # Fungsi untuk meratakan PBJT menjadi satu kategori umum "PBJT"
        def group_pbjt_category(row):
          lv2 = str(row.get("Objek_Lv2", ""))
          if "PBJT" in lv2 or "Pajak Barang" in lv2:
            return "PBJT"
          return lv2
      
        # Terapkan pengelompokan PBJT
        df_chart[""] = df_chart.apply(
            group_pbjt_category, axis=1
        )
        
        # Agregasi total nilai per objek pajak
        pajak_summary = (
            df_chart.groupby("")["sum"].sum().reset_index()
        )
        
        # Hitung Total Keseluruhan Pajak Daerah untuk persentase
        total_pajak_daerah = pajak_summary["sum"].sum()
        
        if total_pajak_daerah > 0:
          # Hitung persentase kontribusi
          pajak_summary["persentase"] = (
              pajak_summary["sum"] / total_pajak_daerah
          ) * 100
        else:
          pajak_summary["persentase"] = 0.0
          
        # Konversi nilai ke Miliar Rupiah untuk label batang
        pajak_summary["sum_miliar"] = pajak_summary["sum"] / 1e9
        
        # Urutkan berdasarkan persentase tertinggi (Descending) dan ambil Top 5
        pajak_summary = pajak_summary.sort_values(
            by="persentase", ascending=False
        ).head(5)

        if not pajak_summary.empty:
          fig, ax = plt.subplots(figsize=(8, 5))
          # Membuat grafik batang berdasarkan persentase
          sns.barplot(
              data=pajak_summary,
              x="",
              y="persentase",
              palette="Blues_r",
              ax=ax,
          )
          
          ax.get_yaxis().set_visible(False)
          ax.spines['left'].set_visible(False)
          ax.spines['top'].set_visible(False)
          ax.spines['right'].set_visible(False)
          ax.spines['bottom'].set_visible(False)
          
          for p in ax.patches:
            height = p.get_height()
            if height > 0:
              # Mencari nilai Miliar yang sesuai dengan posisi batang saat ini
              # Menggunakan indeks patch untuk mengambil data ringkasan
              ax.annotate(
                  f"{height:.1f}%",
                  (p.get_x() + p.get_width() / 2.0, height),
                  ha="center",
                  va="center",
                  xytext=(0, 7),
                  textcoords="offset points",
                  fontsize=9,
                  color="#333",
                  weight="bold",
              )
          plt.xticks(rotation=0, ha="right", fontsize=9)
          st.pyplot(fig)
        else:
          st.info("Ringkasan data pajak kosong.")
      else:
        st.info("Kolom objek atau data Pajak Daerah tidak ditemukan.")
    else:
      st.info("Data wilayah tidak tersedia.")
  except Exception as e:
    # Menampilkan pesan error spesifik agar ketahuan bagian mana yang salah
    st.error(f"Gagal merender grafik pajak: {str(e)}")

with col2:
  st.markdown(
      f"<div style='text-align: center;'><h5>Peran PAD dalam Pendapatan Daerah"
      f"<br>(Miliar Rp)</span></h5></div>",
      unsafe_allow_html=True,
  )
  try:
    if not df.empty:
      # Ambil data spesifik untuk Pemda dan Provinsi yang dipilih
      df_pemda_all = df[
          (df[kolom_provinsi] == selected_provinsi)
          & (df[kolom_pemda] == selected_pemda)
      ]

      if not df_pemda_all.empty:
        # Deteksi otomatis nama kolom nilai numerik yang ada di dataframe
        # (Mencari kolom seperti 'sum', 'Nilai', 'Realiasi', atau kolom numerik pertama)
        possible_value_cols = ['sum', 'Nilai', 'Realisasi', 'Jumlah', 'value']
        val_col = None
        for c in possible_value_cols:
          if c in df_pemda_all.columns:
            val_col = c
            break
        
        # Jika tidak ketemu di list, ambil kolom numerik pertama selain tahun
        if not val_col:
          numeric_cols = df_pemda_all.select_dtypes(include=['number']).columns
          numeric_cols = [c for c in numeric_cols if c.lower() != 'tahun']
          if numeric_cols:
            val_col = numeric_cols[0]

        if not val_col:
          st.error("Kolom nilai untuk perhitungan tidak ditemukan di dataset.")
        else:
          # 1. Total Pendapatan Keseluruhan per Tahun
          df_pendapatan = (
              df_pemda_all.groupby("Tahun")[val_col]
              .sum()
              .reset_index(name="total_pendapatan")
          )

          # 2. Total PAD per Tahun (Komponen berawalan kode '41')
          df_pad_komponen = df_pemda_all[
              df_pemda_all["standarjenismap"].astype(str).str.startswith("41")
          ]
          df_pad_tahunan = (
              df_pad_komponen.groupby("Tahun")[val_col]
              .sum()
              .reset_index(name="total_pad")
          )

          # 3. Gabungkan data untuk Combo Chart
          combo_df = pd.merge(
              df_pad_tahunan, df_pendapatan, on="Tahun", how="left"
          )
          combo_df["sum_triliun"] = combo_df["total_pad"] / 1e9

          # Menghitung persentase PAD terhadap Total Pendapatan Daerah
          combo_df["persen"] = (
              combo_df["total_pad"] / combo_df["total_pendapatan"]
          ) * 100
          combo_df = combo_df.sort_values("Tahun")

          if not combo_df.empty:
            fig, ax = plt.subplots(figsize=(8, 4))

            # Plot Bar Chart (Total PAD dalam Triliun)
            bars = ax.bar(
                combo_df["Tahun"].astype(str),
                combo_df["sum_triliun"],
                color="#1b6ca8",
                width=0.75,
                label="TOTAL PAD",
            )

            ax.get_yaxis().set_visible(False)
            ax.spines["left"].set_visible(False)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_visible(False)
            ax.set_ylim(0, combo_df["sum_triliun"].max() * 1.4)

            # Label nilai nominal di dalam batang bagian bawah
            for bar in bars:
              yval = bar.get_height()
              if yval > 0:
                temp_str = f"{yval:,.2f}"
                formatted_val = (
                    temp_str.replace(",", "TEMP")
                    .replace(".", ",")
                    .replace("TEMP", ".")
                )

                ax.annotate(
                    formatted_val,
                    # Menggunakan posisi 5% dari tinggi batang sebagai titik acuan agar aman di dalam batang
                    xy=(bar.get_x() + bar.get_width() / 2, yval * 0.05),
                    xytext=(0, 0),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    color="white",
                    weight="bold",
                )

            # Sumbu kembar untuk Line Chart (% Rasio PAD terhadap Pendapatan)
            ax2 = ax.twinx()
            ax2.get_yaxis().set_visible(False)
            ax2.spines["top"].set_visible(False)
            ax2.spines["right"].set_visible(False)
            ax2.spines["left"].set_visible(False)
            ax2.spines["bottom"].set_visible(False)
            ax2.set_ylim(0, max(combo_df["persen"].max() * 1.5, 30))

            line = ax2.plot(
                combo_df["Tahun"].astype(str),
                combo_df["persen"],
                color="#f26419",
                linewidth=2.5,
                marker="o",
                markersize=5,
                label="% PAD",
            )

            # Label persentase di atas titik garis
            for x, y in zip(combo_df["Tahun"].astype(str), combo_df["persen"]):
              ax2.annotate(
                  f"{y:.2f}%",
                  xy=(x, y),
                  xytext=(0, 12),
                  textcoords="offset points",
                  ha="center",
                  va="bottom",
                  fontsize=9,
                  color="#d9534f",
                  weight="bold",
                  bbox=dict(
                      boxstyle="round,pad=0.2",
                      fc="#fde8e4",
                      ec="none",
                      alpha=0.9,
                  ),
              )

            ax.set_xlabel("")

            # Legenda di bawah grafik
            lines_1, labels_1 = ax.get_legend_handles_labels()
            lines_2, labels_2 = ax2.get_legend_handles_labels()
            ax.legend(
                lines_1 + lines_2,
                labels_1 + labels_2,
                loc="upper center",
                bbox_to_anchor=(0.5, -0.15),
                ncol=2,
                frameon=False,
                fontsize=9,
            )

            st.pyplot(fig)
          else:
            st.info("Data tren PAD kosong.")
      else:
        st.info("Data wilayah tidak tersedia.")
    else:
      st.info("Dataset utama kosong.")
  except Exception as e:
    st.error(f"Gagal merender Combo Chart: {str(e)}")

st.markdown("---")
st.caption("💡 Dashboard PDRD Data Hub - Struktur PBJT, Sub Total, & Total PDRD.")