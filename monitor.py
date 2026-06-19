#!/usr/bin/env python3
"""Monitor que verifica o progresso do scraper e reinicia se necessário."""

import json
import subprocess
import time
import os
import sys

TARGET_TOTAL = 429
CHECK_INTERVAL = 20  # segundos entre cada verificação
STATUS_FILE = "monitor_status.txt"

def get_status():
    """Retorna o status atual do scraper."""
    running = subprocess.run(['pgrep', '-f', 'dalong_hg_scraper.py'], capture_output=True)
    is_running = running.returncode == 0
    
    if os.path.exists('output/hg_kits_catalog.json'):
        with open('output/hg_kits_catalog.json', 'r') as f:
            data = json.load(f)
        kits_count = len(data['kits'])
    else:
        kits_count = 0
    
    return is_running, kits_count

def restart_scraper():
    """Reinicia o scraper."""
    subprocess.Popen(['nohup', 'python3', 'dalong_hg_scraper.py'], 
                    stdout=open('scraper_run.log', 'w'),
                    stderr=subprocess.STDOUT,
                    cwd=os.getcwd())

def save_status(message):
    """Salva status em arquivo."""
    with open(STATUS_FILE, 'w') as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(message)

print("🔍 Monitor iniciado. Verificando a cada 20 segundos...")
last_count = 0
restart_count = 0

while True:
    try:
        is_running, kits_count = get_status()
        percentage = (kits_count * 100) // TARGET_TOTAL
        remaining = TARGET_TOTAL - kits_count
        
        # Mostrar progresso se mudou
        if kits_count != last_count:
            msg = f"📦 {kits_count}/{TARGET_TOTAL} ({percentage}%) - Restam {remaining} kits"
            print(msg)
            save_status(msg)
            last_count = kits_count
        
        # Verificar se terminou
        if kits_count >= TARGET_TOTAL:
            msg = f"""
🎉🎉🎉 SCRAPER CONCLUÍDO COM SUCESSO! 🎉🎉🎉

✅ Total de kits coletados: {kits_count}
📄 Catálogo: output/hg_kits_catalog.json
🖼️  Imagens: output/images/

🎯 Catálogo mestre completo de todos os kits HG do Dalong!
"""
            print(msg)
            save_status(msg)
            sys.exit(0)
        
        # Reiniciar se parou antes de terminar
        if not is_running and kits_count < TARGET_TOTAL:
            restart_count += 1
            msg = f"⚠️ Scraper parou. Reiniciando... (tentativa {restart_count})\n{kits_count}/{TARGET_TOTAL} kits salvos"
            print(msg)
            save_status(msg)
            restart_scraper()
            time.sleep(5)
        
        time.sleep(CHECK_INTERVAL)
        
    except KeyboardInterrupt:
        print("\n🛑 Monitor interrompido pelo usuário")
        break
    except Exception as e:
        print(f"❌ Erro no monitor: {e}")
        time.sleep(CHECK_INTERVAL)
