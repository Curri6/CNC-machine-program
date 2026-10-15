"""Settings dialog (⚙ button)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QVBoxLayout,
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
        self.rpms = QLineEdit(settings.spindle_rpms)
        self.rpms.setToolTip("The spindle speeds your mill can be set to, separated by commas.\n"
                             "The defaults are typical Taig belt steps: change them to the speeds "
                             "on your mill.\nOne number = a spindle with one speed.")
        self.safez = dspin(settings.safe_z_in, 0.02, 2, 0.05, " in")
        self.tabh = dspin(settings.tab_height_in, 0.005, 0.5, 0.01, " in")
        self.climb = QCheckBox("Climb milling (off = conventional, better for an older mill)")
        self.climb.setChecked(settings.climb_milling)

        form.addRow(self._head("Machine"))
        form.addRow("Top speed (rapids)", self.rapid)
        form.addRow("Warn if deeper than", self.depth)
        form.addRow("Work area X (0 = off)", self.wx)
        form.addRow("Work area Y (0 = off)", self.wy)
        form.addRow("Feed if none is set", self.feed)
        form.addRow(self._head("Making G-code"))
        rp = QHBoxLayout()
        rp.addWidget(self.rpms, 1)
        calc = QPushButton("From pulleys…")
        calc.setToolTip("Work the speeds out from the belt pulley sizes")
        calc.clicked.connect(self._pulleys)
        rp.addWidget(calc)
        form.addRow("Spindle speeds (RPM)", rp)
        form.addRow("Safe height above the top", self.safez)
        form.addRow("Holding tab thickness", self.tabh)
        form.addRow("", self.climb)
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

    def _pulleys(self) -> None:
        from ui.pulley_dialog import PulleyDialog
        dlg = PulleyDialog(self)
        if dlg.exec() and dlg.speeds():
            self.rpms.setText(", ".join(str(v) for v in dlg.speeds()))

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
        self.rpms.setText(d.spindle_rpms)
        self.safez.setValue(d.safe_z_in)
        self.tabh.setValue(d.tab_height_in)
        self.climb.setChecked(d.climb_milling)

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
        test = Settings(spindle_rpms=self.rpms.text())
        s.spindle_rpms = ", ".join(str(r) for r in test.rpm_choices()) if self.rpms.text().strip() \
            else Settings().spindle_rpms
        s.safe_z_in = self.safez.value()
        s.tab_height_in = self.tabh.value()
        s.climb_milling = self.climb.isChecked()
        s.save()
        self.accept()
