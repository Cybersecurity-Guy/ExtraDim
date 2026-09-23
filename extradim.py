import sys
import ctypes
from ctypes import wintypes
import colorsys

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QLinearGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QSlider,
    QSystemTrayIcon,
    QMenu,
)

from PySide6.QtCore import Qt, QPointF, QAbstractNativeEventFilter


# ============================================================
# WINDOWS MAGNIFICATION API
# ============================================================

magnification = ctypes.WinDLL("Magnification.dll")

MAGCOLOREFFECT = ctypes.c_float * 25


magnification.MagInitialize.restype = wintypes.BOOL

magnification.MagUninitialize.restype = wintypes.BOOL

magnification.MagSetFullscreenTransform.argtypes = [
    ctypes.c_float,
    ctypes.c_int,
    ctypes.c_int,
]

magnification.MagSetFullscreenTransform.restype = wintypes.BOOL

magnification.MagSetFullscreenColorEffect.argtypes = [
    ctypes.POINTER(MAGCOLOREFFECT),
]

magnification.MagSetFullscreenColorEffect.restype = wintypes.BOOL

magnification.MagGetFullscreenColorEffect.argtypes = [
    ctypes.POINTER(MAGCOLOREFFECT),
]

magnification.MagGetFullscreenColorEffect.restype = wintypes.BOOL


# ============================================================
# INITIALIZE MAGNIFICATION
# ============================================================

if not magnification.MagInitialize():
    raise RuntimeError(
        "Could not initialize Windows Magnification API."
    )


# ============================================================
# SAVE ORIGINAL WINDOWS COLOR EFFECT
# ============================================================

original_effect = MAGCOLOREFFECT()

if not magnification.MagGetFullscreenColorEffect(
    ctypes.byref(original_effect)
):

    for i in range(25):
        original_effect[i] = 0.0

    original_effect[0] = 1.0
    original_effect[6] = 1.0
    original_effect[12] = 1.0
    original_effect[18] = 1.0
    original_effect[24] = 1.0


# ============================================================
# KEEP MAGNIFICATION AT 1x
# ============================================================

magnification.MagSetFullscreenTransform(
    1.0,
    0,
    0
)


# ============================================================
# GLOBAL COLOR STATE
# ============================================================

# HSV
current_hue = 0.0
current_saturation = 0.0
current_value = 1.0

# Extra Dim darkness
current_darkness = 50


# ============================================================
# APPLY WINDOWS COLOR EFFECT
# ============================================================

def update_windows_effect():

    global current_hue
    global current_saturation
    global current_value
    global current_darkness

    # Convert HSV → RGB
    r, g, b = colorsys.hsv_to_rgb(
        current_hue,
        current_saturation,
        current_value
    )

    # Apply the separate Extra Dim slider.
    #
    # 0% darkness  = 100% brightness
    # 50% darkness = 50% brightness
    # 90% darkness = 10% brightness

    dim_factor = 1.0 - (
        current_darkness / 100.0
    )

    r *= dim_factor
    g *= dim_factor
    b *= dim_factor

    effect = MAGCOLOREFFECT(
        r, 0, 0, 0, 0,
        0, g, 0, 0, 0,
        0, 0, b, 0, 0,
        0, 0, 0, 1, 0,
        0, 0, 0, 0, 1
    )

    success = magnification.MagSetFullscreenColorEffect(
        ctypes.byref(effect)
    )

    if not success:
        print("Failed to apply Windows color effect.")


# ============================================================
# COLOR PICKER
# ============================================================

class ColorPicker(QWidget):

    def __init__(self):

        super().__init__()

        self.setFixedSize(
            295,
            145
        )

        self.dragging_square = False
        self.dragging_hue = False

        self.update()


    # ========================================================
    # PAINT
    # ========================================================

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )


        # ====================================================
        # MAIN COLOR SQUARE
        # ====================================================

        square_width = self.width()
        square_height = 112

        hue_color = QColor.fromHsvF(
            current_hue,
            1.0,
            1.0
        )


        # ----------------------------------------------------
        # White → selected hue
        # ----------------------------------------------------

        horizontal = QLinearGradient(
            0,
            0,
            square_width,
            0
        )

        horizontal.setColorAt(
            0,
            QColor(255, 255, 255)
        )

        horizontal.setColorAt(
            1,
            hue_color
        )

        painter.fillRect(
            0,
            0,
            square_width,
            square_height,
            horizontal
        )


        # ----------------------------------------------------
        # Transparent → black
        # ----------------------------------------------------

        vertical = QLinearGradient(
            0,
            0,
            0,
            square_height
        )

        vertical.setColorAt(
            0,
            QColor(0, 0, 0, 0)
        )

        vertical.setColorAt(
            1,
            QColor(0, 0, 0, 255)
        )

        painter.fillRect(
            0,
            0,
            square_width,
            square_height,
            vertical
        )


        # ====================================================
        # HUE SPECTRUM
        # ====================================================

        hue_y = 118
        hue_height = 16

        hue_gradient = QLinearGradient(
            0,
            0,
            square_width,
            0
        )

        hue_gradient.setColorAt(
            0.0,
            QColor.fromHsv(0, 255, 255)
        )

        hue_gradient.setColorAt(
            1 / 6,
            QColor.fromHsv(60, 255, 255)
        )

        hue_gradient.setColorAt(
            2 / 6,
            QColor.fromHsv(120, 255, 255)
        )

        hue_gradient.setColorAt(
            3 / 6,
            QColor.fromHsv(180, 255, 255)
        )

        hue_gradient.setColorAt(
            4 / 6,
            QColor.fromHsv(240, 255, 255)
        )

        hue_gradient.setColorAt(
            5 / 6,
            QColor.fromHsv(300, 255, 255)
        )

        hue_gradient.setColorAt(
            1.0,
            QColor.fromHsv(360, 255, 255)
        )

        painter.fillRect(
            0,
            hue_y,
            square_width,
            hue_height,
            hue_gradient
        )


        # ====================================================
        # COLOR SQUARE SELECTION CIRCLE
        # ====================================================

        x = (
            current_saturation
            * square_width
        )

        y = (
            1.0 - current_value
        ) * square_height


        # Black outline
        painter.setPen(
            QPen(
                QColor(0, 0, 0),
                1
            )
        )

        painter.setBrush(
            Qt.BrushStyle.NoBrush
        )

        painter.drawEllipse(
            QPointF(x, y),
            10,
            10
        )


        # White ring
        painter.setPen(
            QPen(
                QColor(255, 255, 255),
                3
            )
        )

        painter.drawEllipse(
            QPointF(x, y),
            8,
            8
        )


        # ====================================================
        # HUE SELECTION CIRCLE
        # ====================================================

        hue_x = (
            current_hue
            * square_width
        )

        hue_center_y = (
            hue_y
            + hue_height / 2
        )


        painter.setPen(
            QPen(
                QColor(0, 0, 0),
                1
            )
        )

        painter.drawEllipse(
            QPointF(
                hue_x,
                hue_center_y
            ),
            10,
            10
        )


        painter.setPen(
            QPen(
                QColor(255, 255, 255),
                3
            )
        )

        painter.drawEllipse(
            QPointF(
                hue_x,
                hue_center_y
            ),
            8,
            8
        )


        painter.end()


    # ========================================================
    # MOUSE PRESS
    # ========================================================

    def mousePressEvent(self, event):

        x = event.position().x()
        y = event.position().y()


        # Main color square
        if 0 <= y <= 112:

            self.dragging_square = True

            self.update_square(
                x,
                y
            )


        # Hue bar
        elif 116 <= y <= 140:

            self.dragging_hue = True

            self.update_hue(
                x
            )


    # ========================================================
    # MOUSE MOVE
    # ========================================================

    def mouseMoveEvent(self, event):

        x = event.position().x()
        y = event.position().y()


        if self.dragging_square:

            self.update_square(
                x,
                y
            )


        elif self.dragging_hue:

            self.update_hue(
                x
            )


    # ========================================================
    # MOUSE RELEASE
    # ========================================================

    def mouseReleaseEvent(self, event):

        self.dragging_square = False
        self.dragging_hue = False


    # ========================================================
    # UPDATE COLOR SQUARE
    # ========================================================

    def update_square(
        self,
        x,
        y
    ):

        global current_saturation
        global current_value

        x = max(
            0,
            min(
                self.width(),
                x
            )
        )

        y = max(
            0,
            min(
                112,
                y
            )
        )

        current_saturation = (
            x / self.width()
        )

        current_value = (
            1.0 - (
                y / 112
            )
        )

        update_windows_effect()

        self.update()


    # ========================================================
    # UPDATE HUE
    # ========================================================

    def update_hue(self, x):

        global current_hue

        x = max(
            0,
            min(
                self.width(),
                x
            )
        )

        current_hue = (
            x / self.width()
        )

        update_windows_effect()

        self.update()

# ============================================================
# GLOBAL EXIT HOTKEY
# Ctrl + Alt + Shift + E
# ============================================================

user32 = ctypes.windll.user32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004

VK_E = 0x45

HOTKEY_ID = 1


class GlobalHotkey(QAbstractNativeEventFilter):

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):

        # Windows message structure
        if eventType == "windows_generic_MSG":

            msg = ctypes.cast(
                int(message),
                ctypes.POINTER(MSG)
            ).contents

            # WM_HOTKEY
            if msg.message == 0x0312:

                if msg.wParam == HOTKEY_ID:

                    self.callback()

                    return True, 0

        return False, 0


class MSG(ctypes.Structure):

    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt_x", ctypes.c_long),
        ("pt_y", ctypes.c_long),
    ]

# ============================================================
# CONTROL WINDOW
# ============================================================

class ControlWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Extra Dim"
        )

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )


        # ====================================================
        # COLOR PICKER
        # ====================================================

        self.picker = ColorPicker()


        # ====================================================
        # DARKNESS LABEL
        # ====================================================

        self.darkness_label = QLabel(
            "Darkness: 50%  |  Brightness: 50%"
        )


        # ====================================================
        # DARKNESS SLIDER
        # ====================================================

        self.darkness_slider = QSlider(
            Qt.Orientation.Horizontal
        )

        self.darkness_slider.setMinimum(
            0
        )

        self.darkness_slider.setMaximum(
            90
        )

        self.darkness_slider.setValue(
            current_darkness
        )

        self.darkness_slider.valueChanged.connect(
            self.change_darkness
        )


        # ====================================================
        # LAYOUT
        # ====================================================

        layout = QVBoxLayout()

        layout.setSpacing(
            6
        )

        layout.addWidget(
            self.picker
        )

        layout.addWidget(
            self.darkness_label
        )

        layout.addWidget(
            self.darkness_slider
        )

        self.setLayout(
            layout
        )


        self.resize(
            320,
            205
        )


    # ========================================================
    # DARKNESS SLIDER
    # ========================================================

    def change_darkness(
        self,
        value
    ):

        global current_darkness

        current_darkness = value

        brightness = (
            100 - value
        )

        self.darkness_label.setText(
            f"Darkness: {value}%  |  "
            f"Brightness: {brightness}%"
        )

        update_windows_effect()


    # ========================================================
    # CLOSE = HIDE
    # ========================================================

    def closeEvent(
        self,
        event
    ):

        self.hide()

        event.ignore()


# ============================================================
# APPLICATION
# ============================================================

app = QApplication(
    sys.argv
)

app.setQuitOnLastWindowClosed(
    False
)


# ============================================================
# CONTROL WINDOW
# ============================================================

window = ControlWindow()


# ============================================================
# SYSTEM TRAY
# ============================================================

tray = QSystemTrayIcon(
    app
)

tray.setToolTip(
    "Extra Dim"
)


tray.setIcon(
    app.style().standardIcon(
        app.style().StandardPixmap.SP_ComputerIcon
    )
)


# ============================================================
# TRAY MENU
# ============================================================

menu = QMenu()

show_action = menu.addAction(
    "Show Extra Dim"
)

menu.addSeparator()

exit_action = menu.addAction(
    "Exit Extra Dim"
)

tray.setContextMenu(
    menu
)


# ============================================================
# SHOW CONTROLS
# ============================================================

def show_controls():

    if window.isMinimized():

        window.showNormal()

    else:

        window.show()

    window.raise_()
    window.activateWindow()


show_action.triggered.connect(
    show_controls
)


# ============================================================
# TRAY CLICK
# ============================================================

def tray_clicked(reason):

    print(
        "Tray event:",
        reason
    )

    if reason in (
        QSystemTrayIcon.ActivationReason.Trigger,
        QSystemTrayIcon.ActivationReason.DoubleClick,
    ):

        show_controls()


tray.activated.connect(
    tray_clicked
)


# ============================================================
# EXIT
# ============================================================

def exit_program():

    print("Exiting Extra Dim...")

    # Restore original Windows effect
    magnification.MagSetFullscreenColorEffect(
        ctypes.byref(original_effect)
    )

    # Restore normal magnification
    magnification.MagSetFullscreenTransform(
        1.0,
        0,
        0
    )

    # Remove global hotkey
    user32.UnregisterHotKey(
        None,
        HOTKEY_ID
    )

    # Shut down Magnification API
    magnification.MagUninitialize()

    app.quit()

    print(
        "Exiting Extra Dim..."
    )


    # Restore original Windows effect
    magnification.MagSetFullscreenColorEffect(
        ctypes.byref(
            original_effect
        )
    )


    magnification.MagSetFullscreenTransform(
        1.0,
        0,
        0
    )


    magnification.MagUninitialize()

    app.quit()

# ============================================================
# GLOBAL EXIT HOTKEY
# Ctrl + Alt + Shift + E
# ============================================================

HOTKEY_ID = 1

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004

VK_E = 0x45

if not user32.RegisterHotKey(
    None,
    HOTKEY_ID,
    MOD_CONTROL | MOD_ALT | MOD_SHIFT,
    VK_E
):
    print(
        "WARNING: Could not register "
        "Ctrl + Alt + Shift + E"
    )


class GlobalHotkey(QAbstractNativeEventFilter):

    def nativeEventFilter(
        self,
        eventType,
        message
    ):

        if eventType == "windows_generic_MSG":

            msg = ctypes.cast(
                int(message),
                ctypes.POINTER(MSG)
            ).contents

            # WM_HOTKEY
            if msg.message == 0x0312:

                if msg.wParam == HOTKEY_ID:

                    exit_program()

                    return True, 0

        return False, 0


hotkey = GlobalHotkey()

app.installNativeEventFilter(
    hotkey
)

exit_action.triggered.connect(
    exit_program
)


# ============================================================
# START
# ============================================================

tray.show()

window.show()


sys.exit(
    app.exec()
)