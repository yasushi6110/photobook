# -*- coding: utf-8 -*-
"""
Copyright 2024, YAMAGUCHI Yasushi
"""
import json
from PySide6 import QtWidgets, QtGui, QtCore
import os
from pathlib import Path
from photoBook.define import *
from photoBook.toolBarWidget import ToolBarWidget
from photoBook.photoCollageView import PhotoCollageView
ROOT_PATH = Path(__file__).parent.parent
CONFIG_FILE = ROOT_PATH / "photo_book_config.json"


class PhotoBookApp(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.input_widget = ToolBarWidget()
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.photo_widget = PhotoCollageView()
        self.stock_widget = PhotoCollageView()
        self.stock_widget.canvas_margin_width = 10
        self.stock_widget.canvas_margin_height = 1000
        self.stock_widget.top_under_margin_px = 5
        self.stock_widget.side_margin_px = 5
        self.stock_widget.block_space_margin_px= 5
        self.stock_widget.export_width = 350
        self.stock_widget.export_height = 1000
        # self.stock_widget.wheel_zoom_flag = False
        self._first_show = True
        self.stock_widget.set_block_layout("ストック", tile_layout(3, 10))
        self.stock_widget.draw_layout(True)

        self._setup_gui()
        # 初期値、もしくは前回の復帰
        if not self.load_layout(True):
            self.set_layout_name(self.input_widget.get_current_layout())

    # =================================
    # Public
    # =================================
    def update(self):
        # self.input_widget._change_size()
        self.photo_widget.draw_layout()

    def set_image(self, image_path_list):
        # type: (list[str]) -> None
        """画像を順番に取り込みます
        """
        index = 0
        for image_path in image_path_list:
            if not image_path.lower().endswith(IMAGE_EXTS):
                continue
            self.photo_widget.set_image_to_block(index, image_path)
            index += 1
        self.update()

    def save_image(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "画像を保存", "collage.png", "PNG Files (*.png);;JPEG Files (*.jpg)")
        if path:
            self.photo_widget.export_image(path)
            QtWidgets.QMessageBox.information(self, "保存完了", f"保存しました:\n{path}")

    def save_layout(self, config=False):
        # type: (bool) -> None
        """レイアウトを保存する
        """
        if not config:
            file_path = QtWidgets.QFileDialog.getSaveFileName(
                self, "レイアウトを保存", "", "Layout Files (*.json)")
        else:
            file_path = [CONFIG_FILE.as_posix()]
        if file_path and os.path.isdir(os.path.dirname(file_path[0])):
            # windowのサイズを保持し、再現する
            window_size_width, window_size_height = self.size().width(), self.size().height()
            context = {
                'input_context': self.input_widget.context(),
                'photo_context': self.photo_widget.context(),
                'stock_context': self.stock_widget.context(),
                'window_size': (window_size_width, window_size_height),
            }
            with open(file_path[0], "w", encoding="utf-8") as f:
                json.dump(context, f, indent=4, ensure_ascii=False)

    def load_layout(self, config=False):
        # type: (bool) -> None
        """レイアウトを読み込む
        """
        if not config:
            file_path = QtWidgets.QFileDialog.getOpenFileName(self, "レイアウトを読み込む", "", "Layout Files (*.json)")
        else:
            file_path = [CONFIG_FILE.as_posix()]
        if file_path and os.path.isfile(file_path[0]):
            try:
                with open(file_path[0], "r", encoding="utf-8") as f:
                    context = json.load(f)
                    self.input_widget.set_context(context.get('input_context', {}))
                    self.photo_widget.set_context(context.get('photo_context', []))
                    self.stock_widget.set_context(context.get('stock_context', []))
                    self.resize(*context.get('window_size', (700, 500)))
                return True
            except Exception as e:
                pass
        return False

    def batch_import(self):
        # type: () -> None
        """フォルダを指定してその中の画像を一括で読み込む
        """
        batch_folder = QtWidgets.QFileDialog.getExistingDirectory(self, "画像フォルダを選択")
        if batch_folder and os.path.isdir(batch_folder):
            image_files = [os.path.join(batch_folder, f) for f in os.listdir(batch_folder)]
            image_files.sort()
            self.set_image(image_files)

    # =================================
    # Slots
    # =================================
    def set_background_color(self, color):
        # type: (QtGui.QColor) -> None
        """背景色を設定する
        """
        self.photo_widget.bg_color = color
        self.photo_widget.draw_layout()

    def set_margin(self, space_margin_px, top_under_margin_px, side_margin_px):
        # type: (int, int, int) -> None
        """余白を設定する
        """
        self.photo_widget.block_space_margin_px = space_margin_px
        self.photo_widget.top_under_margin_px = top_under_margin_px
        self.photo_widget.side_margin_px = side_margin_px
        self.photo_widget.draw_layout()

    def set_layout_name(self, layout_name):
        # type: (str) -> None
        """レイアウト名を元にblockのレイアウトを構築する
        """
        self.photo_widget.set_block_layout(layout_name, LAYOUT_PRESETS[layout_name])
        self.photo_widget.draw_layout()

    def set_export_size(self, width_px, height_px, dpi):
        # type: (int, int, int) -> None
        """出力画像のサイズとDPIを設定する
        """
        self.photo_widget.export_height = height_px
        self.photo_widget.export_width = width_px
        self.photo_widget.dpi = dpi
        self.photo_widget.draw_layout()

    # =================================
    # Private
    # =================================
    def _setup_gui(self):
        # type: () -> None
        """GUIの初期設定を行う
        """
        self.setWindowTitle("Photo Book")
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.input_widget)
        layout.addWidget(self.splitter)
        self.splitter.addWidget(self.stock_widget)
        self.splitter.addWidget(self.photo_widget)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        layout.setStretch(0, 0)
        layout.setStretch(1, 1)

        self.input_widget.canvas_size_changed.connect(self.set_export_size)
        self.input_widget.layout_changed.connect(self.set_layout_name)
        self.input_widget.margin_changed.connect(self.set_margin)
        self.input_widget.rotate_changed.connect(self.photo_widget.rotate_selected_image)
        self.input_widget.bg_color_changed.connect(self.set_background_color)
        self.input_widget.save_layout_clicked.connect(self.save_layout)
        self.input_widget.load_layout_clicked.connect(self.load_layout)
        self.input_widget.batch_import_clicked.connect(self.batch_import)
        self.splitter.splitterMoved.connect(self.fit_stock_widget)

        menu = self.menuBar().addMenu("ファイル")
        export_image_action = QtGui.QAction("画像を出力する", self)
        export_image_action.triggered.connect(self.save_image)
        save_layout_action = QtGui.QAction("レイアウトを保存する", self)
        save_layout_action.triggered.connect(self.save_layout)
        load_layout_action = QtGui.QAction("レイアウトを読み込む", self)
        load_layout_action.triggered.connect(self.load_layout)
        bach_import_action = QtGui.QAction("指定したディレクトリーの画像を登録する", self)
        bach_import_action.triggered.connect(self.batch_import)
        menu.addAction(export_image_action)
        menu.addSeparator()
        menu.addAction(save_layout_action)
        menu.addAction(load_layout_action)
        menu.addSeparator()
        menu.addAction(bach_import_action)
        self.input_widget.set_context({})

    # =================================
    # Override
    # =================================
    def fit_stock_widget(self):
        # type: () -> None
        """StockウィジェットのバハをGUIにフィットさせる
        横幅をフィットさせるように調整する
        """
        self.stock_widget.fit_horizontal_window_size()

    def closeEvent(self, event):
        self.save_layout(True)
        return super().closeEvent(event)

    def showEvent(self, event):
        result =  super().showEvent(event)
        if self._first_show:
            self.adjustSize()
            sizes = self.splitter.sizes()
            total_size = sum(sizes)
            sizes[0] = 250
            sizes[1] = total_size - sizes[0]
            self.splitter.setSizes(sizes)
            self.photo_widget.fit_window_size()
            self.stock_widget.fit_window_size()
            self.stock_widget.fit_horizontal_window_size()
        return result

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    win = PhotoBookApp()
    win.show()
    win.update()
    app.exec()
