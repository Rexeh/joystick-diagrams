import json
import logging
from pathlib import Path

from joystick_diagrams.input.profile_collection import ProfileCollection
from joystick_diagrams.plugins.plugin_interface import PluginInterface

from .config import settings
from .il2_parser import IL2Parser

_logger = logging.getLogger(__name__)

CONFIG_FILE = "data.json"


class ParserPlugin(PluginInterface):
    def __init__(self):
        super().__init__()
        print("IL2 Plugin: Initializing...")
        self.settings = settings
        self.settings.validators.register()
        self.path = None
        self.instance: IL2Parser = None
        
        # Load any existing settings
        try:
            self.load_settings()
            if self.path:
                print(f"IL2 Plugin: Loaded existing path from settings: {self.path}")
                # Try to recreate the parser instance
                if self.path.exists():
                    self.instance = IL2Parser(self.path)
                    print("IL2 Plugin: Parser instance recreated from saved path")
                else:
                    print(f"IL2 Plugin: Saved path no longer exists: {self.path}")
                    self.path = None
        except Exception as e:
            print(f"IL2 Plugin: Error loading settings: {e}")
        
        print("IL2 Plugin: Initialization complete")

    def process(self) -> ProfileCollection:
        print(f"IL2 Plugin: process() called, instance available: {self.instance is not None}")
        _logger.info(f"IL2 Plugin: process() called, instance available: {self.instance is not None}")
        
        if self.instance:
            try:
                result = self.instance.process_profiles()
                print(f"IL2 Plugin: Successfully processed {len(result.profiles)} profiles")
                _logger.info(f"Successfully processed {len(result.profiles)} profiles")
                return result
            except Exception as e:
                print(f"IL2 Plugin ERROR in process(): {e}")
                _logger.error(f"Error in process(): {e}")
                import traceback
                traceback.print_exc()
        else:
            print("IL2 Plugin: No instance available for processing")
            _logger.warning("No instance available for processing")
            
        return ProfileCollection()

    def set_path(self, path: Path) -> bool:
        try:
            print(f"IL2 Plugin: Attempting to set input directory: {path}")
            _logger.info(f"IL2 Plugin: Attempting to set input directory: {path}")
            
            # Validate that the path points to a directory
            if not path.exists():
                error_msg = f"Directory {path} does not exist"
                print(f"IL2 Plugin ERROR: {error_msg}")
                _logger.error(error_msg)
                raise FileNotFoundError(error_msg)
                
            if not path.is_dir():
                error_msg = f"Path {path} is not a directory"
                print(f"IL2 Plugin ERROR: {error_msg}")
                _logger.error(error_msg)
                raise ValueError(error_msg)

            # Check for required files
            global_actions_file = path / "global.actions"
            devices_file = path / "devices.txt"
            
            if not global_actions_file.exists():
                error_msg = f"global.actions not found in {path}"
                print(f"IL2 Plugin ERROR: {error_msg}")
                _logger.error(error_msg)
                raise FileNotFoundError(error_msg)
                
            if not devices_file.exists():
                error_msg = f"devices.txt not found in {path}"
                print(f"IL2 Plugin ERROR: {error_msg}")
                _logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            print(f"IL2 Plugin: Directory validation passed, creating IL2Parser for: {path}")
            _logger.info(f"Directory validation passed, creating IL2Parser for: {path}")
            
            self.instance = IL2Parser(path)
            
            # Test if parser can read the files
            try:
                print("IL2 Plugin: Testing parser...")
                test_collection = self.instance.process_profiles()
                success_msg = f"Parser test successful, found {len(test_collection.profiles)} profiles"
                print(f"IL2 Plugin: {success_msg}")
                _logger.info(success_msg)
            except Exception as parser_error:
                error_msg = f"Parser failed to process files: {parser_error}"
                print(f"IL2 Plugin ERROR: {error_msg}")
                _logger.error(error_msg)
                raise parser_error
            
            self.path = path
            self.save_plugin_state()
            print("IL2 Plugin: Setup completed successfully")
            _logger.info("Plugin setup completed successfully")
            return True

        except Exception as e:
            error_msg = f"Failed to set path {path}: {e}"
            print(f"IL2 Plugin ERROR: {error_msg}")
            _logger.error(error_msg)
            import traceback
            print("IL2 Plugin: Full traceback:")
            traceback.print_exc()
            return False

    def save_plugin_state(self):
        with open(
            Path.joinpath(self.get_plugin_data_path(), CONFIG_FILE),
            "w",
            encoding="UTF8",
        ) as f:
            f.write(json.dumps({"path": str(self.path)}))

    def load_settings(self) -> None:
        try:
            with open(
                Path.joinpath(self.get_plugin_data_path(), CONFIG_FILE),
                "r",
                encoding="UTF8",
            ) as f:
                data = json.loads(f.read())
                self.path = Path(data["path"]) if data["path"] else None
        except FileNotFoundError:
            pass

    @property
    def path_type(self):
        return self.FolderPath(
            "Select your IL-2 Sturmovik input directory (containing global.actions and devices.txt)",
            Path(r"C:\Program Files\IL-2 Sturmovik Great Battles\data\input"),
        )

    @property
    def icon(self):
        return f"{Path.joinpath(Path(__file__).parent, self.settings.PLUGIN_ICON)}"
    
    def export_mappings(self, export_path: Path = None) -> bool:
        """Export IL-2 mappings to a CSV file
        
        Args:
            export_path: Optional path for the export file. If None, uses current directory
            
        Returns:
            bool: True if export successful, False otherwise
        """
        if not self.instance:
            _logger.error("No IL-2 parser instance available for export")
            return False
        
        try:
            # Default export path if none provided
            if export_path is None:
                if self.path:
                    export_path = self.path / "export.csv"
                else:
                    export_path = Path.cwd() / "export.csv"
            
            # Ensure the export path has the correct filename
            if export_path.is_dir():
                export_path = export_path / "export.csv"
            elif not export_path.name.endswith('.csv'):
                export_path = export_path.with_suffix('.csv')
            
            # Call the parser's export method
            success = self.instance.export_mapping_to_file(export_path)
            
            if success:
                _logger.info(f"IL-2 mappings exported successfully to: {export_path}")
                print(f"IL-2 mappings exported to: {export_path}")
            else:
                _logger.error("Failed to export IL-2 mappings")
                print("Failed to export IL-2 mappings")
            
            return success
            
        except Exception as e:
            _logger.error(f"Error during IL-2 mapping export: {e}")
            print(f"Error during export: {e}")
            return False


if __name__ == "__main__":
    plugin = ParserPlugin()
