"""HTTP Basic authentication. Mahasiswa usernames must match their NIM."""
import hashlib
import hmac
import secrets
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import pymysql.cursors
from database import get_connection

security = HTTPBasic()


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
    return f'pbkdf2_sha256$600000${salt}${digest}'


def verify_password(password, encoded):
    try:
        algorithm, iterations, salt, expected = encoded.split('$')
        if algorithm != 'pbkdf2_sha256' or not 100000 <= int(iterations) <= 1000000:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, AttributeError):
        return False


def require_user(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    db = get_connection()
    try:
        with db.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute('SELECT username, password_hash, peran FROM users WHERE username=%s', (credentials.username,))
            user = cur.fetchone()
    finally:
        db.close()
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(401, 'Username atau password salah.', headers={'WWW-Authenticate': 'Basic'})
    if user['peran'] not in ('admin', 'dosen_pa', 'mahasiswa'):
        raise HTTPException(403, 'Peran tidak diizinkan.')
    request.state.sigap_role = user['peran']
    return user


def require_pa(user=Depends(require_user)):
    if user['peran'] not in ('admin', 'dosen_pa'):
        raise HTTPException(403, 'Hanya dosen PA atau admin yang dapat mengubah data.')
    return user


if __name__ == '__main__':
    import argparse
    import getpass
    parser = argparse.ArgumentParser(description='Buat akun atau ganti password SIGAP.')
    parser.add_argument('username')
    parser.add_argument('--peran', required=True, choices=['admin', 'dosen_pa', 'mahasiswa'])
    args = parser.parse_args()
    password = getpass.getpass('Password baru (minimal 12 karakter): ')
    if len(password) < 12 or password != getpass.getpass('Ulangi password: '):
        parser.error('Password minimal 12 karakter dan konfirmasi harus sama.')
    db = get_connection()
    try:
        with db.cursor() as cur:
            if args.peran == 'mahasiswa':
                cur.execute('SELECT nim FROM mahasiswa WHERE nim=%s', (args.username,))
                if not cur.fetchone():
                    parser.error('Username mahasiswa harus merupakan NIM yang terdaftar.')
            cur.execute('''INSERT INTO users (username,password_hash,peran) VALUES (%s,%s,%s)
                           ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash),peran=VALUES(peran)''',
                        (args.username, hash_password(password), args.peran))
        db.commit()
    finally:
        db.close()
    print('Akun berhasil disimpan.')
