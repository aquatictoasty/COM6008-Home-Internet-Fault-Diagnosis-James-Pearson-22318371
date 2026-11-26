"""explain the rules that support each possible diagnosis."""

def explain_results(results: dict, facts: dict | None = None, frames=None) -> str:
    if not results:
        if facts and facts.get("password_correction_restored") is True:
            explanation = (
                "No ongoing Wi-Fi password problem is indicated. The affected device connected "
                "after the correct password was re-entered, so the earlier problem appears to "
                "have been a typing error. If it happens again, check the saved password and "
                "compare with another device."
            )
        elif facts and facts.get("microfilter_status") == "missing":
            explanation = (
                "No provider line fault is established. Your phone socket appears to need a "
                "microfilter, but one is not fitted. Fit the correct filter using the provider's "
                "instructions and test the connection again. A missing filter is a local setup "
                "issue and is not, by itself, evidence of a faulty outside line."
            )
        else:
            explanation = (
                "No diagnosis rule is supported by the answers. Check the incoming cables, repeat "
                "the wired test and check the provider's service status. Contact the provider if the "
                "problem continues."
            )
        if frames is not None and frames.ont is not None and frames.ont.get_slot("lan_indicator") == "off":
            explanation += (
                "\n\nNokia ONT Ethernet check: the Port indicator is off. Check both ends "
                "of the cable between the ONT and Hub, and try another cable if needed. This is a "
                "cable check and does not, by itself, indicate a fibre-link fault."
            )
        return explanation

    lines = ["Possible explanation(s):"]
    if len(results) > 1:
        lines.append(
            "More than one rule has matched. The system lists each possible explanation "
            "rather than claiming that one is certain. Further checks may be needed."
        )

    for item in results.values():
        details = item["details"]
        lines.extend(["", details["name"], details["description"]])
        if item["derivations"]:
            lines.append("Earlier reasoning:")
            for rule in item["derivations"]:
                lines.append(f"  {rule['id']}: {rule['explanation']}")
                lines.append("  Sources: " + ", ".join(rule["sources"]))
        lines.append("Rule(s) that matched:")
        for rule in item["rules"]:
            lines.append(f"  {rule['id']}: {rule['explanation']}")
            lines.append("  Sources: " + ", ".join(rule["sources"]))
        lines.append("Suggested next step: " + details["advice"])

    if facts and facts.get("microfilter_status") == "missing":
        lines.append(
            "Separate setup check: fit the required microfilter before asking the provider "
            "to investigate an outside line fault."
        )
    if facts and facts.get("password_correction_restored") is True:
        lines.append("The affected device connected after the correct Wi-Fi password was re-entered.")
    if frames is not None and frames.ont is not None and frames.ont.get_slot("lan_indicator") == "off":
        lines.extend(["", "Nokia ONT Ethernet check: the Port indicator is off. Check both ends of the cable between the ONT and Hub, and try another cable if needed. This is a cable check and does not, by itself, indicate a fibre-link fault."])
    lines.append("These are suggestions based on household answers, not confirmed engineering diagnoses.")
    return "\n".join(lines)
