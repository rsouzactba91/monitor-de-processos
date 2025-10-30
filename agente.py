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
import tkinter as tk
from tkinter import ttk, messagebox

# --------------------------------------------------------
# CONFIGURAÇÃO
# --------------------------------------------------------
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(base_path, "config.txt")

def create_default_config():
    """Cria config.txt com valores padrão somente se não existir."""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("MASTER_SERVER_URL=http://10.10.8.14:5000/status\n")
            f.write("SERVICE_PROCESS_NAMES=APOWERREC.EXE\n")
        print(f"[INFO] Arquivo {CONFIG_FILE} criado com valores padrão.")
    else:
        print(f"[INFO] Usando configuração existente: {CONFIG_FILE}")

def load_config():
    """Lê o config.txt e retorna um dicionário."""
    create_default_config()
    config = {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                config[key] = value
    return config

def save_config(master_url, process_names):
    """Atualiza o config.txt manualmente (para uso pela interface Tkinter)."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(f"MASTER_SERVER_URL={master_url}\n")
        f.write(f"SERVICE_PROCESS_NAMES={','.join(process_names)}\n")
    print("[INFO] Configuração atualizada com sucesso!")

def get_local_ip():
    """Obtém o IP local do computador."""
    return socket.gethostbyname(socket.gethostname())

# --------------------------------------------------------
# MONITORAMENTO
# --------------------------------------------------------
def check_service_status(process_names):
    """Verifica se os processos definidos estão sendo executados."""
    running_processes = {}
    for process_name in process_names:
        is_running = any(
            proc.info['name'] and proc.info['name'].lower() == process_name.lower()
            for proc in psutil.process_iter(['name'])
        )
        running_processes[process_name] = is_running
    return running_processes

def send_status_to_master(master_url, process_name, is_running):
    """Envia o status do processo ao servidor master."""
    status = "Online" if is_running else "Offline"
    payload = {
        "ip": get_local_ip(),
        "process": process_name,
        "status": status
    }
    try:
        print(f"[DEBUG] Enviando para: {master_url}")
        response = requests.post(master_url, json=payload, timeout=5)
        print(f"[INFO] Enviado: {process_name} - {status} | Resposta: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[ERRO] Falha ao enviar status de {process_name}: {e}")

def monitor_loop(master_url, process_names, interval):
    """Loop contínuo de monitoramento e envio de status."""
    while True:
        statuses = check_service_status(process_names)
        for process_name, is_running in statuses.items():
            send_status_to_master(master_url, process_name, is_running)
        time.sleep(interval)

# --------------------------------------------------------
# INTERFACE TKINTER
# --------------------------------------------------------
def abrir_painel(master_url, process_names):
    """Exibe painel com o status atual dos processos monitorados."""
    janela = tk.Tk()
    janela.title("Painel de Monitoramento")
    janela.geometry("420x320")
    janela.resizable(False, False)

    tk.Label(janela, text=f"IP Local: {get_local_ip()}", font=("Arial", 11, "bold")).pack(pady=5)
    tk.Label(janela, text="Status dos Processos:", font=("Arial", 12)).pack()

    tree = ttk.Treeview(janela, columns=("status"), show="headings", height=8)
    tree.heading("status", text="Processo / Status")
    tree.column("status", width=300)
    tree.pack(pady=5)

    def atualizar():
        tree.delete(*tree.get_children())
        statuses = check_service_status(process_names)
        for nome, ativo in statuses.items():
            status_text = f"{nome}: {'Online' if ativo else 'Offline'}"
            tree.insert("", "end", values=(status_text,))
        janela.after(5000, atualizar)  # atualiza a cada 5 segundos

    atualizar()

    tk.Button(janela, text="Fechar", command=janela.destroy).pack(pady=10)
    janela.mainloop()

def abrir_configuracao():
    """Abre janela de configuração Tkinter para editar config.txt."""
    janela = tk.Tk()
    janela.title("Configuração do Agente")
    janela.geometry("400x400")
    janela.resizable(False, False)

    config = load_config()
    master_url = tk.StringVar(value=config.get("MASTER_SERVER_URL", ""))
    process_names = config.get("SERVICE_PROCESS_NAMES", "")
    process_list = [p.strip() for p in process_names.split(",") if p.strip()]

    tk.Label(janela, text="Servidor Master:", font=("Arial", 11, "bold")).pack(pady=5)
    tk.Entry(janela, textvariable=master_url, width=50).pack(pady=5)

    tk.Label(janela, text="Processos a Monitorar:", font=("Arial", 11, "bold")).pack(pady=5)
    lista = tk.Listbox(janela, width=40, height=6)
    lista.pack(pady=5)
    for proc in process_list:
        lista.insert(tk.END, proc)

    novo_proc = tk.StringVar()
    tk.Entry(janela, textvariable=novo_proc, width=40).pack(pady=3)

    def adicionar():
        nome = novo_proc.get().strip()
        if nome and nome not in process_list:
            process_list.append(nome)
            lista.insert(tk.END, nome)
            novo_proc.set("")

    def remover():
        selecionado = lista.curselection()
        if selecionado:
            item = lista.get(selecionado)
            process_list.remove(item)
            lista.delete(selecionado)

    tk.Button(janela, text="Adicionar", command=adicionar).pack(pady=3)
    tk.Button(janela, text="Remover", command=remover).pack(pady=3)

    def salvar():
        save_config(master_url.get(), process_list)
        messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
        janela.destroy()

    tk.Button(janela, text="Salvar Configurações", command=salvar, width=25, height=2).pack(pady=10)
    tk.Button(janela, text="Fechar", command=janela.destroy, width=25, height=2).pack()
    janela.mainloop()

# --------------------------------------------------------
# ÍCONE DE BANDEJA
# --------------------------------------------------------
def create_image():
    """Cria o ícone azul exibido na bandeja."""
    width, height = 64, 64
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse((0, 0, width, height), fill=(0, 122, 204))
    return image

def on_quit(icon, item):
    """Finaliza o agente."""
    icon.stop()
    sys.exit(0)

def on_open_panel(icon, item):
    """Abre o painel de status."""
    config = load_config()
    process_names = [p.strip() for p in config.get("SERVICE_PROCESS_NAMES", "").split(",") if p.strip()]
    abrir_painel(config.get("MASTER_SERVER_URL"), process_names)

def on_open_config(icon, item):
    """Abre a janela de configuração."""
    abrir_configuracao()

def setup_tray_icon(master_url, process_names, check_interval):
    """Cria o ícone de bandeja e inicia o monitoramento em segundo plano."""
    icon = Icon("monitor_agent", create_image(), "Agente de Monitoramento",
        menu=pystray.Menu(
            MenuItem("Abrir Painel", on_open_panel),
            MenuItem("Configurações", on_open_config),
            MenuItem("Sair", on_quit)
        )
    )

    def run_monitor():
        monitor_loop(master_url, process_names, check_interval)

    threading.Thread(target=run_monitor, daemon=True).start()
    icon.run()

# --------------------------------------------------------
# EXECUÇÃO PRINCIPAL
# --------------------------------------------------------
if __name__ == "__main__":
    config = load_config()
    MASTER_SERVER_URL = config.get("MASTER_SERVER_URL", "")
    SERVICE_PROCESS_NAMES = config.get("SERVICE_PROCESS_NAMES", "")
    process_names_list = [p.strip() for p in SERVICE_PROCESS_NAMES.split(",") if p.strip()]
    CHECK_INTERVAL_SECONDS = 10

    print(f"[INFO] Servidor Master: {MASTER_SERVER_URL}")
    print(f"[INFO] Processos monitorados: {process_names_list}")

    setup_tray_icon(MASTER_SERVER_URL, process_names_list, CHECK_INTERVAL_SECONDS)
