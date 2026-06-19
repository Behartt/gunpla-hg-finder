### Scraper de kits HG do Dalong.net

Script Python simples e robusto para montar um catálogo mestre de Gunplas **HG (High Grade)** a partir do Dalong.net.

### O que ele faz

- Navega no catálogo HG: `https://www.dalong.net/reviews/hg/hg_cata_e.htm`
- Coleta, para cada kit:
  - `name` (nome)
  - `kit_id` (código interno do kit no Dalong, ex.: `h01`, `wmh02`)
  - `model_code` (código do modelo, ex.: `RX-77-2`, quando disponível)
  - `line` (linha, ex.: `HGUC`)
  - `franchise` (seção/franquia no catálogo)
  - `release_text` e `release_year` (quando disponível)
  - `price_text` (quando disponível)
  - `detail_url`
  - `image_url` (imagem principal / box art via `og:image`)
- Baixa a imagem principal de cada kit
- Salva tudo em JSON estruturado
- Mantém log detalhado de progresso e erros

### Instalação

```bash
cd /home/ubuntu/gunpla_scraper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Execução

#### Rodar completo (recomendado)

```bash
python dalong_hg_scraper.py
```

Saídas padrão:
- JSON: `output/hg_kits_catalog.json`
- Imagens: `output/images/`
- Logs: `output/scraper.log`

#### Rodar teste rápido (10 kits)

```bash
python dalong_hg_scraper.py --limit 10
```

#### Rodar sem baixar imagens

```bash
python dalong_hg_scraper.py --skip-images
```

### Parâmetros úteis

- `--delay-min` (default: `1.2`)
- `--delay-max` (default: `2.4`)
- `--timeout` (default: `30`)
- `--max-retries` (default: `3`)
- `--output-json` (default: `output/hg_kits_catalog.json`)
- `--images-dir` (default: `output/images`)
- `--log-file` (default: `output/scraper.log`)

Exemplo com delays mais conservadores:

```bash
python dalong_hg_scraper.py --delay-min 1.8 --delay-max 3.0
```

### Observações de robustez

- O scraper usa **retry** por URL com logging de falhas.
- Usa **delay aleatório entre requisições** para reduzir carga no servidor.
- Se uma página falhar, o erro é registrado e o processo continua.
- O JSON final inclui a lista `failures` para reprocessamento posterior.

### Estrutura do JSON

```json
{
  "metadata": {
    "source": "Dalong.net",
    "catalog_url": "...",
    "scraped_at_utc": "...",
    "total_discovered": 0,
    "total_scraped": 0,
    "total_failed": 0,
    "skip_images": false
  },
  "kits": [
    {
      "kit_id": "h01",
      "name": "Guncannon",
      "model_code": "RX-77-2",
      "line": "HGUC Guncannon",
      "franchise": "HGUC / HGAW / HGFC / HGCE",
      "release_text": "1999.5",
      "release_year": 1999,
      "price_text": "¥800",
      "detail_url": "https://i.ytimg.com/vi/Xnzw6LZEyU8/sddefault.jpg",
      "image_url": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiRXJ5L2y_ut_d4RdLrJs1GRXi8y_Bg-bmZ3SpTFyLSaL1GtajCeardj65Rh8jXEbHZMlt3-qw2tpZUfXZrN5yLsxlb_mnndfoRpK9cWQO84gxlYf-y76PzL10XsA2Zm_OZa3Wc4iqHyw8Q/s1600/Box+art.JPG",
      "image_file": "/.../output/images/rx-77-2_h01.jpg",
      "notes": null
    }
  ],
  "failures": []
}
```

### Próximo passo para seu sistema de preços no Brasil

Com esse catálogo mestre pronto, você pode criar um segundo pipeline para:
1. normalizar nomes/códigos,
2. buscar preços em lojas BR,
3. comparar por `model_code` + similaridade de nome.

### App de busca e coleção (marcar kits que você já tem)

Foi adicionado um app em Streamlit (`app.py`) para navegar no catálogo HG com busca e filtros.

Funcionalidades:
- Busca geral por texto (nome, código, linha, franquia, etc.)
- Filtro por franquia
- Filtro por linha
- Filtro por faixa de ano
- Filtro por tags (todas as tags selecionadas devem estar presentes)
- Exibição dos kits com imagem e link para página do Dalong
- Marcar/desmarcar kits que você já possui
- Persistência local da coleção em `output/owned_kits.json`

#### Rodar o app

```bash
cd /home/ubuntu/gunpla_scraper
source .venv/bin/activate  # se estiver usando venv
streamlit run app.py
```

Depois abra a URL local que o Streamlit mostrar no terminal (normalmente `http://localhost:8501`).

#### Arquivos usados pelo app

- Catálogo: `output/hg_kits_catalog.json`
- Coleção pessoal: `output/owned_kits.json`
- Imagens: `output/images/`

#### Observação

Se você rodar o scraper novamente e atualizar o catálogo, o app continua funcionando normalmente e mantém sua lista de kits possuídos em arquivo separado.
