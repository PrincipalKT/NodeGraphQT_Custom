#!/usr/bin/python
from collections import OrderedDict

from Qt import QtCore, QtGui, QtWidgets

from NodeGraphQt.constants import (ICON_NODE_BASE, ITEM_CACHE_MODE, Z_VAL_NODE,
                                   LayoutDirectionEnum, NodeEnum, PortEnum,
                                   PortTypeEnum)
from NodeGraphQt.errors import NodeWidgetError
from NodeGraphQt.qgraphics.node_abstract import AbstractNodeItem
from NodeGraphQt.qgraphics.node_overlay_disabled import XDisabledItem
from NodeGraphQt.qgraphics.node_text_item import NodeTextItem
from NodeGraphQt.qgraphics.port import CustomPortItem, PortItem
import weakref


class NodeItem(AbstractNodeItem):
    """
    Base Node item.

    Args:
        name (str): name displayed on the node.
        parent (QtWidgets.QGraphicsItem): parent item.
    """

    def __init__(self, name='node', parent=None):
        super(NodeItem, self).__init__(name, parent)
        pixmap = QtGui.QPixmap(ICON_NODE_BASE)
        if pixmap.size().height() > NodeEnum.ICON_SIZE.value:
            pixmap = pixmap.scaledToHeight(
                NodeEnum.ICON_SIZE.value,
                QtCore.Qt.SmoothTransformation
            )
        self._properties['icon'] = ICON_NODE_BASE
        self._icon_item = QtWidgets.QGraphicsPixmapItem(pixmap, self)
        self._icon_item.setTransformationMode(QtCore.Qt.SmoothTransformation)
        self._text_item = NodeTextItem(self.name, self)
        self._x_item = XDisabledItem(self, 'DISABLED')
        self._input_items = OrderedDict()
        self._output_items = OrderedDict()
        self._widgets = OrderedDict()
        self._proxy_mode = False
        self._proxy_mode_threshold = 70
        self._flipped_x = False
        self._flipped_y = False


    
    def set_base_node_ref(self,base_node):
        # to be able to call methods on the base node
        # WD-43 : I created this for display name feature 
        # so that NodeTextItem can call base node functions
        self._base_node_weak_ref = weakref.proxy(base_node)

    def get_base_node_ref(self):
        return self._base_node_weak_ref
        

    def post_init(self, viewer, pos=None):
        """
        Called after node has been added into the scene.

        Args:
            viewer (NodeGraphQt.widgets.viewer.NodeViewer): main viewer
            pos (tuple): the cursor pos if node is called with tab search.
        """
        if self.layout_direction == LayoutDirectionEnum.VERTICAL.value:
            font = QtGui.QFont()
            font.setPointSize(15)
            self.text_item.setFont(font)

            # hide port text items for vertical layout.
            if self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
                for text_item in self._input_items.values():
                    text_item.setVisible(False)
                for text_item in self._output_items.values():
                    text_item.setVisible(False)

    def _paint_horizontal(self, painter, option, widget):
        painter.save()
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.NoBrush)

        # base background.
        margin = 1.0
        rect = self.boundingRect()
        rect = QtCore.QRectF(rect.left() + margin,
                             rect.top() + margin,
                             max(0.0, rect.width() - (margin * 2)),
                             max(0.0, rect.height() - (margin * 2)))

        radius = min(4.0, rect.width() / 2.0, rect.height() / 2.0)
        if radius < 0:
            radius = 0
        painter.setBrush(QtGui.QColor(*self.color))
        painter.drawRoundedRect(rect, radius, radius)

        # light overlay on background when selected.
        if self.selected:
            painter.setBrush(QtGui.QColor(*NodeEnum.SELECTED_COLOR.value))
            painter.drawRoundedRect(rect, radius, radius)

        # node name background.
        if self._text_item.isVisible() and self._text_item.toPlainText():
            padding = 3.0, 2.0
            text_rect = self._text_item.boundingRect()
            text_w = max(0.0, rect.width() - padding[0] - margin)
            text_h = max(0.0, text_rect.height() - (padding[1] * 2))
            if text_w > 0 and text_h > 0:
                text_rect = QtCore.QRectF(text_rect.x() + padding[0],
                                          rect.y() + padding[1],
                                          text_w,
                                          text_h)
                if self.selected:
                    painter.setBrush(QtGui.QColor(*NodeEnum.SELECTED_COLOR.value))
                else:
                    painter.setBrush(QtGui.QColor(0, 0, 0, 80))
                r = min(3.0, text_w / 2.0, text_h / 2.0)
                painter.drawRoundedRect(text_rect, r, r)

        # node border
        if self.selected:
            border_width = 1.2
            border_color = QtGui.QColor(
                *NodeEnum.SELECTED_BORDER_COLOR.value
            )
        else:
            border_width = 0.8
            border_color = QtGui.QColor(*self.border_color)

        border_rect = QtCore.QRectF(rect.left(), rect.top(),
                                    rect.width(), rect.height())

        pen = QtGui.QPen(border_color, border_width)
        pen.setCosmetic(self.viewer().get_zoom() < 0.0)
        path = QtGui.QPainterPath()
        path.addRoundedRect(border_rect, radius, radius)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(pen)
        painter.drawPath(path)

        painter.restore()

    def _paint_vertical(self, painter, option, widget):
        painter.save()
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.NoBrush)

        # base background.
        margin = 1.0
        rect = self.boundingRect()
        rect = QtCore.QRectF(rect.left() + margin,
                             rect.top() + margin,
                             max(0.0, rect.width() - (margin * 2)),
                             max(0.0, rect.height() - (margin * 2)))

        radius = min(4.0, rect.width() / 2.0, rect.height() / 2.0)
        if radius < 0:
            radius = 0
        painter.setBrush(QtGui.QColor(*self.color))
        painter.drawRoundedRect(rect, radius, radius)

        # light overlay on background when selected.
        if self.selected:
            painter.setBrush(
                QtGui.QColor(*NodeEnum.SELECTED_COLOR.value)
            )
            painter.drawRoundedRect(rect, radius, radius)

        # top & bottom edge background.
        padding = 2.0
        height = 10
        if rect.height() > (height * 2 + padding * 2) and (rect.width() - (padding * 2)) > 0:
            if self.selected:
                painter.setBrush(QtGui.QColor(*NodeEnum.SELECTED_COLOR.value))
            else:
                painter.setBrush(QtGui.QColor(0, 0, 0, 80))
            for y in [rect.y() + padding, rect.height() - height - 1]:
                edge_rect = QtCore.QRectF(rect.x() + padding, y,
                                         rect.width() - (padding * 2), height)
                painter.drawRoundedRect(edge_rect, 3.0, 3.0)

        # node border
        border_width = 0.8
        border_color = QtGui.QColor(*self.border_color)
        if self.selected:
            border_width = 1.2
            border_color = QtGui.QColor(
                *NodeEnum.SELECTED_BORDER_COLOR.value
            )
        border_rect = QtCore.QRectF(rect.left(), rect.top(),
                                    rect.width(), rect.height())

        pen = QtGui.QPen(border_color, border_width)
        pen.setCosmetic(self.viewer().get_zoom() < 0.0)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(pen)
        painter.drawRoundedRect(border_rect, radius, radius)

        painter.restore()

    @property
    def flipped_x(self):
        return getattr(self, '_flipped_x', False)

    @flipped_x.setter
    def flipped_x(self, value):
        val = bool(value)
        changed = (getattr(self, '_flipped_x', False) != val)
        self._flipped_x = val
        if changed:
            if hasattr(self, 'align_ports'):
                self.align_ports()
            self.update()

    @property
    def flipped_y(self):
        return getattr(self, '_flipped_y', False)

    @flipped_y.setter
    def flipped_y(self, value):
        val = bool(value)
        changed = (getattr(self, '_flipped_y', False) != val)
        self._flipped_y = val
        if changed:
            if hasattr(self, 'align_ports'):
                self.align_ports()
            self.update()

    def paint(self, painter, option, widget):
        """
        Draws the node base not the ports.

        Args:
            painter (QtGui.QPainter): painter used for drawing the item.
            option (QtGui.QStyleOptionGraphicsItem):
                used to describe the parameters needed to draw.
            widget (QtWidgets.QWidget): not used.
        """
        self.auto_switch_mode()
        flipped_x = getattr(self, 'flipped_x', False)
        flipped_y = getattr(self, 'flipped_y', False)
        if flipped_x or flipped_y:
            painter.save()
            cx = self._width / 2.0
            cy = self._height / 2.0
            painter.translate(cx, cy)
            painter.scale(-1.0 if flipped_x else 1.0, -1.0 if flipped_y else 1.0)
            painter.translate(-cx, -cy)

        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._paint_horizontal(painter, option, widget)
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            self._paint_vertical(painter, option, widget)
        else:
            raise RuntimeError('Node graph layout direction not valid!')

        if flipped_x or flipped_y:
            painter.restore()

    def mousePressEvent(self, event):
        """
        Re-implemented to ignore event if LMB is over port collision area.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): mouse event.
        """
        if event.button() == QtCore.Qt.LeftButton:
            for p in self._input_items.keys():
                if p.hovered:
                    event.ignore()
                    return
            for p in self._output_items.keys():
                if p.hovered:
                    event.ignore()
                    return
        super(NodeItem, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Re-implemented to ignore event if Alt modifier is pressed.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): mouse event.
        """
        if event.modifiers() == QtCore.Qt.AltModifier:
            event.ignore()
            return
        super(NodeItem, self).mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """
        Re-implemented to emit "node_double_clicked" signal.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): mouse event.
        """
        if event.button() == QtCore.Qt.LeftButton:
            if not self.disabled:
                # enable text item edit mode.
                items = self.scene().items(event.scenePos())
                if self._text_item in items:
                    self._text_item.set_editable(True)
                    self._text_item.setFocus()
                    event.ignore()
                    return

            viewer = self.viewer()
            if viewer:
                viewer.node_double_clicked.emit(self.id)
        super(NodeItem, self).mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        """
        Re-implemented to update pipes on selection changed.

        Args:
            change:
            value:
        """
        if change == QtWidgets.QGraphicsItem.ItemSelectedChange and self.scene():
            self.reset_pipes()
            if value:
                self.highlight_pipes()
            self.setZValue(Z_VAL_NODE)
            if not self.selected:
                self.setZValue(Z_VAL_NODE + 1)

        return super(NodeItem, self).itemChange(change, value)

    def _tooltip_disable(self, state):
        """
        Updates the node tooltip when the node is enabled/disabled.

        Args:
            state (bool): node disable state.
        """
        tooltip = '<b>{}</b>'.format(self.name)
        if state:
            tooltip += ' <font color="red"><b>(DISABLED)</b></font>'
        tooltip += '<br/>{}<br/>'.format(self.type_)
        self.setToolTip(tooltip)

    def _set_base_size(self, add_w=0.0, add_h=0.0):
        """
        Sets the initial base size for the node.

        Args:
            add_w (float): add additional width.
            add_h (float): add additional height.
        """
        calc_w, calc_h = self.calc_size(add_w, add_h)
        if self._custom_width is not None:
            self._width = self._custom_width
        else:
            self._width = max(calc_w, NodeEnum.WIDTH.value)

        if self._custom_height is not None:
            self._height = self._custom_height
        else:
            self._height = max(calc_h, NodeEnum.HEIGHT.value)

    def _set_text_color(self, color):
        """
        set text color.

        Args:
            color (tuple): color value in (r, g, b, a).
        """
        text_color = QtGui.QColor(*color)
        for port, text in self._input_items.items():
            text.setDefaultTextColor(text_color)
        for port, text in self._output_items.items():
            text.setDefaultTextColor(text_color)
        self._text_item.setDefaultTextColor(text_color)

    def activate_pipes(self):
        """
        active pipe color.
        """
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes:
                pipe.activate()

    def highlight_pipes(self):
        """
        Highlight pipe color.
        """
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes:
                pipe.highlight()

    def reset_pipes(self):
        """
        Reset all the pipe colors.
        """
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes:
                pipe.reset()

    def _calc_size_horizontal(self):
        # width, height from node name text.
        text_w = self._text_item.boundingRect().width()
        text_h = self._text_item.boundingRect().height()

        # width, height from node ports.
        port_width = 0.0
        p_input_text_width = 0.0
        p_output_text_width = 0.0
        p_input_height = 0.0
        p_output_height = 0.0
        for port, text in self._input_items.items():
            if not port.isVisible():
                continue
            if not port_width:
                port_width = port.boundingRect().width()
            t_width = text.boundingRect().width()
            if text.isVisible() and t_width > p_input_text_width:
                p_input_text_width = text.boundingRect().width()

            # flip logic
            if not port.flipped:
                p_input_height += port.boundingRect().height()
            else:
                p_output_height += port.boundingRect().height()
        for port, text in self._output_items.items():
            if not port.isVisible():
                continue
            if not port_width:
                port_width = port.boundingRect().width()
            t_width = text.boundingRect().width()
            if text.isVisible() and t_width > p_output_text_width:
                p_output_text_width = text.boundingRect().width()
            # flip logic
            if not port.flipped:
                p_output_height += port.boundingRect().height()
            else:
                p_input_height += port.boundingRect().height()

        port_text_width = p_input_text_width + p_output_text_width

        # width, height from node embedded widgets.
        widget_width = 0.0
        widget_height = 0.0
        for widget in self._widgets.values():
            if not widget.isVisible():
                continue
            w_width = widget.boundingRect().width()
            w_height = widget.boundingRect().height()
            if w_width > widget_width:
                widget_width = w_width
            widget_height += w_height

        side_padding = 0.0
        if all([widget_width, p_input_text_width, p_output_text_width]):
            port_text_width = max([p_input_text_width, p_output_text_width])
            port_text_width *= 2
        elif widget_width:
            side_padding = 10

        width = port_width + max([text_w, port_text_width]) + side_padding
        height = max([text_h, p_input_height, p_output_height, widget_height])
        if widget_width:
            # add additional width for node widget.
            width += widget_width
        if widget_height:
            # add bottom margin for node widget.
            height += 4.0
        height *= 1.05
        return width, height

    def _calc_size_vertical(self):
        p_input_width = 0.0
        p_output_width = 0.0
        p_input_height = 0.0
        p_output_height = 0.0
        for port in self._input_items.keys():
            if port.isVisible():
                p_input_width += port.boundingRect().width()
                if not p_input_height:
                    p_input_height = port.boundingRect().height()
        for port in self._output_items.keys():
            if port.isVisible():
                p_output_width += port.boundingRect().width()
                if not p_output_height:
                    p_output_height = port.boundingRect().height()

        widget_width = 0.0
        widget_height = 0.0
        for widget in self._widgets.values():
            if not widget.isVisible():
                continue
            if widget.boundingRect().width() > widget_width:
                widget_width = widget.boundingRect().width()
            widget_height += widget.boundingRect().height()

        width = max([p_input_width, p_output_width, widget_width])
        height = p_input_height + p_output_height + widget_height
        return width, height

    def calc_size(self, add_w=0.0, add_h=0.0):
        """
        Calculates the minimum node size.

        Args:
            add_w (float): additional width.
            add_h (float): additional height.

        Returns:
            tuple(float, float): width, height.
        """
        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            width, height = self._calc_size_horizontal()
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            width, height = self._calc_size_vertical()
        else:
            raise RuntimeError('Node graph layout direction not valid!')

        # additional width, height.
        width += add_w
        height += add_h
        return width, height

    def _align_icon_horizontal(self, h_offset, v_offset):
        icon_rect = self._icon_item.boundingRect()
        text_rect = self._text_item.boundingRect()
        x = self.boundingRect().left() + 2.0
        y = text_rect.center().y() - (icon_rect.height() / 2)
        self._icon_item.setPos(x + h_offset, y + v_offset)

    def _align_icon_vertical(self, h_offset, v_offset):
        center_y = self.boundingRect().center().y()
        icon_rect = self._icon_item.boundingRect()
        text_rect = self._text_item.boundingRect()
        x = self.boundingRect().right() + h_offset
        y = center_y - text_rect.height() - (icon_rect.height() / 2) + v_offset
        self._icon_item.setPos(x, y)

    def align_icon(self, h_offset=0.0, v_offset=0.0):
        """
        Align node icon to the default top left of the node.

        Args:
            v_offset (float): additional vertical offset.
            h_offset (float): additional horizontal offset.
        """
        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._align_icon_horizontal(h_offset, v_offset)
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            self._align_icon_vertical(h_offset, v_offset)
        else:
            raise RuntimeError('Node graph layout direction not valid!')

    def _align_label_horizontal(self, h_offset, v_offset):
        rect = self.boundingRect()
        text_rect = self._text_item.boundingRect()
        x = rect.center().x() - (text_rect.width() / 2)
        self._text_item.setPos(x + h_offset, rect.y() + v_offset)

    def _align_label_vertical(self, h_offset, v_offset):
        rect = self._text_item.boundingRect()
        x = self.boundingRect().right() + h_offset
        y = self.boundingRect().center().y() - (rect.height() / 2) + v_offset
        self.text_item.setPos(x, y)

    def align_label(self, h_offset=0.0, v_offset=0.0):
        """
        Center node label text to the top of the node.

        Args:
            v_offset (float): vertical offset.
            h_offset (float): horizontal offset.
        """
        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._align_label_horizontal(h_offset, v_offset)
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            self._align_label_vertical(h_offset, v_offset)
        else:
            raise RuntimeError('Node graph layout direction not valid!')

    def _align_widgets_horizontal(self, v_offset):
        if not self._widgets:
            return
        rect = self.boundingRect()
        y = rect.y() + v_offset
        inputs = [p for p in self.inputs if p.isVisible()]
        outputs = [p for p in self.outputs if p.isVisible()]
        for widget in self._widgets.values():
            if not widget.isVisible():
                continue
            widget_rect = widget.boundingRect()
            if not inputs:
                x = rect.left() + 10
                widget.widget().setTitleAlign('left')
            elif not outputs:
                x = rect.right() - widget_rect.width() - 10
                widget.widget().setTitleAlign('right')
            else:
                x = rect.center().x() - (widget_rect.width() / 2)
                widget.widget().setTitleAlign('center')
            widget.setPos(x, y)
            y += widget_rect.height()

    def _align_widgets_vertical(self, v_offset):
        if not self._widgets:
            return
        rect = self.boundingRect()
        y = rect.center().y() + v_offset
        widget_height = 0.0
        for widget in self._widgets.values():
            if not widget.isVisible():
                continue
            widget_rect = widget.boundingRect()
            widget_height += widget_rect.height()
        y -= widget_height / 2

        for widget in self._widgets.values():
            if not widget.isVisible():
                continue
            widget_rect = widget.boundingRect()
            x = rect.center().x() - (widget_rect.width() / 2)
            widget.widget().setTitleAlign('center')
            widget.setPos(x, y)
            y += widget_rect.height()

    def align_widgets(self, v_offset=0.0):
        """
        Align node widgets to the default center of the node.

        Args:
            v_offset (float): vertical offset.
        """
        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._align_widgets_horizontal(v_offset)
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            self._align_widgets_vertical(v_offset)
        else:
            raise RuntimeError('Node graph layout direction not valid!')

    def _calculate_port_text_pos(self, port, text, width, height, gap=3.0):
        pos_dir = getattr(port, 'label_pos', 'AUTO')
        if pos_dir is None:
            pos_dir = 'AUTO'
        flipped_x = getattr(self, 'flipped_x', False)
        flipped_y = getattr(self, 'flipped_y', False)

        if pos_dir != 'AUTO':
            if flipped_x:
                if 'L' in pos_dir and 'R' not in pos_dir:
                    pos_dir = pos_dir.replace('L', 'R')
                elif 'R' in pos_dir and 'L' not in pos_dir:
                    pos_dir = pos_dir.replace('R', 'L')
            if flipped_y:
                if 'T' in pos_dir and 'B' not in pos_dir:
                    pos_dir = pos_dir.replace('T', 'B')
                elif 'B' in pos_dir and 'T' not in pos_dir:
                    pos_dir = pos_dir.replace('B', 'T')

        # Center of the visual port circle in parent (NodeItem) coordinates
        cx = port.x() + port.boundingRect().width() / 2.0
        cy = port.y() + port.boundingRect().height() / 2.0

        # Visual circle radius (PortItem draws circle with size / 1.8)
        rx = getattr(port, 'circle_radius', None)
        if rx is None:
            rx = getattr(port, '_width', 22.0) / 1.8 / 2.0
        ry = rx

        # Visual outer edges of the port circle
        circle_left = cx - rx
        circle_right = cx + rx
        circle_top = cy - ry
        circle_bottom = cy + ry

        txt_rect = text.boundingRect()
        tw = txt_rect.width()
        th = txt_rect.height()

        # 45-degree diagonal offset from center to circle perimeter
        diag_x = rx * 0.7071
        diag_y = ry * 0.7071

        if pos_dir in ('T', 'TOP'):
            return cx - tw / 2.0, circle_top - th - gap
        elif pos_dir in ('B', 'BOTTOM'):
            return cx - tw / 2.0, circle_bottom + gap
        elif pos_dir in ('L', 'LEFT'):
            return circle_left - tw - gap, cy - th / 2.0
        elif pos_dir in ('R', 'RIGHT'):
            return circle_right + gap, cy - th / 2.0
        elif pos_dir in ('TL', 'TOPLEFT'):
            return (cx - diag_x) - tw - gap, (cy - diag_y) - th - gap
        elif pos_dir in ('TR', 'TOPRIGHT'):
            return (cx + diag_x) + gap, (cy - diag_y) - th - gap
        elif pos_dir in ('BL', 'BOTTOMLEFT'):
            return (cx - diag_x) - tw - gap, (cy + diag_y) + gap
        elif pos_dir in ('BR', 'BOTTOMRIGHT'):
            return (cx + diag_x) + gap, (cy + diag_y) + gap
        else:  # 'AUTO'
            if port.has_custom_pos():
                if cx <= width / 2.0:
                    return circle_right + gap, cy - th / 2.0
                else:
                    return circle_left - tw - gap, cy - th / 2.0
            else:
                if port.port_type == PortTypeEnum.IN.value:
                    if getattr(port, 'flipped', False) != flipped_x:
                        return circle_left - tw - gap, cy - th / 2.0
                    else:
                        return circle_right + gap, cy - th / 2.0
                else:
                    if getattr(port, 'flipped', False) != flipped_x:
                        return circle_right + gap, cy - th / 2.0
                    else:
                        return circle_left - tw - gap, cy - th / 2.0

    def _align_ports_horizontal(self, v_offset):
        width = self._width
        gap = 3.0
        spacing = 1

        flipped_x = getattr(self, 'flipped_x', False)
        flipped_y = getattr(self, 'flipped_y', False)

        # Position custom-positioned ports (origin at bottom-left: (0, 0))
        for port in list(self.inputs) + list(self.outputs):
            if not port.isVisible():
                continue
            if port.has_custom_pos():
                port_width = port.boundingRect().width()
                port_height = port.boundingRect().height()
                # Origin at bottom-left:
                # port.port_x: distance from left edge (0 to width)
                # port.port_y: distance from bottom edge (0 to height)
                eff_x = (width - port.port_x) if flipped_x else port.port_x
                eff_y = (self._height - port.port_y) if flipped_y else port.port_y
                qt_x = eff_x
                qt_y = self._height - eff_y
                port.setPos(qt_x - (port_width / 2.0), qt_y - (port_height / 2.0))

                text = self.get_input_text_item(port) if port.port_type == PortTypeEnum.IN.value else self.get_output_text_item(port)
                if text and text.isVisible():
                    txt_x, txt_y = self._calculate_port_text_pos(port, text, width, self._height, gap=gap)
                    text.setPos(txt_x, txt_y)

        inputs_unflipped = [p for p in self.inputs if p.isVisible() and (getattr(p, 'flipped', False) == flipped_x) and not p.has_custom_pos()]
        inputs_flipped = [p for p in self.inputs if p.isVisible() and (getattr(p, 'flipped', False) != flipped_x) and not p.has_custom_pos()]
        outputs_unflipped = [p for p in self.outputs if p.isVisible() and (getattr(p, 'flipped', False) == flipped_x) and not p.has_custom_pos()]
        outputs_flipped = [p for p in self.outputs if p.isVisible() and (getattr(p, 'flipped', False) != flipped_x) and not p.has_custom_pos()]
        if not flipped_y:
            inputs_unflipped.reverse()
            inputs_flipped.reverse()
            outputs_unflipped.reverse()
            outputs_flipped.reverse()
        port_y_left = v_offset
        port_y_right = v_offset
        while inputs_flipped or inputs_unflipped or outputs_flipped or outputs_unflipped: 
            layer_left_pos_occupied = False
            layer_right_pos_occupied = False
            if inputs_unflipped and not layer_left_pos_occupied:
                port = inputs_unflipped.pop()
                text = self.get_input_text_item(port)
                port_width = port.boundingRect().width()
                port_height = port.boundingRect().height()
                port_x = (port_width / 2) * -1
                port.setPos(port_x, port_y_left)
                if text and text.isVisible():
                    txt_x, txt_y = self._calculate_port_text_pos(port, text, width, self._height, gap=gap)
                    text.setPos(txt_x, txt_y)
                layer_left_pos_occupied = True
                port_y_left += port_height + spacing
            
            if outputs_flipped and not layer_left_pos_occupied:
                port = outputs_flipped.pop()
                text = self.get_output_text_item(port)
                port_width = port.boundingRect().width()
                port_height = port.boundingRect().height()
                port_x = (port_width / 2) * -1
                port.setPos(port_x, port_y_left)
                if text and text.isVisible():
                    txt_x, txt_y = self._calculate_port_text_pos(port, text, width, self._height, gap=gap)
                    text.setPos(txt_x, txt_y)
                layer_left_pos_occupied = True
                port_y_left += port_height + spacing

            if inputs_flipped and not layer_right_pos_occupied:
                port = inputs_flipped.pop()
                text = self.get_input_text_item(port)
                port_width = port.boundingRect().width()
                port_height = port.boundingRect().height()
                port_x = width - (port_width / 2)
                port.setPos(port_x, port_y_right)
                if text and text.isVisible():
                    txt_x, txt_y = self._calculate_port_text_pos(port, text, width, self._height, gap=gap)
                    text.setPos(txt_x, txt_y)
                layer_right_pos_occupied = True
                port_y_right += port_height + spacing

            if outputs_unflipped and not layer_right_pos_occupied:
                port = outputs_unflipped.pop()
                text = self.get_output_text_item(port)
                port_width = port.boundingRect().width()
                port_height = port.boundingRect().height()
                port_x = width - (port_width / 2)
                port.setPos(port_x, port_y_right)
                if text and text.isVisible():
                    txt_x, txt_y = self._calculate_port_text_pos(port, text, width, self._height, gap=gap)
                    text.setPos(txt_x, txt_y)
                layer_right_pos_occupied = True
                port_y_right += port_height + spacing
            
            

            


    # def _align_ports_horizontal(self, v_offset):
    #     width = self._width
    #     txt_offset = PortEnum.CLICK_FALLOFF.value - 2
    #     spacing = 1

    #     # adjust input position
    #     inputs = [p for p in self.inputs if p.isVisible()]
    #     if inputs:
    #         port_width = inputs[0].boundingRect().width()
    #         port_height = inputs[0].boundingRect().height()
    #         if self._flip_node:
    #             port_x = width - (port_width / 2)
    #         else:
    #             port_x = (port_width / 2) * -1
            
    #         port_y = v_offset
    #         for port in inputs:
    #             port.setPos(port_x, port_y)
    #             port_y += port_height + spacing
    #     # adjust input text position
    #     for port, text in self._input_items.items():
    #         if port.isVisible():
    #             if self._flip_node:
    #                 txt_width = text.boundingRect().width() - txt_offset
    #                 txt_x = port.x() - txt_width
    #             else:
    #                 txt_x = port.boundingRect().width() / 2 - txt_offset
    #             text.setPos(txt_x, port.y() - 1.5)

    #     # adjust output position
    #     outputs = [p for p in self.outputs if p.isVisible()]
    #     if outputs:
    #         port_width = outputs[0].boundingRect().width()
    #         port_height = outputs[0].boundingRect().height()
    #         if self._flip_node:
    #             port_x = (port_width / 2) * -1
    #         else:
    #             port_x = width - (port_width / 2)
    #         port_y = v_offset
    #         for port in outputs:
    #             port.setPos(port_x, port_y)
    #             port_y += port_height + spacing
    #     # adjust output text position
    #     for port, text in self._output_items.items():
    #         if port.isVisible():
    #             if self._flip_node:
    #                 txt_x = port.boundingRect().width() / 2 - txt_offset
    #             else:
    #                 txt_width = text.boundingRect().width() - txt_offset
    #                 txt_x = port.x() - txt_width
    #             text.setPos(txt_x, port.y() - 1.5)

    def _align_ports_vertical(self, v_offset):
        # Position custom-positioned ports (origin at bottom-left: (0, 0))
        for port in list(self.inputs) + list(self.outputs):
            if not port.isVisible():
                continue
            if port.has_custom_pos():
                port_width = port.boundingRect().width()
                port_height = port.boundingRect().height()
                qt_x = port.port_x
                qt_y = self._height - port.port_y
                port.setPos(qt_x - (port_width / 2.0), qt_y - (port_height / 2.0))

        # adjust input position
        inputs = [p for p in self.inputs if p.isVisible() and not p.has_custom_pos()]
        if inputs:
            port_width = inputs[0].boundingRect().width()
            port_height = inputs[0].boundingRect().height()
            half_width = port_width / 2
            delta = self._width / (len(inputs) + 1)
            port_x = delta
            port_y = (port_height / 2) * -1
            for port in inputs:
                port.setPos(port_x - half_width, port_y)
                port_x += delta

        # adjust output position
        outputs = [p for p in self.outputs if p.isVisible() and not p.has_custom_pos()]
        if outputs:
            port_width = outputs[0].boundingRect().width()
            port_height = outputs[0].boundingRect().height()
            half_width = port_width / 2
            delta = self._width / (len(outputs) + 1)
            port_x = delta
            port_y = self._height - (port_height / 2)
            for port in outputs:
                port.setPos(port_x - half_width, port_y)
                port_x += delta

    def align_ports(self, v_offset=0.0):
        """
        Align input, output ports in the node layout.

        Args:
            v_offset (float): port vertical offset.
        """
        # Dynamically scale port radius based on component area:
        # Minimum: 2.0px radius, Maximum: 8.0px radius
        # Least component size: 40x40 (area 1600 px^2)
        # For every square pixel increased beyond 1600, radius increases by 0.0005px
        area = float(self._width) * float(self._height)
        delta_area = max(0.0, area - 1600.0)
        port_radius = max(2.0, min(8.0, 2.0 + delta_area * 0.0005))
        for port in list(self.inputs) + list(self.outputs):
            if hasattr(port, 'set_radius'):
                port.set_radius(port_radius)

        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._align_ports_horizontal(v_offset)
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            self._align_ports_vertical(v_offset)
        else:
            raise RuntimeError('Node graph layout direction not valid!')

    def _draw_node_horizontal(self):
        height = self._text_item.boundingRect().height() + 4.0

        # update port text items in visibility.
        show_global = self.show_port_labels
        for port, text in self._input_items.items():
            if port.isVisible():
                text.setVisible(port.display_name and show_global)
        for port, text in self._output_items.items():
            if port.isVisible():
                text.setVisible(port.display_name and show_global)

        # setup initial base size.
        self._set_base_size(add_h=height)
        # set text color when node is initialized.
        self._set_text_color(self.text_color)
        # set the tooltip
        self._tooltip_disable(self.disabled)

        # --- set the initial node layout ---
        # (do all the graphic item layout offsets here)

        # align label text
        self.align_label()
        # align icon
        self.align_icon(h_offset=2.0, v_offset=1.0)
        # arrange input and output ports.
        self.align_ports(v_offset=height)
        # arrange node widgets
        self.align_widgets(v_offset=height)

        self.update()

    def _draw_node_vertical(self):
        # hide the port text items in vertical layout.
        for port, text in self._input_items.items():
            text.setVisible(False)
        for port, text in self._output_items.items():
            text.setVisible(False)

        # setup initial base size.
        self._set_base_size()
        # set text color when node is initialized.
        self._set_text_color(self.text_color)
        # set the tooltip
        self._tooltip_disable(self.disabled)

        # --- setup node layout ---
        # (do all the graphic item layout offsets here)

        # align label text
        self.align_label(h_offset=6)
        # align icon
        self.align_icon(h_offset=6, v_offset=4)
        # arrange input and output ports.
        self.align_ports()
        # arrange node widgets
        self.align_widgets()

        self.update()

    def draw_node(self):
        """
        Re-draw the node item in the scene with proper
        calculated size and widgets aligned.
        """
        self.setTransformOriginPoint(self._width / 2.0, self._height / 2.0)
        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._draw_node_horizontal()
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            self._draw_node_vertical()
        else:
            raise RuntimeError('Node graph layout direction not valid!')

    def post_init(self, viewer=None, pos=None):
        """
        Called after node has been added into the scene.
        Adjust the node layout and form after the node has been added.

        Args:
            viewer (NodeGraphQt.widgets.viewer.NodeViewer): not used
            pos (tuple): cursor position.
        """
        self.draw_node()

        # set initial node position.
        if pos:
            self.xy_pos = pos

    def auto_switch_mode(self):
        """
        Decide whether to draw the node with proxy mode.
        (this is called at the start in the "self.paint()" function.)
        """
        if ITEM_CACHE_MODE is QtWidgets.QGraphicsItem.ItemCoordinateCache:
            return

        rect = self.sceneBoundingRect()
        l = self.viewer().mapToGlobal(
            self.viewer().mapFromScene(rect.topLeft()))
        r = self.viewer().mapToGlobal(
            self.viewer().mapFromScene(rect.topRight()))
        # width is the node width in screen
        width = r.x() - l.x()

        self.set_proxy_mode(width < self._proxy_mode_threshold)

    def set_proxy_mode(self, mode):
        """
        Set whether to draw the node with proxy mode.
        (proxy mode toggles visibility for some qgraphic items in the node.)

        Args:
            mode (bool): true to enable proxy mode.
        """
        if mode is self._proxy_mode:
            return
        self._proxy_mode = mode

        visible = not mode

        # disable overlay item.
        self._x_item.proxy_mode = self._proxy_mode

        # node widget visibility.
        for w in self._widgets.values():
            w.widget().setVisible(visible)

        # port text is not visible in vertical layout.
        if self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            port_text_visible = False
        else:
            port_text_visible = visible

        show_global = self.show_port_labels
        # input port text visibility.
        for port, text in self._input_items.items():
            if port.display_name:
                text.setVisible(port_text_visible and show_global)

        # output port text visibility.
        for port, text in self._output_items.items():
            if port.display_name:
                text.setVisible(port_text_visible and show_global)

        self._text_item.setVisible(visible)
        self._icon_item.setVisible(visible)

    @property
    def show_port_labels(self):
        if hasattr(self, '_show_port_labels') and self._show_port_labels is not None:
            return self._show_port_labels
        if hasattr(self, 'node') and self.node and hasattr(self.node, 'graph') and self.node.graph:
            return getattr(self.node.graph, 'show_port_labels', True)
        try:
            import core.global_state as gs
            return getattr(gs, 'SHOW_PORT_LABELS', True)
        except Exception:
            return True

    @show_port_labels.setter
    def show_port_labels(self, val):
        self._show_port_labels = bool(val)
        for port, text in self._input_items.items():
            if port.isVisible():
                text.setVisible(port.display_name and self._show_port_labels)
        for port, text in self._output_items.items():
            if port.isVisible():
                text.setVisible(port.display_name and self._show_port_labels)
        self.update()

    @property
    def icon(self):
        return self._properties['icon']

    @icon.setter
    def icon(self, path=None):
        self._properties['icon'] = path
        path = path or ICON_NODE_BASE
        pixmap = QtGui.QPixmap(path)
        if pixmap.size().height() > NodeEnum.ICON_SIZE.value:
            pixmap = pixmap.scaledToHeight(
                NodeEnum.ICON_SIZE.value,
                QtCore.Qt.SmoothTransformation
            )
        if pixmap.size().width() > NodeEnum.ICON_SIZE.value:
            pixmap = pixmap.scaledToWidth(
                NodeEnum.ICON_SIZE.value,
                QtCore.Qt.SmoothTransformation
            )
        self._icon_item.setPixmap(pixmap)
        if self.scene():
            self.post_init()

        self.update()

    @AbstractNodeItem.layout_direction.setter
    def layout_direction(self, value=0):
        AbstractNodeItem.layout_direction.fset(self, value)
        self.draw_node()

    @AbstractNodeItem.width.setter
    def width(self, width=0.0):
        if width is None:
            self._custom_width = None
        else:
            self._custom_width = float(width)
            self.prepareGeometryChange()
            self._width = float(width)
        self.draw_node()

    @AbstractNodeItem.height.setter
    def height(self, height=0.0):
        if height is None:
            self._custom_height = None
        else:
            self._custom_height = float(height)
            self.prepareGeometryChange()
            self._height = float(height)
        self.draw_node()

    @AbstractNodeItem.disabled.setter
    def disabled(self, state=False):
        AbstractNodeItem.disabled.fset(self, state)
        for n, w in self._widgets.items():
            w.widget().setDisabled(state)
        self._tooltip_disable(state)
        self._x_item.setVisible(state)

    @AbstractNodeItem.selected.setter
    def selected(self, selected=False):
        AbstractNodeItem.selected.fset(self, selected)
        if selected:
            self.highlight_pipes()

    @AbstractNodeItem.name.setter
    def name(self, name=''):
        AbstractNodeItem.name.fset(self, name)
        if name == self._text_item.toPlainText():
            return
        self._text_item.setPlainText(name)
        if self.scene():
            self.align_label()
        self.update()

    @AbstractNodeItem.color.setter
    def color(self, color=(100, 100, 100, 255)):
        AbstractNodeItem.color.fset(self, color)
        if self.scene():
            self.scene().update()
        self.update()
        
    @AbstractNodeItem.border_color.setter
    def border_color(self, color=(100, 100, 100, 255)):
        AbstractNodeItem.border_color.fset(self, color)
        if self.scene():
            self.scene().update()
        self.update()

    @AbstractNodeItem.text_color.setter
    def text_color(self, color=(100, 100, 100, 255)):
        AbstractNodeItem.text_color.fset(self, color)
        self._set_text_color(color)
        self.update()

    @property
    def text_item(self):
        """
        Get the node name text qgraphics item.

        Returns:
            NodeTextItem: node text object.
        """
        return self._text_item

    @property
    def icon_item(self):
        """
        Get the node icon qgraphics item.

        Returns:
            QtWidgets.QGraphicsPixmapItem: node icon object.
        """
        return self._icon_item

    @property
    def inputs(self):
        """
        Returns:
            list[PortItem]: input port graphic items.
        """
        return list(self._input_items.keys())

    @property
    def outputs(self):
        """
        Returns:
            list[PortItem]: output port graphic items.
        """
        return list(self._output_items.keys())

    def _add_port(self, port):
        """
        Adds a port qgraphics item into the node.

        Args:
            port (PortItem): port item.

        Returns:
            PortItem: port qgraphics item.
        """
        disp_text = getattr(port, 'label', None)
        if disp_text is None:
            disp_text = port.name
        text = QtWidgets.QGraphicsTextItem(disp_text, self)
        text.document().setDocumentMargin(1.5)
        text.font().setPointSize(8)
        text.setFont(text.font())
        show_global = getattr(self, 'show_port_labels', True)
        text.setVisible(port.display_name and show_global)
        text.setCacheMode(ITEM_CACHE_MODE)
        if port.port_type == PortTypeEnum.IN.value:
            self._input_items[port] = text
        elif port.port_type == PortTypeEnum.OUT.value:
            self._output_items[port] = text
        if self.scene():
            self.post_init()
        return port

    def add_input(self, name='input', multi_port=False, display_name=True,
                  locked=False, painter_func=None, flip_node=False,
                  port_x=None, port_y=None, PortX=None, PortY=None,
                  label=None, label_pos='AUTO'):
        """
        Adds a port qgraphics item into the node with the "port_type" set as
        IN_PORT.

        Args:
            name (str): name for the port.
            multi_port (bool): allow multiple connections.
            display_name (bool): display the port name.
            locked (bool): locked state.
            painter_func (function): custom paint function.
            flip_node (bool): flipped state.
            port_x (float): custom x position in px relative to node origin (0, 0).
            port_y (float): custom y position in px relative to node origin (0, 0).
            PortX (float): alias for port_x.
            PortY (float): alias for port_y.
            label (str or None): custom text label to display.
            label_pos (str): directional position ('AUTO', 'T', 'B', 'L', 'R', 'TL', 'TR', 'BL', 'BR').

        Returns:
            PortItem: input port qgraphics item.
        """
        if painter_func:
            port = CustomPortItem(self, painter_func)
        else:
            port = PortItem(self)
        port.name = name
        port.port_type = PortTypeEnum.IN.value
        port.multi_connection = multi_port
        port.display_name = display_name
        port.locked = locked
        port.flipped = flip_node
        port.label = label
        port.label_pos = label_pos
        eff_x = PortX if PortX is not None else port_x
        eff_y = PortY if PortY is not None else port_y
        if eff_x is not None:
            port.port_x = float(eff_x)
        if eff_y is not None:
            port.port_y = float(eff_y)
        return self._add_port(port)

    def add_output(self, name='output', multi_port=False, display_name=True,
                   locked=False, painter_func=None, flip_node=False,
                   port_x=None, port_y=None, PortX=None, PortY=None,
                   label=None, label_pos='AUTO'):
        """
        Adds a port qgraphics item into the node with the "port_type" set as
        OUT_PORT.

        Args:
            name (str): name for the port.
            multi_port (bool): allow multiple connections.
            display_name (bool): display the port name.
            locked (bool): locked state.
            painter_func (function): custom paint function.
            flip_node (bool): flipped state.
            port_x (float): custom x position in px relative to node origin (0, 0).
            port_y (float): custom y position in px relative to node origin (0, 0).
            PortX (float): alias for port_x.
            PortY (float): alias for port_y.
            label (str or None): custom text label to display.
            label_pos (str): directional position ('AUTO', 'T', 'B', 'L', 'R', 'TL', 'TR', 'BL', 'BR').

        Returns:
            PortItem: output port qgraphics item.
        """
        if painter_func:
            port = CustomPortItem(self, painter_func)
        else:
            port = PortItem(self)
        port.name = name
        port.port_type = PortTypeEnum.OUT.value
        port.multi_connection = multi_port
        port.display_name = display_name
        port.locked = locked
        port.flipped = flip_node
        port.label = label
        port.label_pos = label_pos
        eff_x = PortX if PortX is not None else port_x
        eff_y = PortY if PortY is not None else port_y
        if eff_x is not None:
            port.port_x = float(eff_x)
        if eff_y is not None:
            port.port_y = float(eff_y)
        return self._add_port(port)

    def _delete_port(self, port, text):
        """
        Removes port item and port text from node.

        Args:
            port (PortItem): port object.
            text (QtWidgets.QGraphicsTextItem): port text object.
        """
        port.setParentItem(None)
        text.setParentItem(None)
        if self.scene():
            self.scene().removeItem(port)
            self.scene().removeItem(text)
        del port
        del text

    def delete_input(self, port):
        """
        Remove input port from node.

        Args:
            port (PortItem): port object.
        """
        self._delete_port(port, self._input_items.pop(port))

    def delete_output(self, port):
        """
        Remove output port from node.

        Args:
            port (PortItem): port object.
        """
        self._delete_port(port, self._output_items.pop(port))

    def get_input_text_item(self, port_item):
        """
        Args:
            port_item (PortItem): port item.

        Returns:
            QGraphicsTextItem: graphic item used for the port text.
        """
        return self._input_items[port_item]

    def get_output_text_item(self, port_item):
        """
        Args:
            port_item (PortItem): port item.

        Returns:
            QGraphicsTextItem: graphic item used for the port text.
        """
        return self._output_items[port_item]

    @property
    def widgets(self):
        return self._widgets.copy()

    def add_widget(self, widget):
        self._widgets[widget.get_name()] = widget

    def get_widget(self, name):
        widget = self._widgets.get(name)
        if widget:
            return widget
        raise NodeWidgetError('node has no widget "{}"'.format(name))

    def has_widget(self, name):
        return name in self._widgets.keys()

    def from_dict(self, node_dict):
        super(NodeItem, self).from_dict(node_dict)
        if 'flipped_x' in node_dict:
            self.flipped_x = bool(node_dict['flipped_x'])
        if 'flipped_y' in node_dict:
            self.flipped_y = bool(node_dict['flipped_y'])
        if 'rotation' in node_dict:
            self.set_rotation(float(node_dict['rotation']))
        custom_prop = node_dict.get('custom') or {}
        for prop_name, value in custom_prop.items():
            prop_widget = self._widgets.get(prop_name)
            if prop_widget:
                prop_widget.set_value(value)
