"""working memory facts for one broadband troubleshooting session."""

# these are the observations used by the rules. the fibre box link status thing is worked out from its 2 indicator light slots
PRIMITIVE_FACTS = (
    "access_type",
    "router_lights_on",
    "external_power_checked",
    "broadband_light",
    "internet_light",
    "separate_modem_status",
    "ont_link_status",
    "incoming_cable_secure",
    "device_scope",
    "wired_connection",
    "wifi_connection",
    "dsl_sync_drops",
    "dial_tone",
    "recent_line_noise",
    "microfilter_status",
    "provider_status_outage",
    "local_outage_reports",
    "account_status",
    "device_fails_other_networks",
    "wifi_join_status",
    "another_device_connects",
    "password_correction_restored",
    "device_far_or_obstructed",
    "nearby_interference",
    "slowdown_reported",
    "heavy_household_use",
    "peak_time_pattern",
    "router_restart_restored",
    "dsl_modem_restart_restored",
    "ont_restart_restored",
)

# this frame derived fact is calculated from equipment slots before the production rules evaluate a diagnosis. It is not a direct questionnaire answer
FRAME_DERIVED_FACTS = (
    "dsl_line_evidence",
)

# 4 intermediate facts are populated only by production rules. they are not questionnaire answers. the ONT link status thing observation is also calculated separately by the fibre box frame thing from its indicator light slots.
DERIVED_FACTS = (
    "shared_connection_failure",
    "corroborated_outage_pattern",
    "provider_outage_candidate",
    "wireless_path_problem",
)

ALL_FACTS = PRIMITIVE_FACTS + FRAME_DERIVED_FACTS + DERIVED_FACTS

def new_facts() -> dict[str, object | None]:
    """Create a fresh fact store; None means unknown, not false."""
    return {name: None for name in ALL_FACTS}
