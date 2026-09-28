"""Mede consulta anual com 3.650 roteiros fictícios em banco temporário."""
import sys
import tempfile
import threading
import time
import http.client
import json
from datetime import date,timedelta
import server,demo
with tempfile.TemporaryDirectory(prefix='parada-benchmark-') as folder:
    demo.create_demo(folder+'/bench.sqlite3')
    with server.db() as con:
        manager=con.execute('SELECT id FROM managers LIMIT 1').fetchone()['id']
        places=[p['id'] for p in con.execute('SELECT id FROM places ORDER BY id')]
        con.execute('BEGIN IMMEDIATE')
        for i in range(10):
            driver=con.execute('INSERT INTO drivers(name,phone,document,vehicle,km_per_liter,manager_id) VALUES (?,?,?,?,?,?)',(f'Fictício {i}','000',f'BENCH-{i}','Van',12,manager)).lastrowid
            for offset in range(365):
                day=(date(2025,1,1)+timedelta(days=offset)).isoformat()
                route=con.execute('INSERT INTO routes(service_date,driver_id,distance_km,created_at) VALUES (?,?,?,?)',(day,driver,30,server.now())).lastrowid
                for j,p in enumerate(places):
                    con.execute('INSERT INTO stops(route_id,place_id,position,arrival,departure) VALUES (?,?,?,?,?)',(route,p,j+1,day+f'T{8+j:02d}:00:00',day+f'T{8+j:02d}:15:00'))
        con.commit()
    httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    conn=http.client.HTTPConnection('127.0.0.1',httpd.server_port)
    conn.request('POST','/api/login',json.dumps({'email':'admin@parada.test','password':demo.PASSWORD}),{'Content-Type':'application/json'})
    response=conn.getresponse();response.read();cookie=response.getheader('Set-Cookie').split(';',1)[0]
    began=time.perf_counter()
    conn.request('GET','/api/dashboard?start=2025-01-01&end=2025-12-31',headers={'Cookie':cookie})
    response=conn.getresponse();payload=response.read();elapsed=time.perf_counter()-began
    data=json.loads(payload)
    result={'http_status':response.status,'routes':len(data['routes']),'stops':sum(len(r['stops']) for r in data['routes']),'response_bytes':len(payload),'seconds':round(elapsed,4),'limit_seconds':3,'python':sys.version.split()[0]}
    print(json.dumps(result,ensure_ascii=False))
    assert result['http_status']==200 and result['routes']==3650 and elapsed<3
    conn.close();httpd.shutdown();httpd.server_close()
