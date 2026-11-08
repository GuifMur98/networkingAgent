"""Unit tests for the Intelligent Configuration Conflict Analyzer and Non-Destructive Engine."""

from networking_agent.engine.conflict_analyzer import ConfigConflictAnalyzer
from networking_agent.models.config_intent import ConfigurationIntent, ProtocolConfigType

CISCO_SAMPLE_CONFIG = """
hostname Edge-Router-01
!
interface GigabitEthernet0/0
 description WAN Uplink to Primary ISP
 ip address 198.51.100.2 255.255.255.252
!
interface GigabitEthernet0/1
 description Corporate LAN
 ip address 192.168.10.1 255.255.255.0
!
router ospf 1
 router-id 10.255.255.1
 network 192.168.10.0 0.0.0.255 area 0
!
vlan 10,20,30,100
"""

JUNOS_SAMPLE_CONFIG = """
routing-options {
    autonomous-system 65200;
}
protocols {
    ospf {
        area 0.0.0.0 {
            interface ge-0/0/1.0;
        }
    }
}
interfaces {
    ge-0/0/1 {
        unit 0 {
            family inet {
                address 10.200.1.1/24;
            }
        }
    }
}
"""

MIKROTIK_SAMPLE_CONFIG = """
/routing ospf instance
add disabled=no name=default-v2
/routing ospf area
add disabled=no instance=default-v2 name=backbone-v2
/ip address
add address=192.168.88.1/24 interface=bridge network=192.168.88.0
add address=10.0.0.2/30 interface=ether1 network=10.0.0.0
"""


def test_conflict_analyzer_discovers_active_protocols_cisco():
    state = ConfigConflictAnalyzer.analyze_running_state(CISCO_SAMPLE_CONFIG, vendor_family="cisco_ios")
    assert "ospf" in state.active_routing_protocols
    assert state.active_routing_protocols["ospf"] == ["1"]
    assert len(state.configured_interfaces) == 2
    assert 10 in state.active_vlans
    assert 100 in state.active_vlans


def test_conflict_analyzer_discovers_active_protocols_junos():
    state = ConfigConflictAnalyzer.analyze_running_state(JUNOS_SAMPLE_CONFIG, vendor_family="juniper_junos")
    assert "ospf" in state.active_routing_protocols
    assert "bgp" in state.active_routing_protocols
    assert "65200" in state.active_routing_protocols["bgp"]
    assert len(state.configured_interfaces) >= 1


def test_conflict_analyzer_discovers_active_protocols_mikrotik():
    state = ConfigConflictAnalyzer.analyze_running_state(MIKROTIK_SAMPLE_CONFIG, vendor_family="mikrotik_routeros")
    assert "ospf" in state.active_routing_protocols
    assert len(state.configured_interfaces) == 2


def test_dynamic_routing_disambiguation_selects_active_ospf():
    # User requests dynamic routing without specifying OSPF
    req = "agrega la nueva red 172.16.50.0/24 al protocolo de enrutamiento dinamico"
    proto_hint, explanation = ConfigConflictAnalyzer.resolve_dynamic_routing_disambiguation(
        request_text=req,
        running_config=CISCO_SAMPLE_CONFIG,
        vendor_family="cisco_ios",
    )
    assert proto_hint == "ospf (proceso 1)"
    assert "OSPF activo (Proceso ID: 1)" in explanation


def test_dynamic_routing_disambiguation_when_no_protocols_exist():
    empty_config = "hostname Switch-Access-01\ninterface Gi0/1\nswitchport mode access\n"
    req = "agrega una red al enrutamiento dinámico"
    proto_hint, explanation = ConfigConflictAnalyzer.resolve_dynamic_routing_disambiguation(
        request_text=req,
        running_config=empty_config,
        vendor_family="cisco_ios",
    )
    assert proto_hint == "ospf"
    assert "No se detectaron protocolos de enrutamiento dinámico" in explanation


def test_ip_collision_detected_when_subnet_overlaps_other_interface():
    # Candidate commands propose assigning 192.168.10.50/24 on Gi0/2, but 192.168.10.1/24 is on Gi0/1
    candidate_cmds = [
        "interface GigabitEthernet0/2",
        "ip address 192.168.10.50 255.255.255.0",
        "no shutdown",
    ]
    report = ConfigConflictAnalyzer.detect_conflicts(
        request_text="asigna la ip 192.168.10.50 a Gi0/2",
        candidate_commands=candidate_cmds,
        running_config=CISCO_SAMPLE_CONFIG,
        vendor_family="cisco_ios",
    )
    assert report["conflicts_found"] is True
    assert "[!] Conflicto detectado" in report["conflict_analysis"]
    assert "GigabitEthernet0/1" in report["conflict_analysis"]


def test_no_conflicts_detected_for_clean_subnet():
    # Candidate commands propose a completely fresh subnet (172.20.1.0/24)
    candidate_cmds = [
        "interface GigabitEthernet0/3",
        "ip address 172.20.1.1 255.255.255.0",
        "no shutdown",
    ]
    report = ConfigConflictAnalyzer.detect_conflicts(
        request_text="asigna la ip 172.20.1.1 a Gi0/3",
        candidate_commands=candidate_cmds,
        running_config=CISCO_SAMPLE_CONFIG,
        vendor_family="cisco_ios",
    )
    assert report["conflicts_found"] is False
    assert "[OK]" in report["conflict_analysis"]


def test_vlan_preservation_when_vlan_already_exists():
    candidate_cmds = ["vlan 10", "name VENTAS_ACTUALIZADA"]
    report = ConfigConflictAnalyzer.detect_conflicts(
        request_text="actualiza nombre de vlan 10",
        candidate_commands=candidate_cmds,
        running_config=CISCO_SAMPLE_CONFIG,
        vendor_family="cisco_ios",
    )
    assert report["conflicts_found"] is False
    assert "VLAN 10 ya existe en el equipo: se preservó su nombre y puertos" in report["conflict_analysis"]


def test_enrich_intent_populates_conflict_and_state_summary():
    intent = ConfigurationIntent(
        protocol_type=ProtocolConfigType.OSPF,
        description="Integración de red LAN en OSPF",
        candidate_commands=["router ospf 1", "network 172.16.50.0 0.0.0.255 area 0"],
        verification_commands=["show ip ospf neighbor"],
        rollback_commands=["router ospf 1", "no network 172.16.50.0 0.0.0.255 area 0"],
    )
    enriched = ConfigConflictAnalyzer.enrich_intent(
        intent=intent,
        request_text="agrega red al enrutamiento dinamico",
        running_config=CISCO_SAMPLE_CONFIG,
        vendor_family="cisco_ios",
    )
    assert enriched.existing_state_summary is not None
    assert "OSPF (1)" in enriched.existing_state_summary
    assert "[OK]" in enriched.conflict_analysis
