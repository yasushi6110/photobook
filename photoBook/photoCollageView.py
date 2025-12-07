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
        self.block = block
        self.parent_view = parent_view  # type: PhotoCollageView
        self._dragging = False
        self._ctrl_drag = False
        self._last_mouse_pos = QtCore.QPointF()
        self.update_from_block(scene_rect)
        self.setup_gui()

    def setup_gui(self):
        # type: () -> None
        """GUI設定"""
        self.setAcceptDrops(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)

    def update_from_block(self, scene_rect):
        # type: (str) -> None
        """ブロック情報から矩形を更新
        """
        x = scene_rect.width() * self.block.rect_ratio[0]
        y = scene_rect.height() * self.block.rect_ratio[1]
        w = scene_rect.width() * self.block.rect_ratio[2]
        h = scene_rect.height() * self.block.rect_ratio[3]
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

        render_image = self.block.preview_img
        if self.parent_view.render_flag:
            render_image = self.block.full_img

        if render_image:
            img = render_image.convert("RGBA")
            iw, ih = img.size

            # スケール倍率を計算
            ratio = max(self.rect.width() / iw, self.rect.height() / ih) * self.block.scale + 0.005

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
            img = img.rotate(-self.block.rotation, expand=True, resample=Image.BICUBIC)

            # Pillow → QPixmap 変換
            qimg = QtGui.QImage(img.tobytes("raw", "RGBA"), img.width, img.height, QtGui.QImage.Format_RGBA8888)
            pix = QtGui.QPixmap.fromImage(qimg)

            # 中心配置 + offset
            cx = round(self.rect.center().x() - pix.width() / 2 + self.block.offset_x)
            cy = round(self.rect.center().y() - pix.height() / 2 + self.block.offset_y)
            painter.drawPixmap(QtCore.QPointF(cx, cy), pix)
        else:
            # 画像を保存する場合は、BGカラーで塗りつぶす
            if self.parent_view.render_flag:
                painter.fillRect(self.rect, self.parent_view.bg_color)
            else:
                painter.fillRect(self.rect, QtGui.QColor(*self.block.color))

        # =============================
        # 選択していた場合の枠線の描画
        # =============================
        if self.isSelected():
            painter.setRenderHint(QtGui.QPainter.Antialiasing, False)  # アンチエイリアスを無効化
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 0), 10))
        else:
            painter.setPen(QtCore.Qt.NoPen)  # ペンを無効化
        painter.drawRect(self.rect)
        painter.restore()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._dragging = True
            self._ctrl_drag = bool(event.modifiers() & QtCore.Qt.ControlModifier)
            self._last_mouse_pos = event.scenePos()
            self.setSelected(True)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        delta = event.scenePos() - self._last_mouse_pos
        self._last_mouse_pos = event.scenePos()

        if self._ctrl_drag:
            # Ctrl+Drag → 内部画像移動
            self.block.offset_x += delta.x()
            self.block.offset_y += delta.y()
            self.update()
        else:
            # 通常ドラッグ → D&D入れ替え
            drag = QtGui.QDrag(self.parent_view)
            mime = QtCore.QMimeData()
            mime.setText(self.block.image_path or "")
            drag.setMimeData(mime)
            drag.exec(QtCore.Qt.MoveAction)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        # === 外部画像ファイル ===
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isfile(path) and path.lower().endswith(IMAGE_EXTS):
                    self.block.image_path = path
                    self.block.update_image()
                    self.update()
                    break
            event.acceptProposedAction()
            return

        # === 内部D&D（画像入れ替え）===
        if event.mimeData().hasText():
            src_path = event.mimeData().text()
            if not src_path:
                return
            for item in self.parent_view.scene().items():
                if isinstance(item, PhotoBlockItem) and item.block.image_path == src_path:
                    self.block.switch_status(item.block)
                    self.update()
                    item.update()
                    break
            event.acceptProposedAction()

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
                self.block.scale *= 1.05
            else:
                self.block.scale *= 0.95
            self.update()


class PhotoCollageView(QtWidgets.QGraphicsView):

    def __init__(self, layout_name, long_side_px=3508, portrait=True):
        super().__init__()
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setAcceptDrops(True)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)

        self.render_flag = False
        """Export時に高解像度画像を使用するかどうかのフラグ"""
        self.bg_color = QtGui.QColor("white")
        self.space_margin_px = 10
        self.top_under_margin_px = 10
        self.side_margin_px = 10
        self.portrait = portrait
        self.long_side_px = long_side_px
        self._update_canvas_size()
        self._image_path_cache = [None] * 500  # type: list[str]
        self.blocks = []  # type: list[PhotoInfo]
        self.block_count = 1
        self.dpi = None
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setTransform(QtGui.QTransform())  # スケールをリセット
        self.centerOn(0, 0)  # シーンの中心を初期化

        scene = QtWidgets.QGraphicsScene(self)
        self.setScene(scene)
        self.blocks = []
        self._load_layout(layout_name)
        self.draw_layout()

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    # =================================
    # Public Methods
    # =================================
    def get_selected_photo_brock_item(self):
        # type: () -> PhotoBlockItem
        for item in self.scene().items():
            if isinstance(item, PhotoBlockItem) and item.isSelected():
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

    def draw_layout(self, canvas_width=None, canvas_height=None):
        # type: (int ,int ) -> None
        """レイアウトを描画"""
        if not self.scene():
            return
        self.scene().clear()

        rate = self.canvas_height_px / self.canvas_width_px
        if not canvas_width and not canvas_height:
            canvas_width = PREVIEW_CANVAS_WIDTH
            canvas_height = int(canvas_width * rate)

        yohaku = 20000
        base_scene_rect = QtCore.QRectF(-yohaku, -yohaku, canvas_width+yohaku*2, canvas_height+yohaku*2)
        scene_rect = QtCore.QRectF(0, 0, canvas_width, canvas_height)

        self.scene().setSceneRect(scene_rect)
        self.setSceneRect(base_scene_rect)
        color = 160
        self.scene().setBackgroundBrush(QtGui.QColor(color, color, color, 255))
        # self.scene().setBackgroundBrush(QtGui.QBrush(self.bg_color))

        margin_ratio_x = margin_ratio_y = 0
        if self.space_margin_px > 0:
            margin_ratio_x = self.space_margin_px / self.canvas_width_px
            margin_ratio_y = self.space_margin_px / self.canvas_height_px

        side_margin = self.side_margin_px / self.canvas_width_px
        top_under_margin = self.top_under_margin_px / self.canvas_height_px
        side_scale = (1.0 - side_margin * 2.0)
        top_scale = (1.0 - top_under_margin * 2.0)

        # QGraphicsRectItemを作成
        rect_item = QtWidgets.QGraphicsRectItem(0, 0, canvas_width, canvas_height)

        # 色を設定
        brush = QtGui.QBrush(self.bg_color)
        rect_item.setBrush(brush)

        # シーンに追加
        self.scene().addItem(rect_item)

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

        # self.fitInView(scene_rect, QtCore.Qt.KeepAspectRatioByExpanding)
        self.fitInView(scene_rect, QtCore.Qt.KeepAspectRatio)

    def set_background_color(self, color):
        self.bg_color = color
        self.draw_layout()

    def export_image(self, out_path):
        # type: (str) -> None
        self.render_flag = True
        # self.export_scene(out_path)
        self.draw_layout(self.canvas_width_px, self.canvas_height_px)
        for item in  self.scene().items():
            if isinstance(item, PhotoBlockItem):
                item.block.update_image()
            item.setSelected(False)

        img = QtGui.QImage(int(self.canvas_width_px), int(self.canvas_height_px), QtGui.QImage.Format_RGB32)
        img.fill(self.bg_color)
        painter = QtGui.QPainter(img)
        self.scene().render(painter)
        painter.end()
        img.save(out_path)
        self.render_flag = False
        self.draw_layout()

    def set_margin(self, space_margin_px, top_under_margin_px, side_margin_px):
        self.space_margin_px = space_margin_px
        self.top_under_margin_px = top_under_margin_px
        self.side_margin_px = side_margin_px
        self.draw_layout()

    def set_canvas_size(self, width_px, height_px):
        self.canvas_height_px = height_px
        self.canvas_width_px = width_px
        self.draw_layout()

    def set_layout(self, layout_name):
        self._load_layout(layout_name)
        self.scene().clear()
        self.draw_layout()

    def rotate_selected_image(self, rotation_degree):
        # type: (int) -> None
        """選択中の画像を回転"""
        photo_brock_item = self.get_selected_photo_brock_item()
        if photo_brock_item:
            blk = photo_brock_item.block
            if blk.preview_img:
                blk.preview_img = blk.preview_img.rotate(rotation_degree, expand=True)
            if blk.preview_img:
                blk.preview_img = blk.preview_img.rotate(rotation_degree, expand=True)
            blk.rotation = (blk.rotation - rotation_degree) % 360
            photo_brock_item.update()

    # =================================
    # Context
    # =================================
    def context(self):
        # type: (str) -> None
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
        # type: (str) -> None
        """JSONレイアウトを読み込み"""
        self.block_count = len(context)
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
        self.draw_layout()

    # =================================
    # Private Methods
    # =================================
    def _update_canvas_size(self):
        a4_ratio = math.sqrt(2)
        if self.portrait:
            self.canvas_height_px = self.long_side_px
            self.canvas_width_px = int(self.long_side_px / a4_ratio)
        else:
            self.canvas_width_px = self.long_side_px
            self.canvas_height_px = int(self.long_side_px / a4_ratio)
        self.draw_layout()

    def _load_layout(self, layout_name):
        # type: (str) -> None
        """レイアウトを読み込む"""
        # if layout_name in SIZE_SWITCH_LAYOUT:
        #     self.portrait = True
        # self._update_canvas_size()

        for id, rect_ratio in enumerate(LAYOUT_PRESETS[layout_name]):
            if id >= len(self.blocks):
                self.blocks.append(PhotoInfo())
            self.blocks[id].update_rect_ratio(rect_ratio)
            self.blocks[id].update_attr_from_layout(layout_name)
        self.block_count = len(LAYOUT_PRESETS[layout_name])

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
        a3_preview_action = menu.addAction("A3 プレビュー(等倍表示)")
        a4_preview_action = menu.addAction("A4 プレビュー(等倍表示)")
        fit_window_action = menu.addAction("Windowサイズにフィット")

        action = menu.exec(self.mapToGlobal(pos))

        if action == right_rotate_action:
            under_item.block.rotation = (under_item.block.rotation + 90) % 360
        elif action == left_rotate_action:
            under_item.block.rotation = (under_item.block.rotation - 90) % 360
        elif action == reset_action:
            under_item.block.offset_x = 0
            under_item.block.offset_y = 0
            under_item.block.scale = 1.0
            if under_item.block.rotation not in [0, 180]:
                under_item.block.scale = under_item.block.rot_90_scale
            under_item.block.update_image()
        elif action == clear_image_action:
            under_item.block.image_path = None
            under_item.block.preview_img = None
            under_item.block.full_img = None
        elif action in [a3_preview_action, a4_preview_action]:
            if not self.dpi:
                screen = QtWidgets.QApplication.primaryScreen()
                dpi = screen.physicalDotsPerInch()  # 例: 96, 110, 144, 218など
                set_canvas_scale = self.canvas_width_px / PREVIEW_CANVAS_WIDTH
                canvas_dpi = get_a3_dpi(self.canvas_width_px)
                if action == a4_preview_action:
                    canvas_dpi = get_a4_dpi(self.canvas_width_px)
                # 一旦スケールをリセットする
                self.resetTransform()
                self.scale(set_canvas_scale*dpi/canvas_dpi, set_canvas_scale*dpi/canvas_dpi)
        elif action is fit_window_action:
            self.fitInView(self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio)

        under_item.update()

    # =================================
    # Override Methods
    # =================================
    def wheelEvent(self, event):
        # type: (QtGui.QGraphicsSceneWheelEvent) -> None
        """ホイールでスケール"""
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
        """マウスプレスでパン開始"""
        if event.button() == QtCore.Qt.MiddleButton:
            self._pan_start_pos = event.pos()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
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
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        # type: (QtGui.QKeyEvent) -> None
        """Fキーでフィット表示"""
        if event.key() == QtCore.Qt.Key_F:
            self.fitInView(self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio)
        elif event.key() == QtCore.Qt.Key_Plus:
            item = self.get_selected_photo_brock_item()
            item.block.rotation = (item.block.rotation + 90) % 360
            item.update()
        elif event.key() == QtCore.Qt.Key_Minus:
            item = self.get_selected_photo_brock_item()
            item.block.rotation = (item.block.rotation - 90) % 360
            item.update()
        return super().keyPressEvent(event)

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
