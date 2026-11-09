# 🚀 NetworkingAgent Enterprise v2.2.0 - Release Notes

**Fecha de Lanzamiento:** 8 de Noviembre de 2026  
**Etiqueta de Versión:** `v2.2.0`  
**Licencia:** Apache 2.0  
**Certificación:** Python 3.14 / Textual TUI v2.2  
**Estado de Pruebas:** 209/209 aprobadas (100% passing)  

---

## 🌟 Resumen Ejecutivo

**NetworkingAgent Enterprise v2.2.0** introduce un hito arquitectónico fundamental: el nuevo **Módulo 6: Packet Lab**, un analizador y sniffer forense de paquetes de red integrado en la terminal al estilo Wireshark, junto con el motor de diagnóstico autónomo **AI Packet Doctor** y un instalador standalone nativo para Windows (`NetworkingAgent-v2.2.0-Setup.exe`) completamente autosuficiente y con identidad de marca PE oficial.

---

## 🔬 Módulo 6: Packet Lab (Wireshark en Terminal)

### 1. Interfaz de 3 Paneles Sincronizados
Inspirado en la ergonomía de Wireshark y TShark, Packet Lab proporciona:
- **Panel Superior (Lista de Paquetes):** `DataTable` reactivo con visualización en tiempo real de índice, marca de tiempo relativa, IPs/MACs de origen y destino, protocolo con insignias coloreadas de alto contraste, tamaño en bytes y resumen analítico contextual.
- **Panel Central (Árbol de Disección de Protocolos):** Widget `Tree` jerárquico expandible con desglose campo a campo de cada capa de red (Enlace, Red, Transporte y Aplicación).
- **Panel Inferior (Hex Dump Dual Hex/ASCII):** Volcado de 16 columnas que resalta automáticamente en color cian brillante la región exacta de bytes seleccionada en el árbol de protocolos.

### 2. Motor de Disección Multi-Protocolo a Nivel de Cable
Decodificación pura y sin dependencias nativas para:
- **Capa 2:** Ethernet II, 802.1Q VLAN Tagging, ARP (Request y Reply).
- **Capa 3:** IPv4, IPv6, ICMP (Echo Request/Reply, Destination Unreachable con códigos de MTU, Time Exceeded).
- **Capa 4:** TCP (decodificación completa de banderas SYN, ACK, RST, FIN, PSH, URG, número de secuencia, acuse, longitud de payload y tamaño de ventana) y UDP.
- **Capa 7:** DNS (decodificación de nombres de dominio por etiquetas y códigos RCODE), DHCP/BOOTP, BGP v4 (Keepalive, Update, Notification) y OSPF v2 (Hello, Database Description).

### 3. AI Packet Doctor: Diagnóstico Forense y Detección de Anomalías
Al pulsar el botón **AI Packet Doctor** (`a`), el motor estadístico evalúa la captura y emite un informe estructurado en Markdown que detecta:
- **Retransmisiones TCP:** Tráfico duplicado por pérdida de paquetes o congestión intermedia.
- **Caída de Ventana a Cero (Zero-Window):** Saturación de buffer del receptor que paraliza la sesión.
- **Picos de Reseteos (RST Spikes):** Cierres abruptos forzados por firewalls o puertos inaccesibles.
- **Agujeros Negros de Path MTU:** Caídas por paquetes no fragmentables detectadas vía ICMP tipo 3 código 4.
- **Fallos de Resolución DNS:** Detección de errores `NXDOMAIN` y `SERVFAIL`.

### 4. Soporte Libpcap (.pcap) Nativo
- Lector `PcapReader` y escritor `PcapWriter` implementados en Python puro, compatibles con microsegundos y nanosegundos.
- Compatibilidad 100% bidireccional con Wireshark, tcpdump y Zeek.
- Exportación rápida (`s`) e importación directa (`o`) desde la terminal.

### 5. Captura Local y Generador Remoto para Routers
- Captura local asíncrona mediante Scapy `AsyncSniffer` con filtros BPF.
- Generador de secuencias de captura de tráfico en routers para Cisco IOS (EPC), Juniper Junos (`monitor traffic`) y MikroTik RouterOS (`/tool sniffer`).

---

## 📦 Instalador Standalone Oficial para Windows (.exe)

- **Instalador Único y Profesional:** Generación de `NetworkingAgent-v2.2.0-Setup.exe` que incluye el binario ejecutable (`networking-agent.exe`), recursos visuales y documentación completa.
- **Iconos PE de Alta Fidelidad en 10 Resoluciones:**
  - Icono del Instalador (flecha de descarga sobre red) embebido en las cabeceras PE del setup.
  - Icono de la Aplicación (nodo 'N' de red) embebido en `networking-agent.exe`, accesos directos del Escritorio y Menú Inicio.
- **Integración Nativa en Windows:**
  - Creación automática de accesos directos con iconos oficiales.
  - Registro formal en "Aplicaciones Instaladas de Windows" (Configuración y Panel de Control) con tamaño estimado y desinstalador limpio en PowerShell.
  - Variable de entorno `PATH` configurada automáticamente.

---

## 📊 Métricas de Calidad

- **Suite de Pruebas Automatizadas:** **209 pruebas** (`pytest tests/`) con 100% de éxito.
- **Linter y Formato:** 0 errores con `ruff check .`
- **Compatibilidad de Plataformas:** Windows 10/11 x64, Linux x64 (Ubuntu, Debian, RHEL, Arch), macOS (Apple Silicon e Intel).
