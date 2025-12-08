# -*- coding: utf-8 -*-
"""
Copyright 2024, YAMAGUCHI Yasushi
"""
from PySide6 import QtWidgets, QtGui, QtCore
from .define import *


class ToolBarWidget(QtWidgets.QWidget):
    # values_changed = QtCore.Signal()
    canvas_size_changed = QtCore.Signal(int, int, int)
    layout_changed = QtCore.Signal(str)
    margin_changed = QtCore.Signal(int, int, int)
    bg_color_changed = QtCore.Signal(QtGui.QColor)
    rotate_changed = QtCore.Signal(int)
    save_layout_clicked = QtCore.Signal()
    load_layout_clicked = QtCore.Signal()
    batch_import_clicked = QtCore.Signal()

    def __init__(self):
        super().__init__()

        # =============================
        # サイズ関連
        # =============================
        self.bg_color = QtGui.QColor(255, 255, 255)
        self.size_preset = QtWidgets.QComboBox()
        self.size_preset.addItems(SIZE_PRESETS.keys())

        # =============================
        # サイズ関連
        # =============================
        self.space_margin_spin = QtWidgets.QSpinBox()
        self.space_margin_spin.setRange(0, 200)
        self.space_margin_spin.setValue(10)
        self.space_margin_spin.setMinimumWidth(70)

        self.top_under_margin_spin = QtWidgets.QSpinBox()
        self.top_under_margin_spin.setRange(0, 200)
        self.top_under_margin_spin.setValue(10)
        self.top_under_margin_spin.setMinimumWidth(70)

        self.side_margin_spin = QtWidgets.QSpinBox()
        self.side_margin_spin.setRange(0, 200)
        self.side_margin_spin.setValue(10)
        self.side_margin_spin.setMinimumWidth(70)

        self.size_switch_cb = QtWidgets.QCheckBox("サイズ スイッチ")
        self.layout_combo = QtWidgets.QComboBox()
        self.layout_combo.addItems(LAYOUT_PRESETS.keys())

        self.bg_color_btn = QtWidgets.QPushButton("背景色")
        self.bg_color_btn.clicked.connect(self._choose_color)

        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(2)
        h_layout1 = QtWidgets.QHBoxLayout()

        h_layout1.setContentsMargins(10, 0, 10, 0)
        h_layout1.setSpacing(3)
        h_layout1.addWidget(QtWidgets.QLabel("サイズ(px):"))
        h_layout1.addWidget(self.size_preset)
        h_layout1.addWidget(self.size_switch_cb)
        h_layout1.addWidget(QtWidgets.QLabel("レイアウト:"))
        h_layout1.addWidget(self.layout_combo)
        h_layout1.addWidget(QtWidgets.QLabel("余白(px):"))
        h_layout1.addWidget(self.space_margin_spin)
        h_layout1.addWidget(QtWidgets.QLabel("上下の余白(px):"))
        h_layout1.addWidget(self.top_under_margin_spin)
        h_layout1.addWidget(QtWidgets.QLabel("横の余白(px):"))
        h_layout1.addWidget(self.side_margin_spin)
        h_layout1.addWidget(self.bg_color_btn)
        h_layout1.addStretch(1)

        self.setLayout(v_layout)
        v_layout.addLayout(h_layout1)
        self.space_margin_spin.valueChanged.connect(self.change_margin)
        self.top_under_margin_spin.valueChanged.connect(self.change_margin)
        self.side_margin_spin.valueChanged.connect(self.change_margin)
        self.layout_combo.currentTextChanged.connect(self._change_layout)
        self.size_preset.currentTextChanged.connect(self._size_preset_changed)
        self.size_switch_cb.stateChanged.connect(self._size_preset_changed)
        self.setMinimumWidth(400)

    def get_current_layout(self):
        # type: () -> str
        """現在選択されているレイアウト名を取得する
        """
        return self.layout_combo.currentText()

    def _change_layout(self, layout_name):
        # type: (str) -> None
        """レイアウトのGUIを変更したときに呼ばれる関数"""
        self.size_switch_cb.setChecked(layout_name in SIZE_SWITCH_LAYOUT)
        self.layout_changed.emit(layout_name)

    def _size_preset_changed(self):
        # type: () -> None
        """サイズプリセット変更時の処理
        """
        preset_name = self.size_preset.currentText()
        if preset_name in SIZE_PRESETS:
            height, width, dpi = SIZE_PRESETS[preset_name]
            if self.size_switch_cb.isChecked():
                self.canvas_size_changed.emit(height, width, dpi)
            else:
                self.canvas_size_changed.emit(width, height, dpi)

    def _choose_color(self):
        # type: () -> None
        """背景色選択ダイアログを表示する
        """
        color = QtWidgets.QColorDialog.getColor(initial=self.bg_color)
        if color.isValid():
            self.bg_color = color
            self.bg_color_changed.emit(color)

    def change_margin(self):
        # type: () -> None
        """余白変更を通知する
        """
        self.margin_changed.emit(self.space_margin_spin.value(),
                                  self.top_under_margin_spin.value(),
                                  self.side_margin_spin.value())

    def context(self):
        # type: () -> dict
        """現在の設定値を辞書で取得する
        """
        r_color = self.bg_color.toRgb().red()
        g_color = self.bg_color.toRgb().green()
        b_color = self.bg_color.toRgb().blue()
        context = {
            'bg_color': (r_color, g_color, b_color),
            'size_preset': self.size_preset.currentText(),
            "size_switch": self.size_switch_cb.isChecked(),
            "layout": self.layout_combo.currentText(),
            "space_margin": self.space_margin_spin.value(),
            "top_under_margin": self.top_under_margin_spin.value(),
            "side_margin": self.side_margin_spin.value(),
        }
        return context

    def set_context(self, context):
        # type: (dict) -> None
        """設定値を辞書から読み込む
        """
        self.bg_color = QtGui.QColor(*context.get("bg_color", (255, 255, 255)))
        self.bg_color_changed.emit(self.bg_color)
        self.size_switch_cb.setChecked(context.get("size_switch", False))
        size_preset_name = context.get("size_preset", "A4 3508 x 2480 px (300 DPI)")
        size_preset_index = self.size_preset.findText(size_preset_name)
        if size_preset_index >= 0:
            self.size_preset.setCurrentIndex(size_preset_index)
        layout_name = context.get("layout", "横 default")
        layout_index = self.layout_combo.findText(layout_name)
        if layout_index >= 0:
            self.layout_combo.setCurrentIndex(layout_index)
        self.space_margin_spin.setValue(context.get("space_margin", 10))
        self.top_under_margin_spin.setValue(context.get("top_under_margin", 10))
        self.side_margin_spin.setValue(context.get("side_margin", 10))

        self._size_preset_changed()
        self.change_margin()
