from joystick_diagrams.export_text_layout import TextLayoutOptions, fit_label


def test_unbroken_long_word_triggers_shrink_before_giving_up():
    options = TextLayoutOptions(
        enabled=True,
        wrap=True,
        max_chars=8,
        max_lines=2,
        font_size=12,
        shrink=True,
        min_font_size=7,
        ellipsis=False,
    )

    lines, font_size = fit_label(
        "Supercalifragilisticexpialidocious",
        options,
        template_font_size=12,
    )

    assert lines == ["Supercalifragilisticexpialidocious"]
    assert font_size == 7


def test_ellipsis_truncates_an_unbroken_word_at_minimum_font_size():
    options = TextLayoutOptions(
        enabled=True,
        wrap=True,
        max_chars=8,
        max_lines=1,
        font_size=12,
        shrink=True,
        min_font_size=7,
        ellipsis=True,
    )

    lines, font_size = fit_label(
        "Supercalifragilisticexpialidocious",
        options,
        template_font_size=12,
    )

    assert font_size == 7
    assert len(lines) == 1
    assert lines[0].endswith("…")
    assert len(lines[0]) <= round(8 * 12 / 7)


def test_x52_multi_action_label_is_preserved_without_ellipsis():
    label = (
        "Smoke Toggle | Spray Toggle | Toggle Afterburner | "
        "Firefighting Scoop Doors | Grapple Hook Toggle | Skydive Doorlights Dec"
    )
    options = TextLayoutOptions(
        enabled=True,
        wrap=True,
        max_chars=18,
        max_lines=3,
        font_size=0,
        shrink=True,
        min_font_size=7,
        ellipsis=False,
    )

    lines, font_size = fit_label(label, options, template_font_size=12)

    assert font_size == 7
    assert lines == [
        "Smoke Toggle | Spray Toggle",
        "Toggle Afterburner",
        "Firefighting Scoop Doors",
        "Grapple Hook Toggle",
        "Skydive Doorlights Dec",
    ]
    assert "Smoke Toggle" in " ".join(lines)
    assert "Skydive Doorlights Dec" in " ".join(lines)
