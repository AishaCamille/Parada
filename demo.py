"""Demonstração fictícia dos roteiros A/B/C, em banco separado do banco normal."""
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
import server

DEMO_DB = server.ROOT / 'data' / 'demonstracao.sqlite3'
PASSWORD = 'Parada-demo-123'


def create_demo(path=DEMO_DB, service_day=None):
    path = Path(path)
    server.DB_PATH = path
    # Uma demonstração existente é preservada; nada é apagado ou sobrescrito.
    if path.exists():
        return False
    server.init_db()
    day = service_day or date.today()
    with server.db() as con:
        con.execute('BEGIN IMMEDIATE')
        manager_id = con.execute('INSERT INTO managers(name,phone,email,invite_code) VALUES (?,?,?,?)',
            ('Equipe Demonstração', '00000000000', 'gerente@parada.test', 'PARADA-DEMO')).lastrowid
        admin_id = con.execute("INSERT INTO users(name,email,password_hash,role) VALUES (?,?,?,'admin')",
            ('Administrador Demo','admin@parada.test',server.hash_password(PASSWORD))).lastrowid
        con.execute("INSERT INTO users(name,email,password_hash,role,manager_id) VALUES (?,?,?,'manager',?)",
            ('Gerente Demo','gerente@parada.test',server.hash_password(PASSWORD),manager_id))
        addresses = ['Seg. Família (partida)', 'Rua Peru, 55', 'Rua X, 5', 'Av. João César']
        place_ids = [con.execute('INSERT INTO places(address,latitude,longitude,manager_id) VALUES (?,?,?,?)',
            (address,-19.93+i*0.001,-44.05+i*0.001,manager_id)).lastrowid for i,address in enumerate(addresses)]
        for label, minutes, distance in [('A',[15,10,50],30),('B',[10,5,26],20),('C',[5,10,30],25)]:
            driver_id=con.execute('INSERT INTO drivers(name,phone,document,vehicle,km_per_liter,manager_id) VALUES (?,?,?,?,?,?)',
                (f'Motorista {label} (fictício)','00000000000',f'DEMO-{label}','Veículo fictício',12,manager_id)).lastrowid
            con.execute("INSERT INTO users(name,email,password_hash,role,driver_id) VALUES (?,?,?,'driver',?)",
                (f'Motorista {label}',f'motorista{label.lower()}@parada.test',server.hash_password(PASSWORD),driver_id))
            route_id=con.execute('INSERT INTO routes(service_date,driver_id,distance_km,created_at) VALUES (?,?,?,?)',
                (day.isoformat(),driver_id,distance,server.now())).lastrowid
            current = datetime.combine(day, datetime.min.time()).replace(hour=8)
            for index, place_id in enumerate(place_ids):
                duration=20 if index==0 else minutes[index-1]
                departure=current+timedelta(minutes=duration)
                con.execute('INSERT INTO stops(route_id,place_id,position,arrival,departure) VALUES (?,?,?,?,?)',
                    (route_id,place_id,index+1,current.isoformat(),departure.isoformat()))
                current=departure+timedelta(minutes=10)
            server.audit(con, {'id':admin_id}, 'route', route_id, 'demo', after={'roteiro':label,'dados':'fictícios'})
        con.commit()
    return True


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve',action='store_true',help='Inicia o servidor de demonstração')
    parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args()
    created=create_demo()
    print('Demonstração criada.' if created else 'Demonstração existente preservada.')
    print(f'Banco separado: {DEMO_DB}')
    print('Contas: admin@parada.test, gerente@parada.test, motoristaa@parada.test')
    print(f'Senha de demonstração: {PASSWORD}')
    print('Totais esperados: A = 75 min; B = 41 min; C = 45 min; período = 161 min.')
    if args.serve:
        server.init_db()
        print(f'Abra http://127.0.0.1:{args.port}')
        server.ThreadingHTTPServer(('127.0.0.1',args.port),server.Handler).serve_forever()
