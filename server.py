import json
import hashlib
import os
import secrets
import threading
import urllib.error
import urllib.request
import uuid
from urllib.parse import unquote
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
DB_DIR = ROOT / "data"
DB_FILE = DB_DIR / "kisanlink.json"
FARMER_DB_FILE = DB_DIR / "farmers.json"
BUYER_DB_FILE = DB_DIR / "buyers.json"
TRANSACTIONS_DB_FILE = DB_DIR / "transactions.json"
LOCK = threading.Lock()
SESSIONS = {}
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
SEED = {
    "lots": [
        {"id": "LOT-1042", "crop": "Tomato", "qty": "5,000 kg", "quality": "Grade A", "offer": "₹27/kg", "status": "Offer received"},
        {"id": "LOT-1038", "crop": "Onion", "qty": "3,000 kg", "quality": "Grade A", "offer": "₹33/kg", "status": "Bidding"},
        {"id": "LOT-1021", "crop": "Soybean", "qty": "8,000 kg", "quality": "FAQ", "offer": "₹51/kg", "status": "Sold"},
    ],
    "transactions": [
        ["TXN-1002", "GreenHarvest Foods", "₹1,35,000", "Pending", "Pickup scheduled", "Today"],
        ["TXN-0998", "CityMart Institutions", "₹98,000", "Paid ✓", "Delivered", "18 Aug"],
    ],
    "bids": [], "assays": [], "grievances": [], "fpoLots": [], "nwrRequests": [],
    "audit": [],
    "markets": [
        {"market": "Nagpur APMC", "crop": "Tomato", "price": 25, "distance": 15, "arrival": 120, "trend": 4.8, "quality": "Grade A/B"},
        {"market": "Kamptee Market", "crop": "Tomato", "price": 23, "distance": 25, "arrival": 85, "trend": 2.2, "quality": "Grade A/B"},
        {"market": "Wardha APMC", "crop": "Tomato", "price": 27, "distance": 70, "arrival": 62, "trend": 6.4, "quality": "Grade A"},
        {"market": "Nagpur APMC", "crop": "Onion", "price": 31, "distance": 15, "arrival": 210, "trend": -1.3, "quality": "Grade A/B"},
        {"market": "Katol Market", "crop": "Onion", "price": 34, "distance": 48, "arrival": 95, "trend": 3.8, "quality": "Grade A"},
        {"market": "Hingna Market", "crop": "Soybean", "price": 48, "distance": 24, "arrival": 75, "trend": 5.1, "quality": "FAQ"},
    ],
    "buyers": [
        {"name": "GreenHarvest Foods", "type": "Processor", "crop": "Tomato", "price": 27, "qty": "5,000 kg", "distance": 62, "reliability": 96, "quality": "Grade A", "payment": "2 days"},
        {"name": "FreshBasket Retail", "type": "Retailer", "crop": "Tomato", "price": 26, "qty": "3,000 kg", "distance": 35, "reliability": 93, "quality": "Grade A", "payment": "3 days"},
        {"name": "CityMart Institutions", "type": "Institutional", "crop": "Onion", "price": 33, "qty": "7,000 kg", "distance": 42, "reliability": 98, "quality": "Grade A", "payment": "1 day"},
    ],
    "profile": {"name": "Vansh Thakre", "accountType": "Individual Farmer", "district": "Nagpur", "state": "Maharashtra", "crops": "Tomato, Onion, Soybean"},
    "users": [
        {"id": "USR-FARMER", "name": "Vansh Thakre", "email": "farmer@kisanlink.local", "password": "", "role": "farmer"},
        {"id": "USR-ADMIN", "name": "KisanLink Admin", "email": "admin@kisanlink.local", "password": "", "role": "admin"},
    ],
}


def password_hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def ensure_users(db):
    if not db.get("users"):
        db["users"] = SEED["users"]
    for user, password in zip(db["users"], ("farmer123", "admin123")):
        if not user.get("password"):
            user["password"] = password_hash(password)


def load_db():
    DB_DIR.mkdir(exist_ok=True)
    if not DB_FILE.exists():
        DB_FILE.write_text(json.dumps(SEED, ensure_ascii=False, indent=2), encoding="utf-8")
    db = json.loads(DB_FILE.read_text(encoding="utf-8"))
    had_users = bool(db.get("users"))
    ensure_users(db)
    changed = not had_users
    for key in ("markets", "buyers"):
        if key not in db:
            db[key] = SEED[key]
            changed = True
    if FARMER_DB_FILE.exists():
        farmer_data = json.loads(FARMER_DB_FILE.read_text(encoding="utf-8"))
        db["lots"] = farmer_data.get("lots", db.get("lots", []))
        db["profile"] = farmer_data.get("profile", db.get("profile", {}))
        db["farmerUsers"] = farmer_data.get("users", [user for user in db.get("users", []) if user.get("role") == "farmer"])
    else:
        changed = True
    if BUYER_DB_FILE.exists():
        buyer_data = json.loads(BUYER_DB_FILE.read_text(encoding="utf-8"))
        db["buyers"] = buyer_data.get("buyers", db.get("buyers", []))
        db["buyerUsers"] = buyer_data.get("users", [user for user in db.get("users", []) if user.get("role") == "buyer"])
    else:
        changed = True
    if TRANSACTIONS_DB_FILE.exists():
        transaction_data = json.loads(TRANSACTIONS_DB_FILE.read_text(encoding="utf-8"))
        db["transactions"] = transaction_data.get("transactions", db.get("transactions", []))
    else:
        changed = True
    if changed:
        save_db(db)
    return db


def save_db(db):
    DB_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    farmer_users = db.get("farmerUsers", [user for user in db.get("users", []) if user.get("role") == "farmer"])
    buyer_users = db.get("buyerUsers", [user for user in db.get("users", []) if user.get("role") == "buyer"])
    FARMER_DB_FILE.write_text(json.dumps({"users": farmer_users, "profile": db.get("profile", {}), "lots": db.get("lots", []), "assays": db.get("assays", []), "fpoLots": db.get("fpoLots", [])}, ensure_ascii=False, indent=2), encoding="utf-8")
    BUYER_DB_FILE.write_text(json.dumps({"users": buyer_users, "buyers": db.get("buyers", []), "bids": db.get("bids", [])}, ensure_ascii=False, indent=2), encoding="utf-8")
    TRANSACTIONS_DB_FILE.write_text(json.dumps({"transactions": db.get("transactions", []), "nwrRequests": db.get("nwrRequests", [])}, ensure_ascii=False, indent=2), encoding="utf-8")


def make_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def audit(db, user, action, resource, resource_id=""):
    db.setdefault("audit", []).insert(0, {"id": make_id("AUD"), "userId": user.get("id"), "action": action, "resource": resource, "resourceId": resource_id, "createdAt": datetime.now().isoformat()})


def find_record(records, record_id):
    return next((record for record in records if record.get("id") == record_id), None) if records and isinstance(records[0], dict) else None


def ai_reply(message, db, history=None):
    context = json.dumps({"lots": db.get("lots", [])[:8], "transactions": db.get("transactions", [])[:8], "grievances": db.get("grievances", [])[:5]}, ensure_ascii=False)
    history = history or []
    prompt = f"You are KisanLink Assistant for Indian farmers. Answer simply and practically. Use this current signed-in user's data, never invent prices or payment status, and say when data is unavailable or demo data. Current data: {context}"
    if GEMINI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        contents = [{"role": item.get("role", "user"), "parts": [{"text": str(item.get("text", ""))}]} for item in history[-8:]]
        contents.append({"role": "user", "parts": [{"text": f"{prompt}\nUser question: {message}"}]})
        payload = json.dumps({"contents": contents, "generationConfig": {"temperature": 0.3, "maxOutputTokens": 500}}).encode("utf-8")
        request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
                text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                if text:
                    return text, "gemini"
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError):
            pass
    lowered = message.lower()
    previous = " ".join(str(item.get("text", "")) for item in history).lower()
    if "lot" in previous and any(word in lowered for word in ("what", "which", "how", "them", "those", "next")):
        return "Review each lot's crop, quantity, quality, offer, and status in My Lots. Publish lots marked Published, compare offers for Offer received, and use Live Bidding for lots marked Bidding.", "local"
    if "lot" in lowered:
        return f"You currently have {len(db.get('lots', []))} produce lots. Open My Lots to create, review, or publish a lot.", "local"
    if "price" in lowered or "market" in lowered:
        return "Open Market Prices to compare nearby mandi rates. Prices shown in this local installation are marketplace reference data.", "local"
    if "transaction" in lowered or "payment" in lowered:
        return f"Your account has {len(db.get('transactions', []))} transaction records. Open Transactions to review payment and delivery status.", "local"
    return "I can help with market prices, buyers, lots, quality checks, bidding, logistics, transactions, and grievances. Ask me about one of these.", "local"


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, body):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def current_user(self):
        cookie = self.headers.get("Cookie", "")
        token = next((item.split("=", 1)[1] for item in cookie.split("; ") if item.startswith("kl_session=")), None)
        return SESSIONS.get(token)

    def require_user(self):
        user = self.current_user()
        if not user:
            self.send_json(401, {"error": "Login required"})
        return user

    def require_admin(self):
        user = self.require_user()
        if user and user.get("role") != "admin":
            self.send_json(403, {"error": "Administrator access required"})
            return None
        return user

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path == "/api/health":
            return self.send_json(200, {"status": "ok", "service": "kisanlink", "time": datetime.now().isoformat()})
        resource_keys = {"/api/markets": "markets", "/api/buyers": "buyers", "/api/lots": "lots", "/api/transactions": "transactions", "/api/bids": "bids", "/api/assays": "assays", "/api/grievances": "grievances"}
        if path in resource_keys or path in ("/api/admin/overview", "/api/admin/data", "/api/admin/audit", "/api/admin/users"):
            user = self.require_user()
            if not user:
                return
            with LOCK:
                db = load_db()
                if path == "/api/admin/overview":
                    if user.get("role") != "admin":
                        return self.send_json(403, {"error": "Administrator access required"})
                    return self.send_json(200, {"users": len(db.get("users", [])), "lots": len(db.get("lots", [])), "transactions": len(db.get("transactions", [])), "bids": len(db.get("bids", [])), "grievances": len(db.get("grievances", [])), "recentLots": db.get("lots", [])[:10], "recentGrievances": db.get("grievances", [])[:10]})
                if path == "/api/admin/data":
                    if user.get("role") != "admin":
                        return self.send_json(403, {"error": "Administrator access required"})
                    users = [{key: value for key, value in item.items() if key != "password"} for item in db.get("users", [])]
                    return self.send_json(200, {"users": users, "lots": db.get("lots", []), "transactions": db.get("transactions", []), "bids": db.get("bids", []), "assays": db.get("assays", []), "grievances": db.get("grievances", []), "fpoLots": db.get("fpoLots", []), "nwrRequests": db.get("nwrRequests", [])})
                if path == "/api/admin/audit":
                    if user.get("role") != "admin":
                        return self.send_json(403, {"error": "Administrator access required"})
                    return self.send_json(200, db.get("audit", [])[:100])
                if path == "/api/admin/users":
                    if user.get("role") != "admin":
                        return self.send_json(403, {"error": "Administrator access required"})
                    return self.send_json(200, [{key: value for key, value in item.items() if key != "password"} for item in db.get("users", [])])
                return self.send_json(200, db.get(resource_keys[path], []))
        if path == "/api/me":
            user = self.current_user()
            return self.send_json(200, {"authenticated": bool(user), "user": user})
        if path == "/api/state":
            user = self.require_user()
            if not user:
                return
            with LOCK:
                db = load_db()
                return self.send_json(200, {**db, "user": user, "users": None})
        if path in ("/", "/index.html"):
            raw = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            return self.wfile.write(raw)
        user = self.require_user()
        if not user:
            return
        with LOCK:
            db = load_db()
            if path == "/api/markets":
                return self.send_json(200, db.get("markets", []))
            if path == "/api/buyers":
                return self.send_json(200, db.get("buyers", []))
            if path == "/api/lots":
                return self.send_json(200, db.get("lots", []))
            if path == "/api/transactions":
                return self.send_json(200, db.get("transactions", []))
            if path == "/api/bids":
                return self.send_json(200, db.get("bids", []))
            if path == "/api/assays":
                return self.send_json(200, db.get("assays", []))
            if path == "/api/grievances":
                return self.send_json(200, db.get("grievances", []))
            if path == "/api/admin/overview":
                if user.get("role") != "admin":
                    return self.send_json(403, {"error": "Administrator access required"})
                return self.send_json(200, {"users": len(db.get("users", [])), "lots": len(db.get("lots", [])), "transactions": len(db.get("transactions", [])), "bids": len(db.get("bids", [])), "grievances": len(db.get("grievances", [])), "recentLots": db.get("lots", [])[:10], "recentGrievances": db.get("grievances", [])[:10]})
        self.send_error(404, "Not found")

    def do_POST(self):
        try:
            data = self.read_json()
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"error": "Invalid JSON request"})
        if self.path == "/api/register":
            with LOCK:
                db = load_db()
                name = str(data.get("name", "")).strip()
                email = str(data.get("email", "")).strip().lower()
                password = str(data.get("password", "")).strip()
                if len(name) < 2:
                    return self.send_json(400, {"error": "Enter your full name"})
                if "@" not in email or "." not in email:
                    return self.send_json(400, {"error": "Enter a valid email address"})
                if len(password) < 6:
                    return self.send_json(400, {"error": "Password must be at least 6 characters"})
                if any(item["email"].lower() == email for item in db["users"]):
                    return self.send_json(409, {"error": "An account with this email already exists"})
                role = str(data.get("role", "farmer")).strip().lower()
                if role not in ("farmer", "buyer"):
                    return self.send_json(400, {"error": "Public registration is available for farmers and buyers"})
                user = {"id": make_id("USR"), "name": name, "email": email, "password": password_hash(password), "role": role}
                db["users"].append(user)
                save_db(db)
                public_user = {key: value for key, value in user.items() if key != "password"}
                token = secrets.token_urlsafe(32)
                SESSIONS[token] = public_user
                body = json.dumps({"user": public_user}).encode("utf-8")
                self.send_response(201)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Set-Cookie", f"kl_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=86400")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                return self.wfile.write(body)
        if self.path == "/api/login":
            with LOCK:
                db = load_db()
                email = str(data.get("email", "")).strip().lower()
                password = str(data.get("password", "")).strip()
                requested_role = str(data.get("role", "")).strip().lower()
                user = next((item for item in db["users"] if item["email"].strip().lower() == email and (not requested_role or item.get("role") == requested_role) and secrets.compare_digest(item["password"], password_hash(password))), None)
                if not user:
                    return self.send_json(401, {"error": "Invalid email or password"})
                public_user = {key: value for key, value in user.items() if key != "password"}
                token = secrets.token_urlsafe(32)
                SESSIONS[token] = public_user
                body = json.dumps({"user": public_user}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Set-Cookie", f"kl_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=86400")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                return self.wfile.write(body)
        if self.path == "/api/logout":
            user = self.current_user()
            if user:
                cookie = self.headers.get("Cookie", "")
                token = next((item.split("=", 1)[1] for item in cookie.split("; ") if item.startswith("kl_session=")), None)
                SESSIONS.pop(token, None)
            self.send_response(200)
            self.send_header("Set-Cookie", "kl_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0")
            self.end_headers()
            return
        if self.path == "/api/search":
            user = self.require_user()
            if not user:
                return
            query = str(data.get("query", "")).strip().lower()
            with LOCK:
                db = load_db()
                result = {key: [item for item in db.get(key, []) if query in json.dumps(item, ensure_ascii=False).lower()] for key in ("markets", "buyers", "lots")}
                return self.send_json(200, result)
        user = self.require_user()
        if not user:
            return
        with LOCK:
            db = load_db()
            path = self.path
            if path == "/api/chat":
                if not str(data.get("message", "")).strip():
                    return self.send_json(400, {"error": "message is required"})
                reply, provider = ai_reply(str(data["message"]).strip(), db, data.get("history"))
                return self.send_json(200, {"reply": reply, "provider": provider})
            if path == "/api/lots":
                lot = {"id": make_id("LOT"), "crop": data.get("crop"), "qty": f"{int(data.get('qty', 0)):,} kg", "quality": data.get("quality"), "offer": "Awaiting", "status": "Published"}
                if not lot["crop"] or not data.get("qty") or not lot["quality"]:
                    return self.send_json(400, {"error": "crop, qty and quality are required"})
                db["lots"].insert(0, lot)
                save_db(db)
                return self.send_json(201, lot)
            if path == "/api/transactions":
                txn = [make_id("TXN"), data.get("buyer", "Verified Buyer"), data.get("amount", "₹0"), "Pending", "Pickup scheduled", "Today"]
                db["transactions"].insert(0, txn); save_db(db); return self.send_json(201, txn)
            if path == "/api/bids":
                bid = {"id": make_id("BID"), "lotId": data.get("lotId", "LOT-1042"), "amount": data.get("amount"), "createdAt": datetime.now().isoformat()}
                db["bids"].insert(0, bid); save_db(db); return self.send_json(201, bid)
            if path == "/api/assays":
                assay = {"id": make_id("ASSAY"), "lotId": data.get("lotId"), "crop": data.get("crop"), "grade": "A", "confidence": 91, "damage": 2, "notes": data.get("notes", "")}
                db["assays"].insert(0, assay); save_db(db); return self.send_json(201, assay)
            if path == "/api/grievances":
                grievance = {"id": make_id("GRV"), "reference": data.get("reference"), "type": data.get("type"), "description": data.get("description"), "evidence": data.get("evidence", "No attachment"), "status": "SUBMITTED"}
                db["grievances"].insert(0, grievance); save_db(db); return self.send_json(201, grievance)
            if path in ("/api/fpo-lots", "/api/nwr"):
                key = "fpoLots" if path.endswith("fpo-lots") else "nwrRequests"
                record = {"id": make_id("FPO-LOT" if key == "fpoLots" else "NWR"), "lotId": data.get("lotId", "LOT-1042"), "status": "REQUESTED"}
                db[key].insert(0, record)
                if key == "fpoLots": db["lots"].insert(0, {**record, "crop": "Tomato", "qty": "5,000 kg", "quality": "Grade A", "offer": "Awaiting", "status": "Aggregation open"})
                save_db(db); return self.send_json(201, record)
            return self.send_json(404, {"error": "API route not found"})

    def do_PUT(self):
        user = self.require_user()
        if not user:
            return
        path_parts = [unquote(part) for part in self.path.strip("/").split("/")]
        if user.get("role") == "admin" and len(path_parts) == 4 and path_parts[:2] == ["api", "admin"]:
            resource, record_id = path_parts[2], path_parts[3]
            data = self.read_json()
            with LOCK:
                db = load_db()
                if resource == "users":
                    record = next((item for item in db.get("users", []) if item.get("id") == record_id), None)
                    allowed = {"name", "email", "role"}
                elif resource in ("lots", "grievances"):
                    record = find_record(db.get(resource, []), record_id)
                    allowed = {"status", "offer", "quality", "description"}
                else:
                    return self.send_json(404, {"error": "Resource not editable"})
                if not record:
                    return self.send_json(404, {"error": "Record not found"})
                record.update({key: value for key, value in data.items() if key in allowed})
                audit(db, user, "update", resource, record_id)
                save_db(db)
                return self.send_json(200, {key: value for key, value in record.items() if key != "password"})
        if self.path != "/api/profile":
            return self.send_json(404, {"error": "API route not found"})
        data = self.read_json()
        with LOCK:
            db = load_db(); db["profile"].update(data); save_db(db); return self.send_json(200, db["profile"])

    def do_DELETE(self):
        user = self.require_admin()
        if not user:
            return
        path_parts = [unquote(part) for part in self.path.strip("/").split("/")]
        if len(path_parts) != 4 or path_parts[0:2] != ["api", "admin"]:
            return self.send_json(404, {"error": "Delete route not found"})
        resource, record_id = path_parts[2], path_parts[3]
        if resource not in ("users", "lots", "grievances"):
            return self.send_json(404, {"error": "Resource not deletable"})
        with LOCK:
            db = load_db()
            records = db.get(resource, [])
            original = len(records)
            db[resource] = [item for item in records if item.get("id") != record_id]
            if len(db[resource]) == original:
                return self.send_json(404, {"error": "Record not found"})
            audit(db, user, "delete", resource, record_id)
            save_db(db)
            return self.send_json(200, {"deleted": record_id, "resource": resource})

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    with LOCK:
        load_db()
    print(f"KisanLink running at http://localhost:{port}")
    ThreadingHTTPServer(("", port), Handler).serve_forever()
