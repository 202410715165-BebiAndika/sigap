# SIGAP — versi perbaikan

Sistem peringatan dini risiko akademik berbasis Certainty Factor, FastAPI, MySQL, Jinja2, Bootstrap, dan Chart.js.

## Memakai database SIGAP yang sudah ada

Buka terminal dari folder versi perbaikan ini. Gunakan Python dari virtual environment SIGAP yang lama, atau buat virtual environment baru dan jalankan `pip install -r requirements.txt`.

```bash
/Users/bebiandika/sigap/venv/bin/python migrate.py
/Users/bebiandika/sigap/venv/bin/python auth.py admin --peran admin
/Users/bebiandika/sigap/venv/bin/python main.py
```

1. `migrate.py` menambahkan kolom periode pada hasil gejala. Tidak menghapus data mahasiswa. Dapat dijalankan ulang.
2. `auth.py` meminta password baru minimal 12 karakter melalui terminal. Akun lama dengan password plaintext, termasuk `admin123`, tidak diterima. Tidak ada password default.
3. Buka http://127.0.0.1:8000 dan masuk melalui dialog login browser.
4. Klik **Jalankan Mesin CF** untuk mengganti hasil perhitungan periode aktif dengan hasil yang benar. Gejala lama yang belum memiliki periode tetap disimpan tetapi tidak ditampilkan.

**Jangan menjalankan `seed.py` pada database asli:** skrip tersebut menghapus data mahasiswa dan menggantinya dengan 200 data contoh. Skrip ini hanya untuk database percobaan.

Jika port 8000 sedang dipakai aplikasi lama, hentikan server lama sebelum menjalankan versi ini.

## Instalasi database baru

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python database.py
python migrate.py
# Opsional, hanya untuk database contoh baru:
python seed.py
python auth.py admin --peran admin
python main.py
```

## Akun dan akses

```bash
python auth.py dosen1 --peran dosen_pa
python auth.py MHS20230001 --peran mahasiswa
```

Admin dan dosen PA dapat melihat semua mahasiswa, mengisi data, dan menjalankan mesin CF. Username mahasiswa harus sama dengan NIM yang sudah terdaftar; mahasiswa hanya dapat melihat detailnya sendiri. Perintah `auth.py` juga dapat mengganti password atau peran akun yang sudah ada. Akses dosen belum dipisahkan berdasarkan dosen pembimbing.

Login menggunakan HTTP Basic. Server bawaan hanya mendengarkan di 127.0.0.1; jika dipublikasikan, gunakan HTTPS. Dokumentasi API interaktif FastAPI tetap tersedia; endpoint data memerlukan autentikasi.

## Konfigurasi database

Variabel lingkungan opsional:

- `SIGAP_DB_HOST`: default `localhost`
- `SIGAP_DB_PORT`: default `3306`
- `SIGAP_DB_USER`: default `root`
- `SIGAP_DB_PASSWORD`: default kosong
- `SIGAP_DB_NAME`: default `sigap`

Pastikan tepat satu baris `periode` memiliki `aktif=1`. Aplikasi mengembalikan 409 bila belum ada atau ada beberapa periode aktif.

## Perbaikan

- G3 membaca `jumlah_terlambat`; aturan lama bermetrik `terlambat` tetap kompatibel.
- `cf_user` disimpan langsung dari tier masing-masing aturan.
- Progres SKS input memakai total SKS semester sebelumnya ditambah SKS semester yang diinput; pengeditan semester yang sama tidak menghitungnya dua kali.
- Data akademik, hasil risiko, dan gejala menggunakan periode aktif yang sama.
- Data semester setelah semester sekarang tidak ikut total dan prediksi.
- Tier CF tidak lagi memiliki celah desimal di antara batas; toleransi lima desimal mengatasi noise FLOAT database.
- Validasi server untuk NIM, panjang teks, semester, IPS, kehadiran, SKS, dan keterlambatan; menolak NaN/infinity dan SKS lulus melebihi SKS diambil.
- Input dan hasil mesin disimpan dalam satu transaksi; kegagalan membatalkan perubahan.
- Login, password PBKDF2, akses peran, akses mahasiswa terbatas pada dirinya sendiri, serta penolakan permintaan tulis lintas situs pada browser.
- Menjalankan mesin memakai POST. Membuka dashboard tidak lagi mengubah database.
- Lokasi template ditentukan dari lokasi `main.py`, bukan direktori terminal.

Model prediksi tetap memakai asumsi SKS semester sekarang sudah merupakan hasil akhir semester. Prediksi berbasis SKS bukan bukti kelulusan administratif atau penyelesaian skripsi. Data semester tidak memiliki versi historis per periode; perubahan riwayat semester memengaruhi prediksi berbasis riwayat terkini.

## Pengujian

Dari folder ini:

```bash
python -m pytest tests/ -q
```

Tes regresi mencakup rumus CF, G3, bobot masing-masing gejala, batas tier, periode, SKS kumulatif, rollback, validasi form melalui ASGI, autentikasi, dan pembatasan akses. Tes tidak membutuhkan atau menulis ke database MySQL asli.

Versi ini sudah diterapkan pada aplikasi asli dan diuji dengan MySQL. Migrasi sudah dijalankan, hasil periode aktif dihitung ulang, dan 37 tes regresi lulus. Pengujian pada salinan database juga mencakup penyimpanan form; seluruh 200 mahasiswa asli tetap utuh.
