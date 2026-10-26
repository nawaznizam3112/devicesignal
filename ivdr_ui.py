"""IVDR mode: example library plus editable inputs, with citations and a rationale draft."""
from dataclasses import asdict

import pandas as pd
import streamlit as st

from ivdr import (IVD_BOOLS, IVD_CATEGORY, IVD_CATEGORY_ORDER, IVD_EURLEX, IVD_ORDER, IVD_PRESETS, IVD_REFS,
                  IVD_ROUTES, IVD_RULE_INFO, IVD_STATUS_HELP, RULE3, SECTION, IvdFacts, classify_ivd, ivd_rationale_md,
                  ivd_what_if)
from ui_results import banner

COLORS = {"A": "#2e7d32", "B": "#f9a825", "C": "#ef6c00", "D": "#c62828"}
ICONS = {"Named in Annex VIII": "✅", "Reported in MDCG 2020-16 (secondary)": "🟠", "Reasoned": "🟡"}


def _load():
    for k, v in asdict(IVD_PRESETS[st.session_state["iv_preset"]]).items():
        st.session_state[f"iv_f_{k}"] = list(v) if k == "rule3" else v


def _names():
    return [n for n in IVD_PRESETS if st.session_state["iv_category"] in ("All", IVD_CATEGORY[n])]


def _on_category():
    st.session_state["iv_preset"] = _names()[0]
    _load()


def render_ivdr():
    if "iv_preset" not in st.session_state:
        st.session_state["iv_category"] = "All"
        st.session_state["iv_preset"] = next(iter(IVD_PRESETS))
        _load()
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        st.selectbox("Specialty", ["All"] + IVD_CATEGORY_ORDER, key="iv_category", on_change=_on_category)
        st.selectbox("Start from an example", _names(), key="iv_preset", on_change=_load)
        purpose = st.text_area("Intended purpose (optional; goes into the rationale draft)", key="iv_purpose",
                               height=80)
        st.multiselect("Rule 3: class C purposes", list(RULE3), format_func=lambda k: f"({k}) {RULE3[k]}",
                       key="iv_f_rule3")
        for group, items in IVD_BOOLS.items():
            with st.expander(group, expanded=False):
                for key, text in items.items():
                    st.checkbox(text, key=f"iv_f_{key}")
        st.selectbox("Class of the device the calibrator/control is used with", list(IVD_ORDER), key="iv_f_parent_class")
    facts = IvdFacts(**{k: (tuple(sorted(st.session_state[f"iv_f_{k}"])) if k == "rule3"
                            else st.session_state[f"iv_f_{k}"]) for k in asdict(IvdFacts())})
    res, name = classify_ivd(facts), st.session_state["iv_preset"]
    with right:
        st.caption("IVDR Annex VIII: classes A (lowest) to D (highest). The higher class always governs.")
        banner(f"Class {res.cls}", COLORS[res.cls])
        t_why, t_cite, t_check, t_what, t_route, t_rep = st.tabs(
            ["Why this class", "Citations", "Guidance check", "What-if lab", "Route to market", "Report"])
        with t_why:
            st.dataframe(pd.DataFrame([{"Rule": h.rule, "Class": h.cls, "Rationale": h.why} for h in res.hits]),
                         hide_index=True, width="stretch")
        with t_cite:
            st.caption("Summaries are paraphrased; the authoritative wording is in the Regulation.")
            for h in res.hits:
                title, summary = IVD_RULE_INFO[h.rule]
                with st.expander(f"Rule {h.rule}: {title} → class {h.cls}", expanded=h.cls == res.cls):
                    st.markdown(f"**Where:** {h.ref}  \n**Applied because:** {h.why}  \n**Rule in brief:** {summary}")
                    st.markdown(f"[Regulation (EU) 2017/746 on EUR-Lex]({IVD_EURLEX})")
            fired = {h.rule for h in res.hits}
            st.dataframe(pd.DataFrame([{"Rule": r, "Topic": t, "Section": f"Annex VIII, {SECTION[r]}",
                                        "Triggered": "yes" if r in fired else "no"}
                                       for r, (t, _) in IVD_RULE_INFO.items()]), hide_index=True, width="stretch")
        with t_check:
            ref = IVD_REFS.get(name)
            st.caption("Annex VIII is verified. MDCG 2020-16 (Rev.5, 9 September 2026; only Rule 7 changed) could not "
                       "be retrieved in full, so examples are labelled by what supports them.")
            if ref:
                if facts != IVD_PRESETS[name]:
                    st.warning("You have edited the inputs. This check refers to the original example.")
                st.markdown(f"### {ICONS[ref.status]} {ref.status}")
                st.caption(IVD_STATUS_HELP[ref.status])
                c1, c2 = st.columns(2)
                c1.metric("Engine class", classify_ivd(IVD_PRESETS[name]).cls)
                c2.metric("Guidance / reasoned class", ref.guidance_class)
                st.markdown(f"**Where to look:** {ref.location}  \n{ref.note}")
            with st.expander("All examples"):
                st.dataframe(pd.DataFrame([{"Specialty": IVD_CATEGORY[n], "Example": n,
                                            "Engine": classify_ivd(IVD_PRESETS[n]).cls, "Guidance": r.guidance_class,
                                            "Status": f"{ICONS[r.status]} {r.status}"}
                                           for n, r in IVD_REFS.items()]), hide_index=True, width="stretch")
        with t_what:
            _, flips = ivd_what_if(facts)
            if flips:
                st.dataframe(pd.DataFrame(flips, columns=["Input", "Changed to", "New class"]), hide_index=True,
                             width="stretch")
            else:
                st.info("No single-input change alters this classification.")
        with t_route:
            st.write(IVD_ROUTES[res.cls])
            st.caption("Indicative only; verify against Article 48 and Annexes IX-XI.")
        with t_rep:
            md = ivd_rationale_md(name, facts, res, purpose)
            st.download_button("Download classification rationale draft (.md)", md,
                               file_name="ivdr_classification_rationale.md", key="iv_rat")
            with st.expander("Preview the rationale draft"):
                st.markdown(md)
