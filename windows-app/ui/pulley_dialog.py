"""Work out the spindle speeds from the belt pulleys.

The spindle motor turns at one speed (the Franklin Electric motor's label
says 3250 RPM). The belt goes between a step on the motor pulley and a
step on the spindle pulley; for each belt position:

    spindle RPM = motor RPM × motor-step diameter ÷ spindle-step diameter

Measure across each pulley step (any unit, as long as both are the same).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from ui import theme

MOTOR_RPM = 3250        # Franklin Electric 1/4 HP motor label (images/franklin-electric-spindle-motor.jpg)


def speeds(motor_rpm: float, pairs: list[tuple[float, float]]) -> list[int]:
    out = []
    for m, s in pairs:
        if m > 0 and s > 0:
            out.append(int(round(motor_rpm * m / s, -1)))
    return sorted(set(out))


class PulleyDialog(QDialog):
    ROWS = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spindle speeds from the pulleys")
        self.setMinimumWidth(480)
        lay = QVBoxLayout(self)
        intro = QLabel("Unplug the mill and open the belt cover. For each belt position, measure "
                       "across the motor pulley step and the spindle pulley step the belt sits on "
                       "(both in mm or both in inches). The app works out the spindle speed.")
        intro.setWordWrap(True)
        lay.addWidget(intro)
        row = QHBoxLayout()
        row.addWidget(QLabel("Motor speed (from its label)"))
        self.motor = QSpinBox()
        self.motor.setRange(100, 30000)
        self.motor.setValue(MOTOR_RPM)
        self.motor.setSuffix(" RPM")
        self.motor.valueChanged.connect(self._update)
        row.addWidget(self.motor)
        row.addStretch(1)
        lay.addLayout(row)
        self.table = QTableWidget(self.ROWS, 3)
        self.table.setHorizontalHeaderLabels(["Motor step", "Spindle step", "Spindle RPM"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        for r in range(self.ROWS):
            it = QTableWidgetItem("")
            self.table.setItem(r, 2, it)
            for c in (0, 1):
                self.table.setItem(r, c, QTableWidgetItem(""))
        self.table.itemChanged.connect(self._update)
        lay.addWidget(self.table)
        self.result = QLabel("")
        self.result.setWordWrap(True)
        lay.addWidget(self.result)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                        QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Use these speeds")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        self._update()

    def pairs(self) -> list[tuple[float, float]]:
        out = []
        for r in range(self.ROWS):
            try:
                m = float(self.table.item(r, 0).text())
                s = float(self.table.item(r, 1).text())
            except (ValueError, AttributeError):
                continue
            out.append((m, s))
        return out

    def set_row(self, r: int, motor_step: float, spindle_step: float) -> None:
        self.table.item(r, 0).setText(f"{motor_step:g}")
        self.table.item(r, 1).setText(f"{spindle_step:g}")

    def speeds(self) -> list[int]:
        return speeds(self.motor.value(), self.pairs())

    def _update(self, *_a) -> None:
        self.table.blockSignals(True)
        for r in range(self.ROWS):
            try:
                m = float(self.table.item(r, 0).text())
                s = float(self.table.item(r, 1).text())
                v = f"{int(round(self.motor.value() * m / s, -1)):,}" if m > 0 and s > 0 else ""
            except (ValueError, AttributeError, ZeroDivisionError):
                v = ""
            self.table.item(r, 2).setText(v)
        self.table.blockSignals(False)
        sp = self.speeds()
        if sp:
            self.result.setText("Spindle speeds: " + ", ".join(f"{v:,}" for v in sp) + " RPM")
            self.result.setStyleSheet(f"color: {theme.OK}; font-weight: 600;")
        else:
            self.result.setText("Type the two sizes for at least one belt position.")
            self.result.setStyleSheet(f"color: {theme.MUTED};")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(sp))
