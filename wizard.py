"""Guided mode: plain-language questions that build an MDR Facts object for your own device."""
import streamlit as st

from engine import Facts, describe_facts
from ui_results import render_mdr_results

KIND = {"passive": "A physical product with no power source (instrument, implant, dressing, material...)",
        "active": "Powered or electronic equipment (needs an external energy source)",
        "software": "Software or an app"}
SW = {"other": "Does not inform clinical decisions", "informs": "Informs diagnostic or therapeutic decisions",
      "serious": "Decisions could cause serious deterioration or surgery",
      "irreversible": "Decisions could cause death or irreversible harm",
      "monitors": "Monitors physiological processes (not vital)",
      "monitors_vital": "Monitors vital parameters where changes mean immediate danger"}
CONTACT = {"none": "No body contact, or intact skin only",
           "orifice": "Enters a natural body opening (mouth, nose, ear, eye surface, stoma...)",
           "surgical": "Goes through the skin or a surgical opening, then is removed",
           "implant": "Is implanted and stays in the body"}
ORIFICE_SITE = {"anterior": "Mouth (as far as the pharynx), ear canal or nasal cavity",
                "other": "Anywhere else (eye surface, deeper airways, urinary tract, stoma...)"}
DURATION = {"transient": "Less than 60 minutes", "short_term": "60 minutes to 30 days",
            "long_term": "More than 30 days"}
SITE = {"other": "Elsewhere (bone, soft tissue, jaw...)", "teeth": "In the teeth",
        "heart_ccs_cns": "Heart, central blood vessels, brain or spinal cord"}
IMPLANT = {"none": "None of these", "active_implantable": "Active implantable device or accessory",
           "breast_or_mesh": "Breast implant or surgical mesh", "joint_replacement": "Joint replacement",
           "spinal": "Spinal disc or spinal column implant (not screws or plates)"}
INJURED = {"barrier": "Barrier, compression or absorbing exudate",
           "microenvironment": "Managing the wound micro-environment",
           "secondary_intent": "Wounds breaching the dermis that heal only by secondary intent",
           "other": "Other contact"}
ACT = {"treat": "Treats by delivering or exchanging energy (laser, stimulator, ventilator...)",
       "diagnose": "Diagnoses or monitors (imaging, vital signs...)",
       "deliver": "Delivers or removes medicines, liquids or substances (pump, suction...)",
       "control": "Controls or monitors another active device"}
DIAG = {"generic": "None of the specific cases below", "energy_absorbed": "Supplies energy the body absorbs",
        "visible_illumination": "Visible light used in the diagnosis itself",
        "radiopharm_imaging": "Images radiopharmaceuticals",
        "vital_monitoring": "Direct diagnosis or monitoring of vital processes",
        "vital_immediate_danger": "Vital parameters where changes mean immediate danger"}
CONTROLS = {"implantable": "An active implantable device (e.g. pacemaker programmer)",
            "iib": "A class IIb therapeutic device"}
SPECIAL = {"blood": "Handles blood, body liquids, cells, tissues, or liquids/gases for later administration",
           "in_vitro": "A substance used in vitro with human cells, tissues, organs or embryos",
           "disinfect": "Cleans, disinfects or sterilises other devices",
           "xray": "Records X-ray diagnostic images", "contraception": "Contraception or STI prevention",
           "tissue": "Made from non-viable human or animal tissue, cells or derivatives",
           "nano": "Contains nanomaterial",
           "substance": "A substance (gel, spray, liquid) put into the body or applied to skin",
           "inhalation": "Delivers medicine by inhalation"}
BLOOD = {"channel": "Only channels or stores them (tubing, containers)", "bag": "It is a blood bag",
         "modify_simple": "Modifies them by filtration, centrifugation or gas/heat exchange only",
         "modify_other": "Modifies them another way (e.g. dialysis)"}
DISINFECT = {"devices": "Disinfects or sterilises medical devices",
             "invasive": "Disinfectant or washer for invasive devices as the end point of processing",
             "lenses": "Contact lens care", "physical": "Cleans by physical action only (brush, ultrasonic bath)"}
TISSUE = {"animal": "Animal", "human": "Human"}
NANO = {"negligible": "Negligible", "low": "Low", "medium_high": "Medium or high"}
PURPOSE_SITE = {"skin_oral_nasal": "Skin, or oral/nasal cavity as far as the pharynx",
                "stomach_gi": "Stomach or lower gut", "other": "Elsewhere"}


def facts_from_answers(a: dict) -> Facts:
    """Pure mapping from wizard answers to MDR Facts (kept free of Streamlit so it can be tested)."""
    kw, kind = {}, a.get("kind", "passive")
    if kind == "software":
        kw["software"] = a.get("sw_role", "other")
    else:
        contact, dur = a.get("contact", "none"), a.get("duration", "transient")
        if contact == "orifice":
            kw.update(invasiveness="body_orifice", duration=dur, connected_active_iia_plus=bool(a.get("connects_active")),
                      site="oral_ear_nasal" if a.get("orifice_site") == "anterior" else "other")
        elif contact == "surgical":
            kw.update(invasiveness="surgical", duration=dur, site=a.get("site", "other"),
                      reusable_instrument=bool(a.get("reusable")),
                      connected_to_active_device=bool(a.get("connected_instrument")))
        elif contact == "implant":
            kw.update(invasiveness="implantable", duration="long_term", site=a.get("site", "other"),
                      special_implant=a.get("special_implant", "none"))
        if contact in ("orifice", "surgical", "implant"):
            kw.update(absorbed_or_bio=bool(a.get("absorbed")), chemical_change=bool(a.get("chemical")),
                      administers_medicinal=bool(a.get("administers")))
        kw["incorporates_medicinal"] = bool(a.get("incorporates_medicinal"))
        if a.get("touches_injured"):
            kw["injured_contact"] = a.get("injured_type", "other")
    if kind == "active":
        kw["active_device"], pur = True, a.get("act_purposes", [])
        if "treat" in pur:
            kw.update(active_therapeutic=True, hazardous_energy=bool(a.get("hazardous_energy")),
                      closed_loop=bool(a.get("closed_loop")))
        if "diagnose" in pur:
            kw.update(active_diagnostic=True, diag_mode=a.get("diag_mode", "generic"))
        if ("treat" in pur or "diagnose" in pur) and a.get("ionising"):
            kw["ionising"] = True
        if "deliver" in pur:
            kw.update(active_delivers_substances=True, hazardous_delivery=bool(a.get("hazardous_delivery")))
        if "control" in pur:
            kw["controls_active_implantable" if a.get("controls") == "implantable" else "controls_iib_therapeutic"] = True
    sp = a.get("special", [])
    if "blood" in sp:
        mode = a.get("blood_mode", "channel")
        if mode in ("channel", "bag"):
            kw.update(channels_or_stores=True, stores_body_material=bool(a.get("blood_material")) or mode == "bag",
                      blood_bag=mode == "bag")
            kw["connected_active_iia_plus"] = kw.get("connected_active_iia_plus", False) or bool(a.get("connects_active"))
        else:
            kw.update(modifies_composition=True, simple_treatment=mode == "modify_simple")
    if "in_vitro" in sp:
        kw["in_vitro_contact"] = True
    if "disinfect" in sp:
        mode = a.get("disinfect_mode", "devices")
        kw.update(disinfects_devices=mode in ("devices", "invasive", "physical"),
                  disinfects_invasive_endpoint=mode == "invasive", disinfects_contact_lenses=mode == "lenses",
                  cleans_physical_only=mode == "physical")
    if "xray" in sp:
        kw["records_xray"] = True
    if "contraception" in sp:
        kw["contraception_std"] = True
    if "tissue" in sp:
        kw.update(tissue_origin=a.get("tissue_origin", "animal"), intact_skin_only=bool(a.get("intact_skin_only")))
    if "nano" in sp:
        kw["nano_exposure"] = a.get("nano_exposure", "negligible")
    if "substance" in sp:
        kw.update(substance_based=True, systemically_absorbed=bool(a.get("systemic")),
                  purpose_site=a.get("purpose_site", "skin_oral_nasal"))
    if "inhalation" in sp:
        kw.update(inhalation_delivery=True, inhalation_critical=bool(a.get("inhalation_critical")))
    kw.update(sterile=bool(a.get("sterile")), measuring=bool(a.get("measuring")))
    return Facts(**kw)


def _pick(label, options, key):
    return st.selectbox(label, list(options), format_func=options.get, key=key)


def render_wizard():
    a = {}
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        st.caption("Answer for the intended purpose in your instructions for use, not for accidental use.")
        purpose = st.text_area("Intended purpose (optional; goes into the rationale draft)", key="wz_purpose", height=90)
        a["kind"] = st.radio("1. What is it?", list(KIND), format_func=KIND.get, key="wz_kind")
        if a["kind"] == "software":
            a["sw_role"] = _pick("2. What does the software do?", SW, "wz_sw")
            st.caption("Software that drives or influences a hardware device takes that device's class, so classify "
                       "the device instead (Annex VIII 3.3).")
        else:
            c = a["contact"] = st.radio("2. How does it contact the body?", list(CONTACT), format_func=CONTACT.get,
                                        key="wz_contact")
            if c == "orifice":
                a["orifice_site"] = _pick("Which opening?", ORIFICE_SITE, "wz_osite")
                a["duration"] = _pick("Continuous use", DURATION, "wz_dur_o")
                a["connects_active"] = st.checkbox("Connects to a powered device of class IIa or higher "
                                                   "(ventilator, suction pump...)", key="wz_conn")
            if c == "surgical":
                a["duration"] = _pick("Continuous use", DURATION, "wz_dur_s")
                a["site"] = _pick("Where does it act?", SITE, "wz_site_s")
                a["reusable"] = st.checkbox("A reusable surgical instrument (cutting, drilling, clamping...)",
                                            key="wz_reuse")
                a["connected_instrument"] = st.checkbox("It connects to a powered device (e.g. a handpiece)",
                                                        key="wz_connins")
            if c == "implant":
                a["site"] = _pick("Where is it placed?", SITE, "wz_site_i")
                a["special_implant"] = _pick("Is it one of these?", IMPLANT, "wz_impl")
            if c in ("orifice", "surgical", "implant"):
                a["absorbed"] = st.checkbox("Has a biological effect, or is wholly or mainly absorbed", key="wz_abs")
                a["chemical"] = st.checkbox("Undergoes ongoing chemical change in the body", key="wz_chem")
                a["administers"] = st.checkbox("Administers or holds a medicinal product for delivery", key="wz_adm")
            a["incorporates_medicinal"] = st.checkbox("Incorporates a substance that is a medicine in its own right "
                                                      "(e.g. antibiotic, heparin)", key="wz_inc")
            a["touches_injured"] = st.checkbox("Touches injured skin or mucous membrane (incl. scars)", key="wz_inj")
            if a["touches_injured"]:
                a["injured_type"] = _pick("What is it for?", INJURED, "wz_injt")
        if a["kind"] == "active":
            a["act_purposes"] = st.multiselect("3. What does it do? (pick all that apply)", list(ACT),
                                               format_func=ACT.get, key="wz_act")
            pur = a["act_purposes"]
            if "treat" in pur:
                a["hazardous_energy"] = st.checkbox("The energy could be potentially hazardous (judged on the "
                                                    "technology, not your mitigations)", key="wz_haz")
                a["closed_loop"] = st.checkbox("It has a built-in diagnostic function that drives the therapy "
                                               "(closed loop, AED)", key="wz_loop")
            if "diagnose" in pur:
                a["diag_mode"] = _pick("Which describes it best?", DIAG, "wz_diag")
            if "treat" in pur or "diagnose" in pur:
                a["ionising"] = st.checkbox("Emits ionising radiation", key="wz_ion")
            if "deliver" in pur:
                a["hazardous_delivery"] = st.checkbox("Delivery is potentially hazardous (substance, body part, mode)",
                                                      key="wz_hazd")
            if "control" in pur:
                a["controls"] = _pick("It controls or monitors...", CONTROLS, "wz_ctrl")
        a["special"] = st.multiselect("4. Does any of this apply?", list(SPECIAL), format_func=SPECIAL.get,
                                      key="wz_special")
        sp = a["special"]
        if "blood" in sp:
            a["blood_mode"] = _pick("What does it do with them?", BLOOD, "wz_blood")
            if a["blood_mode"] == "channel":
                a["blood_material"] = st.checkbox("It carries blood, body liquids, organs, cells or tissues "
                                                  "(not only gases or other liquids)", key="wz_bm")
                a["connects_active"] = a.get("connects_active") or st.checkbox(
                    "It may connect to a powered device of class IIa or higher", key="wz_conn2")
        if "disinfect" in sp:
            a["disinfect_mode"] = _pick("Which describes it?", DISINFECT, "wz_dis")
        if "tissue" in sp:
            a["tissue_origin"] = _pick("Origin", TISSUE, "wz_tis")
            a["intact_skin_only"] = st.checkbox("Touches intact skin only", key="wz_skin")
        if "nano" in sp:
            a["nano_exposure"] = _pick("Potential for internal exposure", NANO, "wz_nano")
        if "substance" in sp:
            a["systemic"] = st.checkbox("The substance or its metabolites are systemically absorbed to work",
                                        key="wz_sys")
            a["purpose_site"] = _pick("Where does it achieve its purpose?", PURPOSE_SITE, "wz_ps")
        if "inhalation" in sp:
            a["inhalation_critical"] = st.checkbox("Life-threatening condition, or the device's mode of action is "
                                                   "critical to efficacy and safety", key="wz_inh")
        a["sterile"] = st.checkbox("Supplied sterile", key="wz_ster")
        a["measuring"] = st.checkbox("Has a measuring function", key="wz_meas")
    facts = facts_from_answers(a)
    with right:
        with st.expander("How your answers were read", expanded=False):
            st.markdown("\n".join(f"- {d}" for d in describe_facts(facts)))
        render_mdr_results(facts, "Your device", "wz", purpose)
