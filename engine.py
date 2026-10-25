"""Rule engine for EU MDR (Regulation 2017/745) Annex VIII classification, Rules 1-22.

Built against the Annex VIII text in OJ L 117, 5.5.2017. Educational tool: verify against the
Regulation and MDCG 2021-24. Not modelled: implementing rules 3.2 (combinations/accessories)
and 3.4 (most critical use); apply those by classifying each device or use case separately.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace

EURLEX = "https://eur-lex.europa.eu/eli/reg/2017/745/oj"
ORDER = {"I": 0, "IIa": 1, "IIb": 2, "III": 3}
CHOICES = {
    "invasiveness": ["non_invasive", "body_orifice", "surgical", "implantable"],
    "duration": ["transient", "short_term", "long_term"],
    "site": ["other", "oral_ear_nasal", "teeth", "heart_ccs_cns"],
    "software": ["none", "other", "informs", "serious", "irreversible", "monitors", "monitors_vital"],
    "injured_contact": ["none", "barrier", "secondary_intent", "microenvironment", "other"],
    "special_implant": ["none", "active_implantable", "breast_or_mesh", "joint_replacement", "spinal"],
    "diag_mode": ["generic", "energy_absorbed", "visible_illumination", "radiopharm_imaging",
                  "vital_monitoring", "vital_immediate_danger"],
    "tissue_origin": ["none", "human", "animal"],
    "nano_exposure": ["none", "negligible", "low", "medium_high"],
    "purpose_site": ["skin_oral_nasal", "stomach_gi", "other"],
}


@dataclass(frozen=True)
class Facts:
    invasiveness: str = "non_invasive"
    duration: str = "transient"
    site: str = "other"
    software: str = "none"
    injured_contact: str = "none"
    special_implant: str = "none"
    diag_mode: str = "generic"
    tissue_origin: str = "none"
    nano_exposure: str = "none"
    purpose_site: str = "skin_oral_nasal"
    # body interaction
    absorbed_or_bio: bool = False
    chemical_change: bool = False
    administers_medicinal: bool = False
    incorporates_medicinal: bool = False
    reusable_instrument: bool = False
    connected_to_active_device: bool = False
    connected_active_iia_plus: bool = False
    # active devices
    active_device: bool = False
    active_therapeutic: bool = False
    hazardous_energy: bool = False
    controls_iib_therapeutic: bool = False
    controls_active_implantable: bool = False
    closed_loop: bool = False
    active_diagnostic: bool = False
    ionising: bool = False
    records_xray: bool = False
    active_delivers_substances: bool = False
    hazardous_delivery: bool = False
    # non-invasive handling of body material
    channels_or_stores: bool = False
    stores_body_material: bool = False
    blood_bag: bool = False
    modifies_composition: bool = False
    simple_treatment: bool = False
    in_vitro_contact: bool = False
    # special rules
    contraception_std: bool = False
    disinfects_devices: bool = False
    disinfects_invasive_endpoint: bool = False
    disinfects_contact_lenses: bool = False
    cleans_physical_only: bool = False
    intact_skin_only: bool = False
    substance_based: bool = False
    systemically_absorbed: bool = False
    inhalation_delivery: bool = False
    inhalation_critical: bool = False
    # class I markers
    sterile: bool = False
    measuring: bool = False


@dataclass(frozen=True)
class Hit:
    rule: str
    cls: str
    why: str
    ref: str


SECTION = {"1": "4.1", "2": "4.2", "3": "4.3", "4": "4.4", "5": "5.1", "6": "5.2", "7": "5.3", "8": "5.4",
           "9": "6.1", "10": "6.2", "11": "6.3", "12": "6.4", "13": "6.5", "14": "7.1", "15": "7.2",
           "16": "7.3", "17": "7.4", "18": "7.5", "19": "7.6", "20": "7.7", "21": "7.8", "22": "7.9"}


def _h(rule, cls, why, part=""):
    ref = f"Annex VIII, Ch. III, {SECTION[rule]}" + (f" ({part})" if part else "")
    return Hit(rule, cls, why, ref)


def _build(rule, cls, why, part, extras):
    for cond, c, text, p in extras:
        if cond and ORDER[c] > ORDER[cls]:
            cls, why, part = c, text, p
    return _h(rule, cls, why, part)


def rule_1(f):
    if f.invasiveness == "non_invasive":
        return _h("1", "I", "Non-invasive device: default class I unless a later rule applies.")


def rule_2(f):
    if f.invasiveness != "non_invasive" or not f.channels_or_stores:
        return None
    return _build("2", "I", "Channelling/storing device meeting none of the raising criteria.", "closing line", [
        (f.connected_active_iia_plus, "IIa", "May be connected to a class IIa/IIb/III active device.", "1st indent"),
        (f.stores_body_material, "IIa", "Channels or stores blood, body liquids, organs, cells or tissues.",
         "2nd indent"),
        (f.stores_body_material and f.blood_bag, "IIb", "Blood bag (named exception within the 2nd indent).",
         "2nd indent"),
    ])


def rule_3(f):
    if f.invasiveness != "non_invasive" or not (f.modifies_composition or f.in_vitro_contact):
        return None
    if f.modifies_composition and f.simple_treatment:
        base = ("IIa", "Alters composition by filtration, centrifugation or gas/heat exchange only.", "para 1")
    elif f.modifies_composition:
        base = ("IIb", "Modifies biological/chemical composition of cells, tissues, blood or liquids.", "para 1")
    else:
        base = ("I", "", "para 2")
    return _build("3", *base, [(f.in_vitro_contact, "III",
                                "Substance used in vitro in direct contact with human cells, tissues, organs "
                                "or pre-implantation embryos.", "para 2")])


def rule_4(f):
    table = {
        "barrier": ("I", "Mechanical barrier, compression or absorption of exudates.", "1st indent"),
        "secondary_intent": ("IIb", "Injuries breaching the dermis/mucosa that heal only by secondary intent.",
                             "2nd indent"),
        "microenvironment": ("IIa", "Manages the micro-environment of injured skin or mucosa.", "3rd indent"),
        "other": ("IIa", "Other contact with injured skin or mucosa.", "4th indent"),
    }
    if f.injured_contact in table:
        return _h("4", *table[f.injured_contact])


def rule_5(f):
    if f.invasiveness != "body_orifice":
        return None
    oral = f.site == "oral_ear_nasal"
    if f.connected_active_iia_plus:
        return _h("5", "IIa", "Orifice-invasive device connected to a class IIa/IIb/III active device.", "para 2")
    if f.duration == "transient":
        return _h("5", "I", "Transient use via a body orifice.", "1st indent")
    if f.duration == "short_term":
        if oral:
            return _h("5", "I", "Short-term use in oral cavity (to pharynx), ear canal or nasal cavity.",
                      "2nd indent exception")
        return _h("5", "IIa", "Short-term use via another body orifice.", "2nd indent")
    if oral and not f.absorbed_or_bio:
        return _h("5", "IIa", "Long-term use in oral/ear/nasal cavity and not liable to be absorbed.",
                  "3rd indent exception")
    return _h("5", "IIb", "Long-term use via a body orifice.", "3rd indent")


def rule_6(f):
    if f.invasiveness != "surgical" or f.duration != "transient":
        return None
    if f.reusable_instrument and not f.connected_to_active_device:
        base = ("I", "Reusable surgical instrument without connection to an active device.", "2nd indent")
    else:
        base = ("IIa", "Transient surgically invasive device: default class IIa.", "lead-in")
    return _build("6", *base, [
        (f.site == "heart_ccs_cns", "III", "Direct contact with heart, central circulation or CNS.", "3rd indent"),
        (f.ionising, "IIb", "Supplies energy as ionising radiation.", "4th indent"),
        (f.absorbed_or_bio, "IIb", "Biological effect or wholly/mainly absorbed.", "5th indent"),
        (f.administers_medicinal, "IIb", "Administers medicinal products (potentially hazardous mode).",
         "6th indent"),
    ])


def rule_7(f):
    if f.invasiveness != "surgical" or f.duration != "short_term":
        return None
    return _build("7", "IIa", "Short-term surgically invasive device: default class IIa.", "lead-in", [
        (f.site == "heart_ccs_cns", "III", "Direct contact with heart, central circulation or CNS.", "2nd indent"),
        (f.ionising, "IIb", "Supplies energy as ionising radiation.", "3rd indent"),
        (f.absorbed_or_bio, "III", "Biological effect or wholly/mainly absorbed.", "4th indent"),
        (f.chemical_change and f.site != "teeth", "IIb", "Chemical change in the body (not in teeth).",
         "5th indent"),
        (f.administers_medicinal, "IIb", "Administers medicines.", "6th indent"),
    ])


SPECIAL_IMPLANTS = {
    "active_implantable": ("Active implantable device or its accessory.", "6th indent"),
    "breast_or_mesh": ("Breast implant or surgical mesh.", "7th indent"),
    "joint_replacement": ("Total or partial joint replacement (ancillary screws, plates etc. excepted).",
                          "8th indent"),
    "spinal": ("Spinal disc replacement or implant contacting the spinal column (screws, plates etc. excepted).",
               "9th indent"),
}


def rule_8(f):
    if not (f.invasiveness == "implantable" or (f.invasiveness == "surgical" and f.duration == "long_term")):
        return None
    if f.site == "teeth":
        base = ("IIa", "Placed in the teeth.", "1st indent")
    else:
        base = ("IIb", "Implantable or long-term surgically invasive device: default class IIb.", "lead-in")
    why, part = SPECIAL_IMPLANTS.get(f.special_implant, ("", ""))
    return _build("8", *base, [
        (f.site == "heart_ccs_cns", "III", "Direct contact with heart, central circulation or CNS.", "2nd indent"),
        (f.absorbed_or_bio, "III", "Biological effect or wholly/mainly absorbed.", "3rd indent"),
        (f.chemical_change and f.site != "teeth", "III", "Chemical change in the body (not in teeth).",
         "4th indent"),
        (f.administers_medicinal, "III", "Administers medicinal products.", "5th indent"),
        (f.special_implant != "none", "III", why, part),
    ])


def rule_9(f):
    if not (f.active_therapeutic or f.controls_iib_therapeutic or f.controls_active_implantable):
        return None
    base = ("IIa", "Active therapeutic device administering or exchanging energy.", "para 1") \
        if f.active_therapeutic else ("IIb", "Controls or influences a class IIb therapeutic device.", "para 2")
    return _build("9", *base, [
        (f.active_therapeutic and f.hazardous_energy, "IIb", "Energy exchange in a potentially hazardous way.",
         "para 1"),
        (f.controls_iib_therapeutic, "IIb", "Controls, monitors or influences a class IIb therapeutic device.",
         "para 2"),
        (f.active_therapeutic and f.ionising, "IIb", "Emits ionising radiation for therapy.", "para 3"),
        (f.controls_active_implantable, "III", "Controls, monitors or influences an active implantable device.",
         "para 4"),
    ])


DIAG = {
    "energy_absorbed": ("IIa", "Supplies energy that the body absorbs.", "1st indent"),
    "visible_illumination": ("I", "Only illuminates the body in the visible spectrum (exception to 1st indent).",
                             "1st indent"),
    "radiopharm_imaging": ("IIa", "Images in vivo distribution of radiopharmaceuticals.", "2nd indent"),
    "vital_monitoring": ("IIa", "Direct diagnosis or monitoring of vital physiological processes.", "3rd indent"),
    "vital_immediate_danger": ("IIb", "Vital parameters where variation means immediate danger to the patient.",
                               "3rd indent"),
}


def rule_10(f):
    if not f.active_diagnostic:
        return None
    base = DIAG.get(f.diag_mode)
    if f.ionising:
        return _build("10", *(base or ("I", "", "")),
                      [(True, "IIb", "Emits ionising radiation for diagnostic radiology.", "para 2")])
    return _h("10", *base) if base else None


SOFTWARE = {
    "informs": ("IIa", "Software informing diagnostic or therapeutic decisions.", "para 1"),
    "serious": ("IIb", "Decisions could cause serious deterioration or surgical intervention.", "para 1, 2nd indent"),
    "irreversible": ("III", "Decisions could cause death or irreversible deterioration.", "para 1, 1st indent"),
    "monitors": ("IIa", "Software monitoring physiological processes.", "para 2"),
    "monitors_vital": ("IIb", "Monitors vital parameters where variation means immediate danger.", "para 2"),
    "other": ("I", "All other software.", "para 3"),
}


def rule_11(f):
    if f.software in SOFTWARE:
        return _h("11", *SOFTWARE[f.software])


def rule_12(f):
    if f.active_delivers_substances:
        if f.hazardous_delivery:
            return _h("12", "IIb", "Administers/removes substances in a potentially hazardous manner.")
        return _h("12", "IIa", "Administers or removes medicinal products, body liquids or substances.")


def rule_13(f):
    if f.active_device and not any(r(f) for r in (rule_9, rule_10, rule_11, rule_12)):
        return _h("13", "I", "Active device not covered by Rules 9-12.")


def rule_14(f):
    if f.incorporates_medicinal:
        return _h("14", "III", "Integral substance that is a medicinal product on its own, acting ancillary.")


def rule_15(f):
    if f.contraception_std:
        long_inv = f.invasiveness == "implantable" or (
            f.invasiveness in ("body_orifice", "surgical") and f.duration == "long_term")
        if long_inv:
            return _h("15", "III", "Contraception/STI prevention that is implantable or long-term invasive.")
        return _h("15", "IIb", "Contraception or prevention of sexually transmitted disease.")


def rule_16(f):
    if f.disinfects_contact_lenses:
        return _h("16", "IIb", "Disinfecting, cleaning, rinsing or hydrating contact lenses.", "para 1")
    if f.disinfects_devices and not f.cleans_physical_only:
        if f.disinfects_invasive_endpoint:
            return _h("16", "IIb", "Disinfectant/washer-disinfector for invasive devices as end point.", "para 2")
        return _h("16", "IIa", "Disinfecting or sterilising medical devices.", "para 2")


def rule_17(f):
    if f.records_xray:
        return _h("17", "IIa", "Specifically intended for recording X-ray diagnostic images.")


def rule_18(f):
    if f.tissue_origin != "none" and not (f.tissue_origin == "animal" and f.intact_skin_only):
        return _h("18", "III", "Made with non-viable human/animal tissues, cells or derivatives.")


def rule_19(f):
    table = {"negligible": "IIa", "low": "IIb", "medium_high": "III"}
    if f.nano_exposure in table:
        return _h("19", table[f.nano_exposure], f"Nanomaterial with {f.nano_exposure.replace('_', '/')} "
                  "potential for internal exposure.")


def rule_20(f):
    if f.inhalation_delivery and f.invasiveness == "body_orifice":
        if f.inhalation_critical:
            return _h("20", "IIb", "Inhalation delivery where mode of action is critical or condition life-threatening.")
        return _h("20", "IIa", "Orifice-invasive device delivering medicinal products by inhalation.")


def rule_21(f):
    if not f.substance_based:
        return None
    if f.systemically_absorbed:
        part = "2nd indent" if f.purpose_site == "stomach_gi" else "1st indent"
        return _h("21", "III", "Substance (or metabolites) systemically absorbed to achieve its purpose.", part)
    if f.purpose_site == "skin_oral_nasal":
        return _h("21", "IIa", "Applied to skin or oral/nasal cavity (to pharynx), acting locally.", "3rd indent")
    return _h("21", "IIb", "Substance-based device in all other cases.", "4th indent")


def rule_22(f):
    if f.active_therapeutic and f.closed_loop:
        return _h("22", "III", "Active therapeutic device with integrated diagnostic function driving management.")


RULES = [rule_1, rule_2, rule_3, rule_4, rule_5, rule_6, rule_7, rule_8, rule_9, rule_10, rule_11, rule_12,
         rule_13, rule_14, rule_15, rule_16, rule_17, rule_18, rule_19, rule_20, rule_21, rule_22]

RULE_INFO = {
    "1": ("Non-invasive default", "Devices that do not enter the body are class I unless a later rule raises them."),
    "2": ("Channelling and storing", "Non-invasive channels/containers for body liquids, cells or tissues that "
          "return to the body: IIa if connectable to an active IIa+ device or used for body liquids, organs, cells "
          "or tissues; blood bags IIb; otherwise I."),
    "3": ("Modifying body liquids", "Non-invasive devices altering composition of blood, cells, tissues or liquids "
          "bound for the body: IIb, or IIa for filtration, centrifugation, gas/heat exchange. Substances used in "
          "vitro on human cells, tissues, organs or pre-implantation embryos: III."),
    "4": ("Injured skin or mucosa", "I for barrier, compression or exudate absorption; IIb for wounds healing only "
          "by secondary intent; IIa for micro-environment management and all other cases. Reaches invasive devices "
          "touching injured mucosa."),
    "5": ("Orifice-invasive devices", "Class by duration (I, IIa, IIb), lower for oral cavity to pharynx, ear canal "
          "to drum and nasal cavity; IIa if linked to an active IIa+ device."),
    "6": ("Transient surgically invasive", "Default IIa. Reusable instruments I; ionising energy, biological "
          "effect/absorption or hazardous drug delivery IIb; heart, central circulation or CNS contact III."),
    "7": ("Short-term surgically invasive", "Default IIa. Ionising energy, chemical change (not in teeth) or "
          "medicine delivery IIb; heart/CCS/CNS contact or biological effect/absorption III."),
    "8": ("Implantable and long-term surgically invasive", "Default IIb; placed in teeth IIa. III for heart/CCS/CNS "
          "contact, biological effect/absorption, chemical change (not in teeth), medicine delivery, active "
          "implantables, breast implants, meshes, joint replacements and spinal implants."),
    "9": ("Active therapeutic devices", "Energy delivery IIa, IIb if potentially hazardous; controllers of IIb "
          "therapeutic devices and therapeutic ionising radiation IIb; controllers of active implantables III."),
    "10": ("Active diagnostic and monitoring", "IIa for energy absorbed by the body (visible-light illumination is "
           "I), radiopharmaceutical imaging, or direct diagnosis/monitoring of vital processes (IIb if immediate "
           "danger). Diagnostic ionising radiation IIb."),
    "11": ("Software", "Decision-informing software IIa; IIb if serious deterioration or surgery could follow; III "
           "if death or irreversible harm. Physiological monitoring IIa (immediate-danger vital parameters IIb). "
           "Other software I."),
    "12": ("Active delivery or removal", "Active devices administering or removing medicinal products, body "
           "liquids or substances: IIa, IIb if potentially hazardous."),
    "13": ("Other active devices", "Active devices not caught by Rules 9-12 are class I."),
    "14": ("Medicinal substance incorporated", "Integral substance that alone would be a medicinal product and acts "
           "ancillary to the device: III."),
    "15": ("Contraception and STI prevention", "IIb; III if implantable or long-term invasive."),
    "16": ("Disinfection and sterilisation", "Contact-lens care IIb; disinfecting/sterilising devices IIa, or IIb "
           "for disinfectants and washer-disinfectors serving invasive devices as end point. Purely physical "
           "cleaning of non-lens devices is out of scope."),
    "17": ("X-ray image recording", "Devices specifically for recording X-ray diagnostic images: IIa."),
    "18": ("Non-viable tissues or cells", "Devices made with non-viable human or animal tissues, cells or "
           "derivatives: III, except animal-derived devices touching intact skin only."),
    "19": ("Nanomaterials", "By potential for internal exposure: high or medium III, low IIb, negligible IIa."),
    "20": ("Inhalation drug delivery", "Orifice-invasive devices delivering medicinal products by inhalation: IIa; "
           "IIb if mode of action is critical to efficacy/safety or the condition is life-threatening."),
    "21": ("Substance-based devices", "Substances introduced via an orifice or applied to skin and absorbed or "
           "dispersed: III if systemically absorbed to achieve purpose; IIa for skin or oral/nasal cavity acting "
           "locally; IIb otherwise."),
    "22": ("Closed-loop therapy", "Active therapeutic devices with an integrated diagnostic function that "
           "significantly determines patient management (closed loop, AEDs): III."),
}


@dataclass(frozen=True)
class Result:
    cls: str
    label: str
    hits: tuple


def classify(f: Facts) -> Result:
    hits = tuple(h for r in RULES if (h := r(f)))
    cls = max((h.cls for h in hits), key=ORDER.__getitem__) if hits else "I"
    label = cls
    if cls == "I":
        ir = f.reusable_instrument and not f.connected_to_active_device
        label += ("s" if f.sterile else "") + ("m" if f.measuring else "") + ("r" if ir else "")
    return Result(cls, label, hits)


def rule_status(res: Result) -> dict:
    out = {}
    for h in res.hits:
        if h.rule not in out or ORDER[h.cls] > ORDER[out[h.rule]]:
            out[h.rule] = h.cls
    return out


OPTIONS = {x.name: CHOICES.get(x.name, [False, True]) for x in fields(Facts)}


def what_if(f: Facts):
    """Flip each single input; return the changes that move the final class."""
    base = classify(f).cls
    out = []
    for name, opts in OPTIONS.items():
        for opt in opts:
            if opt != getattr(f, name):
                new = classify(replace(f, **{name: opt})).cls
                if new != base:
                    out.append((name, opt, new))
    return base, out


ROUTES = {
    "I": "Manufacturer self-declaration (Annex II technical documentation + Annex IV DoC). "
         "Notified Body only for Is (sterility), Im (measuring) or Ir (reuse processing) aspects.",
    "IIa": "Notified Body required. Annex IX (QMS + technical documentation sampling) or "
           "Annex XI Part A (product conformity verification) with Annex II/III documentation.",
    "IIb": "Notified Body required. Annex IX Ch. I & III (QMS + documentation assessment, "
           "at least one device per generic group) or Annex X + XI.",
    "III": "Notified Body required. Annex IX Ch. I & II (full technical documentation assessment "
           "per device) or Annex X + XI. Clinical evaluation consultation may apply to implantables.",
}

_A = dict(active_device=True)
PRESETS = {
    "Alginate impression material": Facts(invasiveness="body_orifice", duration="short_term", site="oral_ear_nasal"),
    "Clear orthodontic aligner": Facts(invasiveness="body_orifice", duration="long_term", site="oral_ear_nasal"),
    "Composite filling material": Facts(invasiveness="surgical", duration="long_term", site="teeth"),
    "Dental implant (placed in jawbone)": Facts(invasiveness="implantable", duration="long_term"),
    "Resorbable bone graft": Facts(invasiveness="implantable", duration="long_term", absorbed_or_bio=True),
    "Resorbable porcine collagen membrane": Facts(invasiveness="implantable", duration="long_term",
                                                  absorbed_or_bio=True, tissue_origin="animal"),
    "Hand excavator / curette (reusable)": Facts(invasiveness="surgical", reusable_instrument=True),
    "Handpiece-driven dental bur (reusable)": Facts(invasiveness="surgical", reusable_instrument=True,
                                                    connected_to_active_device=True),
    "Dental X-ray generator": Facts(active_diagnostic=True, ionising=True, **_A),
    "Intraoral X-ray sensor": Facts(records_xray=True),
    "Intraoral camera (light for visibility only)": Facts(active_diagnostic=True, **_A),
    "Laser caries detector": Facts(active_diagnostic=True, diag_mode="energy_absorbed", **_A),
    "Diode dental laser": Facts(active_therapeutic=True, hazardous_energy=True, **_A),
    "Computer-controlled anaesthetic delivery unit": Facts(active_delivers_substances=True, **_A),
    "Benchtop steam steriliser": Facts(disinfects_devices=True, **_A),
    "Ultrasonic instrument cleaner (physical action)": Facts(disinfects_devices=True, cleans_physical_only=True,
                                                             **_A),
    "Caries-detection AI software": Facts(software="informs"),
    "PRF blood collection tube": Facts(channels_or_stores=True, stores_body_material=True),
    "PRF centrifuge": Facts(modifies_composition=True, simple_treatment=True, **_A),
    "Saliva substitute (substance-based)": Facts(substance_based=True),
    "Gauze compression pad on oral wound": Facts(injured_contact="barrier"),
    "Dental handpiece (powered)": Facts(active_therapeutic=True, **_A),
    "Electric pulp tester": Facts(active_diagnostic=True, diag_mode="energy_absorbed", **_A),
    "Dental aspirator tip": Facts(invasiveness="body_orifice", site="oral_ear_nasal", connected_active_iia_plus=True),
    "Dental curing light": Facts(**_A),
    "Washer-disinfector for dental instruments": Facts(disinfects_devices=True, disinfects_invasive_endpoint=True,
                                                       **_A),
    "Fissure sealant": Facts(invasiveness="body_orifice", duration="long_term", site="oral_ear_nasal"),
    "Temporary filling material": Facts(invasiveness="surgical", duration="short_term", site="teeth"),
    "Endodontic material with antibiotic": Facts(invasiveness="surgical", duration="long_term", site="teeth",
                                                 incorporates_medicinal=True),
    "Nano-filled composite (embedded nanomaterial)": Facts(invasiveness="surgical", duration="long_term",
                                                           site="teeth", nano_exposure="negligible"),
    "Blank canvas": Facts(),
}


def report_md(name: str, f: Facts, res: Result) -> str:
    lines = [f"# MDR classification worksheet: {name}", "", f"**Result: Class {res.label}**", "",
             "## Rules triggered", "", "| Rule | Class | Where in Annex VIII | Rationale |", "|---|---|---|---|"]
    lines += [f"| {h.rule} {RULE_INFO[h.rule][0]} | {h.cls} | {h.ref} | {h.why} |" for h in res.hits]
    lines += ["", "Highest class among triggered rules governs (Annex VIII, Ch. II, 3.5).", "",
              "## Inputs", ""] + [f"- {k}: {getattr(f, k)}" for k in OPTIONS]
    lines += ["", "## Indicative conformity route", "", ROUTES[res.cls], "", f"Regulation text: {EURLEX}", "",
              "_Teaching tool. Verify against Regulation (EU) 2017/745 and MDCG 2021-24._"]
    return "\n".join(lines)


# ---- Cross-reference of presets against MDCG 2021-24 Rev.1 (April 2026) ----
MDCG_URL = "https://health.ec.europa.eu/document/download/cbb19821-a517-4e13-bf87-fdc6ddd1782e_en"
DENTAL_LIST_URL = ("https://www.fide-online.org/wp-content/uploads/2023/10/"
                   "Classification_of_dental_devices_according_MDR_2022-02-01-final.pdf")
NAMED, REASONED, JUDGEMENT = "Named in guidance", "Reasoned", "Needs judgement"
STATUS_HELP = {
    NAMED: "The guidance lists this device type (or states the point) in the rule's examples or notes.",
    REASONED: "Consistent with the rule text, but no named example was found. Document your argument.",
    JUDGEMENT: "The class depends on intended-purpose wording or a hazard argument.",
}


@dataclass(frozen=True)
class PresetRef:
    status: str
    guidance_class: str
    location: str
    note: str


PRESET_REFS = {
    "Alginate impression material": PresetRef(NAMED, "I", "4.2 Rule 5, p. 34",
        "Dental impression materials are class I examples under Rule 5, both transient and short-term oral use."),
    "Clear orthodontic aligner": PresetRef(REASONED, "IIa", "4.2 Rule 5, p. 34",
        "Aligners are not named. Closest named examples are orthodontic wires and fixed prostheses (IIa: long-term, "
        "oral cavity, not absorbed). Replacement by the next aligner counts as continuous use (Annex VIII 3.6(b)), "
        "so long-term is the likely reading."),
    "Composite filling material": PresetRef(NAMED, "IIa", "4.2 Rule 8, p. 39",
        "Dental filling materials and pins are IIa examples under Rule 8 (placed in the teeth)."),
    "Dental implant (placed in jawbone)": PresetRef(NAMED, "IIb", "4.2 Rule 8, p. 39; Note 4, p. 41",
        "Dental implants and abutments are named IIb. Note 4: implants securing teeth or prostheses to the jaw "
        "bones stay IIb unless bioactive-coated."),
    "Resorbable bone graft": PresetRef(NAMED, "III", "4.2 Rule 8, p. 39; Rule 18, p. 53",
        "Wholly or mainly absorbed implants are III under Rule 8; bone graft substitutes are also named under "
        "Rule 18 (III)."),
    "Resorbable porcine collagen membrane": PresetRef(NAMED, "III", "4.2 Rule 18, p. 53",
        "Devices made from animal-sourced collagen are named III examples under Rule 18."),
    "Hand excavator / curette (reusable)": PresetRef(NAMED, "I", "4.2 Rule 6, p. 36",
        "Excavators, forceps, retractors and dental osteotomes are named reusable surgical instruments (Ir)."),
    "Handpiece-driven dental bur (reusable)": PresetRef(NAMED, "IIa", "4.2 Rule 6 Note 1, p. 37; Rule 9, p. 42",
        "Note 1: instruments connected to an active device are not 'reusable surgical instruments', so the Rule 6 "
        "default IIa applies. Dental handpieces are a named Rule 9 IIa example."),
    "Dental X-ray generator": PresetRef(NAMED, "IIb", "4.2 Rule 10, p. 45",
        "Diagnostic X-ray machines are named IIb (ionising radiation for diagnostic radiology)."),
    "Intraoral X-ray sensor": PresetRef(NAMED, "IIa", "4.2 Rule 17, p. 53",
        "Digital X-ray detectors for recording images are named IIa; Rule 10 note 6 routes recording to Rule 17."),
    "Intraoral camera (light for visibility only)": PresetRef(REASONED, "I", "4.2 Rule 13, p. 49; Rule 10 Note 1, p. 45",
        "Cameras are not named. With no Rule 9-12 trigger the device falls to Rule 13 (class I; dental curing lights "
        "are named there). Rule 10 note 1: 'illuminate' means light used in the diagnosis itself, not light that "
        "merely improves visibility."),
    "Laser caries detector": PresetRef(REASONED, "IIa", "4.2 Rule 10, p. 44",
        "Not named. Closest named example is the pulp tester (energy absorbed by the body, IIa). Confirm the device "
        "really delivers energy the tissue absorbs."),
    "Diode dental laser": PresetRef(NAMED, "IIb", "4.2 Rule 9, p. 43",
        "Surgical lasers are named IIb (coherent light). Assumes surgical use, not low-level therapy."),
    "Computer-controlled anaesthetic delivery unit": PresetRef(JUDGEMENT, "IIa", "4.2 Rule 12, p. 48",
        "Default IIa, but infusion pumps are named IIb. Whether local-anaesthetic delivery is potentially hazardous "
        "(substance, body part, mode of application) needs a documented argument; IIb is defensible."),
    "Benchtop steam steriliser": PresetRef(NAMED, "IIa", "4.2 Rule 16, p. 52",
        "Sterilisers for medical devices are a named IIa example."),
    "Ultrasonic instrument cleaner (physical action)": PresetRef(NAMED, "I", "4.2 Rule 16, p. 52",
        "Ultrasonic devices cleaning by physical action only are excluded from Rule 16. They are devices only if "
        "specifically intended for cleaning medical devices; then Rule 13 gives class I."),
    "Caries-detection AI software": PresetRef(JUDGEMENT, "IIa", "4.2 Rule 11, pp. 46-47",
        "IIa if it only informs decisions. The class rises with decision impact (stroke image analysis is named "
        "III). The intended-purpose wording decides."),
    "PRF blood collection tube": PresetRef(REASONED, "IIa", "4.2 Rule 2, pp. 29-30",
        "Not named. Rule 2 gives IIa for devices channelling or storing blood for later administration."),
    "PRF centrifuge": PresetRef(REASONED, "IIa", "4.2 Rule 3, p. 31",
        "Closest named example: centrifugation of blood for (auto)transfusion, IIa. Centrifuges used to manufacture "
        "a medicinal product are excluded, so check PRF is not treated that way."),
    "Saliva substitute (substance-based)": PresetRef(REASONED, "IIa", "Annex VIII 7.8 (Rule 21)",
        "Rule 21 gives IIa for substances applied in the oral cavity and acting there. The Rule 21 example table "
        "was not retrieved, so no named example is confirmed."),
    "Gauze compression pad on oral wound": PresetRef(NAMED, "I", "4.2 Rule 4, pp. 32-33",
        "Gauze dressings acting as a barrier or absorbing exudate, including on mucous membrane, are class I."),
    "Dental handpiece (powered)": PresetRef(NAMED, "IIa", "4.2 Rule 9, p. 42",
        "Dental handpieces are named IIa examples (mechanical energy)."),
    "Electric pulp tester": PresetRef(NAMED, "IIa", "4.2 Rule 10, p. 44",
        "Pulp testers are named IIa examples (energy absorbed by the body)."),
    "Dental aspirator tip": PresetRef(NAMED, "IIa", "4.2 Rule 5, p. 35",
        "Dental aspirator tips are named IIa examples (orifice-invasive, connected to an active device)."),
    "Dental curing light": PresetRef(NAMED, "I", "4.2 Rule 13, p. 49",
        "Dental curing lights are named class I examples of other active devices."),
    "Washer-disinfector for dental instruments": PresetRef(NAMED, "IIb", "4.2 Rule 16, p. 52",
        "Washer-disinfectors for invasive devices as the end point of processing (dental equipment given as an "
        "example) are IIb."),
    "Fissure sealant": PresetRef(NAMED, "IIa", "4.2 Rule 5, p. 34",
        "Fissure sealants are named IIa examples (long-term, oral cavity, not absorbed)."),
    "Temporary filling material": PresetRef(NAMED, "IIa", "4.2 Rule 7, p. 37",
        "Temporary filling materials are named IIa examples of short-term surgically invasive devices."),
    "Endodontic material with antibiotic": PresetRef(NAMED, "III", "4.2 Rule 14, p. 50",
        "Endodontic materials with antibiotics are named class III examples under Rule 14."),
    "Nano-filled composite (embedded nanomaterial)": PresetRef(NAMED, "IIa", "4.2 Rule 19, p. 55; Note 3",
        "Dental filling materials are a named IIa example (negligible exposure). Note 3 says to assess release "
        "during curing, grinding and polishing."),
}
