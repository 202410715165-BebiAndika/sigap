import asyncio
import json
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException

import main
from auth import hash_password, verify_password, require_pa, require_user
from services.inference.cf_engine import nilai, kontribusi, klasifikasi_risiko, prediksi_lulus_tepat_waktu


class Cursor:
    def __init__(self, db):
        self.db = db
        self.query = ''
        self.params = None
    def execute(self, query, params=None):
        self.query, self.params = query, params
        self.db.calls.append((query, params))
        if self.db.fail and 'INSERT INTO hasil_risiko' in query:
            raise RuntimeError('simulated failure')
    def fetchone(self):
        if 'FROM data_akademik' in self.query:
            return self.db.academic
        if 'SUM(sks_lulus)' in self.query:
            return {'total': self.db.previous_sks}
        if 'FROM dosen_pa' in self.query:
            return {'id': 1}
    def fetchall(self):
        if 'FROM periode' in self.query:
            return self.db.periods
        if 'FROM aturan' in self.query:
            return self.db.rules
        if 'FROM mahasiswa' in self.query:
            return [dict(nim='TEST', semester_sekarang=6, target_sks=144, target_semester=8)]
        return []
    def close(self): pass


def rule(code, metric, condition, threshold, weight, tiers):
    return dict(kode=code, metrik=metric, kondisi=condition, ambang=threshold, cf_pakar=weight,
                cf_user_mapping=json.dumps([dict(min=low, max=high, cf_user=user) for low,high,user in tiers]))


class DB:
    def __init__(self):
        self.calls = []
        self.commits = self.rollbacks = 0
        self.fail = False
        self.periods = [{'id': 2}]
        self.previous_sks = 100
        self.academic = dict(kehadiran=55., jumlah_terlambat=5, ips_drop=1., sks_progress_ratio=1.111)
        self.rules = [
            rule('G1', 'kehadiran', '<',75,.6,[(0,59.99,1),(60,69.99,.8),(70,74.99,.5)]),
            rule('G3', 'terlambat','>=',3,.4,[(3,4,.6),(5,6,.8),(7,99,1)]),
            rule('G4', 'ips_drop','>=',.5,.55,[(.5,.79,.5),(.8,1.19,.8),(1.2,4,1)]),
            rule('G6', 'sks_progress_ratio','<',.85,.5,[(0,.499,1),(.5,.699,.8),(.7,.849,.5)])]
    def cursor(self,*args): return Cursor(self)
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


def test_reference_cf():
    symptoms = {'G1':.48,'G3':.24,'G4':.385}
    assert nilai(symptoms) == pytest.approx(.756952)
    assert kontribusi(symptoms)['G1'] == pytest.approx(.224352)


@pytest.mark.parametrize('score,category',[(0,'Rendah'),(.3999,'Rendah'),(.4,'Sedang'),(.7,'Tinggi'),(1,'Tinggi')])
def test_categories(score,category):
    assert klasifikasi_risiko(score) == category


def test_g3_and_individual_user_weights_and_period():
    db=DB(); main.run_cf_engine(db)
    saved={p[2]:p for q,p in db.calls if 'INSERT INTO hasil_gejala' in q}
    assert saved['G3'][3:5] == pytest.approx((.8,.32))
    assert saved['G1'][3:5] == pytest.approx((1,.6))
    assert saved['G4'][3:5] == pytest.approx((.8,.44))
    assert all(p[1] == 2 for p in saved.values())
    assert any('periode_id=%s' in q and p == ('TEST',2) for q,p in db.calls if 'FROM data_akademik' in q)
    assert db.commits == 1


@pytest.mark.parametrize('drop,expected',[(.79,.275),(.79999995,.44),(1.19999995,.55)])
def test_float_tier_boundaries(drop,expected):
    db=DB(); db.academic['ips_drop']=drop;main.run_cf_engine(db)
    row=next(p for q,p in db.calls if 'INSERT INTO hasil_gejala' in q and p[2]=='G4')
    assert row[4] == pytest.approx(expected)


def test_engine_rolls_back_on_failure():
    db=DB();db.fail=True
    with pytest.raises(RuntimeError): main.run_cf_engine(db)
    assert db.commits == 0 and db.rollbacks == 1


@pytest.mark.parametrize('periods',[[],[{'id':1},{'id':2}]])
def test_requires_single_active_period(periods):
    db=DB();db.periods=periods
    with pytest.raises(HTTPException) as e:main.run_cf_engine(db)
    assert e.value.status_code == 409


def input_values():
    return dict(nim='TEST',nama='Mahasiswa',prodi='TI',angkatan=2024,semester_sekarang=6,
                kehadiran=90,nilai_tugas=80,terlambat=0,ips_sebelumnya=3.5,ips_terakhir=3.5,
                sks_diambil=20,sks_lulus=20)


def test_input_cumulative_sks_atomic_commit():
    db=DB(); main.input_submit(request=None,db=db,**input_values())
    row=next(p for q,p in db.calls if 'INSERT INTO data_akademik' in q)
    assert row[-1] == 1.111
    assert db.commits == 1


def test_input_failure_does_not_commit():
    db=DB();db.fail=True
    with pytest.raises(RuntimeError):main.input_submit(request=None,db=db,**input_values())
    assert db.commits == 0


def test_sks_passed_cannot_exceed_taken():
    db=DB();values=input_values();values['sks_lulus']=24
    with pytest.raises(HTTPException) as e:main.input_submit(request=None,db=db,**values)
    assert e.value.status_code == 422 and db.commits == 0


def test_passwords_are_hashed_and_old_plaintext_rejected():
    hashed=hash_password('test-password-long')
    assert verify_password('test-password-long',hashed)
    assert not verify_password('wrong-password',hashed)
    assert not verify_password('admin123','admin123')


def test_student_cannot_write_or_read_another_student():
    user={'username':'STUDENT','peran':'mahasiswa'}
    with pytest.raises(HTTPException) as e:require_pa(user)
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:main.detail(None,'OTHER',db=DB(),user=user)
    assert e.value.status_code == 403


async def asgi_request(method,path,values=None,headers=None):
    body=urlencode(values or {}).encode()
    messages=[]
    scope={'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':method,
           'scheme':'http','path':path,'raw_path':path.encode(),'query_string':b'',
           'root_path':'','headers':[(b'host',b'testserver'),(b'content-type',b'application/x-www-form-urlencoded')]+(headers or []),
           'server':('testserver',80),'client':('127.0.0.1',1)}
    delivered=False
    async def receive():
        nonlocal delivered
        if not delivered:
            delivered=True
            return {'type':'http.request','body':body,'more_body':False}
        await asyncio.sleep(100)
    async def send(message):messages.append(message)
    await main.app(scope,receive,send)
    return next(m['status'] for m in messages if m['type']=='http.response.start')


@pytest.mark.parametrize('key,value',[('kehadiran',-1),('kehadiran',101),('ips_terakhir',4.1),('semester_sekarang',0),('sks_diambil',25),('nim','../bad'),('terlambat',-2),('kehadiran','nan')])
def test_server_rejects_invalid_form(key,value):
    db=DB();v=input_values();v[key]=value
    main.app.dependency_overrides[require_user]=lambda:{'username':'pa','peran':'dosen_pa'}
    main.app.dependency_overrides[main.get_db]=lambda:db
    try:assert asyncio.run(asgi_request('POST','/input-data',v)) == 422
    finally:main.app.dependency_overrides.clear()
    assert db.commits == 0


def test_anonymous_request_requires_login():
    assert asyncio.run(asgi_request('GET','/')) == 401


def test_cross_site_write_rejected():
    assert asyncio.run(asgi_request('POST','/run-engine',headers=[(b'origin',b'https://evil.example')])) == 403


@pytest.mark.parametrize('sks,semester,status',[(144,8,'Lulus Tepat Waktu'),(140,8,'Tidak Lulus Tepat Waktu'),(72,4,'On Track'),(144,9,'Lulus Terlambat')])
def test_prediction_cases(sks,semester,status):
    assert prediksi_lulus_tepat_waktu(sks,semester)['status'].startswith(status)


@pytest.fixture
def sql_db():
    """Exercise real SQL and Jinja rendering offline, without touching MySQL."""
    import sqlite3
    conn=sqlite3.connect(':memory:',check_same_thread=False)
    conn.row_factory=sqlite3.Row
    conn.executescript('''
        CREATE TABLE periode(id INTEGER,aktif INTEGER);
        INSERT INTO periode VALUES(1,0),(2,1);
        CREATE TABLE mahasiswa(nim TEXT,nama TEXT,prodi TEXT,angkatan INTEGER,semester_sekarang INTEGER,target_sks INTEGER,target_semester INTEGER);
        INSERT INTO mahasiswa VALUES('TEST','Nama Uji','TI',2024,6,144,8);
        CREATE TABLE data_semester(nim TEXT,semester INTEGER,sks_diambil INTEGER,sks_lulus INTEGER,ips REAL);
        INSERT INTO data_semester VALUES('TEST',1,20,20,3.5),('TEST',2,20,20,3.5),('TEST',3,20,20,3.5),('TEST',4,20,20,3.5),('TEST',5,20,20,3.5),('TEST',6,20,20,3.5);
        CREATE TABLE data_akademik(nim TEXT,periode_id INTEGER,kehadiran REAL,jumlah_terlambat INTEGER,ips_drop REAL,sks_progress_ratio REAL);
        INSERT INTO data_akademik VALUES('TEST',2,55,5,1,1.111),('TEST',1,99,0,0,1.111);
        CREATE TABLE aturan(id INTEGER,kode TEXT,metrik TEXT,kondisi TEXT,ambang REAL,cf_pakar REAL,cf_user_mapping TEXT,aktif INTEGER,deskripsi TEXT,indikator TEXT);
        CREATE TABLE hasil_risiko(nim TEXT,periode_id INTEGER,cf_gabungan REAL,kategori TEXT,status_prediksi TEXT);
        CREATE TABLE hasil_gejala(nim TEXT,periode_id INTEGER,kode_aturan TEXT,cf_user REAL,cf_gejala REAL,kontribusi REAL);
    ''')
    for i,r in enumerate(DB().rules):
        conn.execute('INSERT INTO aturan VALUES(?,?,?,?,?,?,?,?,?,?)',(i,r['kode'],r['metrik'],r['kondisi'],r['ambang'],r['cf_pakar'],r['cf_user_mapping'],1,'Deskripsi uji',r['metrik']))
    conn.commit()
    class SQLCursor:
        def __init__(self):self.c=conn.cursor()
        def execute(self,q,p=None):self.c.execute(q.replace('%s','?').replace('%%','%'),p or ())
        def fetchone(self):
            r=self.c.fetchone()
            return dict(r) if r is not None else None
        def fetchall(self):return [dict(r) for r in self.c.fetchall()]
        def close(self):self.c.close()
    class SQLDB:
        def cursor(self,*args):return SQLCursor()
        def commit(self):conn.commit()
        def rollback(self):conn.rollback()
    db=SQLDB()
    main.run_cf_engine(db)
    main.app.dependency_overrides[main.get_db]=lambda:db
    main.app.dependency_overrides[require_user]=lambda:{'username':'pa','peran':'dosen_pa'}
    yield db
    main.app.dependency_overrides.clear()
    conn.close()


@pytest.mark.parametrize('path',['/','/input-data','/mahasiswa/TEST'])
def test_pages_render_against_sql(sql_db,path):
    assert asyncio.run(asgi_request('GET',path)) == 200


def test_sql_engine_keeps_other_period_results(sql_db):
    c=sql_db.cursor()
    c.execute("INSERT INTO hasil_gejala VALUES('TEST',1,'G1',.5,.3,.3)")
    main.run_cf_engine(sql_db)
    c.execute('SELECT COUNT(*) AS n FROM hasil_gejala WHERE periode_id=1')
    assert c.fetchone()['n'] == 1
    c.execute("SELECT cf_user FROM hasil_gejala WHERE periode_id=2 AND kode_aturan='G3'")
    assert c.fetchone()['cf_user'] == .8


def test_student_endpoints(sql_db):
    main.app.dependency_overrides[require_user]=lambda:{'username':'TEST','peran':'mahasiswa'}
    assert asyncio.run(asgi_request('GET','/')) == 303
    assert asyncio.run(asgi_request('GET','/mahasiswa/TEST')) == 200
    assert asyncio.run(asgi_request('GET','/mahasiswa/OTHER')) == 403
    assert asyncio.run(asgi_request('GET','/input-data')) == 403
    assert asyncio.run(asgi_request('POST','/run-engine')) == 403
    assert asyncio.run(asgi_request('POST','/input-data',input_values())) == 403
