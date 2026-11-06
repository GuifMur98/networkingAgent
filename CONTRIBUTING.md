# 🤝 Guía de Contribución y Desarrollo: NetworkingAgent

¡Gracias por tu interés en contribuir a **NetworkingAgent**! Para mantener la máxima calidad, seguridad y estabilidad requerida en entornos de telecomunicaciones y redes críticas, seguimos un proceso de desarrollo y control de versiones estandarizado.

---

## 🌳 Estrategia de Ramas (*Branching Model*)

Seguimos una versión moderna y simplificada del modelo **Git Flow / Trunk-based Enterprise**:

```
main (Producción / Releases estables)
  ▲
  │ Pull Request (con revisión de código y CI pasando)
  │
develop (Integración y desarrollo activo)
  ▲
  ├── feature/soporte-arista-eos
  ├── feature/soporte-restconf
  └── fix/reprompt-validacion
```

### Reglas de Ramas:
1. **`main` (Protegida):** Contiene el código de producción estable. Cada merge en `main` representa un release versionado (e.g. `v0.1.0`). No se permite hacer push directo a `main`.
2. **`develop` (Integración):** Rama base para desarrollo continuo. Todas las nuevas funcionalidades e integraciones convergen aquí.
3. **`feature/<nombre-descriptivo>`:** Se desprenden de `develop` para desarrollar nuevas capacidades (ej. `feature/driver-fortinet`, `feature/telemetry-kafka`).
4. **`fix/<nombre-descriptivo>`:** Se desprenden de `develop` para correcciones de bugs.
5. **`hotfix/<nombre-descriptivo>`:** Se desprenden de `main` exclusivamente para solucionar incidentes críticos en producción.

---

## 🛠️ Configuración del Entorno de Desarrollo

Requerimientos:
- Python `>= 3.12`
- [`uv`](https://github.com/astral-sh/uv)

```bash
# 1. Clonar el repositorio
git clone https://github.com/GuifMur98/networkingAgent.git
cd networkingAgent

# 2. Cambiar a la rama develop
git checkout develop

# 3. Crear tu rama de trabajo
git checkout -b feature/mi-nueva-mejora

# 4. Sincronizar dependencias completas de desarrollo
uv sync --extra dev
```

---

## 🔌 Cómo Añadir un Nuevo Driver de Fabricante

Para soportar un nuevo fabricante (ej. Arista EOS, Huawei VRP):

1. **Crear el Driver:** Crea `src/networking_agent/drivers/<vendor>.py` heredando de `NetworkOSDriver`.
2. **Implementar Métodos Requeridos:**
   - `get_health_commands()`: Lista de comandos de lectura para inspeccionar CPU, interfaces y errores.
   - `get_gateway_interfaces()`: Lista de interfaces críticas/WAN que deben blindarse.
   - `get_rollback_description()`: Descripción del mecanismo de reversión disponible.
   - `build_candidate_commands(intent)`: Mapeo de `NetworkIntent` a la sintaxis CLI nativa.
   - `rollback(backup_reference)`: Procedimiento de reversión del equipo.
3. **Registrar en Factory:** Registra la clase en `src/networking_agent/drivers/factory.py`.
4. **Añadir Pruebas Unitarias:** Escribe tests en `tests/test_drivers.py` comprobando la generación de comandos y rollback sin necesidad de hardware físico.

---

## 🧠 Cómo Añadir un Nuevo Cerebro de IA

1. Crea `src/networking_agent/brains/<provider>.py` heredando de `LLMBrain`.
2. Implementa `analyze_event(telemetry_data: str) -> NetworkIntent`.
3. Inyecta `HARDENED_SYSTEM_PROMPT` para garantizar el aislamiento de prompt injections.
4. Registra el proveedor en `src/networking_agent/brains/factory.py`.
5. Añade tests unitarios en `tests/test_brains.py`.

---

## ✅ Verificación y Calidad de Código Pre-Commit

Antes de abrir un Pull Request, debes certificar que los tests y el linter pasen localmente:

```bash
# Ejecutar la suite completa de 105 tests unitarios
uv run --no-sync pytest

# Verificar estilo y reglas de linter con ruff
uv run --no-sync ruff check .

# Formatear el código automáticamente
uv run --no-sync ruff format .
```

### Reglas Críticas:
- **Cero Secretos:** Nunca hagas commit de archivos `.env`, `.key`, o contraseñas reales.
- **Rutas Relativas:** No incluyas rutas absolutas de tu máquina local en la documentación o código.
- **Commits Semánticos:** Utiliza mensajes estructurados: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`.

---

## 🚀 Flujo para Enviar un Pull Request (PR)

1. Haz push de tu rama:
   ```bash
   git push origin feature/mi-nueva-mejora
   ```
2. Abre un **Pull Request** hacia la rama **`develop`** en GitHub.
3. Completa el checklist de la plantilla de PR.
4. Espera a que los checks de **GitHub Actions CI** pasen en verde.
