from dataclasses import asdict

import pandas as pd
import streamlit as st

from engine import ORDER, PRESETS, ROUTES, Facts, classify, report_md, what_if

st.set_page_config(page_title="MDR Classifier Lab", page_icon="🦷", layout="wide")

LABELS = {
    "invasiveness": ("How does it interact with the body?", {
        "non_invasive": "Non-invasive (intact skin / no penetration)",
        "body_orifice": "Invasive via body orifice (non-surgical)",
        "surgical": "Surgically invasive",
        "implantable": "Implantable"}),
    "duration": ("Continuous duration of use", {
        "transient": "Transient (< 60 min)",
        "short_term": "Short-term (60 min to 30 days)",
        "long_term": "Long-term (> 30 days)"}),
    "site": ("Where is it used or placed?", {
        "other": "Other site (e.g. jawbone, soft tissue)",
        "oral_ear_nasal": "Oral cavity to pharynx / ear canal / nasal cavity",
        "teeth": "In the teeth",
        "heart_ccs_cns": "Heart, central circulation or CNS"}),
    "software": ("Software impact on clinical decisions", {
        "none": "Not software / no decision input",
        "informs": "Informs diagnostic or therapeutic decisions",
        "serious": "Could cause serious deterioration / surgery",
        "irreversible": "Could cause death / irreversible harm"}),
}
BOOLS = {
    "Energy & radiation": {
        "active_therapeutic": "Active device delivering/exchanging energy to treat",
        "hazardous_energy": "...in a potentially hazardous way",
        "active_diagnostic": "Active diagnostic / monitoring device",
        "ionising": "Emits ionising radiation",
        "records_xray": "Records X-ray diagnostic images",
        "connected_active_iia_plus": "Connects to a class IIa+ active device"},
    "Biology & chemistry": {
        "absorbed_or_bio": "Biological effect, or wholly/mainly absorbed",
        "chemical_change": "Undergoes chemical change in the body",
        "administers_medicinal": "Administers medicinal products",
        "incorporates_medicinal": "Incorporates a medicinal substance",
        "reusable_instrument": "Reusable surgical instrument"},
    "Processing & markers": {
        "disinfects_devices": "Disinfects / sterilises medical devices",
        "disinfects_invasive_endpoint": "...as end point for invasive devices (solution/washer)",
        "sterile": "Supplied sterile", "measuring": "Has a measuring function"},
}
COLORS = {"I": "#2e7d32", "IIa": "#f9a825", "IIb": "#ef6c00", "III": "#c62828"}


def load_preset():
    for k, v in asdict(PRESETS[st.session_state["preset"]]).items():
        st.session_state[f"f_{k}"] = v


if "preset" not in st.session_state:
    st.session_state["preset"] = next(iter(PRESETS))
    load_preset()

st.title("🦷 Dental Device MDR Classifier Lab")
st.caption("Annex VIII of EU MDR 2017/745 as a transparent rule engine. Teaching subset: Rules 1, 5-11, 14, 16, 17.")

left, right = st.columns([1, 1.25], gap="large")
with left:
    st.selectbox("Start from a dental example", list(PRESETS), key="preset", on_change=load_preset)
    for name, (question, opts) in LABELS.items():
        st.selectbox(question, list(opts), format_func=opts.get, key=f"f_{name}")
    for group, items in BOOLS.items():
        with st.expander(group, expanded=group != "Processing & markers"):
            for key, text in items.items():
                st.checkbox(text, key=f"f_{key}")

facts = Facts(**{k: st.session_state[f"f_{k}"] for k in asdict(Facts())})
res = classify(facts)
base, flips = what_if(facts)

with right:
    st.markdown(
        f"<div style='padding:1.2rem;border-radius:12px;background:{COLORS[res.cls]};color:white;"
        f"text-align:center;font-size:2.4rem;font-weight:700'>Class {res.label}</div>",
        unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["Why this class", "What-if lab", "Route to market", "Report"])
    with tab1:
        st.write("The **highest class among all triggered rules wins** (Annex VIII, 3.5).")
        df = pd.DataFrame([{"Rule": h.rule, "Class": h.cls, "Rationale": h.why,
                            "Level": ORDER[h.cls] + 1} for h in res.hits])
        st.dataframe(df.drop(columns="Level"), hide_index=True, width="stretch")
        if not df.empty:
            st.bar_chart(df.set_index("Rule")["Level"], horizontal=True)
    with tab2:
        st.write("Single changes to your inputs that would move the classification:")
        if flips:
            st.dataframe(pd.DataFrame([(a, str(b), c) for a, b, c in flips], columns=["Input", "Changed to", "New class"]),
                         hide_index=True, width="stretch")
        else:
            st.info("No single-input change alters this classification.")
    with tab3:
        st.write(ROUTES[res.cls])
    with tab4:
        md = report_md(st.session_state["preset"], facts, res)
        st.download_button("Download worksheet (.md)", md, file_name="mdr_classification.md")
        st.markdown(md)
