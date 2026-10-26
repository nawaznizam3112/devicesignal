"""Example explorer: pick a library example, then edit any input."""
from dataclasses import asdict

import streamlit as st

from engine import CATEGORY_ORDER, PRESET_CATEGORY, PRESETS, Facts
from labels import BOOLS, LABELS
from ui_results import render_mdr_results

SPECIALTIES = ["All"] + [c for c in CATEGORY_ORDER if c in set(PRESET_CATEGORY.values())]


def load_preset():
    for k, v in asdict(PRESETS[st.session_state["preset"]]).items():
        st.session_state[f"f_{k}"] = v


def preset_names():
    return [n for n in PRESETS if st.session_state["category"] in ("All", PRESET_CATEGORY[n])]


def on_category():
    st.session_state["preset"] = preset_names()[0]
    load_preset()


def render_explorer():
    if "preset" not in st.session_state:
        st.session_state["category"] = "All"
        st.session_state["preset"] = next(iter(PRESETS))
        load_preset()
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        st.selectbox("Specialty", SPECIALTIES, key="category", on_change=on_category)
        st.selectbox("Start from an example", preset_names(), key="preset", on_change=load_preset)
        for name, (question, opts) in LABELS.items():
            st.selectbox(question, list(opts), format_func=opts.get, key=f"f_{name}")
        for group, items in BOOLS.items():
            with st.expander(group, expanded=False):
                for key, text in items.items():
                    st.checkbox(text, key=f"f_{key}")
    facts = Facts(**{k: st.session_state[f"f_{k}"] for k in asdict(Facts())})
    with right:
        render_mdr_results(facts, st.session_state["preset"], "ex")
