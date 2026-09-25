import os
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None

BASE_DIR = Path(__file__).resolve().parent
IS_VERCEL = bool(os.environ.get("VERCEL"))
DB_PATH = Path("/tmp/vape_guard.db") if IS_VERCEL else BASE_DIR / "vape_guard.db"
DATABASE_URL = os.environ.get("DATABASE_URL")

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "vape-guard-demo-secret-key")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

INITIAL_PRODUCTS = [
    {
        "serial": "VAPE-2024-ALPHA",
        "name": "Nova Pod X",
        "batch": "B-1048",
        "manufacturer": "VaporPrime Labs",
    },
    {
        "serial": "VAPE-2024-BETA",
        "name": "Aero Mint 20",
        "batch": "M-1487",
        "manufacturer": "AeroLeaf",
    },
    {
        "serial": "VAPE-2024-GAMMA",
        "name": "CloudWave Plus",
        "batch": "C-1182",
        "manufacturer": "CloudWave",
    },
]


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        if DATABASE_URL and psycopg2 is not None:
            db = psycopg2.connect(DATABASE_URL)
            db.row_factory = None
        else:
            db = sqlite3.connect(DB_PATH)
            db.row_factory = sqlite3.Row
        g._database = db
    return db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("_database", None)
    if db is not None:
        db.close()


def init_db():
    if DATABASE_URL and psycopg2 is not None:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    serial TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    batch TEXT NOT NULL,
                    manufacturer TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS verification_logs (
                    id SERIAL PRIMARY KEY,
                    product_serial TEXT,
                    age INTEGER,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
                """
            )
            cur.execute(
                "INSERT INTO admin_users (username, password) VALUES (%s, %s) ON CONFLICT (username) DO NOTHING",
                (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD)),
            )
            for product in INITIAL_PRODUCTS:
                cur.execute(
                    "INSERT INTO products (serial, name, batch, manufacturer) VALUES (%s, %s, %s, %s) ON CONFLICT (serial) DO NOTHING",
                    (product["serial"], product["name"], product["batch"], product["manufacturer"]),
                )
        conn.commit()
        conn.close()
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                batch TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS verification_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_serial TEXT,
                age INTEGER,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
            """
        )

        conn.execute(
            "INSERT OR IGNORE INTO admin_users (username, password) VALUES (?, ?)",
            (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD)),
        )

        for product in INITIAL_PRODUCTS:
            conn.execute(
                "INSERT OR IGNORE INTO products (serial, name, batch, manufacturer) VALUES (?, ?, ?, ?)",
                (
                    product["serial"],
                    product["name"],
                    product["batch"],
                    product["manufacturer"],
                ),
            )
        conn.commit()


init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = get_db().execute(
            "SELECT username, password FROM admin_users WHERE username = ?",
            (username,),
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session["admin_logged_in"] = True
            session["admin_username"] = username
            return redirect(url_for("admin_dashboard"))

        return render_template("login.html", error="Username atau password salah.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_username", None)
    return redirect(url_for("login"))


@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    return render_template("admin.html", username=session.get("admin_username", "admin"))


@app.route("/api/products")
def get_products():
    rows = get_db().execute(
        "SELECT serial, name, batch, manufacturer, created_at FROM products ORDER BY id DESC"
    ).fetchall()
    return jsonify({"products": [dict(row) for row in rows]})


@app.route("/api/admin/products", methods=["POST"])
def add_product():
    if not session.get("admin_logged_in"):
        return jsonify({"success": False, "message": "Anda harus login sebagai admin."}), 401

    payload = request.get_json(silent=True) or {}
    serial = (payload.get("serial") or "").strip().upper()
    name = (payload.get("name") or "").strip()
    batch = (payload.get("batch") or "").strip()
    manufacturer = (payload.get("manufacturer") or "").strip()

    if not all([serial, name, batch, manufacturer]):
        return jsonify({"success": False, "message": "Semua field produk harus diisi."}), 400

    try:
        get_db().execute(
            "INSERT INTO products (serial, name, batch, manufacturer) VALUES (?, ?, ?, ?)",
            (serial, name, batch, manufacturer),
        )
        get_db().commit()
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Serial produk sudah terdaftar."}), 409

    return jsonify({"success": True, "message": "Produk baru berhasil ditambahkan."})


@app.route("/api/admin/logs")
def get_logs():
    rows = get_db().execute(
        "SELECT id, product_serial, age, status, created_at FROM verification_logs ORDER BY id DESC LIMIT 20"
    ).fetchall()
    return jsonify({"logs": [dict(row) for row in rows]})


@app.route("/api/verify-product", methods=["POST"])
def verify_product():
    payload = request.get_json(silent=True) or {}
    serial = (payload.get("serial") or "").strip().upper()

    if not serial:
        return jsonify({"valid": False, "message": "Nomor seri wajib diisi."}), 400

    product = get_db().execute(
        "SELECT serial, name, batch, manufacturer FROM products WHERE serial = ?",
        (serial,),
    ).fetchone()

    if product is None:
        return jsonify(
            {
                "valid": False,
                "message": "Seri produk tidak terdaftar atau kemungkinan palsu.",
            }
        )

    return jsonify(
        {
            "valid": True,
            "message": "Produk terdaftar resmi dan aman untuk dipasarkan.",
            "product": {
                "name": product["name"],
                "batch": product["batch"],
                "manufacturer": product["manufacturer"],
                "serial": product["serial"],
            },
        }
    )


@app.route("/api/verify-age", methods=["POST"])
def verify_age():
    payload = request.get_json(silent=True) or {}
    age = payload.get("age")

    try:
        age_value = int(age)
    except (TypeError, ValueError):
        return jsonify({"valid": False, "message": "Data umur tidak valid."}), 400

    if age_value < 18:
        get_db().execute(
            "INSERT INTO verification_logs (product_serial, age, status, created_at) VALUES (?, ?, ?, ?)",
            (payload.get("serial") or "-", age_value, "failed", datetime.utcnow().isoformat()),
        )
        get_db().commit()
        return jsonify({"valid": False, "message": "Verifikasi gagal: Anda belum memenuhi syarat umur pembelian."})

    get_db().execute(
        "INSERT INTO verification_logs (product_serial, age, status, created_at) VALUES (?, ?, ?, ?)",
        (payload.get("serial") or "-", age_value, "success", datetime.utcnow().isoformat()),
    )
    get_db().commit()
    return jsonify({"valid": True, "message": "Verifikasi umur berhasil. Pembelian dapat dilanjutkan."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
