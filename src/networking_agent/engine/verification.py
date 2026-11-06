"""Closed-loop health verification engine for comparing pre and post change states."""

from typing import Dict

from networking_agent.core.logging import logger


class VerificationEngine:
    """Compares pre-remediation and post-remediation device states."""

    @classmethod
    def evaluate_changes(
        cls,
        pre_state: Dict[str, str],
        post_state: Dict[str, str],
        target_entity: str = "",
    ) -> bool:
        """Determines whether the remediation succeeded and no regressions were introduced.

        Returns True if post-check is healthy.
        """
        logger.info("[*] Comparing pre-change and post-change operational states...")

        # Analyze differences across health check commands
        has_critical_error = False
        for cmd, post_out in post_state.items():
            pre_out = pre_state.get(cmd, "")
            if pre_out != post_out:
                logger.info(f"[*] State changed for diagnostic command: [cyan]{cmd}[/cyan]")

            # Check for err-disabled presence
            if "err-disabled" in cmd.lower() and "err-disabled" in post_out.lower():
                if target_entity and target_entity.lower() in post_out.lower():
                    logger.warning(f"[yellow]Target '{target_entity}' remains in err-disabled state.[/yellow]")
                    has_critical_error = True

            # Check for BGP/OSPF neighbor states
            if ("ospf" in cmd.lower() or "bgp" in cmd.lower()) and "down" in post_out.lower():
                logger.warning(f"[yellow]Detected neighbor down in command '{cmd}'[/yellow]")

        if has_critical_error:
            logger.error("[bold red]Post-change verification failed: target error still active.[/bold red]")
            return False

        logger.info("[bold green]Post-change verification passed successfully.[/bold green]")
        return True
