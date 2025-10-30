import os
import sys
import json
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem, Icon
from logger import log_status, read_log

# --------------------------------------------------------
# CONFIGURAÇÃO INICIAL
# --------------------------------------------------------
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(base_path, "config.json")
OFFLINE_TIMEOUT = 20  # segundos

def create_default_config():
    """Cria um config.json padrão se não existir."""
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

def load_config():
    """Carrega o config.json."""
    if not os.path.exists(CONFIG_FILE):
        create_default_config()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config_data):
    """Salva o config.json."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)
    messagebox.showinfo("Configuração", "Configurações salvas com sucesso!")

# --------------------------------------------------------
# DADOS DE MONITORAMENTO
# --------------------------------------------------------
status_dict = {}

def update_status(ip, process, status):
    """Atualiza o status manualmente (simula recebimento de agentes)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_dict[ip] = {"process": process, "status": status, "timestamp": timestamp}
    log_status(ip, ip, process, status, timestamp)

# --------------------------------------------------------
# INTERFACE TKINTER
# --------------------------------------------------------
def abrir_painel():
    """Abre o painel principal de monitoramento."""
    janela = tk.Tk()
    janela.title("Painel de Monitoramento")
    janela.geometry("700x500")
    janela.resizable(False, False)

    tk.Label(janela, text="Status dos Processos", font=("Arial", 14, "bold")).pack(pady=10)

    tree = ttk.Treeview(janela, columns=("ip", "nome", "processo", "status", "timestamp"), show="headings", height=12)
    for col in ("ip", "nome", "processo", "status", "timestamp"):
        tree.heading(col, text=col.capitalize())
        tree.column(col, width=130 if col != "timestamp" else 160)
    tree.pack(pady=5)

    def atualizar():
        tree.delete(*tree.get_children())
        now = datetime.now()
        config = load_config()
        for conn in config["connections"]:
            ip = conn["ip"]
            nome = conn["nome_da_conexao"]
            processos = conn["processos"]
            entry = status_dict.get(ip, None)
            if entry:
                try:
                    last_update = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
                except:
                    last_update = datetime.fromtimestamp(0)
                offline = (now - last_update).total_seconds() > OFFLINE_TIMEOUT
                status_text = "OFFLINE" if offline else entry["status"]
                tree.insert("", "end", values=(ip, nome, entry["process"], status_text, entry["timestamp"]))
            else:
                tree.insert("", "end", values=(ip, nome, ", ".join(processos), "OFFLINE", "-"))
        janela.after(5000, atualizar)

    atualizar()

    def abrir_logs():
        logs = read_log()
        log_janela = tk.Toplevel(janela)
        log_janela.title("Logs do Sistema")
        log_janela.geometry("600x400")
        text = tk.Text(log_janela, wrap="word", font=("Consolas", 10))
        text.pack(expand=True, fill="both")
        for line in logs:
            text.insert("end", json.dumps(line, ensure_ascii=False) + "\n")

    tk.Button(janela, text="Ver Logs", command=abrir_logs, width=20, height=2).pack(pady=10)
    tk.Button(janela, text="Fechar", command=janela.destroy, width=20, height=2).pack(pady=5)
    janela.mainloop()

def abrir_configuracao():
    """Abre a janela de configuração para editar o config.json."""
    config = load_config()
    janela = tk.Tk()
    janela.title("Configuração de Conexões")
    janela.geometry("600x500")
    janela.resizable(False, False)

    tk.Label(janela, text="Gerenciar Conexões", font=("Arial", 14, "bold")).pack(pady=10)

    tree = ttk.Treeview(janela, columns=("ip", "nome", "processos"), show="headings", height=10)
    for col in ("ip", "nome", "processos"):
        tree.heading(col, text=col.capitalize())
        tree.column(col, width=180 if col != "processos" else 220)
    tree.pack(pady=5)

    def carregar_lista():
        tree.delete(*tree.get_children())
        for conn in config["connections"]:
            tree.insert("", "end", values=(conn["ip"], conn["nome_da_conexao"], ", ".join(conn["processos"])))

    carregar_lista()

    ip_var = tk.StringVar()
    nome_var = tk.StringVar()
    proc_var = tk.StringVar()

    form = tk.Frame(janela)
    form.pack(pady=10)

    tk.Label(form, text="IP:").grid(row=0, column=0)
    tk.Entry(form, textvariable=ip_var, width=20).grid(row=0, column=1)

    tk.Label(form, text="Nome:").grid(row=1, column=0)
    tk.Entry(form, textvariable=nome_var, width=20).grid(row=1, column=1)

    tk.Label(form, text="Processos (sep. por vírgula):").grid(row=2, column=0)
    tk.Entry(form, textvariable=proc_var, width=40).grid(row=2, column=1)

    def adicionar():
        new_conn = {
            "ip": ip_var.get().strip(),
            "nome_da_conexao": nome_var.get().strip(),
            "processos": [p.strip() for p in proc_var.get().split(",") if p.strip()]
        }
        if new_conn["ip"] and new_conn["nome_da_conexao"]:
            config["connections"].append(new_conn)
            save_config(config)
            carregar_lista()
            ip_var.set("")
            nome_var.set("")
            proc_var.set("")

    def remover():
        sel = tree.selection()
        if not sel:
            return
        valores = tree.item(sel[0], "values")
        ip = valores[0]
        config["connections"] = [c for c in config["connections"] if c["ip"] != ip]
        save_config(config)
        carregar_lista()

    tk.Button(janela, text="Adicionar", command=adicionar, width=15).pack(pady=5)
    tk.Button(janela, text="Remover", command=remover, width=15).pack(pady=5)
    tk.Button(janela, text="Salvar e Fechar", command=janela.destroy, width=20, height=2).pack(pady=10)

    janela.mainloop()

# --------------------------------------------------------
# ÍCONE DE BANDEJA
# --------------------------------------------------------
def create_image():
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse((0, 0, 64, 64), fill=(0, 122, 204))
    return image

def on_quit(icon, item):
    icon.stop()
    sys.exit()

def setup_tray():
    icon = Icon("monitor_servidor", create_image(), "Servidor de Monitoramento", menu=pystray.Menu(
        MenuItem("Abrir Painel", lambda icon, item: threading.Thread(target=abrir_painel).start()),
        MenuItem("Configurações", lambda icon, item: threading.Thread(target=abrir_configuracao).start()),
        MenuItem("Sair", on_quit)
    ))
    icon.run()

# --------------------------------------------------------
# EXECUÇÃO
# --------------------------------------------------------
if __name__ == "__main__":
    create_default_config()
    threading.Thread(target=setup_tray, daemon=False).start()
