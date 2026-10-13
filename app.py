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

# ==========================================
# 1. SIDEBAR: HANYA PILIH PROVINSI (GLOBAL)
# ==========================================
st.sidebar.markdown("### 📌 Filter Wilayah Utama")
selected_provinsi = st.sidebar.selectbox(
    "Pilih Provinsi", sorted(df[kolom_provinsi].unique())
)

st.sidebar.markdown("---")
st.sidebar.info(
    "Pilih kategori analisis melalui tab di halaman utama untuk melihat rincian"
    " Agregat, Provinsi Saja, atau Kab./Kota Saja."
)

# ==========================================
# 2. KONTEN UTAMA: MENGGUNAKAN 3 TAB UTAMA
# ==========================================
tab1, tab2, tab3 = st.tabs(
    [
        "🌐 1. Agregat Provinsi",
        "🏛️ 2. Provinsi Saja",
        "🏙️ 3. Kab./Kota Saja",
    ]
)


# =========================================================================
# TAB 1: AGREGAT PROVINSI (Provinsi + Seluruh Kab./Kota)
# =========================================================================
with tab1:
  st.markdown(
      f"#### Analisis Agregat Se-Provinsi {selected_provinsi} (Gabungan"
      " Provinsi & Kab./Kota)"
  )

  # Filter data seluruh provinsi
  df_agregat = df[df[kolom_provinsi] == selected_provinsi]

  # Tambahkan baris penampung universal:
  df_wilayah = df_agregat
  display_title_wilayah = f"Provinsi {selected_provinsi} (Agregat)"

  if not df_agregat.empty:
    display_title_wilayah = f"Provinsi {selected_provinsi} (Agregat)"

    # --- BAGIAN A: TABEL PER JENIS BERDASARKAN LEVEL 2 ---
    st.markdown("##### 📋 Tabel Rangkuman Pendapatan Daerah (Level 2)")
    # (Sisipkan kode tabel level 2 Anda di sini menggunakan df_agregat)

    st.markdown("---")

    # --- BAGIAN B: DUA GRAFIK UTAMA (Kiri & Kanan) ---
    col1, col2 = st.columns(2)

    # Grafik Kiri 1: Ranking Pajak Daerah Provinsi (Agregat)
    with col1:
      st.markdown(
          f"<div style='text-align: center; min-height: 75px;'><h5>📊 Ranking"
          f" Pajak Daerah Provinsi<br>{selected_provinsi}</h5></div>",
          unsafe_allow_html=True,
      )
      try:
        # 1. Filter murni hanya untuk kelompok Pajak Daerah (biasanya berawalan '4101')
        df_pajak = df_wilayah[
            df_wilayah["standarjenismap"].astype(str).str.startswith("4101")
        ]
        if df_pajak.empty:
          df_pajak = df_wilayah[
              df_wilayah["standarjenismap"].astype(str).str.startswith("41")
          ]

        val_col = next(
            (
                c
                for c in ["sum", "Nilai", "Realisasi", "Jumlah", "value"]
                if c in df_pajak.columns
            ),
            None,
        )

        if val_col and not df_pajak.empty:
          # 2. Salin dataframe dan kelompokkan PBJT menjadi satu nama kategori seragam "PBJT"
          df_pajak_processed = df_pajak.copy()

          # Jika uraian jenis map mengandung kata 'PBJT' atau 'Pajak Barang Jasa Tertentu', satukan namanya
          mask_pbjt = (
              df_pajak_processed["Objek_Lv2"]
              .astype(str)
              .str.contains("PBJT|Barang dan Jasa Tertentu", case=False)
          )
          df_pajak_processed.loc[mask_pbjt, "Objek_Lv2"] = "PBJT"

          # Groupby berdasarkan uraian yang telah disatukan
          top_pajak = (
              df_pajak_processed.groupby("Objek_Lv2")[val_col]
              .sum()
              .reset_index(name="total_nilai")
          )

          total_all = top_pajak["total_nilai"].sum()
          if total_all > 0:
            top_pajak["persen"] = (
                top_pajak["total_nilai"] / total_all
            ) * 100
            top_pajak = top_pajak.sort_values(
                by="persen", ascending=False
            ).head(5)

            fig, ax = plt.subplots(figsize=(7, 4))
            bars1 = ax.bar(
                top_pajak["Objek_Lv2"],
                top_pajak["persen"],
                color="#1b6ca8",
                width=0.5,
            )
            ax.get_yaxis().set_visible(False)
            for spine in ax.spines.values():
              spine.set_visible(False)
            ax.set_ylim(0, top_pajak["persen"].max() * 1.3)
            plt.xticks(fontsize=8)

            for p in bars1:
              h = p.get_height()
              if h > 0:
                ax.annotate(
                    f"{h:.1f}%",
                    xy=(p.get_x() + p.get_width() / 2, h),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    weight="bold",
                )
            st.pyplot(fig, use_container_width=True)
          else:
            st.info("Data pajak kosong.")
        else:
          st.info("Data tidak ditemukan.")
      except Exception as e:
        st.error(f"Error Grafik Ranking: {e}")

    # Grafik Kanan 1: Peran PAD dalam Pendapatan Daerah (Combo Chart)
    with col2:
      st.markdown(
          f"<div style='text-align: center; min-height: 75px;'>📈 Peran PAD"
          f" dalam Pendapatan Daerah<br>{display_title_wilayah}<br><span"
          f" style='font-size: 0.85em; font-weight: normal;'>(Miliar"
          f" Rp)</span></div>",
          unsafe_allow_html=True,
      )
      try:
        val_col = next(
            (
                c
                for c in ["sum", "Nilai", "Realisasi", "Jumlah", "value"]
                if c in df_agregat.columns
            ),
            None,
        )
        if val_col:
          df_pendapatan = (
              df_agregat.groupby("Tahun")[val_col]
              .sum()
              .reset_index(name="total_pendapatan")
          )
          df_pad_komponen = df_agregat[
              df_agregat["standarjenismap"].astype(str).str.startswith("41")
          ]
          df_pad_tahunan = (
              df_pad_komponen.groupby("Tahun")[val_col]
              .sum()
              .reset_index(name="total_pad")
          )

          combo_df = pd.merge(
              df_pad_tahunan, df_pendapatan, on="Tahun", how="left"
          )
          combo_df["sum_miliar"] = combo_df["total_pad"] / 1e9
          combo_df["persen"] = (
              combo_df["total_pad"] / combo_df["total_pendapatan"]
          ) * 100
          combo_df = combo_df.sort_values("Tahun")

          if not combo_df.empty:
            fig, ax = plt.subplots(figsize=(7, 4))
            bars2 = ax.bar(
                combo_df["Tahun"].astype(str),
                combo_df["sum_miliar"],
                color="#1b6ca8",
                width=0.5,
                label="TOTAL PAD",
            )
            ax.get_yaxis().set_visible(False)
            for spine in ax.spines.values():
              spine.set_visible(False)
            ax.set_ylim(0, combo_df["sum_miliar"].max() * 1.4)

            for bar in bars2:
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
                    xy=(bar.get_x() + bar.get_width() / 2, yval * 0.05),
                    xytext=(0, 0),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="white",
                    weight="bold",
                )

            ax2 = ax.twinx()
            ax2.get_yaxis().set_visible(False)
            for spine in ax2.spines.values():
              spine.set_visible(False)
            ax2.set_ylim(0, max(combo_df["persen"].max() * 1.5, 30))
            ax2.plot(
                combo_df["Tahun"].astype(str),
                combo_df["persen"],
                color="#f26419",
                linewidth=2,
                marker="o",
                markersize=4,
                label="% PAD",
            )

            for x, y in zip(combo_df["Tahun"].astype(str), combo_df["persen"]):
              ax2.annotate(
                  f"{y:.2f}%",
                  xy=(x, y),
                  xytext=(0, 10),
                  textcoords="offset points",
                  ha="center",
                  va="bottom",
                  fontsize=8,
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
            lines_1, labels_1 = ax.get_legend_handles_labels()
            lines_2, labels_2 = ax2.get_legend_handles_labels()
            ax.legend(
                lines_1 + lines_2,
                labels_1 + labels_2,
                loc="upper center",
                bbox_to_anchor=(0.5, -0.15),
                ncol=2,
                frameon=False,
                fontsize=8,
            )
            st.pyplot(fig, use_container_width=True)
      except Exception as e:
        st.error(f"Error: {e}")
  else:
    st.warning("Data agregat provinsi tidak ditemukan.")


# =========================================================================
# TAB 2: PROVINSI SAJA (Level Pemda Provinsi)
# =========================================================================
with tab2:
  st.markdown(f"#### Analisis Level Pemda Provinsi {selected_provinsi}")
  df_prov_saja = df[
      (df[kolom_provinsi] == selected_provinsi)
      & (df[kolom_pemda].astype(str).str.contains("Provinsi|DKI", case=False))
  ]
  
  # Tambahkan baris penampung universal ini:
  df_wilayah = df_prov_saja
  display_title_wilayah = f"Pemda Provinsi {selected_provinsi}"

  if not df_prov_saja.empty:
    display_title_wilayah = f"Pemda Provinsi {selected_provinsi}"

    st.markdown("##### 📋 Tabel Rangkuman Pendapatan Daerah (Level 2)")
    # (Sisipkan kode tabel level 2 Anda di sini menggunakan df_prov_saja)

    st.markdown("---")

    col1, col2 = st.columns(2)

    # Grafik Kiri 2: Ranking Pajak Daerah Provinsi Saja
    with col1:
      st.markdown(
          f"<div style='text-align: center; min-height: 75px;'><h5>📊 Ranking"
          f" Pajak Daerah<br>{display_title_wilayah}</h5></div>",
          unsafe_allow_html=True,
      )
      try:
        # 1. Filter murni hanya untuk kelompok Pajak Daerah (biasanya berawalan '4101')
        df_pajak = df_wilayah[
            df_wilayah["standarjenismap"].astype(str).str.startswith("4101")
        ]
        if df_pajak.empty:
          df_pajak = df_wilayah[
              df_wilayah["standarjenismap"].astype(str).str.startswith("41")
          ]

        val_col = next(
            (
                c
                for c in ["sum", "Nilai", "Realisasi", "Jumlah", "value"]
                if c in df_pajak.columns
            ),
            None,
        )

        if val_col and not df_pajak.empty:
          # 2. Salin dataframe dan kelompokkan PBJT menjadi satu nama kategori seragam "PBJT"
          df_pajak_processed = df_pajak.copy()

          # Jika uraian jenis map mengandung kata 'PBJT' atau 'Pajak Barang Jasa Tertentu', satukan namanya
          mask_pbjt = (
              df_pajak_processed["Objek_Lv2"]
              .astype(str)
              .str.contains("PBJT|Barang dan Jasa Tertentu", case=False)
          )
          df_pajak_processed.loc[mask_pbjt, "Objek_Lv2"] = "PBJT"

          # Groupby berdasarkan uraian yang telah disatukan
          top_pajak = (
              df_pajak_processed.groupby("Objek_Lv2")[val_col]
              .sum()
              .reset_index(name="total_nilai")
          )

          total_all = top_pajak["total_nilai"].sum()
          if total_all > 0:
            top_pajak["persen"] = (
                top_pajak["total_nilai"] / total_all
            ) * 100
            top_pajak = top_pajak.sort_values(
                by="persen", ascending=False
            ).head(5)

            fig, ax = plt.subplots(figsize=(7, 4))
            bars1 = ax.bar(
                top_pajak["Objek_Lv2"],
                top_pajak["persen"],
                color="#1b6ca8",
                width=0.5,
            )
            ax.get_yaxis().set_visible(False)
            for spine in ax.spines.values():
              spine.set_visible(False)
            ax.set_ylim(0, top_pajak["persen"].max() * 1.3)
            plt.xticks(fontsize=8)

            for p in bars1:
              h = p.get_height()
              if h > 0:
                ax.annotate(
                    f"{h:.1f}%",
                    xy=(p.get_x() + p.get_width() / 2, h),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    weight="bold",
                )
            st.pyplot(fig, use_container_width=True)
          else:
            st.info("Data pajak kosong.")
        else:
          st.info("Data tidak ditemukan.")
      except Exception as e:
        st.error(f"Error Grafik Ranking: {e}")

    # Grafik Kanan 2: Peran PAD Provinsi Saja
    with col2:
      st.markdown(
          f"<div style='text-align: center; min-height: 75px;'>📈 Peran PAD"
          f" dalam Pendapatan Daerah<br>{display_title_wilayah}<br><span"
          f" style='font-size: 0.85em; font-weight: normal;'>(Miliar"
          f" Rp)</span></div>",
          unsafe_allow_html=True,
      )
      try:
        val_col = next(
            (
                c
                for c in ["sum", "Nilai", "Realisasi", "Jumlah", "value"]
                if c in df_prov_saja.columns
            ),
            None,
        )
        if val_col:
          df_pendapatan = (
              df_prov_saja.groupby("Tahun")[val_col]
              .sum()
              .reset_index(name="total_pendapatan")
          )
          df_pad_komponen = df_prov_saja[
              df_prov_saja["standarjenismap"].astype(str).str.startswith("41")
          ]
          df_pad_tahunan = (
              df_pad_komponen.groupby("Tahun")[val_col]
              .sum()
              .reset_index(name="total_pad")
          )

          combo_df = pd.merge(
              df_pad_tahunan, df_pendapatan, on="Tahun", how="left"
          )
          combo_df["sum_miliar"] = combo_df["total_pad"] / 1e9
          combo_df["persen"] = (
              combo_df["total_pad"] / combo_df["total_pendapatan"]
          ) * 100
          combo_df = combo_df.sort_values("Tahun")

          if not combo_df.empty:
            fig, ax = plt.subplots(figsize=(7, 4))
            bars2 = ax.bar(
                combo_df["Tahun"].astype(str),
                combo_df["sum_miliar"],
                color="#1b6ca8",
                width=0.5,
                label="TOTAL PAD",
            )
            ax.get_yaxis().set_visible(False)
            for spine in ax.spines.values():
              spine.set_visible(False)
            ax.set_ylim(0, combo_df["sum_miliar"].max() * 1.4)

            for bar in bars2:
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
                    xy=(bar.get_x() + bar.get_width() / 2, yval * 0.05),
                    xytext=(0, 0),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="white",
                    weight="bold",
                )

            ax2 = ax.twinx()
            ax2.get_yaxis().set_visible(False)
            for spine in ax2.spines.values():
              spine.set_visible(False)
            ax2.set_ylim(0, max(combo_df["persen"].max() * 1.5, 30))
            ax2.plot(
                combo_df["Tahun"].astype(str),
                combo_df["persen"],
                color="#f26419",
                linewidth=2,
                marker="o",
                markersize=4,
                label="% PAD",
            )

            for x, y in zip(combo_df["Tahun"].astype(str), combo_df["persen"]):
              ax2.annotate(
                  f"{y:.2f}%",
                  xy=(x, y),
                  xytext=(0, 10),
                  textcoords="offset points",
                  ha="center",
                  va="bottom",
                  fontsize=8,
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
            lines_1, labels_1 = ax.get_legend_handles_labels()
            lines_2, labels_2 = ax2.get_legend_handles_labels()
            ax.legend(
                lines_1 + lines_2,
                labels_1 + labels_2,
                loc="upper center",
                bbox_to_anchor=(0.5, -0.15),
                ncol=2,
                frameon=False,
                fontsize=8,
            )
            st.pyplot(fig, use_container_width=True)
      except Exception as e:
        st.error(f"Error: {e}")
  else:
    st.warning("Data level provinsi tidak ditemukan.")


# =========================================================================
# TAB 3: KAB./KOTA SAJA (Pilihan Pemda di dalam Konten Utama)
# =========================================================================
with tab3:
  st.markdown("#### Analisis Kabupaten / Kota Spesifik")

  # Menyiapkan pilihan nama kabupaten/kota di dalam konten utama (bukan sidebar)
  list_kab_kota = df[
      (df[kolom_provinsi] == selected_provinsi)
      & (~df[kolom_pemda].astype(str).str.contains("Provinsi|DKI", case=False))
  ][kolom_pemda].unique()
  list_kab_kota = sorted([str(x) for x in list_kab_kota])

  if list_kab_kota:
    # Widget Selectbox diletakkan di dalam tab konten utama
    selected_pemda_tab3 = st.selectbox(
        "Pilih Nama Kabupaten / Kota", list_kab_kota, key="select_pemda_tab3"
    )

    df_kab_saja = df[
        (df[kolom_provinsi] == selected_provinsi)
        & (df[kolom_pemda] == selected_pemda_tab3)
    ]
    
    # Tambahkan baris penampung universal ini:
    df_wilayah = df_kab_saja
    display_title_wilayah = selected_pemda_tab3
    
    display_title_wilayah = selected_pemda_tab3

    st.markdown("##### 📋 Tabel Rangkuman Pendapatan Daerah (Level 2)")
    # (Sisipkan kode tabel level 2 Anda di sini menggunakan df_kab_saja)

    st.markdown("---")

    col1, col2 = st.columns(2)

    # Grafik Kiri 3: Ranking Pajak Daerah Kab./Kota
    with col1:
      st.markdown(
          f"<div style='text-align: center; min-height: 75px;'><h5>📊 Ranking"
          f" Pajak Daerah<br>{display_title_wilayah}</h5></div>",
          unsafe_allow_html=True,
      )
      try:
        # 1. Filter murni hanya untuk kelompok Pajak Daerah (biasanya berawalan '4101')
        df_pajak = df_wilayah[
            df_wilayah["standarjenismap"].astype(str).str.startswith("4101")
        ]
        if df_pajak.empty:
          df_pajak = df_wilayah[
              df_wilayah["standarjenismap"].astype(str).str.startswith("41")
          ]

        val_col = next(
            (
                c
                for c in ["sum", "Nilai", "Realisasi", "Jumlah", "value"]
                if c in df_pajak.columns
            ),
            None,
        )

        if val_col and not df_pajak.empty:
          # 2. Salin dataframe dan kelompokkan PBJT menjadi satu nama kategori seragam "PBJT"
          df_pajak_processed = df_pajak.copy()

          # Jika uraian jenis map mengandung kata 'PBJT' atau 'Pajak Barang Jasa Tertentu', satukan namanya
          mask_pbjt = (
              df_pajak_processed["Objek_Lv2"]
              .astype(str)
              .str.contains("PBJT|Barang dan Jasa Tertentu", case=False)
          )
          df_pajak_processed.loc[mask_pbjt, "Objek_Lv2"] = "PBJT"

          # Groupby berdasarkan uraian yang telah disatukan
          top_pajak = (
              df_pajak_processed.groupby("Objek_Lv2")[val_col]
              .sum()
              .reset_index(name="total_nilai")
          )

          total_all = top_pajak["total_nilai"].sum()
          if total_all > 0:
            top_pajak["persen"] = (
                top_pajak["total_nilai"] / total_all
            ) * 100
            top_pajak = top_pajak.sort_values(
                by="persen", ascending=False
            ).head(5)

            fig, ax = plt.subplots(figsize=(7, 4))
            bars1 = ax.bar(
                top_pajak["Objek_Lv2"],
                top_pajak["persen"],
                color="#1b6ca8",
                width=0.5,
            )
            ax.get_yaxis().set_visible(False)
            for spine in ax.spines.values():
              spine.set_visible(False)
            ax.set_ylim(0, top_pajak["persen"].max() * 1.3)
            plt.xticks(fontsize=8)

            for p in bars1:
              h = p.get_height()
              if h > 0:
                ax.annotate(
                    f"{h:.1f}%",
                    xy=(p.get_x() + p.get_width() / 2, h),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    weight="bold",
                )
            st.pyplot(fig, use_container_width=True)
          else:
            st.info("Data pajak kosong.")
        else:
          st.info("Data tidak ditemukan.")
      except Exception as e:
        st.error(f"Error Grafik Ranking: {e}")

    # Grafik Kanan 3: Peran PAD Kab./Kota Saja
    with col2:
      st.markdown(
          f"<div style='text-align: center; min-height: 75px;'>📈 Peran PAD"
          f" dalam Pendapatan Daerah<br>{display_title_wilayah}<br><span"
          f" style='font-size: 0.85em; font-weight: normal;'>(Miliar"
          f" Rp)</span></div>",
          unsafe_allow_html=True,
      )
      try:
        val_col = next(
            (
                c
                for c in ["sum", "Nilai", "Realisasi", "Jumlah", "value"]
                if c in df_kab_saja.columns
            ),
            None,
        )
        if val_col:
          df_pendapatan = (
              df_kab_saja.groupby("Tahun")[val_col]
              .sum()
              .reset_index(name="total_pendapatan")
          )
          df_pad_komponen = df_kab_saja[
              df_kab_saja["standarjenismap"].astype(str).str.startswith("41")
          ]
          df_pad_tahunan = (
              df_pad_komponen.groupby("Tahun")[val_col]
              .sum()
              .reset_index(name="total_pad")
          )

          combo_df = pd.merge(
              df_pad_tahunan, df_pendapatan, on="Tahun", how="left"
          )
          combo_df["sum_miliar"] = combo_df["total_pad"] / 1e9
          combo_df["persen"] = (
              combo_df["total_pad"] / combo_df["total_pendapatan"]
          ) * 100
          combo_df = combo_df.sort_values("Tahun")

          if not combo_df.empty:
            fig, ax = plt.subplots(figsize=(7, 4))
            bars2 = ax.bar(
                combo_df["Tahun"].astype(str),
                combo_df["sum_miliar"],
                color="#1b6ca8",
                width=0.5,
                label="TOTAL PAD",
            )
            ax.get_yaxis().set_visible(False)
            for spine in ax.spines.values():
              spine.set_visible(False)
            ax.set_ylim(0, combo_df["sum_miliar"].max() * 1.4)

            for bar in bars2:
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
                    xy=(bar.get_x() + bar.get_width() / 2, yval * 0.05),
                    xytext=(0, 0),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="white",
                    weight="bold",
                )

            ax2 = ax.twinx()
            ax2.get_yaxis().set_visible(False)
            for spine in ax2.spines.values():
              spine.set_visible(False)
            ax2.set_ylim(0, max(combo_df["persen"].max() * 1.5, 30))
            ax2.plot(
                combo_df["Tahun"].astype(str),
                combo_df["persen"],
                color="#f26419",
                linewidth=2,
                marker="o",
                markersize=4,
                label="% PAD",
            )

            for x, y in zip(combo_df["Tahun"].astype(str), combo_df["persen"]):
              ax2.annotate(
                  f"{y:.2f}%",
                  xy=(x, y),
                  xytext=(0, 10),
                  textcoords="offset points",
                  ha="center",
                  va="bottom",
                  fontsize=8,
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
            lines_1, labels_1 = ax.get_legend_handles_labels()
            lines_2, labels_2 = ax2.get_legend_handles_labels()
            ax.legend(
                lines_1 + lines_2,
                labels_1 + labels_2,
                loc="upper center",
                bbox_to_anchor=(0.5, -0.15),
                ncol=2,
                frameon=False,
                fontsize=8,
            )
            st.pyplot(fig, use_container_width=True)
      except Exception as e:
        st.error(f"Error: {e}")
  else:
    st.warning("Daftar Kabupaten/Kota tidak ditemukan.")

st.markdown("---")
st.caption("💡 Dashboard PDRD Data Hub - Struktur PBJT, Sub Total, & Total PDRD.")