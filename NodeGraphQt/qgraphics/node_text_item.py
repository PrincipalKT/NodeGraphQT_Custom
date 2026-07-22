from Qt import QtWidgets, QtCore, QtGui


class NodeTextItem(QtWidgets.QGraphicsTextItem):
    """
    NodeTextItem class used to display and edit the name of a NodeItem.
    """

    def __init__(self, text, parent=None):
        super(NodeTextItem, self).__init__(text, parent)
        self._locked = False
        self.set_locked(False)
        self.set_editable(False)

    def mouseDoubleClickEvent(self, event):
        """
        Re-implemented to jump into edit mode when user clicks on node text.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): mouse event.
        """
        if not self._locked:
            if event.button() == QtCore.Qt.LeftButton:
                self.set_editable(True)
                event.ignore()
                return
        super(NodeTextItem, self).mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        """
        Re-implemented to catch the Return & Escape keys when in edit mode.

        Args:
            event (QtGui.QKeyEvent): key event.
        """
        if event.key() == QtCore.Qt.Key_Return:
            current_text = self.toPlainText()

            #IMP : Calls Node.py method in SteagSIM
            self.node.get_base_node_ref().set_display_name(current_text)

            #NOTE : Actual library code (commented out)
            # self.set_node_name(current_text)

            self.set_editable(False)
        elif event.key() == QtCore.Qt.Key_Escape:

            #IMP : Calls Node.py method in SteagSIM
            self.setPlainText(self.node.get_base_node_ref().display_name())

            self.set_editable(False)
        super(NodeTextItem, self).keyPressEvent(event)

    def focusOutEvent(self, event):
        """
        Re-implemented to jump out of edit mode.

        Args:
            event (QtGui.QFocusEvent):
        """
        current_text = self.toPlainText()
        #IMP : Calls Node.py method in SteagSIM
        self.node.get_base_node_ref().set_display_name(current_text)

        #NOTE : Actual library code (commented out)
        # self.set_node_name(current_text)
        
        self.set_editable(False)
        super(NodeTextItem, self).focusOutEvent(event)

    def set_editable(self, value=False):
        """
        Set the edit mode for the text item.

        Args:
            value (bool):  true in edit mode.
        """
        if self._locked:
            return
        if value:
            self.setTextInteractionFlags(
                QtCore.Qt.TextEditable |
                QtCore.Qt.TextSelectableByMouse |
                QtCore.Qt.TextSelectableByKeyboard
            )
        else:
            self.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
            cursor = self.textCursor()
            cursor.clearSelection()
            self.setTextCursor(cursor)


    #NOTE : This is just sitting here
    def set_node_name(self, name):
        """
        Updates the node name through the node "NodeViewer().node_name_changed"
        signal which then updates the node name through the BaseNode object this
        will register it as an undo command.

        Args:
            name (str): new node name.
        """
        name = name.strip()
        if name != self.node.name:
            viewer = self.node.viewer()
            viewer.node_name_changed.emit(self.node.id, name)

    def set_locked(self, state=False):
        """
        Locks the text item so it can not be editable.

        Args:
            state (bool): lock state.
        """
        self._locked = state
        if self._locked:
            self.setFlag(QtWidgets.QGraphicsItem.ItemIsFocusable, False)
            self.setCursor(QtCore.Qt.ArrowCursor)
            self.setToolTip('')
        else:
            self.setFlag(QtWidgets.QGraphicsItem.ItemIsFocusable, True)
            self.setToolTip('double-click to edit node name.')
            self.setCursor(QtCore.Qt.IBeamCursor)

    @property
    def node(self):
        """
        Get the parent node item.

        Returns:
            NodeItem: parent node qgraphics item.
        """
        return self.parentItem()
    
    def _on_display_name_property_changed(self):
        """Hook to update the textItem graphic on UI when the display name property is changed.
        
        One of the multiple ways to do it.
        """
        base_ref = self.node.get_base_node_ref()
        result = base_ref.display_name()
        self.setPlainText(result)
