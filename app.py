#!/usr/bin/env python3
"""
App de busca para catálogo HG do Dalong.

Funcionalidades:
- Busca textual por qualquer campo relevante
- Filtros por franquia, linha, ano e tags
- Visualização dos kits com imagem
- Marcação de kits já possuídos (com persistência local)
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Dict, List, Set

import streamlit as st

CATALOG_PATH = Path("output/hg_kits_catalog.json")
OWNED_PATH = Path("output/owned_kits.json")


@st.cache_data(show_spinner=False)
def load_catalog(path: Path) -> List[Dict]:
    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    kits = data.get("kits", [])
    kits.sort(key=lambda item: ((item.get("release_year") or 9999), item.get("name") or ""))
    return kits


def load_owned(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("owned_kit_ids", []))
    except Exception:
        return set()


def save_owned(path: Path, owned: Set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"owned_kit_ids": sorted(owned)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def tokenize_text(value: str) -> Set[str]:
    tokens = set(re.findall(r"[a-z0-9-]+", (value or "").lower()))
    return {token for token in tokens if len(token) >= 2}


def build_tags(kit: Dict) -> Set[str]:
    fields = [
        kit.get("name") or "",
        kit.get("model_code") or "",
        kit.get("line") or "",
        kit.get("franchise") or "",
        kit.get("notes") or "",
        kit.get("release_text") or "",
    ]
    tags = set()
    for field in fields:
        tags.update(tokenize_text(field))
    return tags


def apply_filters(
    kits: List[Dict],
    query: str,
    selected_franchises: List[str],
    selected_lines: List[str],
    year_min: int,
    year_max: int,
    selected_tags: List[str],
    only_owned: bool,
    owned_ids: Set[str],
) -> List[Dict]:
    query_tokens = tokenize_text(query)
    selected_tags_set = set(tag.lower() for tag in selected_tags)

    filtered: List[Dict] = []
    for kit in kits:
        kit_id = str(kit.get("kit_id") or "")
        franchise = kit.get("franchise") or ""
        line = kit.get("line") or ""
        release_year = kit.get("release_year")

        if selected_franchises and franchise not in selected_franchises:
            continue
        if selected_lines and line not in selected_lines:
            continue

        if isinstance(release_year, int):
            if release_year < year_min or release_year > year_max:
                continue
        else:
            if year_min > 1900 or year_max < 2099:
                continue

        tags = build_tags(kit)

        if query_tokens and not query_tokens.issubset(tags):
            searchable = " ".join(
                [
                    kit.get("name") or "",
                    kit.get("model_code") or "",
                    kit.get("line") or "",
                    kit.get("franchise") or "",
                    kit.get("notes") or "",
                    kit.get("kit_id") or "",
                ]
            ).lower()
            if not all(token in searchable for token in query_tokens):
                continue

        if selected_tags_set and not selected_tags_set.issubset(tags):
            continue

        if only_owned and kit_id not in owned_ids:
            continue

        filtered.append(kit)

    return filtered


def get_image_source(kit: Dict) -> str | None:
    local_path = kit.get("image_file")
    if local_path and Path(local_path).exists():
        return local_path
    return kit.get("image_url")


def main() -> None:
    st.set_page_config(page_title="Gunpla HG Finder", page_icon="🤖", layout="wide")
    st.title("🤖 Gunpla HG Finder")
    st.caption("Busque kits HG por tags, filtros e marque os kits que você já possui.")

    kits = load_catalog(CATALOG_PATH)
    if not kits:
        st.error(
            "Catálogo não encontrado. Gere o catálogo primeiro em output/hg_kits_catalog.json "
            "rodando o scraper: python3 dalong_hg_scraper.py"
        )
        st.stop()

    owned_ids = load_owned(OWNED_PATH)

    all_franchises = sorted({kit.get("franchise") or "Sem franquia" for kit in kits})
    all_lines = sorted({kit.get("line") or "Sem linha" for kit in kits})

    years = [kit.get("release_year") for kit in kits if isinstance(kit.get("release_year"), int)]
    min_year = min(years) if years else 1900
    max_year = max(years) if years else 2099

    all_tags: Set[str] = set()
    for kit in kits:
        all_tags.update(build_tags(kit))
    all_tags_sorted = sorted(all_tags)

    with st.sidebar:
        st.header("Filtros")
        query = st.text_input("Busca geral (nome, código, franquia, etc.)")

        selected_franchises = st.multiselect("Franquias", all_franchises)
        selected_lines = st.multiselect("Linhas", all_lines)

        selected_years = st.slider(
            "Ano de lançamento",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year),
        )

        selected_tags = st.multiselect("Tags (todas devem bater)", all_tags_sorted)

        only_owned = st.checkbox("Mostrar apenas kits que eu já tenho")

    filtered_kits = apply_filters(
        kits=kits,
        query=query,
        selected_franchises=selected_franchises,
        selected_lines=selected_lines,
        year_min=selected_years[0],
        year_max=selected_years[1],
        selected_tags=selected_tags,
        only_owned=only_owned,
        owned_ids=owned_ids,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de kits", len(kits))
    c2.metric("Kits filtrados", len(filtered_kits))
    c3.metric("Kits que você já tem", len(owned_ids))

    col_a, col_b = st.columns(2)
    if col_a.button("✅ Marcar todos os filtrados como 'tenho'"):
        owned_ids.update(str(kit.get("kit_id") or "") for kit in filtered_kits)
        save_owned(OWNED_PATH, owned_ids)
        st.success("Kits filtrados marcados como possuídos.")

    if col_b.button("🧹 Desmarcar todos os filtrados"):
        filtered_ids = {str(kit.get("kit_id") or "") for kit in filtered_kits}
        owned_ids = {kit_id for kit_id in owned_ids if kit_id not in filtered_ids}
        save_owned(OWNED_PATH, owned_ids)
        st.success("Kits filtrados desmarcados.")

    st.divider()

    page_size = st.selectbox("Resultados por página", [12, 24, 48], index=1)
    total_pages = max(1, math.ceil(len(filtered_kits) / page_size))
    page = st.number_input("Página", min_value=1, max_value=total_pages, value=1)

    start = (page - 1) * page_size
    end = start + page_size
    page_kits = filtered_kits[start:end]

    if not page_kits:
        st.info("Nenhum kit encontrado com os filtros atuais.")
        return

    changed = False

    for kit in page_kits:
        kit_id = str(kit.get("kit_id") or "")
        name = kit.get("name") or "Sem nome"
        model_code = kit.get("model_code") or "-"
        line = kit.get("line") or "-"
        franchise = kit.get("franchise") or "-"
        year = kit.get("release_year") or "-"
        price = kit.get("price_text") or "-"
        detail_url = kit.get("detail_url") or ""

        st.subheader(f"{name} ({kit_id})")
        col1, col2 = st.columns([1, 2])

        with col1:
            image_source = get_image_source(kit)
            if image_source:
                st.image(image_source, use_container_width=True)
            else:
                st.caption("Sem imagem")

        with col2:
            st.write(f"**Model Code:** {model_code}")
            st.write(f"**Linha:** {line}")
            st.write(f"**Franquia:** {franchise}")
            st.write(f"**Ano:** {year}")
            st.write(f"**Preço original:** {price}")
            if detail_url:
                st.link_button("Abrir página no Dalong", detail_url)

            key = f"owned_{kit_id}"
            if key not in st.session_state:
                st.session_state[key] = kit_id in owned_ids

            new_value = st.checkbox("Já tenho este kit", key=key)
            old_value = kit_id in owned_ids

            if new_value and not old_value:
                owned_ids.add(kit_id)
                changed = True
            elif not new_value and old_value:
                owned_ids.discard(kit_id)
                changed = True

        st.divider()

    if changed:
        save_owned(OWNED_PATH, owned_ids)
        st.success("Coleção atualizada!")


if __name__ == "__main__":
    main()
