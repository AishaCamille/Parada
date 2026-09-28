"""Fluxos de ponta a ponta da API, com banco temporário."""
import http.client
import json
import threading
import tempfile
import time
import unittest
from datetime import date, timedelta
from pathlib import Path

import server


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db = server.DB_PATH
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="parada-tests-")
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        server.DB_PATH = cls.original_db
        cls.temp_dir.cleanup()

    def setUp(self):
        server.DB_PATH = Path(self.temp_dir.name) / f"{self._testMethodName}.sqlite3"
        server.init_db()

    def request(self, method, path, body=None, cookie=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port)
        headers = {"Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        conn.request(method, path, json.dumps(body).encode() if body is not None else None, headers)
        response = conn.getresponse()
        raw = response.read()
        result = raw.decode() if path.startswith("/api/export") else json.loads(raw)
        cookie_out = response.getheader("Set-Cookie")
        status = response.status
        conn.close()
        return status, result, cookie_out

    def test_core_flow_and_access(self):
        status, data, _ = self.request("GET", "/api/setup")
        self.assertTrue(data["needs_setup"])
        status, _, _ = self.request("POST", "/api/setup", {"name":"Admin", "email":"admin@example.test", "password":"senha-forte-123"})
        self.assertEqual(status, 201)
        status, _, cookie = self.request("POST", "/api/login", {"email":"admin@example.test", "password":"senha-forte-123"})
        self.assertEqual(status, 200)
        cookie = cookie.split(";", 1)[0]
        _, initial_manager, _ = self.request("POST", "/api/managers", {"name":"Gestor inicial", "phone":"123", "email":"gestor@example.test"}, cookie)
        _, driver, _ = self.request("POST", "/api/drivers", {"name":"Ana", "phone":"31999999999", "document":"DOC1", "vehicle":"Moto", "manager_id":initial_manager["id"], "km_per_liter":20}, cookie)
        _, first, _ = self.request("POST", "/api/places", {"address":"Partida", "latitude":-19.9, "longitude":-43.9}, cookie)
        _, second, _ = self.request("POST", "/api/places", {"address":"Rua Peru, 55", "latitude":-19.8, "longitude":-43.8}, cookie)
        status, route, _ = self.request("POST", "/api/routes", {"service_date":"2026-09-24", "driver_id":driver["id"], "distance_km":100}, cookie)
        self.assertEqual(status, 201)
        rid = route["id"]
        _, route, _ = self.request("POST", f"/api/routes/{rid}/stops", {"place_id":first["id"]}, cookie)
        first_stop = route["stops"][0]["id"]
        _, route, _ = self.request("POST", f"/api/routes/{rid}/stops", {"place_id":second["id"]}, cookie)
        second_stop = route["stops"][1]["id"]
        for stop in (first_stop, second_stop):
            status, route, _ = self.request("PATCH", f"/api/stops/{stop}", {"arrival":"2026-09-24T09:00", "departure":"2026-09-24T09:15"}, cookie)
            self.assertEqual(status, 200)
        self.assertEqual(route["stopped_seconds"], 900)
        self.assertEqual(route["stops"][0]["stopped_seconds"], 0)
        self.assertEqual(route["estimated_cost"], 30)
        self.assertEqual(route["workday_percent"], 3.1)
        status, place, _ = self.request("PATCH", f"/api/places/{second['id']}", {"address":"Rua Peru, 55", "latitude":-19.7, "longitude":-43.7}, cookie)
        self.assertEqual(status, 200)
        self.assertEqual(place["latitude"], -19.7)
        status, data, _ = self.request("GET", "/api/dashboard?start=2026-09-01&end=2026-09-30", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(data["daily"], {"2026-09-24":900})
        self.assertEqual(len(data["history"]), 1)
        self.assertEqual(data["history"][0]["address"], "Rua Peru, 55")
        status, _, _ = self.request("PUT", "/api/settings", {"fuel_price":8,"default_km_per_liter":10,"extra_cost_per_km":0.1,"workday_hours":6,"count_from_position":2}, cookie)
        self.assertEqual(status, 200)
        status, recalculated, _ = self.request("GET", f"/api/routes/{rid}", cookie=cookie)
        self.assertEqual(recalculated["estimated_cost"], 50)
        self.assertEqual(recalculated["workday_percent"], 4.2)
        status, csv_data, _ = self.request("GET", "/api/export?start=2026-09-01&end=2026-09-30", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertIn("Rua Peru, 55", csv_data)
        self.assertNotIn("Partida", csv_data)
        status, _, _ = self.request("PATCH", f"/api/stops/{second_stop}", {"departure":"2026-09-24T08:00"}, cookie)
        self.assertEqual(status, 400)
        status, _, _ = self.request("POST", "/api/users", {"name":"Ana", "email":"ana@example.test", "password":"senha-forte-456", "role":"driver", "driver_id":driver["id"]}, cookie)
        self.assertEqual(status, 201)
        _, _, driver_cookie = self.request("POST", "/api/login", {"email":"ana@example.test", "password":"senha-forte-456"})
        driver_cookie = driver_cookie.split(";",1)[0]
        status, _, _ = self.request("POST", "/api/places", {"address":"Proibido"}, driver_cookie)
        self.assertEqual(status, 403)
        status, _, _ = self.request("GET", "/api/audit", cookie=driver_cookie)
        self.assertEqual(status, 403)
        status, own, _ = self.request("GET", f"/api/routes/{rid}", cookie=driver_cookie)
        self.assertEqual(status, 200)
        self.assertEqual(own["driver_id"], driver["id"])
        status, audit, _ = self.request("GET", "/api/audit", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertTrue(any(x["entity"]=="stop" and x["action"]=="update" for x in audit))
        status, manager, _ = self.request("POST", "/api/managers", {"name":"Bruno","phone":"31988888888","email":"bruno@example.test"}, cookie)
        self.assertEqual(status, 201)
        status, _, _ = self.request("POST", "/api/users", {"name":"Bruno","email":"bruno@example.test","password":"senha-forte-789","role":"manager","manager_id":manager["id"]}, cookie)
        self.assertEqual(status, 201)
        _, _, manager_cookie = self.request("POST", "/api/login", {"email":"bruno@example.test","password":"senha-forte-789"})
        manager_cookie = manager_cookie.split(";",1)[0]
        status, _, _ = self.request("GET", f"/api/routes/{rid}", cookie=manager_cookie)
        self.assertEqual(status, 403)
        status, other_driver, _ = self.request("POST", "/api/drivers", {"name":"Caio","phone":"31977777777","document":"DOC2","vehicle":"Van"}, manager_cookie)
        self.assertEqual(status, 201)
        status, managed_route, _ = self.request("POST", "/api/routes", {"service_date":"2026-09-24","driver_id":other_driver["id"],"distance_km":10}, manager_cookie)
        self.assertEqual(status, 201)
        self.assertEqual(managed_route["driver_id"], other_driver["id"])
        with server.db() as con:
            con.execute("BEGIN")
            for offset in range(365):
                day=(date(2025,9,24)+timedelta(days=offset)).isoformat()
                route_id=con.execute("INSERT INTO routes(service_date,driver_id,distance_km,created_at) VALUES (?,?,?,?)",(day,driver["id"],20,server.now())).lastrowid
                con.execute("INSERT INTO stops(route_id,place_id,position) VALUES (?,?,1)",(route_id,first["id"]))
                con.execute("INSERT INTO stops(route_id,place_id,position,arrival,departure) VALUES (?,?,?,?,?)",(route_id,second["id"],2,day+"T10:00:00",day+"T10:10:00"))
            con.commit()
        began=time.perf_counter()
        status, year_data, _ = self.request("GET", "/api/dashboard?start=2025-09-24&end=2026-09-23", cookie=cookie)
        elapsed=time.perf_counter()-began
        self.assertEqual(status, 200)
        self.assertEqual(len(year_data["routes"]), 365)
        self.assertLess(elapsed, 3, f"Consulta de 12 meses levou {elapsed:.2f}s")


    def test_public_registration_and_team_isolation(self):
        password = "senha-segura-123"
        def register(role, email, **extra):
            return self.request("POST", "/api/register", {"role":role, "name":email,
                "email":email, "phone":"31999999999", "password":password, **extra})
        def login(email):
            status, _, cookie = self.request("POST", "/api/login", {"email":email,"password":password})
            self.assertEqual(status, 200)
            cookie = cookie.split(";",1)[0]
            return cookie, self.request("GET", "/api/me", cookie=cookie)[1]
        self.assertEqual(register("admin", "invalid@example.test")[0],400)
        for email in ("manager1@example.test", "manager2@example.test"):
            self.assertEqual(register("manager", email)[0],201)
        manager_cookie, manager = login("manager1@example.test")
        other_cookie, other = login("manager2@example.test")
        code = manager["team"]["invite_code"]
        self.assertNotEqual(code, other["team"]["invite_code"])
        driver_fields = {"document":"PUBLIC1", "vehicle":"Van", "invite_code":code}
        self.assertEqual(register("driver", "driver1@example.test", **{**driver_fields,"invite_code":"invalid"})[0],400)
        self.assertEqual(register("driver", "driver1@example.test", **driver_fields)[0],201)
        self.assertTrue(self.request('GET','/api/setup')[1]['needs_setup'])
        self.assertEqual(self.request('POST','/api/setup',{'name':'Admin','email':'admin@example.test','password':password})[0],201)
        self.assertFalse(self.request('GET','/api/setup')[1]['needs_setup'])
        self.assertEqual(self.request('POST','/api/setup',{'name':'Outro','email':'outro@example.test','password':password})[0],409)
        driver_cookie, driver = login("driver1@example.test")
        self.assertEqual(driver["team"]["name"], manager["name"])
        self.assertNotIn("invite_code",driver["team"])
        self.assertEqual(register("driver", "manager1@example.test", **{**driver_fields,"document":"ROLLBACK"})[0],409)
        with server.db() as con:
            self.assertIsNone(con.execute("SELECT id FROM drivers WHERE document='ROLLBACK'").fetchone())
        status, team, _ = self.request("GET", "/api/drivers", cookie=manager_cookie)
        self.assertEqual([d["id"] for d in team],[driver["driver_id"]])
        self.assertEqual(self.request("GET", "/api/drivers", cookie=other_cookie)[1],[])
        status, route, _ = self.request("POST", "/api/routes", {"driver_id":driver["driver_id"],"service_date":date.today().isoformat(),"distance_km":10}, manager_cookie)
        self.assertEqual(status,201)
        self.assertEqual(self.request("GET", f"/api/routes/{route['id']}", cookie=other_cookie)[0],403)
        self.assertEqual(self.request("GET", f"/api/routes/{route['id']}", cookie=driver_cookie)[0],200)
        self.assertEqual(self.request("GET", "/api/dashboard", cookie=other_cookie)[1]["routes"],[])
        self.assertNotIn("driver1@example.test", self.request("GET", "/api/export", cookie=other_cookie)[1])
        self.assertEqual(self.request("POST", "/api/drivers", {"name":"Blocked"}, driver_cookie)[0],403)
        self.assertEqual(self.request("POST", "/api/routes", {"driver_id":driver["driver_id"],"service_date":date.today().isoformat(),"distance_km":0}, other_cookie)[0],403)
        status, _, cleared_cookie = self.request("POST", "/api/logout", cookie=driver_cookie)
        self.assertEqual(status,200)
        self.assertIn("Max-Age=0",cleared_cookie)
        self.assertEqual(self.request("GET", "/api/me", cookie=driver_cookie)[0],401)
        self.assertEqual(self.request("POST", "/api/logout", cookie=driver_cookie)[0],200)
        self.assertEqual(self.request("POST", "/api/logout")[0],200)
        new_cookie, signed_in = login("driver1@example.test")
        self.assertEqual(signed_in["id"],driver["id"])
        self.assertNotEqual(new_cookie,driver_cookie)
        server.init_db()
        self.assertEqual(self.request("GET", "/api/me", cookie=manager_cookie)[1]["team"]["invite_code"],code)


    def test_vehicle_updates_and_place_isolation(self):
        password='senha-teste-123'
        cookies=[]
        for i in (1,2):
            email=f'gestor{i}@example.test'
            self.assertEqual(self.request('POST','/api/register',{'role':'manager','name':f'Gestor {i}','email':email,'phone':'000','password':password})[0],201)
            cookies.append(self.request('POST','/api/login',{'email':email,'password':password})[2].split(';',1)[0])
        owner,other=cookies
        fields={'name':'Motorista fictício','phone':'000','document':'DOC-EDIT','vehicle':'Van','km_per_liter':12}
        _,driver,_=self.request('POST','/api/drivers',fields,owner)
        _,place,_=self.request('POST','/api/places',{'address':'Ponto privado','latitude':-19,'longitude':-44},owner)
        self.assertEqual(self.request('GET','/api/places',cookie=other)[1],[])
        self.assertEqual(self.request('PATCH',f"/api/places/{place['id']}",{'address':'Tentativa'},other)[0],403)
        self.assertEqual(self.request('PATCH',f"/api/drivers/{driver['id']}",{**fields,'km_per_liter':20},other)[0],403)
        _,route,_=self.request('POST','/api/routes',{'service_date':'2026-09-28','driver_id':driver['id'],'distance_km':100},owner)
        self.assertEqual(route['estimated_cost'],50)
        status,updated,_=self.request('PATCH',f"/api/drivers/{driver['id']}",{**fields,'km_per_liter':20},owner)
        self.assertEqual(status,200)
        self.assertEqual(updated['km_per_liter'],20)
        self.assertEqual(self.request('GET',f"/api/routes/{route['id']}",cookie=owner)[1]['estimated_cost'],30)
        self.assertEqual(self.request('PATCH',f"/api/drivers/{driver['id']}",{**fields,'km_per_liter':0},owner)[0],400)
        _,other_driver,_=self.request('POST','/api/drivers',{**fields,'document':'OTHER'},other)
        _,other_route,_=self.request('POST','/api/routes',{'service_date':'2026-09-28','driver_id':other_driver['id'],'distance_km':1},other)
        self.assertEqual(self.request('POST',f"/api/routes/{other_route['id']}/stops",{'place_id':place['id']},other)[0],403)
        self.assertEqual(self.request('POST',f"/api/routes/{route['id']}/stops",{'place_id':place['id']+0.5},owner)[0],400)
        self.assertEqual(self.request('POST','/api/places',{'address':None},owner)[0],400)

    def test_period_boundaries_and_batch_queries(self):
        for start,end in [('2025-01-01','2025-12-31'),('2024-01-01','2024-12-31'),('2024-02-29','2025-02-27')]:
            self.assertEqual(server.period({'start':[start],'end':[end]}),(start,end))
        for start,end in [('2025-01-01','2026-01-01'),('2024-02-29','2025-02-28'),('2026-09-28','2026-09-27')]:
            with self.assertRaises(server.ApiError): server.period({'start':[start],'end':[end]})
        with server.db() as con:
            statements=[]
            con.set_trace_callback(statements.append)
            server.period_data(con,{'role':'admin'},'2026-01-01','2026-12-31')
            self.assertEqual(len([s for s in statements if s.startswith('SELECT')]),3)

    def test_statement_examples_and_demo_preservation(self):
        import demo
        demo_path=Path(self.temp_dir.name)/'demo.sqlite3'
        self.assertTrue(demo.create_demo(demo_path,date(2026,9,28)))
        with server.db() as con:
            data=server.period_data(con,{'role':'admin'},'2026-09-28','2026-09-28')
            self.assertEqual([r['stopped_seconds']//60 for r in data['routes']],[75,41,45])
            self.assertEqual(data['total_seconds'],161*60)
            self.assertEqual(data['total_cost'],37.5)
            self.assertTrue(all(r['stops'][0]['stopped_seconds']==0 for r in data['routes']))
        self.assertFalse(demo.create_demo(demo_path))
        status,_,cookie=self.request('POST','/api/login',{'email':'admin@parada.test','password':demo.PASSWORD})
        self.assertEqual(status,200)
        cookie=cookie.split(';',1)[0]
        status,_,_=self.request('PUT','/api/settings',{'fuel_price':6,'default_km_per_liter':12,'extra_cost_per_km':0,'workday_hours':8,'count_from_position':3},cookie)
        self.assertEqual(status,200)
        _,data,_=self.request('GET','/api/dashboard?start=2026-09-28&end=2026-09-28',cookie=cookie)
        self.assertEqual(data['total_seconds'],131*60)
        self.assertEqual(self.request('PATCH',f"/api/stops/{data['routes'][0]['stops'][1]['id']}",{'arrival':'2026-09-27T08:00'},cookie)[0],400)
        _,audit,_=self.request('GET','/api/audit',cookie=cookie)
        self.assertTrue(any(x['entity']=='settings' for x in audit))


if __name__ == "__main__":
    unittest.main()
