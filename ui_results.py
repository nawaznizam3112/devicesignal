"""Shared results panel for any MDR Facts object (explorer and wizard)."""
import pandas as pd
import streamlit as st

from engine import (DENTAL_LIST_URL, EURLEX, MDCG_URL, ORDER, PRESET_CATEGORY, PRESET_REFS, PRESETS, ROUTES,
                    RULE_INFO, SECTION, STATUS_HELP, UNCHECKED_RULES, classify, rationale_md, report_md, rule_status,
                    similar_examples, what_if)

COLORS = {"I": "#2e7d32", "IIa": "#f9a825", "IIb": "#ef6c00", "III": "#c62828"}
ICONS = {"Named in guidance": "✅", "Reasoned": "🟡", "Needs judgement": "⚠️"}


def banner(text, color):
    st.markdown(f"<div style='padding:1.2rem;border-radius:12px;background:{color};color:white;"
                f"text-align:center;font-size:2.4rem;font-weight:700'>{text}</div>", unsafe_allow_html=True)


def render_mdr_results(facts, name, prefix, intended_purpose=""):
    res = classify(facts)
    _, flips = what_if(facts)
    banner(f"Class {res.label}", COLORS[res.cls])
    t_why, t_cite, t_mdcg, t_what, t_route, t_rep = st.tabs(
        ["Why this class", "Citations", "MDCG check", "What-if lab", "Route to market", "Report"])
    with t_why:
        st.write("The **highest class among all triggered rules wins** (Annex VIII, Ch. II, 3.5).")
        df = pd.DataFrame([{"Rule": h.rule, "Class": h.cls, "Rationale": h.why, "Level": ORDER[h.cls] + 1}
                           for h in res.hits])
        st.dataframe(df.drop(columns="Level"), hide_index=True, width="stretch")
        if not df.empty:
            st.bar_chart(df.set_index("Rule")["Level"], horizontal=True)
    with t_cite:
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
    with t_mdcg:
        ref = PRESET_REFS.get(name)
        st.caption("Examples are cross-checked against MDCG 2021-24 Rev.1 (April 2026). Notes are paraphrased; "
                   "page numbers are as printed in the PDF.")
        if ref is None:
            st.info("Custom inputs have no direct cross-reference. Closest library examples, by rules triggered "
                    "and class:")
            st.dataframe(pd.DataFrame([{"Example": n, "Class": r.guidance_class,
                                        "Status": f"{ICONS[r.status]} {r.status}", "Where": r.location}
                                       for n, r in similar_examples(res)]), hide_index=True, width="stretch")
        else:
            if facts != PRESETS[name]:
                st.warning("You have edited the inputs. This check refers to the original example.")
            engine_cls = classify(PRESETS[name]).cls
            st.markdown(f"### {ICONS[ref.status]} {ref.status}")
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
        with st.expander("All examples"):
            st.dataframe(pd.DataFrame([{"Specialty": PRESET_CATEGORY[n], "Example": n,
                                        "Engine": classify(PRESETS[n]).cls, "Guidance": r.guidance_class,
                                        "Status": f"{ICONS[r.status]} {r.status}", "Where": r.location}
                                       for n, r in PRESET_REFS.items()]), hide_index=True, width="stretch")
        if any(h.rule in UNCHECKED_RULES for h in res.hits):
            st.info("Rules 20-22: the guidance example tables could not be retrieved, so results involving these "
                    "rules are not cross-checked. Compare them against MDCG 2021-24 Rev.1 manually.")
    with t_what:
        st.write("Single changes to your inputs that would move the classification:")
        if flips:
            st.dataframe(pd.DataFrame([(a, str(b), c) for a, b, c in flips],
                                      columns=["Input", "Changed to", "New class"]),
                         hide_index=True, width="stretch")
        else:
            st.info("No single-input change alters this classification.")
    with t_route:
        st.write(ROUTES[res.cls])
    with t_rep:
        md = report_md(name, facts, res)
        st.download_button("Download worksheet (.md)", md, file_name="mdr_classification.md", key=f"{prefix}_ws")
        rat = rationale_md(name, facts, res, intended_purpose)
        st.download_button("Download classification rationale draft (.md)", rat,
                           file_name="classification_rationale.md", key=f"{prefix}_rat")
        with st.expander("Preview the rationale draft"):
            st.markdown(rat)
