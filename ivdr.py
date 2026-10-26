"""Rule engine for EU IVDR (Regulation 2017/746) Annex VIII classification, Rules 1-7 plus implementing rules.

Built against the as-adopted Annex VIII text. MDCG 2020-16 (Rev.5, September 2026, which only clarifies Rule 7) was
not retrievable in full, so examples are labelled by what supports them. Teaching tool: verify against the Regulation.
Not modelled: implementing rules 1.2-1.4 (combinations, accessories, driving software); classify each item separately.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace

IVD_EURLEX = "https://eur-lex.europa.eu/eli/reg/2017/746/oj"
IVD_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
IVD_RULED, IVD_REPORTED, IVD_REASONED = "Named in Annex VIII", "Reported in MDCG 2020-16 (secondary)", "Reasoned"
IVD_STATUS_HELP = {
    IVD_RULED: "The Annex VIII wording itself names or directly dictates this case.",
    IVD_REPORTED: "Secondary reports of MDCG 2020-16 give this example; the guidance text itself was not retrieved.",
    IVD_REASONED: "Follows from the rule text, but no named example was found. Document your argument.",
}
RULE3 = {
    "a": "Detects a sexually transmitted agent",
    "b": "Detects an infectious agent in CSF or blood without high propagation risk",
    "c": "Detects an infectious agent where an erroneous result risks death or severe disability",
    "d": "Prenatal screening of immune status towards transmissible agents",
    "e": "Infective or immune status where an error could lead to a life-threatening management decision",
    "f": "Companion diagnostic",
    "g": "Disease staging where an error could lead to a life-threatening management decision",
    "h": "Screening, diagnosis or staging of cancer",
    "i": "Human genetic testing",
    "j": "Monitoring levels of medicinal products or substances where an error could be life-threatening",
    "k": "Management of patients with a life-threatening disease or condition",
    "l": "Screening for congenital disorders in the embryo or foetus",
    "m": "Newborn screening where missed disorders could be life-threatening or severely disabling",
}
IVD_BOOLS = {
    "Rule 1: high public-health risk": {
        "donor_screening": "Detects a transmissible agent in blood, cells, tissues or organs to judge suitability "
                           "for transfusion, transplantation or cell administration",
        "high_risk_agent": "Detects an agent causing a life-threatening disease with high propagation risk",
        "infectious_load_critical": "Determines infectious load of a life-threatening disease where monitoring is "
                                    "critical"},
    "Rule 2: blood grouping and tissue typing": {
        "blood_grouping_or_typing": "Blood grouping or tissue typing for transfusion/transplant compatibility",
        "major_blood_group_marker": "...for ABO, Rhesus, Kell, Kidd or Duffy markers"},
    "Rule 4: self-testing and near-patient": {
        "self_testing": "Intended for self-testing by a layperson",
        "self_test_exempt": "...pregnancy, fertility, cholesterol, or urine glucose/erythrocytes/leucocytes/bacteria",
        "near_patient": "Intended for near-patient testing (classified in its own right)"},
    "Rule 5: laboratory products": {
        "general_lab_product": "General laboratory product, buffer, washing solution, general culture medium or "
                               "histological stain",
        "ivd_instrument": "Instrument specifically intended for IVD procedures",
        "specimen_receptacle": "Specimen receptacle"},
    "Controls and calibrators": {
        "control_without_value": "Control without a quantitative or qualitative assigned value (Rule 7)",
        "calibrator_or_assigned_control": "Calibrator, or control with assigned values (takes the device's class)"},
}


@dataclass(frozen=True)
class IvdFacts:
    rule3: tuple = ()
    donor_screening: bool = False
    high_risk_agent: bool = False
    infectious_load_critical: bool = False
    blood_grouping_or_typing: bool = False
    major_blood_group_marker: bool = False
    self_testing: bool = False
    self_test_exempt: bool = False
    near_patient: bool = False
    general_lab_product: bool = False
    ivd_instrument: bool = False
    specimen_receptacle: bool = False
    control_without_value: bool = False
    calibrator_or_assigned_control: bool = False
    parent_class: str = "B"


@dataclass(frozen=True)
class IvdHit:
    rule: str
    cls: str
    why: str
    ref: str


@dataclass(frozen=True)
class IvdResult:
    cls: str
    hits: tuple


SECTION = {"1": "2.1", "2": "2.2", "3": "2.3", "4": "2.4", "5": "2.5", "6": "2.6", "7": "2.7", "IR": "1.5, 1.6"}


def _h(rule, cls, why, part=""):
    return IvdHit(rule, cls, why, f"Annex VIII, {SECTION[rule]}" + (f" ({part})" if part else ""))


def rule_1(f):
    out = []
    if f.donor_screening:
        out.append(_h("1", "D", "Detects a transmissible agent to assess suitability for transfusion, transplantation "
                                "or cell administration.", "1st indent"))
    if f.high_risk_agent:
        out.append(_h("1", "D", "Agent causing life-threatening disease with high or suspected high propagation "
                                "risk.", "2nd indent"))
    if f.infectious_load_critical:
        out.append(_h("1", "D", "Infectious load of a life-threatening disease where monitoring is critical.",
                      "3rd indent"))
    return out


def rule_2(f):
    if not f.blood_grouping_or_typing:
        return []
    if f.major_blood_group_marker:
        return [_h("2", "D", "Blood grouping for the ABO, Rhesus, Kell, Kidd or Duffy systems.", "exception")]
    return [_h("2", "C", "Blood grouping or tissue typing for transfusion/transplant compatibility.")]


def rule_3(f):
    return [_h("3", "C", RULE3[k], k) for k in f.rule3]


def rule_4(f):
    if not f.self_testing:
        return []
    if f.self_test_exempt:
        return [_h("4", "B", "Self-test in the exception list (pregnancy, fertility, cholesterol, urine glucose, "
                             "erythrocytes, leucocytes or bacteria).", "a")]
    return [_h("4", "C", "Device intended for self-testing.", "a")]


def rule_5(f):
    items = [(f.general_lab_product, "General laboratory product, accessory without critical characteristics, "
                                    "buffer, washing solution, general culture medium or histological stain.", "a"),
             (f.ivd_instrument, "Instrument specifically intended for in vitro diagnostic procedures.", "b"),
             (f.specimen_receptacle, "Specimen receptacle.", "c")]
    return [_h("5", "A", why, p) for cond, why, p in items if cond]


def rule_7(f):
    return [_h("7", "B", "Control without a quantitative or qualitative assigned value.")] if f.control_without_value \
        else []


def impl_calibrator(f):
    if f.calibrator_or_assigned_control:
        return [IvdHit("IR", f.parent_class, f"Calibrator or assigned-value control takes the class of its device "
                       f"(class {f.parent_class}).", "Annex VIII, 1.5 and 1.6")]
    return []


def classify_ivd(f: IvdFacts) -> IvdResult:
    hits = [h for r in (rule_1, rule_2, rule_3, rule_4, rule_5, rule_7, impl_calibrator) for h in r(f)]
    if not hits:
        hits = [_h("6", "B", "Not covered by Rules 1-5 or 7: residual class B.")]
    return IvdResult(max((h.cls for h in hits), key=IVD_ORDER.__getitem__), tuple(hits))


IVD_RULE_INFO = {
    "1": ("High public-health risk", "Class D: transmissible agents in donated blood, cells, tissues or organs; agents "
          "causing life-threatening disease with high propagation risk; infectious load where monitoring is critical."),
    "2": ("Blood grouping and tissue typing", "Class C, rising to D for the ABO, Rhesus, Kell, Kidd and Duffy markers."),
    "3": ("Class C purposes", "Thirteen listed purposes, including sexually transmitted agents, companion "
          "diagnostics, cancer, genetic testing, prenatal and newborn screening and life-threatening management "
          "decisions."),
    "4": ("Self-testing and near-patient", "Self-tests are class C, except pregnancy, fertility, cholesterol and urine "
          "glucose, erythrocyte, leucocyte and bacteria tests (class B). Near-patient devices are classified in "
          "their own right."),
    "5": ("Class A laboratory products", "General laboratory products, accessories without critical characteristics, "
          "buffers, washing solutions, general culture media, histological stains; IVD instruments; specimen "
          "receptacles."),
    "6": ("Residual rule", "Devices not covered by Rules 1-5 and 7 are class B."),
    "7": ("Controls without assigned values", "Class B. MDCG 2020-16 Rev.5 (9 Sept 2026) clarifies that indicative "
          "ranges on standalone QC materials are not assigned values."),
    "IR": ("Calibrators and assigned-value controls", "They take the class of the device they are used with."),
}
IVD_ROUTES = {
    "A": "Manufacturer self-declaration (Annex II/III documentation and declaration of conformity). A notified body "
         "is involved only for sterile devices, limited to sterility aspects.",
    "B": "Notified body required: quality management system assessment plus technical documentation assessed on a "
         "sampling basis per category of devices, or product conformity verification routes.",
    "C": "Notified body required: quality management system assessment plus technical documentation assessment of at "
         "least one representative device per generic device group. Companion diagnostics also involve a medicines "
         "authority consultation.",
    "D": "Notified body required: quality management system assessment plus technical documentation assessment of "
         "every device, with EU reference laboratory verification against common specifications where applicable "
         "and possible expert panel scrutiny.",
}


def ivd_what_if(f: IvdFacts):
    base, out = classify_ivd(f).cls, []
    for x in fields(IvdFacts):
        if x.name == "rule3":
            for k in RULE3:
                cls = classify_ivd(replace(f, rule3=tuple(sorted(set(f.rule3) ^ {k})))).cls
                if cls != base:
                    out.append((f"Rule 3({k})", "toggled", cls))
        elif x.name == "parent_class":
            out += [(x.name, c, n) for c in IVD_ORDER if c != f.parent_class
                    if (n := classify_ivd(replace(f, parent_class=c)).cls) != base]
        else:
            cls = classify_ivd(replace(f, **{x.name: not getattr(f, x.name)})).cls
            if cls != base:
                out.append((x.name, str(not getattr(f, x.name)), cls))
    return base, out


def ivd_describe(f: IvdFacts) -> list:
    out = [f"Rule 3({k}): {RULE3[k]}" for k in f.rule3]
    out += [text for items in IVD_BOOLS.values() for k, text in items.items() if getattr(f, k)]
    return out + ([f"Parent device class: {f.parent_class}"] if f.calibrator_or_assigned_control else [])


def ivd_rationale_md(name: str, f: IvdFacts, res: IvdResult, purpose: str = "") -> str:
    ref = IVD_REFS.get(name) if IVD_PRESETS.get(name) == f else None
    L = [f"# IVDR classification rationale (draft): {name}", "", f"**Proposed class: {res.cls}**", "",
         "## 1. Intended purpose", "",
         purpose.strip() or "[Complete before use: state the intended purpose exactly as in the instructions for use. "
                            "Class follows the intended purpose (Annex VIII 1.1).]", "",
         "## 2. Characteristics relevant to classification", ""]
    L += [f"- {d}" for d in ivd_describe(f)] or ["- None of the characteristics below apply."]
    L += ["", "## 3. Application of Annex VIII", "", "All seven rules and the implementing rules were considered. "
          "Triggered:", "", "| Rule | Class | Where | Reason |", "|---|---|---|---|"]
    L += [f"| {h.rule} ({IVD_RULE_INFO[h.rule][0]}) | {h.cls} | {h.ref} | {h.why} |" for h in res.hits]
    L += ["", f"Where several rules apply the higher class governs (Annex VIII, 1.9). The device is class {res.cls}.",
          "", "## 4. Supporting guidance", ""]
    L.append(f"{ref.status}: {ref.location}. {ref.note}" if ref else
             "No cross-reference applies to these inputs. Compare the device with the examples in MDCG 2020-16 Rev.5.")
    L += ["", "## 5. Open points to document", "",
          "- Confirm the intended purpose wording supports exactly this class; vague wording can push a device up.",
          "- Classify accessories, software and combinations separately (Annex VIII 1.2-1.4); not modelled here."]
    if f.near_patient:
        L.append("- Near-patient testing is classified in its own right: state the intended user and setting.")
    if f.control_without_value:
        L.append("- Rev.5 of MDCG 2020-16 distinguishes indicative ranges from assigned values; check your IFU "
                 "wording.")
    L += ["", f"Regulation text: {IVD_EURLEX}", "",
          "_Draft for regulatory review. Teaching tool, not a legal opinion; verify against Regulation (EU) 2017/746._"]
    return "\n".join(L)


@dataclass(frozen=True)
class IvdRef:
    status: str
    guidance_class: str
    location: str
    note: str


_R, _G, _X = IVD_RULED, IVD_REPORTED, IVD_REASONED
IVD_EXAMPLES = [
    ("Blood & transplantation", "ABO / Rhesus blood grouping reagent",
     dict(blood_grouping_or_typing=True, major_blood_group_marker=True), _R, "D", "Annex VIII 2.2 (Rule 2)",
     "Rule 2 names ABO, Rhesus, Kell, Kidd and Duffy markers as class D."),
    ("Blood & transplantation", "HLA tissue typing for transplant matching", dict(blood_grouping_or_typing=True), _R,
     "C", "Annex VIII 2.2 (Rule 2)", "Tissue typing is class C; only the listed blood-group markers rise to D."),
    ("Blood & transplantation", "Donor blood screening assay", dict(donor_screening=True), _R, "D",
     "Annex VIII 2.1 (Rule 1, 1st indent)", "Detecting transmissible agents to assess donor suitability is class D."),
    ("Infectious disease", "HIV diagnostic assay", dict(high_risk_agent=True), _G, "D",
     "Annex VIII 2.1 (Rule 1, 2nd indent)", "HIV, hepatitis B and hepatitis C are reported as MDCG Rule 1 examples."),
    ("Infectious disease", "Hepatitis B diagnostic assay", dict(high_risk_agent=True), _G, "D",
     "Annex VIII 2.1 (Rule 1, 2nd indent)", "Reported as a Rule 1 example in MDCG 2020-16."),
    ("Infectious disease", "HIV viral load assay", dict(infectious_load_critical=True), _G, "D",
     "Annex VIII 2.1 (Rule 1, 3rd indent)", "Viral load tests where monitoring is critical are reported as examples."),
    ("Infectious disease", "Chlamydia / gonorrhoea NAAT", dict(rule3=("a",)), _R, "C", "Annex VIII 2.3 (Rule 3(a))",
     "Sexually transmitted agents are class C."),
    ("Infectious disease", "Meningitis pathogen test (CSF or blood)", dict(rule3=("b",)), _R, "C",
     "Annex VIII 2.3 (Rule 3(b))", "Infectious agents in CSF or blood without high propagation risk are class C."),
    ("Infectious disease", "Rubella immune status in pregnancy", dict(rule3=("d",)), _R, "C",
     "Annex VIII 2.3 (Rule 3(d))", "Prenatal immune-status screening is class C."),
    ("Self-testing", "Pregnancy self-test", dict(self_testing=True, self_test_exempt=True), _R, "B",
     "Annex VIII 2.4 (Rule 4(a))", "Pregnancy self-tests are in the class B exception list."),
    ("Self-testing", "Ovulation / fertility self-test", dict(self_testing=True, self_test_exempt=True), _R, "B",
     "Annex VIII 2.4 (Rule 4(a))", "Fertility self-tests are in the class B exception list."),
    ("Self-testing", "Cholesterol self-test", dict(self_testing=True, self_test_exempt=True), _R, "B",
     "Annex VIII 2.4 (Rule 4(a))", "Cholesterol self-tests are in the class B exception list."),
    ("Self-testing", "Urine glucose self-test strip", dict(self_testing=True, self_test_exempt=True), _R, "B",
     "Annex VIII 2.4 (Rule 4(a))", "Glucose in urine is in the exception list."),
    ("Self-testing", "Blood glucose self-test meter", dict(self_testing=True), _X, "C", "Annex VIII 2.4 (Rule 4(a))",
     "Only urine glucose is in the exception list, so blood glucose self-tests default to class C."),
    ("Self-testing", "HIV self-test", dict(high_risk_agent=True, self_testing=True), _G, "D",
     "Annex VIII 2.1 and 2.4", "A self-test for HIV stays class D because Rule 1 governs (reported)."),
    ("Self-testing", "SARS-CoV-2 antigen self-test", dict(self_testing=True), _G, "C",
     "Annex VIII 2.4 (Rule 4(a)); MDCG 2020-16 Rev.4",
     "A consultancy report says Rev.4 (March 2025) lists SARS-CoV-2 self-tests under Rule 4(a) and no longer treats "
     "SARS-CoV-2 detection as class D. Older material still calls it class D."),
    ("Oncology, genetics & drugs", "Companion diagnostic (HER2-type tissue test)", dict(rule3=("f",)), _R, "C",
     "Annex VIII 2.3 (Rule 3(f))", "Companion diagnostics are class C."),
    ("Oncology, genetics & drugs", "Cancer diagnosis tumour-marker assay", dict(rule3=("h",)), _R, "C",
     "Annex VIII 2.3 (Rule 3(h))", "Screening, diagnosis or staging of cancer is class C."),
    ("Oncology, genetics & drugs", "Germline genetic test (BRCA-type)", dict(rule3=("i",)), _R, "C",
     "Annex VIII 2.3 (Rule 3(i))", "Human genetic testing is class C."),
    ("Oncology, genetics & drugs", "Immunosuppressant drug-level monitoring", dict(rule3=("j",)), _R, "C",
     "Annex VIII 2.3 (Rule 3(j))", "Monitoring drug levels where an error could be life-threatening is class C."),
    ("Oncology, genetics & drugs", "Test managing a life-threatening condition", dict(rule3=("k",)), _R, "C",
     "Annex VIII 2.3 (Rule 3(k))", "Management of life-threatening disease is class C."),
    ("Pregnancy & newborn", "Non-invasive prenatal screening", dict(rule3=("l",)), _R, "C",
     "Annex VIII 2.3 (Rule 3(l))", "Screening for congenital disorders in the embryo or foetus is class C."),
    ("Pregnancy & newborn", "Newborn metabolic screening (PKU-type)", dict(rule3=("m",)), _R, "C",
     "Annex VIII 2.3 (Rule 3(m))", "Newborn screening where missed disorders are life-threatening is class C."),
    ("Laboratory products & controls", "ELISA analyser (instrument)", dict(ivd_instrument=True), _R, "A",
     "Annex VIII 2.5 (Rule 5(b))", "IVD instruments are class A; the reagents run on them are classified separately."),
    ("Laboratory products & controls", "Specimen collection tube", dict(specimen_receptacle=True), _R, "A",
     "Annex VIII 2.5 (Rule 5(c))", "Specimen receptacles are class A."),
    ("Laboratory products & controls", "General wash buffer", dict(general_lab_product=True), _R, "A",
     "Annex VIII 2.5 (Rule 5(a))", "Buffers and washing solutions are class A."),
    ("Laboratory products & controls", "Histological stain", dict(general_lab_product=True), _R, "A",
     "Annex VIII 2.5 (Rule 5(a))", "Histological stains are class A."),
    ("Laboratory products & controls", "Routine clinical chemistry reagent", dict(), _X, "B",
     "Annex VIII 2.6 (Rule 6)", "No specific rule applies, so the residual class B applies. Check that no Rule 3 "
                                "purpose fits the intended purpose."),
    ("Laboratory products & controls", "Control material without assigned values", dict(control_without_value=True),
     _R, "B", "Annex VIII 2.7 (Rule 7)", "Rev.5 clarifies that indicative ranges are not assigned values."),
    ("Laboratory products & controls", "Calibrator for a class C assay",
     dict(calibrator_or_assigned_control=True, parent_class="C"), _R, "C", "Annex VIII 1.5",
     "Calibrators take the class of the device they are used with."),
    ("Laboratory products & controls", "Quantitative control for a class D assay",
     dict(calibrator_or_assigned_control=True, parent_class="D"), _R, "D", "Annex VIII 1.6",
     "Controls with assigned values take the class of the device."),
]
IVD_PRESETS = {n: IvdFacts(**kw) for _, n, kw, *_ in IVD_EXAMPLES}
IVD_REFS = {n: IvdRef(st, c, loc, note) for _, n, _, st, c, loc, note in IVD_EXAMPLES}
IVD_CATEGORY = {n: cat for cat, n, *_ in IVD_EXAMPLES}
IVD_CATEGORY_ORDER = list(dict.fromkeys(cat for cat, *_ in IVD_EXAMPLES))
