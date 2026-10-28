"""Local Windows launcher: prepare .env, show Wi-Fi address, run exactly one Uvicorn worker.

This script does not install applications or contact API-Football by itself.
The scanner starts inside FastAPI only if an API key is configured.
"""
from __future__ import annotations

import os
import ipaddress
import secrets
import socket
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.env'


def config_lines() -> dict[str, str]:
    if not ENV.exists():
        ENV.write_text((ROOT / '.env.example').read_text(encoding='utf-8'), encoding='utf-8')
    settings = {}
    for line in ENV.read_text(encoding='utf-8-sig').splitlines():
        text = line.strip()
        if not text or text.startswith('#') or '=' not in text:
            continue
        key, value = text.split('=', 1)
        settings[key.strip()] = value.strip().strip('"').strip("'")
    if not settings.get('JHONNY_LAN_PASSWORD'):
        password = secrets.token_urlsafe(18)
        lines = ENV.read_text(encoding='utf-8-sig').splitlines()
        replaced = False
        for i, line in enumerate(lines):
            if line.strip().startswith('JHONNY_LAN_PASSWORD='):
                lines[i] = 'JHONNY_LAN_PASSWORD=' + password
                replaced = True
        if not replaced:
            lines.append('JHONNY_LAN_PASSWORD=' + password)
        ENV.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        settings['JHONNY_LAN_PASSWORD'] = password
    try:
        ENV.chmod(0o600)
    except OSError:
        pass
    return settings


def find_private_ip() -> str | None:
    # No packets are sent. Used only to identify the source LAN address.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('192.0.2.1', 80))
            ip = sock.getsockname()[0]
            if ipaddress.ip_address(ip).is_private and not ipaddress.ip_address(ip).is_loopback:
                return ip
    except OSError:
        pass
    try:
        for candidate in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ipaddress.ip_address(candidate).is_private and not ipaddress.ip_address(candidate).is_loopback:
                return candidate
    except OSError:
        pass
    return None


def main() -> int:
    if sys.version_info < (3, 11):
        print('Se requiere Python 3.11 o superior.'); return 2
    os.chdir(ROOT)
    cfg = config_lines()
    os.environ['JHONNY_LAN_PASSWORD'] = cfg['JHONNY_LAN_PASSWORD']
    # No publication of official signals in the first local release.
    os.environ['SHADOW_MODE'] = 'true'
    os.environ['WORKER_SINGLE_PROCESS_ONLY'] = 'true'
    if not cfg.get('API_FOOTBALL_KEY') and not cfg.get('FOOTBALL_DATA_KEY'):
        os.environ['WORKER_ENABLED'] = 'false'
        scanner = 'PAUSADO: falta API_FOOTBALL_KEY en .env'
    else:
        scanner = 'HABILITADO EN SHADOW (sin senales oficiales)'
    ip = find_private_ip()
    print('\n' + '='*68)
    print('JHONNY ELITE V3  -  ELITE LIVE INTELLIGENCE')
    print('='*68)
    print('MOTOR LIVE:', scanner)
    print('COMPUTADORA: http://127.0.0.1:8000/panel')
    print('TELEFONO:   ', f'http://{ip}:8000/panel' if ip else 'Busca la IPv4 de tu PC con ipconfig')
    print('RED: misma red Wi-Fi privada, permite acceso SOLO a red privada en el firewall.')
    print('USUARIO: jhonny')
    print('CONTRASENA:', cfg['JHONNY_LAN_PASSWORD'])
    print('La contrasena esta en .env; no compartas ese archivo.')
    print('Presiona Ctrl+C para cerrar. NO abras worker.py por separado.')
    print('='*68 + '\n')

    def open_browser():
        try:
            webbrowser.open('http://127.0.0.1:8000/panel')
        except Exception:
            pass

    threading.Timer(3.0, open_browser).start()
    try:
        import uvicorn
        # Workers=1 and reload=False are essential: double workers spend double API.
        uvicorn.run('main:app', host='0.0.0.0', port=8000, workers=1,
                    reload=False, access_log=False, log_level='info')
        return 0
    except OSError as exc:
        print('No se puede usar el puerto 8000. Quiza JHONNY ya esta abierto:', exc)
        return 1
    except ImportError as exc:
        print('Falta una dependencia Python:', exc)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
