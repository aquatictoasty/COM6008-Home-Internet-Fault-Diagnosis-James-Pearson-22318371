"""simple frames for storing broadband equipment observations.

Each frame is a small record with named slots. unknown observations remain
None. The rule engine reads the slots as ordinary facts
"""

from __future__ import annotations

from typing import Any, ClassVar

class Frame:
    """base class that stores values in the slots defined by a frame"""

    FRAME_NAME: ClassVar[str] = "Frame"
    SLOTS: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def slot_definitions(cls) -> dict[str, None]:
        """return this frame's slots, including slots inherited from its parent"""
        names: list[str] = []
        for parent in reversed(cls.mro()):
            names.extend(getattr(parent, "SLOTS", ()))
        return {name: None for name in names}

    def __init__(self, **initial_values: Any) -> None:
        self._slots = {name: None for name in self.slot_definitions()}
        for name, value in initial_values.items():
            self.set_slot(name, value)

    def set_slot(self, name: str, value: Any) -> None:
        if name not in self._slots:
            raise KeyError(f"{name!r} is not a slot of {self.FRAME_NAME}")
        self._slots[name] = value

    def get_slot(self, name: str) -> Any:
        if name not in self._slots:
            raise KeyError(f"{name!r} is not a slot of {self.FRAME_NAME}")
        return self._slots[name]

    def as_dict(self) -> dict[str, Any]:
        return dict(self._slots)

class NetworkEquipmentFrame(Frame):
    """Shared observations held by equipment connected to the network."""

    FRAME_NAME = "Network equipment"
    SLOTS = ("power_state", "connection_status")

class RouterFrame(NetworkEquipmentFrame):
    FRAME_NAME = "Router"
    SLOTS = (
        "external_power_checked", "broadband_light", "internet_light",
        "incoming_cable_secure", "router_restart_restored", "nearby_interference",
    )

class FibreONTFrame(NetworkEquipmentFrame):
    FRAME_NAME = "Fibre box"
    SLOTS = ("pon_indicator", "los_indicator", "lan_indicator", "ont_restart_restored")

    def derive_link_status(self) -> str | None:
        """Interpret the fibre-box lights as normal, in verification or possibly faulty."""
        pon = self.get_slot("pon_indicator")
        los = self.get_slot("los_indicator")
        if pon == "off" or los == "red" or (pon == "flashing" and los == "flashing"):
            return "fault_indicator"
        if pon == "green_solid" and los == "off":
            return "healthy"
        if pon == "flashing" and los == "off":
            return "verification"
        return None

class DSLModemFrame(NetworkEquipmentFrame):
    FRAME_NAME = "Separate modem"
    SLOTS = (
        "dsl_sync_drops", "dial_tone", "recent_line_noise", "microfilter_status",
        "dsl_modem_restart_restored",
    )

    def derive_line_evidence(
        self, shared_connection_failure: bool | None, broadband_light: str | None
    ) -> str | None:
        """Only report line evidence when repeated signal loss has support."""
        sync_loss = self.get_slot("dsl_sync_drops")
        dial_tone = self.get_slot("dial_tone")
        if sync_loss is None:
            return None
        if sync_loss is False:
            return "no_sync_loss"
        if dial_tone == "poor":
            return "corroborated"
        if shared_connection_failure is True and broadband_light == "abnormal":
            return "corroborated"
        if dial_tone is not None and shared_connection_failure is not None and broadband_light is not None:
            return "sync_loss_only"
        return None

class UserDeviceFrame(Frame):
    FRAME_NAME = "User device"
    SLOTS = (
        "device_fails_other_networks", "wifi_join_status", "another_device_connects",
        "device_far_or_obstructed",
    )

class ConnectionContextFrame(Frame):
    FRAME_NAME = "Household connection"
    SLOTS = (
        "access_type", "device_scope", "wired_connection", "wifi_connection",
        "provider_status_outage", "local_outage_reports", "account_status",
        "slowdown_reported", "heavy_household_use", "peak_time_pattern",
        "untyped_access_status",
    )

# tthe table links each rule fact to the frame slot where the observation is stored.
FACT_LOCATORS: dict[str, tuple[str, str]] = {
    "access_type": ("context", "access_type"),
    "router_lights_on": ("router", "power_state"),
    "external_power_checked": ("router", "external_power_checked"),
    "broadband_light": ("router", "broadband_light"),
    "internet_light": ("router", "internet_light"),
    "separate_modem_status": ("access_equipment", "connection_status"),
    "ont_link_status": ("ont", "derived_link_status"),
    "incoming_cable_secure": ("router", "incoming_cable_secure"),
    "device_scope": ("context", "device_scope"),
    "wired_connection": ("context", "wired_connection"),
    "wifi_connection": ("context", "wifi_connection"),
    "dsl_sync_drops": ("dsl", "dsl_sync_drops"),
    "dial_tone": ("dsl", "dial_tone"),
    "recent_line_noise": ("dsl", "recent_line_noise"),
    "microfilter_status": ("dsl", "microfilter_status"),
    "provider_status_outage": ("context", "provider_status_outage"),
    "local_outage_reports": ("context", "local_outage_reports"),
    "account_status": ("context", "account_status"),
    "device_fails_other_networks": ("device", "device_fails_other_networks"),
    "wifi_join_status": ("device", "wifi_join_status"),
    "another_device_connects": ("device", "another_device_connects"),
    "device_far_or_obstructed": ("device", "device_far_or_obstructed"),
    "nearby_interference": ("router", "nearby_interference"),
    "slowdown_reported": ("context", "slowdown_reported"),
    "heavy_household_use": ("context", "heavy_household_use"),
    "peak_time_pattern": ("context", "peak_time_pattern"),
    "router_restart_restored": ("router", "router_restart_restored"),
    "dsl_modem_restart_restored": ("dsl", "dsl_modem_restart_restored"),
    "ont_restart_restored": ("ont", "ont_restart_restored"),
}

class FrameStore:
    """Create and update the frames for one consultation."""

    def __init__(self) -> None:
        self.context = ConnectionContextFrame()
        self.router = RouterFrame()
        self.device = UserDeviceFrame()
        self.ont: FibreONTFrame | None = None
        self.dsl: DSLModemFrame | None = None

    def _configure_access_frame(self, access_type: str | None) -> None:
        if access_type == "full_fibre":
            self.ont = self.ont or FibreONTFrame()
            self.dsl = None
        elif access_type in {"copper", "part_fibre"}:
            self.dsl = self.dsl or DSLModemFrame()
            self.ont = None

    def _active_access_frame(self) -> NetworkEquipmentFrame | None:
        return self.ont if self.ont is not None else self.dsl

    def _get_frame(self, name: str) -> Frame | None:
        return {
            "context": self.context,
            "router": self.router,
            "device": self.device,
            "ont": self.ont,
            "dsl": self.dsl,
        }.get(name)

    def set_fact(self, fact_name: str, value: Any) -> None:
        """Store a fact in the frame slot assigned to it."""
        if fact_name not in FACT_LOCATORS:
            raise KeyError(f"No frame slot is mapped for fact {fact_name!r}")
        frame_name, slot_name = FACT_LOCATORS[fact_name]
        if fact_name == "ont_link_status":
            raise ValueError("ont_link_status is calculated from the fibre-box lights")
        if frame_name == "context":
            self.context.set_slot(slot_name, value)
            if fact_name == "access_type":
                self._configure_access_frame(value)
        elif frame_name == "access_equipment":
            frame = self._active_access_frame()
            (frame or self.context).set_slot(
                slot_name if frame else "untyped_access_status", value
            )
        elif frame_name == "ont":
            self.ont = self.ont or FibreONTFrame()
            self.ont.set_slot(slot_name, value)
        elif frame_name == "dsl":
            self.dsl = self.dsl or DSLModemFrame()
            self.dsl.set_slot(slot_name, value)
        else:
            frame = self._get_frame(frame_name)
            if frame is None:
                raise KeyError(f"Frame {frame_name!r} is not available")
            frame.set_slot(slot_name, value)

    def set_equipment_slot(self, frame_name: str, slot_name: str, value: Any) -> None:
        """Set a slot used only by the relevant equipment frame."""
        if frame_name == "ont":
            frame = self.ont = self.ont or FibreONTFrame()
        elif frame_name == "dsl":
            frame = self.dsl = self.dsl or DSLModemFrame()
        else:
            frame = self._get_frame(frame_name)
        if frame is None:
            raise KeyError(f"Frame {frame_name!r} is not available")
        frame.set_slot(slot_name, value)

    def value_for_fact(self, fact_name: str) -> Any:
        """Read a fact from its frame, calculating the fibre status if needed."""
        if fact_name not in FACT_LOCATORS:
            return None
        frame_name, slot_name = FACT_LOCATORS[fact_name]
        if fact_name == "ont_link_status":
            return None if self.ont is None else self.ont.derive_link_status()
        if frame_name == "access_equipment":
            frame = self._active_access_frame()
            if frame is not None:
                return frame.get_slot(slot_name)
            return self.context.get_slot("untyped_access_status")
        frame = self._get_frame(frame_name)
        return None if frame is None else frame.get_slot(slot_name)

    def to_facts(self, base_facts: dict[str, Any]) -> dict[str, Any]:
        """Copy the stored observations into the format used by the rules."""
        facts = dict(base_facts)
        for name in FACT_LOCATORS:
            value = self.value_for_fact(name)
            if name == "ont_link_status" or value is not None or facts.get(name) is None:
                facts[name] = value
        facts["dsl_line_evidence"] = (
            None if self.dsl is None else self.dsl.derive_line_evidence(
                facts.get("shared_connection_failure"), facts.get("broadband_light")
            )
        )
        return facts

    def update_from_answer(self, question: dict, answer: str) -> None:
        """Save the facts and frame-specific slots from an answer."""
        for name, value in question["updates"][answer].items():
            if name in FACT_LOCATORS:
                self.set_fact(name, value)
        for frame_name, slots in question.get("frame_updates", {}).get(answer, {}).items():
            for slot_name, value in slots.items():
                self.set_equipment_slot(frame_name, slot_name, value)

    def active_frame_names(self) -> list[str]:
        names = ["Household connection", "Router"]
        if self.ont is not None:
            names.append("Fibre box")
        if self.dsl is not None:
            names.append("DSL modem")
        names.append("User device")
        return names

    def describe(self) -> str:
        return ", ".join(self.active_frame_names())

    def snapshot(self) -> dict[str, dict[str, Any]]:
        result = {
            "ConnectionContext": self.context.as_dict(),
            "Router": self.router.as_dict(),
            "UserDevice": self.device.as_dict(),
        }
        if self.ont is not None:
            result["Fibre box"] = self.ont.as_dict()
            result["Fibre box"]["derived_link_status"] = self.ont.derive_link_status()
        if self.dsl is not None:
            result["Separate modem"] = self.dsl.as_dict()
            result["Separate modem"]["derived_line_evidence"] = self.dsl.derive_line_evidence(
                self.context.get_slot("device_scope") == "all"
                and self.context.get_slot("wired_connection") == "fails",
                self.router.get_slot("broadband_light"),
            )
        return result

def new_frame_store() -> FrameStore:
    """Create the frames for a new consultation."""
    return FrameStore()
