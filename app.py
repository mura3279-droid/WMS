from pathlib import Path
import streamlit as st
import pandas as pd

# Standalone Streamlit entry point: does not require a separate index.html.
st.set_page_config(page_title="Поиск адреса товара", page_icon="📦", layout="centered")
st.markdown("""
<style>
.block-container{max-width:760px;padding-top:1rem;padding-bottom:3rem}
.big-address{font-size:1.35rem;font-weight:800;color:#087f5b;word-break:break-word}
[data-testid="stMetric"]{background:#f4f7f9;padding:12px;border-radius:12px}
div.stButton>button,div.stDownloadButton>button{width:100%;min-height:48px;border-radius:12px}
@media(max-width:640px){.block-container{padding-left:.8rem;padding-right:.8rem}h1{font-size:1.55rem}}
</style>
""", unsafe_allow_html=True)

st.title("📦 Поиск адреса товара")
st.caption("Откройте на iPhone или Android. Можно искать по ШК, коду товара или названию.")

@st.cache_data(show_spinner=False)
def load_excel(file_bytes, filename):
    from io import BytesIO
    df = pd.read_excel(BytesIO(file_bytes), dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.isna().all()].fillna("")
    for c in df.columns:
        df[c] = df[c].astype(str).replace({"nan":"None", "None":""}).str.strip()
    return df

uploaded = st.file_uploader("Загрузить Excel-базу товаров", type=["xlsx", "xls"])
base_candidates = [Path(__file__).resolve().parent / "1 этаж адрес(1).xlsx", Path(__file__).resolve().parent / "1 этаж адрес.xlsx"]
if uploaded:
    df = load_excel(uploaded.getvalue(), uploaded.name)
else:
    local = next((p for p in base_candidates if p.exists()), None)
    if local:
        df = load_excel(local.read_bytes(), local.name)
    else:
        st.info("Загрузите Excel-файл, чтобы начать поиск. Отдельный index.html не требуется.")
        st.stop()

# Resolve column names flexibly.
def find_col(candidates):
    normalized = {str(c).strip().casefold(): c for c in df.columns}
    for candidate in candidates:
        if candidate.casefold() in normalized:
            return normalized[candidate.casefold()]
    return None

cols = {
    "barcode": find_col(["Штрих Код", "ШК", "Штрихкод", "Штрих-код", "Barcode"]),
    "sku": find_col(["Код SKU", "Код товара", "SKU", "КодТовара"]),
    "name": find_col(["Наименование SKU", "Наименование", "Название товара", "Товар"]),
    "group": find_col(["Группа", "Группа товара"]),
    "subgroup": find_col(["Подгруппа", "Подгруппа товара"]),
    "unit": find_col(["Единица измерения", "Ед. изм.", "Ед изм"]),
    "stock": find_col(["Доступный остаток", "Остаток", "Количество факт"]),
    "address": find_col(["Адрес", "Адрес хранения"]),
}

# Keep barcodes as strings (including leading zeroes).
query = st.text_input("Штрихкод / код товара / название", placeholder="Отсканируйте сканером или введите ШК вручную", key="lookup")
if query.strip():
    q = query.strip()
    searchable = [cols[k] for k in ("barcode", "sku", "name") if cols[k]]
    mask = pd.Series(False, index=df.index)
    for col in searchable:
        mask = mask | df[col].astype(str).str.contains(q, case=False, na=False, regex=False)
    found = df[mask]
    if found.empty:
        st.error("ШК или товар не найден. Проверьте цифры и попробуйте ещё раз.")
    else:
        # Group duplicate rows for same product, preserving every unique address.
        first = found.iloc[0]
        def v(row, key):
            c = cols.get(key)
            return str(row[c]).strip() if c else "—"
        st.success(f"Найдено совпадений: {len(found)}")
        st.subheader(v(first, "name") or "Товар без наименования")
        a, b = st.columns(2)
        a.metric("ШК", v(first, "barcode"))
        b.metric("Код товара", v(first, "sku"))
        st.write("**Группа:**", v(first, "group"))
        st.write("**Подгруппа:**", v(first, "subgroup"))
        st.write("**Доступный остаток:**", (v(first, "stock") + " " + v(first, "unit")).strip())
        addresses = []
        if cols["address"]:
            for value in found[cols["address"]].astype(str).str.strip().tolist():
                if value and value not in addresses:
                    addresses.append(value)
        st.markdown("### 📍 Адреса хранения")
        if not addresses:
            st.warning("Адрес не указан в Excel")
        for i, address in enumerate(addresses, 1):
            parts = address.split(".")
            st.markdown(f"**Адрес №{i}**")
            st.markdown(f'<div class="big-address">{address}</div>', unsafe_allow_html=True)
            if len(parts) == 5:
                labels = ["Склад", "Зона", "Аллея", "Модуль", "Полка"]
                grid = st.columns(5)
                for c, label, value in zip(grid, labels, parts):
                    c.metric(label, value)
            else:
                st.caption("Формат адреса отличается от ожидаемого: склад.зона.аллея.модуль.полка")
        if len(found) > 1:
            st.caption("Показаны все строки Excel, совпавшие с запросом. Если у товара несколько адресов, они отображаются отдельно.")
else:
    st.info("Наведите камеру сканера ТСД или подключённого сканера на штрихкод — если устройство вводит ШК как клавиатуру, цифры появятся в поле выше. Если сканер недоступен, введите ШК вручную.")

with st.expander("Проверка структуры Excel"):
    st.write("Колонки распознаны:")
    st.json({k: (v or "не найдена") for k, v in cols.items()})
    st.caption("Это приложение работает без index.html: замените только app.py в GitHub.")
