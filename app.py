import streamlit as st
from pathlib import Path
import streamlit.components.v1 as components

st.set_page_config(page_title="Склад — поиск адреса", page_icon="📦", layout="centered", initial_sidebar_state="collapsed")
st.markdown("<style>.block-container{padding:0!important;max-width:760px!important}header{visibility:hidden}</style>", unsafe_allow_html=True)
html_path=Path(__file__).parent / "index.html"
if not html_path.exists():
    st.error("Не найден index.html. Убедитесь, что он загружен в GitHub вместе с app.py.")
else:
    page=html_path.read_text(encoding="utf-8")
    components.html(page, height=1900, scrolling=True)
