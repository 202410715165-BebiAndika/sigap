import json
from pathlib import Path
from html import escape
from fastapi import FastAPI, Depends, Request, Form, Query, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pymysql
import pymysql.cursors

from database import get_connection
from auth import require_user, require_pa
from services.inference.cf_engine import (
    nilai, kontribusi, klasifikasi_risiko, prediksi_lulus_tepat_waktu
)

app = FastAPI(title="SIGAP - Deteksi Dini Ketepatan Waktu Lulus", dependencies=[Depends(require_user)])
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def get_db():
    conn = get_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def active_period(cur):
    cur.execute("SELECT id FROM periode WHERE aktif=1 ORDER BY id")
    periods = cur.fetchall()
    if len(periods) != 1:
        raise HTTPException(409, "Harus ada tepat satu periode aktif.")
    return periods[0]['id']


def run_cf_engine(db, nim_filter=None, commit=True):
    cur = db.cursor(pymysql.cursors.DictCursor)
    try:
        periode_id = active_period(cur)
        cur.execute("SELECT * FROM aturan WHERE aktif=1 ORDER BY id")
        aturan_list = cur.fetchall()
        if nim_filter:
            cur.execute("SELECT * FROM mahasiswa WHERE nim=%s", (nim_filter,))
        else:
            cur.execute("SELECT * FROM mahasiswa")
        mhs_list = cur.fetchall()
        for mhs in mhs_list:
            nim = mhs['nim']
            cur.execute("SELECT * FROM data_akademik WHERE nim=%s AND periode_id=%s", (nim, periode_id))
            da = cur.fetchone()
            cur.execute("DELETE FROM hasil_risiko WHERE nim=%s AND periode_id=%s", (nim, periode_id))
            cur.execute("DELETE FROM hasil_gejala WHERE nim=%s AND periode_id=%s", (nim, periode_id))
            if not da:
                continue
            gejala = {}
            users = {}
            for aturan in aturan_list:
                metrik = {'terlambat': 'jumlah_terlambat'}.get(aturan['metrik'], aturan['metrik'])
                value = da.get(metrik)
                if value is None:
                    continue
                operator = aturan['kondisi']
                if operator not in ('<', '>='):
                    raise HTTPException(409, "Operator aturan tidak didukung.")
                if not (value < aturan['ambang'] if operator == '<' else value >= aturan['ambang']):
                    continue
                # Tier memakai batas bawah; batas atas tetap ditangani kondisi aturan.
                # Pembulatan menyerap noise FLOAT MySQL pada batas seperti 0.8.
                value = round(value, 5)
                mapping = sorted(json.loads(aturan['cf_user_mapping']), key=lambda t: t['min'], reverse=True)
                tier = next((t for t in mapping if value >= t['min']), None)
                if tier is None:
                    continue
                user = tier['cf_user']
                if not 0 <= user <= 1 or not 0 <= aturan['cf_pakar'] <= 1:
                    raise HTTPException(409, "Bobot CF harus di antara 0 dan 1.")
                users[aturan['kode']] = user
                gejala[aturan['kode']] = aturan['cf_pakar'] * user
            skor = nilai(gejala)
            kontrib = kontribusi(gejala)
            cur.execute("SELECT COALESCE(SUM(sks_lulus),0) AS total FROM data_semester WHERE nim=%s AND semester<=%s", (nim, mhs['semester_sekarang']))
            total = cur.fetchone()['total']
            prediksi = prediksi_lulus_tepat_waktu(total, mhs['semester_sekarang'], mhs['target_sks'], mhs['target_semester'])
            cur.execute("""INSERT INTO hasil_risiko (nim, periode_id, cf_gabungan, kategori, status_prediksi)
                           VALUES (%s,%s,%s,%s,%s)""", (nim, periode_id, skor, klasifikasi_risiko(skor), prediksi['status']))
            for kode, cf in gejala.items():
                cur.execute("""INSERT INTO hasil_gejala (nim, periode_id, kode_aturan, cf_user, cf_gejala, kontribusi)
                               VALUES (%s,%s,%s,%s,%s,%s)""", (nim, periode_id, kode, users[kode], cf, kontrib[kode]))
        if commit:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()


@app.middleware("http")
async def reject_cross_site_writes(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        from urllib.parse import urlsplit
        from fastapi.responses import JSONResponse
        origin = request.headers.get('origin')
        if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and urlsplit(origin).netloc != request.headers.get('host')):
            return JSONResponse({'detail': 'Permintaan lintas situs ditolak.'}, status_code=403)
    return await call_next(request)


# ---------- Helper: mapping filter prediksi ke SQL WHERE ----------
PREDIKSI_PATTERNS = {
    'OnTrack': [
        "h.status_prediksi LIKE '%%On Track%%'",
        "h.status_prediksi = 'Lulus Tepat Waktu'",
        "h.status_prediksi LIKE '%%Memenuhi%%'",
    ],
    'Berisiko': [
        "h.status_prediksi LIKE '%%Berisiko (Masih%%'",
        "h.status_prediksi LIKE '%%Lulus Terlambat%%'",
    ],
    'BerisikoTinggi': [
        "h.status_prediksi LIKE '%%Berisiko Tinggi%%'",
        "h.status_prediksi = 'Tidak Lulus Tepat Waktu'",
    ],
}


@app.get("/")
def dashboard(request: Request,
               kategori: str = Query(default="Semua"),
               prediksi: str = Query(default="Semua"),
               db=Depends(get_db), user=Depends(require_user)):
    if user['peran'] == 'mahasiswa':
        return RedirectResponse(url=f"/mahasiswa/{user['username']}", status_code=303)
    cur = db.cursor(pymysql.cursors.DictCursor)
    active_period(cur)
    cur.execute("""
        SELECT kategori, COUNT(*) AS jml FROM hasil_risiko
        WHERE periode_id=(SELECT id FROM periode WHERE aktif=1 LIMIT 1)
        GROUP BY kategori
    """)
    rows = cur.fetchall()
    statistik = {'total': 0, 'tinggi': 0, 'sedang': 0, 'rendah': 0}
    for r in rows:
        statistik[r['kategori'].lower()] = r['jml']
        statistik['total'] += r['jml']

    cur.execute("""
        SELECT status_prediksi, COUNT(*) AS jml FROM hasil_risiko
        WHERE periode_id=(SELECT id FROM periode WHERE aktif=1 LIMIT 1)
        GROUP BY status_prediksi
    """)
    prediksi_rows = cur.fetchall()
    statistik_prediksi = {'on_track': 0, 'berisiko': 0, 'tinggi': 0}
    for r in prediksi_rows:
        s = (r['status_prediksi'] or '').lower()
        if 'tidak lulus' in s or 'berisiko tinggi' in s:
            statistik_prediksi['tinggi'] += r['jml']
        elif 'lulus terlambat' in s or 'berisiko (masih' in s:
            statistik_prediksi['berisiko'] += r['jml']
        elif 'on track' in s or 'memenuhi' in s or s == 'lulus tepat waktu':
            statistik_prediksi['on_track'] += r['jml']

    # Filter gabungan (kategori + prediksi)
    where_clauses = []
    params = []
    if kategori != "Semua":
        where_clauses.append("h.kategori=%s")
        params.append(kategori)
    if prediksi != "Semua" and prediksi in PREDIKSI_PATTERNS:
        patterns = PREDIKSI_PATTERNS[prediksi]
        where_clauses.append("(" + " OR ".join(patterns) + ")")

    base_select = """
        SELECT m.nim, m.nama, m.prodi, m.angkatan, m.semester_sekarang,
               h.cf_gabungan, h.kategori, h.status_prediksi,
               (SELECT SUM(sks_lulus) FROM data_semester WHERE nim=m.nim AND semester<=m.semester_sekarang) AS total_sks
        FROM mahasiswa m
    """
    if where_clauses:
        sql = base_select + """
            JOIN hasil_risiko h ON h.nim=m.nim
                AND h.periode_id=(SELECT id FROM periode WHERE aktif=1 LIMIT 1)
            WHERE """ + " AND ".join(where_clauses) + """
            ORDER BY h.cf_gabungan DESC, m.nim
        """
        cur.execute(sql, params)
    else:
        sql = base_select + """
            LEFT JOIN hasil_risiko h ON h.nim=m.nim
                AND h.periode_id=(SELECT id FROM periode WHERE aktif=1 LIMIT 1)
            ORDER BY h.cf_gabungan DESC, m.nim
        """
        cur.execute(sql)
    mhs_list = cur.fetchall()
    cur.close()

    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request, "statistik": statistik,
        "statistik_prediksi": statistik_prediksi,
        "mahasiswa": mhs_list,
        "filter_aktif": kategori, "filter_prediksi": prediksi,
    })


@app.post("/run-engine", dependencies=[Depends(require_pa)])
def run_engine(db=Depends(get_db)):
    run_cf_engine(db)
    return RedirectResponse(url="/", status_code=303)


@app.get("/mahasiswa/{nim}")
def detail(request: Request, nim: str, db=Depends(get_db), user=Depends(require_user)):
    if user['peran'] == 'mahasiswa' and user['username'] != nim:
        raise HTTPException(403, "Anda hanya dapat melihat data sendiri.")
    cur = db.cursor(pymysql.cursors.DictCursor)

    cur.execute("SELECT * FROM mahasiswa WHERE nim=%s", (nim,))
    mhs = cur.fetchone()
    if not mhs:
        cur.close()
        return RedirectResponse(url="/", status_code=303)

    periode_id = active_period(cur)
    cur.execute("SELECT * FROM data_akademik WHERE nim=%s AND periode_id=%s", (nim, periode_id))
    da = cur.fetchone()

    cur.execute("SELECT * FROM hasil_risiko WHERE nim=%s AND periode_id=%s", (nim, periode_id))
    hasil = cur.fetchone()

    cur.execute("SELECT * FROM hasil_gejala WHERE nim=%s AND periode_id=%s ORDER BY kontribusi DESC", (nim, periode_id))
    gejala_list = cur.fetchall()

    cur.execute("SELECT kode, deskripsi, indikator FROM aturan")
    aturan_map = {r['kode']: r for r in cur.fetchall()}

    cur.execute("SELECT semester, sks_diambil, sks_lulus, ips FROM data_semester WHERE nim=%s AND semester<=%s ORDER BY semester", (nim, mhs['semester_sekarang']))
    progresi = cur.fetchall()

    total_sks_lulus = sum(p['sks_lulus'] for p in progresi)
    total_sks_diambil = sum(p['sks_diambil'] for p in progresi)

    prediksi = prediksi_lulus_tepat_waktu(
        total_sks_lulus=total_sks_lulus,
        semester_sekarang=mhs['semester_sekarang'],
        target_sks=mhs['target_sks'],
        target_semester=mhs['target_semester'],
    )

    if hasil and hasil['cf_gabungan'] is not None:
        skor = hasil['cf_gabungan']
        kat = hasil['kategori']
        skor_persen = round(skor * 100, 1)
        if kat == "Tinggi":
            ambang = ">= 70 persen"
            level_text = "BERISIKO TINGGI tidak lulus tepat waktu"
            saran = "perlu intervensi segera dalam 1-2 minggu"
        elif kat == "Sedang":
            ambang = "40 - 69.9 persen"
            level_text = "BERISIKO SEDANG tidak lulus tepat waktu"
            saran = "perlu pemantauan ketat dan bimbingan akademik"
        else:
            ambang = "< 40 persen"
            level_text = "BERISIKO RENDAH"
            saran = "cukup pemantauan rutin"

        if gejala_list:
            top = gejala_list[0]
            top_kode = top['kode_aturan']
            top_desc = escape(aturan_map.get(top_kode, {}).get('deskripsi', top_kode))
            top_kode = escape(top_kode)
            top_kontrib = round(top['kontribusi'] * 100, 1)
            penjelasan = (
                f"Skor CF mahasiswa ini <b>{skor_persen}&#37;</b>, "
                f"masuk kategori <b>{kat}</b> (ambang {ambang}). "
                f"Artinya mahasiswa ini {level_text}, {saran}. "
                f"Pemicu dominan adalah <b>{top_kode}</b> ({top_desc}) "
                f"dengan kontribusi <b>{top_kontrib}&#37;</b> terhadap skor total."
            )
            if len(gejala_list) > 1:
                kedua = gejala_list[1]
                kedua_kode = kedua['kode_aturan']
                kedua_desc = escape(aturan_map.get(kedua_kode, {}).get('deskripsi', kedua_kode))
                kedua_kode = escape(kedua_kode)
                kedua_kontrib = round(kedua['kontribusi'] * 100, 1)
                penjelasan += (
                    f" Gejala kedua: <b>{kedua_kode}</b> ({kedua_desc}) "
                    f"dengan kontribusi {kedua_kontrib}&#37;."
                )
        else:
            penjelasan = (
                f"Skor CF mahasiswa ini <b>{skor_persen}&#37;</b>, "
                f"masuk kategori <b>{kat}</b>. "
                f"Tidak ada gejala terdeteksi - mahasiswa {level_text.lower()}, {saran}."
            )
    else:
        skor_persen = 0.0
        kat = "Belum diproses"
        penjelasan = "Mahasiswa belum diproses mesin CF. Klik 'Jalankan Mesin CF' di dashboard."

    rekomendasi_map = {
        'G1': "Panggil mahasiswa untuk bimbingan akademik dan tanyakan hambatan kehadiran. Buat komitmen kehadiran minimal 80 persen.",
        'G3': "Bantu mahasiswa menyusun jadwal pengumpulan tugas. Ajarkan manajemen waktu dan teknik prioritas.",
        'G4': "Analisis mata kuliah yang menurunkan IPS. Sarankan remedial atau bimbingan belajar untuk mata kuliah kritis.",
        'G6': "Evaluasi beban SKS mahasiswa. Jika tertinggal dari timeline 18 SKS/semester, pertimbangkan penambahan SKS di semester pendek atau perbaikan strategi belajar.",
    }
    rekomendasi = []
    for g in gejala_list:
        kode = g['kode_aturan']
        if kode in rekomendasi_map:
            rekomendasi.append({'kode': kode, 'teks': rekomendasi_map[kode]})
    if not rekomendasi:
        rekomendasi.append({'kode': '-', 'teks': "Lanjutkan pemantauan rutin." if hasil else "Jalankan mesin CF sebelum menentukan tindak lanjut."})

    cur.close()

    return templates.TemplateResponse(request, "detail.html", {
        "request": request, "mhs": mhs, "data_akademik": da, "hasil": hasil,
        "gejala": gejala_list, "aturan_map": aturan_map, "progresi": progresi,
        "total_sks_lulus": total_sks_lulus, "total_sks_diambil": total_sks_diambil,
        "prediksi": prediksi, "skor_persen": skor_persen, "kategori": kat,
        "penjelasan": penjelasan, "rekomendasi": rekomendasi,
    })


@app.get("/input-data", dependencies=[Depends(require_pa)])
def input_form(request: Request, db=Depends(get_db)):
    cur = db.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT nim, nama FROM mahasiswa ORDER BY nim LIMIT 50")
    mhs_list = cur.fetchall()
    cur.close()
    return templates.TemplateResponse(request, "input.html", {
        "request": request, "mahasiswa": mhs_list,
    })


@app.post("/input-data", dependencies=[Depends(require_pa)])
def input_submit(request: Request,
                 nim: str = Form(..., pattern=r"^[A-Za-z0-9_-]{1,20}$"), nama: str = Form(..., min_length=1, max_length=100),
                 prodi: str = Form("Teknik Informatika", min_length=1, max_length=50),
                 angkatan: int = Form(2024, ge=1900, le=2100),
                 semester_sekarang: int = Form(1, ge=1, le=14),
                 kehadiran: float = Form(..., ge=0, le=100, allow_inf_nan=False),
                 nilai_tugas: float = Form(80.0, ge=0, le=100, allow_inf_nan=False),
                 terlambat: int = Form(0, ge=0),
                 ips_sebelumnya: float = Form(..., ge=0, le=4, allow_inf_nan=False),
                 ips_terakhir: float = Form(..., ge=0, le=4, allow_inf_nan=False),
                 sks_diambil: int = Form(20, ge=0, le=24),
                 sks_lulus: int = Form(20, ge=0, le=24),
                 db=Depends(get_db)):
    cur = db.cursor(pymysql.cursors.DictCursor)

    if not nama.strip() or not prodi.strip():
        raise HTTPException(422, "Nama dan prodi wajib diisi.")
    if sks_lulus > sks_diambil:
        raise HTTPException(422, "SKS lulus tidak boleh melebihi SKS diambil.")
    cur.execute("SELECT COALESCE(SUM(sks_lulus),0) AS total FROM data_semester WHERE nim=%s AND semester<%s", (nim, semester_sekarang))
    total = cur.fetchone()['total'] + sks_lulus
    sks_progress_ratio = round(total / (semester_sekarang * 18), 3)

    periode_id = active_period(cur)

    cur.execute("SELECT id FROM dosen_pa LIMIT 1")
    dr = cur.fetchone()
    dosen_id = dr['id'] if dr else 1

    cur.execute("""
        INSERT INTO mahasiswa
            (nim, nama, angkatan, prodi, dosen_pa_id, semester_sekarang,
             status_aktif, target_sks, target_semester)
        VALUES (%s,%s,%s,%s,%s,%s,1,144,8)
        ON DUPLICATE KEY UPDATE
            nama=VALUES(nama), angkatan=VALUES(angkatan), prodi=VALUES(prodi),
            semester_sekarang=VALUES(semester_sekarang)
    """, (nim, nama, angkatan, prodi, dosen_id, semester_sekarang))

    cur.execute("DELETE FROM data_akademik WHERE nim=%s AND periode_id=%s", (nim, periode_id))
    cur.execute("""
        INSERT INTO data_akademik
            (nim, periode_id, kehadiran, nilai_tugas, jumlah_terlambat,
             ips_sebelumnya, ips_terakhir, sks_progress_ratio)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (nim, periode_id, kehadiran, nilai_tugas, terlambat,
          ips_sebelumnya, ips_terakhir, sks_progress_ratio))

    cur.execute("DELETE FROM data_semester WHERE nim=%s AND semester=%s",
                (nim, semester_sekarang))
    cur.execute("""
        INSERT INTO data_semester (nim, semester, sks_diambil, sks_lulus, ips)
        VALUES (%s,%s,%s,%s,%s)
    """, (nim, semester_sekarang, sks_diambil, sks_lulus, ips_terakhir))

    run_cf_engine(db, nim_filter=nim, commit=False)
    db.commit()
    cur.close()

    return RedirectResponse(url=f"/mahasiswa/{nim}", status_code=303)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
