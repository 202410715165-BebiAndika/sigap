# SIGAP — Sistem Inteligen Gejala Akademik Prediktif

Prototipe sistem pakar berbasis Certainty Factor untuk membantu pemantauan risiko akademik mahasiswa.

**Kelompok 8, F5A1**

- Bebi Andika — 202410715165: pembuatan aplikasi dan laporan, kontribusi 50%.
- Muhammad Nur Aufa — 202410715011: penyusunan dan finalisasi laporan, kontribusi 50%.

## Menjalankan notebook di Google Colab

1. Buka https://colab.research.google.com/.
2. Pilih **File → Upload notebook**, lalu pilih `SIGAP_Colab.ipynb`. Alternatif: **File → Open notebook → GitHub** dan masukkan tautan repositori ini.
3. Pilih **Runtime → Run all**. Notebook membuat 200 data simulasi secara otomatis dan tidak memerlukan MySQL.
4. Lihat data, basis aturan, skor risiko, gejala dominan, prediksi SKS, grafik, dan hasil pemeriksaan.
5. Untuk menyimpan hasil, buka folder `hasil_sigap` pada panel Files, klik kanan `hasil_sigap.zip`, lalu Download.
6. Simpan salinan notebook di Drive atau unduh `.ipynb` setelah semua sel selesai dijalankan.

Setelah repositori dibuat, format tautan langsung Colab adalah:

```text
https://colab.research.google.com/github/USERNAME/sigap/blob/main/SIGAP_Colab.ipynb
```

Ganti `USERNAME`, nama repo `sigap`, dan branch `main` jika berbeda. Tautan ini bukan URL repo yang sudah dibuat otomatis.

## Dataset dan Excel

Semua data yang disertakan adalah **data simulasi**, bukan data mahasiswa nyata. Generator mengikuti fungsi `seed.py` dengan random seed 42. Data dibentuk untuk demonstrasi; kelompok generator bukan label pakar dan bukan label kebenaran untuk mengukur akurasi.

- `data/dataset_mahasiswa.csv`: ringkasan 200 mahasiswa; satu baris per NIM.
- `data/data_semester.csv`: riwayat SKS dan IPS per mahasiswa per semester.
- `data/dataset_sigap.xlsx`: sheet Dataset, Semester, Aturan, dan Kamus.
- `data/aturan_cf.json`: empat aturan prototipe G1, G3, G4, G6 beserta tier CF user.
- `data/hasil_risiko_contoh.csv`: hasil perhitungan notebook pada dataset simulasi bawaan.
- `data/README.md`: definisi kolom dan batas penggunaan data.

Untuk memakai CSV/Excel sendiri di Colab, unggah file melalui panel Files, lalu ubah `DATASET_PATH` pada bagian 5. Excel dibaca dari sheet `Dataset`. Biarkan variabel kosong jika hanya mencoba dataset simulasi bawaan.

## Menjalankan aplikasi web secara lokal

Siapkan MySQL/XAMPP dan Python, kemudian dari folder repositori:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python database.py
python migrate.py
python auth.py admin --peran admin
python main.py
```

Buka http://127.0.0.1:8000. Pada Windows, aktivasi virtual environment menggunakan `venv\Scripts\activate`.

Untuk database demo yang baru dan kosong, `python seed.py` dapat dijalankan setelah inisialisasi. **seed.py menghapus data mahasiswa lama**; jangan jalankan pada database yang ingin dipertahankan. File CSV/Excel pada repo dipakai oleh notebook; aplikasi web saat ini tetap membaca MySQL.

Konfigurasi MySQL dapat diberikan melalui `SIGAP_DB_HOST`, `SIGAP_DB_PORT`, `SIGAP_DB_USER`, `SIGAP_DB_PASSWORD`, dan `SIGAP_DB_NAME`. Password akun dimasukkan saat membuat akun, bukan disimpan di repositori.

## Menjalankan demonstrasi Python tanpa MySQL

```bash
pip install pandas
python demo_sigap.py
```

File `demo_sigap.py` berisi sel kode notebook dalam bentuk skrip. Untuk membaca Excel, install `openpyxl` juga.

Pengujian aplikasi web:

```bash
python -m pytest tests/ -q
```

## Cakupan dan validasi

Notebook memiliki 14 pemeriksaan yang telah dijalankan berurutan secara lokal. Eksekusi pada akun Google Colab perlu dilakukan setelah notebook diunggah. Aplikasi web memiliki 37 tes regresi yang terpisah.

CF merupakan skor keyakinan berbasis aturan. Kategori hasil sistem bukan label pakar, sehingga accuracy, precision, recall, dan kappa belum dapat diklaim dari dataset ini. Prediksi kelulusan hanya memproyeksikan progres SKS; tidak memeriksa skripsi dan persyaratan administratif.

Perhitungan desimal pada notebook dinormalisasi agar konsisten ketika data dibaca dari CSV/Excel; kasus tepat pada batas tier dapat berbeda dengan FLOAT mentah database MySQL. Contoh manual proposal dengan CF G4 0,385 dipakai untuk validasi rumus, sedangkan tier otomatis aplikasi pada penurunan IPS 0,70 memakai CF user 0,50.

Notebook ini berfokus pada mesin analisis. Dashboard, autentikasi, dan database dijalankan melalui aplikasi FastAPI. Integrasi SIA/LMS, G2/G5, notifikasi, serta penjadwalan otomatis masih merupakan rencana pengembangan.

Kode, notebook, dataset, serta panduan pengumpulan disiapkan dengan bantuan AI. Periksa seluruh hasil dan sesuaikan pengungkapan penggunaan AI pada Lampiran F dengan berkas yang benar-benar dikumpulkan.

## Panduan resmi

- GitHub: https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository
- Mengunggah file: https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository
- Google Colab: https://research.google.com/colaboratory/faq.html
