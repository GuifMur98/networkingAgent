"""Blast Radius assessment and protection policies."""

from typing import List, Optional

from networking_agent.core.config import settings
from networking_agent.core.exceptions import BlastRadiusViolationError
from networking_agent.core.logging import logger
from networking_agent.models.intent import NetworkIntent


class BlastRadiusGuard:
    """Ensures that autonomous or proposed actions do not exceed defined safety blast radius."""

    def __init__(self, protected_interfaces: Optional[List[str]] = None):
        self.protected_interfaces = [iface.lower() for iface in (protected_interfaces or settings.protected_interfaces)]

    def verify_intent(
        self,
        intent: NetworkIntent,
        wan_interfaces: Optional[List[str]] = None,
    ) -> None:
        """Verifies that the intent does not target critical infrastructure components."""
        if not intent.requires_config_change or intent.action == "none":
            return

        if intent.target_interface:
            target_lower = intent.target_interface.lower()

            # 1. Strict WAN & Uplink Safeguard (Prevents remote isolation)
            all_wan = set(
                [w.lower() for w in (wan_interfaces or [])]
                + ["wan", "uplink", "internet", "gateway", "dialer", "ether1"]
            )
            is_wan = any(target_lower == w or target_lower.startswith(w) for w in all_wan)

            if is_wan and intent.action in ["disable_interface", "restart_interface"]:
                msg = (
                    f"CRITICAL SAFETY VIOLATION: Target interface '{intent.target_interface}' is identified "
                    f"as an active WAN / Uplink / Gateway interface. Disabling or bouncing this interface "
                    f"is strictly prohibited to prevent total loss of remote management and network blackout."
                )
                logger.critical(f"[bold red]{msg}[/bold red]")
                raise BlastRadiusViolationError(msg)

            # 2. Base protected interfaces (management, loopbacks, etc.)
            for protected in self.protected_interfaces:
                if target_lower == protected or target_lower.startswith(protected):
                    msg = (
                        f"Blast Radius Violation: Target interface '{intent.target_interface}' "
                        f"is protected against automated modification (management/core interface)."
                    )
                    logger.error(f"[bold red]{msg}[/bold red]")
                    raise BlastRadiusViolationError(msg)

        if intent.action == "disable_interface":
            logger.warning(
                f"[yellow]High blast radius action requested: 'disable_interface' on {intent.target_interface}[/yellow]"
            )

        if intent.action == "reset_bgp_neighbor" and not intent.bgp_neighbor_ip:
            raise BlastRadiusViolationError("BGP reset action requires a specific neighbor IP address.")
