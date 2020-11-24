from __future__ import annotations

import os
from pathlib import Path

import typing
from dataclasses import dataclass, field
from io import BytesIO

from lxml import etree

import pygame
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QScrollArea, QSplitter

from classes.templater import Templater
from functions.helper import log


@dataclass
class DeviceState:
    deviceId: str
    deviceName: str
    guid: typing.Optional[str] = None
    buttons: dict[str, bool] = field(default_factory=dict)
    axes: dict[str, float] = field(default_factory=dict)
    hats: dict[str, tuple[float, float]] = field(default_factory=dict)


@dataclass
class TreeItem:
    _item_data: list[QtCore.QVariant]
    _parent_item: TreeItem
    _child_items: list[TreeItem]

    def __init__(self, item_data: list[QtCore.QVariant], parent_item: TreeItem = None):
        self._item_data = item_data
        self._parent_item = parent_item
        self._child_items = []

    def __del__(self):
        self._child_items.clear()

    def append_child(self, child: TreeItem):
        self._child_items.append(child)

    def child(self, row: int) -> typing.Optional[TreeItem]:
        if row < 0 or row >= len(self._child_items):
            return None
        return self._child_items[row]

    def child_count(self) -> int:
        return len(self._child_items)

    def column_count(self) -> int:
        return len(self._item_data)

    def data(self, column: int) -> QtCore.QVariant:
        if column < 0 or column >= len(self._item_data):
            return QtCore.QVariant()
        return self._item_data[column]

    def row(self) -> int:
        if self._parent_item:
            return self._parent_item._child_items.index(self)
        return 0

    def parent_item(self) -> TreeItem:
        return self._parent_item


class TreeModel(QtCore.QAbstractItemModel):
    _root_item: typing.Optional[TreeItem]

    def __del__(self):
        self._root_item = None

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self._root_item = TreeItem([QtCore.QVariant("Title"), QtCore.QVariant("Summary")])

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = ...) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        parent_item: TreeItem

        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()

        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        return QtCore.QModelIndex()

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()

        child_item: TreeItem = index.internalPointer()
        parent_item = child_item.parent_item()

        if not parent_item:
            # TODO: is this a valid case? for the root item yes
            return QtCore.QModelIndex()

        if parent_item == self._root_item:
            return QtCore.QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        parent_item: TreeItem
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item: TreeItem = parent.internalPointer()

        return parent_item.child_count()

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.isValid():
            parent_item: TreeItem = parent.internalPointer()
            return parent_item.column_count()
        return self._root_item.column_count()

    def data(self, index: QtCore.QModelIndex, role: int = -1) -> QtCore.QVariant:
        if not index.isValid():
            return QtCore.QVariant()

        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()

        item: TreeItem = index.internalPointer()

        return item.data(index.column())

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return QtCore.Qt.ItemFlags(QtCore.Qt.NoItemFlags)

        return super().flags(index)

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = -1) -> QtCore.QVariant:
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._root_item.data(section)

        return QtCore.QVariant()


class DeviceModel(TreeModel):
    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)

    def signal_state(self, deviceState: DeviceState):
        existing_item: typing.Optional[TreeItem] = None
        root_item = self._root_item
        for i in range(root_item.child_count()):
            existing_item = root_item.child(i)
        if not existing_item:
            self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount())
            device_item = TreeItem(
                [QtCore.QVariant(deviceState.deviceId), QtCore.QVariant(deviceState.deviceName)],
                root_item
            )
            self._produce_device_items(device_item, deviceState)
            root_item.append_child(device_item)
            self.endInsertRows()
        else:
            self._update_device_items(existing_item, deviceState)

    @staticmethod
    def _produce_device_items(device_item: TreeItem, deviceState: DeviceState):
        device_item.append_child(
            TreeItem([QtCore.QVariant("Joystick name"), QtCore.QVariant(deviceState.deviceName)], device_item),
        )
        device_item.append_child(
            TreeItem([QtCore.QVariant("GUID"), QtCore.QVariant(deviceState.guid)], device_item)
        )
        axes_item = TreeItem([QtCore.QVariant("Number of axes"), QtCore.QVariant(len(deviceState.axes))], device_item)
        for key, value in deviceState.axes.items():
            axes_item.append_child(TreeItem([QtCore.QVariant(key), QtCore.QVariant(value)], axes_item))
        device_item.append_child(axes_item)

        button_item = TreeItem([QtCore.QVariant("Number of buttons"), QtCore.QVariant(len(deviceState.buttons))],
                               device_item)
        for key, value in deviceState.buttons.items():
            button_item.append_child(TreeItem([QtCore.QVariant(key), QtCore.QVariant(value)], button_item))
        device_item.append_child(button_item)
        hats_item = TreeItem([QtCore.QVariant("Number of hats"), QtCore.QVariant(len(deviceState.hats))], device_item)
        for key, value in deviceState.hats.items():
            hats_item.append_child(TreeItem([QtCore.QVariant(key), QtCore.QVariant(value)], hats_item))
        device_item.append_child(hats_item)

    @staticmethod
    def _update_device_items(device_item: TreeItem, deviceState: DeviceState):
        axes_item = device_item.child(2)
        for index, key in enumerate(deviceState.axes):
            data = axes_item.child(index).data(1)
            data.swap(QtCore.QVariant(deviceState.axes[key]))

        button_item = device_item.child(3)
        for index, key in enumerate(deviceState.buttons):
            data = button_item.child(index).data(1)
            data.swap(QtCore.QVariant(deviceState.buttons[key]))

        hats_item = device_item.child(4)
        for index, key in enumerate(deviceState.hats):
            data = hats_item.child(index).data(1)
            data.swap(QtCore.QVariant(deviceState.hats[key]))


@dataclass
class RenderThread(QtCore.QThread):
    _deviceState: dict[str, DeviceState]
    _refresher: lambda: None

    def __init__(self, deviceState: dict[str, DeviceState], refresher: lambda: None):
        QtCore.QThread.__init__(self)
        self._deviceState = deviceState
        self._refresher = refresher

        pygame.joystick.init()

    def run(self):
        clock = pygame.time.Clock()
        while not self.isInterruptionRequested():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # TODO: do something with these events
                    # log("Quit pressed")
                    pass
                elif event.type == pygame.JOYBUTTONDOWN:
                    # TODO: do something with these events
                    # log("Joystick button pressed.")
                    pass
                elif event.type == pygame.JOYBUTTONUP:
                    # TODO: do something with these events
                    # log("Joystick button released.")
                    pass

            joystick_count = pygame.joystick.get_count()

            for i in range(joystick_count):
                joystick = pygame.joystick.Joystick(i)
                joystick.init()

                try:
                    jid = joystick.get_instance_id()
                except AttributeError:
                    # get_instance_id() is an SDL2 method
                    jid = joystick.get_id()
                device_id = f"Joystick {jid}"

                # Get the name from the OS for the controller/joystick.
                name = joystick.get_name()

                if jid not in self._deviceState:
                    self._deviceState[device_id] = DeviceState(device_id, name)

                device_state = self._deviceState[device_id]

                try:
                    guid = joystick.get_guid()
                except AttributeError:
                    # get_guid() is an SDL2 method
                    pass
                else:
                    device_state.guid = guid

                # Usually axis run in pairs, up/down for one, and left/right for the other.
                axes = joystick.get_numaxes()

                for j in range(axes):
                    axis = joystick.get_axis(j)
                    device_state.axes[f"Axis_{j + 1}"] = axis

                buttons = joystick.get_numbuttons()

                for j in range(buttons):
                    button = joystick.get_button(j)
                    device_state.buttons[f"Button_{j + 1}"] = button

                hats = joystick.get_numhats()

                # Hat position. All or nothing for direction, not a float like get_axis(). Position is a tuple of int
                # values (x, y).
                for j in range(hats):
                    hat = joystick.get_hat(j)
                    device_state.hats[f"Hat_{j + 1}"] = hat

            #
            # ALL CODE TO DRAW SHOULD GO ABOVE THIS COMMENT
            #

            # Limit to 20 frames per second.
            clock.tick(20)
            log(f"render {clock}")
            self._refresher()


@dataclass
class DebugDisplayImageWidget(QtWidgets.QTreeView):
    deviceState: dict[str, DeviceState]
    refresher: lambda: None
    parent: typing.Optional['QtWidgets.QWidget'] = None
    renderThread: RenderThread = field(init=False)

    def __post_init__(self):
        super().__init__(self.parent)
        self.setMinimumSize(400, 700)
        self.setModel(DeviceModel())
        self.renderThread = RenderThread(self.deviceState, self.refresh)
        self.renderThread.start()
        self.expandAll()

    def refresh(self):
        model = typing.cast(DeviceModel, self.model())

        # TODO: is this the right thing todo? maybe better let the tread write directly to this?
        for _, device_state in self.deviceState.items():
            model.signal_state(device_state)

        # TODO: temporary expansion
        self.expandAll()
        self.resizeColumnToContents(0)
        self.refresher()


@dataclass
class DeviceRenderDisplay(QSvgWidget):
    deviceState: dict[str, DeviceState] = field(default_factory=dict)
    parent: typing.Optional['QtWidgets.QWidget'] = None
    selected_device_id: str = field(default='', init=False)
    _old_template: bytes = field(init=False)
    _template_cache: dict[str, str] = field(default_factory=dict, init=False)
    _index_map: dict[str, dict[str, int]] = field(default_factory=dict, init=False)

    def __post_init__(self):
        super(DeviceRenderDisplay, self).__init__(self.parent)
        self._old_template = b'0'
        # TODO: this is just a temporary load to avoid stretched svgs. There should be a better way to reserve a good size
        self.load("templates/CH Fighterstick USB.svg")

    # @print_timing
    # actual timing max 10ms
    def refresh(self):
        if self.selected_device_id not in self.deviceState:
            log(f"{self.selected_device_id} not found in {self.deviceState}")
            return

        selected_device = self.deviceState[self.selected_device_id]
        selected_device_name = selected_device.deviceName
        if selected_device_name in self._template_cache:
            base_template = self._template_cache[selected_device_name]
        else:
            # TODO: we need mapping here as not all devices are the same reported e.g virpil
            device_template_path = Path(os.path.join("templates", f"{selected_device_name}.svg"))
            if not device_template_path.exists():
                log(f"{selected_device_name} not found in templates", "error")
                return
            templater = Templater(device_template_path, brand_template=selected_device_name)
            # TODO: pull real bindings here: currently this is a dummy
            temp_bindings_buttons = selected_device.buttons.keys()
            templater.replace_with_bindings(dict(zip(temp_bindings_buttons, temp_bindings_buttons)))
            base_template = templater.get_template_as_bytes()
            if not base_template:
                log(f"{selected_device_name} not found in templates", "error")
                return
            self._template_cache[selected_device_name] = base_template

        # start = time()
        # TODO 1: cache parsed tree and use references for switching
        # TODO 2: use stax parser
        tree = etree.parse(BytesIO(base_template))
        # print(f"etree parse {(time() - start) * 1000:.2f}ms")

        for button_name, pressed in selected_device.buttons.items():
            if not pressed:
                continue
            # start = time()
            # TODO: we could use XPath class to only compile once
            # TODO: usually you would do something lie /svg:svg/svg:g/svg:rect[@id='Button_1'] but somehow this seems to not work
            # TODO: don't map unbound buttons by checking list length
            button_in_xml = tree.xpath(f"/svg:svg/svg:g/svg:rect[@id='{button_name}_rect']",
                                       namespaces={'svg': 'http://www.w3.org/2000/svg'})[0]
            # print(f"xpath {(time() - start) * 1000:.2f}ms")
            button_in_xml.attrib['fill'] = 'red'

        new_bytes = etree.tostring(tree)
        if new_bytes != self._old_template:
            log(f"update render for {self.selected_device_id}")
            self.load(new_bytes)
            self._old_template = new_bytes
            self.update()


@dataclass
class VisualizerWindow(QtWidgets.QMainWindow):
    deviceState: dict[str, DeviceState] = field(default_factory=dict)
    parent: typing.Optional['QtWidgets.QWidget'] = None
    device_render_display: DeviceRenderDisplay = None
    _stick_selector: QtWidgets.QComboBox = field(default='', init=False)
    _connected_devices: int = field(default=-1, init=False)

    def __post_init__(self) -> None:
        super(VisualizerWindow, self).__init__(self.parent)

        self.deviceState = {}

        main_splitter = QSplitter(self)

        debug_display_image_widget = DebugDisplayImageWidget(self.deviceState, self.refresh)
        q_scroll_area = QScrollArea()
        q_scroll_area.setWidget(debug_display_image_widget)

        main_splitter.addWidget(q_scroll_area)

        render_splitter = QSplitter(main_splitter)
        render_splitter.setOrientation(QtCore.Qt.Vertical)
        self.stick_selector = QtWidgets.QComboBox()
        self.stick_selector.activated.connect(self._switch_stick)
        render_splitter.addWidget(self.stick_selector)
        device_render_display = DeviceRenderDisplay(self.deviceState)
        render_splitter.addWidget(device_render_display)
        main_splitter.addWidget(render_splitter)

        self.setCentralWidget(main_splitter)
        self.setMinimumSize(debug_display_image_widget.width(), debug_display_image_widget.height())
        self.device_render_display = device_render_display

    def _switch_stick(self):
        switch_action: QtWidgets.QAction = self.stick_selector.itemData(self.stick_selector.currentIndex())
        self.device_render_display.selected_device_id = switch_action.text()
        log(f"switch selected device to {self.device_render_display.selected_device_id}")

    def refresh(self):
        if self.device_render_display:
            known_devices: list[str] = []
            currently_connected_devices = len(self.deviceState)
            if currently_connected_devices != self._connected_devices:
                self._connected_devices = currently_connected_devices
                log(f"Updating {currently_connected_devices} devices")

                # Add new devices
                for device_id, device_state in self.deviceState.items():
                    known_devices.append(device_state.deviceName)
                    stick_present = False
                    for i in range(self.stick_selector.count()):
                        if self.stick_selector.itemText(i) != device_state.deviceName:
                            continue
                        log(f"device {device_state.deviceName} found")
                        stick_present = True
                    if not stick_present:
                        log(f"adding new device {device_state.deviceName}")
                        switch_action = QtWidgets.QAction(self.stick_selector)
                        switch_action.setText(device_id)
                        self.stick_selector.addItem(device_state.deviceName, QtCore.QVariant(switch_action))

                log(f"known devices: {known_devices}")

                # Cleanup devices that not anymore connected
                for i in range(self.stick_selector.count()):
                    item_text = self.stick_selector.itemText(i)
                    if item_text not in known_devices:
                        log(f"removing item {item_text}")
                        self.stick_selector.removeItem(i)

            self.device_render_display.refresh()
