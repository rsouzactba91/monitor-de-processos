import time
import psutil
import requests
import socket
import os
import sys
import threading
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem, Icon

# Define o caminho do arquivo de configuração
if getattr(sys, 'frozen', False):
    # Se o script estiver sendo executado como um executável
    base_path = os.path.dirname(sys.executable)
else:
    # Se o script estiver sendo executado como um script Python
    base_path = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(base_path, "config.txt")

def create_default_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("MASTER_SERVER_URL=http://10.10.8.101:5000/status\n")
            f.write("SERVICE_PROCESS_NAMES=APOWERREC.EXE\n")
        print(f"Arquivo {CONFIG_FILE} criado com valores padrão. Edite conforme necessário.")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        create_default_config()
        print(f"Por favor, edite o arquivo {CONFIG_FILE} e ajuste as configurações.")
        sys.exit(0)
    config = {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                config[key] = value
    return config

def get_local_ip():
    return socket.gethostbyname(socket.gethostname())

def check_service_status(process_names):
    running_processes = {}
    for process_name in process_names:
        is_running = any(proc.info['name'] and proc.info['name'].lower() == process_name.lower() for proc in psutil.process_iter(['name']))
        running_processes[process_name] = is_running
    return running_processes

def send_status_to_master(master_url, process_name, is_running):
    status = "Online" if is_running else "Offline"
    payload = {
        "ip": get_local_ip(),
        "process": process_name,
        "status": status
    }
    try:
        response = requests.post(master_url, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"[INFO] Enviado com sucesso: {process_name} - {status}")
        else:
            print(f"[ERRO] Falha ao enviar status de {process_name}. Código: {response.status_code}")
    except Exception as e:
        print(f"[EXCEÇÃO] Não foi possível conectar ao master para {process_name}: {e}")

def monitor_loop(master_url, process_names, interval):
    print(f"Agente iniciado. Monitorando processos: {process_names} a cada {interval} segundos.")
    while True:
        statuses = check_service_status(process_names)
        for process_name, is_running in statuses.items():
            send_status_to_master(master_url, process_name, is_running)
        time.sleep(interval)

def create_image():
    # Cria uma imagem para o ícone da bandeja (círculo azul)
    width = 64
    height = 64
    image = Image.new('RGBA', (width, height), (0,0,0,0))
    dc = ImageDraw.Draw(image)
    dc.ellipse((0, 0, width, height), fill=(0, 122, 204))
    return image

def on_quit(icon, item):
    icon.stop()
    print("Agente finalizado.")
    sys.exit(0)

def setup_tray_icon(master_url, process_names, check_interval):
    icon = Icon("monitor_agent", create_image(), "Agente de Monitoramento", menu=pystray.Menu(
        MenuItem("Sair", on_quit)
    ))

    def run_monitor():
        monitor_loop(master_url, process_names, check_interval)

    threading.Thread(target=run_monitor, daemon=True).start()
    icon.run()

if __name__ == "__main__":
    config = load_config()
    MASTER_SERVER_URL = config.get("MASTER_SERVER_URL")
    SERVICE_PROCESS_NAMES = config.get("SERVICE_PROCESS_NAMES", "")

    if not MASTER_SERVER_URL or not SERVICE_PROCESS_NAMES:
        print("Configurações inválidas. Edite o config.txt.")
        sys.exit(1)

    process_names_list = [p.strip() for p in SERVICE_PROCESS_NAMES.split(",") if p.strip()]
    CHECK_INTERVAL_SECONDS = 10

    setup_tray_icon(MASTER_SERVER_URL, process_names_list, CHECK_INTERVAL_SECONDS)
