"""Parada: MVP de monitoramento de tempo parado. Sem dependências externas."""
from __future__ import annotations

import csv
from contextlib import contextmanager
import hashlib
import hmac
import io
import json
import os
import secrets
import sqlite3
import sys
import threading
import webbrowser
from datetime import date, datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("PARADA_DB", ROOT / "data" / "parada.sqlite3"))
SESSION_HOURS = 12


class ApiError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS drivers (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL,
          document TEXT NOT NULL UNIQUE, vehicle TEXT NOT NULL,
          km_per_liter REAL CHECK(km_per_liter>0),
          manager_id INTEGER REFERENCES managers(id));
        CREATE TABLE IF NOT EXISTS managers (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','manager','driver')),
          driver_id INTEGER REFERENCES drivers(id), manager_id INTEGER REFERENCES managers(id),
          CHECK((role='driver' AND driver_id IS NOT NULL AND manager_id IS NULL) OR
                (role='manager' AND manager_id IS NOT NULL AND driver_id IS NULL) OR
                (role='admin' AND driver_id IS NULL AND manager_id IS NULL)));
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          expires_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS places (
          id INTEGER PRIMARY KEY, address TEXT NOT NULL,
          latitude REAL CHECK(latitude BETWEEN -90 AND 90),
          longitude REAL CHECK(longitude BETWEEN -180 AND 180));
        CREATE TABLE IF NOT EXISTS routes (
          id INTEGER PRIMARY KEY, service_date TEXT NOT NULL,
          driver_id INTEGER NOT NULL REFERENCES drivers(id),
          distance_km REAL NOT NULL DEFAULT 0 CHECK(distance_km>=0),
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS stops (
          id INTEGER PRIMARY KEY, route_id INTEGER NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
          place_id INTEGER NOT NULL REFERENCES places(id), position INTEGER NOT NULL CHECK(position>=1),
          arrival TEXT, departure TEXT,
          UNIQUE(route_id,position), CHECK(departure IS NULL OR arrival IS NOT NULL),
          CHECK(departure IS NULL OR departure>=arrival));
        CREATE INDEX IF NOT EXISTS idx_routes_date ON routes(service_date);
        CREATE INDEX IF NOT EXISTS idx_stops_route ON stops(route_id,position);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit (
          id INTEGER PRIMARY KEY, at TEXT NOT NULL, actor_id INTEGER REFERENCES users(id),
          entity TEXT NOT NULL, entity_id INTEGER NOT NULL, action TEXT NOT NULL,
          before_json TEXT, after_json TEXT);
        """)
        if "invite_code" not in {r["name"] for r in con.execute("PRAGMA table_info(managers)")}:
            con.execute("ALTER TABLE managers ADD COLUMN invite_code TEXT")
        for manager in con.execute("SELECT id FROM managers WHERE invite_code IS NULL").fetchall():
            con.execute("UPDATE managers SET invite_code=? WHERE id=?", (secrets.token_hex(8).upper(), manager["id"]))
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_manager_invite ON managers(invite_code)")
        for key, value in {
            "fuel_price": "6.00", "default_km_per_liter": "12", "extra_cost_per_km": "0",
            "workday_hours": "8", "count_from_position": "2"
        }.items():
            con.execute("INSERT OR IGNORE INTO settings VALUES (?,?)", (key, value))


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_password(password):
    if len(password) < 10:
        raise ApiError("A senha deve ter pelo menos 10 caracteres.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password, stored):
    try:
        salt, digest = stored.split(":")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 260_000)
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def required(body, key):
    value = str(body.get(key, "")).strip()
    if not value:
        raise ApiError(f"Campo obrigatório: {key}.")
    return value


def number(body, key, minimum=None, maximum=None, optional=False):
    value = body.get(key)
    if optional and (value is None or value == ""):
        return None
    try:
        value = float(value)
    except (ValueError, TypeError):
        raise ApiError(f"Número inválido: {key}.")
    if not (-float("inf") < value < float("inf")) or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise ApiError(f"Valor fora do intervalo: {key}.")
    return value


def integer(body, key, minimum=1):
    try:
        value = int(body.get(key))
    except (ValueError, TypeError):
        raise ApiError(f"Inteiro inválido: {key}.")
    if value < minimum:
        raise ApiError(f"Valor inválido: {key}.")
    return value


def service_date(value):
    try:
        return date.fromisoformat(value).isoformat()
    except (ValueError, TypeError):
        raise ApiError("Data inválida; use AAAA-MM-DD.")


def timestamp(value):
    if value in (None, ""):
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is not None:
            raise ValueError
        return dt.isoformat(timespec="seconds")
    except (ValueError, TypeError):
        raise ApiError("Data/hora inválida; use horário local sem fuso.")


def row_dict(row):
    return dict(row) if row else None


def audit(con, actor, entity, entity_id, action, before=None, after=None):
    con.execute("INSERT INTO audit(at,actor_id,entity,entity_id,action,before_json,after_json) VALUES (?,?,?,?,?,?,?)",
                (now(), actor["id"], entity, entity_id, action,
                 json.dumps(before, ensure_ascii=False) if before is not None else None,
                 json.dumps(after, ensure_ascii=False) if after is not None else None))


def settings(con):
    return {r["key"]: float(r["value"]) for r in con.execute("SELECT key,value FROM settings")}


def route_allowed(user, route, con):
    if not route:
        raise ApiError("Roteiro não encontrado.", 404)
    if user["role"] == "driver" and route["driver_id"] != user["driver_id"]:
        raise ApiError("Acesso negado.", 403)
    if user["role"] == "manager" and not con.execute("SELECT 1 FROM drivers WHERE id=? AND manager_id=?", (route["driver_id"],user["manager_id"])).fetchone():
        raise ApiError("Acesso negado.", 403)


def route_details(con, route_id, user):
    route = con.execute("SELECT r.*,d.name AS driver_name,d.km_per_liter FROM routes r JOIN drivers d ON d.id=r.driver_id WHERE r.id=?", (route_id,)).fetchone()
    route_allowed(user, route, con)
    item = row_dict(route)
    cfg = settings(con)
    stops = [dict(x) for x in con.execute("""SELECT s.*,p.address,p.latitude,p.longitude
        FROM stops s JOIN places p ON p.id=s.place_id WHERE s.route_id=? ORDER BY s.position""", (route_id,))]
    total = 0
    for stop in stops:
        seconds = 0
        if stop["position"] >= cfg["count_from_position"] and stop["arrival"] and stop["departure"]:
            seconds = int((datetime.fromisoformat(stop["departure"]) - datetime.fromisoformat(stop["arrival"])).total_seconds())
        stop["stopped_seconds"] = seconds
        total += seconds
    rate = item["km_per_liter"] or cfg["default_km_per_liter"]
    item["stops"] = stops
    item["stopped_seconds"] = total
    item["workday_percent"] = round(total / (cfg["workday_hours"] * 3600) * 100, 1)
    item["cost_per_km"] = round(cfg["fuel_price"] / rate + cfg["extra_cost_per_km"], 4)
    item["estimated_cost"] = round(item["distance_km"] * item["cost_per_km"], 2)
    return item


def period(query):
    start = service_date(query.get("start", [date.today().replace(day=1).isoformat()])[0])
    end = service_date(query.get("end", [date.today().isoformat()])[0])
    if end < start or (date.fromisoformat(end) - date.fromisoformat(start)).days > 366:
        raise ApiError("Escolha um período de até 12 meses, com início anterior ao fim.")
    return start, end


def period_data(con, user, start, end):
    sql = "SELECT r.id FROM routes r JOIN drivers d ON d.id=r.driver_id WHERE r.service_date BETWEEN ? AND ?"
    args = [start, end]
    if user["role"] == "driver":
        sql += " AND r.driver_id=?"
        args.append(user["driver_id"])
    if user["role"] == "manager":
        sql += " AND d.manager_id=?"
        args.append(user["manager_id"])
    routes = [route_details(con, x["id"], user) for x in con.execute(sql + " ORDER BY r.service_date,r.id", args)]
    daily, monthly, places = {}, {}, {}
    history = []
    for route in routes:
        day, month = route["service_date"], route["service_date"][:7]
        daily[day] = daily.get(day, 0) + route["stopped_seconds"]
        monthly[month] = monthly.get(month, 0) + route["stopped_seconds"]
        for stop in route["stops"]:
            if stop["position"] == 1:
                continue
            places[stop["address"]] = places.get(stop["address"], 0) + stop["stopped_seconds"]
            history.append({"route_id": route["id"], "service_date": day, "driver_name": route["driver_name"],
                            "position": stop["position"], "address": stop["address"], "arrival": stop["arrival"],
                            "departure": stop["departure"], "stopped_seconds": stop["stopped_seconds"]})
    return {"routes": routes, "history": history, "daily": daily, "monthly": monthly,
            "places": places, "total_seconds": sum(daily.values()), "total_cost": round(sum(x["estimated_cost"] for x in routes), 2),
            "workday_hours": settings(con)["workday_hours"]}


class Handler(BaseHTTPRequestHandler):
    def respond(self, data, status=200, cookie=None, content_type="application/json; charset=utf-8"):
        payload = json.dumps(data, ensure_ascii=False).encode() if content_type.startswith("application/json") else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(payload)

    def body(self):
        size = int(self.headers.get("Content-Length", "0"))
        if size > 1_000_000:
            raise ApiError("Conteúdo muito grande.", 413)
        try:
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError
            return data
        except (ValueError, UnicodeDecodeError):
            raise ApiError("JSON inválido.")

    def user(self, con):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            token = cookie["parada_session"].value
        except (KeyError, AttributeError):
            raise ApiError("Entre para continuar.", 401)
        digest = hashlib.sha256(token.encode()).hexdigest()
        row = con.execute("""SELECT u.id,u.name,u.email,u.role,u.driver_id,u.manager_id
            FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?""",
                          (digest, now())).fetchone()
        if not row:
            raise ApiError("Sessão expirada. Entre novamente.", 401)
        return row_dict(row)

    def handle_request(self, method):
        url = urlsplit(self.path)
        path, query = url.path, parse_qs(url.query)
        if method == "GET" and path in ("/", "/app.js", "/style.css"):
            file = ROOT / {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[path]
            mime = "text/html" if path == "/" else "text/javascript" if path == "/app.js" else "text/css"
            self.respond(file.read_bytes(), content_type=mime + "; charset=utf-8")
            return
        if not path.startswith("/api/"):
            raise ApiError("Não encontrado.", 404)
        body = self.body() if method in ("POST", "PUT", "PATCH") and path != "/api/logout" else {}
        with db() as con:
            if path == "/api/logout" and method == "POST":
                cookie = SimpleCookie(); cookie.load(self.headers.get("Cookie", ""))
                if "parada_session" in cookie:
                    con.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(cookie["parada_session"].value.encode()).hexdigest(),))
                self.respond({"ok": True}, cookie="parada_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"); return
            if path == "/api/register" and method == "POST":
                new_role = required(body, "role")
                if new_role not in ("driver", "manager"):
                    raise ApiError("Escolha motorista ou gerente.")
                name, phone = required(body, "name"), required(body, "phone")
                email = required(body, "email").lower()
                if "@" not in email or "." not in email.split("@")[-1]:
                    raise ApiError("Informe um e-mail válido.")
                password_hash = hash_password(required(body, "password"))
                con.execute("BEGIN IMMEDIATE")
                driver_id = manager_id = None
                if new_role == "manager":
                    manager_id = con.execute("INSERT INTO managers(name,phone,email,invite_code) VALUES (?,?,?,?)",
                                             (name, phone, email, secrets.token_hex(8).upper())).lastrowid
                else:
                    manager = con.execute("SELECT id FROM managers WHERE invite_code=?",
                                          (required(body, "invite_code").upper(),)).fetchone()
                    if not manager:
                        raise ApiError("Código da equipe inválido. Solicite o código ao seu gerente.")
                    driver_id = con.execute("INSERT INTO drivers(name,phone,document,vehicle,km_per_liter,manager_id) VALUES (?,?,?,?,?,?)",
                                            (name, phone, required(body, "document"), required(body, "vehicle"),
                                             number(body, "km_per_liter", 0.01, optional=True), manager["id"])).lastrowid
                user_id = con.execute("INSERT INTO users(name,email,password_hash,role,driver_id,manager_id) VALUES (?,?,?,?,?,?)",
                                      (name, email, password_hash, new_role, driver_id, manager_id)).lastrowid
                audit(con, {"id": user_id}, "user", user_id, "register", after={"role": new_role})
                con.commit()
                self.respond({"id": user_id}, 201); return
            if path == "/api/setup" and method == "GET":
                self.respond({"needs_setup": con.execute("SELECT NOT EXISTS(SELECT 1 FROM users)").fetchone()[0] == 1})
                return
            if path == "/api/setup" and method == "POST":
                if con.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                    raise ApiError("Configuração inicial já concluída.", 409)
                cur = con.execute("INSERT INTO users(name,email,password_hash,role) VALUES (?,?,?,'admin')",
                                  (required(body, "name"), required(body, "email").lower(), hash_password(required(body, "password"))))
                self.respond({"id": cur.lastrowid}, 201)
                return
            if path == "/api/login" and method == "POST":
                row = con.execute("SELECT * FROM users WHERE email=?", (required(body, "email").lower(),)).fetchone()
                if not row or not verify_password(required(body, "password"), row["password_hash"]):
                    raise ApiError("E-mail ou senha incorretos.", 401)
                token = secrets.token_urlsafe(32)
                expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat(timespec="seconds")
                con.execute("INSERT INTO sessions VALUES (?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), row["id"], expires))
                self.respond({"user": {k: row[k] for k in ("id", "name", "email", "role", "driver_id", "manager_id")}},
                             cookie=f"parada_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_HOURS*3600}")
                return
            user = self.user(con)
            role = user["role"]
            if path == "/api/me" and method == "GET":
                if role == "manager":
                    user["team"] = row_dict(con.execute("SELECT name,invite_code FROM managers WHERE id=?", (user["manager_id"],)).fetchone())
                elif role == "driver":
                    user["team"] = row_dict(con.execute("SELECT m.name FROM managers m JOIN drivers d ON d.manager_id=m.id WHERE d.id=?", (user["driver_id"],)).fetchone())
                self.respond(user); return
            if path == "/api/settings":
                if method == "GET": self.respond(settings(con)); return
                if method == "PUT" and role == "admin":
                    limits = {"fuel_price": (0, None), "default_km_per_liter": (0.01, None),
                              "extra_cost_per_km": (0, None), "workday_hours": (0.1, 24), "count_from_position": (2, 100)}
                    before = settings(con)
                    con.execute("BEGIN IMMEDIATE")
                    for key, (low, high) in limits.items():
                        value = number(body, key, low, high)
                        if key == "count_from_position" and not value.is_integer(): raise ApiError("A posição inicial deve ser inteira.")
                        con.execute("UPDATE settings SET value=? WHERE key=?", (str(value), key))
                    audit(con, user, "settings", 1, "update", before, settings(con))
                    con.commit()
                    self.respond(settings(con)); return
            if path == "/api/drivers":
                if method == "GET":
                    clause = " WHERE id=?" if role == "driver" else " WHERE manager_id=?" if role == "manager" else ""
                    ident = user["driver_id"] if role == "driver" else user["manager_id"] if role == "manager" else None
                    self.respond([dict(x) for x in con.execute("SELECT * FROM drivers" + clause + " ORDER BY name", (ident,) if ident else ())]); return
                if method == "POST" and role in ("admin", "manager"):
                    manager_id=user["manager_id"] if role=="manager" else integer(body,"manager_id")
                    cur = con.execute("INSERT INTO drivers(name,phone,document,vehicle,km_per_liter,manager_id) VALUES (?,?,?,?,?,?)",
                                      (required(body,"name"),required(body,"phone"),required(body,"document"),required(body,"vehicle"),number(body,"km_per_liter",0.01,optional=True),manager_id))
                    audit(con,user,"driver",cur.lastrowid,"create",after={"name":body["name"],"vehicle":body["vehicle"]})
                    self.respond({"id":cur.lastrowid},201); return
            if path == "/api/managers":
                if method == "GET" and role in ("admin","manager"):
                    self.respond([dict(x) for x in con.execute("SELECT * FROM managers"+(" WHERE id=?" if role=="manager" else "")+" ORDER BY name",(user["manager_id"],) if role=="manager" else ())]); return
                if method == "POST" and role == "admin":
                    cur = con.execute("INSERT INTO managers(name,phone,email,invite_code) VALUES (?,?,?,?)",
                                      (required(body,"name"),required(body,"phone"),required(body,"email").lower(),secrets.token_hex(8).upper()))
                    audit(con,user,"manager",cur.lastrowid,"create",after={"name":body["name"]})
                    self.respond({"id":cur.lastrowid},201); return
            if path == "/api/users" and role == "admin":
                if method == "GET":
                    self.respond([dict(x) for x in con.execute("SELECT id,name,email,role,driver_id,manager_id FROM users ORDER BY name")]); return
                if method == "POST":
                    new_role = required(body,"role")
                    if new_role not in ("admin","manager","driver"): raise ApiError("Perfil inválido.")
                    driver_id = integer(body,"driver_id") if new_role == "driver" else None
                    manager_id = integer(body,"manager_id") if new_role == "manager" else None
                    cur = con.execute("INSERT INTO users(name,email,password_hash,role,driver_id,manager_id) VALUES (?,?,?,?,?,?)",
                                      (required(body,"name"),required(body,"email").lower(),hash_password(required(body,"password")),new_role,driver_id,manager_id))
                    audit(con,user,"user",cur.lastrowid,"create",after={"name":body["name"],"email":body["email"],"role":new_role})
                    self.respond({"id":cur.lastrowid},201); return
            if path == "/api/places":
                if method == "GET":
                    if role=="driver":
                        rows=con.execute("SELECT DISTINCT p.* FROM places p JOIN stops s ON s.place_id=p.id JOIN routes r ON r.id=s.route_id WHERE r.driver_id=? ORDER BY p.address",(user["driver_id"],))
                    else:
                        rows=con.execute("SELECT * FROM places ORDER BY address")
                    self.respond([dict(x) for x in rows]); return
                if method == "POST" and role in ("admin","manager"):
                    cur = con.execute("INSERT INTO places(address,latitude,longitude) VALUES (?,?,?)",
                                      (required(body,"address"),number(body,"latitude",-90,90,True),number(body,"longitude",-180,180,True)))
                    audit(con,user,"place",cur.lastrowid,"create",after=body)
                    self.respond({"id":cur.lastrowid},201); return
            parts=path.strip("/").split("/")
            if len(parts)==3 and parts[:2]==["api","places"] and parts[2].isdigit() and method=="PATCH" and role in ("admin","manager"):
                place_id=int(parts[2]); old=con.execute("SELECT * FROM places WHERE id=?",(place_id,)).fetchone()
                if not old: raise ApiError("Ponto não encontrado.",404)
                updated=(required(body,"address"),number(body,"latitude",-90,90,True),number(body,"longitude",-180,180,True),place_id)
                con.execute("UPDATE places SET address=?,latitude=?,longitude=? WHERE id=?",updated)
                new=row_dict(con.execute("SELECT * FROM places WHERE id=?",(place_id,)).fetchone())
                audit(con,user,"place",place_id,"update",row_dict(old),new)
                self.respond(new); return
            if path == "/api/routes":
                if method == "GET":
                    start,end=period(query)
                    self.respond(period_data(con,user,start,end)["routes"]); return
                if method == "POST" and role in ("admin","manager"):
                    driver_id=integer(body,"driver_id")
                    driver=con.execute("SELECT * FROM drivers WHERE id=?",(driver_id,)).fetchone()
                    if not driver: raise ApiError("Motorista não encontrado.")
                    if role=="manager" and driver["manager_id"]!=user["manager_id"]: raise ApiError("Acesso negado.",403)
                    cur=con.execute("INSERT INTO routes(service_date,driver_id,distance_km,created_at) VALUES (?,?,?,?)",
                                    (service_date(required(body,"service_date")),driver_id,number(body,"distance_km",0),now()))
                    audit(con,user,"route",cur.lastrowid,"create",after=body)
                    self.respond(route_details(con,cur.lastrowid,user),201); return
            if len(parts)>=3 and parts[:2]==["api","routes"] and parts[2].isdigit():
                route_id=int(parts[2]); route=con.execute("SELECT * FROM routes WHERE id=?",(route_id,)).fetchone()
                route_allowed(user,route,con)
                if len(parts)==3 and method=="GET": self.respond(route_details(con,route_id,user)); return
                if len(parts)==3 and method=="PATCH" and role in ("admin","manager"):
                    before=row_dict(route)
                    con.execute("UPDATE routes SET distance_km=? WHERE id=?",(number(body,"distance_km",0),route_id))
                    audit(con,user,"route",route_id,"update",before,row_dict(con.execute("SELECT * FROM routes WHERE id=?",(route_id,)).fetchone()))
                    self.respond(route_details(con,route_id,user)); return
                if len(parts)==4 and parts[3]=="stops" and method=="POST" and role in ("admin","manager"):
                    place_id=integer(body,"place_id")
                    if not con.execute("SELECT 1 FROM places WHERE id=?",(place_id,)).fetchone(): raise ApiError("Ponto não encontrado.")
                    next_pos=con.execute("SELECT COALESCE(MAX(position),0)+1 FROM stops WHERE route_id=?",(route_id,)).fetchone()[0]
                    cur=con.execute("INSERT INTO stops(route_id,place_id,position) VALUES (?,?,?)",(route_id,place_id,next_pos))
                    audit(con,user,"stop",cur.lastrowid,"create",after={"route_id":route_id,"place_id":place_id,"position":next_pos})
                    self.respond(route_details(con,route_id,user),201); return
            if len(parts)==3 and parts[:2]==["api","stops"] and parts[2].isdigit() and method=="PATCH":
                stop_id=int(parts[2]); stop=con.execute("SELECT * FROM stops WHERE id=?",(stop_id,)).fetchone()
                if not stop: raise ApiError("Parada não encontrada.",404)
                route=con.execute("SELECT * FROM routes WHERE id=?",(stop["route_id"],)).fetchone()
                route_allowed(user,route,con)
                if "arrival" not in body and "departure" not in body: raise ApiError("Informe chegada ou saída.")
                arrival=timestamp(body["arrival"]) if "arrival" in body else stop["arrival"]
                departure=timestamp(body["departure"]) if "departure" in body else stop["departure"]
                if departure and not arrival: raise ApiError("Registre a chegada antes da saída.")
                if arrival and departure and departure<arrival: raise ApiError("A saída deve ocorrer após a chegada.")
                if arrival and arrival[:10] != route["service_date"]: raise ApiError("A chegada deve ocorrer na data do roteiro.")
                before=row_dict(stop)
                con.execute("UPDATE stops SET arrival=?,departure=? WHERE id=?",(arrival,departure,stop_id))
                audit(con,user,"stop",stop_id,"update",before,row_dict(con.execute("SELECT * FROM stops WHERE id=?",(stop_id,)).fetchone()))
                self.respond(route_details(con,route["id"],user)); return
            if path in ("/api/dashboard","/api/export") and method=="GET":
                start,end=period(query); data=period_data(con,user,start,end)
                if path=="/api/dashboard": self.respond(data); return
                out=io.StringIO(); writer=csv.writer(out,delimiter=";")
                writer.writerow(["Data","Roteiro","Motorista","Ordem","Endereço","Chegada","Saída","Tempo parado (segundos)"])
                for h in data["history"]:
                    writer.writerow([h[k] for k in ("service_date","route_id","driver_name","position","address","arrival","departure","stopped_seconds")])
                content="\ufeff"+out.getvalue()
                self.respond(content.encode("utf-8"),content_type="text/csv; charset=utf-8"); return
            if path=="/api/audit" and method=="GET" and role=="admin":
                self.respond([dict(x) for x in con.execute("""SELECT a.id,a.at,u.name AS actor,a.entity,a.entity_id,a.action,a.before_json,a.after_json
                    FROM audit a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 200""")]); return
            raise ApiError("Acesso negado ou recurso não encontrado.",403 if role=="driver" else 404)

    def do_GET(self): self.safe("GET")
    def do_POST(self): self.safe("POST")
    def do_PUT(self): self.safe("PUT")
    def do_PATCH(self): self.safe("PATCH")

    def safe(self, method):
        try:
            self.handle_request(method)
        except ApiError as exc:
            self.respond({"error":exc.message},exc.status)
        except sqlite3.IntegrityError:
            self.respond({"error":"Registro duplicado ou referência inválida."},409)
        except (OSError, ValueError) as exc:
            self.respond({"error":"Erro ao processar a solicitação."},500)
            print(f"Server error: {exc}")


if __name__ == "__main__":
    init_db()
    port=int(os.environ.get("PORT","8000"))
    server=ThreadingHTTPServer(("127.0.0.1",port),Handler)
    url=f"http://127.0.0.1:{port}"
    print(f"Parada disponível em {url}")
    if "--open" in sys.argv:
        timer=threading.Timer(0.5, lambda: webbrowser.open(url))
        timer.daemon=True
        timer.start()
    server.serve_forever()
