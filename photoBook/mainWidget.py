# -*- coding: utf-8 -*-
"""
Copyright 2024, YAMAGUCHI Yasushi
"""
from PySide6 import QtWidgets, QtGui
import os
from photoBook.define import *
from photoBook.toolBarWidget import ToolBarWidget
from photoBook.photoCollageView import PhotoCollageView as PhotoCollageWidget


class PhotoBookApp(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.input_widget = ToolBarWidget()
        layout_name = self.input_widget.get_current_layout()
        self.photo_widget = PhotoCollageWidget(layout_name=layout_name)
        self._setup_gui()

    def update(self):
        # size = self.input_widget.get_attr("long_side_px")
        # margin = self.input_widget.get_attr("margin_px")
        # layout_name = self.input_widget.get_attr("layout")
        self.input_widget._change_size()
        # self.input_widget._choose_color()
        # self.photo_widget._load_layout(layout_name)
        # self.photo_widget.set_canvas_by_long_side(size, self.photo_widget.portrait)
        # self.photo_widget.set_canvas_size
        # self.photo_widget.set_margin(margin)
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

    def save_layout(self):
        # type: () -> None
        """レイアウトを保存する
        """
        file_path = QtWidgets.QFileDialog.getSaveFileName(self, "レイアウトを保存", "", "Layout Files (*.json)")
        if os.path.isdir(os.path.dirname(file_path[0])):
            context = {
                'input_context': self.input_widget.context(),
                'photo_context': self.photo_widget.context()
            }
            import json
            with open(file_path[0], "w", encoding="utf-8") as f:
                json.dump(context, f, indent=4, ensure_ascii=False)

    def load_layout(self):
        # type: () -> None
        """レイアウトを読み込む
        """
        file_path = QtWidgets.QFileDialog.getOpenFileName(self, "レイアウトを読み込む", "", "Layout Files (*.json)")
        if file_path and os.path.isfile(file_path[0]):
            import json
            with open(file_path[0], "r", encoding="utf-8") as f:
                context = json.load(f)
                self.input_widget.set_context(context.get('input_context', {}))
                self.photo_widget.set_context(context.get('photo_context', {}))

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
        layout.addWidget(self.photo_widget)
        layout.setStretch(0, 0)
        layout.setStretch(1, 1)

        # self.input_widget.values_changed.connect(self.apply_settings)
        self.input_widget.canvas_size_changed.connect(self.photo_widget.set_canvas_size)
        self.input_widget.layout_changed.connect(self.photo_widget.set_layout)
        self.input_widget.margin_changed.connect(self.photo_widget.set_margin)
        self.input_widget.rotate_changed.connect(self.photo_widget.rotate_selected_image)
        self.input_widget.bg_color_changed.connect(self.photo_widget.set_background_color)
        self.input_widget.save_layout_clicked.connect(self.save_layout)
        self.input_widget.load_layout_clicked.connect(self.load_layout)
        self.input_widget.batch_import_clicked.connect(self.batch_import)

        menu = self.menuBar().addMenu("ファイル")
        save_action = QtGui.QAction("画像を保存", self)
        save_action.triggered.connect(self.save_image)
        menu.addAction(save_action)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    win = PhotoBookApp()
    win.resize(700, 500)
    win.show()
    app.exec()
