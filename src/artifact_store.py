"""Content-addressed loading and explicit session invalidation."""
import hashlib,json
from pathlib import Path
import joblib
import streamlit as st
def content_version(model_path,result_path):
    parts=[]
    for path in (model_path,result_path):
        parts.append(hashlib.sha256(Path(path).read_bytes()).hexdigest())
    return ":".join(parts)
@st.cache_resource(show_spinner=False,max_entries=4)
def _read_artifacts(model_path,result_path,version):
    pack=joblib.load(model_path)
    result=json.loads(Path(result_path).read_text(encoding="utf-8"))
    if content_version(model_path,result_path)!=version:
        raise RuntimeError("文件正在更新，请稍后重新加载")
    return pack,result
def load_artifacts(model_path,result_path):
    model_path=str(Path(model_path).resolve());result_path=str(Path(result_path).resolve())
    version=content_version(model_path,result_path)
    pack,result=_read_artifacts(model_path,result_path,version)
    if content_version(model_path,result_path)!=version:
        raise RuntimeError("文件正在更新，请稍后重新加载")
    return pack,result,version
def sync_session_version(state,version):
    previous=state.get("artifact_version")
    changed=previous is not None and previous!=version
    if changed:
        state.pop("history",None)
        state.pop("invalid_current",None)
    state["artifact_version"]=version
    return changed
