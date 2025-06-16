from flask import Flask, request, jsonify, render_template_string
import os
from datetime import datetime
import sys
import json
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem, Icon
import waitress
import threading
from logger import log_status, read_log

if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(base_path, "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "connections": [
                {
                    "ip": "10.10.9.59",
                    "nome_da_conexao": "PC_CAMERAS",
                    "processos": ["APOWERREC.EXE"]
                },
                {
                    "ip": "192.168.1.101",
                    "nome_da_conexao": "PC_101",
                    "processos": ["processo1.exe"]
                }
            ]
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()
connections = config.get('connections', [])
ip_to_nome = {conn['ip']: conn.get('nome_da_conexao', conn['ip']) for conn in connections}
ip_to_processos = {conn['ip']: conn.get('processos', []) for conn in connections}
FIXED_IPS = list(ip_to_nome.keys())

status_dict = {}
OFFLINE_TIMEOUT = 20  # segundos

app = Flask(__name__)

@app.route('/status', methods=['POST'])
def receive_status():
    data = request.get_json()
    process = data.get("process")
    status = data.get("status")
    ip = request.remote_addr

    if not process or not status:
        return jsonify({"error": "Dados incompletos"}), 400

    if ip not in FIXED_IPS:
        return jsonify({"error": "IP não autorizado"}), 403

    allowed_processes_lower = [p.lower() for p in ip_to_processos.get(ip, [])]
    if process.lower() not in allowed_processes_lower:
        return jsonify({"error": f"Processo '{process}' não autorizado para o IP {ip}"}), 403

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    status_dict[ip] = {
        "process": process.upper(),
        "status": status.upper(),
        "timestamp": timestamp,
    }

    log_status(ip, ip_to_nome.get(ip, ip), process.upper(), status.upper(), timestamp)
    print(f"[RECEBIDO] {timestamp} - {ip} | {process.upper()} está {status.upper()}")
    return jsonify({"message": "Status recebido com sucesso"}), 200

@app.route('/status/all')
def status_all():
    now = datetime.now()
    result = {}

    for ip in FIXED_IPS:
        entry = status_dict.get(ip)
        if entry:
            try:
                last_update = datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M:%S')
            except:
                last_update = datetime.fromtimestamp(0)

            offline = (now - last_update).total_seconds() > OFFLINE_TIMEOUT
            
            status_value = entry['status']
            if offline:
                status_value = "OFFLINE"

            result[ip] = {
                "process": entry["process"],
                "status": status_value,
                "timestamp": entry["timestamp"],
                "offline": offline
            }
        else:
            result[ip] = {
                "process": "Desconhecido",
                "status": "OFFLINE",
                "timestamp": "-",
                "offline": True
            }

    return jsonify(result)

@app.route('/log')
def view_log():
    logs = read_log()
    return jsonify(logs)

def format_log_with_colors(log_entry):
    parts = []
    for key, value in log_entry.items():
        color = ""
        if key.lower() == "ip":
            color = "blue"
        elif key.lower() == "status":
            color = "red" if str(value).upper() == "OFFLINE" else "green"
        elif key.lower() == "process":
            color = "purple"
        elif key.lower() == "timestamp":
            color = "gray"
        else:
            color = "black"
        parts.append(f'<span style="color: {color};"><strong>{key}:</strong> {value}</span>')
    return " | ".join(parts)

@app.route('/')
def homepage():
    status_data = status_all().get_json()
    log_lines = read_log()
    log_content = [format_log_with_colors(line) for line in log_lines]

    return render_template_string('''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Monitor de Processos</title>
    <style>
        body { font-family: 'Arial', sans-serif; padding: 24px; background-color: #f4f4f9; }
        h1 { color: #2563eb; }
        table { width: 100%; max-width: 960px; border-collapse: collapse; background: #fff; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        th, td { padding: 12px 16px; border-bottom: 1px solid #ccc; }
        thead { background-color: #2563eb; color: white; }
        .status-online { color: green; font-weight: bold; }
        .status-offline { color: red; font-weight: bold; }
        .log-container { margin-top: 24px; max-width: 960px; background: white; padding: 16px; border-radius: 8px;
            font-family: monospace; white-space: pre-wrap; max-height: 300px; overflow-y: auto; }
    </style>
</head>
<body>
    <h1>Monitor de Processos</h1>
    <table>
        <thead>
            <tr>
                <th>IP</th>
                <th>Nome da Conexão</th>
                <th>Processo</th>
                <th>Status</th>
                <th>Última Atualização</th>
                <th>Offline</th>
            </tr>
        </thead>
        <tbody>
            {% for ip in ips %}
            {% set entry = status_dict[ip] %}
            <tr>
                <td>{{ ip }}</td>
                <td>{{ ip_to_nome.get(ip, ip) }}</td>
                <td>{{ entry.process }}</td>
                <td class="{{ 'status-offline' if entry.status == 'OFFLINE' else 'status-online' }}">{{ entry.status }}</td>
                <td>{{ entry.timestamp }}</td>
                <td class="{{ 'status-offline' if entry.offline else 'status-online' }}">{{ "Sim" if entry.offline else "Não" }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="log-container">
        <strong>Logs Recentes:</strong>
        <pre>{{ log_content | join('<br>') | safe }}</pre>
    </div>
</body>
</html>
''', ips=FIXED_IPS, status_dict=status_data, log_content=log_content, ip_to_nome=ip_to_nome)

def run_flask():
    waitress.serve(app, host='0.0.0.0', port=5000)

def create_image(width, height):
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    dc = ImageDraw.Draw(image)
    dc.ellipse((0, 0, width, height), fill=(0, 0, 255))
    return image

def on_quit(icon, item):
    icon.stop()
    sys.exit()

def setup(icon):
    icon.visible = True

if __name__ == '__main__':
    icon = Icon("monitor_processos", create_image(64, 64), "Monitor de Processos", menu=(MenuItem("Sair", on_quit),))
    threading.Thread(target=run_flask, daemon=True).start()
    icon.run(setup)
