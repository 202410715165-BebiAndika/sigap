# Data simulasi SIGAP

Sumber: fungsi generator pada `seed.py` aplikasi SIGAP; seed acak 42. Tidak membaca database mahasiswa asli. Dataset ini berisi data sintetis untuk demonstrasi dan tidak boleh diklaim sebagai hasil pengumpulan data mahasiswa atau label penilaian dosen PA.

## Ringkasan mahasiswa

`dataset_mahasiswa.csv` dan sheet `Dataset` pada Excel memiliki kolom yang sama:

| Kolom | Definisi |
|---|---|
| nim | Identitas contoh yang unik, disimpan sebagai teks. |
| nama | Nama simulasi. |
| prodi | Program studi simulasi. |
| angkatan | Tahun angkatan simulasi. |
| semester_sekarang | Semester terakhir dengan hasil akademik yang sudah tercatat. |
| kehadiran | Persentase kehadiran 0–100. |
| nilai_tugas | Nilai rata-rata tugas 0–100; belum menjadi aturan G2. |
| jumlah_terlambat | Jumlah keterlambatan tugas, bilangan bulat nonnegatif. |
| ips_sebelumnya | IPS semester sebelumnya, 0–4. |
| ips_terakhir | IPS semester terakhir, 0–4. |
| total_sks_lulus | Jumlah SKS kumulatif, bukan SKS satu semester. |
| target_sks | Target 144 SKS pada prototipe. |
| target_semester | Target 8 semester pada prototipe. |

Riwayat `data_semester.csv` memiliki kunci `(nim, semester)` dan kolom `sks_diambil`, `sks_lulus`, `ips`. Total `sks_lulus` per NIM sesuai dengan `total_sks_lulus` pada ringkasan.

Notebook menghitung ulang `ips_drop = ips_sebelumnya - ips_terakhir` dan `sks_progress_ratio = total_sks_lulus / (semester_sekarang * 18)`.

Basis aturan tersimpan di `aturan_cf.json` dan sheet `Aturan`. Batas tier, CF pakar, dan ambang kategori merupakan parameter prototipe yang belum divalidasi dengan penilaian pakar nyata.

`hasil_risiko_contoh.csv` adalah keluaran perhitungan pada dataset simulasi; kolom `kategori` bukan label ground truth. Jangan memakainya sebagai bukti akurasi prediksi akademik.
