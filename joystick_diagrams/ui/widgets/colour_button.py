"""``ColourButton``: a swatch button with a palette menu and "More colours…".

The default palette is the Okabe-Ito colour-blind-safe set used for modifier
key groups. The button shows the current colour as its swatch icon with the
colour's *name* as text ("Blue"); a colour outside the palette shows its hex
value. The accessible name and tooltip carry the name plus the hex value, so
the exact value is always available without cluttering the row (plan §5.5.4).
"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QColorDialog, QMenu, QPushButton, QWidget

from joystick_diagrams.ui import strings_appearance as S

OKABE_ITO_SWATCHES: tuple[str, ...] = (
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#56B4E9",
    "#F0E442",
    "#000000",
)


def swatch_icon(colour: str | None, size: int = 16) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor("#3C4043"))
    if colour:
        painter.setBrush(QColor(colour))
    else:
        painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
    if not colour:
        painter.drawLine(3, size - 3, size - 3, 3)
    painter.end()
    return QIcon(pixmap)


def colour_name(colour: str | None) -> str:
    if not colour:
        return S.COLOUR_TEMPLATE
    return S.SWATCH_NAMES.get(colour.upper(), colour.upper())


class ColourButton(QPushButton):
    colour_changed = Signal(
        object
    )  # str hex, or None when "Template colour" is allowed

    def __init__(
        self,
        colour: str | None = None,
        swatches: tuple[str, ...] = OKABE_ITO_SWATCHES,
        allow_none: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._colour: str | None = None
        self._swatches = swatches
        self._allow_none = allow_none
        self.setIconSize(QSize(16, 16))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("class", "plugin-setup-button")
        self.clicked.connect(self._show_menu)
        self.set_colour(colour)

    def colour(self) -> str | None:
        return self._colour

    def set_colour(self, colour: str | None, emit: bool = False) -> None:
        self._colour = colour.upper() if colour else None
        self.setIcon(swatch_icon(self._colour))
        name = colour_name(self._colour)
        self.setText(name)
        self.setAccessibleName(
            f"{name} {self._colour}" if self._colour and name != self._colour else name
        )
        self.setToolTip(self.accessibleName())
        if emit:
            self.colour_changed.emit(self._colour)

    def _show_menu(self) -> None:
        menu = QMenu(self)
        for swatch in self._swatches:
            action = menu.addAction(swatch_icon(swatch), colour_name(swatch))
            action.triggered.connect(lambda _=False, c=swatch: self.set_colour(c, True))
        menu.addSeparator()
        more = menu.addAction(S.MORE_COLOURS)
        more.triggered.connect(self._pick_more)
        if self._allow_none:
            template = menu.addAction(swatch_icon(None), S.COLOUR_TEMPLATE)
            template.triggered.connect(lambda: self.set_colour(None, True))
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def _pick_more(self) -> None:
        initial = QColor(self._colour) if self._colour else QColor("#0072B2")
        picked = QColorDialog.getColor(initial, self, S.MORE_COLOURS)
        if picked.isValid():
            self.set_colour(picked.name().upper(), True)
