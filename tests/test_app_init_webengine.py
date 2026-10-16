from pathlib import Path

APP_INIT_PATH = Path(__file__).parents[1] / "joystick_diagrams" / "app_init.py"


def _app_init_source() -> str:
    return APP_INIT_PATH.read_text(encoding="utf-8")


def test_webengine_warmup_happens_before_main_window_is_shown():
    source = _app_init_source()

    warmup_call = source.index("_warm_up_webengine(app)")
    show_call = source.index("window.show()")

    assert warmup_call < show_call


def test_stylesheet_is_applied_before_main_window_is_shown():
    source = _app_init_source()

    stylesheet_call = source.index("apply_stylesheet(")
    show_call = source.index("window.show()")

    assert stylesheet_call < show_call


def test_webengine_warmup_is_kept_alive_for_the_application_session():
    source = _app_init_source()

    assert "app._webengine_warmup = warmup" in source
    assert 'warmup.load(QUrl("about:blank"))' in source
