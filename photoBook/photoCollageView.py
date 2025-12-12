# -*- coding: utf-8 -*-
"""
PhotoCollage - QGraphicsView完全再現版
"""
import copy
from PySide6 import QtWidgets, QtGui, QtCore
from PIL import Image
from pillow_heif import register_heif_opener
register_heif_opener()
import os
import random
import math
from .define import *
PREVIEW_MAX_SIZE = 512.0
PREVIEW_CANVAS_WIDTH = 1900
DRAG_ITEM = None

class PhotoInfo:
    """画像ブロック情報"""
    def __init__(self, rect_ratio=None):
        # type: (tuple[float, float, float, float]) -> None
        self._layout_cache = {}
        self._current_layout = None
        self.init_rect_ratio = (0.0, 0.0, 1.0, 1.0)
        self.rect_ratio = (0.0, 0.0, 1.0, 1.0)
        self.image_path = None  # type: str
        self.preview_img = None  # type: Image.ImageFile
        self.full_img = None  # type: Image.ImageFile
        self.color = (255, random.randint(180, 210), random.randint(180, 210))
        self.offset_x = 0
        self.offset_y = 0
        self.scale = 1.0
        self.rotation = 0
        self.rot_90_scale = 1.0
        self.update_rect_ratio(rect_ratio)

    def update_rect_ratio(self, rect_ratio):
        self.init_rect_ratio = rect_ratio
        self.rect_ratio = copy.deepcopy(self.init_rect_ratio)

    def update_attr_from_layout(self, layout_name):
        if self._current_layout:
            self._layout_cache[self._current_layout] = [self.offset_x, self.offset_y, self.scale]
        if layout_name in self._layout_cache:
            self.offset_x, self.offset_y, self.scale = self._layout_cache[layout_name]
        else:
            self.offset_x, self.offset_y, self.scale = 0, 0, 1.0
        self._current_layout = layout_name

    def update_image(self):
        if not self.image_path or not os.path.isfile(self.image_path):
            self.preview_img = None
            self.full_img = None
            return
        image = Image.open(self.image_path)
        self.full_img = image
        if image.width > image.height:
            new_width = PREVIEW_MAX_SIZE
            new_height = (PREVIEW_MAX_SIZE / image.width) * image.height
            self.rot_90_scale = float(new_width) / float(new_height)
        else:
            new_height = PREVIEW_MAX_SIZE
            new_width = (PREVIEW_MAX_SIZE / image.height) * image.width
            self.rot_90_scale = float(new_height) / float(new_width)
        self.preview_img = image.resize((int(new_width), int(new_height)), Image.BICUBIC)

    def switch_status(self, item):
        # type: (PhotoInfo) -> None
        """ブロックの状態を別のブロックと入れ替え
        """
        self.image_path, item.image_path = item.image_path, self.image_path
        self.preview_img, item.preview_img = item.preview_img, self.preview_img
        self.full_img, item.full_img = item.full_img, self.full_img
        self.offset_x, item.offset_x = item.offset_x, self.offset_x
        self.offset_y, item.offset_y = item.offset_y, self.offset_y
        self.scale, item.scale = item.scale, self.scale
        self.rotation, item.rotation = item.rotation, self.rotation


class PhotoBlockItem(QtWidgets.QGraphicsItem):

    """セル単位のアイテム：内部画像の移動／回転／スケール対応"""
    def __init__(self, block: PhotoInfo, scene_rect: QtCore.QRectF, parent_view):
        super().__init__()
        self._block = block
        self._photo_block_items = []  # type: list[PhotoBlockItem]
        self._parent_view = parent_view  # type: PhotoCollageView
        self._dragging = False
        self._ctrl_drag = False
        self._last_mouse_pos = QtCore.QPointF()
        self._is_selected = False
        self._is_drop_target = False
        self._dpi = None
        self.update_from_block(scene_rect)
        self.setup_gui()

    def setup_gui(self):
        # type: () -> None
        """GUI設定"""
        # Drag & Drop を受け入れる
        self.setAcceptDrops(True)
        # 自身が選択できるようにする
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)

    def update_from_block(self, scene_rect):
        # type: (str) -> None
        """ブロック情報から矩形を更新
        """
        x = scene_rect.width() * self._block.rect_ratio[0]
        y = scene_rect.height() * self._block.rect_ratio[1]
        w = scene_rect.width() * self._block.rect_ratio[2]
        h = scene_rect.height() * self._block.rect_ratio[3]
        self.rect = QtCore.QRectF(x, y, w, h)
        self.prepareGeometryChange()

    # ==========================
    # Override
    # ==========================
    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget=None):
        painter.save()
        painter.fillRect(self.rect, QtGui.QColor(200, 200, 200))
        painter.setClipRect(self.rect)

        render_image = self._block.preview_img
        if self._parent_view.export_flag:
            render_image = self._block.full_img

        if render_image:
            img = render_image.convert("RGBA")
            iw, ih = img.size

            # スケール倍率を計算
            ratio = max(self.rect.width() / iw, self.rect.height() / ih) * self._block.scale + 0.005

            scaled_size = (int(iw * ratio), int(ih * ratio))
            img = img.resize(scaled_size, Image.BICUBIC)

            # Image.NEAREST (最近傍補間)
            # Image.BOX (エリア補間)
            # Image.BILINEAR (双線形補間)
            # Image.HAMMING (ハミング補間)
            # Image.BICUBIC (双三次補間)
            # Image.LANCZOS (ランツォシュ補間)
            # 選択のポイント
            # 高速性重視: NEAREST または BILINEAR
            # 品質重視: BICUBIC または LANCZOS
            # 縮小時のエイリアシング抑制: AREA

            # 回転（アスペクト比維持、中心基準）
            img = img.rotate(-self._block.rotation, expand=True, resample=Image.BICUBIC)

            # Pillow → QPixmap 変換
            qimg = QtGui.QImage(img.tobytes("raw", "RGBA"), img.width, img.height, QtGui.QImage.Format_RGBA8888)
            pix = QtGui.QPixmap.fromImage(qimg)

            # 中心配置 + offset
            cx = round(self.rect.center().x() - pix.width() / 2 + self._block.offset_x * self._parent_view.canvas_width)
            cy = round(self.rect.center().y() - pix.height() / 2 + self._block.offset_y * self._parent_view.canvas_height)
            painter.drawPixmap(QtCore.QPointF(cx, cy), pix)
        else:
            # 画像を保存する場合は、BGカラーで塗りつぶす
            if self._parent_view.export_flag:
                painter.fillRect(self.rect, self._parent_view.bg_color)
            else:
                painter.fillRect(self.rect, QtGui.QColor(*self._block.color))

        # =============================
        # 選択していた場合の枠線の描画
        # =============================
        if self._is_selected:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, False)  # アンチエイリアスを無効化
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 0), 10))
        elif self._is_drop_target:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, False)  # アンチエイリアスを無効化
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 100, 100), 10))
        else:
            painter.setPen(QtCore.Qt.NoPen)  # ペンを無効化
        painter.drawRect(self.rect)
        painter.restore()

    # =================================
    # Mouse Events
    # =================================
    def mousePressEvent(self, event):
        global DRAG_ITEM
        self._parent_view.clear_selection()
        self._is_selected = True
        if event.button() == QtCore.Qt.LeftButton:
            self._dragging = True
            self._ctrl_drag = bool(event.modifiers() & QtCore.Qt.ControlModifier)
            self._last_mouse_pos = event.scenePos()
            if self._ctrl_drag:
                self.scene().clearSelection()
            else:
                DRAG_ITEM = self
        self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        global DRAG_ITEM
        if not self._dragging:
            DRAG_ITEM = None
            return
        delta = event.scenePos() - self._last_mouse_pos
        self._last_mouse_pos = event.scenePos()

        if self._ctrl_drag:
            # Ctrl+Drag → 内部画像移動
            self._block.offset_x += delta.x() / self._parent_view.canvas_width
            self._block.offset_y += delta.y() / self._parent_view.canvas_height
            self.update()
        else:
            # 通常ドラッグ → D&D入れ替え
            drag = QtGui.QDrag(self._parent_view)
            mime = QtCore.QMimeData()
            mime.setText(self._block.image_path or "")
            drag.setMimeData(mime)
            drag.exec(QtCore.Qt.MoveAction)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        global DRAG_ITEM
        self._dragging = False
        DRAG_ITEM = None
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        # type: (QtGui.QGraphicsSceneWheelEvent) -> None
        """ホイールでスケール"""
        ctrl_drag = bool(event.modifiers() & QtCore.Qt.ControlModifier)
        if ctrl_drag:
            delta = 0
            # Qt6 では angleDelta が無いので、代替で delta() を使用
            if hasattr(event, "delta"):
                delta = event.delta()
            elif hasattr(event, "angleDelta"):  # 念のためPyQt互換
                delta = event.angleDelta().y()
            if delta > 0:
                self._block.scale *= 1.05
            else:
                self._block.scale *= 0.95
            self.update()
            return
        return super().wheelEvent(event)

    # =================================
    # Drag Drop Events
    # =================================
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            self._parent_view.clear_selection(drop=True)
            self._is_drop_target = True
            self.update()
            event.acceptProposedAction()

    def dropEvent(self, event):
        global DRAG_ITEM
        # === 外部画像ファイル ===
        # if event.mimeData().hasUrls():
        #     for url in event.mimeData().urls():
        #         path = url.toLocalFile()
        #         if os.path.isfile(path) and path.lower().endswith(IMAGE_EXTS):
        #             self._block.image_path = path
        #             self._block.update_image()
        #             self.update()
        #             break
        #     event.acceptProposedAction()
        #     return

        # === 内部D&D（画像入れ替え）===
        if event.mimeData().hasText():
            src_path = event.mimeData().text()
            if not src_path:
                return
            # for item in self.parent_view.scene().items():
            #     if isinstance(item, PhotoBlockItem) and item.block.image_path == src_path:
            #         self.block.switch_status(item.block)
            #         self.update()
            #         item.update()
            #         break
            item = DRAG_ITEM
            if item and isinstance(item, PhotoBlockItem) and item._block.image_path == src_path:
                self._block.switch_status(item._block)
                self.update()
                item.update()
            event.acceptProposedAction()

        self._parent_view.clear_selection()
        self._parent_view.clear_selection(drop=True)
        self._is_selected = True
        self.update()


class PhotoCollageView(QtWidgets.QGraphicsView):

    def __init__(self):
        super().__init__()
        self.blocks = []  # type: list[PhotoInfo]
        """画像ブロック情報リスト"""
        self.block_count = 1
        """使用中のブロック数"""
        self._photo_block_items = []  # type: list[PhotoBlockItem]
        """現在保持しているPhotoBlockItemリスト"""
        self.bg_color = QtGui.QColor("white")
        """背景色"""
        self.dpi = 20  # type: int
        """出力解像度(DPI)"""
        self.export_flag = False
        """Export時に高解像度画像を使用するかどうかのフラグ"""
        self.canvas_margin_width = 20000
        self.canvas_margin_height = 20000
        """パンしやすいようにするメインのキャンバスの周りの余白"""
        self.canvas_width = 100
        """編集時のキャンバス幅(px)"""
        self.canvas_height = 100
        """編集時のキャンバス高さ(px)"""
        self.export_width = 100
        """Export時の幅(px)"""
        self.export_height = 1000
        """Export時の高さ(px)"""
        self.block_space_margin_px = 10
        """ブロック間の余白(px)"""
        self.top_under_margin_px = 10
        """上下の余白(px)"""
        self.side_margin_px = 10
        """左右の余白(px)"""
        self.wheel_zoom_flag = True
        """ホイールズーム有効フラグ"""
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setAcceptDrops(True)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setTransform(QtGui.QTransform())  # スケールをリセット
        self.centerOn(0, 0)  # シーンの中心を初期化

        # DefaultのScene
        scene = QtWidgets.QGraphicsScene(self)
        self.setScene(scene)

        # ContextMenu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    # =================================
    # Public Methods
    # =================================
    def get_selected_photo_brock_item(self):
        # type: () -> PhotoBlockItem
        for item in self.scene().items():
            if isinstance(item, PhotoBlockItem) and item._is_selected:
                return item
        return None

    def set_image_to_block(self, block_id, image_path):
        # type: (int, str) -> None
        """指定のブロックに画像をセット"""
        if 0 <= block_id  and block_id < len(self.blocks):
            blk = self.blocks[block_id]
        else:
            blk = PhotoInfo()
            self.blocks.append(blk)
        blk.image_path = image_path
        blk.update_image()

    def draw_layout(self, export_flag=False, fit_window=True):
        # type: (bool, bool) -> None
        """レイアウトを描画"""
        # 後でポジションとスケールを再現できるように数値を保持
        # scale = self.transform().m11()
        # center = self.mapToScene(self.viewport().rect().center())

        self.scene().clear()
        self.canvas_width = self.export_width
        self.canvas_height = self.export_height
        if not export_flag:
            self.canvas_width = PREVIEW_CANVAS_WIDTH
            rate = float(self.export_height) / float(self.export_width)
            self.canvas_height = int(self.canvas_width * rate)

        # Photoが登録されるシーンの大きさ
        scene_rect = QtCore.QRectF(0, 0, self.canvas_width, self.canvas_height)
        self.scene().setSceneRect(scene_rect)

        # キャンバスのパンをしやすくするために、大きめのシーンにする
        base_scene_rect = QtCore.QRectF(
            -self.canvas_margin_width, -self.canvas_margin_height,
            self.canvas_width+self.canvas_margin_width*2, self.canvas_height+self.canvas_margin_height*2)
        self.setSceneRect(base_scene_rect)

        # Background Color
        color = 160
        self.scene().setBackgroundBrush(QtGui.QColor(color, color, color, 255))

        # 各スペースの値をpxから出力サイズを1とした場合に比率に治す
        margin_ratio_x = margin_ratio_y = 0
        if self.block_space_margin_px > 0:
            margin_ratio_x = self.block_space_margin_px / self.export_width
            margin_ratio_y = self.block_space_margin_px / self.export_height

        side_margin = self.side_margin_px / self.export_width
        top_under_margin = self.top_under_margin_px / self.export_height
        side_scale = (1.0 - side_margin * 2.0)
        top_scale = (1.0 - top_under_margin * 2.0)

        # Photoの下地の色を決めるQGraphicsRectItemを作成し追加
        brush = QtGui.QBrush(self.bg_color)
        rect_item = QtWidgets.QGraphicsRectItem(0, 0, self.canvas_width, self.canvas_height)
        rect_item.setBrush(brush)
        self.scene().addItem(rect_item)

        self._photo_block_items.clear()

        # Photoのブロックを追加
        for blk in self.blocks[:self.block_count]:
            # rect_ratio からマージン分を減算
            x, y, w, h = blk.init_rect_ratio[0:4]
            x += margin_ratio_x / 2
            y += margin_ratio_y / 2
            w -= margin_ratio_x
            h -= margin_ratio_y
            x = x * side_scale + side_margin
            y = y * top_scale + top_under_margin
            w = w * side_scale
            h = h * top_scale
            blk.rect_ratio = (x, y, w, h)
            item = PhotoBlockItem(blk, scene_rect, self)
            self.scene().addItem(item)
            self._photo_block_items.append(item)

        if fit_window:
            self.fitInView(scene_rect, QtCore.Qt.KeepAspectRatio)

    def export_image(self, out_path):
        # type: (str) -> None
        self.export_flag = True
        # self.export_scene(out_path)
        self.draw_layout(True)
        for item in  self.scene().items():
            if isinstance(item, PhotoBlockItem):
                item._block.update_image()
            item.setSelected(False)
        self.clear_selection()
        self.clear_selection(drop=True)

        img = QtGui.QImage(int(self.export_width), int(self.export_height), QtGui.QImage.Format_RGB32)
        img.fill(self.bg_color)
        dots_per_meter = int(self.dpi / 0.0254)
        img.setDotsPerMeterX(dots_per_meter)
        img.setDotsPerMeterY(dots_per_meter)

        painter = QtGui.QPainter(img)
        self.scene().render(painter)
        painter.end()
        img.save(out_path)
        self.export_flag = False
        self.draw_layout(fit_window=False)

    def rotate_selected_image(self, rotation_degree):
        # type: (int) -> None
        """選択中の画像を回転
        """
        photo_brock_item = self.get_selected_photo_brock_item()
        if photo_brock_item:
            blk = photo_brock_item._block
            if blk.preview_img:
                blk.preview_img = blk.preview_img.rotate(rotation_degree, expand=True)
            if blk.preview_img:
                blk.preview_img = blk.preview_img.rotate(rotation_degree, expand=True)
            blk.rotation = (blk.rotation - rotation_degree) % 360
            photo_brock_item.update()

    def clear_selection(self, drop=False):
        # type: (bool) -> None
        """選択状態をクリア"""
        for item in self._photo_block_items:
            if drop and item._is_drop_target:
                item._is_drop_target = False
                item.update()
            elif not drop and item._is_selected:
                item._is_selected = False
                item.update()

    def set_block_layout(self, layout_name, brock_ratio_list):
        # type: (str, list[list[float]]) -> None
        """レイアウトを読み込む"""
        for id, rect_ratio in enumerate(brock_ratio_list):
            if id >= len(self.blocks):
                self.blocks.append(PhotoInfo())
            self.blocks[id].update_rect_ratio(rect_ratio)
            self.blocks[id].update_attr_from_layout(layout_name)
        self.block_count = len(brock_ratio_list)

    # =================================
    # Context
    # =================================
    def context(self):
        # type: (str) -> list[dict]
        """現在のレイアウトをJSON保存"""
        layout_data = []
        for blk in self.blocks[:self.block_count]:
            layout_data.append({
                "rect_ratio": blk.init_rect_ratio,
                "offset_x": blk.offset_x,
                "offset_y": blk.offset_y,
                "scale": blk.scale,
                "rotation": blk.rotation,
                "file_path": blk.image_path,
            })
        return layout_data

    def set_context(self, context):
        # type: (list[dict]) -> None
        """JSONレイアウトを読み込み"""
        # self.block_count = len(context)
        for id, blk_data in enumerate(context):
            if id >= len(self.blocks):
                self.blocks.append(PhotoInfo())
            blk = self.blocks[id]
            blk.update_rect_ratio(blk_data.get("rect_ratio", (0.0, 0.0, 1.0, 1.0)))
            blk.offset_x = blk_data.get("offset_x", 0)
            blk.offset_y = blk_data.get("offset_y", 0)
            blk.scale = blk_data.get("scale", 1.0)
            blk.rotation = blk_data.get("rotation", 0)
            blk.image_path = blk_data.get("file_path", None)
            blk.update_image()
        self.draw_layout(fit_window=False)

    # =================================
    # Private Methods
    # =================================
    def _get_mouse_under_item(self):
        # type: () -> PhotoBlockItem | None
        """マウス下のアイテムを取得"""
        mouse_pos = self.mapFromGlobal(QtGui.QCursor.pos())
        scene_mouse_pos = self.mapToScene(mouse_pos)
        items = self.scene().items(scene_mouse_pos)
        for item in items:
            if isinstance(item, PhotoBlockItem):
                return item
        return None

    # ==========================
    # 右クリックメニュー
    # ==========================
    def show_context_menu(self, pos):
        # type: (QtCore.QPointF) -> None
        """右クリックメニュー表示
        """
        under_item = self._get_mouse_under_item()  # type: PhotoBlockItem | None
        menu = QtWidgets.QMenu(self)
        right_rotate_action = QtGui.QAction("右 90°回転")
        left_rotate_action = QtGui.QAction("左 90°回転")
        reset_action = QtGui.QAction("フィット")
        clear_image_action = QtGui.QAction("画像をクリア")

        if under_item:
            menu.addAction(right_rotate_action)
            menu.addAction(left_rotate_action)
            menu.addAction(reset_action)
            menu.addSeparator()
            menu.addAction(clear_image_action)

        menu.addSeparator()
        # a3_preview_action = menu.addAction("A3 プレビュー(等倍表示)")
        # a4_preview_action = menu.addAction("A4 プレビュー(等倍表示)")
        preview_size_action = menu.addAction("印刷サイズで画面に表示する")
        fit_window_action = menu.addAction("Windowサイズにフィットさせる")
        menu.addSeparator()
        clear_duplicate_images_action = menu.addAction("重複している画像をクリア")
        clear_all_image_action = menu.addAction("全ての画像をクリア")

        action = menu.exec(self.mapToGlobal(pos))

        if action == right_rotate_action:
            under_item._block.rotation = (under_item._block.rotation + 90) % 360
            under_item.update()
        elif action == left_rotate_action:
            under_item._block.rotation = (under_item._block.rotation - 90) % 360
            under_item.update()
        elif action == reset_action:
            under_item._block.offset_x = 0
            under_item._block.offset_y = 0
            under_item._block.scale = 1.0
            if under_item._block.rotation not in [0, 180]:
                under_item._block.scale = under_item._block.rot_90_scale
            under_item._block.update_image()
            under_item.update()
        elif action == clear_image_action:
            under_item._block.image_path = None
            under_item._block.preview_img = None
            under_item._block.full_img = None
            under_item.update()
        elif action == preview_size_action:
            set_canvas_scale = self.export_width / PREVIEW_CANVAS_WIDTH
            screen = screen_at_mouse()
            screen_dpi = screen.physicalDotsPerInch()  # 例: 96, 110, 144, 218など
            canvas_dpi = self.dpi
            # if not canvas_dpi:
            #     # screen = QtWidgets.QApplication.primaryScreen()
            #     canvas_dpi = get_a3_dpi(self.export_width)
            #     if action == a4_preview_action:
            #         canvas_dpi = get_a4_dpi(self.export_width)
            # 一旦スケールをリセットする
            self.resetTransform()
            self.scale(set_canvas_scale*screen_dpi/canvas_dpi, set_canvas_scale*screen_dpi/canvas_dpi)
        elif action is fit_window_action:
            self.fit_window_size()
        elif action is clear_all_image_action:
            # 確認用のDialogを出す
            reply = QtWidgets.QMessageBox.question(
                self, "全ての画像をクリア",
                "本当に全ての画像をクリアしますか？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                for blk in self.blocks:
                    blk.image_path = None
                    blk.preview_img = None
                    blk.full_img = None
            self.draw_layout()
        elif action is clear_duplicate_images_action:
            seen_paths = set()
            for blk in self.blocks:
                if blk.image_path and os.path.abspath(blk.image_path) in seen_paths:
                    blk.image_path = None
                    blk.preview_img = None
                    blk.full_img = None
                elif blk.image_path:
                    seen_paths.add(os.path.abspath(blk.image_path))
            self.draw_layout()

    def fit_horizontal_window_size(self):
        # type: () -> None
        """Canvasのサイズを横フィットさせる"""
        view_width = self.viewport().width()
        scale_factor = view_width / self.canvas_width
        self.resetTransform()
        self.scale(scale_factor, scale_factor)

    def fit_window_size(self):
        # type: () -> None
        """Windowサイズにフィットさせる"""
        self.fitInView(self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio)

    # =================================
    # Override Methods
    # =================================
    def wheelEvent(self, event):
        # type: (QtGui.QGraphicsSceneWheelEvent) -> None
        """ホイールでスケール"""
        if not self.wheel_zoom_flag:
            return QtWidgets.QGraphicsView.wheelEvent(self, event)
        if bool(event.modifiers() & QtCore.Qt.ControlModifier):
            return QtWidgets.QGraphicsView.wheelEvent(self, event)
        delta = 0
        # Qt6 では angleDelta が無いので、代替で delta() を使用
        if hasattr(event, "delta"):
            delta = event.delta()
        elif hasattr(event, "angleDelta"):  # 念のためPyQt互換
            delta = event.angleDelta().y()
        scale_factor = 1.05 if delta > 0 else 0.95
        # マウスの位置を中心にスケール
        # mouse_pos = event.position().toPoint()
        # scene_mouse_pos = self.mapToScene(mouse_pos)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.scale(scale_factor, scale_factor)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        # return QtWidgets.QGraphicsView.wheelEvent(self, event)

    def mousePressEvent(self, event):
        # type: (QtGui.QMouseEvent) -> None
        """マウスプレスでパン開始
        """
        self.clear_selection()
        self.clear_selection(drop=True)
        if event.button() == QtCore.Qt.MiddleButton:
            self._pan_start_pos = event.pos()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        # under_item = self._get_mouse_under_item()
        # if under_item: print(under_item._block.image_path)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # type: (QtGui.QMouseEvent) -> None
        """マウス移動でパン"""
        if event.buttons() & QtCore.Qt.MiddleButton:
            delta = event.pos() - self._pan_start_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan_start_pos = event.pos()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # type: (QtGui.QMouseEvent) -> None
        """マウスリリースでパン終了"""
        if event.button() == QtCore.Qt.MiddleButton:
            self.setCursor(QtCore.Qt.ArrowCursor)
        self.clear_selection(drop=True)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        # type: (QtGui.QKeyEvent) -> None
        """Fキーでフィット表示"""
        if event.key() == QtCore.Qt.Key_F:
            self.fit_window_size()
        elif event.key() == QtCore.Qt.Key_Plus:
            item = self.get_selected_photo_brock_item()
            item._block.rotation = (item._block.rotation + 90) % 360
            item.update()
        elif event.key() == QtCore.Qt.Key_Minus:
            item = self.get_selected_photo_brock_item()
            item._block.rotation = (item._block.rotation - 90) % 360
            item.update()
        return super().keyPressEvent(event)

    def dropEvent(self, event):
        global DRAG_ITEM
        # === 外部画像ファイル ===
        if event.mimeData().hasUrls():
            if len(event.mimeData().urls()) == 1:
                under_mouse_item = self._get_mouse_under_item()
                path = event.mimeData().urls()[0].toLocalFile()
                if os.path.isfile(path) and path.lower().endswith(IMAGE_EXTS):
                    under_mouse_item._block.image_path = path
                    under_mouse_item._block.update_image()
                    under_mouse_item.update()
                    self.clear_selection()
                    self.clear_selection(drop=True)
                    under_mouse_item._is_selected = True
            else:
                image_path_list = [url.toLocalFile() for url in event.mimeData().urls()]
                image_path_list = [path for path in image_path_list
                                   if os.path.isfile(path) and path.lower().endswith(IMAGE_EXTS)]
                under_mouse_item = self._get_mouse_under_item()
                for index, image_path in enumerate(image_path_list):
                    skip_flag = under_mouse_item is not None
                    for item in self._photo_block_items:
                        if skip_flag and item is under_mouse_item:
                            if index == 0:
                                item._block.image_path = image_path
                                item._block.update_image()
                                item.update()
                                break
                            skip_flag = False
                            continue
                        if skip_flag:
                            continue
                        if item._block.image_path:
                            continue
                        item._block.image_path = image_path
                        item._block.update_image()
                        item.update()
                        break

            event.acceptProposedAction()
        self.update()
        self.clear_selection(drop=True)
        super().dropEvent(event)


def get_a4_dpi(width_px):
    """A4ピクセルサイズからDPIを計算"""
    width_in = 297 / 25.4  # 297x210
    dpi_x = width_px / width_in
    return dpi_x


def get_a3_dpi(width_px):
    """A4ピクセルサイズからDPIを計算"""
    width_in = 297 / 25.4  # 297x210
    dpi_x = width_px / width_in
    return dpi_x / 1.41


def screen_at_mouse():
    # type: () -> QtGui.QScreen | None
    """マウスが乗っているスクリーンを取得する"""
    pos = QtGui.QCursor.pos()  # マウスのグローバル座標 (QPoint)
    for s in QtWidgets.QApplication.screens():
        geo = s.geometry()  # QRect: スクリーンの位置とサイズ
        if geo.contains(pos):
            return s
    return QtWidgets.QApplication.primaryScreen()  # マウスがどのスクリーンにも乗っていない場合
