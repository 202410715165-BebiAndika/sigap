import random
import pymysql
from database import get_connection

random.seed(42)

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


def seed():
    conn = get_connection()
    cur = conn.cursor()

    for tbl in ['hasil_gejala', 'hasil_risiko', 'tindak_lanjut',
                'data_semester', 'data_akademik', 'mahasiswa']:
        cur.execute(f"DELETE FROM {tbl}")
    print("[OK] Data lama dibersihkan.")

    cur.execute("SELECT id FROM periode WHERE aktif=1 LIMIT 1")
    row = cur.fetchone()
    periode_id = row[0] if row else 1
    cur.execute("SELECT id FROM dosen_pa LIMIT 1")
    row = cur.fetchone()
    dosen_id = row[0] if row else 1

    kategori_list = (['on_track'] * 80 + ['sedang'] * 60 + ['tinggi'] * 60)
    random.shuffle(kategori_list)

    jumlah = 0
    for i, kategori in enumerate(kategori_list, start=1):
        nim = f"MHS{2023}{i:04d}"
        nama = buat_nama(i)
        angkatan = random.choice([2022, 2023, 2024])

        if kategori == 'on_track':
            semester_sekarang = random.randint(5, 8)
        elif kategori == 'sedang':
            semester_sekarang = random.randint(5, 8)
        else:
            semester_sekarang = random.randint(4, 10)

        prodi = random.choice(PRODI_LIST)

        cur.execute("""
            INSERT INTO mahasiswa
                (nim, nama, angkatan, prodi, dosen_pa_id,
                 semester_sekarang, status_aktif, target_sks, target_semester)
            VALUES (%s,%s,%s,%s,%s,%s,1,144,8)
        """, (nim, nama, angkatan, prodi, dosen_id, semester_sekarang))

        progresi = generate_progresi_semester(kategori, semester_sekarang)
        ringkasan = hitung_ringkasan(progresi, kategori)

        for p in progresi:
            cur.execute("""
                INSERT INTO data_semester
                    (nim, semester, sks_diambil, sks_lulus, ips)
                VALUES (%s,%s,%s,%s,%s)
            """, (nim, p['semester'], p['sks_diambil'], p['sks_lulus'], p['ips']))

        if ringkasan:
            cur.execute("""
                INSERT INTO data_akademik
                    (nim, periode_id, kehadiran, nilai_tugas, jumlah_terlambat,
                     ips_sebelumnya, ips_terakhir, sks_progress_ratio)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (nim, periode_id, ringkasan['kehadiran'], ringkasan['nilai_tugas'],
                  ringkasan['terlambat'], ringkasan['ips_sebelumnya'],
                  ringkasan['ips_terakhir'], ringkasan['sks_progress_ratio']))

        jumlah += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"[OK] {jumlah} mahasiswa dibuat - semua dipastikan memicu minimal 1 gejala.")
    print("[DONE] Jalankan: python3 main.py  (atau uvicorn main:app --reload)")


if __name__ == '__main__':
    try:
        seed()
    except pymysql.Error as e:
        print(f"[ERROR] {e}")
