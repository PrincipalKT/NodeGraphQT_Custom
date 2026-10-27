#!/usr/bin/python
from NodeGraphQt.base.commands import PropertyChangedCmd
from NodeGraphQt.base.model import NodeModel
from NodeGraphQt.constants import NodePropWidgetEnum


class _ClassProperty(object):

    def __init__(self, f):
        self.f = f

    def __get__(self, instance, owner):
        return self.f(owner)


class NodeObject(object):
    """
    The ``NodeGraphQt.NodeObject`` class is the main base class that all
    nodes inherit from.

    .. inheritance-diagram:: NodeGraphQt.NodeObject

    Args:
        qgraphics_item (AbstractNodeItem): QGraphicsItem item used for drawing.
    """

    __identifier__ = 'nodeGraphQt.nodes'
    """
    Unique node identifier domain. eg. ``"io.github.jchanvfx"``

    .. important:: re-implement this attribute to provide a unique node type.
    
        .. code-block:: python
            :linenos:
    
            from NodeGraphQt import NodeObject
    
            class ExampleNode(NodeObject):
    
                # unique node identifier domain.
                __identifier__ = 'io.github.jchanvfx'
    
                def __init__(self):
                    ...
    
    :return: node type domain.
    :rtype: str
    
    :meta hide-value:
    """

    NODE_NAME = None
    """
    Initial base node name.

    .. important:: re-implement this attribute to provide a base node name.
    
        .. code-block:: python
            :linenos:
    
            from NodeGraphQt import NodeObject
    
            class ExampleNode(NodeObject):
    
                # initial default node name.
                NODE_NAME = 'Example Node'
    
                def __init__(self):
                    ...
    
    :return: node name
    :rtype: str
    
    :meta hide-value:
    """

    NODE_WIDTH = None
    """
    Initial custom node width.
    """

    NODE_HEIGHT = None
    """
    Initial custom node height.
    """

    def __init__(self, qgraphics_item=None):
        """
        Args:
            qgraphics_item (AbstractNodeItem): QGraphicsItem used for drawing.
        """
        self._graph = None
        self._model = NodeModel()
        self._model.type_ = self.type_
        self._model.name = self.NODE_NAME

        _NodeItem = qgraphics_item
        if _NodeItem is None:
            raise RuntimeError(
                'No qgraphics item specified for the node object!'
            )

        self._view = _NodeItem()

        #WARN : Assumes NodeItem class as passed qgraphics_item
        self._view.set_base_node_ref(self)

        self._view.type_ = self.type_
        self._view.name = self.model.name
        self._view.id = self._model.id
        self._view.layout_direction = self._model.layout_direction

        initial_width = getattr(self, 'NODE_WIDTH', None)
        initial_height = getattr(self, 'NODE_HEIGHT', None)

        if initial_width is not None:
            self._view.width = initial_width
            self._model.width = float(initial_width)
            self._model.custom_width = float(initial_width)
        if initial_height is not None:
            self._view.height = initial_height
            self._model.height = float(initial_height)
            self._model.custom_height = float(initial_height)

    def __repr__(self):
        return '<{}("{}") object at {}>'.format(
            self.__class__.__name__, self.NODE_NAME, hex(id(self)))

    @_ClassProperty
    def type_(cls):
        """
        Node type identifier followed by the class name.
        `eg.` ``"nodeGraphQt.nodes.NodeObject"``

        Returns:
            str: node type (``__identifier__.__className__``)
        """
        return cls.__identifier__ + '.' + cls.__name__

    @property
    def id(self):
        """
        The node unique id.

        Returns:
            str: unique identifier string to the node.
        """
        return self.model.id

    @property
    def graph(self):
        """
        The parent node graph.

        Returns:
            NodeGraphQt.NodeGraph: node graph instance.
        """
        return self._graph

    @property
    def view(self):
        """
        Returns the :class:`QtWidgets.QGraphicsItem` used in the scene.

        Returns:
            NodeGraphQt.qgraphics.node_abstract.AbstractNodeItem: node item.
        """
        return self._view

    def set_view(self, item):
        """
        Set a new ``QGraphicsItem`` item to be used as the view.
        (the provided qgraphics item must be subclassed from the
        ``AbstractNodeItem`` object.)

        Args:
            item (NodeGraphQt.qgraphics.node_abstract.AbstractNodeItem): node item.
        """
        if self._view:
            old_view = self._view
            scene = self._view.scene()
            scene.removeItem(old_view)
            self._view = item
            scene.addItem(self._view)
        else:
            self._view = item
        self.NODE_NAME = self._view.name

        # update the view.
        self.update()

    @property
    def model(self):
        """
        Return the node model.

        Returns:
            NodeGraphQt.base.model.NodeModel: node model object.
        """
        return self._model

    def set_model(self, model):
        """
        Set a new model to the node model.
        (Setting a new node model will also update the views qgraphics item.)

        Args:
            model (NodeGraphQt.base.model.NodeModel): node model object.
        """
        self._model = model
        self._model.type_ = self.type_
        self._model.id = self.view.id

        # update the view.
        self.update()

    def update_model(self):
        """
        Update the node model from view.
        """
        for name, val in self.view.properties.items():
            if name in self.model.properties.keys():
                setattr(self.model, name, val)
            if name in self.model.custom_properties.keys():
                self.model.custom_properties[name] = val
        if hasattr(self.view, 'flipped_x'):
            self.model.set_property('flipped_x', self.view.flipped_x)
        if hasattr(self.view, 'flipped_y'):
            self.model.set_property('flipped_y', self.view.flipped_y)
        if hasattr(self.view, 'rotation'):
            self.model.set_property('rotation', self.view.rotation)

    def update(self):
        """
        Update the node view from model.
        """
        settings = self.model.to_dict[self.model.id]
        settings['id'] = self.model.id
        self.view.from_dict(settings)

    def serialize(self):
        """
        Serialize node model to a dictionary.

        example:

        .. highlight:: python
        .. code-block:: python

            {'0x106cf75a8': {
                'name': 'foo node',
                'color': (48, 58, 69, 255),
                'border_color': (85, 100, 100, 255),
                'text_color': (255, 255, 255, 180),
                'type': 'io.github.jchanvfx.MyNode',
                'selected': False,
                'disabled': False,
                'visible': True,
                'inputs': {
                    <port_name>: {<node_id>: [<port_name>, <port_name>]}
                },
                'outputs': {
                    <port_name>: {<node_id>: [<port_name>, <port_name>]}
                },
                'input_ports': [<port_name>, <port_name>],
                'output_ports': [<port_name>, <port_name>],
                'width': 0.0,
                'height: 0.0,
                'pos': (0.0, 0.0),
                'layout_direction': 0,
                'custom': {},
                }
            }

        Returns:
            dict: serialized node
        """
        return self.model.to_dict

    def name(self):
        """
        Name of the node.

        Returns:
            str: name of the node.
        """
        return self.model.name

    def set_name(self, name=''):
        """
        Set the name of the node.

        Args:
            name (str): name for the node.
        """
        self.set_property('name', name)

    def color(self):
        """
        Returns the node color in (red, green, blue) value.

        Returns:
            tuple: ``(r, g, b)`` from ``0-255`` range.
        """
        r, g, b, a = self.model.color
        return r, g, b

    def set_color(self, r=0, g=0, b=0):
        """
        Sets the color of the node in (red, green, blue) value.

        Args:
            r (int): red value ``0-255`` range.
            g (int): green value ``0-255`` range.
            b (int): blue value ``0-255`` range.
        """
        self.set_property('color', (r, g, b, 255))

    def disabled(self):
        """
        Returns whether the node is enabled or disabled.

        Returns:
            bool: True if the node is disabled.
        """
        return self.model.disabled

    def set_disabled(self, mode=False):
        """
        Set the node state to either disabled or enabled.

        Args:
            mode(bool): True to disable node.
        """
        self.set_property('disabled', mode)

    def selected(self):
        """
        Returns the selected state of the node.

        Returns:
            bool: True if the node is selected.
        """
        self.model.selected = self.view.isSelected()
        return self.model.selected

    def set_selected(self, selected=True):
        """
        Set the node to be selected or not selected.

        Args:
            selected (bool): True to select the node.
        """
        self.set_property('selected', selected)

    def create_property(self, name, value, items=None, range=None,
                        widget_type=None, widget_tooltip=None, tab=None):
        """
        Creates a custom property to the node.

        See Also:
            Custom node properties bin widget
            :class:`NodeGraphQt.PropertiesBinWidget`

        Hint:
            To see all the available property widget types to display in
            the ``PropertiesBinWidget`` widget checkout
            :attr:`NodeGraphQt.constants.NodePropWidgetEnum`.

        Args:
            name (str): name of the property.
            value (object): data.
            items (list[str]): items used by widget type
                attr:`NodeGraphQt.constants.NodePropWidgetEnum.QCOMBO_BOX`
            range (tuple or list): ``(min, max)`` values used by
                :attr:`NodeGraphQt.constants.NodePropWidgetEnum.SLIDER`
            widget_type (int): widget flag to display in the
                :class:`NodeGraphQt.PropertiesBinWidget`
            widget_tooltip (str): widget tooltip for the property widget
                displayed in the :class:`NodeGraphQt.PropertiesBinWidget`
            tab (str): name of the widget tab to display in the
                :class:`NodeGraphQt.PropertiesBinWidget`.
        """
        widget_type = widget_type or NodePropWidgetEnum.HIDDEN.value
        self.model.add_property(
            name, value, items, range, widget_type, widget_tooltip, tab
        )

    def properties(self):
        """
        Returns all the node properties.

        Returns:
            dict: a dictionary of node properties.
        """
        props = self.model.to_dict[self.id].copy()
        props['id'] = self.id
        return props

    def get_property(self, name):
        """
        Return the node property.

        Args:
            name (str): name of the property.

        Returns:
            object: property data.
        """
        if self.graph and name == 'selected':
            self.model.set_property(name, self.view.selected)

        return self.model.get_property(name)

    def width(self):
        """
        Returns the node width.

        Returns:
            float: node width.
        """
        if self.view:
            return self.view.width
        return self.model.width or 0.0

    def height(self):
        """
        Returns the node height.

        Returns:
            float: node height.
        """
        if self.view:
            return self.view.height
        return self.model.height or 0.0

    def set_width(self, width, push_undo=True):
        """
        Set the node width.

        Args:
            width (float): node width.
            push_undo (bool): register the command to the undo stack. (default: True)
        """
        self.set_property('width', width, push_undo=push_undo)

    def set_height(self, height, push_undo=True):
        """
        Set the node height.

        Args:
            height (float): node height.
            push_undo (bool): register the command to the undo stack. (default: True)
        """
        self.set_property('height', height, push_undo=push_undo)

    def set_property(self, name, value, push_undo=True):
        """
        Set the value on the node property.

        Note:
            When setting the node ``"name"`` property a new unique name will be
            used if another node in the graph has the same node name.

        Args:
            name (str): name of the property.
            value (object): property data (python built in types).
            push_undo (bool): register the command to the undo stack. (default: True)
        """
        # prevent signals from causing an infinite loop.
        if self.get_property(name) == value:
            return

        # prevent nodes from have the same name.
        if self.graph and name == 'name':
            value = self.graph.get_unique_name(value)
            self.NODE_NAME = value

        if self.graph:
            undo_cmd = PropertyChangedCmd(self, name, value)
            if name == 'name':
                undo_cmd.setText(
                    'renamed "{}" to "{}"'.format(self.name(), value)
                )
            elif name in ['width', 'height', 'flipped_x', 'flipped_y', 'rotation']:
                undo_cmd.setText(
                    'set "{}:{}" to {}'.format(self.name(), name, value)
                )
            if push_undo:
                undo_stack = self.graph.undo_stack()
                undo_stack.push(undo_cmd)
            else:
                undo_cmd.redo()
        else:
            if hasattr(self.view, name):
                setattr(self.view, name, value)
            self.model.set_property(name, value)
            if name in ['width', 'height']:
                self.view.draw_node()
            elif name in ['flipped_x', 'flipped_y']:
                if hasattr(self.view, 'align_ports'):
                    self.view.align_ports()
                self.view.draw_node()
            elif name == 'rotation':
                if hasattr(self.view, 'set_rotation'):
                    self.view.set_rotation(value)

        # redraw the node for custom properties.
        if self.model.is_custom_property(name):
            self.view.draw_node()

    @property
    def rotation(self):
        """
        Returns the node rotation in degrees (-360.0 to 360.0).

        Returns:
            float: node rotation in degrees.
        """
        if self.view and hasattr(self.view, 'rotation'):
            return self.view.rotation
        return getattr(self.model, 'rotation', 0.0)

    @rotation.setter
    def rotation(self, value):
        self.set_rotation(value)

    def set_rotation(self, deg=0.0, push_undo=True):
        """
        Set the node rotation in degrees (-360.0 to 360.0).

        Args:
            deg (float): rotation in degrees.
            push_undo (bool): register command to undo stack. (default: True)
        """
        deg = max(-360.0, min(360.0, float(deg)))
        self.set_property('rotation', deg, push_undo=push_undo)

    @property
    def flipped_x(self):
        if hasattr(self.view, 'flipped_x'):
            return self.view.flipped_x
        return getattr(self.model, 'flipped_x', False)

    @flipped_x.setter
    def flipped_x(self, value):
        val = bool(value)
        self.model.set_property('flipped_x', val)
        if hasattr(self.view, 'flipped_x'):
            self.view.flipped_x = val

    @property
    def flipped_y(self):
        if hasattr(self.view, 'flipped_y'):
            return self.view.flipped_y
        return getattr(self.model, 'flipped_y', False)

    @flipped_y.setter
    def flipped_y(self, value):
        val = bool(value)
        self.model.set_property('flipped_y', val)
        if hasattr(self.view, 'flipped_y'):
            self.view.flipped_y = val

    def has_property(self, name):
        """
        Check if node custom property exists.

        Args:
            name (str): name of the node.

        Returns:
            bool: true if property name exists in the Node.
        """
        return name in self.model.custom_properties.keys()

    def set_x_pos(self, x):
        """
        Set the node horizontal X position in the node graph.

        Args:
            x (float or int): node X position.
        """
        y = self.pos()[1]
        self.set_pos(float(x), y)

    def set_y_pos(self, y):
        """
        Set the node horizontal Y position in the node graph.

        Args:
            y (float or int): node Y position.
        """

        x = self.pos()[0]
        self.set_pos(x, float(y))

    def set_pos(self, x, y):
        """
        Set the node X and Y position in the node graph.

        Args:
            x (float or int): node X position.
            y (float or int): node Y position.
        """
        self.set_property('pos', [float(x), float(y)])

    def x_pos(self):
        """
        Get the node X position in the node graph.

        Returns:
            float: x position.
        """
        return self.model.pos[0]

    def y_pos(self):
        """
        Get the node Y position in the node graph.

        Returns:
            float: y position.
        """
        return self.model.pos[1]

    def pos(self):
        """
        Get the node XY position in the node graph.

        Returns:
            list[float, float]: x, y position.
        """
        if self.view.xy_pos and self.view.xy_pos != self.model.pos:
            self.model.pos = self.view.xy_pos

        return self.model.pos

    def layout_direction(self):
        """
        Returns layout direction for this node.

        See Also:
            :meth:`NodeObject.set_layout_direction`

        Returns:
            int: node layout direction.
        """
        return self.model.layout_direction

    def set_layout_direction(self, value=0):
        """
        Sets the node layout direction to either horizontal or vertical on
        the current node only.

        `Implemented in` ``v0.3.0``

        See Also:
            :meth:`NodeGraph.set_layout_direction`
            :meth:`NodeObject.layout_direction`

        Warnings:
            This function does not register to the undo stack.

        Args:
            value (int): layout direction mode.
        """
        self.model.layout_direction = value
        self.view.layout_direction = value
