---
name: New Vendor / OS Driver Request
about: Propose adding support for a new network vendor or operating system
title: "[VENDOR]: Support for "
labels: ["vendor-support", "driver"]
assignees: ""
---

### 🖧 Vendor & OS Details
- **Vendor Name:** (e.g. Arista Networks, Fortinet, Huawei, Nokia)
- **Network OS:** (e.g. EOS, FortiOS, VRP, SR OS)
- **Target Hardware / Series:** (e.g. 7050X, FortiGate 100F)

### 🔍 Diagnostic Commands Required
List the read-only operational commands to inspect CPU, interfaces, and packet errors:
- CPU utilization: `...`
- Interface status: `...`
- Error/drop counters: `...`
- Routing summary: `...`

### 🛠️ Remediation Syntax
- Interface shutdown / no shutdown: `...`
- Duplex / MTU configuration: `...`
- BGP neighbor reset: `...`

### 🔄 Rollback Mechanism Available on Platform
- Does the OS support atomic commit? (e.g. `commit confirmed`, checkpoint, session rollback)
- Recommended rollback commands: `...`
