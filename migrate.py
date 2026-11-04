"""Add period ownership without resetting student records or legacy evidence."""
from database import get_connection


def migrate():
    db = get_connection()
    try:
        with db.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM hasil_gejala LIKE 'periode_id'")
            if not cur.fetchone():
                cur.execute('ALTER TABLE hasil_gejala ADD COLUMN periode_id INT NULL, ADD INDEX idx_gejala_periode (nim, periode_id), ADD CONSTRAINT fk_gejala_periode FOREIGN KEY (periode_id) REFERENCES periode(id)')
        db.commit()
    finally:
        db.close()


if __name__ == '__main__':
    migrate()
    print('Migrasi selesai. Jalankan Mesin CF untuk mengisi ulang hasil periode aktif.')
