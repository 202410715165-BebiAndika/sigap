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
