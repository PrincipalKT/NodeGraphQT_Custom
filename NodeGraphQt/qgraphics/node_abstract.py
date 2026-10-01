#!/usr/bin/python
from Qt import QtCore, QtWidgets

from NodeGraphQt.constants import (
    Z_VAL_NODE,
    ITEM_CACHE_MODE,
    LayoutDirectionEnum,
    NodeEnum
)


class AbstractNodeItem(QtWidgets.QGraphicsItem):
    """
    The base class of all node qgraphics item.
    """

    def __init__(self, name='node', parent=None):
        super(AbstractNodeItem, self).__init__(parent)
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsSelectable |
            QtWidgets.QGraphicsItem.ItemIsMovable
        )
        self.setCacheMode(ITEM_CACHE_MODE)
        self.setZValue(Z_VAL_NODE)
        self._properties = {
            'id': None,
            'name': name.strip(),
            'color': (13, 18, 23, 255),
            'border_color': (46, 57, 66, 255),
            'text_color': (255, 255, 255, 180),
            'type_': 'AbstractBaseNode',
            'selected': False,
            'disabled': False,
            'visible': False,
            'layout_direction': LayoutDirectionEnum.HORIZONTAL.value,
            'rotation': 0.0,
        }
        self._width = NodeEnum.WIDTH.value
        self._height = NodeEnum.HEIGHT.value
        self._custom_width = None
        self._custom_height = None
        self.setTransformOriginPoint(self._width / 2.0, self._height / 2.0)

    def __repr__(self):
        return '{}.{}(\'{}\')'.format(
            self.__module__, self.__class__.__name__, self.name)

    def boundingRect(self):
        return QtCore.QRectF(0.0, 0.0, self._width, self._height)

    def mousePressEvent(self, event):
        """
        Re-implemented to update "self._properties['selected']" attribute.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): mouse event.
        """
        self._properties['selected'] = True
        super(AbstractNodeItem, self).mousePressEvent(event)

    def setSelected(self, selected):
        self._properties['selected'] = selected
        super(AbstractNodeItem, self).setSelected(selected)

    def draw_node(self):
        """
        Re-draw the node item in the scene with proper
        calculated size and widgets aligned.

        (this is called from the builtin custom widgets.)
        """
        return

    def pre_init(self, viewer, pos=None):
        """
        Called before node has been added into the scene.

        Args:
            viewer (NodeGraphQt.widgets.viewer.NodeViewer): main viewer.
            pos (tuple): the cursor pos if node is called with tab search.
        """
        return

    def post_init(self, viewer, pos=None):
        """
        Called after node has been added into the scene.

        Args:
            viewer (NodeGraphQt.widgets.viewer.NodeViewer): main viewer
            pos (tuple): the cursor pos if node is called with tab search.
        """
        return

    @property
    def id(self):
        return self._properties['id']

    @id.setter
    def id(self, unique_id=''):
        self._properties['id'] = unique_id

    @property
    def type_(self):
        return self._properties['type_']

    @type_.setter
    def type_(self, node_type='NODE'):
        self._properties['type_'] = node_type

    @property
    def layout_direction(self):
        return self._properties['layout_direction']

    @layout_direction.setter
    def layout_direction(self, value=0):
        self._properties['layout_direction'] = value

    @property
    def size(self):
        return self._width, self._height

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width=0.0):
        if width is None:
            self._custom_width = None
        else:
            self.prepareGeometryChange()
            self._width = float(width)
            self._custom_width = float(width)
            self.setTransformOriginPoint(self._width / 2.0, self._height / 2.0)

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, height=0.0):
        if height is None:
            self._custom_height = None
        else:
            self.prepareGeometryChange()
            self._height = float(height)
            self._custom_height = float(height)
            self.setTransformOriginPoint(self._width / 2.0, self._height / 2.0)

    @property
    def rotation(self):
        return float(self._properties.get('rotation', 0.0))

    @rotation.setter
    def rotation(self, deg=0.0):
        self.set_rotation(deg)

    def set_rotation(self, deg=0.0):
        deg = max(-360.0, min(360.0, float(deg)))
        self._properties['rotation'] = deg
        self.setTransformOriginPoint(self._width / 2.0, self._height / 2.0)
        self.setRotation(deg)
        ports = []
        if hasattr(self, 'inputs'):
            ports.extend(self.inputs)
        elif hasattr(self, '_input_items'):
            ports.extend(list(self._input_items.keys()))
        if hasattr(self, 'outputs'):
            ports.extend(self.outputs)
        elif hasattr(self, '_output_items'):
            ports.extend(list(self._output_items.keys()))
        for port in ports:
            if hasattr(port, 'redraw_connected_pipes'):
                port.redraw_connected_pipes()
        self.update()

    @property
    def color(self):
        return self._properties['color']

    @color.setter
    def color(self, color=(0, 0, 0, 255)):
        self._properties['color'] = color

    @property
    def text_color(self):
        return self._properties['text_color']

    @text_color.setter
    def text_color(self, color=(100, 100, 100, 255)):
        self._properties['text_color'] = color

    @property
    def border_color(self):
        return self._properties['border_color']

    @border_color.setter
    def border_color(self, color=(0, 0, 0, 255)):
        self._properties['border_color'] = color

    @property
    def disabled(self):
        return self._properties['disabled']

    @disabled.setter
    def disabled(self, state=False):
        self._properties['disabled'] = state

    @property
    def selected(self):
        if self._properties['selected'] != self.isSelected():
            self._properties['selected'] = self.isSelected()
        return self._properties['selected']

    @selected.setter
    def selected(self, selected=False):
        self.setSelected(selected)

    @property
    def visible(self):
        return self._properties['visible']

    @visible.setter
    def visible(self, visible=False):
        self._properties['visible'] = visible
        self.setVisible(visible)

    @property
    def xy_pos(self):
        """
        return the item scene postion.
        ("node.pos" conflicted with "QGraphicsItem.pos()"
        so it was refactored to "xy_pos".)

        Returns:
            list[float]: x, y scene position.
        """
        return [float(self.scenePos().x()), float(self.scenePos().y())]

    @xy_pos.setter
    def xy_pos(self, pos=None):
        """
        set the item scene postion.
        ("node.pos" conflicted with "QGraphicsItem.pos()"
        so it was refactored to "xy_pos".)

        Args:
            pos (list[float]): x, y scene position.
        """
        pos = pos or [0.0, 0.0]
        self.setPos(pos[0], pos[1])

    @property
    def name(self):
        return self._properties['name']

    @name.setter
    def name(self, name=''):
        self._properties['name'] = name
        self.setToolTip('node: {}'.format(name))

    @property
    def properties(self):
        """
        return the node view attributes.

        Returns:
            dict: {property_name: property_value}
        """
        props = {'width': self.width,
                 'height': self.height,
                 'flipped_x': getattr(self, 'flipped_x', False),
                 'flipped_y': getattr(self, 'flipped_y', False),
                 'pos':  self.xy_pos}
        props.update(self._properties)
        return props

    def viewer(self):
        """
        return the main viewer.

        Returns:
            NodeGraphQt.widgets.viewer.NodeViewer: viewer object.
        """
        if self.scene():
            return self.scene().viewer()

    def delete(self):
        """
        remove node view from the scene.
        """
        if self.scene():
            self.scene().removeItem(self)

    def from_dict(self, node_dict):
        """
        set the node view attributes from the dictionary.

        Args:
            node_dict (dict): serialized node dict.
        """
        node_attrs = list(self._properties.keys()) + ['width', 'height', 'flipped_x', 'flipped_y', 'pos']
        for name, value in node_dict.items():
            if name in node_attrs:
                if name in ['width', 'height'] and value is None:
                    continue
                # "node.pos" conflicted with "QGraphicsItem.pos()"
                # so it's refactored to "xy_pos".
                if name == 'pos':
                    name = 'xy_pos'
                setattr(self, name, value)
