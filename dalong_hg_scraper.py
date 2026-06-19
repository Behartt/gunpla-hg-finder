#!/usr/bin/env python3
"""
Scraper de kits HG do Dalong.net.

Coleta:
- nome do kit
- código interno do kit (ex.: h01, ho22, wmh03)
- código/modelo (ex.: RX-77-2)
- linha (ex.: HGUC, HGCE)
- franquia/série (com base na seção do catálogo)
- ano e data de lançamento (quando disponível)
- preço de referência (quando disponível)
- URL da página e URL da imagem principal

Também baixa a imagem principal (box art/capa) de cada kit.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_CATALOG_URL = "https://www.dalong.net/reviews/hg/hg_cata_e.htm"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)


@dataclass
class KitRecord:
    kit_id: str
    name: str
    model_code: Optional[str]
    line: Optional[str]
    franchise: str
    release_text: Optional[str]
    release_year: Optional[int]
    price_text: Optional[str]
    detail_url: str
    image_url: Optional[str]
    image_file: Optional[str]
    notes: Optional[str]


class DalongHGScraper:
    def __init__(
        self,
        catalog_url: str,
        output_json: Path,
        images_dir: Path,
        delay_min: float,
        delay_max: float,
        timeout: int,
        max_retries: int,
        skip_images: bool,
    ) -> None:
        self.catalog_url = catalog_url
        self.output_json = output_json
        self.images_dir = images_dir
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.timeout = timeout
        self.max_retries = max_retries
        self.skip_images = skip_images

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

        self.logger = logging.getLogger("dalong_hg_scraper")

    def polite_delay(self) -> None:
        seconds = random.uniform(self.delay_min, self.delay_max)
        time.sleep(seconds)

    def request_with_retry(self, url: str, is_binary: bool = False) -> Optional[requests.Response]:
        for attempt in range(1, self.max_retries + 1):
            try:
                self.polite_delay()
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    return response

                self.logger.warning(
                    "HTTP %s para %s (tentativa %s/%s)",
                    response.status_code,
                    url,
                    attempt,
                    self.max_retries,
                )
            except requests.RequestException as exc:
                self.logger.warning(
                    "Erro de requisição para %s (tentativa %s/%s): %s",
                    url,
                    attempt,
                    self.max_retries,
                    exc,
                )

        self.logger.error("Falha final ao acessar %s", url)
        return None

    def parse_catalog(self) -> List[Tuple[str, str]]:
        self.logger.info("Lendo catálogo HG: %s", self.catalog_url)
        response = self.request_with_retry(self.catalog_url)
        if not response:
            raise RuntimeError("Não foi possível carregar o catálogo HG do Dalong.")

        soup = BeautifulSoup(response.text, "html.parser")

        links: List[Tuple[str, str]] = []
        seen: set[str] = set()
        current_section = "HG"

        for tag in soup.find_all(["h1", "h2", "h3", "h4", "a"]):
            if tag.name in {"h1", "h2", "h3", "h4"}:
                section_text = " ".join(tag.get_text(" ", strip=True).split())
                if section_text:
                    current_section = section_text.replace("▶", "").strip()
                continue

            href = tag.get("href")
            if not href:
                continue

            full_url = urljoin(self.catalog_url, href)
            if "/reviews/" not in full_url or not full_url.endswith("_p.htm"):
                continue

            if full_url in seen:
                continue

            seen.add(full_url)
            links.append((current_section, full_url))

        self.logger.info("Total de páginas de kits encontradas no catálogo: %s", len(links))
        return links

    @staticmethod
    def extract_kit_id(detail_url: str) -> str:
        path = urlparse(detail_url).path
        # Ex.: /reviews/hg/h01/h01_p.htm => h01
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            folder = parts[-2]
            if folder:
                return folder.lower()

        # fallback
        m = re.search(r"([a-z0-9]+)_p\.htm$", path, re.IGNORECASE)
        return m.group(1).lower() if m else "unknown"

    @staticmethod
    def sanitize_filename(value: str) -> str:
        value = value.strip().lower()
        value = re.sub(r"[^a-z0-9._-]+", "_", value)
        value = re.sub(r"_+", "_", value)
        return value.strip("_") or "kit"

    @staticmethod
    def extract_model_code(text: str) -> Optional[str]:
        # Padrões comuns: RX-78-2, MS-06S, XXXG-01W, etc.
        patterns = [
            r"\b[A-Z]{1,6}-[A-Z0-9]{1,6}(?:-[A-Z0-9]{1,6})*\b",
            r"\b[A-Z]{2,6}[0-9]{1,4}[A-Z]?\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None

    def parse_detail_page(self, franchise: str, detail_url: str) -> Dict:
        response = self.request_with_retry(detail_url)
        if not response:
            raise RuntimeError(f"Não foi possível carregar página do kit: {detail_url}")

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.get_text(strip=True) if soup.title else ""
        title = re.sub(r"\s*-\s*Dalong\.net\s*$", "", title, flags=re.IGNORECASE).strip()

        h1 = soup.find("h1")
        kit_name = h1.get_text(" ", strip=True) if h1 else title

        info_line = None
        for p in soup.find_all("p"):
            txt = " ".join(p.get_text(" ", strip=True).split())
            if "|" in txt and ("¥" in txt or re.search(r"\b\d{4}\.?\d{0,2}\b", txt)):
                info_line = txt
                break

        line = None
        release_text = None
        price_text = None
        notes = None
        release_year = None

        if info_line:
            parts = [x.strip() for x in info_line.split("|")]
            if len(parts) >= 1:
                line = parts[0] or None
            if len(parts) >= 2:
                release_text = parts[1] or None
                m_year = re.search(r"(19\d{2}|20\d{2})", release_text or "")
                if m_year:
                    release_year = int(m_year.group(1))
            if len(parts) >= 3:
                price_text = parts[2] or None
            if len(parts) >= 4:
                notes = " | ".join(parts[3:])

        span = soup.find("span")
        span_text = span.get_text(" ", strip=True) if span else ""

        model_code = self.extract_model_code(span_text) or self.extract_model_code(title)

        og_img = soup.find("meta", attrs={"property": "og:image"})
        image_url = og_img.get("content", "").strip() if og_img else ""
        if image_url:
            image_url = urljoin(detail_url, image_url)

        kit_id = self.extract_kit_id(detail_url)

        record = KitRecord(
            kit_id=kit_id,
            name=kit_name,
            model_code=model_code,
            line=line,
            franchise=franchise,
            release_text=release_text,
            release_year=release_year,
            price_text=price_text,
            detail_url=detail_url,
            image_url=image_url or None,
            image_file=None,
            notes=notes,
        )

        return asdict(record)

    def download_main_image(self, kit: Dict) -> Optional[str]:
        if self.skip_images:
            return None

        image_url = kit.get("image_url")
        if not image_url:
            return None

        kit_ref = kit.get("model_code") or kit.get("kit_id") or "kit"
        base_name = self.sanitize_filename(str(kit_ref))

        parsed = urlparse(image_url)
        ext = Path(parsed.path).suffix.lower() or ".jpg"
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            ext = ".jpg"

        file_name = f"{base_name}_{kit.get('kit_id','kit')}{ext}"
        image_path = self.images_dir / file_name

        if image_path.exists() and image_path.stat().st_size > 0:
            self.logger.debug("Imagem já existe, pulando download: %s", image_path)
            return str(image_path)

        response = self.request_with_retry(image_url, is_binary=True)
        if not response:
            self.logger.warning("Não foi possível baixar imagem: %s", image_url)
            return None

        try:
            image_path.write_bytes(response.content)
            return str(image_path)
        except OSError as exc:
            self.logger.error("Erro ao salvar imagem %s: %s", image_path, exc)
            return None

    def save_progress(self, kits: List[Dict], failures: List[Dict], total_discovered: int) -> None:
        """Salva o progresso atual no arquivo JSON."""
        result = {
            "metadata": {
                "source": "Dalong.net",
                "catalog_url": self.catalog_url,
                "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
                "total_discovered": total_discovered,
                "total_scraped": len(kits),
                "total_failed": len(failures),
                "skip_images": self.skip_images,
            },
            "kits": kits,
            "failures": failures,
        }
        self.output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_existing_progress(self) -> Tuple[List[Dict], List[Dict], set[str]]:
        """Carrega o progresso existente do arquivo JSON se ele existir."""
        if not self.output_json.exists():
            return [], [], set()
        
        try:
            data = json.loads(self.output_json.read_text(encoding="utf-8"))
            kits = data.get("kits", [])
            failures = data.get("failures", [])
            
            # Cria um set de URLs já processadas para evitar duplicatas
            processed_urls = set()
            for kit in kits:
                if "detail_url" in kit:
                    processed_urls.add(kit["detail_url"])
            for failure in failures:
                if "detail_url" in failure:
                    processed_urls.add(failure["detail_url"])
            
            self.logger.info("Progresso anterior carregado: %s kits, %s falhas", len(kits), len(failures))
            return kits, failures, processed_urls
        except Exception as exc:
            self.logger.warning("Erro ao carregar progresso anterior: %s. Começando do zero.", exc)
            return [], [], set()

    def run(self, limit: Optional[int]) -> Dict:
        self.output_json.parent.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

        # Carregar progresso existente
        kits, failures, processed_urls = self.load_existing_progress()

        catalog_items = self.parse_catalog()
        if limit is not None and limit > 0:
            catalog_items = catalog_items[:limit]
            self.logger.info("Modo limitado ativado: processando apenas %s kits", len(catalog_items))

        total = len(catalog_items)
        processed_count = 0
        
        for idx, (franchise, detail_url) in enumerate(catalog_items, start=1):
            # Pula URLs já processadas
            if detail_url in processed_urls:
                self.logger.debug("[%s/%s] Kit já processado, pulando: %s", idx, total, detail_url)
                continue
            
            self.logger.info("[%s/%s] Processando kit: %s", idx, total, detail_url)
            try:
                kit = self.parse_detail_page(franchise=franchise, detail_url=detail_url)
                image_file = self.download_main_image(kit)
                if image_file:
                    kit["image_file"] = image_file
                kits.append(kit)
                processed_urls.add(detail_url)
                processed_count += 1
                
                # Salva a cada 5 kits processados para não sobrecarregar I/O
                if processed_count % 5 == 0:
                    self.save_progress(kits, failures, total)
                    self.logger.debug("Progresso salvo: %s kits", len(kits))
                    
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("Erro ao processar %s: %s", detail_url, exc)
                failures.append({"detail_url": detail_url, "error": str(exc)})
                processed_urls.add(detail_url)
                processed_count += 1

        # Salvamento final
        self.save_progress(kits, failures, total)
        self.logger.info("JSON salvo em: %s", self.output_json)
        self.logger.info("Imagens em: %s", self.images_dir)

        result = {
            "metadata": {
                "source": "Dalong.net",
                "catalog_url": self.catalog_url,
                "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
                "total_discovered": total,
                "total_scraped": len(kits),
                "total_failed": len(failures),
                "skip_images": self.skip_images,
            },
            "kits": kits,
            "failures": failures,
        }

        return result


def setup_logger(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("dalong_hg_scraper")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scraper simples e robusto de kits HG do Dalong.net")
    parser.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL, help="URL do catálogo HG")
    parser.add_argument(
        "--output-json",
        default="output/hg_kits_catalog.json",
        help="Arquivo JSON de saída",
    )
    parser.add_argument(
        "--images-dir",
        default="output/images",
        help="Diretório para salvar imagens",
    )
    parser.add_argument(
        "--log-file",
        default="output/scraper.log",
        help="Arquivo de log",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=1.2,
        help="Delay mínimo (segundos) entre requisições",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=2.4,
        help="Delay máximo (segundos) entre requisições",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Timeout de cada requisição")
    parser.add_argument("--max-retries", type=int, default=3, help="Tentativas por URL")
    parser.add_argument("--limit", type=int, default=None, help="Limitar quantidade de kits (teste)")
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Não baixar imagens (somente metadados)",
    )

    args = parser.parse_args()

    if args.delay_min < 0 or args.delay_max < 0:
        parser.error("delay_min e delay_max devem ser >= 0")
    if args.delay_max < args.delay_min:
        parser.error("delay_max deve ser >= delay_min")

    return args


def main() -> None:
    args = parse_args()

    output_json = Path(args.output_json).resolve()
    images_dir = Path(args.images_dir).resolve()
    log_file = Path(args.log_file).resolve()

    setup_logger(log_file)
    logger = logging.getLogger("dalong_hg_scraper")

    logger.info("Iniciando scraper HG do Dalong.net")
    logger.info("Respeitando delays entre %.2fs e %.2fs", args.delay_min, args.delay_max)

    scraper = DalongHGScraper(
        catalog_url=args.catalog_url,
        output_json=output_json,
        images_dir=images_dir,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        timeout=args.timeout,
        max_retries=args.max_retries,
        skip_images=args.skip_images,
    )

    result = scraper.run(limit=args.limit)

    logger.info(
        "Finalizado. Kits coletados: %s | Falhas: %s",
        result["metadata"]["total_scraped"],
        result["metadata"]["total_failed"],
    )


if __name__ == "__main__":
    main()
