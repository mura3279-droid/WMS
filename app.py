import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Склад — поиск адреса",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container {padding: 1rem 0.8rem 0 !important; max-width: 760px !important;}
    header {visibility: hidden;}
    div[data-testid="stFileUploader"] {border-radius: 12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("### 🔄 Обновление базы товаров")
st.caption("Загрузите новый Excel (.xlsx), чтобы заменить таблицу товаров в приложении.")
uploaded_file = st.file_uploader(
    "Выбрать новый Excel-файл",
    type=["xlsx"],
    accept_multiple_files=False,
    help="Новый файл должен содержать столбцы с кодом SKU, штрихкодом, наименованием и адресом товара.",
)

html_path = Path(__file__).parent / "index.html"
if not html_path.exists():
    st.error("Не найден index.html. Убедитесь, что он загружен в GitHub вместе с app.py.")
    st.stop()

page = html_path.read_text(encoding="utf-8")


def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def make_items(file_bytes):
    df = pd.read_excel(file_bytes, dtype=str, keep_default_na=False)
    df.columns = [str(c).strip() for c in df.columns]

    aliases = {
        "Код SKU": ["Код SKU", "Код товара", "SKU", "КодТовара", "Код sku"],
        "Штрих Код": ["Штрих Код", "ШК", "Штрихкод", "Штрих-код", "Barcode", "Штрих код"],
        "Наименование SKU": ["Наименование SKU", "Наименование", "Название товара", "Товар", "Наименование товара"],
        "Единица измерения": ["Единица измерения", "Ед. изм.", "Ед изм", "Единица", "ЕИ"],
        "Доступный остаток": ["Доступный остаток", "Остаток", "Количество", "Кол-во", "Факт"],
        "Группа": ["Группа", "Группа товара", "Товарная группа"],
        "Подгруппа": ["Подгруппа", "Подгруппа товара"],
        "Торговая марка": ["Торговая марка", "Бренд", "ТМ"],
        "Адрес": ["Адрес", "Адрес хранения", "Адрес ячейки", "Место хранения"],
    }
    rename = {}
    for target, names in aliases.items():
        found = next((name for name in names if name in df.columns), None)
        if found:
            rename[found] = target
    df = df.rename(columns=rename)

    required = ["Код SKU", "Штрих Код", "Наименование SKU"]
    missing = [name for name in required if name not in df.columns]
    if missing:
        raise ValueError("В Excel не найдены обязательные столбцы: " + ", ".join(missing))

    for col in aliases:
        if col not in df.columns:
            df[col] = ""

    result = []
    for _, row in df.iterrows():
        item = {col: clean(row.get(col, "")) for col in aliases}
        address = item["Адрес"]
        parts = [part.strip() for part in address.split(".")] if address else []
        item["address_parts"] = parts if len(parts) == 5 else []
        result.append(item)
    return result


if uploaded_file is not None:
    try:
        items = make_items(uploaded_file.getvalue())
        if not items:
            st.warning("В выбранном Excel нет строк с товарами. Продолжает отображаться прежняя база.")
        else:
            data = json.dumps(items, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
            page, count = re.subn(r"const ITEMS=\[.*?\];", "const ITEMS=" + data + ";", page, count=1, flags=re.S)
            if count != 1:
                st.error("Не удалось обновить базу внутри интерфейса. Проверьте исходный index.html.")
            else:
                page = page.replace("База: 1 этаж · 2 319 строк Excel.", f"База обновлена из Excel · {len(items):,} строк.".replace(",", " "))
                st.success(f"Новый файл загружен: {len(items):,} строк товаров.".replace(",", " "))
                st.caption("Обновлённая база действует в текущем сеансе приложения.")
    except Exception as exc:
        st.error(f"Не удалось прочитать Excel: {exc}")
        st.info("Проверьте, что выбран файл .xlsx и в первой строке находятся названия столбцов.")

components.html(page, height=1900, scrolling=True)
