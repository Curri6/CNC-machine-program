"""Settings dialog (⚙ button)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel, QLineEdit, QSpinBox,
    QVBoxLayout,
)

from app_config import Settings


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(440)
        self.s = settings
        lay = QVBoxLayout(self)
        form = QFormLayout()
        form.setVerticalSpacing(10)

        def dspin(v, lo, hi, step, suffix, dec=3):
            w = QDoubleSpinBox()
            w.setRange(lo, hi)
            w.setDecimals(dec)
            w.setSingleStep(step)
            w.setValue(v)
            w.setSuffix(suffix)
            w.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            return w

        self.rapid = dspin(settings.rapid_in_per_min, 0.5, 200, 0.5, " in/min", 1)
        self.depth = dspin(settings.max_depth_in, 0.001, 10, 0.05, " in")
        self.wx = dspin(settings.work_x_in, 0, 100, 0.5, " in", 2)
        self.wy = dspin(settings.work_y_in, 0, 100, 0.5, " in", 2)
        self.feed = dspin(settings.default_feed_in_per_min, 0.1, 200, 1, " in/min", 1)
        self.laptop = QLineEdit(settings.laptop_ip)
        self.oldpc = QLineEdit(settings.old_pc_ip)
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(settings.ftp_port)
        self.port.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)

        form.addRow(self._head("Machine"))
        form.addRow("Top speed (rapids)", self.rapid)
        form.addRow("Warn if deeper than", self.depth)
        form.addRow("Work area X (0 = off)", self.wx)
        form.addRow("Work area Y (0 = off)", self.wy)
        form.addRow("Feed if none is set", self.feed)
        form.addRow(self._head("Network (match the old PC)"))
        form.addRow("Laptop address", self.laptop)
        form.addRow("Old PC address", self.oldpc)
        form.addRow("FTP port", self.port)
        lay.addLayout(form)
        note = QLabel("Network changes take effect when the link is turned off and on again.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        lay.addWidget(note)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                              QDialogButtonBox.StandardButton.Cancel |
                              QDialogButtonBox.StandardButton.RestoreDefaults)
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self._defaults)
        lay.addWidget(bb)

    @staticmethod
    def _head(text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet("font-weight: 600; margin-top: 6px;")
        return l

    def _defaults(self) -> None:
        d = Settings()
        self.rapid.setValue(d.rapid_in_per_min)
        self.depth.setValue(d.max_depth_in)
        self.wx.setValue(d.work_x_in)
        self.wy.setValue(d.work_y_in)
        self.feed.setValue(d.default_feed_in_per_min)
        self.laptop.setText(d.laptop_ip)
        self.oldpc.setText(d.old_pc_ip)
        self.port.setValue(d.ftp_port)

    def _save(self) -> None:
        s = self.s
        s.rapid_in_per_min = self.rapid.value()
        s.max_depth_in = self.depth.value()
        s.work_x_in = self.wx.value()
        s.work_y_in = self.wy.value()
        s.default_feed_in_per_min = self.feed.value()
        s.laptop_ip = self.laptop.text().strip() or s.laptop_ip
        s.old_pc_ip = self.oldpc.text().strip() or s.old_pc_ip
        s.ftp_port = self.port.value()
        s.save()
        self.accept()
