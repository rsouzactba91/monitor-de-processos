import os
import sys
import json

if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(base_path, "status_log.jsonl")

def log_status(ip, nome_conexao, process, status, timestamp):
    if status.upper() != "OFFLINE":
        return

    log_entry = {
        "timestamp": timestamp,
        "ip": ip,
        "nome_conexao": nome_conexao,
        "process": process,
        "status": status
    }

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        print(f"[LOG] {timestamp} | {ip} | {nome_conexao} | {process} | {status}")
    except Exception as e:
        print(f"[ERROR] Falha ao escrever no log: {e}")

def read_log():
    if not os.path.exists(LOG_FILE):
        return []

    logs = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return logs
    except Exception as e:
        print(f"[ERROR] Falha ao ler o log: {e}")
        return []

def print_log_with_colors():
    logs = read_log()
    verde = "\033[92m"
    amarelo = "\033[93m"
    reset = "\033[0m"

    for entry in logs:
        print(f"{amarelo}timestamp{reset}: {verde}{entry.get('timestamp', '')}{reset} | "
              f"{amarelo}ip{reset}: {verde}{entry.get('ip', '')}{reset} | "
              f"{amarelo}nome_conexao{reset}: {verde}{entry.get('nome_conexao', '')}{reset} | "
              f"{amarelo}process{reset}: {verde}{entry.get('process', '')}{reset} | "
              f"{amarelo}status{reset}: {verde}{entry.get('status', '')}{reset}")
