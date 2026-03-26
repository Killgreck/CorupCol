#!/usr/bin/env python3
"""
Servidor local para el dashboard CorupCol.
Uso: python3 servidor_local.py
Luego abrir: http://localhost:8080
"""
import http.server
import socketserver
import os
import webbrowser
import threading

PORT = 8080
DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "dashboard")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def log_message(self, format, *args):
        # Solo loguear errores, no cada request
        if args[1] not in ('200', '304'):
            super().log_message(format, *args)

def abrir_navegador():
    import time
    time.sleep(0.8)
    webbrowser.open(f"http://localhost:{PORT}")

print(f"╔══════════════════════════════════════════════╗")
print(f"║        CorupCol — Servidor Local              ║")
print(f"╠══════════════════════════════════════════════╣")
print(f"║  URL:  http://localhost:{PORT}                   ║")
print(f"║  Dir:  {DASHBOARD_DIR[:38]}  ║")
print(f"╠══════════════════════════════════════════════╣")
print(f"║  Ctrl+C para detener                         ║")
print(f"╚══════════════════════════════════════════════╝")

threading.Thread(target=abrir_navegador, daemon=True).start()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
