"""Demonstrasi SIGAP tanpa MySQL. Install pandas sebelum menjalankan."""

import json
import math
from pathlib import Path
from html import escape
import pandas as pd

try:
    from IPython.display import display, HTML
except ImportError:
    def display(value):
        print(value.to_string(index=False) if isinstance(value, pd.DataFrame) else value)
    def HTML(value):
        return value

print('Python siap. pandas:', pd.__version__)


def combine(a: float, b: float) -> float:
    return a + b * (1 - a)


def nilai(gejala: dict) -> float:
    skor = 0.0
    for cf in gejala.values():
        skor = combine(skor, cf)
    return skor


def kontribusi(gejala: dict) -> dict:
    penuh = nilai(gejala)
    hasil = {}
    for k in gejala:
        gejala_tanpa_k = {x: v for x, v in gejala.items() if x != k}
        hasil[k] = penuh - nilai(gejala_tanpa_k)
    return hasil


def klasifikasi_risiko(skor_cf: float) -> str:
    if skor_cf < 0.40:
        return "Rendah"
    elif skor_cf < 0.70:
        return "Sedang"
    else:
        return "Tinggi"


def prediksi_lulus_tepat_waktu(total_sks_lulus: int,
                                semester_sekarang: int,
                                target_sks: int = 144,
                                target_semester: int = 8,
                                max_sks_per_semester: int = 24) -> dict:
    """Prediksi apakah mahasiswa akan lulus tepat waktu (PERSIS 8 semester, 144 SKS).

    Aturan ketat:
      - semester_sekarang > 8:
          * SKS >= 144 -> "Lulus Terlambat (Melebihi 8 Semester)"
          * SKS < 144  -> "Tidak Lulus Tepat Waktu"
      - semester_sekarang == 8:
          * SKS >= 144 -> "Lulus Tepat Waktu"
          * SKS < 144  -> "Tidak Lulus Tepat Waktu"
      - semester_sekarang < 8 dan SKS >= 144:
          * "Sudah Memenuhi Syarat Kelulusan" (bisa lulus lebih cepat)
      - semester_sekarang < 8 dan SKS < 144:
          * Proyeksikan SKS di semester 8 berdasarkan tren
          * Jika proyeksi >= 144 -> "On Track"
          * Jika SKS/semester dibutuhkan <= 24 -> "Berisiko (masih bisa)"
          * Jika tidak -> "Berisiko Tinggi Tidak Lulus Tepat Waktu"
    """
    sks_dibutuhkan = target_sks - total_sks_lulus
    semester_tersisa = target_semester - semester_sekarang
    avg_sks = round(total_sks_lulus / semester_sekarang, 1) if semester_sekarang > 0 else 0

    # Kasus 1: Sudah melebihi batas semester target (> 8)
    if semester_sekarang > target_semester:
        if total_sks_lulus >= target_sks:
            return {
                "status": "Lulus Terlambat (Melebihi 8 Semester)",
                "warna": "warning", "mungkin": False,
                "total_sks_lulus": total_sks_lulus, "sks_dibutuhkan": 0,
                "semester_tersisa": 0, "sks_per_sem_dibutuhkan": None,
                "avg_sks_per_semester": avg_sks,
                "projected_sks_semester_8": total_sks_lulus,
            }
        else:
            return {
                "status": "Tidak Lulus Tepat Waktu",
                "warna": "danger", "mungkin": False,
                "total_sks_lulus": total_sks_lulus, "sks_dibutuhkan": sks_dibutuhkan,
                "semester_tersisa": 0, "sks_per_sem_dibutuhkan": None,
                "avg_sks_per_semester": avg_sks,
                "projected_sks_semester_8": total_sks_lulus,
            }

    # Kasus 2: Tepat di semester 8
    if semester_sekarang == target_semester:
        if total_sks_lulus >= target_sks:
            return {
                "status": "Lulus Tepat Waktu",
                "warna": "success", "mungkin": True,
                "total_sks_lulus": total_sks_lulus, "sks_dibutuhkan": 0,
                "semester_tersisa": 0, "sks_per_sem_dibutuhkan": 0,
                "avg_sks_per_semester": avg_sks,
                "projected_sks_semester_8": total_sks_lulus,
            }
        else:
            return {
                "status": "Tidak Lulus Tepat Waktu",
                "warna": "danger", "mungkin": False,
                "total_sks_lulus": total_sks_lulus, "sks_dibutuhkan": sks_dibutuhkan,
                "semester_tersisa": 0, "sks_per_sem_dibutuhkan": None,
                "avg_sks_per_semester": avg_sks,
                "projected_sks_semester_8": total_sks_lulus,
            }

    # Kasus 3: Sudah memenuhi 144 SKS sebelum semester 8 (bisa lulus cepat)
    if sks_dibutuhkan <= 0:
        return {
            "status": "Sudah Memenuhi Syarat Kelulusan",
            "warna": "success", "mungkin": True,
            "total_sks_lulus": total_sks_lulus, "sks_dibutuhkan": 0,
            "semester_tersisa": semester_tersisa, "sks_per_sem_dibutuhkan": 0,
            "avg_sks_per_semester": avg_sks,
            "projected_sks_semester_8": total_sks_lulus,
        }

    # Kasus 4: Masih aktif (semester < 8) dan belum mencapai 144
    avg_sks_per_sem = total_sks_lulus / semester_sekarang if semester_sekarang > 0 else 0
    projected_sks = total_sks_lulus + semester_tersisa * avg_sks_per_sem
    sks_per_sem_dibutuhkan = sks_dibutuhkan / semester_tersisa
    mungkin = sks_per_sem_dibutuhkan <= max_sks_per_semester

    if projected_sks >= target_sks:
        status = "On Track (Diprediksi Lulus Tepat Waktu)"
        warna = "success"
    elif mungkin:
        status = "Berisiko (Masih Bisa Dicapai dengan Beban SKS Tinggi)"
        warna = "warning"
    else:
        status = "Berisiko Tinggi Tidak Lulus Tepat Waktu"
        warna = "danger"

    return {
        "status": status, "warna": warna, "mungkin": mungkin,
        "total_sks_lulus": total_sks_lulus, "sks_dibutuhkan": sks_dibutuhkan,
        "semester_tersisa": semester_tersisa,
        "sks_per_sem_dibutuhkan": round(sks_per_sem_dibutuhkan, 1),
        "avg_sks_per_semester": round(avg_sks_per_sem, 1),
        "projected_sks_semester_8": round(projected_sks, 1),
    }


ATURAN = [{'kode': 'G1', 'deskripsi': 'Kehadiran kuliah di bawah 75 persen', 'indikator': 'kehadiran', 'kondisi': '<', 'ambang': 75.0, 'metrik': 'kehadiran', 'cf_pakar': 0.6, 'tiers': [{'min': 70, 'max': 74.99, 'cf_user': 0.5}, {'min': 60, 'max': 69.99, 'cf_user': 0.8}, {'min': 0, 'max': 59.99, 'cf_user': 1.0}]}, {'kode': 'G3', 'deskripsi': 'Keterlambatan mengumpulkan tugas >= 3 kali', 'indikator': 'terlambat', 'kondisi': '>=', 'ambang': 3.0, 'metrik': 'jumlah_terlambat', 'cf_pakar': 0.4, 'tiers': [{'min': 3, 'max': 4, 'cf_user': 0.6}, {'min': 5, 'max': 6, 'cf_user': 0.8}, {'min': 7, 'max': 99, 'cf_user': 1.0}]}, {'kode': 'G4', 'deskripsi': 'IPS terakhir turun >= 0.5 dari semester sebelumnya', 'indikator': 'ips_drop', 'kondisi': '>=', 'ambang': 0.5, 'metrik': 'ips_drop', 'cf_pakar': 0.55, 'tiers': [{'min': 0.5, 'max': 0.79, 'cf_user': 0.5}, {'min': 0.8, 'max': 1.19, 'cf_user': 0.8}, {'min': 1.2, 'max': 4.0, 'cf_user': 1.0}]}, {'kode': 'G6', 'deskripsi': 'Progress SKS di bawah target timeline kelulusan', 'indikator': 'sks_progress_ratio', 'kondisi': '<', 'ambang': 0.85, 'metrik': 'sks_progress_ratio', 'cf_pakar': 0.5, 'tiers': [{'min': 0.7, 'max': 0.849, 'cf_user': 0.5}, {'min': 0.5, 'max': 0.699, 'cf_user': 0.8}, {'min': 0.0, 'max': 0.499, 'cf_user': 1.0}]}]

ringkasan_aturan = pd.DataFrame([
    {k: v for k, v in a.items() if k != 'tiers'} for a in ATURAN
])
display(ringkasan_aturan[['kode', 'deskripsi', 'metrik', 'kondisi', 'ambang', 'cf_pakar']])


import random

PRODI_LIST = ['Teknik Informatika', 'Sistem Informasi', 'Ilmu Komputer']

NAMA_DEPAN = ['Adi', 'Budi', 'Citra', 'Dewi', 'Eka', 'Fajar', 'Gita', 'Hadi',
              'Indah', 'Joko', 'Kartika', 'Lina', 'Made', 'Nia', 'Oki', 'Putri',
              'Rama', 'Sari', 'Tono', 'Umar', 'Vina', 'Wawan', 'Yuni', 'Zaki']

NAMA_BELAKANG = ['Pratama', 'Santoso', 'Wijaya', 'Lestari', 'Hidayat', 'Maulana',
                 'Anggraini', 'Permata', 'Kusuma', 'Nugroho', 'Rahmawati', 'Saputra',
                 'Wibowo', 'Yulianti', 'Halim', 'Putri', 'Ramadhan', 'Safitri']

def buat_nama(i):
    return f"{random.choice(NAMA_DEPAN)} {random.choice(NAMA_BELAKANG)} {i:03d}"

def generate_progresi_semester(kategori, semester_sekarang):
    data = []
    for sem in range(1, semester_sekarang + 1):
        if kategori == 'on_track':
            sks_diambil = random.choice([18, 20, 20, 21, 22])
            gagal = random.choices([0, 0, 0, 2], k=1)[0]
            ips = round(random.uniform(3.0, 3.8), 2)
        elif kategori == 'sedang':
            sks_diambil = random.choice([15, 18, 18, 20])
            gagal = random.choices([0, 0, 2, 3], k=1)[0]
            ips = round(random.uniform(2.5, 3.2), 2)
        else:
            sks_diambil = random.choice([9, 12, 12, 15, 15, 18])
            gagal = random.choices([0, 2, 3, 4, 6], k=1)[0]
            ips = round(random.uniform(1.8, 2.8), 2)
        sks_lulus = max(0, sks_diambil - gagal)
        data.append({
            'semester': sem,
            'sks_diambil': sks_diambil,
            'sks_lulus': sks_lulus,
            'ips': ips,
        })
    return data

def hitung_ringkasan(progresi, kategori):
    """Hitung data_akademik ringkasan dari progresi semester.

    PENTING: Setiap kategori DIPAKSA memicu minimal 1 gejala agar CF tidak 0 persen.
    Fungsi ini bisa memodifikasi progresi[-2]['ips'] untuk konsistensi.
    """
    if not progresi:
        return None

    ips_terakhir = progresi[-1]['ips']
    ips_sebelumnya = progresi[-2]['ips'] if len(progresi) >= 2 else ips_terakhir

    if kategori == 'on_track':
        # Paksa 1 gejala minor terpicu -> CF 15-35 persen (Rendah)
        pilihan = random.choice(['g1_minor', 'g3_minor', 'g4_minor',
                                  'g1_minor', 'g3_minor'])
        if pilihan == 'g1_minor':
            kehadiran = round(random.uniform(70.0, 74.9), 1)
            terlambat = random.randint(0, 2)
        elif pilihan == 'g3_minor':
            kehadiran = round(random.uniform(80.0, 95.0), 1)
            terlambat = random.randint(3, 4)
        else:  # g4_minor
            kehadiran = round(random.uniform(80.0, 95.0), 1)
            terlambat = random.randint(0, 2)
            if len(progresi) >= 2:
                drop = round(random.uniform(0.5, 0.7), 2)
                progresi[-2]['ips'] = round(min(4.0, ips_terakhir + drop), 2)
                ips_sebelumnya = progresi[-2]['ips']

    elif kategori == 'sedang':
        # Paksa 2 gejala: G1 + G3 -> CF 45-65 persen (Sedang)
        kehadiran = round(random.uniform(60.0, 74.9), 1)
        terlambat = random.randint(3, 5)

    else:  # tinggi
        # Paksa 3-4 gejala dengan cf_user tinggi -> CF 80-95 persen (Tinggi)
        kehadiran = round(random.uniform(45.0, 59.9), 1)
        terlambat = random.randint(5, 8)
        if len(progresi) >= 2:
            drop = round(random.uniform(0.8, 1.5), 2)
            progresi[-2]['ips'] = round(min(4.0, ips_terakhir + drop), 2)
            ips_sebelumnya = progresi[-2]['ips']

    nilai_tugas = round(random.uniform(60, 95), 1)
    total_sks_lulus = sum(p['sks_lulus'] for p in progresi)
    semester_sekarang = len(progresi)
    expected_sks = semester_sekarang * 18
    sks_progress_ratio = round(total_sks_lulus / expected_sks, 3) if expected_sks > 0 else 1.0

    return {
        'kehadiran': kehadiran,
        'nilai_tugas': nilai_tugas,
        'terlambat': terlambat,
        'ips_sebelumnya': ips_sebelumnya,
        'ips_terakhir': ips_terakhir,
        'sks_progress_ratio': sks_progress_ratio,
        'total_sks_lulus': total_sks_lulus,
    }

def buat_dataset():
    # Data simulasi dari logika seed.py; tidak menyentuh database SIGAP.
    random.seed(42)
    groups = ['on_track'] * 80 + ['sedang'] * 60 + ['tinggi'] * 60
    random.shuffle(groups)
    students, semesters = [], []
    for i, group in enumerate(groups, 1):
        nim = f'MHS2023{i:04d}'
        nama = buat_nama(i)
        angkatan = random.choice([2022, 2023, 2024])
        sem = random.randint(5, 8) if group != 'tinggi' else random.randint(4, 10)
        prodi = random.choice(PRODI_LIST)
        history = generate_progresi_semester(group, sem)
        academic = hitung_ringkasan(history, group)
        students.append({
            'nim': nim, 'nama': nama, 'prodi': prodi, 'angkatan': angkatan,
            'semester_sekarang': sem, 'kehadiran': academic['kehadiran'],
            'nilai_tugas': academic['nilai_tugas'],
            'jumlah_terlambat': academic['terlambat'],
            'ips_sebelumnya': academic['ips_sebelumnya'],
            'ips_terakhir': academic['ips_terakhir'],
            'total_sks_lulus': academic['total_sks_lulus'],
            'target_sks': 144, 'target_semester': 8,
        })
        semesters.extend({'nim': nim, **p} for p in history)
    return pd.DataFrame(students), pd.DataFrame(semesters)


DATASET_PATH = ''  # Kosong = otomatis memakai 200 mahasiswa simulasi.

data_simulasi, semester_simulasi = buat_dataset()
if DATASET_PATH:
    path = Path(DATASET_PATH)
    if path.suffix.lower() == '.csv':
        data = pd.read_csv(path, dtype={'nim': str})
    elif path.suffix.lower() == '.xlsx':
        data = pd.read_excel(path, sheet_name='Dataset', dtype={'nim': str})
    else:
        raise ValueError('Gunakan file .csv atau .xlsx.')
    print('Sumber data:', path.name)
else:
    data = data_simulasi.copy()
    print('Sumber data: SIMULASI, seed 42.')

required = list(data_simulasi.columns)
missing = set(required) - set(data.columns)
if missing:
    raise ValueError(f'Kolom belum lengkap: {sorted(missing)}')
data = data[required].copy()
if data.isna().any().any():
    raise ValueError('Data memiliki nilai kosong. Lengkapi terlebih dahulu.')
if data['nim'].astype(str).str.strip().eq('').any() or data['nim'].duplicated().any():
    raise ValueError('NIM wajib terisi dan unik: satu baris per mahasiswa.')
for column in required[3:]:
    data[column] = pd.to_numeric(data[column], errors='raise')
    if not data[column].map(math.isfinite).all():
        raise ValueError(f'{column} memuat NaN atau infinity.')
for column in ['kehadiran', 'nilai_tugas']:
    if not data[column].between(0, 100).all():
        raise ValueError(f'{column} harus 0–100.')
for column in ['ips_sebelumnya', 'ips_terakhir']:
    if not data[column].between(0, 4).all():
        raise ValueError(f'{column} harus 0–4.')
for column in ['semester_sekarang', 'target_semester', 'target_sks']:
    if not data[column].gt(0).all():
        raise ValueError(f'{column} harus positif.')
for column in ['angkatan', 'semester_sekarang', 'jumlah_terlambat', 'total_sks_lulus', 'target_sks', 'target_semester']:
    if not data[column].mod(1).eq(0).all() or not data[column].ge(0).all():
        raise ValueError(f'{column} harus berupa bilangan bulat nonnegatif.')
data['ips_drop'] = (data['ips_sebelumnya'] - data['ips_terakhir']).round(5)
data['sks_progress_ratio'] = (data['total_sks_lulus'] / (data['semester_sekarang'] * 18)).round(3)
print('Jumlah mahasiswa:', len(data))
display(data.head())


SARAN = {
    'G1': 'Bimbingan mengenai hambatan kehadiran dan komitmen kehadiran.',
    'G3': 'Susun jadwal tugas dan evaluasi manajemen waktu.',
    'G4': 'Evaluasi mata kuliah yang menurunkan IPS dan kebutuhan bimbingan belajar.',
    'G6': 'Evaluasi progres serta beban SKS dan susun strategi mengejar ketertinggalan.',
}

def ekstrak_gejala(mahasiswa):
    gejala, users = {}, {}
    for aturan in ATURAN:
        value = round(float(mahasiswa[aturan['metrik']]), 5)
        cocok = value < aturan['ambang'] if aturan['kondisi'] == '<' else value >= aturan['ambang']
        if not cocok:
            continue
        tiers = sorted(aturan['tiers'], key=lambda t: t['min'], reverse=True)
        tier = next((t for t in tiers if value >= t['min']), None)
        if tier:
            kode = aturan['kode']
            users[kode] = tier['cf_user']
            gejala[kode] = aturan['cf_pakar'] * tier['cf_user']
    return gejala, users

hasil_rows, gejala_rows = [], []
for mahasiswa in data.to_dict('records'):
    gejala, users = ekstrak_gejala(mahasiswa)
    cf = nilai(gejala)
    kontrib = kontribusi(gejala)
    prediksi = prediksi_lulus_tepat_waktu(
        mahasiswa['total_sks_lulus'], mahasiswa['semester_sekarang'],
        mahasiswa['target_sks'], mahasiswa['target_semester'],
    )
    urutan = sorted(gejala, key=lambda k: kontrib[k], reverse=True)
    hasil_rows.append({
        'nim': mahasiswa['nim'], 'nama': mahasiswa['nama'],
        'cf_gabungan': cf, 'kategori': klasifikasi_risiko(cf),
        'gejala': ', '.join(urutan) or '-',
        'status_prediksi': prediksi['status'],
        'rekomendasi': ' '.join(SARAN[k] for k in urutan) if urutan else 'Lanjutkan pemantauan rutin.',
    })
    for kode in urutan:
        gejala_rows.append({
            'nim': mahasiswa['nim'], 'kode': kode, 'cf_user': users[kode],
            'cf_gejala': gejala[kode], 'kontribusi': kontrib[kode],
        })
hasil = pd.DataFrame(hasil_rows).sort_values(['cf_gabungan', 'nim'], ascending=[False, True])
detail_gejala = pd.DataFrame(gejala_rows, columns=['nim', 'kode', 'cf_user', 'cf_gejala', 'kontribusi'])
display(hasil.head(10))


tests = []
def cek(nama, kondisi):
    assert kondisi, nama
    tests.append(nama)

contoh = {'G1': 0.48, 'G3': 0.24, 'G4': 0.385}
cek('CF contoh proposal', math.isclose(nilai(contoh), 0.756952, abs_tol=1e-9))
cek('Kontribusi G1', math.isclose(kontribusi(contoh)['G1'], 0.224352, abs_tol=1e-9))
cek('Tanpa gejala', nilai({}) == 0)
for score, label in [(0, 'Rendah'), (0.3999, 'Rendah'), (0.4, 'Sedang'), (0.7, 'Tinggi')]:
    cek(f'Kategori {score}', klasifikasi_risiko(score) == label)
base = dict(kehadiran=90, jumlah_terlambat=0, ips_drop=0, sks_progress_ratio=1)
cek('G3 terlambat 5 kali', math.isclose(ekstrak_gejala({**base, 'jumlah_terlambat': 5})[0]['G3'], .32))
cek('Tidak ada gejala palsu', ekstrak_gejala(base)[0] == {})
cek('CF user tiap gejala valid', detail_gejala['cf_user'].between(0, 1).all())
cek('CF gabungan valid', hasil['cf_gabungan'].between(0, 1).all())
cek('SKS 144 semester 8', prediksi_lulus_tepat_waktu(144, 8)['status'] == 'Lulus Tepat Waktu')
cek('SKS 140 semester 8', prediksi_lulus_tepat_waktu(140, 8)['status'] == 'Tidak Lulus Tepat Waktu')
cek('SKS kumulatif', math.isclose(120 / (6 * 18), 1.1111111111111112))
print(f'{len(tests)} pemeriksaan notebook LULUS.')
print('Pemeriksaan notebook ini terpisah dari 37 tes regresi aplikasi web.')


distribusi = hasil['kategori'].value_counts().reindex(['Tinggi', 'Sedang', 'Rendah'], fill_value=0)
display(distribusi.rename_axis('Kategori').reset_index(name='Jumlah mahasiswa'))
colors = {'Tinggi': '#bf6666', 'Sedang': '#cfaa5d', 'Rendah': '#71a68c'}
bars = []
for i, (label, jumlah) in enumerate(distribusi.items()):
    y = 20 + i * 45
    width = float(jumlah) / max(len(hasil), 1) * 400
    bars.append(f'<text x="0" y="{y+18}" font-size="14">{label}</text>'
                f'<rect x="85" y="{y}" width="{width}" height="26" rx="4" fill="{colors[label]}"/>'
                f'<text x="{100+width}" y="{y+18}" font-size="14">{jumlah}</text>')
grafik_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 580 165" role="img" aria-label="Distribusi kategori risiko">' + ''.join(bars) + '</svg>'
display(HTML(grafik_svg))
NIM_CONTOH = str(hasil.iloc[0]['nim'])  # Dapat diganti dengan NIM lain dari dataset.
display(hasil.loc[hasil['nim'].astype(str).eq(NIM_CONTOH)])
display(detail_gejala.loc[detail_gejala['nim'].astype(str).eq(NIM_CONTOH)])


import zipfile
out = Path('hasil_sigap')
out.mkdir(exist_ok=True)
data[required].to_csv(out / 'dataset_mahasiswa.csv', index=False)
hasil.to_csv(out / 'hasil_risiko.csv', index=False)
detail_gejala.to_csv(out / 'hasil_gejala.csv', index=False)
(out / 'distribusi_risiko.svg').write_text(grafik_svg, encoding='utf-8')
with zipfile.ZipFile(out / 'hasil_sigap.zip', 'w', zipfile.ZIP_DEFLATED) as arsip:
    for name in ['dataset_mahasiswa.csv', 'hasil_risiko.csv', 'hasil_gejala.csv', 'distribusi_risiko.svg']:
        arsip.write(out / name, arcname=name)
print('Selesai. Unduh file dari folder:', out.as_posix())
