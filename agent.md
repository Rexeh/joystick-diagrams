# Joystick Diagrams - Analyse & Kontext

## Projektübersicht

| Feld | Wert |
|------|------|
| Name | Joystick Diagrams |
| Autor | Robert Cox (GitHub: Rexeh) |
| Version | 2.1.0 |
| Sprache | Python 3.11-3.12 |
| GUI | PySide6 (Qt 6) |
| Lizenz | Open Source |
| Homepage | https://www.joystick-diagrams.com |
| Repository | https://github.com/Rexeh/joystick-diagrams |
| Community | Discord |

## Was macht das Projekt?

Joystick Diagrams erstellt automatisch visuelle SVG-Diagramme für Controller-Belegungen. Statt textbasierter Binding-Listen generiert es druckbare Diagramme mit allen Tastenbelegungen.

**Zielgruppe:** Flugsimulator-Enthusiasten, Racing-Sim-Nutzer, Streamer, Tutorial-Ersteller, alle mit komplexen Controller-Konfigurationen.

## Unterstützte Spiele (Plugins)

- **DCS World** (`dcs_world_plugin/`) - Lua Config Parser
- **Microsoft Flight Simulator 2020** (`fs2020_plugin/`)
- **Star Citizen** (`star_citizen_plugin/`)
- **Joystick Gremlin** (`joystick_gremlin_plugin/`) - XML Parser
- **IL-2 Sturmovik** (`il2_sturmovik_plugin/`)
- Erweiterbar durch Custom Plugins

## Tech-Stack

- **PySide6** - Qt 6 GUI Framework
- **qt-material** - Material Design Theming
- **PLY** - Lexer/Parser (Config-Dateien)
- **dynaconf** - Konfigurationsmanagement + Validierung
- **qtawesome** - Font Awesome Icons
- **requests** - HTTP (Update-Checks)
- **semver** - Versionierung
- **Poetry** - Dependency Management
- **cx_Freeze** - Windows EXE Build
- **Inno Setup** - Windows Installer

## Projektstruktur

```
joystick-diagrams-clauc/
├── joystick_diagrams/            # Haupt-Python-Paket
│   ├── __main__.py               # Entry Point (Logging + app_init)
│   ├── app_init.py               # Bootstrapping (DB, Plugins, UI)
│   ├── app_state.py              # Singleton - globaler App-Zustand
│   ├── export.py                 # SVG-Template Population + Export
│   ├── export_device.py          # Export-Datenmodell
│   ├── template.py               # Template-Parsing (Regex)
│   ├── plugin_wrapper.py         # Plugin-Wrapper
│   ├── profile_wrapper.py        # Profile-Wrapper
│   ├── utils.py                  # Hilfsfunktionen
│   ├── config.py                 # App-Konfiguration
│   ├── exceptions.py             # Custom Exceptions
│   ├── version.py                # Versionsverwaltung
│   │
│   ├── db/                       # SQLite Persistenz
│   │   ├── db_handler.py         # DB-Initialisierung
│   │   ├── db_connection.py      # Verbindungsmanagement
│   │   ├── db_device_management.py
│   │   ├── db_plugin_data.py
│   │   ├── db_profiles.py
│   │   └── db_settings.py
│   │
│   ├── input/                    # Domain Models
│   │   ├── device.py             # Device_ (Buttons, Achsen, Hats)
│   │   ├── profile.py            # Profile_
│   │   ├── profile_collection.py # ProfileCollection
│   │   ├── input.py              # Input_ Basisklasse
│   │   ├── button.py             # Button
│   │   ├── axis.py               # Achse/Slider
│   │   ├── hat.py                # POV Hat
│   │   └── modifier.py           # Modifier-Kombinationen
│   │
│   ├── plugins/                  # Plugin-System
│   │   ├── plugin_interface.py   # ABC - PluginInterface
│   │   ├── plugin_manager.py     # Discovery, Loading, Validierung
│   │   ├── dcs_world_plugin/
│   │   ├── fs2020_plugin/
│   │   ├── joystick_gremlin_plugin/
│   │   ├── star_citizen_plugin/
│   │   ├── il2_sturmovik_plugin/
│   │   └── Example/
│   │
│   └── ui/                       # PySide6 GUI
│       ├── main_window.py
│       ├── configure_page.py
│       ├── device_setup.py
│       ├── export_page.py
│       └── plugins_page.py
│
├── templates/                    # SVG Diagramm-Vorlagen (48 Dateien)
├── tests/                        # pytest Suite
├── docs/                         # Dokumentation
├── installer/                    # Inno Setup
├── img/                          # Logo/Icons
├── theme/                        # UI-Theme
├── pyproject.toml                # Projekt-Config
├── poetry.lock                   # Dependency Lock
├── setup.py                      # cx_Freeze Build
└── makefile                      # Build-Automation
```

## Architektur

### Design Patterns
- **Singleton:** `AppState` - globaler Zustand (Profile, Plugins)
- **Plugin-Architektur:** `PluginInterface` ABC mit Discovery via `plugin_manager.py`
- **Wrapper Pattern:** `PluginWrapper`, `ProfileWrapper`
- **Repository Pattern:** `db_*` Module
- **MVC:** Model (input/), View (ui/), Controller (Wrappers)

### Datenfluss
```
Game Config Files
    ↓ (Plugin Parser)
ProfileCollection
    ↓
AppState (indiziert Profile)
    ↓
ProfileWrapper (UI-Adapter)
    ↓
UI Pages (Configure, Export)
    ↓
Template Population (export.py)
    ↓
SVG Export
```

## SVG Template Format (KRITISCH)

Templates sind **draw.io-generierte SVGs** mit dem mxGraphModel-Format.

### Placeholder-Konventionen

| Typ | Format | Beispiele |
|-----|--------|-----------|
| Buttons | `BUTTON_X` | BUTTON_1, BUTTON_2, BUTTON_127 |
| Achsen | `AXIS_NAME` | AXIS_X, AXIS_Y, AXIS_RX, AXIS_RZ |
| Slider | `AXIS_SLIDER_X` | AXIS_SLIDER_1, AXIS_SLIDER_2 |
| Hat/POV | `POV_X_DIR` | POV_1_U, POV_1_D, POV_1_L, POV_1_R |
| Hat Diag. | `POV_X_DIR` | POV_1_UR, POV_1_UL, POV_1_DR, POV_1_DL |
| Modifier All | `INPUT_Modifiers` | BUTTON_1_MODIFIERS |
| Modifier Key | `INPUT_Modifier_X_Key` | BUTTON_1_MODIFIER_1_KEY |
| Modifier Action | `INPUT_Modifier_X_Action` | BUTTON_1_MODIFIER_1_ACTION |
| Name | `TEMPLATE_NAME` | (einmal pro Template) |
| Datum | `CURRENT_DATE` | (einmal pro Template) |

### SVG mxCell Struktur

Jeder Placeholder ist ein `mxCell`-Element im `content`-Attribut des SVG:

```xml
<mxCell id="..." value="BUTTON_1"
    style="rounded=1;whiteSpace=wrap;html=1;strokeColor=#6c8ebf;strokeWidth=2;align=left;fillColor=#dae8fc;"
    parent="1" vertex="1">
    <mxGeometry x="420" y="70" width="150" height="40" as="geometry" />
</mxCell>
```

Der Placeholder-Text erscheint sowohl im `content`-Attribut (mxGraphModel) als auch im gerenderten SVG-Body (foreignObject/text-Elemente).

### Regex-Patterns (template.py)

```python
BUTTON_KEY = re.compile(r"\bBUTTON_\d+\b", re.IGNORECASE)
HAT_KEY = re.compile(r"\bPOV_\d+_[URDL]+\b", re.IGNORECASE)
AXIS_KEY = re.compile(r"\bAXIS_[a-zA-Z]+_?\d?+\b", re.IGNORECASE)
```

## Plugin-Interface Vertrag

### Pflichtdateien pro Plugin
```
plugin_verzeichnis/
├── __init__.py      # Leer (Package-Marker)
├── main.py          # ParserPlugin(PluginInterface) Klasse
├── config.py        # Dynaconf Settings
└── settings.json    # Plugin-Metadaten
```

### settings.json Pflichtfelder
```json
{
    "PLUGIN_NAME": "Plugin Name",
    "PLUGIN_ICON": "./img/icon.ico",
    "VERSION": "1.0.0"
}
```

### config.py Template
```python
from pathlib import Path
from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    settings_files=[f"{Path(__file__).parent.joinpath('settings.json')}"],
)
settings.validators.register(
    Validator("PLUGIN_NAME", required=True),
    Validator("PLUGIN_ICON", required=True),
    Validator("VERSION", required=True),
)
```

### main.py - Abstrakte Methoden

```python
class ParserPlugin(PluginInterface):
    def __init__(self):
        self.settings = settings
        self.settings.validators.register()
        self.path = None

    def process(self) -> ProfileCollection:
        """Verarbeite Input und gebe ProfileCollection zurueck"""

    def set_path(self, path: Path) -> bool:
        """Setze und validiere den Pfad, return True bei Erfolg"""

    def load_settings(self) -> None:
        """Lade persistierte Plugin-Einstellungen"""

    @property
    def path_type(self) -> FolderPath | FilePath:
        """Definiere Input-Methode (Ordner oder Datei)"""

    @property
    def icon(self) -> str:
        """Pfad zum Plugin-Icon"""
```

## Dev-Tooling

- **Lint:** `ruff` (rules: A, E, C90, I, W, F, B, Q, N, PL)
- **Format:** `ruff format` (double quotes)
- **Type Check:** `mypy` (relaxed: no untyped defs required)
- **Test:** `pytest` + `pytest-qt` (marker: `uitest`)
- **Coverage:** 40% minimum, excludes: config.py, plugins/*, ui/*, db*
- **Pre-commit:** trailing whitespace, end-of-file, YAML, ruff
- **CI:** GitHub Actions (Ubuntu, Python 3.11, Xvfb)
- **Build:** cx_Freeze + Inno Setup (Windows)
- **Make Targets:** `test`, `unit-test`, `fmt`, `lint`, `build-exe`
