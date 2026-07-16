"""Unit tests for conflict_strategy setting getters and defaults."""

from unittest.mock import patch

from joystick_diagrams.conflict_strategy import (
    ALIAS_CONFLICT_STRATEGY_KEY,
    DEFAULT_ALIAS_STRATEGY,
    DEFAULT_INHERITANCE_STRATEGY,
    INHERITANCE_CONFLICT_STRATEGY_KEY,
    AliasConflictStrategy,
    InheritanceConflictStrategy,
    get_alias_strategy,
    get_inheritance_strategy,
)


class TestAliasStrategyGetter:
    def test_unset_returns_default(self):
        with patch(
            "joystick_diagrams.db.db_settings.get_setting", return_value=None
        ) as mock_get:
            assert get_alias_strategy() == DEFAULT_ALIAS_STRATEGY
            mock_get.assert_called_once_with(ALIAS_CONFLICT_STRATEGY_KEY)

    def test_valid_value_returns_parsed_enum(self):
        with patch(
            "joystick_diagrams.db.db_settings.get_setting", return_value="MODIFIER"
        ):
            assert get_alias_strategy() == AliasConflictStrategy.MODIFIER
        with patch(
            "joystick_diagrams.db.db_settings.get_setting",
            return_value="CONCATENATE",
        ):
            assert get_alias_strategy() == AliasConflictStrategy.CONCATENATE

    def test_invalid_value_falls_back_to_default(self):
        with patch(
            "joystick_diagrams.db.db_settings.get_setting",
            return_value="NONSENSE",
        ):
            assert get_alias_strategy() == DEFAULT_ALIAS_STRATEGY


class TestInheritanceStrategyGetter:
    def test_unset_returns_default(self):
        with patch(
            "joystick_diagrams.db.db_settings.get_setting", return_value=None
        ) as mock_get:
            assert get_inheritance_strategy() == DEFAULT_INHERITANCE_STRATEGY
            mock_get.assert_called_once_with(INHERITANCE_CONFLICT_STRATEGY_KEY)

    def test_valid_value_returns_parsed_enum(self):
        for value, expected in [
            ("KEEP_EXISTING", InheritanceConflictStrategy.KEEP_EXISTING),
            ("MODIFIER", InheritanceConflictStrategy.MODIFIER),
            ("CONCATENATE", InheritanceConflictStrategy.CONCATENATE),
        ]:
            with patch(
                "joystick_diagrams.db.db_settings.get_setting", return_value=value
            ):
                assert get_inheritance_strategy() == expected

    def test_invalid_value_falls_back_to_default(self):
        with patch(
            "joystick_diagrams.db.db_settings.get_setting",
            return_value="GARBAGE",
        ):
            assert get_inheritance_strategy() == DEFAULT_INHERITANCE_STRATEGY


class TestDefaults:
    def test_alias_default_is_concatenate(self):
        assert DEFAULT_ALIAS_STRATEGY == AliasConflictStrategy.CONCATENATE

    def test_inheritance_default_is_keep_existing(self):
        assert DEFAULT_INHERITANCE_STRATEGY == InheritanceConflictStrategy.KEEP_EXISTING
