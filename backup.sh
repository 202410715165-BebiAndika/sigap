#!/bin/bash
# ============================================================
# Script backup SIGAP untuk share/submit/upload
# Jalankan: bash ~/sigap/backup.sh
# ============================================================

set -e

# Konfigurasi
PROJECT_DIR="$HOME/sigap"
BACKUP_DIR="$HOME/sigap_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ZIP_FILE="$BACKUP_DIR/sigap_${TIMESTAMP}.zip"

echo "=============================================="
echo "  Backup Aplikasi SIGAP"
echo "=============================================="

# Cek folder proyek
if [ ! -d "$PROJECT_DIR" ]; then
    echo "ERROR: Folder $PROJECT_DIR tidak ditemukan"
    exit 1
fi

# Buat folder backup
mkdir -p "$BACKUP_DIR"

# Buat file .gitignore sementara jika belum ada
if [ ! -f "$PROJECT_DIR/.gitignore" ]; then
    echo "Membuat .gitignore sementara..."
    cat > "$PROJECT_DIR/.gitignore" << 'EOF'
venv/
__pycache__/
*.pyc
.DS_Store
sigap.db
*.log
EOF
fi

# Backup database MySQL (jika tersedia)
echo ""
echo "[1/3] Backup database MySQL..."
DB_BACKUP="$PROJECT_DIR/sigap_db_backup.sql"
if command -v mysqldump &> /dev/null; then
    mysqldump -u root sigap > "$DB_BACKUP" 2>/dev/null && \
        echo "  Database backup: $DB_BACKUP" || \
        echo "  WARNING: MySQL tidak aktif atau database sigap tidak ada - skip"
else
    echo "  mysqldump tidak tersedia - skip (backup manual via phpMyAdmin)"
fi

# Buat README jika belum ada
if [ ! -f "$PROJECT_DIR/README.md" ]; then
    echo ""
    echo "[2/3] Membuat README.md otomatis..."
    cat > "$PROJECT_DIR/README.md" << 'EOF'
# SIGAP - Sistem Intelijen Gejala Akademik

Sistem peringatan dini mahasiswa berisiko tidak lulus tepat waktu berbasis
mesin Certainty Factor (CF) Shortliffe & Buchanan (1975).

## Tech Stack
- Python 3.12+ / FastAPI
- MySQL (XAMPP)
- Jinja2 templates + Bootstrap 5
- Chart.js untuk visualisasi
- pytest untuk testing

## Cara Menjalankan
1. Install XAMPP, start MySQL di port 3306
2. Buat virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Inisialisasi database:
   ```bash
   python3 database.py
   ```
5. Generate data mahasiswa (200 mahasiswa):
   ```bash
   python3 seed.py
   ```
6. Jalankan server:
   ```bash
   python3 main.py
   ```
7. Buka browser: http://127.0.0.1:8000

## Konfigurasi Database
- Host: localhost
- Port: 3306
- User: root
- Password: (kosong - default XAMPP)
- Database: sigap

## Struktur Folder
```
sigap/
├── main.py              # Aplikasi FastAPI (endpoint)
├── database.py          # Skema MySQL + seed awal
├── seed.py              # Generator 200 mahasiswa + data semester
├── services/
│   └── inference/
│       └── cf_engine.py # Mesin CF + fungsi prediksi
├── templates/           # Jinja2 HTML templates
│   ├── dashboard.html
│   ├── detail.html
│   └── input.html
├── tests/
│   └── test_cf_engine.py  # 10 tes pytest
└── requirements.txt
```

## Validasi Mesin CF
Untuk input {G1: 0.48, G3: 0.24, G4: 0.385}:
- CF gabungan: 0.757 (kategori Tinggi)
- Kontribusi G1: 0.224, G4: 0.152, G3: 0.077

Jalankan tes: `pytest tests/ -v`

## Aktor
- **Dosen PA**: akses penuh (9 use case)
- **Mahasiswa**: read-only (3 use case)
EOF
    echo "  README.md dibuat"
fi

# Zip folder (exclude venv, __pycache__, .DS_Store, dll)
echo ""
echo "[3/3] Membuat file ZIP..."
cd "$HOME"
zip -r "$ZIP_FILE" sigap \
    -x "sigap/venv/*" \
    -x "sigap/__pycache__/*" \
    -x "*/__pycache__/*" \
    -x "*.pyc" \
    -x "sigap/.DS_Store" \
    -x "sigap/**/*.DS_Store" \
    -x "sigap/sigap.db" \
    -x "sigap/*.log" \
    -q

echo ""
echo "=============================================="
echo "  BACKUP SELESAI"
echo "=============================================="
echo ""
echo "File backup: $ZIP_FILE"
echo "Ukuran: $(du -h "$ZIP_FILE" | cut -f1)"
echo ""
echo "Isi ZIP:"
unzip -l "$ZIP_FILE" | tail -n +4 | head -n -2 | awk '{printf "  %-50s %s\n", $4, $1}' | head -30
echo ""
echo "Cara pakai:"
echo "  - Upload ke chat AI: drag-drop file ZIP ke kotak chat"
echo "  - Submit ke kampus: kirim file ZIP via email/LMS"
echo "  - Upload ke GitHub: unzip di folder baru lalu git init"
echo ""
