"""Connectivity and reachability diagnostic engine for network inventory devices."""

import asyncio
import platform
import re
import socket
import time
from dataclasses import dataclass
from typing import Optional

from netmiko import ConnectHandler

from networking_agent.core.logging import logger
from networking_agent.models.device import DeviceInventory


@dataclass
class PingResult:
    """Structured result of an ICMP ping execution."""

    host: str
    is_reachable: bool
    rtt_avg: str
    packet_loss: str
    sent: int = 0
    received: int = 0
    raw_output: str = ""


@dataclass
class PortResult:
    """Structured result of a TCP port connection probe."""

    host: str
    port: int
    is_open: bool
    elapsed_ms: Optional[int]
    error: Optional[str]


@dataclass
class SSHCheckResult:
    """Structured result of an SSH authentication handshake test."""

    host: str
    port: int
    authenticated: bool
    prompt: Optional[str]
    elapsed_ms: Optional[int]
    error: Optional[str]


@dataclass
class DeviceConnectivityReport:
    """Comprehensive multi-layer connectivity report for a network device."""

    device_id: Optional[int]
    host: str
    ping: PingResult
    tcp_port: PortResult
    ssh: Optional[SSHCheckResult] = None

    @property
    def is_online(self) -> bool:
        """Device is considered online if reachable via ICMP or TCP port is open."""
        return self.ping.is_reachable or self.tcp_port.is_open


class ConnectivityTester:
    """Performs L3 ICMP, L4 TCP port, and L7 SSH diagnostics against network devices."""

    @staticmethod
    async def ping(host: str, count: int = 2, timeout_ms: int = 1200) -> PingResult:
        """Executes a system ping command asynchronously and parses packet loss and latency."""
        is_windows = platform.system().lower() == "windows"
        cmd = [
            "ping",
            "-n" if is_windows else "-c",
            str(count),
            "-w" if is_windows else "-W",
            str(timeout_ms),
            host,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=4.0)
            raw = stdout.decode("cp1252" if is_windows else "utf-8", errors="ignore")

            # Determine reachability by reply markers and returncode
            has_reply = ("TTL=" in raw or "ttl=" in raw) and proc.returncode == 0

            # Parse average RTT
            rtt_match = re.search(r"(?:Media|Average|Promedio|media)\s*=\s*(\d+ms|\d+\.?\d*ms)", raw)
            avg_rtt = rtt_match.group(1) if rtt_match else ("<1ms" if has_reply else "N/A")

            # Parse packet loss
            loss_match = re.search(r"\((\d+%).*?(?:perdidos|loss)", raw)
            packet_loss = loss_match.group(1) if loss_match else ("0%" if has_reply else "100%")

            # Parse packet counts
            sent_m = re.search(r"(?:enviados|Sent)\s*=\s*(\d+)", raw)
            recv_m = re.search(r"(?:recibidos|Received)\s*=\s*(\d+)", raw)
            sent = int(sent_m.group(1)) if sent_m else count
            received = int(recv_m.group(1)) if recv_m else (count if has_reply else 0)

            return PingResult(
                host=host,
                is_reachable=has_reply,
                rtt_avg=avg_rtt,
                packet_loss=packet_loss,
                sent=sent,
                received=received,
                raw_output=raw.strip(),
            )
        except Exception as e:
            logger.debug(f"Ping exception for {host}: {e}")
            return PingResult(
                host=host,
                is_reachable=False,
                rtt_avg="Timeout",
                packet_loss="100%",
                sent=count,
                received=0,
                raw_output=str(e),
            )

    @staticmethod
    async def check_port(host: str, port: int = 22, timeout: float = 2.5) -> PortResult:
        """Probes TCP socket connectivity to the specified port."""
        loop = asyncio.get_running_loop()

        def _probe() -> tuple[bool, Optional[int], Optional[str]]:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try:
                t0 = time.perf_counter()
                s.connect((host, port))
                elapsed = int((time.perf_counter() - t0) * 1000)
                return True, elapsed, None
            except Exception as ex:
                return False, None, str(ex)
            finally:
                s.close()

        is_open, elapsed_ms, err = await loop.run_in_executor(None, _probe)
        return PortResult(
            host=host,
            port=port,
            is_open=is_open,
            elapsed_ms=elapsed_ms,
            error=err,
        )

    @staticmethod
    async def test_ssh_credentials(device: DeviceInventory, timeout: float = 6.0) -> SSHCheckResult:
        """Tests full Netmiko SSH authentication against the device without modifying state."""
        loop = asyncio.get_running_loop()

        def _ssh() -> tuple[bool, Optional[str], Optional[int], Optional[str]]:
            t0 = time.perf_counter()
            conn_dict = device.to_netmiko_dict()
            conn_dict["conn_timeout"] = int(timeout)
            try:
                with ConnectHandler(**conn_dict) as ssh:
                    prompt = ssh.find_prompt()
                    elapsed = int((time.perf_counter() - t0) * 1000)
                    return True, prompt, elapsed, None
            except Exception as ex:
                return False, None, None, str(ex)

        auth_ok, prompt, elapsed_ms, err = await loop.run_in_executor(None, _ssh)
        return SSHCheckResult(
            host=device.host,
            port=device.port,
            authenticated=auth_ok,
            prompt=prompt,
            elapsed_ms=elapsed_ms,
            error=err,
        )

    @classmethod
    async def run_full_diagnosis(
        cls,
        device: DeviceInventory,
        include_ssh: bool = False,
    ) -> DeviceConnectivityReport:
        """Executes ICMP ping, TCP port probe, and optionally SSH handshake."""
        ping_res = await cls.ping(device.host)
        port_res = await cls.check_port(device.host, device.port)

        ssh_res: Optional[SSHCheckResult] = None
        if include_ssh and port_res.is_open:
            ssh_res = await cls.test_ssh_credentials(device)

        return DeviceConnectivityReport(
            device_id=getattr(device, "id", None),
            host=device.host,
            ping=ping_res,
            tcp_port=port_res,
            ssh=ssh_res,
        )
