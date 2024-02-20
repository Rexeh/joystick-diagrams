from joystick_diagrams import app_state

# Run each plugin
# Get the profiles from all the executed plugins
# Find/Restore and Merge any Profile Configurations
# Find/Restore any XYZ i.e. Layer in NAME edits / Profile Name Changes


def run_parser_plugins():
    """Run the parser plugins available"""
    _state = app_state.AppState()

    for wrapper in _state.plugin_manager.plugin_wrappers:
        if wrapper.ready:
            wrapper.process()
