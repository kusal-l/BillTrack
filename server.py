import os
import sys
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_FILE = os.path.join(os.path.dirname(__file__), 'database.db')
STATIC_INDEX = os.path.join(os.path.dirname(__file__), 'index.html')

# In-memory active sessions: token -> username
ACTIVE_SESSIONS = {}

# ── Database Management ──

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS sales_bills (
            id TEXT PRIMARY KEY,
            billno TEXT NOT NULL,
            date TEXT NOT NULL,
            shop TEXT NOT NULL,
            area TEXT NOT NULL,
            total REAL NOT NULL,
            paid REAL NOT NULL,
            status TEXT NOT NULL,
            paydate TEXT,
            mode TEXT,
            cheque TEXT,
            photo TEXT,
            notes TEXT,
            createdAt TEXT,
            updatedAt TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchase_bills (
            id TEXT PRIMARY KEY,
            billno TEXT NOT NULL,
            date TEXT NOT NULL,
            factory TEXT NOT NULL,
            amount REAL NOT NULL,
            photo TEXT,
            notes TEXT,
            createdAt TEXT,
            updatedAt TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS areas (
            name TEXT PRIMARY KEY NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS factories (
            name TEXT PRIMARY KEY NOT NULL
        )
    ''')
    
    c.execute('SELECT COUNT(*) FROM factories')
    if c.fetchone()[0] == 0:
        c.executemany('INSERT INTO factories (name) VALUES (?)', [
            ('Wealth',), ('Teema',), ('Hewage',), ('Ananda',)
        ])
        
    # Table schema migrations
    c.execute("PRAGMA table_info(sales_bills)")
    columns = [r[1] for r in c.fetchall()]
    if 'payments' not in columns:
        c.execute("ALTER TABLE sales_bills ADD COLUMN payments TEXT DEFAULT '[]'")
        
    conn.commit()
    conn.close()

# ── Password Hashing ──

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_bytes(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ":" + pwd_hash.hex()

def verify_password(stored_password_hash, input_password):
    try:
        salt_hex, hash_hex = stored_password_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', input_password.encode('utf-8'), salt, 100000)
        return pwd_hash.hex() == hash_hex
    except Exception:
        return False

# ── Request Handler ──

class BillTrackHandler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_json(self, message, status=400):
        self.send_json({"error": message}, status)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def get_user_from_request(self):
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
            if token in ACTIVE_SESSIONS:
                return ACTIVE_SESSIONS[token]
        return None

    def read_json_body(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            return json.loads(body.decode('utf-8'))
        except Exception:
            return None

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # 1. Serve Static Frontend
        if path == '/' or path == '/index.html':
            if os.path.exists(STATIC_INDEX):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(STATIC_INDEX, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"index.html not found.")
            return

        # Serve static uploads
        if path.startswith('/uploads/'):
            filename = os.path.basename(path)
            uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
            local_path = os.path.join(uploads_dir, filename)
            # Safe check to prevent path traversal
            if os.path.commonpath([uploads_dir]) == os.path.commonpath([uploads_dir, local_path]) and os.path.exists(local_path):
                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.end_headers()
                with open(local_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"File not found.")
            return

        # 2. Public API: Auth Status (Checks if setup is required)
        if path == '/api/auth/status':
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM users')
            user_count = c.fetchone()[0]
            conn.close()

            setup_required = (user_count == 0)
            user = self.get_user_from_request()
            self.send_json({
                "setupRequired": setup_required,
                "loggedIn": user is not None,
                "username": user
            })
            return

        # Secure APIs (Require Authentication)
        user = self.get_user_from_request()
        if not user:
            self.send_error_json("Unauthorized access", 401)
            return

        # 3. GET /api/sales - List sales bills
        if path == '/api/sales':
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM sales_bills')
            rows = c.fetchall()
            bills = [dict(r) for r in rows]
            conn.close()
            self.send_json(bills)
            return

        # 4. GET /api/purchases - List purchase bills
        if path == '/api/purchases':
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM purchase_bills')
            rows = c.fetchall()
            bills = [dict(r) for r in rows]
            conn.close()
            self.send_json(bills)
            return

        # 5. GET /api/areas - List areas
        if path == '/api/areas':
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT name FROM areas')
            areas = [r[0] for r in c.fetchall()]
            conn.close()
            self.send_json(areas)
            return

        # 6. GET /api/factories - List factories
        if path == '/api/factories':
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT name FROM factories')
            factories = [r[0] for r in c.fetchall()]
            conn.close()
            self.send_json(factories)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # 1. Handle file upload (before JSON parsing)
        if path == '/api/upload':
            user = self.get_user_from_request()
            if not user:
                self.send_error_json("Unauthorized access", 401)
                return
            
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_error_json("Content-Type must be multipart/form-data")
                return
            
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 3.5 * 1024 * 1024:
                self.send_error_json("File size exceeds 3MB limit", 413)
                return
                
            body = self.rfile.read(content_length)
            
            try:
                boundary = content_type.split("boundary=")[1].encode('utf-8')
            except IndexError:
                self.send_error_json("Invalid multipart boundary")
                return
                
            parts = body.split(b'--' + boundary)
            file_data = None
            filename = None
            
            for part in parts:
                if b'filename="' in part:
                    parts_split = part.split(b'\r\n\r\n', 1)
                    if len(parts_split) < 2:
                        continue
                    part_headers, part_body = parts_split
                    if part_body.endswith(b'\r\n'):
                        part_body = part_body[:-2]
                    if part_body.endswith(b'--'):
                        pass
                        
                    import re
                    fn_match = re.search(rb'filename="([^"]+)"', part_headers)
                    if fn_match:
                        filename = fn_match.group(1).decode('utf-8', errors='ignore')
                        filename = os.path.basename(filename)
                    file_data = part_body
                    break
            
            if not file_data or not filename:
                self.send_error_json("No file uploaded")
                return
                
            if len(file_data) > 3 * 1024 * 1024:
                self.send_error_json("Uploaded PDF exceeds 3MB limit")
                return
                
            if not filename.lower().endswith('.pdf'):
                self.send_error_json("Only PDF files are allowed")
                return
                
            uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            
            unique_filename = f"{secrets.token_hex(8)}_{filename}"
            save_path = os.path.join(uploads_dir, unique_filename)
            with open(save_path, 'wb') as f:
                f.write(file_data)
                
            file_url = f"/uploads/{unique_filename}"
            self.send_json({"success": True, "fileUrl": file_url})
            return

        body = self.read_json_body()

        # 1. POST /api/auth/setup
        if path == '/api/auth/setup':
            if not body or 'username' not in body or 'password' not in body:
                self.send_error_json("Missing username or password")
                return
            username = body['username'].strip()
            password = body['password']
            if not username or not password:
                self.send_error_json("Username and password cannot be empty")
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM users')
            if c.fetchone()[0] > 0:
                conn.close()
                self.send_error_json("Setup already completed")
                return
            
            pwd_hash = hash_password(password)
            try:
                c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, pwd_hash))
                conn.commit()
            except Exception as e:
                conn.close()
                self.send_error_json(f"Error creating user: {str(e)}")
                return
            conn.close()
            self.send_json({"success": True, "message": "Admin user created successfully"})
            return

        # 2. POST /api/auth/login
        if path == '/api/auth/login':
            if not body or 'username' not in body or 'password' not in body:
                self.send_error_json("Missing credentials")
                return
            username = body['username'].strip()
            password = body['password']

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
            row = c.fetchone()
            conn.close()

            if row and verify_password(row[0], password):
                token = secrets.token_hex(32)
                ACTIVE_SESSIONS[token] = username
                self.send_json({
                    "success": True,
                    "token": token,
                    "username": username
                })
            else:
                self.send_error_json("Invalid username or password", 401)
            return

        # Secure APIs (Require Authentication)
        user = self.get_user_from_request()
        if not user:
            self.send_error_json("Unauthorized access", 401)
            return

        # 2.5 POST /api/auth/change-password
        if path == '/api/auth/change-password':
            if not body or 'currentPassword' not in body or 'newPassword' not in body:
                self.send_error_json("Missing current or new password")
                return
            
            current_pwd = body['currentPassword']
            new_pwd = body['newPassword']
            
            if not new_pwd or len(new_pwd) < 6:
                self.send_error_json("New password must be at least 6 characters")
                return
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT password_hash FROM users WHERE username = ?', (user,))
            row = c.fetchone()
            
            if not row or not verify_password(row[0], current_pwd):
                conn.close()
                self.send_error_json("Current password is incorrect", 400)
                return
            
            new_hash = hash_password(new_pwd)
            c.execute('UPDATE users SET password_hash = ? WHERE username = ?', (new_hash, user))
            conn.commit()
            conn.close()
            
            self.send_json({"success": True, "message": "Password changed successfully"})
            return

        # 3. POST /api/sales - Create/update sales bill
        if path == '/api/sales':
            if not body or 'billno' not in body or 'total' not in body:
                self.send_error_json("Missing required fields")
                return
            
            id = body.get('id') or secrets.token_hex(8)
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT createdAt FROM sales_bills WHERE id = ?', (id,))
            exists = c.fetchone()
            
            created_at = exists[0] if exists else now
            
            # Read payments JSON field
            payments = body.get('payments', '[]')
            if not isinstance(payments, str):
                payments = json.dumps(payments)
            
            c.execute('''
                INSERT OR REPLACE INTO sales_bills 
                (id, billno, date, shop, area, total, paid, status, paydate, mode, cheque, photo, notes, payments, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                id, body['billno'], body['date'], body['shop'], body['area'],
                float(body['total']), float(body['paid']), body['status'],
                body.get('paydate', ''), body.get('mode', ''), body.get('cheque', ''),
                body.get('photo', ''), body.get('notes', ''), payments, created_at, now
            ))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "id": id})
            return

        # 4. POST /api/purchases - Create/update purchase bill
        if path == '/api/purchases':
            if not body or 'billno' not in body or 'amount' not in body:
                self.send_error_json("Missing required fields")
                return
            
            id = body.get('id') or secrets.token_hex(8)
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('SELECT createdAt FROM purchase_bills WHERE id = ?', (id,))
            exists = c.fetchone()
            
            created_at = exists[0] if exists else now
            
            c.execute('''
                INSERT OR REPLACE INTO purchase_bills 
                (id, billno, date, factory, amount, photo, notes, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                id, body['billno'], body['date'], body['factory'],
                float(body['amount']), body.get('photo', ''), body.get('notes', ''),
                created_at, now
            ))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "id": id})
            return

        # 5. POST /api/areas - Create new area
        if path == '/api/areas':
            if not body or 'name' not in body:
                self.send_error_json("Missing area name")
                return
            name = body['name'].strip()
            if not name:
                self.send_error_json("Area name cannot be empty")
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            try:
                c.execute('INSERT INTO areas (name) VALUES (?)', (name,))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close()
                self.send_error_json("Area already exists")
                return
            conn.close()
            self.send_json({"success": True})
            return

        # 6. POST /api/factories - Create new factory
        if path == '/api/factories':
            if not body or 'name' not in body:
                self.send_error_json("Missing factory name")
                return
            name = body['name'].strip()
            if not name:
                self.send_error_json("Factory name cannot be empty")
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            try:
                c.execute('INSERT INTO factories (name) VALUES (?)', (name,))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close()
                self.send_error_json("Factory already exists")
                return
            conn.close()
            self.send_json({"success": True})
            return

        self.send_response(444)
        self.end_headers()

    def do_DELETE(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        user = self.get_user_from_request()
        if not user:
            self.send_error_json("Unauthorized access", 401)
            return

        # 1. DELETE /api/sales/<id>
        if path.startswith('/api/sales/'):
            id = path[len('/api/sales/'):]
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('DELETE FROM sales_bills WHERE id = ?', (id,))
            conn.commit()
            conn.close()
            self.send_json({"success": True})
            return

        # 2. DELETE /api/purchases/<id>
        if path.startswith('/api/purchases/'):
            id = path[len('/api/purchases/'):]
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('DELETE FROM purchase_bills WHERE id = ?', (id,))
            conn.commit()
            conn.close()
            self.send_json({"success": True})
            return

        # 3. DELETE /api/areas/<name>
        if path.startswith('/api/areas/'):
            import urllib.parse
            name = urllib.parse.unquote(path[len('/api/areas/'):])
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('DELETE FROM areas WHERE name = ?', (name,))
            conn.commit()
            conn.close()
            self.send_json({"success": True})
            return

        # 4. DELETE /api/factories/<name>
        if path.startswith('/api/factories/'):
            import urllib.parse
            name = urllib.parse.unquote(path[len('/api/factories/'):])
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('DELETE FROM factories WHERE name = ?', (name,))
            conn.commit()
            conn.close()
            self.send_json({"success": True})
            return

        self.send_response(444)
        self.end_headers()


def run_server(port=3000):
    init_db()
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, BillTrackHandler)
    print(f"BillTrack Server started on http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == '__main__':
    if '--reset-password' in sys.argv or 'reset' in sys.argv:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('DELETE FROM users')
        conn.commit()
        conn.close()
        print("✓ User credentials have been reset! Launch BillTrack to create your new username and password.")
        sys.exit(0)

    port = 3000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
