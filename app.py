from dataclasses import asdict

import pandas as pd
import streamlit as st

from engine import (DENTAL_LIST_URL, EURLEX, MDCG_URL, ORDER, PRESET_REFS, PRESETS, ROUTES, RULE_INFO, SECTION,
                    STATUS_HELP, Facts, classify, report_md, rule_status, what_if)
from labels import BOOLS, LABELS

st.set_page_config(page_title="MDR Classifier Lab", page_icon="🦷", layout="wide")
COLORS = {"I": "#2e7d32", "IIa": "#f9a825", "IIb": "#ef6c00", "III": "#c62828"}


def load_preset():
    for k, v in asdict(PRESETS[st.session_state["preset"]]).items():
        st.session_state[f"f_{k}"] = v


if "preset" not in st.session_state:
    st.session_state["preset"] = next(iter(PRESETS))
    load_preset()

st.title("🦷 Dental Device MDR Classifier Lab")
st.caption("EU MDR 2017/745 Annex VIII, Rules 1-22, as a transparent and cited rule engine.")

left, right = st.columns([1, 1.25], gap="large")
with left:
    st.selectbox("Start from a dental example", list(PRESETS), key="preset", on_change=load_preset)
    for name, (question, opts) in LABELS.items():
        st.selectbox(question, list(opts), format_func=opts.get, key=f"f_{name}")
    for group, items in BOOLS.items():
        with st.expander(group, expanded=False):
            for key, text in items.items():
                st.checkbox(text, key=f"f_{key}")

facts = Facts(**{k: st.session_state[f"f_{k}"] for k in asdict(Facts())})
res = classify(facts)
_, flips = what_if(facts)

with right:
    st.markdown(
        f"<div style='padding:1.2rem;border-radius:12px;background:{COLORS[res.cls]};color:white;"
        f"text-align:center;font-size:2.4rem;font-weight:700'>Class {res.label}</div>",
        unsafe_allow_html=True)
    tab1, tab2, tab_mdcg, tab3, tab4, tab5 = st.tabs(
        ["Why this class", "Citations", "MDCG check", "What-if lab", "Route to market", "Report"])
    with tab1:
        st.write("The **highest class among all triggered rules wins** (Annex VIII, Ch. II, 3.5).")
        df = pd.DataFrame([{"Rule": h.rule, "Class": h.cls, "Rationale": h.why, "Level": ORDER[h.cls] + 1}
                           for h in res.hits])
        st.dataframe(df.drop(columns="Level"), hide_index=True, width="stretch")
        if not df.empty:
            st.bar_chart(df.set_index("Rule")["Level"], horizontal=True)
    with tab2:
        st.caption("Rule summaries are paraphrased. The authoritative wording is in the Regulation; "
                   "MDCG 2021-24 gives worked guidance.")
        for h in res.hits:
            title, summary = RULE_INFO[h.rule]
            with st.expander(f"Rule {h.rule}: {title} → class {h.cls}", expanded=h.cls == res.cls):
                st.markdown(f"**Where:** {h.ref}  \n**Applied because:** {h.why}  \n**Rule in brief:** {summary}")
                st.markdown(f"[Regulation (EU) 2017/745 on EUR-Lex]({EURLEX})")
        status = rule_status(res)
        st.markdown("**All 22 rules at a glance**")
        st.dataframe(pd.DataFrame([{"Rule": r, "Topic": RULE_INFO[r][0], "Section": f"Annex VIII, {SECTION[r]}",
                                    "Result": status.get(r, "not triggered")} for r in RULE_INFO]),
                     hide_index=True, width="stretch")
    with tab3:
        st.write("Single changes to your inputs that would move the classification:")
        if flips:
            st.dataframe(pd.DataFrame([(a, str(b), c) for a, b, c in flips],
                                      columns=["Input", "Changed to", "New class"]),
                         hide_index=True, width="stretch")
        else:
            st.info("No single-input change alters this classification.")
    with tab4:
        st.write(ROUTES[res.cls])
    with tab5:
        md = report_md(st.session_state["preset"], facts, res)
        st.download_button("Download worksheet (.md)", md, file_name="mdr_classification.md")
        st.markdown(md)

    with tab_mdcg:
        name = st.session_state["preset"]
        ref = PRESET_REFS.get(name)
        icons = {"Named in guidance": "✅", "Reasoned": "🟡", "Needs judgement": "⚠️"}
        st.caption("Each dental example is cross-checked against MDCG 2021-24 Rev.1 (April 2026). "
                   "Notes are paraphrased; page numbers are as printed in the PDF.")
        if ref is None:
            st.info("The blank canvas has no guidance cross-reference. Pick a dental example to see one.")
        else:
            if facts != PRESETS[name]:
                st.warning("You have edited the inputs. This check refers to the original preset.")
            engine_cls = classify(PRESETS[name]).cls
            st.markdown(f"### {icons[ref.status]} {ref.status}")
            st.caption(STATUS_HELP[ref.status])
            c1, c2 = st.columns(2)
            c1.metric("Engine class", engine_cls)
            c2.metric("Guidance / reasoned class", ref.guidance_class)
            if engine_cls == ref.guidance_class:
                st.success("Engine and guidance agree.")
            else:
                st.error("Engine and guidance disagree. Treat this as a bug.")
            st.markdown(f"**Where to look:** MDCG 2021-24 Rev.1, section {ref.location}  \n{ref.note}")
        st.markdown(f"[MDCG 2021-24 Rev.1 (PDF)]({MDCG_URL}) · "
                    f"[Dental-device classification list, 2022 (secondary, industry-authored)]({DENTAL_LIST_URL})")
        st.markdown("**All examples**")
        st.dataframe(pd.DataFrame([{"Example": n, "Engine": classify(PRESETS[n]).cls, "Guidance": r.guidance_class,
                                    "Status": f"{icons[r.status]} {r.status}", "Where": r.location}
                                   for n, r in PRESET_REFS.items()]), hide_index=True, width="stretch")
