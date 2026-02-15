"""AI prompt templates for controller image analysis."""

SYSTEM_PROMPT = """You are an expert at analyzing images of gaming controllers, joysticks,
throttles, pedals, and other HID devices. Your task is to identify all interactive controls
(buttons, axes, hat switches, sliders) visible in the image and provide their approximate
positions.

You must return a valid JSON object and nothing else."""

ANALYSIS_PROMPT = """Analyze this image of a gaming controller or joystick device.

Identify ALL visible interactive controls and classify them:

1. **Buttons** - Push buttons, triggers, toggles, switches
2. **Axes** - Joystick axes (X/Y movement), rotation axes (twist/rudder), throttle levers
3. **Hat switches** - POV hats (4-way or 8-way directional switches, usually small round or cross-shaped)
4. **Sliders** - Linear slider controls, throttle sliders

For each control, provide:
- `type`: one of "button", "axis", "hat", "slider"
- `id`: sequential number starting from 1 within each type
- `label`: descriptive name (e.g. "Trigger", "Thumb Button", "POV Hat 1", "Throttle Axis")
- `x`: horizontal position as fraction 0.0-1.0 (left to right)
- `y`: vertical position as fraction 0.0-1.0 (top to bottom)

For hat switches, provide the center position only (directions will be auto-generated).

Also identify:
- `device_name`: the name/model of the device if recognizable, otherwise a descriptive name
- `device_type`: one of "joystick", "throttle", "pedals", "button_box", "gamepad", "other"

Return ONLY valid JSON in this exact format:
```json
{
    "device_name": "Device Name",
    "device_type": "joystick",
    "controls": [
        {"type": "button", "id": 1, "label": "Trigger", "x": 0.5, "y": 0.8},
        {"type": "axis", "id": 1, "label": "X Axis", "x": 0.5, "y": 0.5},
        {"type": "hat", "id": 1, "label": "POV Hat 1", "x": 0.3, "y": 0.2},
        {"type": "slider", "id": 1, "label": "Throttle", "x": 0.1, "y": 0.5}
    ]
}
```

Be thorough - identify every visible control. If the image is a diagram or schematic,
use the labeled positions. If it's a photo, estimate positions based on visible controls."""
