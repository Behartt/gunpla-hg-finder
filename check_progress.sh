#!/bin/bash
# Script para verificar o progresso do scraper

echo "=== STATUS DO SCRAPER DE GUNPLA HG ==="
echo ""

# Verifica se o processo está rodando
if pgrep -f "dalong_hg_scraper.py" > /dev/null; then
    echo "✅ Scraper está RODANDO"
    echo ""
else
    echo "⚠️  Scraper NÃO está rodando (pode ter finalizado ou houve erro)"
    echo ""
fi

# Mostra as últimas linhas do log
if [ -f "output/scraper.log" ]; then
    echo "📊 Últimas atualizações:"
    tail -n 5 output/scraper.log
    echo ""
    
    # Conta quantos kits já foram processados
    PROCESSED=$(grep -c "Processando kit:" output/scraper.log)
    echo "📦 Kits processados até agora: $PROCESSED"
    
    # Conta quantos kits estão no JSON
    if [ -f "output/hg_kits_catalog.json" ]; then
        SAVED=$(python3 -c "import json; data=json.load(open('output/hg_kits_catalog.json')); print(len(data['kits']))" 2>/dev/null || echo "0")
        echo "💾 Kits salvos no catálogo: $SAVED"
    fi
    
    # Conta quantas imagens foram baixadas
    if [ -d "output/images" ]; then
        IMAGES=$(ls -1 output/images/ 2>/dev/null | wc -l)
        echo "🖼️  Imagens baixadas: $IMAGES"
    fi
else
    echo "⚠️  Arquivo de log não encontrado ainda"
fi

echo ""
echo "Para ver o log completo: tail -f output/scraper.log"
echo "Para parar o scraper: pkill -f dalong_hg_scraper.py"
