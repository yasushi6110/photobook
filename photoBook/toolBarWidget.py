# -*- coding: utf-8 -*-
"""
Copyright 2024, YAMAGUCHI Yasushi
"""
from PySide6 import QtWidgets, QtGui, QtCore
from .define import *


class ToolBarWidget(QtWidgets.QWidget):
    # values_changed = QtCore.Signal()
    canvas_size_changed = QtCore.Signal(int, int)
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
        self.size_preset = QtWidgets.QComboBox()
        self.size_preset.addItems(SIZE_PRESETS.keys())

        self.size1_spin = QtWidgets.QSpinBox()
        self.size1_spin.setRange(50, 10000)
        self.size1_spin.setValue(3508)
        self.size1_spin.setMinimumWidth(90)

        self.size2_spin = QtWidgets.QSpinBox()
        self.size2_spin.setRange(50, 10000)
        self.size2_spin.setValue(2480)
        self.size2_spin.setMinimumWidth(90)

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

        self.rotate_btn_plus = QtWidgets.QPushButton("90°回転")
        self.rotate_btn_minus = QtWidgets.QPushButton("-90°回転")
        self.save_layout_button = QtWidgets.QPushButton("レイアウト保存")
        self.save_layout_button.clicked.connect(self.save_layout_clicked.emit)
        self.load_layout_button = QtWidgets.QPushButton("レイアウト読込")
        self.load_layout_button.clicked.connect(self.load_layout_clicked.emit)
        self.batch_import_button = QtWidgets.QPushButton("一括読み込み")
        self.batch_import_button.clicked.connect(self.batch_import_clicked.emit)

        self.bg_color_btn = QtWidgets.QPushButton("背景色")
        self.bg_color_btn.clicked.connect(self._choose_color)
        self.rotate_btn_plus.clicked.connect(lambda: self.rotate_changed.emit(90))
        self.rotate_btn_minus.clicked.connect(lambda: self.rotate_changed.emit(-90))

        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(2)
        h_layout1 = QtWidgets.QHBoxLayout()
        h_layout2 = QtWidgets.QHBoxLayout()
        h_layout3 = QtWidgets.QHBoxLayout()

        h_layout1.setContentsMargins(10, 0, 10, 0)
        h_layout1.setSpacing(3)
        h_layout1.addWidget(QtWidgets.QLabel("サイズ(px):"))
        h_layout1.addWidget(self.size_preset)
        h_layout1.addWidget(self.size1_spin)
        h_layout1.addWidget(self.size2_spin)
        h_layout1.addWidget(self.size_switch_cb)
        h_layout1.addStretch(1)

        h_layout2.setContentsMargins(10, 0, 10, 0)
        h_layout2.setSpacing(3)
        h_layout2.addWidget(QtWidgets.QLabel("レイアウト:"))
        h_layout2.addWidget(self.layout_combo)
        h_layout2.addWidget(QtWidgets.QLabel("余白(px):"))
        h_layout2.addWidget(self.space_margin_spin)
        h_layout2.addWidget(QtWidgets.QLabel("上下の余白(px):"))
        h_layout2.addWidget(self.top_under_margin_spin)
        h_layout2.addWidget(QtWidgets.QLabel("横の余白(px):"))
        h_layout2.addWidget(self.side_margin_spin)
        h_layout2.addStretch(1)

        h_layout3.setContentsMargins(10, 0, 10, 0)
        h_layout3.setSpacing(3)
        h_layout3.addWidget(self.rotate_btn_minus)
        h_layout3.addWidget(self.rotate_btn_plus)
        h_layout3.addWidget(self.bg_color_btn)
        h_layout3.addWidget(self.save_layout_button)
        h_layout3.addWidget(self.load_layout_button)
        h_layout3.addWidget(self.batch_import_button)
        h_layout3.addStretch(1)

        self.setLayout(v_layout)
        v_layout.addLayout(h_layout1)
        v_layout.addLayout(h_layout2)
        v_layout.addLayout(h_layout3)
        self.size1_spin.valueChanged.connect(self._change_size)
        self.size2_spin.valueChanged.connect(self._change_size)
        self.space_margin_spin.valueChanged.connect(self.change_margin)
        self.top_under_margin_spin.valueChanged.connect(self.change_margin)
        self.side_margin_spin.valueChanged.connect(self.change_margin)
        self.layout_combo.currentTextChanged.connect(self._change_layout)
        self.size_preset.currentTextChanged.connect(self._size_preset_changed)
        self.setup_gui()

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
            size1, size2 = SIZE_PRESETS[preset_name]
            self.size1_spin.setValue(size1)
            self.size2_spin.setValue(size2)
            self._change_size()

    def _choose_color(self):
        # type: () -> None
        """背景色選択ダイアログを表示する
        """
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.bg_color_changed.emit(color)

    def change_margin(self):
        # type: () -> None
        """余白変更を通知する
        """
        self.margin_changed.emit(self.space_margin_spin.value(),
                                  self.top_under_margin_spin.value(),
                                  self.side_margin_spin.value())

    def _change_size(self):
        # type: () -> None
        """サイズ変更を通知する
        """
        if self.size_switch_cb.isChecked():
            self.canvas_size_changed.emit(self.size2_spin.value(), self.size1_spin.value())
        else:
            self.canvas_size_changed.emit(self.size1_spin.value(), self.size2_spin.value())

    def setup_gui(self):
        # type: () -> None
        """GUIの初期設定を行う
        """
        self.size_switch_cb.stateChanged.connect(self._change_size)

    def context(self):
        # type: () -> dict
        """現在の設定値を辞書で取得する
        """
        context = {
            'size_preset': self.size_preset.currentText(),
            "size1": self.size1_spin.value(),
            "size2": self.size2_spin.value(),
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
        self.size_preset.setCurrentText(context.get("size_preset", "A4 3508 x 2480 px (300 DPI)"))
        self.size1_spin.setValue(context.get("size1", 3508))
        self.size2_spin.setValue(context.get("size2", 2480))
        self.size_switch_cb.setChecked(context.get("size_switch", False))
        layout_name = context.get("layout", "横 default")
        index = self.layout_combo.findText(layout_name)
        if index >= 0:
            self.layout_combo.setCurrentIndex(index)
        self.space_margin_spin.setValue(context.get("space_margin", 10))
        self.top_under_margin_spin.setValue(context.get("top_under_margin", 10))
        self.side_margin_spin.setValue(context.get("side_margin", 10))
