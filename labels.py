"""UI wording for every Facts field."""
LABELS = {
    "invasiveness": ("How does it interact with the body?", {
        "non_invasive": "Non-invasive (no penetration)", "body_orifice": "Invasive via body orifice (non-surgical)",
        "surgical": "Surgically invasive", "implantable": "Implantable"}),
    "duration": ("Continuous duration of use", {
        "transient": "Transient (< 60 min)", "short_term": "Short-term (60 min to 30 days)",
        "long_term": "Long-term (> 30 days)"}),
    "site": ("Where is it used or placed?", {
        "other": "Other site (e.g. jawbone, soft tissue)", "oral_ear_nasal": "Oral cavity to pharynx / ear canal / nasal",
        "teeth": "In the teeth", "heart_ccs_cns": "Heart, central circulation or CNS"}),
    "software": ("Software role", {
        "none": "Not software", "other": "Other software (no clinical decision input)",
        "informs": "Informs diagnostic/therapeutic decisions", "serious": "Could cause serious deterioration / surgery",
        "irreversible": "Could cause death / irreversible harm", "monitors": "Monitors physiological processes",
        "monitors_vital": "Monitors vital parameters (immediate danger)"}),
    "injured_contact": ("Contact with injured skin or mucosa (incl. scars)", {
        "none": "No", "barrier": "Barrier / compression / exudate absorption",
        "secondary_intent": "Wounds healing by secondary intent", "microenvironment": "Manages micro-environment",
        "other": "Other contact"}),
    "special_implant": ("Special implant type (Rule 8)", {
        "none": "None of these", "active_implantable": "Active implantable / accessory",
        "breast_or_mesh": "Breast implant or surgical mesh", "joint_replacement": "Joint replacement",
        "spinal": "Spinal disc / spinal column implant"}),
    "diag_mode": ("Active diagnostic function (Rule 10)", {
        "generic": "None of the specific cases", "energy_absorbed": "Supplies energy absorbed by the body",
        "visible_illumination": "Visible light used in the diagnosis itself", "radiopharm_imaging": "Images radiopharmaceuticals",
        "vital_monitoring": "Direct diagnosis/monitoring of vital processes",
        "vital_immediate_danger": "Vital parameters, immediate danger"}),
    "tissue_origin": ("Non-viable tissue/cell origin (Rule 18)", {
        "none": "None", "human": "Human", "animal": "Animal"}),
    "nano_exposure": ("Nanomaterial internal exposure (Rule 19)", {
        "none": "No nanomaterial", "negligible": "Negligible", "low": "Low", "medium_high": "Medium or high"}),
    "purpose_site": ("Where the substance achieves its purpose (Rule 21)", {
        "skin_oral_nasal": "Skin / oral or nasal cavity", "stomach_gi": "Stomach / lower GI tract", "other": "Elsewhere"}),
}
BOOLS = {
    "Active devices & energy": {
        "active_device": "Active device (needs external energy source)",
        "active_therapeutic": "Active therapeutic (delivers/exchanges energy)",
        "hazardous_energy": "...potentially hazardous energy", "ionising": "Emits ionising radiation",
        "controls_iib_therapeutic": "Controls/influences a class IIb therapeutic device",
        "controls_active_implantable": "Controls/influences an active implantable",
        "closed_loop": "Integrated diagnostic function drives therapy (closed loop)",
        "active_diagnostic": "Active diagnostic / monitoring device", "records_xray": "Records X-ray images",
        "active_delivers_substances": "Administers/removes medicinal products, liquids or substances",
        "hazardous_delivery": "...in a potentially hazardous manner"},
    "Invasive devices": {
        "absorbed_or_bio": "Biological effect, or wholly/mainly absorbed",
        "chemical_change": "Undergoes ongoing chemical change in the body (not just setting on placement)",
        "administers_medicinal": "Administers medicinal products",
        "incorporates_medicinal": "Incorporates a medicinal substance (Rule 14)",
        "reusable_instrument": "Reusable surgical instrument",
        "connected_to_active_device": "Connected to an active device",
        "connected_active_iia_plus": "May connect to a class IIa+ active device",
        "inhalation_delivery": "Delivers medicinal product by inhalation (Rule 20)",
        "inhalation_critical": "...critical mode of action or life-threatening condition"},
    "Non-invasive body material": {
        "channels_or_stores": "Channels or stores liquids/gases/tissues for administration (Rule 2)",
        "stores_body_material": "...blood, body liquids, organs, cells or tissues",
        "blood_bag": "...it is a blood bag",
        "modifies_composition": "Modifies composition of blood/cells/tissues (Rule 3)",
        "simple_treatment": "...by filtration, centrifugation or gas/heat exchange only",
        "in_vitro_contact": "Substance used in vitro on human cells/tissues/embryos"},
    "Special rules & markers": {
        "contraception_std": "Contraception / STI prevention (Rule 15)",
        "disinfects_devices": "Disinfects / sterilises medical devices (Rule 16)",
        "disinfects_invasive_endpoint": "...solution/washer-disinfector, invasive devices end point",
        "disinfects_contact_lenses": "Contact lens care",
        "cleans_physical_only": "Cleans by physical action only",
        "intact_skin_only": "Contacts intact skin only", "substance_based": "Substance-based device (Rule 21)",
        "systemically_absorbed": "...systemically absorbed to achieve its purpose",
        "sterile": "Supplied sterile", "measuring": "Has a measuring function"},
}
