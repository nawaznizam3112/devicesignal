"""Rule engine for a teaching subset of EU MDR (2017/745) Annex VIII classification.

Educational tool: always verify against the Regulation text and MDCG 2021-24.
Implements Rules 1, 5-11, 14, 16, 17 and the "highest class wins" principle (Annex VIII, 3.5).
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace

ORDER = {"I": 0, "IIa": 1, "IIb": 2, "III": 3}
INVASIVENESS = ["non_invasive", "body_orifice", "surgical", "implantable"]
DURATION = ["transient", "short_term", "long_term"]
SITE = ["other", "oral_ear_nasal", "teeth", "heart_ccs_cns"]
SOFTWARE = ["none", "informs", "serious", "irreversible"]


@dataclass(frozen=True)
class Facts:
    invasiveness: str = "non_invasive"
    duration: str = "transient"
    site: str = "other"
    software: str = "none"
    absorbed_or_bio: bool = False
    chemical_change: bool = False
    administers_medicinal: bool = False
    incorporates_medicinal: bool = False
    reusable_instrument: bool = False
    active_therapeutic: bool = False
    hazardous_energy: bool = False
    active_diagnostic: bool = False
    ionising: bool = False
    records_xray: bool = False
    connected_active_iia_plus: bool = False
    disinfects_devices: bool = False
    disinfects_invasive_endpoint: bool = False
    sterile: bool = False
    measuring: bool = False


@dataclass(frozen=True)
class Hit:
    rule: str
    cls: str
    why: str


def _build(rule, base, why, extras):
    cls = base
    for cond, c, text in extras:
        if cond and ORDER[c] > ORDER[cls]:
            cls, why = c, text
    return Hit(rule, cls, why)


def rule_1(f):
    if f.invasiveness == "non_invasive":
        return Hit("1", "I", "Non-invasive device: default class I unless a later rule applies.")


def rule_5(f):
    if f.invasiveness != "body_orifice":
        return None
    oral = f.site == "oral_ear_nasal"
    if f.connected_active_iia_plus:
        return Hit("5", "IIa", "Orifice-invasive device connected to a class IIa/IIb/III active device.")
    if f.duration == "transient":
        return Hit("5", "I", "Transient use via a body orifice.")
    if f.duration == "short_term":
        if oral:
            return Hit("5", "I", "Short-term use in oral cavity (to pharynx), ear canal or nasal cavity.")
        return Hit("5", "IIa", "Short-term use via another body orifice.")
    if oral and not f.absorbed_or_bio:
        return Hit("5", "IIa", "Long-term use in oral/ear/nasal cavity, not liable to be absorbed by mucous membrane.")
    return Hit("5", "IIb", "Long-term use via a body orifice.")


def rule_6(f):
    if f.invasiveness != "surgical" or f.duration != "transient":
        return None
    base, why = ("I", "Reusable surgical instrument (Ir).") if f.reusable_instrument else (
        "IIa", "Transient surgically invasive device: default IIa.")
    return _build("6", base, why, [
        (f.site == "heart_ccs_cns", "III", "Direct contact with heart, central circulatory system or CNS."),
        (f.ionising, "IIb", "Supplies energy as ionising radiation."),
        (f.absorbed_or_bio, "IIb", "Biological effect or wholly/mainly absorbed."),
        (f.administers_medicinal, "IIb", "Administers medicinal product in a potentially hazardous manner."),
    ])


def rule_7(f):
    if f.invasiveness != "surgical" or f.duration != "short_term":
        return None
    return _build("7", "IIa", "Short-term surgically invasive device: default IIa.", [
        (f.site == "heart_ccs_cns", "III", "Direct contact with heart, central circulatory system or CNS."),
        (f.ionising, "IIb", "Supplies energy as ionising radiation."),
        (f.absorbed_or_bio, "III", "Biological effect or wholly/mainly absorbed."),
        (f.chemical_change and f.site != "teeth", "IIb", "Undergoes chemical change in the body."),
        (f.administers_medicinal, "IIb", "Administers medicinal products."),
    ])


def rule_8(f):
    if not (f.invasiveness == "implantable" or (f.invasiveness == "surgical" and f.duration == "long_term")):
        return None
    if f.site == "teeth":
        base, why = "IIa", "Implantable/long-term surgically invasive, but placed in the teeth: IIa."
    else:
        base, why = "IIb", "Implantable or long-term surgically invasive device: default IIb."
    return _build("8", base, why, [
        (f.site == "heart_ccs_cns", "III", "Direct contact with heart, central circulatory system or CNS."),
        (f.absorbed_or_bio, "III", "Biological effect or wholly/mainly absorbed."),
        (f.chemical_change and f.site != "teeth", "III", "Undergoes chemical change in the body (not in teeth)."),
        (f.administers_medicinal, "III", "Administers medicinal products."),
    ])


def rule_9(f):
    if not f.active_therapeutic:
        return None
    if f.hazardous_energy or f.ionising:
        return Hit("9", "IIb", "Active therapeutic device with potentially hazardous energy / ionising radiation.")
    return Hit("9", "IIa", "Active therapeutic device administering or exchanging energy.")


def rule_10(f):
    if not f.active_diagnostic:
        return None
    if f.ionising:
        return Hit("10", "IIb", "Active device emitting ionising radiation for diagnostic radiology.")
    return Hit("10", "IIa", "Active diagnostic/monitoring device.")


def rule_11(f):
    table = {
        "informs": ("IIa", "Software providing information for diagnostic/therapeutic decisions."),
        "serious": ("IIb", "Decisions may cause serious deterioration or surgical intervention."),
        "irreversible": ("III", "Decisions may cause death or irreversible deterioration."),
    }
    if f.software in table:
        cls, why = table[f.software]
        return Hit("11", cls, why)


def rule_14(f):
    if f.incorporates_medicinal:
        return Hit("14", "III", "Incorporates a medicinal substance with ancillary action.")


def rule_16(f):
    if not f.disinfects_devices:
        return None
    if f.disinfects_invasive_endpoint:
        return Hit("16", "IIb", "Disinfecting solution/washer-disinfector for invasive devices as end point.")
    return Hit("16", "IIa", "Intended specifically for disinfecting or sterilising medical devices.")


def rule_17(f):
    if f.records_xray:
        return Hit("17", "IIa", "Intended for recording diagnostic images generated by X-ray radiation.")


RULES = [rule_1, rule_5, rule_6, rule_7, rule_8, rule_9, rule_10, rule_11, rule_14, rule_16, rule_17]


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
        label += ("s" if f.sterile else "") + ("m" if f.measuring else "") + ("r" if f.reusable_instrument else "")
    return Result(cls, label, hits)


CHOICES = {"invasiveness": INVASIVENESS, "duration": DURATION, "site": SITE, "software": SOFTWARE}
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

PRESETS = {
    "Alginate impression material": Facts(invasiveness="body_orifice", duration="short_term", site="oral_ear_nasal"),
    "Clear orthodontic aligner": Facts(invasiveness="body_orifice", duration="long_term", site="oral_ear_nasal"),
    "Composite filling material": Facts(invasiveness="surgical", duration="long_term", site="teeth"),
    "Dental implant (placed in jawbone)": Facts(invasiveness="implantable", duration="long_term"),
    "Resorbable bone graft": Facts(invasiveness="implantable", duration="long_term", absorbed_or_bio=True),
    "Reusable dental bur": Facts(invasiveness="surgical", duration="transient", reusable_instrument=True),
    "Dental X-ray generator": Facts(active_diagnostic=True, ionising=True),
    "Intraoral X-ray sensor": Facts(records_xray=True),
    "Diode dental laser": Facts(active_therapeutic=True, hazardous_energy=True),
    "Benchtop steam steriliser": Facts(disinfects_devices=True),
    "Caries-detection AI software": Facts(software="informs"),
    "Blank canvas": Facts(),
}


def report_md(name: str, f: Facts, res: Result) -> str:
    lines = [f"# MDR classification worksheet: {name}", "", f"**Result: Class {res.label}**", "",
             "## Rules triggered", "", "| Rule | Class | Rationale |", "|---|---|---|"]
    lines += [f"| {h.rule} | {h.cls} | {h.why} |" for h in res.hits]
    lines += ["", "## Inputs", ""] + [f"- {k}: {getattr(f, k)}" for k in OPTIONS]
    lines += ["", "## Indicative conformity route", "", ROUTES[res.cls], "",
              "_Teaching tool covering a subset of Annex VIII. Verify against Regulation (EU) 2017/745 and MDCG 2021-24._"]
    return "\n".join(lines)
