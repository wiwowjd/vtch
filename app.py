import json
import os
from flask import Flask, request, jsonify, render_template
from flask.views import MethodView

app = Flask(__name__)

# ─── Data loader — satu file endpoints.json berisi semua endpoint ─────────────

ENDPOINTS_FILE = os.path.join(os.path.dirname(__file__), "endpoints.json")

def load_all() -> dict:
    """Baca seluruh endpoints.json."""
    with open(ENDPOINTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_meta_and_data(name: str):
    """Return (meta, data) dari satu endpoint. data = semua field kecuali _meta."""
    raw  = load_all()[name]
    meta = raw.get("_meta", {})
    data = {k: v for k, v in raw.items() if k != "_meta"}
    return meta, data

def validate_params(meta: dict, source: dict) -> list:
    """Return list key yang required tapi kosong di source."""
    return [
        p["key"] for p in meta.get("params", [])
        if p.get("required") and not str(source.get(p["key"], "")).strip()
    ]

def parse_body() -> dict:
    """Ambil body POST: coba JSON dulu, fallback ke form-data."""
    body = request.get_json(silent=True)
    if body is None:
        body = request.form.to_dict()
    return body or {}


# ─── Halaman utama ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─── API Index — list semua endpoint + meta ───────────────────────────────────

@app.route("/api", methods=["GET"])
def api_index():
    all_eps = load_all()
    result  = []
    for key, val in all_eps.items():
        meta = val.get("_meta", {})
        result.append({
            "endpoint":    f"/api/{key}",
            "name":        meta.get("name", key),
            "description": meta.get("description", ""),
            "method":      meta.get("method", "GET"),
            "params":      meta.get("params", [])
        })
    return jsonify({"status": 200, "total": len(result), "endpoints": result})


# ─── Endpoint Classes (MethodView) ────────────────────────────────────────────

class StatusEndpoint(MethodView):
    """GET /api/status — Cek status server."""

    def get(self):
        meta, data = get_meta_and_data("status")
        return jsonify({
            "status":   200,
            "endpoint": "/api/status",
            "method":   "GET",
            "params":   request.args.to_dict(),
            "data":     data
        })


class InfoEndpoint(MethodView):
    """GET /api/info — Informasi komunitas VTCH."""

    def get(self):
        meta, data = get_meta_and_data("info")
        return jsonify({
            "status":   200,
            "endpoint": "/api/info",
            "method":   "GET",
            "params":   request.args.to_dict(),
            "data":     data
        })


class ContactEndpoint(MethodView):
    """GET /api/contact — Link channel & grup VTCH."""

    def get(self):
        meta, data = get_meta_and_data("contact")
        return jsonify({
            "status":   200,
            "endpoint": "/api/contact",
            "method":   "GET",
            "data":     data
        })


class PingEndpoint(MethodView):
    """GET /api/ping — Cek koneksi ke server."""

    def get(self):
        meta, data = get_meta_and_data("ping")
        return jsonify({
            "status":   200,
            "endpoint": "/api/ping",
            "method":   "GET",
            "data":     data
        })


class CariEndpoint(MethodView):
    """GET /api/cari?q=<kata_kunci> — Pencarian dengan query parameter."""

    def get(self):
        meta, data = get_meta_and_data("cari")
        params     = request.args.to_dict()

        missing = validate_params(meta, params)
        if missing:
            return jsonify({
                "status":   400,
                "error":    "Missing Parameter",
                "message":  f"Parameter wajib tidak ada: {', '.join(missing)}",
                "required": missing
            }), 400

        return jsonify({
            "status":   200,
            "endpoint": "/api/cari",
            "method":   "GET",
            "params":   params,
            "data":     data
        })


class PesanEndpoint(MethodView):
    """
    GET  /api/pesan — Info endpoint pesan.
    POST /api/pesan — Kirim pesan ke komunitas VTCH.
                      Body: { "nama": str (opsional), "pesan": str (wajib) }
    """

    def get(self):
        meta, data = get_meta_and_data("pesan")
        return jsonify({
            "status":   200,
            "endpoint": "/api/pesan",
            "method":   "GET",
            "data":     data
        })

    def post(self):
        meta, _ = get_meta_and_data("pesan")
        body    = parse_body()

        missing = validate_params(meta, body)
        if missing:
            return jsonify({
                "status":   400,
                "error":    "Missing Field",
                "message":  f"Field wajib tidak diisi: {', '.join(missing)}",
                "required": missing
            }), 400

        nama  = (body.get("nama", "") or "Anonim").strip()
        pesan = body.get("pesan", "").strip()

        return jsonify({
            "status":   200,
            "endpoint": "/api/pesan",
            "method":   "POST",
            "sukses":   True,
            "pesan_diterima": {"nama": nama, "pesan": pesan},
            "balasan":  f"Pesan dari '{nama}' diterima. Terima kasih!"
        })


class QuoteEndpoint(MethodView):
    """GET /api/quote — Kutipan inspirasi hacker."""

    def get(self):
        meta, data = get_meta_and_data("quote")
        return jsonify({
            "status":   200,
            "endpoint": "/api/quote",
            "method":   "GET",
            "data":     data
        })


class ToolsEndpoint(MethodView):
    """GET /api/tools — Daftar tools rekomendasi VTCH."""

    def get(self):
        meta, data = get_meta_and_data("tools")
        return jsonify({
            "status":   200,
            "endpoint": "/api/tools",
            "method":   "GET",
            "data":     data
        })


# ─── Register semua endpoint class ke URL ────────────────────────────────────

ENDPOINT_VIEWS = {
    "status":  StatusEndpoint,
    "info":    InfoEndpoint,
    "contact": ContactEndpoint,
    "ping":    PingEndpoint,
    "cari":    CariEndpoint,
    "pesan":   PesanEndpoint,
    "quote":   QuoteEndpoint,
    "tools":   ToolsEndpoint,
}

for _name, _view in ENDPOINT_VIEWS.items():
    app.add_url_rule(
        f"/api/{_name}",
        view_func=_view.as_view(_name),
        methods=["GET", "POST"]
    )


# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api"):
        return jsonify({
            "status":    404,
            "error":     "Not Found",
            "message":   "Endpoint tidak ditemukan.",
            "available": list(ENDPOINT_VIEWS.keys())
        }), 404
    return render_template("404.html"), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({
        "status":  405,
        "error":   "Method Not Allowed",
        "message": "Method tidak diizinkan untuk endpoint ini."
    }), 405

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "status":  500,
        "error":   "Internal Server Error",
        "message": "Terjadi kesalahan pada server."
    }), 500


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
