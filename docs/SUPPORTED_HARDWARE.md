# 🖧 Matriz de Hardware y Compatibilidad Multi-Fabricante v2.1.1

> **Dispositivos Certificados, Comandos de Diagnóstico Especializados por Protocolo, Síntesis Declarativa y Mecanismos de Reversión**

---

## 1. Resumen de Soporte Multi-Vendor

**NetworkingAgent Enterprise v2.1** incorpora controladores especializados (*drivers*) diseñados para interactuar de forma nativa con los principales sistemas operativos de red del mercado corporativo y de telecomunicaciones:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        SISTEMAS OPERATIVOS DE RED SOPORTADOS                           │
│                                                                                        │
│   • Cisco IOS / IOS-XE    (Catalyst, ISR, ASR, CSR1000v, C8000v)                       │
│   • Cisco NX-OS           (Nexus 3000, 5000, 7000, 9000 Data Center)                  │
│   • Cisco IOS-XR          (ASR 9000, NCS 5500, XRv9000 Service Provider)              │
│   • Juniper Junos OS      (EX, QFX, MX, SRX, vSRX Campus & Core)                      │
│   • MikroTik RouterOS     (RouterBOARD, Cloud Core Router CCR v6 & v7, CHR)            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Cisco IOS / IOS-XE (`cisco_ios` / `cisco_xe`)

### 2.1. Familias de Equipos Certificadas
- **Switches de Acceso y Campus:** Cisco Catalyst 2960-X/XR, 3560, 3750-X, 3850, 9200, 9300, 9500.
- **Routers de Servicios Integrados:** Cisco ISR 1100, 1900, 2900, 3900, 4300, 4400 Series.
- **Routers de Agregación de Borde:** Cisco ASR 1000 Series (ASR 1001-X, 1002-HX, 1006-X).
- **Entornos Virtualizados:** Cisco CSR1000v, Cisco Catalyst 8000v (C8000v).

### 2.2. Comandos de Inspección en Vivo y Salud Base
```bash
show ip interface brief
show processes cpu | include CPU utilization
show interfaces status
show interfaces counters errors
show ip route summary
show ip ospf neighbor
show interfaces status err-disabled
```

### 2.3. Comandos de Diagnóstico Especializados por Protocolo
| Protocolo | Método Interno | Comandos CLI Ejecutados |
|---|---|---|
| **BGP** | `_bgp_diag_commands()` | `show ip bgp summary`<br>`show ip bgp neighbors` |
| **OSPF** | `_ospf_diag_commands()` | `show ip ospf neighbor`<br>`show ip ospf interface brief` |
| **VLAN / Trunk** | `_vlan_diag_commands()` | `show vlan brief`<br>`show interfaces trunk` |
| **STP** | `_stp_diag_commands()` | `show spanning-tree summary`<br>`show spanning-tree detail` |
| **Port-Channel** | `_channel_diag_commands()` | `show etherchannel summary`<br>`show etherchannel port-channel` |
| **ACL** | `_acl_diag_commands()` | `show access-lists` |

### 2.4. Síntesis de Configuración Declarativa
- **BGP:** `router bgp <asn>` → `neighbor <ip> remote-as <asn>` → `network <net> mask <mask>`.
- **OSPF:** `router ospf <process_id>` → `router-id <id>` → `network <ip> <wildcard> area <area>`.
- **VLAN & SVI:** `vlan <id>` / `name <nombre>` → `interface Vlan<id>` / `ip address <ip> <mask>` / `no shutdown`.
- **STP:** `spanning-tree mode rapid-pvst` / `spanning-tree portfast bpduguard default`.
- **Port-Channel:** `interface range <ifaces>` → `channel-group <id> mode active`.

### 2.5. Mecanismo de Rollback y Snapshot
- **Snapshot Pre-Cambio:** Descarga de `show running-config` persistido localmente en `backups/<host>_<timestamp>.cfg`.
- **Persistencia Post-Cambio:** Ejecución automática de `copy running-config startup-config` (`save_config`).
- **Rollback Atómico:** `configure replace flash:<snapshot_name> force` o aplicación de `rollback_commands` negados.

---

## 3. Cisco NX-OS (`cisco_nxos`)

### 3.1. Familias de Equipos Certificadas
- **Switches de Centro de Datos (Nexus):** Cisco Nexus 3000, 5000, 7000, 9000 Series (Spine-and-Leaf, VXLAN EVPN).
- **Plataformas Virtuales:** Cisco Nexus 9000v (NX-OSv).

### 3.2. Comandos de Diagnóstico e Inspección en Vivo
```bash
show interface status
show system resources
show ip interface brief
show interface counters errors
show ip route summary
show bgp l2vpn evpn summary
show ip ospf neighbors
show interfaces status err-disabled
```

### 3.3. Comandos de Diagnóstico Especializados por Protocolo
| Protocolo | Método Interno | Comandos CLI Ejecutados |
|---|---|---|
| **BGP** | `_bgp_diag_commands()` | `show ip bgp summary`<br>`show ip bgp neighbors` |
| **OSPF** | `_ospf_diag_commands()` | `show ip ospf neighbors`<br>`show ip ospf interface brief` |
| **VLAN / Trunk** | `_vlan_diag_commands()` | `show vlan brief`<br>`show interface trunk` |
| **STP** | `_stp_diag_commands()` | `show spanning-tree summary`<br>`show spanning-tree detail` |
| **Port-Channel** | `_channel_diag_commands()` | `show port-channel summary`<br>`show lacp neighbor` |
| **ACL** | `_acl_diag_commands()` | `show ip access-lists` |

### 3.4. Sesión Transaccional y Checkpoints de Hardware
Las configuraciones en NX-OS se ejecutan mediante sesiones atómicas aisladas:
```bash
configure session AI_AGENT_FIX
  interface Ethernet1/1
    mtu 9216
  commit
```

### 3.5. Mecanismo de Rollback
- **Checkpoint Local de Hardware:** Creación del punto de restauración nativo:  
  `checkpoint PRE_AI_REMEDIATION`
- **Rollback:** Restauración sin reinicio a nivel de hardware:  
  `rollback running-config checkpoint PRE_AI_REMEDIATION`

---

## 4. Cisco IOS-XR (`cisco_xr`)

### 4.1. Familias de Equipos Certificadas
- **Routers de Núcleo y Carrier:** Cisco ASR 9000 Series (ASR 9006, 9010, 9904), Cisco NCS 5500 Series, 8000 Series.
- **Plataformas Virtuales:** Cisco XRv9000.

### 4.2. Comandos de Diagnóstico e Inspección en Vivo
```bash
show ipv4 interface brief
show processes cpu | include CPU
show interfaces summary
show route summary
show ospf neighbor
show bgp summary
```

### 4.3. Commit Confirmado y Reversión
En IOS-XR los cambios se encapsulan con temporizador de confirmación automática de 3 minutos (`commit confirmed 180`). Si el agente o el operador pierde conectividad, el sistema operativo revierte automáticamente al estado anterior:
```bash
interface GigabitEthernet0/0/0/0
 mtu 9216
commit confirmed 180
```
- **Rollback Explícito:** `rollback configuration last 1`

---

## 5. Juniper Junos OS (`juniper_junos`)

### 5.1. Familias de Equipos Certificadas
- **Switches de Campus y Datacenter:** Juniper EX2300, EX3400, EX4300, QFX5100, QFX10000 Series.
- **Routers Universales de Borde:** Juniper MX Series (MX104, MX204, MX480, MX960).
- **Firewalls y Seguridad:** Juniper SRX Series (SRX300, SRX1500, SRX4200, vSRX).

### 5.2. Comandos de Diagnóstico e Inspección en Vivo
```bash
show interfaces terse
show chassis routing-engine
show interfaces extensive | match "Errors|Drops|Duplex"
show route summary
show system uptime
show ospf neighbor
show bgp summary
```

### 5.3. Comandos de Diagnóstico Especializados por Protocolo
| Protocolo | Método Interno | Comandos CLI Ejecutados |
|---|---|---|
| **BGP** | `_bgp_diag_commands()` | `show bgp summary`<br>`show bgp neighbor` |
| **OSPF** | `_ospf_diag_commands()` | `show ospf neighbor`<br>`show ospf interface` |
| **VLAN** | `_vlan_diag_commands()` | `show vlans`<br>`show ethernet-switching interfaces` |
| **STP** | `_stp_diag_commands()` | `show spanning-tree bridge`<br>`show spanning-tree interface` |
| **Port-Channel (AE)** | `_channel_diag_commands()` | `show interfaces terse ae*`<br>`show lacp interfaces` |
| **Firewall / ACL** | `_acl_diag_commands()` | `show firewall` |

### 5.4. Síntesis Jerárquica Junos y Commit Confirmado
Toda modificación en Junos se valida en bloque y se inyecta con temporizador de reversión:
```bash
set protocols bgp group EXTERNAL neighbor 192.168.10.2 peer-as 65100
set protocols bgp group EXTERNAL neighbor 192.168.10.2 description "Enlace Datacenter"
commit confirmed 3
```
- **Rollback:** `rollback 1` seguido de `commit and-quit`.

---

## 6. MikroTik RouterOS (`mikrotik_routeros`)

### 6.1. Familias de Equipos Certificadas
- **Versiones de RouterOS:** Compatible con **RouterOS v6** y la nueva arquitectura de enrutamiento de **RouterOS v7**.
- **Equipos de Núcleo:** MikroTik Cloud Core Router (CCR1009, CCR1016, CCR1036, CCR2004, CCR2116, CCR2216).
- **Switches de Distribución:** MikroTik Cloud Router Switch (CRS305, CRS309, CRS326, CRS328).
- **Equipos de Acceso y Branch:** MikroTik RouterBOARD (RB3011, RB4011, RB5009, hEX, hAP ac3/ax3).
- **Plataformas en la Nube:** MikroTik Cloud Hosted Router (CHR) en Proxmox, VMware ESXi, AWS, Azure o KVM.

### 6.2. Comandos de Diagnóstico e Inspección en Vivo
```bash
/system resource print
/interface print stats
/interface ethernet print detail
/ip dns print
/interface print terse
/ip route print count-only
```

### 6.3. Comandos de Diagnóstico Especializados por Protocolo
| Protocolo | Método Interno | Comandos CLI Ejecutados |
|---|---|---|
| **BGP** | `_bgp_diag_commands()` | `/routing bgp session print`<br>`/routing bgp connection print` |
| **OSPF** | `_ospf_diag_commands()` | `/routing ospf neighbor print`<br>`/routing ospf interface print` |
| **VLAN / Bridge** | `_vlan_diag_commands()` | `/interface vlan print`<br>`/interface bridge vlan print` |
| **STP** | `_stp_diag_commands()` | `/interface bridge print`<br>`/interface bridge port print` |
| **Bonding (LACP)** | `_channel_diag_commands()` | `/interface bonding print` |
| **Firewall / ACL** | `_acl_diag_commands()` | `/ip firewall filter print` |

### 6.4. Mecanismo de Rollback y Snapshot
- **Exportación de Configuración:** `/export verbose=no` persistido en disco local antes de cualquier cambio.
- **Snapshot Binario Interno de Hardware:**  
  `/system backup save name=before_ai_remediation`
- **Rollback:** Restauración atómica del archivo de respaldo binario:  
  `/system backup load name=before_ai_remediation.backup`

---

## 7. Tabla Comparativa de Capacidades por Plataforma

| Capacidad Operacional | Cisco IOS/XE | Cisco NX-OS | Cisco IOS-XR | Juniper Junos | MikroTik RouterOS |
|---|:---:|:---:|:---:|:---:|:---:|
| **SSH Connection Pooling** | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí |
| **Descubrimiento Dinámico de Mgmt IP** | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí |
| **Diagnóstico Dinámico por Síntoma** | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí |
| **Configuración Declarativa Multi-Protocolo** | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí |
| **Detección de Solapamiento IP y Colisiones** | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí |
| **Validación Sintáctica Pre-Flight (Dry-Run)** | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí |
| **Diagnóstico de Conectividad (Ping/SSH 22)** | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí |
| **Commit Confirmado Nativo** | ❌ (Replace) | ❌ (Checkpoint) | ✅ Sí (180s) | ✅ Sí (3 min) | ❌ (Backup binario) |
| **Rollback Atómico en Caliente** | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí |
| **Soporte Despliegue en Lote (Batch)** | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí | ✅ Sí |
