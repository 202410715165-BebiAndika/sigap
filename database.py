import json
import os
import pymysql

DB_CONFIG = {
    'host': os.getenv('SIGAP_DB_HOST', 'localhost'),
    'user': os.getenv('SIGAP_DB_USER', 'root'),
    'password': os.getenv('SIGAP_DB_PASSWORD', ''),
    'port': int(os.getenv('SIGAP_DB_PORT', '3306')),
    'connect_timeout': 5,
    'charset': 'utf8mb4',
}
DB_NAME = os.getenv('SIGAP_DB_NAME', 'sigap')
if not DB_NAME.replace('_', '').isalnum():
    raise ValueError('Nama database hanya boleh berisi huruf, angka, dan underscore.')


def get_connection(database=True):
    cfg = DB_CONFIG.copy()
    if database:
        cfg['database'] = DB_NAME
    return pymysql.connect(**cfg)


def init_db():
    conn = get_connection(database=False)
    cur = conn.cursor()
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS {DB_NAME} "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"[OK] Database '{DB_NAME}' siap.")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            peran VARCHAR(20) NOT NULL,
            dibuat_pada TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dosen_pa (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nip VARCHAR(20) UNIQUE NOT NULL,
            nama VARCHAR(100) NOT NULL,
            email VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS mahasiswa (
            nim VARCHAR(20) PRIMARY KEY,
            nama VARCHAR(100) NOT NULL,
            angkatan INT NOT NULL,
            prodi VARCHAR(50) NOT NULL,
            dosen_pa_id INT,
            semester_sekarang INT NOT NULL DEFAULT 1,
            status_aktif TINYINT(1) NOT NULL DEFAULT 1,
            target_sks INT NOT NULL DEFAULT 144,
            target_semester INT NOT NULL DEFAULT 8,
            FOREIGN KEY (dosen_pa_id) REFERENCES dosen_pa(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS periode (
            id INT AUTO_INCREMENT PRIMARY KEY,
            kode VARCHAR(20) UNIQUE NOT NULL,
            nama VARCHAR(50) NOT NULL,
            aktif TINYINT(1) NOT NULL DEFAULT 0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS data_akademik (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nim VARCHAR(20) NOT NULL,
            periode_id INT,
            kehadiran FLOAT NOT NULL,
            nilai_tugas FLOAT NOT NULL,
            jumlah_terlambat INT NOT NULL,
            ips_sebelumnya FLOAT NOT NULL,
            ips_terakhir FLOAT NOT NULL,
            ips_drop FLOAT GENERATED ALWAYS AS (ips_sebelumnya - ips_terakhir) STORED,
            sks_progress_ratio FLOAT NOT NULL DEFAULT 1.0,
            dibuat_pada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_nim_periode (nim, periode_id),
            FOREIGN KEY (nim) REFERENCES mahasiswa(nim),
            FOREIGN KEY (periode_id) REFERENCES periode(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS data_semester (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nim VARCHAR(20) NOT NULL,
            semester INT NOT NULL,
            sks_diambil INT NOT NULL,
            sks_lulus INT NOT NULL,
            ips FLOAT NOT NULL,
            UNIQUE KEY uq_nim_sem (nim, semester),
            FOREIGN KEY (nim) REFERENCES mahasiswa(nim)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS aturan (
            id INT AUTO_INCREMENT PRIMARY KEY,
            kode VARCHAR(10) UNIQUE NOT NULL,
            deskripsi TEXT NOT NULL,
            indikator VARCHAR(50) NOT NULL,
            kondisi VARCHAR(20) NOT NULL,
            ambang FLOAT NOT NULL,
            metrik VARCHAR(50) NOT NULL,
            cf_pakar FLOAT NOT NULL,
            cf_user_mapping TEXT NOT NULL,
            aktif TINYINT(1) NOT NULL DEFAULT 1
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hasil_risiko (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nim VARCHAR(20) NOT NULL,
            periode_id INT,
            cf_gabungan FLOAT NOT NULL,
            kategori VARCHAR(20) NOT NULL,
            status_prediksi VARCHAR(100),
            dihitung_pada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_nim_periode (nim, periode_id),
            FOREIGN KEY (nim) REFERENCES mahasiswa(nim),
            FOREIGN KEY (periode_id) REFERENCES periode(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hasil_gejala (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nim VARCHAR(20) NOT NULL,
            periode_id INT,
            kode_aturan VARCHAR(10) NOT NULL,
            cf_user FLOAT NOT NULL,
            cf_gejala FLOAT NOT NULL,
            kontribusi FLOAT NOT NULL,
            FOREIGN KEY (nim) REFERENCES mahasiswa(nim)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tindak_lanjut (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nim VARCHAR(20) NOT NULL,
            catatan TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            dibuat_pada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (nim) REFERENCES mahasiswa(nim)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            aksi VARCHAR(50) NOT NULL,
            detail TEXT,
            waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("[OK] Semua tabel dibuat.")


def seed_initial():
    conn = get_connection()
    cur = conn.cursor()


    cur.execute(
        "INSERT IGNORE INTO dosen_pa (nip, nama, email) VALUES (%s,%s,%s)",
        ('198001012005011001', 'Dr. Herlawanti, M.Kom', 'herlawanti@kampus.ac.id')
    )
    cur.execute("SELECT id FROM dosen_pa WHERE nip=%s", ('198001012005011001',))
    dosen_id = cur.fetchone()[0]

    cur.execute(
        "INSERT IGNORE INTO periode (kode, nama, aktif) VALUES (%s,%s,%s)",
        ('2026-Genap', 'Semester Genap 2025/2026', 1)
    )
    cur.execute("SELECT id FROM periode WHERE kode=%s", ('2026-Genap',))
    periode_id = cur.fetchone()[0]

    aturan_list = [
        ('G1', 'Kehadiran kuliah di bawah 75 persen',
         'kehadiran', '<', 75.0, 'kehadiran', 0.60,
         json.dumps([
             {"min": 70, "max": 74.99, "cf_user": 0.5},
             {"min": 60, "max": 69.99, "cf_user": 0.8},
             {"min": 0, "max": 59.99, "cf_user": 1.0},
         ])),
        ('G3', 'Keterlambatan mengumpulkan tugas >= 3 kali',
         'terlambat', '>=', 3.0, 'jumlah_terlambat', 0.40,
         json.dumps([
             {"min": 3, "max": 4, "cf_user": 0.6},
             {"min": 5, "max": 6, "cf_user": 0.8},
             {"min": 7, "max": 99, "cf_user": 1.0},
         ])),
        ('G4', 'IPS terakhir turun >= 0.5 dari semester sebelumnya',
         'ips_drop', '>=', 0.5, 'ips_drop', 0.55,
         json.dumps([
             {"min": 0.5, "max": 0.79, "cf_user": 0.5},
             {"min": 0.8, "max": 1.19, "cf_user": 0.8},
             {"min": 1.2, "max": 4.0, "cf_user": 1.0},
         ])),
        ('G6', 'Progress SKS di bawah target timeline kelulusan',
         'sks_progress_ratio', '<', 0.85, 'sks_progress_ratio', 0.50,
         json.dumps([
             {"min": 0.70, "max": 0.849, "cf_user": 0.5},
             {"min": 0.50, "max": 0.699, "cf_user": 0.8},
             {"min": 0.00, "max": 0.499, "cf_user": 1.0},
         ])),
    ]

    for a in aturan_list:
        cur.execute("""
            INSERT INTO aturan
                (kode, deskripsi, indikator, kondisi, ambang, metrik, cf_pakar, cf_user_mapping, aktif)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,1)
            ON DUPLICATE KEY UPDATE deskripsi=VALUES(deskripsi)
        """, a)

    conn.commit()
    cur.close()
    conn.close()
    print(f"[OK] Seed awal: dosen_id={dosen_id}, periode_id={periode_id}, {len(aturan_list)} aturan (G1,G3,G4,G6).")


if __name__ == '__main__':
    try:
        init_db()
        seed_initial()
        print("\n[DONE] Database SIGAP (MySQL) siap digunakan.")
        print("Langkah berikutnya:")
        print("  1) pip install -r requirements.txt")
        print("  2) python3 seed.py")
        print("  3) python3 main.py   (atau uvicorn main:app --reload)")
    except pymysql.Error as e:
        print(f"[ERROR] MySQL: {e}")
        print("Pastikan XAMPP MySQL sudah dijalankan (XAMPP Control Panel -> Start MySQL).")
