#!/usr/bin/python
import math

from Qt import QtCore, QtGui, QtWidgets

from NodeGraphQt.constants import (
    LayoutDirectionEnum,
    PipeEnum,
    PipeLayoutEnum,
    PortTypeEnum,
    ITEM_CACHE_MODE,
    Z_VAL_PIPE,
    Z_VAL_NODE_WIDGET
)
from NodeGraphQt.qgraphics.port import PortItem

PIPE_STYLES = {
    PipeEnum.DRAW_TYPE_DEFAULT.value: QtCore.Qt.SolidLine,
    PipeEnum.DRAW_TYPE_DASHED.value: QtCore.Qt.DashLine,
    PipeEnum.DRAW_TYPE_DOTTED.value: QtCore.Qt.DotLine
}

_PIPE_ID_COUNTER = 0


def _get_next_pipe_id():
    global _PIPE_ID_COUNTER
    _PIPE_ID_COUNTER += 1
    return _PIPE_ID_COUNTER


class PipeSpatialIndex(object):
    """
    2D uniform spatial grid for fast line-segment candidate lookup.
    Avoids scanning all QGraphicsScene items and port/node bounding rects.
    """
    def __init__(self, cell_size=250.0):
        self.cell_size = float(cell_size)
        self.grid = {}
        self.pipe_cells = {}

    def clear(self):
        self.grid.clear()
        self.pipe_cells.clear()

    def update_pipe(self, pipe, pos1, pos2):
        self.remove_pipe(pipe)
        if pos1 is None or pos2 is None:
            return
        all_x = [pos1.x(), pos2.x()]
        all_y = [pos1.y(), pos2.y()]
        for wp in getattr(pipe, 'waypoints', []):
            all_x.append(wp.x())
            all_y.append(wp.y())
        min_x = min(all_x)
        max_x = max(all_x)
        min_y = min(all_y)
        max_y = max(all_y)

        c_min_x = int(min_x // self.cell_size)
        c_max_x = int(max_x // self.cell_size)
        c_min_y = int(min_y // self.cell_size)
        c_max_y = int(max_y // self.cell_size)

        cells = set()
        for cx in range(c_min_x, c_max_x + 1):
            for cy in range(c_min_y, c_max_y + 1):
                cells.add((cx, cy))
                self.grid.setdefault((cx, cy), set()).add(pipe)
        self.pipe_cells[pipe] = cells

    def remove_pipe(self, pipe):
        cells = self.pipe_cells.pop(pipe, None)
        if cells:
            for c in cells:
                bucket = self.grid.get(c)
                if bucket:
                    bucket.discard(pipe)
                    if not bucket:
                        del self.grid[c]

    def query(self, min_x, max_x, min_y, max_y):
        c_min_x = int(min_x // self.cell_size)
        c_max_x = int(max_x // self.cell_size)
        c_min_y = int(min_y // self.cell_size)
        c_max_y = int(max_y // self.cell_size)

        candidates = set()
        for cx in range(c_min_x, c_max_x + 1):
            for cy in range(c_min_y, c_max_y + 1):
                bucket = self.grid.get((cx, cy))
                if bucket:
                    candidates.update(bucket)
        return candidates


def _get_spatial_index(scene):
    if scene is None:
        return None
    idx = getattr(scene, '_pipe_spatial_index', None)
    if idx is None:
        idx = PipeSpatialIndex(250.0)
        scene._pipe_spatial_index = idx
    return idx


class PipeItem(QtWidgets.QGraphicsPathItem):
    """
    Base Pipe item used for drawing node connections.
    """
    _SUSPEND_BRIDGES = False

    def __init__(self, input_port=None, output_port=None):
        super(PipeItem, self).__init__()
        self._pipe_id = _get_next_pipe_id()
        self._p1 = None
        self._p2 = None
        self._bridge_distances = []
        self._crossing_pipes = set()
        self._in_draw_path = False

        self.setZValue(Z_VAL_PIPE)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
        self.setCacheMode(ITEM_CACHE_MODE)

        self._color = PipeEnum.COLOR.value
        self._style = PipeEnum.DRAW_TYPE_DEFAULT.value
        self._active = False
        self._highlight = False
        self._input_port = input_port
        self._output_port = output_port

        size = 6.0
        self._poly = QtGui.QPolygonF()
        self._poly.append(QtCore.QPointF(-size, size))
        self._poly.append(QtCore.QPointF(0.0, -size * 1.5))
        self._poly.append(QtCore.QPointF(size, size))

        self._waypoints = []

        self._dir_pointer = QtWidgets.QGraphicsPolygonItem(self)
        self._dir_pointer.setPolygon(self._poly)
        self._dir_pointer.setFlag(
            QtWidgets.QGraphicsPathItem.ItemIsSelectable, False
        )

        self.reset()

    @property
    def waypoints(self):
        """
        Returns list of intermediate joint waypoints (QPointF).
        """
        return [QtCore.QPointF(wp) for wp in self._waypoints]

    @waypoints.setter
    def waypoints(self, points):
        self._waypoints = [
            QtCore.QPointF(p[0], p[1]) if isinstance(p, (list, tuple)) else QtCore.QPointF(p)
            for p in (points or [])
        ]

    def add_waypoint(self, pt):
        """
        Add a joint waypoint to the connection pipe.
        """
        if isinstance(pt, (list, tuple)):
            pt = QtCore.QPointF(pt[0], pt[1])
        self._waypoints.append(QtCore.QPointF(pt))

    def pop_waypoint(self):
        """
        Remove and return the most recently added waypoint.
        """
        if self._waypoints:
            return self._waypoints.pop()
        return None

    def clear_waypoints(self):
        """
        Clear all intermediate waypoints.
        """
        self._waypoints = []

    def __repr__(self):
        in_name = self._input_port.name if self._input_port else ''
        out_name = self._output_port.name if self._output_port else ''
        return '{}.Pipe(\'{}\', \'{}\')'.format(
            self.__module__, in_name, out_name)

    def hoverEnterEvent(self, event):
        self.activate()

    def hoverLeaveEvent(self, event):
        self.reset()
        if self.input_port and self.output_port:
            if self.input_port.node.selected:
                self.highlight()
            elif self.output_port.node.selected:
                self.highlight()
        if self.isSelected():
            self.highlight()

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsPathItem.ItemSelectedChange and self.scene():
            if value:
                self.highlight()
            else:
                self.reset()
        return super(PipeItem, self).itemChange(change, value)

    def boundingRect(self):
        rect = super(PipeItem, self).boundingRect()
        if self._waypoints:
            rect = rect.adjusted(-5.0, -5.0, 5.0, 5.0)
        return rect

    def paint(self, painter, option, widget):
        """
        Draws the connection line between nodes.

        Args:
            painter (QtGui.QPainter): painter used for drawing the item.
            option (QtGui.QStyleOptionGraphicsItem):
                used to describe the parameters needed to draw.
            widget (QtWidgets.QWidget): not used.
        """
        painter.save()

        pen = self.pen()
        if self.disabled():
            if not self._active:
                pen.setColor(QtGui.QColor(*PipeEnum.DISABLED_COLOR.value))
                pen.setStyle(PIPE_STYLES.get(PipeEnum.DRAW_TYPE_DOTTED.value))
                pen.setWidth(3)

        painter.setPen(pen)
        painter.setBrush(self.brush())
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.drawPath(self.path())

        # Draw joint markers at intermediate waypoints (PCB style joint dots)
        if self._waypoints:
            painter.setPen(QtCore.Qt.NoPen)
            joint_color = pen.color()
            painter.setBrush(joint_color)
            for wp in self._waypoints:
                painter.drawEllipse(wp, 3.5, 3.5)

        # QPaintDevice: Cannot destroy paint device that is being painted.
        painter.restore()

    @staticmethod
    def _calc_distance(p1, p2):
        x = math.pow((p2.x() - p1.x()), 2)
        y = math.pow((p2.y() - p1.y()), 2)
        return math.sqrt(x + y)

    def _draw_direction_pointer(self):
        """
        updates the pipe direction pointer arrow.
        """
        if not (self.input_port and self.output_port):
            self._dir_pointer.setVisible(False)
            return

        if self.disabled():
            if not (self._active or self._highlight):
                color = QtGui.QColor(*PipeEnum.DISABLED_COLOR.value)
                pen = self._dir_pointer.pen()
                pen.setColor(color)
                self._dir_pointer.setPen(pen)
                self._dir_pointer.setBrush(color.darker(200))

        if (self.viewer_pipe_layout() in (PipeLayoutEnum.STRAIGHT.value, None)
                and getattr(self, '_p1', None) and getattr(self, '_p2', None)):
            points = [self._p1] + self.waypoints + [self._p2]
            longest_seg = None
            max_len = -1.0
            for i in range(len(points) - 1):
                seg_len = math.hypot(points[i+1].x() - points[i].x(), points[i+1].y() - points[i].y())
                if seg_len > max_len:
                    max_len = seg_len
                    longest_seg = (points[i], points[i+1], seg_len)

            if not longest_seg or longest_seg[2] < 10.0:
                self._dir_pointer.setVisible(False)
                return

            p1, p2, length = longest_seg
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            radians = math.atan2(dy, dx)
            degrees = math.degrees(radians) + 90
            self._dir_pointer.setRotation(degrees)

            best_frac = 0.5
            pos = QtCore.QPointF(p1.x() + best_frac * dx, p1.y() + best_frac * dy)
            self._dir_pointer.setPos(pos)
            self._dir_pointer.setScale(1.0)
            self._dir_pointer.setVisible(True)
        else:
            self._dir_pointer.setVisible(True)
            loc_pt = self.path().pointAtPercent(0.49)
            tgt_pt = self.path().pointAtPercent(0.51)
            radians = math.atan2(tgt_pt.y() - loc_pt.y(),
                                 tgt_pt.x() - loc_pt.x())
            degrees = math.degrees(radians) + 90
            self._dir_pointer.setRotation(degrees)
            self._dir_pointer.setPos(self.path().pointAtPercent(0.5))

            cen_x = self.path().pointAtPercent(0.5).x()
            cen_y = self.path().pointAtPercent(0.5).y()
            dist = math.hypot(tgt_pt.x() - cen_x, tgt_pt.y() - cen_y)

            self._dir_pointer.setVisible(True)
            if dist < 0.3:
                self._dir_pointer.setVisible(False)
                return
            if dist < 1.0:
                self._dir_pointer.setScale(dist)

    def _draw_path_cycled_vertical(self, start_port, pos1, pos2, path):
        """
        Draw pipe vertically around node if connection is cyclic.

        Args:
            start_port (PortItem): port used to draw the starting point.
            pos1 (QPointF): start port position.
            pos2 (QPointF): end port position.
            path (QPainterPath): path to draw.
        """
        n_rect = start_port.node.boundingRect()
        ptype = start_port.port_type
        start_pos = pos1 if ptype == PortTypeEnum.IN.value else pos2
        end_pos = pos2 if ptype == PortTypeEnum.IN.value else pos1

        padding = 40
        top = start_pos.y() - padding
        bottom = end_pos.y() + padding
        path.moveTo(end_pos)
        path.lineTo(end_pos.x(), bottom)
        path.lineTo(end_pos.x() + n_rect.right(), bottom)
        path.lineTo(end_pos.x() + n_rect.right(), top)
        path.lineTo(start_pos.x(), top)
        path.lineTo(start_pos)
        self.setPath(path)

    def _draw_path_cycled_horizontal(self, start_port, pos1, pos2, path):
        """
        Draw pipe horizontally around node if connection is cyclic.

        Args:
            start_port (PortItem): port used to draw the starting point.
            pos1 (QPointF): start port position.
            pos2 (QPointF): end port position.
            path (QPainterPath): path to draw.
        """
        n_rect = start_port.node.boundingRect()
        ptype = start_port.port_type
        start_pos = pos1 if ptype == PortTypeEnum.IN.value else pos2
        end_pos = pos2 if ptype == PortTypeEnum.IN.value else pos1

        padding = 40
        left = end_pos.x() + padding
        right = start_pos.x() - padding
        path.moveTo(start_pos)
        path.lineTo(right, start_pos.y())
        path.lineTo(right, end_pos.y() + n_rect.bottom())
        path.lineTo(left, end_pos.y() + n_rect.bottom())
        path.lineTo(left, end_pos.y())
        path.lineTo(end_pos)
        self.setPath(path)

    def _draw_path_vertical(self, start_port, pos1, pos2, path):
        """
        Draws the vertical path between ports.

        Args:
            start_port (PortItem): port used to draw the starting point.
            pos1 (QPointF): start port position.
            pos2 (QPointF): end port position.
            path (QPainterPath): path to draw.
        """
        if self.viewer_pipe_layout() == PipeLayoutEnum.CURVED.value:
            ctr_offset_y1, ctr_offset_y2 = pos1.y(), pos2.y()
            tangent = abs(ctr_offset_y1 - ctr_offset_y2)

            max_height = start_port.node.boundingRect().height()
            tangent = min(tangent, max_height)
            if start_port.port_type == PortTypeEnum.IN.value:
                ctr_offset_y1 -= tangent
                ctr_offset_y2 += tangent
            else:
                ctr_offset_y1 += tangent
                ctr_offset_y2 -= tangent

            ctr_point1 = QtCore.QPointF(pos1.x(), ctr_offset_y1)
            ctr_point2 = QtCore.QPointF(pos2.x(), ctr_offset_y2)
            path.cubicTo(ctr_point1, ctr_point2, pos2)
            self.setPath(path)
        elif self.viewer_pipe_layout() == PipeLayoutEnum.ANGLE.value:
            ctr_offset_y1, ctr_offset_y2 = pos1.y(), pos2.y()
            distance = abs(ctr_offset_y1 - ctr_offset_y2)/2
            if start_port.port_type == PortTypeEnum.IN.value:
                ctr_offset_y1 -= distance
                ctr_offset_y2 += distance
            else:
                ctr_offset_y1 += distance
                ctr_offset_y2 -= distance

            ctr_point1 = QtCore.QPointF(pos1.x(), ctr_offset_y1)
            ctr_point2 = QtCore.QPointF(pos2.x(), ctr_offset_y2)
            path.lineTo(ctr_point1)
            path.lineTo(ctr_point2)
            path.lineTo(pos2)
            self.setPath(path)

    def _draw_path_horizontal(self, start_port, pos1, pos2, path,end_port):
        
        """
        Draws the horizontal path between ports.

        Args:
            start_port (PortItem): port used to draw the starting point.
            pos1 (QPointF): start port position.
            pos2 (QPointF): end port position.
            path (QPainterPath): path to draw.
        """
        if self.viewer_pipe_layout() == PipeLayoutEnum.CURVED.value:
            ctr_offset_x1, ctr_offset_x2 = pos1.x(), pos2.x()
            tangent = abs(ctr_offset_x1 - ctr_offset_x2)

            max_width = start_port.node.boundingRect().width()
            tangent = min(tangent, max_width)
            if start_port.port_type == PortTypeEnum.IN.value:
                ctr_offset_x1 -= tangent
                ctr_offset_x2 += tangent
            else:
                ctr_offset_x1 += tangent
                ctr_offset_x2 -= tangent

            ctr_point1 = QtCore.QPointF(ctr_offset_x1, pos1.y())
            ctr_point2 = QtCore.QPointF(ctr_offset_x2, pos2.y())
            path.cubicTo(ctr_point1, ctr_point2, pos2)
            self.setPath(path)
        elif self.viewer_pipe_layout() == PipeLayoutEnum.ANGLE.value:
            ctr_offset_x1, ctr_offset_x2 = pos1.x(), pos2.x()
            distance = abs(ctr_offset_x1 - ctr_offset_x2) / 2

            if not end_port:
                if start_port.port_type == PortTypeEnum.IN.value:
                    if not start_port.flipped:
                        ctr_offset_x1 -= distance
                    else:
                        ctr_offset_x1 += distance
                    ctr_offset_x2 += distance # assuming normal output port
                    
                else:
                    if not start_port.flipped:
                        ctr_offset_x1 += distance
                    else:
                        ctr_offset_x1 -= distance
                    ctr_offset_x2 -= distance # assuming normal input port
                    
            else:
                if start_port.port_type == PortTypeEnum.IN.value:
                    if not start_port.flipped:
                        ctr_offset_x1 -= distance
                    else:
                        ctr_offset_x1 += distance
                    if not end_port.flipped:
                        ctr_offset_x2 += distance
                    else:
                        ctr_offset_x2 -= distance

                    
                else:
                    if not start_port.flipped:
                        ctr_offset_x1 += distance
                    else:
                        ctr_offset_x1 -= distance
                    if not end_port.flipped:
                        ctr_offset_x2 -= distance
                    else:
                        ctr_offset_x2+= distance
                

            ctr_point1 = QtCore.QPointF(ctr_offset_x1, pos1.y())
            ctr_point2 = QtCore.QPointF(ctr_offset_x2, pos2.y())
            path.lineTo(ctr_point1)
            path.lineTo(ctr_point2)
            path.lineTo(pos2)
            self.setPath(path)

    def _draw_path_straight_with_bridges(self, pos1, pos2, start_port, end_port, path, notify_crossings=True):
        """
        Draw a straight line or multi-segment joint path from pos1 through any
        waypoints to pos2 with inverted U bridges jumping over older crossing pipes
        (like in electrical schematics / PCB traces).
        """
        self._in_draw_path = True
        try:
            raw_points = [pos1] + self.waypoints + [pos2]
            points = [raw_points[0]]
            for pt in raw_points[1:]:
                if math.hypot(pt.x() - points[-1].x(), pt.y() - points[-1].y()) > 1.0:
                    points.append(pt)
            if len(points) < 2:
                points = raw_points

            # Fast path if bridges calculation is suspended
            if getattr(PipeItem, '_SUSPEND_BRIDGES', False) or not self.scene():
                for pt in points[1:]:
                    path.lineTo(pt)
                self.setPath(path)
                self._bridge_distances = []
                self._draw_direction_pointer()
                return

            BRIDGE_RADIUS = 8.0
            BRIDGE_HEIGHT = 8.0
            is_live = isinstance(self, LivePipeItem)
            current_crossing_pipes = set()
            all_bridge_distances = []

            # Collect ports associated with self to avoid bridging at shared junctions
            self_ports = set()
            if start_port:
                self_ports.add(start_port)
            if end_port:
                self_ports.add(end_port)
            if self.input_port:
                self_ports.add(self.input_port)
            if self.output_port:
                self_ports.add(self.output_port)

            idx = _get_spatial_index(self.scene())

            def get_item_segments(other_item):
                op1 = getattr(other_item, '_p1', None)
                op2 = getattr(other_item, '_p2', None)
                if op1 is None or op2 is None:
                    return []
                owps = getattr(other_item, 'waypoints', [])
                opts = [op1] + owps + [op2]
                return [(opts[j], opts[j + 1]) for j in range(len(opts) - 1)]

            for seg_idx in range(len(points) - 1):
                p_start = points[seg_idx]
                p_end = points[seg_idx + 1]

                dx = p_end.x() - p_start.x()
                dy = p_end.y() - p_start.y()
                L_A = math.hypot(dx, dy)

                if L_A < (2.0 * BRIDGE_RADIUS + 6.0):
                    path.lineTo(p_end)
                    continue

                min_ax = min(p_start.x(), p_end.x()) - BRIDGE_RADIUS
                max_ax = max(p_start.x(), p_end.x()) + BRIDGE_RADIUS
                min_ay = min(p_start.y(), p_end.y()) - BRIDGE_RADIUS
                max_ay = max(p_start.y(), p_end.y()) + BRIDGE_RADIUS

                if idx is not None:
                    candidate_items = idx.query(min_ax, max_ax, min_ay, max_ay)
                else:
                    search_rect = QtCore.QRectF(min_ax, min_ay, max(max_ax - min_ax, 1.0), max(max_ay - min_ay, 1.0))
                    candidate_items = self.scene().items(search_rect)

                seg_bridges = []
                for item in candidate_items:
                    if not isinstance(item, PipeItem) or item is self:
                        continue
                    if isinstance(item, LivePipeItem):
                        continue
                    if not item.isVisible():
                        continue

                    item_ports = set()
                    if item.input_port:
                        item_ports.add(item.input_port)
                    if item.output_port:
                        item_ports.add(item.output_port)
                    if self_ports and (self_ports & item_ports):
                        continue

                    for q1, q2 in get_item_segments(item):
                        min_bx = min(q1.x(), q2.x())
                        max_bx = max(q1.x(), q2.x())
                        min_by = min(q1.y(), q2.y())
                        max_by = max(q1.y(), q2.y())
                        if max_bx < min_ax or min_bx > max_ax or max_by < min_ay or min_by > max_ay:
                            continue

                        sx = q2.x() - q1.x()
                        sy = q2.y() - q1.y()
                        denom = dx * sy - dy * sx
                        if abs(denom) < 1e-6:
                            continue

                        q_dx = q1.x() - p_start.x()
                        q_dy = q1.y() - p_start.y()
                        t = (q_dx * sy - q_dy * sx) / denom
                        u = (q_dx * dy - q_dy * dx) / denom

                        dist_a = t * L_A
                        L_B = math.hypot(sx, sy)
                        dist_b = u * L_B

                        if not (BRIDGE_RADIUS + 4.0 <= dist_a <= L_A - (BRIDGE_RADIUS + 4.0)):
                            continue
                        if not (4.0 <= dist_b <= L_B - 4.0):
                            continue

                        current_crossing_pipes.add(item)
                        if not is_live:
                            item._crossing_pipes.add(self)

                        if is_live or getattr(self, '_pipe_id', 0) > getattr(item, '_pipe_id', 0):
                            Ix = p_start.x() + t * dx
                            Iy = p_start.y() + t * dy
                            seg_bridges.append((dist_a, QtCore.QPointF(Ix, Iy)))

                seg_bridges.sort(key=lambda b: b[0])
                filtered_bridges = []
                last_d = -1e9
                for dist, pt in seg_bridges:
                    if dist - last_d >= 2.0 * BRIDGE_RADIUS:
                        filtered_bridges.append((dist, pt))
                        last_d = dist

                all_bridge_distances.extend(b[0] for b in filtered_bridges)

                if not filtered_bridges:
                    path.lineTo(p_end)
                else:
                    u_x = dx / L_A
                    u_y = dy / L_A

                    if abs(u_x) > 1e-4:
                        if u_x > 0:
                            n_x, n_y = u_y, -u_x
                        else:
                            n_x, n_y = -u_y, u_x
                    else:
                        n_x, n_y = 1.0, 0.0

                    R = BRIDGE_RADIUS
                    H = BRIDGE_HEIGHT
                    ku = 0.15
                    kh = 4.0 / 3.0

                    for dist, pt in filtered_bridges:
                        Ax = pt.x() - R * u_x
                        Ay = pt.y() - R * u_y
                        path.lineTo(Ax, Ay)

                        Bx = pt.x() + R * u_x
                        By = pt.y() + R * u_y

                        C1x = Ax + ku * R * u_x + kh * H * n_x
                        C1y = Ay + ku * R * u_y + kh * H * n_y
                        C2x = Bx - ku * R * u_x + kh * H * n_x
                        C2y = By - ku * R * u_y + kh * H * n_y

                        path.cubicTo(
                            QtCore.QPointF(C1x, C1y),
                            QtCore.QPointF(C2x, C2y),
                            QtCore.QPointF(Bx, By)
                        )

                    path.lineTo(p_end)

            self._bridge_distances = all_bridge_distances
            self.setPath(path)
            self._draw_direction_pointer()

            # Refresh crossing pipes that need update (newer pipes jumping over self)
            if not is_live and notify_crossings:
                old_crossing = self._crossing_pipes - current_crossing_pipes
                for p in old_crossing:
                    p._crossing_pipes.discard(self)

                pipes_to_refresh = (self._crossing_pipes | current_crossing_pipes) - {self}
                self._crossing_pipes = current_crossing_pipes
                for p in pipes_to_refresh:
                    if (
                        p.scene() and
                        getattr(p, '_pipe_id', 0) > getattr(self, '_pipe_id', 0) and
                        not getattr(p, '_in_draw_path', False)
                    ):
                        p.draw_path(p.input_port, p.output_port, notify_crossings=False)
        finally:
            self._in_draw_path = False

    def draw_path(self, start_port, end_port=None, cursor_pos=None, notify_crossings=True):
        """
        Draws the path between ports.

        Args:
            start_port (PortItem): port used to draw the starting point.
            end_port (PortItem): port used to draw the end point.
            cursor_pos (QtCore.QPointF): cursor position if specified this
                will be the draw end point.
            notify_crossings (bool): if true, refresh crossing pipes.
        """
        if not start_port:
            return

        # get start / end positions.
        if cursor_pos:
            p_start_port = start_port
            p_end_port = None
            pos1 = p_start_port.mapToScene(p_start_port.boundingRect().center())
            pos2 = QtCore.QPointF(cursor_pos)
        elif end_port:
            if self.output_port and self.input_port:
                p_start_port = self.output_port
                p_end_port = self.input_port
            elif start_port.port_type == PortTypeEnum.OUT.value:
                p_start_port = start_port
                p_end_port = end_port
            else:
                p_start_port = end_port
                p_end_port = start_port

            pos1 = p_start_port.mapToScene(p_start_port.boundingRect().center())
            pos2 = p_end_port.mapToScene(p_end_port.boundingRect().center())
        else:
            return

        # visibility check for connected pipe.
        if self.input_port and self.output_port:
            is_visible = all([
                self._input_port.isVisible(),
                self._output_port.isVisible(),
                self._input_port.node.isVisible(),
                self._output_port.node.isVisible()
            ])
            self.setVisible(is_visible)

            # don't draw pipe if a port or node is not visible.
            if not is_visible:
                return

        self._p1 = QtCore.QPointF(pos1)
        self._p2 = QtCore.QPointF(pos2)
        idx = _get_spatial_index(self.scene())
        if idx is not None and not isinstance(self, LivePipeItem):
            idx.update_pipe(self, pos1, pos2)

        line = QtCore.QLineF(pos1, pos2)
        path = QtGui.QPainterPath()

        direction = self.viewer_layout_direction()

        if p_end_port and not self.viewer().acyclic:
            if p_end_port.node == p_start_port.node and not self._waypoints:
                if direction is LayoutDirectionEnum.VERTICAL.value:
                    self._draw_path_cycled_vertical(
                        p_start_port, pos1, pos2, path
                    )
                    self._draw_direction_pointer()
                    return
                elif direction is LayoutDirectionEnum.HORIZONTAL.value:
                    self._draw_path_cycled_horizontal(
                        p_start_port, pos1, pos2, path
                    )
                    self._draw_direction_pointer()
                    return

        path.moveTo(pos1.x(), pos1.y())

        if self.viewer_pipe_layout() in (PipeLayoutEnum.STRAIGHT.value, None) or self._waypoints:
            self._draw_path_straight_with_bridges(pos1, pos2, p_start_port, p_end_port, path, notify_crossings=notify_crossings)
            return

        if direction is LayoutDirectionEnum.VERTICAL.value:
            self._draw_path_vertical(p_start_port, pos1, pos2, path)
        elif direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._draw_path_horizontal(p_start_port, pos1, pos2, path, p_end_port)

        self._draw_direction_pointer()

    def reset_path(self):
        """
        reset the pipe initial path position.
        """
        self._p1 = None
        self._p2 = None
        self._bridge_distances = []
        self._waypoints = []
        if self.scene():
            idx = _get_spatial_index(self.scene())
            if idx is not None:
                idx.remove_pipe(self)
        path = QtGui.QPainterPath(QtCore.QPointF(0.0, 0.0))
        self.setPath(path)
        self._draw_direction_pointer()

    def port_from_pos(self, pos, reverse=False):
        """
        Args:
            pos (QtCore.QPointF): current scene position.
            reverse (bool): false to return the nearest port.

        Returns:
            PortItem: port item.
        """
        inport_pos = self.input_port.mapToScene(self.input_port.boundingRect().center())
        outport_pos = self.output_port.mapToScene(self.output_port.boundingRect().center())
        input_dist = self._calc_distance(inport_pos, pos)
        output_dist = self._calc_distance(outport_pos, pos)
        if input_dist < output_dist:
            port = self.output_port if reverse else self.input_port
        else:
            port = self.input_port if reverse else self.output_port
        return port

    def viewer(self):
        """
        Returns:
            NodeViewer: node graph viewer.
        """
        if self.scene():
            return self.scene().viewer()

    def viewer_pipe_layout(self):
        """
        Returns:
            int: pipe layout mode.
        """
        viewer = self.viewer()
        if viewer:
            return viewer.get_pipe_layout()

    def viewer_layout_direction(self):
        """
        Returns:
            int: graph layout mode.
        """
        viewer = self.viewer()
        if viewer:
            return viewer.get_layout_direction()

    def set_pipe_styling(self, color, width=2, style=0):
        """
        Args:
            color (list or tuple): (r, g, b, a) values 0-255
            width (int): pipe width.
            style (int): pipe style.
        """
        pen = self.pen()
        pen.setWidth(width)
        pen.setColor(QtGui.QColor(*color))
        pen.setStyle(PIPE_STYLES.get(style))
        pen.setJoinStyle(QtCore.Qt.MiterJoin)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        self.setPen(pen)
        self.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))

        pen = self._dir_pointer.pen()
        pen.setJoinStyle(QtCore.Qt.MiterJoin)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setWidth(width)
        pen.setColor(QtGui.QColor(*color))
        self._dir_pointer.setPen(pen)
        self._dir_pointer.setBrush(QtGui.QColor(*color).darker(200))

    def activate(self):
        self._active = True
        self.set_pipe_styling(
            color=PipeEnum.ACTIVE_COLOR.value,
            width=3,
            style=PipeEnum.DRAW_TYPE_DEFAULT.value
        )

    def active(self):
        return self._active

    def highlight(self):
        self._highlight = True
        self.set_pipe_styling(
            color=PipeEnum.HIGHLIGHT_COLOR.value,
            width=2,
            style=PipeEnum.DRAW_TYPE_DEFAULT.value
        )

    def highlighted(self):
        return self._highlight

    def reset(self):
        """
        reset the pipe state and styling.
        """
        self._active = False
        self._highlight = False
        self.set_pipe_styling(color=self.color, width=2, style=self.style)
        self._draw_direction_pointer()

    def set_connections(self, port1, port2):
        """
        Args:
            port1 (PortItem): port item object.
            port2 (PortItem): port item object.
        """
        ports = {
            port1.port_type: port1,
            port2.port_type: port2
        }
        self.input_port = ports[PortTypeEnum.IN.value]
        self.output_port = ports[PortTypeEnum.OUT.value]
        ports[PortTypeEnum.IN.value].add_pipe(self)
        ports[PortTypeEnum.OUT.value].add_pipe(self)

    def disabled(self):
        """
        Returns:
            bool: true if pipe is a disabled connection.
        """
        if self.input_port and self.input_port.node.disabled:
            return True
        if self.output_port and self.output_port.node.disabled:
            return True
        return False

    @property
    def input_port(self):
        return self._input_port

    @input_port.setter
    def input_port(self, port):
        if isinstance(port, PortItem) or not port:
            self._input_port = port
        else:
            self._input_port = None

    @property
    def output_port(self):
        return self._output_port

    @output_port.setter
    def output_port(self, port):
        if isinstance(port, PortItem) or not port:
            self._output_port = port
        else:
            self._output_port = None

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = color

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, style):
        self._style = style

    def delete(self):
        crossing_to_notify = list(getattr(self, '_crossing_pipes', []))
        for p in crossing_to_notify:
            p._crossing_pipes.discard(self)
        self._crossing_pipes.clear()
        if self.input_port and self.input_port.connected_pipes:
            self.input_port.remove_pipe(self)
        if self.output_port and self.output_port.connected_pipes:
            self.output_port.remove_pipe(self)
        if self.scene():
            idx = _get_spatial_index(self.scene())
            if idx is not None:
                idx.remove_pipe(self)
            self.scene().removeItem(self)
        for p in crossing_to_notify:
            try:
                if p.scene() and not getattr(p, '_in_draw_path', False):
                    p.draw_path(p.input_port, p.output_port)
            except Exception:
                pass


class LivePipeItem(PipeItem):
    """
    Live Pipe item used for drawing the live connection with the cursor.
    """

    def __init__(self):
        super(LivePipeItem, self).__init__()
        self._pipe_id = float('inf')
        self.setZValue(Z_VAL_NODE_WIDGET + 1)

        self.color = PipeEnum.ACTIVE_COLOR.value
        self.style = PipeEnum.DRAW_TYPE_DASHED.value
        self.set_pipe_styling(color=self.color, width=3, style=self.style)

        self.shift_selected = False

        self._idx_pointer = LivePipePolygonItem(self)
        self._idx_pointer.setPolygon(self._poly)
        self._idx_pointer.setBrush(QtGui.QColor(*self.color).darker(300))
        pen = self._idx_pointer.pen()
        pen.setWidth(self.pen().width())
        pen.setColor(self.pen().color())
        pen.setJoinStyle(QtCore.Qt.MiterJoin)
        self._idx_pointer.setPen(pen)

        color = self.pen().color()
        color.setAlpha(80)
        self._idx_text = QtWidgets.QGraphicsTextItem(self)
        self._idx_text.setDefaultTextColor(color)
        font = self._idx_text.font()
        font.setPointSize(7)
        self._idx_text.setFont(font)

    def hoverEnterEvent(self, event):
        """
        re-implemented back to the base default behaviour or the pipe will
        lose it styling when another pipe is selected.
        """
        QtWidgets.QGraphicsPathItem.hoverEnterEvent(self, event)

    def draw_path(self, start_port, end_port=None, cursor_pos=None, color=None):
        """
        re-implemented to also update the index pointer arrow position.

        Args:
            start_port (PortItem): port used to draw the starting point.
            end_port (PortItem): port used to draw the end point.
            cursor_pos (QtCore.QPointF): cursor position if specified this
                will be the draw end point.
            color (list[int]): override arrow index pointer color. (r, g, b)
        """
        super(LivePipeItem, self).draw_path(start_port, end_port, cursor_pos)
        self.draw_index_pointer(start_port, cursor_pos, color)

    def draw_index_pointer(self, start_port, cursor_pos, color=None):
        """
        Update the index pointer arrow position and direction when the
        live pipe path is redrawn.

        Args:
            start_port (PortItem): start port item.
            cursor_pos (QtCore.QPoint): cursor scene position.
            color (list[int]): override arrow index pointer color. (r, g, b).
        """
        text_rect = self._idx_text.boundingRect()

        transform = QtGui.QTransform()
        transform.translate(cursor_pos.x(), cursor_pos.y())
        if self.viewer_layout_direction() is LayoutDirectionEnum.VERTICAL.value:
            text_pos = (
                cursor_pos.x() + (text_rect.width() / 2.5),
                cursor_pos.y() - (text_rect.height() / 2)
            )
            if start_port.port_type == PortTypeEnum.OUT.value:
                transform.rotate(180)
        elif self.viewer_layout_direction() is LayoutDirectionEnum.HORIZONTAL.value:
            text_pos = (
                cursor_pos.x() - (text_rect.width() / 2),
                cursor_pos.y() - (text_rect.height() * 1.25)
            )
            if start_port.port_type == PortTypeEnum.IN.value:
                transform.rotate(-90)
            else:
                transform.rotate(90)
        self._idx_text.setPos(*text_pos)
        self._idx_text.setPlainText('{}'.format(start_port.name))

        self._idx_pointer.setPolygon(transform.map(self._poly))

        pen_color = QtGui.QColor(*PipeEnum.HIGHLIGHT_COLOR.value)
        if isinstance(color, (list, tuple)):
            pen_color = QtGui.QColor(*color)

        pen = self._idx_pointer.pen()
        pen.setColor(pen_color)
        self._idx_pointer.setBrush(pen_color.darker(300))
        self._idx_pointer.setPen(pen)


class LivePipePolygonItem(QtWidgets.QGraphicsPolygonItem):
    """
    Custom live pipe polygon shape.
    """

    def __init__(self, parent):
        super(LivePipePolygonItem, self).__init__(parent)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)

    def paint(self, painter, option, widget):
        """
        Args:
            painter (QtGui.QPainter): painter used for drawing the item.
            option (QtGui.QStyleOptionGraphicsItem):
                used to describe the parameters needed to draw.
            widget (QtWidgets.QWidget): not used.
        """
        painter.save()
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawPolygon(self.polygon())
        painter.restore()
