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
# 1. SIDEBAR: FILTER & CAKUPAN WILAYAH
# ==========================================
st.sidebar.markdown("### 📌 Cakupan Analisis Wilayah")

kategori_wilayah = st.sidebar.radio(
    "Pilih Kategori Cakupan",
    [
        "1. Agregat Provinsi (Provinsi + Kab./Kota)",
        "2. Provinsi Saja (Level Provinsi)",
        "3. Kab./Kota Saja (Spesifik per Daerah)",
    ],
)

st.sidebar.markdown("---")

# Pilih Provinsi diletakkan SATU KALI di sini agar tidak duplikat
selected_provinsi = st.sidebar.selectbox(
    "Pilih Provinsi", sorted(df[kolom_provinsi].unique())
)

# Inisialisasi variabel pilihan pemda
selected_pemda = None

if "1. Agregat" in kategori_wilayah:
  display_title_wilayah = f"Provinsi {selected_provinsi} (Agregat)"
  df_pemda_all = df[df[kolom_provinsi] == selected_provinsi]

elif "2. Provinsi Saja" in kategori_wilayah:
  display_title_wilayah = f"Provinsi {selected_provinsi} (Pemda Provinsi)"
  # Filter khusus baris level provinsi (sesuaikan penamaan di dataset Anda jika perlu)
  df_pemda_all = df[
      (df[kolom_provinsi] == selected_provinsi)
      & (df[kolom_pemda].astype(str).str.contains("Provinsi|DKI", case=False))
  ]

else:
  # Memunculkan kembali pilihan Kabupaten/Kota di bawah tab pilih provinsi
  list_kab_kota = df[
      (df[kolom_provinsi] == selected_provinsi)
      & (~df[kolom_pemda].astype(str).str.contains("Provinsi|DKI", case=False))
  ][kolom_pemda].unique()

  selected_pemda = st.sidebar.selectbox(
      "Pilih Nama Kabupaten / Kota", sorted([str(x) for x in list_kab_kota])
  )
  display_title_wilayah = selected_pemda
  df_pemda_all = df[
      (df[kolom_provinsi] == selected_provinsi)
      & (df[kolom_pemda] == selected_pemda)
  ]


# ==========================================
# 2. UTAMA: TAMPILAN DUA KOLOM GRAFIK
# ==========================================
col1, col2 = st.columns(2)

# ------------------------------------------
# KOLOM 1: KONTRIBUTOR UTAMA PAJAK DAERAH
# ------------------------------------------
with col1:
  st.markdown(
      f"<div style='text-align: center; min-height: 75px;'><h5>📊 Kontributor"
      f" Utama Pajak Daerah<br>{display_title_wilayah}</h5></div>",
      unsafe_allow_html=True,
  )
  try:
    if not df_pemda_all.empty:
      # Filter kode pajak (misalnya berawalan 4101 atau sesuai struktur Anda)
      df_pajak = df_pemda_all[
          df_pemda_all["standarjenismap"].astype(str).str.startswith("4101")
      ]
      if df_pajak.empty:
        df_pajak = df_pemda_all[
            df_pemda_all["standarjenismap"].astype(str).str.startswith("41")
        ]

      # Deteksi kolom nilai otomatis
      possible_value_cols = ["sum", "Nilai", "Realisasi", "Jumlah", "value"]
      val_col = next(
          (c for c in possible_value_cols if c in df_pajak.columns), None
      )
      if not val_col:
        numeric_cols = [
            c
            for c in df_pajak.select_dtypes(include=["number"]).columns
            if c.lower() != "tahun"
        ]
        val_col = numeric_cols[0] if numeric_cols else None

      if val_col:
        top_pajak = (
            df_pajak.groupby("uraianjenismap")[val_col]
            .sum()
            .reset_index(name="total_nilai")
        )
        total_all_pajak = top_pajak["total_nilai"].sum()

        if total_all_pajak > 0:
          top_pajak["persen"] = (
              top_pajak["total_nilai"] / total_all_pajak
          ) * 100
          top_pajak = top_pajak.sort_values(
              by="persen", ascending=False
          ).head(5)

          fig, ax = plt.subplots(figsize=(7, 4))
          bars1 = ax.bar(
              top_pajak["uraianjenismap"],
              top_pajak["persen"],
              color="#1b6ca8",
              width=0.5,
          )

          ax.get_yaxis().set_visible(False)
          for spine in ax.spines.values():
            spine.set_visible(False)
          ax.set_ylim(0, top_pajak["persen"].max() * 1.3)
          plt.xticks(rotation=0, fontsize=8)

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

          ax.set_xlabel("")
          st.pyplot(fig, use_container_width=True)
        else:
          st.info("Data pajak kosong.")
      else:
        st.error("Kolom nilai tidak ditemukan.")
    else:
      st.info("Data wilayah tidak tersedia.")
  except Exception as e:
    st.error(f"Gagal merender Grafik Kiri: {str(e)}")


# ------------------------------------------
# KOLOM 2: COMBO CHART (PERAN PAD)
# ------------------------------------------
with col2:
  st.markdown(
      f"<div style='text-align: center; min-height: 75px;'>📈 Peran PAD dalam"
      f" Pendapatan Daerah<br>{display_title_wilayah}<br><span"
      f" style='font-size: 0.85em; font-weight: normal;'>(Miliar"
      f" Rp)</span></div>",
      unsafe_allow_html=True,
  )
  try:
    if not df_pemda_all.empty:
      possible_value_cols = ["sum", "Nilai", "Realisasi", "Jumlah", "value"]
      val_col = next(
          (c for c in possible_value_cols if c in df_pemda_all.columns), None
      )
      if not val_col:
        numeric_cols = [
            c
            for c in df_pemda_all.select_dtypes(include=["number"]).columns
            if c.lower() != "tahun"
        ]
        val_col = numeric_cols[0] if numeric_cols else None

      if val_col:
        # Total Pendapatan Keseluruhan per Tahun
        df_pendapatan = (
            df_pemda_all.groupby("Tahun")[val_col]
            .sum()
            .reset_index(name="total_pendapatan")
        )

        # Total PAD per Tahun (Awalan '41')
        df_pad_komponen = df_pemda_all[
            df_pemda_all["standarjenismap"].astype(str).str.startswith("41")
        ]
        df_pad_tahunan = (
            df_pad_komponen.groupby("Tahun")[val_col]
            .sum()
            .reset_index(name="total_pad")
        )

        combo_df = pd.merge(
            df_pad_tahunan, df_pendapatan, on="Tahun", how="left"
        )
        combo_df["sum_miliar"] = (
            combo_df["total_pad"] / 1e9
        )  # Skala Miliar (sesuaikan dengan sumber data Anda)
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

          # Label nominal batang dengan format pemisah ribuan titik (.) dan desimal koma (,)
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

          # Sumbu kembar untuk Line Chart (% Rasio)
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
        else:
          st.info("Data tren kosong.")
      else:
        st.error("Kolom nilai tidak ditemukan.")
    else:
      st.info("Data wilayah tidak tersedia.")
  except Exception as e:
    st.error(f"Gagal merender Combo Chart: {str(e)}")

st.markdown("---")
st.caption("💡 Dashboard PDRD Data Hub - Struktur PBJT, Sub Total, & Total PDRD.")