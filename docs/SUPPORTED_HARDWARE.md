# 🖧 Matriz de Hardware y Compatibilidad Multi-Fabricante

> **Dispositivos Certificados, Comandos de Diagnóstico, Mapeo de Acciones y Mecanismos de Reversión**

---

## 1. Resumen de Soporte Multi-Vendor

**NetworkingAgent** cuenta con controladores especializados (*drivers*) diseñados específicamente para interactuar con los sistemas operativos de red líderes en el mercado de telecomunicaciones corporativas y de proveedores de servicios de internet (ISPs).

---

## 2. Cisco IOS / IOS-XE (`cisco_ios` / `cisco_xe`)

### 2.1. Familias de Equipos Certificadas
- **Switches de Acceso y Distribución:** Cisco Catalyst 2960, 3560, 3750, 3850, 9200, 9300, 9500.
- **Routers de Servicios Integrados (ISR):** Cisco ISR 1100, 1900, 2900, 3900, 4300, 4400.
- **Routers de Agregación (ASR):** Cisco ASR 1000 Series.
- **Plataformas Virtuales:** Cisco CSR1000v, Catalyst 8000v.

### 2.2. Comandos de Diagnóstico e Inspección en Vivo
```bash
show ip interface brief
show processes cpu | include CPU utilization
show interfaces status
show interfaces counters errors
show ip route summary
show ip ospf neighbor
show interfaces status err-disabled
```

### 2.3. Mapeo de Acciones Neutrales a CLI Nativo
| Acción Neutral (`NetworkIntent`) | Sintaxis CLI Inyectada |
|---|---|
| `disable_interface` | `interface <iface>`<br>`shutdown` |
| `enable_interface` | `interface <iface>`<br>`no shutdown` |
| `restart_interface` | `interface <iface>`<br>`shutdown`<br>`no shutdown` |
| `set_interface_duplex_full` | `interface <iface>`<br>`speed auto`<br>`duplex full` |
| `set_interface_mtu` | `interface <iface>`<br>`ip mtu <mtu>` |
| `reset_bgp_neighbor` | `clear ip bgp <neighbor_ip>` |
| `clear_arp_cache` | `clear arp-cache` |

### 2.4. Mecanismo de Rollback y Snapshot
- **Snapshot Pre-Cambio:** Descarga de `show running-config` con marca de tiempo UTC.
- **Rollback:** `configure replace flash:<snapshot_name> force` o reversión atómica de comandos.

---

## 3. Cisco NX-OS (`cisco_nxos`)

### 3.1. Familias de Equipos Certificadas
- **Switches de Centro de Datos (Nexus):** Cisco Nexus 3000, 5000, 7000, 9000 Series (Spine/Leaf fabrics, ACI o modo Standalone NX-OS).
- **Plataformas Virtuales:** Cisco Nexus 9000v.

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

### 3.3. Mapeo de Acciones y Sesión Transaccional
Las configuraciones en NX-OS se encapsulan en una sesión atómica (`configure session AI_AGENT_FIX`):

| Acción Neutral | Sintaxis CLI Inyectada |
|---|---|
| `disable_interface` | `configure session AI_AGENT_FIX`<br>`interface <iface>`<br>`shutdown`<br>`commit` |
| `set_interface_mtu` | `configure session AI_AGENT_FIX`<br>`interface <iface>`<br>`mtu <mtu>`<br>`commit` |
| `reset_bgp_neighbor` | `clear bgp all <neighbor_ip> soft` |
| `clear_arp_cache` | `clear ip arp force-delete` |

### 3.4. Mecanismo de Rollback y Snapshot
- **Checkpoint Remoto:** Creación de un punto de restauración hardware nativo:  
  `checkpoint PRE_AI_REMEDIATION`
- **Rollback:** Restauración atómica de hardware:  
  `rollback running-config checkpoint PRE_AI_REMEDIATION`

---

## 4. Cisco IOS-XR (`cisco_xr`)

### 4.1. Familias de Equipos Certificadas
- **Routers de Núcleo y Carrier:** Cisco ASR 9000 Series, NCS 5500 Series, 8000 Series.
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

### 4.3. Mapeo de Acciones y Commit Confirmado
En IOS-XR todos los cambios se aplican con temporizador de confirmación automática de 3 minutos (`commit confirmed 180`), evitando aislamiento en caso de error:

```bash
interface <iface>
shutdown
commit confirmed 180
```

### 4.4. Mecanismo de Rollback
- **Rollback:** `rollback configuration last 1`

---

## 5. Juniper Junos OS (`juniper_junos`)

### 5.1. Familias de Equipos Certificadas
- **Switches de Campus y Datacenter:** Juniper EX2300, EX3400, EX4300, QFX5100, QFX10000.
- **Routers de Borde y Núcleo:** Juniper MX Series (MX104, MX204, MX480, MX960).
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

### 5.3. Mapeo de Acciones Neutrales a Junos CLI
| Acción Neutral | Sintaxis Junos CLI |
|---|---|
| `disable_interface` | `set interfaces <iface> disable`<br>`commit confirmed 3` |
| `enable_interface` | `delete interfaces <iface> disable`<br>`commit confirmed 3` |
| `set_interface_duplex_full` | `set interfaces <iface> gigether-options full-duplex`<br>`commit confirmed 3` |
| `set_interface_mtu` | `set interfaces <iface> mtu <mtu>`<br>`commit confirmed 3` |
| `reset_bgp_neighbor` | `clear bgp neighbor <neighbor_ip>` |
| `clear_arp_cache` | `clear arp` |

### 5.4. Mecanismo de Rollback
- **Commit Confirmado:** Si no se confirma el cambio en 3 minutos, Junos revierte automáticamente al commit previo.
- **Rollback Activo:** `rollback 1` seguido de `commit and-quit`.

---

## 6. MikroTik RouterOS (`mikrotik_routeros`)

### 6.1. Familias de Equipos Certificadas
- **Versiones de RouterOS:** Compatible con **RouterOS v6** y **RouterOS v7**.
- **Equipos Core:** MikroTik Cloud Core Router (CCR1009, CCR1036, CCR1072, CCR2004, CCR2116, CCR2216).
- **Equipos de Borde y Distribución:** MikroTik Cloud Router Switch (CRS305, CRS326, CRS328).
- **Equipos de Acceso y CPEs:** MikroTik RouterBOARD (RB3011, RB4011, RB5009, hEX, hAP ac/ax).
- **Plataformas Virtuales:** MikroTik Cloud Hosted Router (CHR) en VMware, Proxmox, AWS o KVM.

### 6.2. Comandos de Diagnóstico e Inspección en Vivo
```bash
/system resource print
/interface print stats
/interface ethernet print detail
/ip dns print
/interface print terse
/ip route print count-only
```

### 6.3. Mapeo de Acciones Neutrales a RouterOS CLI
| Acción Neutral | Sintaxis RouterOS CLI |
|---|---|
| `disable_interface` | `/interface set [find name="<iface>"] disabled=yes` |
| `enable_interface` | `/interface set [find name="<iface>"] disabled=no` |
| `restart_interface` | `/interface set [find name="<iface>"] disabled=yes`<br>`/interface set [find name="<iface>"] disabled=no` |
| `set_interface_duplex_full` | `/interface ethernet set [find name="<iface>"] auto-negotiation=yes full-duplex=yes` |
| `set_interface_mtu` | `/interface set [find name="<iface>"] mtu=<mtu>` |
| `reset_bgp_neighbor` | `/routing bgp connection disable [find remote.address="<ip>"]`<br>`/routing bgp connection enable [find remote.address="<ip>"]` |
| `clear_arp_cache` | `/ip arp remove [find]` |

### 6.4. Mecanismo de Rollback y Snapshot
- **Exportación Humana:** Descarga de `/export verbose=no` antes de aplicar cambios.
- **Hardware Backup Interno:** Creación de snapshot binario antes de ejecutar modificaciones:  
  `/system backup save name=before_ai_remediation`
- **Rollback:** Carga del snapshot original:  
  `/system backup load name=before_ai_remediation.backup`
