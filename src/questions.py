"""questionnaire and answer to fact mapping stuff.

a question may include an ``ask_if`` condition this keeps line specific checks
out of fibre consultations and device specific checks out of whole h ouse cases.
"""

QUESTIONS = [
    {
        "id": "Q01",
        "prompt": "Which type of broadband connection do you have?",
        "options": ["copper/ADSL", "part-fibre (FTTC/VDSL)", "full fibre (FTTP)", "not sure"],
        "display_options": ["Copper phone line", "Part-fibre (fibre to a street cabinet)", "Full-fibre (fibre to your home)", "Not sure"],
        "reason": "The type of connection decides which equipment checks apply.",
        "updates": {
            "copper/ADSL": {"access_type": "copper"},
            "part-fibre (FTTC/VDSL)": {"access_type": "part_fibre"},
            "full fibre (FTTP)": {"access_type": "full_fibre"},
            "not sure": {"access_type": "unknown"},
        },
    },
    {
        "id": "Q02",
        "prompt": "Are any lights on the router?",
        "options": ["yes", "no", "not sure"],
        "reason": "This establishes whether the router appears to have power.",
        "updates": {"yes": {"router_lights_on": True}, "no": {"router_lights_on": False}, "not sure": {"router_lights_on": None}},
    },
    {
        "id": "Q03",
        "prompt": "If the router has no lights, have you checked the power button, cable and mains socket?",
        "options": ["yes, all checked", "no", "not checked"],
        "reason": "A power-supply check avoids attributing an external power problem to the router.",
        "ask_if": {"router_lights_on": False},
        "updates": {"yes, all checked": {"external_power_checked": True}, "no": {"external_power_checked": False}, "not checked": {"external_power_checked": None}},
    },
    {
        "id": "Q04",
        "prompt": "According to your router's own guide, what do its broadband/DSL and Internet indicators show?",
        "options": ["broadband abnormal", "TP-Link Internet light off but broadband normal", "both normal", "both abnormal", "not sure"],
        "reason": "Indicator meanings vary by router model, so use the manufacturer's guide. The TP-Link Internet-light-off option is model-specific and is not a universal fault indicator.",
        "updates": {
            "broadband abnormal": {"broadband_light": "abnormal", "internet_light": None},
            "TP-Link Internet light off but broadband normal": {"broadband_light": "normal", "internet_light": "off"},
            "both normal": {"broadband_light": "normal", "internet_light": "normal"},
            "both abnormal": {"broadband_light": "abnormal", "internet_light": "abnormal"},
            "not sure": {"broadband_light": None, "internet_light": None},
        },
    },
    {
        "id": "Q05",
        "prompt": "If you have a separate modem or fibre box, what do its lights show?",
        "options": [
            "ONT: PON solid green and LOS off (normal)",
            "Nokia ONT: Power and PON steady green; Port indicator off",
            "ONT: PON off",
            "ONT: LOS red",
            "ONT: PON red (unclassified)",
            "ONT: PON and LOS both flashing",
            "ONT: PON flashing, LOS off (verification)",
            "Separate modem: normal",
            "Separate modem: abnormal",
            "no separate box",
            "not sure",
        ],
        "display_options": [
            "Fibre box: connection light steady green, warning light off (normal)",
            "Nokia fibre box: Power and PON steady green; Port indicator off",
            "Fibre box: connection light off",
            "Fibre box: warning light red",
            "Fibre box: PON light red (unclassified)",
            "Fibre box: both lights flashing",
            "Fibre box: connection light flashing, warning light off (verification)",
            "Separate modem: lights normal",
            "Separate modem: lights abnormal",
            "No separate box",
            "Not sure",
        ],
        "reason": "Indicator layouts vary by fibre-box model. This question interprets the listed PON/LOS patterns and the Nokia Port-indicator-off condition. Some ECI models use an Optical indicator, which is not interpreted here, so select “not sure” for an unlisted layout and check the model guide. On the Nokia layout, the Port indicator being off can mean the cable to the Hub is unplugged or broken, so check both ends and try another cable.",
        "ask_if": {"access_type": ["copper", "part_fibre", "full_fibre"]},
        "require_known": ["access_type"],
        "updates": {
            "ONT: PON solid green and LOS off (normal)": {"separate_modem_status": "normal"},
            "Nokia ONT: Power and PON steady green; Port indicator off": {"separate_modem_status": None},
            "ONT: PON off": {"separate_modem_status": "abnormal"},
            "ONT: LOS red": {"separate_modem_status": "abnormal"},
            "ONT: PON red (unclassified)": {"separate_modem_status": None},
            "ONT: PON and LOS both flashing": {"separate_modem_status": "abnormal"},
            "ONT: PON flashing, LOS off (verification)": {"separate_modem_status": "verification"},
            "Separate modem: normal": {"separate_modem_status": "normal"},
            "Separate modem: abnormal": {"separate_modem_status": "abnormal"},
            "no separate box": {"separate_modem_status": "not_present"},
            "not sure": {"separate_modem_status": None},
        },
        "frame_updates": {
            "ONT: PON solid green and LOS off (normal)": {"ont": {"pon_indicator": "green_solid", "los_indicator": "off"}},
            "Nokia ONT: Power and PON steady green; Port indicator off": {"ont": {"power_state": "on", "pon_indicator": "green_solid", "lan_indicator": "off"}},
            "ONT: PON off": {"ont": {"pon_indicator": "off"}},
            "ONT: LOS red": {"ont": {"los_indicator": "red"}},
            "ONT: PON red (unclassified)": {"ont": {"pon_indicator": "red"}},
            "ONT: PON and LOS both flashing": {"ont": {"pon_indicator": "flashing", "los_indicator": "flashing"}},
            "ONT: PON flashing, LOS off (verification)": {"ont": {"pon_indicator": "flashing", "los_indicator": "off"}},
        },
    },
    {
        "id": "Q06",
        "prompt": "Are the incoming cable connections firmly seated at both ends?",
        "options": ["yes", "no, one may be loose", "not checked"],
        "reason": "A loose connection can interrupt service before a router or line fault is established.",
        "updates": {"yes": {"incoming_cable_secure": True}, "no, one may be loose": {"incoming_cable_secure": False}, "not checked": {"incoming_cable_secure": None}},
    },
    {
        "id": "Q07",
        "prompt": "How many devices are affected?",
        "options": ["all devices", "one device", "some devices", "not sure"],
        "reason": "Device scope distinguishes a shared connection problem from a device-specific problem.",
        "updates": {"all devices": {"device_scope": "all"}, "one device": {"device_scope": "one"}, "some devices": {"device_scope": "some"}, "not sure": {"device_scope": None}},
    },
    {
        "id": "Q08",
        "prompt": "What happens when you test with Ethernet and Wi-Fi?",
        "options": ["Ethernet works, Wi-Fi fails", "both fail", "Ethernet fails, Wi-Fi works", "Wi-Fi works, Ethernet not tested", "not tested"],
        "reason": "A working wired connection alongside failed Wi-Fi isolates the wireless part of the connection path.",
        "updates": {
            "Ethernet works, Wi-Fi fails": {"wired_connection": "works", "wifi_connection": "fails"},
            "both fail": {"wired_connection": "fails", "wifi_connection": "fails"},
            "Ethernet fails, Wi-Fi works": {"wired_connection": "fails", "wifi_connection": "works"},
            "Wi-Fi works, Ethernet not tested": {"wired_connection": None, "wifi_connection": "works"},
            "not tested": {"wired_connection": None, "wifi_connection": None},
        },
    },
    {
        "id": "Q09",
        "prompt": "When the connection drops, does your router show that the DSL/VDSL line itself has lost synchronisation and reconnected?",
        "options": ["yes", "no", "not sure"],
        "reason": "Answer yes only when the DSL/VDSL line itself loses synchronisation. A general loss of internet access or Wi-Fi alone does not establish DSL synchronisation loss.",
        "ask_if": {"access_type": ["copper", "part_fibre"]},
        "updates": {"yes": {"dsl_sync_drops": True}, "no": {"dsl_sync_drops": False}, "not sure": {"dsl_sync_drops": None}},
    },
    {
        "id": "Q10",
        "prompt": "Is the landline dial tone clear?",
        "options": ["clear", "no dial tone or noisy", "not applicable", "not sure"],
        "reason": "A noisy or absent phone tone can be relevant when broadband uses the copper phone line.",
        "ask_if": {"access_type": ["copper", "part_fibre"]},
        "updates": {"clear": {"dial_tone": "clear"}, "no dial tone or noisy": {"dial_tone": "poor"}, "not applicable": {"dial_tone": "not_applicable"}, "not sure": {"dial_tone": None}},
    },
    {
        "id": "Q11",
        "prompt": "Where your socket requires one, is a microfilter fitted?",
        "options": ["fitted", "missing", "not required", "not sure"],
        "reason": "Microfilters are required on some single-socket copper installations, but not every socket type uses them.",
        "ask_if": {"access_type": ["copper", "part_fibre"]},
        "updates": {"fitted": {"microfilter_status": "fitted"}, "missing": {"microfilter_status": "missing"}, "not required": {"microfilter_status": "not_required"}, "not sure": {"microfilter_status": None}},
    },
    {
        "id": "Q12",
        "prompt": "Does your provider's service-status page show an outage?",
        "options": ["yes", "no", "not checked"],
        "reason": "A provider status notice can confirm a known service outage.",
        "ask_if": {"device_scope": "all", "wired_connection": "fails"},
        "require_known": ["device_scope", "wired_connection"],
        "updates": {"yes": {"provider_status_outage": True}, "no": {"provider_status_outage": False}, "not checked": {"provider_status_outage": None}},
    },
    {
        "id": "Q13",
        "prompt": "Are other customers in your area reporting a similar problem?",
        "options": ["yes", "no", "not checked"],
        "reason": "Reports from neighbours can support a wider problem, but do not confirm the provider network.",
        "ask_if": {"device_scope": "all", "wired_connection": "fails"},
        "require_known": ["device_scope", "wired_connection"],
        "updates": {"yes": {"local_outage_reports": True}, "no": {"local_outage_reports": False}, "not checked": {"local_outage_reports": None}},
    },
    {
        "id": "Q14",
        "prompt": "Does your provider explicitly show the account or service as suspended or restricted?",
        "options": ["yes", "no, shown as active", "not checked"],
        "reason": "An overdue bill alone does not establish suspension; this asks for an explicit account-status indication.",
        "updates": {"yes": {"account_status": "suspended"}, "no, shown as active": {"account_status": "active"}, "not checked": {"account_status": None}},
    },
    {
        "id": "Q15",
        "prompt": "Does the same affected device also fail to connect to other Wi-Fi networks?",
        "options": ["yes", "no, it works elsewhere", "not tested"],
        "reason": "If the device also fails on other networks, the problem may be with the device itself.",
        "ask_if": {"device_scope": "one"},
        "updates": {"yes": {"device_fails_other_networks": True}, "no, it works elsewhere": {"device_fails_other_networks": False}, "not tested": {"device_fails_other_networks": None}},
    },
    {
        "id": "Q16",
        "prompt": "When the affected device tries to join your home Wi-Fi, what happens?",
        "options": ["password is rejected", "previously saved network does not reconnect automatically", "connects", "not sure"],
        "reason": "This separates a rejected password from a saved-network problem. Apple calls its setting Auto-Join, while other devices may use a different name for automatic connection.",
        "ask_if": {"device_scope": ["one", "some", None]},
        "updates": {"password is rejected": {"wifi_join_status": "password_rejected"}, "previously saved network does not reconnect automatically": {"wifi_join_status": "auto_rejoin_failed"}, "connects": {"wifi_join_status": "connects"}, "not sure": {"wifi_join_status": None}},
    },
    {
        "id": "Q17",
        "prompt": "Can another device join the same home Wi-Fi using the current password?",
        "options": ["yes", "no", "not tested"],
        "reason": "This checks whether the same Wi-Fi password works on another device.",
        "ask_if": {"wifi_join_status": "password_rejected"},
        "require_known": ["wifi_join_status"],
        "updates": {"yes": {"another_device_connects": True}, "no": {"another_device_connects": False}, "not tested": {"another_device_connects": None}},
    },
    {
        "id": "Q18",
        "prompt": "Is the affected device far from the router or separated by several walls or obstacles?",
        "options": ["yes", "no", "not sure"],
        "reason": "Distance and obstacles can reduce Wi-Fi coverage even when the wired connection works.",
        "ask_if": {"wired_connection": "works", "wifi_connection": "fails"},
        "require_known": ["wired_connection", "wifi_connection"],
        "updates": {"yes": {"device_far_or_obstructed": True}, "no": {"device_far_or_obstructed": False}, "not sure": {"device_far_or_obstructed": None}},
    },
    {
        "id": "Q19",
        "prompt": "Are there nearby electrical devices that could interfere with the wireless signal?",
        "options": ["yes", "no", "not sure"],
        "reason": "Some household electronics can affect Wi-Fi, especially when a wired connection still works.",
        "ask_if": {"wired_connection": "works", "wifi_connection": "fails"},
        "require_known": ["wired_connection", "wifi_connection"],
        "updates": {"yes": {"nearby_interference": True}, "no": {"nearby_interference": False}, "not sure": {"nearby_interference": None}},
    },
    {
        "id": "Q20",
        "prompt": "Is the connection still available, but performance becomes slow, laggy or stuttery?",
        "options": ["yes", "no", "not sure"],
        "reason": "Congestion can affect slow or stuttering performance without a complete connection failure.",
        "updates": {"yes": {"slowdown_reported": True}, "no": {"slowdown_reported": False}, "not sure": {"slowdown_reported": None}},
    },
    {
        "id": "Q21",
        "prompt": "At the time, is someone else using the connection for online video or another data-heavy activity?",
        "options": ["yes", "no", "not sure"],
        "reason": "Concurrent video viewing or other data-heavy activity can contribute to household congestion.",
        "ask_if": {"slowdown_reported": True},
        "require_known": ["slowdown_reported"],
        "updates": {"yes": {"heavy_household_use": True}, "no": {"heavy_household_use": False}, "not sure": {"heavy_household_use": None}},
    },
    {
        "id": "Q22",
        "prompt": "Does the slowdown recur at roughly the same busy time, such as each evening?",
        "options": ["yes", "no", "not sure"],
        "reason": "A repeatable time-of-day pattern can indicate a peak-period capacity issue, although the cause still needs provider testing.",
        "ask_if": {"slowdown_reported": True},
        "require_known": ["slowdown_reported"],
        "updates": {"yes": {"peak_time_pattern": True}, "no": {"peak_time_pattern": False}, "not sure": {"peak_time_pattern": None}},
    },
    {
        "id": "Q23",
        "prompt": "After restarting the router, did the household connection return?",
        "options": ["yes, it returned", "no, problem remained", "not tried"],
        "reason": "Once all devices are affected and the incoming cable is secure, this checks whether restarting the router restores the household connection. It applies to copper, part-fibre and full-fibre services.",
        "ask_if": {"device_scope": "all", "incoming_cable_secure": True},
        "require_known": ["device_scope", "incoming_cable_secure"],
        "updates": {"yes, it returned": {"router_restart_restored": True}, "no, problem remained": {"router_restart_restored": False}, "not tried": {"router_restart_restored": None}},
    },
    {
        "id": "Q24",
        "prompt": "If you have a separate modem, did restarting it restore the connection?",
        "options": ["yes, it restored service", "no", "not applicable", "not tried"],
        "reason": "This records whether restarting the separate modem restores service. It is asked only for copper and part-fibre connections.",
        "ask_if": {"access_type": ["copper", "part_fibre"], "separate_modem_status": ["normal", "abnormal"]},
        "require_known": ["access_type", "separate_modem_status"],
        "updates": {"yes, it restored service": {"dsl_modem_restart_restored": True}, "no": {"dsl_modem_restart_restored": False}, "not applicable": {"dsl_modem_restart_restored": None}, "not tried": {"dsl_modem_restart_restored": None}},
    },
    {
        "id": "Q25",
        "prompt": "If you have a fibre box, did restarting it restore the connection?",
        "options": ["yes, it restored service", "no", "not applicable", "not tried"],
        "reason": "This records whether restarting the fibre box restores service. It is kept separate from restarting a router or modem.",
        "ask_if": {"access_type": "full_fibre"},
        "require_known": ["access_type"],
        "updates": {"yes, it restored service": {"ont_restart_restored": True}, "no": {"ont_restart_restored": False}, "not applicable": {"ont_restart_restored": None}, "not tried": {"ont_restart_restored": None}},
        "frame_updates": {"yes, it restored service": {"ont": {"ont_restart_restored": True}}, "no": {"ont": {"ont_restart_restored": False}}},
    },
    {
        "id": "Q26",
        "prompt": "Has the landline been noisy or without dial tone recently, even if the noise has now cleared?",
        "options": ["yes, recently", "no", "not sure"],
        "reason": "This check records recent phone-line noise separately from the current dial tone. For copper connections, the diagnostic rules consider it alongside a reported slowdown before suggesting a provider line or profile check.",
        "ask_if": {"access_type": "copper"},
        "require_known": ["access_type"],
        "updates": {"yes, recently": {"recent_line_noise": True}, "no": {"recent_line_noise": False}, "not sure": {"recent_line_noise": None}},
    },
    {
        "id": "Q27",
        "prompt": "After re-entering the correct Wi-Fi password, did the affected device connect?",
        "options": ["yes, it connected", "no, the password was still rejected", "not tried", "not sure"],
        "reason": "This distinguishes a corrected credential entry from a password rejection that persists after the correct password is entered.",
        "ask_if": {"wifi_join_status": "password_rejected"},
        "require_known": ["wifi_join_status"],
        "updates": {
            "yes, it connected": {"password_correction_restored": True},
            "no, the password was still rejected": {"password_correction_restored": False},
            "not tried": {"password_correction_restored": None},
            "not sure": {"password_correction_restored": None},
        },
    },
]

def available_options(question: dict, facts: dict) -> list[str]:
    """Return only answers that apply to the household's connection type."""
    if question["id"] != "Q05":
        return list(question["options"])

    access_type = facts.get("access_type")
    if access_type == "full_fibre":
        return [
            "ONT: PON solid green and LOS off (normal)",
            "Nokia ONT: Power and PON steady green; Port indicator off",
            "ONT: PON off",
            "ONT: LOS red",
            "ONT: PON red (unclassified)",
            "ONT: PON and LOS both flashing",
            "ONT: PON flashing, LOS off (verification)",
            "not sure",
        ]
    if access_type in {"copper", "part_fibre"}:
        return [
            "Separate modem: normal",
            "Separate modem: abnormal",
            "no separate box",
            "not sure",
        ]
    return []

Q05_DISPLAY_OPTIONS = {
    "ONT: PON solid green and LOS off (normal)": "Fibre box: connection light steady green, warning light off (normal)",
    "Nokia ONT: Power and PON steady green; Port indicator off": "Nokia fibre box: Power and PON steady green; Port indicator off",
    "ONT: PON off": "Fibre box: connection light off",
    "ONT: LOS red": "Fibre box: warning light red",
    "ONT: PON red (unclassified)": "Fibre box: PON light red (unclassified)",
    "ONT: PON and LOS both flashing": "Fibre box: both lights flashing",
    "ONT: PON flashing, LOS off (verification)": "Fibre box: connection light flashing, warning light off (verification)",
    "Separate modem: normal": "Separate modem: lights normal",
    "Separate modem: abnormal": "Separate modem: lights abnormal",
    "no separate box": "No separate modem",
    "not sure": "Not sure",
}

def display_options(question: dict, facts: dict) -> list[str]:
    """return plain language labels for the answers currently available."""
    options = available_options(question, facts)
    if question["id"] == "Q05":
        return [Q05_DISPLAY_OPTIONS[option] for option in options]
    labels = question.get("display_options")
    if labels and len(labels) == len(question["options"]):
        label_by_option = dict(zip(question["options"], labels))
        return [label_by_option[option] for option in options]
    return options

def _condition_matches(value: object, expected: object) -> bool:
    if isinstance(expected, list):
        return value in expected
    return value == expected

def should_ask(question: dict, facts: dict) -> bool:
    """reeturn False when a branch is irrelevant or its prerequisite was not shown."""
    for fact_name in question.get("require_known", []):
        if facts.get(fact_name) is None:
            return False
    for fact_name, expected in question.get("ask_if", {}).items():
        current = facts.get(fact_name)
        if current is None:
            continue
        if not _condition_matches(current, expected):
            return False
    return True

def apply_answer(facts: dict, question_id: str, answer: str, frames=None) -> None:
    """vvalidates an answer and update only the facts attached to that option."""
    question = next((item for item in QUESTIONS if item["id"] == question_id), None)
    if question is None:
        raise KeyError(f"Unknown question: {question_id}")
    if answer not in available_options(question, facts):
        raise ValueError(f"Invalid answer for {question_id} and the selected connection type: {answer}")
    facts.update(question["updates"][answer])
    if frames is not None:
        frames.update_from_answer(question, answer)
