"""Streamlit host; camera pixels and inference stay inside the browser component."""
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

_component = components.declare_component(
    'raise_counter', path=str(Path(__file__).parent / 'raise_counter')
)

def render_raise_counter():
    st.title('抬手计数')
    st.write('实时做动作，或选择一段视频。让系统帮你数，也可以自己修正。')
    _component(key='raise_counter_v55', default=None)
