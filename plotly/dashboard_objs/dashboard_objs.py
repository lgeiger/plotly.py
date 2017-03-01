"""
dashboard_objs
==========

A module for creating and manipulating dashboard content. You can create
a Dashboard object, insert boxes, swap boxes, remove a box and get an HTML
preview of the Dashboard.
"""

import pprint

from plotly import exceptions, optional_imports
from plotly.utils import node_generator

IPython = optional_imports.get_module('IPython')

# default HTML parameters
MASTER_WIDTH = 400
MASTER_HEIGHT = 400
FONT_SIZE = 10

ID_NOT_VALID_MESSAGE = (
    "Your box_id must be a number in your dashboard. To view a "
    "representation of your dashboard run get_preview()."
)


def _empty_box():
    empty_box = {
        'type': 'box',
        'boxType': 'empty'
    }
    return empty_box


def _box(fileId='', shareKey=None, title=''):
    box = {
        'type': 'box',
        'boxType': 'plot',
        'fileId': fileId,
        'shareKey': shareKey,
        'title': title
    }
    return box


def _container(box_1=None, box_2=None, size=MASTER_HEIGHT,
               sizeUnit='px', direction='vertical'):
    if box_1 is None:
        box_1 = _empty_box()
    if box_2 is None:
        box_2 = _empty_box()

    container = {
        'type': 'split',
        'size': size,
        'sizeUnit': sizeUnit,
        'direction': direction,
        'first': box_1,
        'second': box_2
    }
    return container

dashboard_html = ("""
<!DOCTYPE HTML>
<html>
  <head>
    <style>
      body {{
        margin: 0px;
        padding: 0px;
      }}
    </style>
  </head>
  <body>
    <canvas id="myCanvas" width="400" height="400"></canvas>
    <script>
      var canvas = document.getElementById('myCanvas');
      var context = canvas.getContext('2d');
      <!-- Dashboard -->
      context.beginPath();
      context.rect(0, 0, {width}, {height});
      context.lineWidth = 2;
      context.strokeStyle = 'black';
      context.stroke();
      </script>
  </body>
</html>
""".format(width=MASTER_WIDTH, height=MASTER_HEIGHT))


def _draw_line_through_box(dashboard_html, top_left_x, top_left_y, box_w,
                           box_h, direction='vertical'):
    is_horizontal = (direction == 'horizontal')

    if is_horizontal:
        new_top_left_x = top_left_x + box_w / 2
        new_top_left_y = top_left_y
        new_box_w = 1
        new_box_h = box_h
    else:
        new_top_left_x = top_left_x
        new_top_left_y = top_left_y + box_h / 2
        new_box_w = box_w
        new_box_h = 1

    html_box = """<!-- Draw some lines in -->
          context.beginPath();
          context.rect({top_left_x}, {top_left_y}, {box_w}, {box_h});
          context.lineWidth = 1;
          context.strokeStyle = 'black';
          context.stroke();
    """.format(top_left_x=new_top_left_x, top_left_y=new_top_left_y,
               box_w=new_box_w, box_h=new_box_h)

    index_for_new_box = dashboard_html.find('</script>') - 1
    dashboard_html = (dashboard_html[:index_for_new_box] + html_box +
                      dashboard_html[index_for_new_box:])
    return dashboard_html


def _add_html_text(dashboard_html, text, top_left_x, top_left_y, box_w, box_h):
    html_text = """<!-- Insert box numbers -->
          context.font = '{font_size}pt Times New Roman';
          context.textAlign = 'center';
          context.fillText({text}, {top_left_x} + 0.5*{box_w}, {top_left_y} + 0.5*{box_h});
    """.format(text=text, top_left_x=top_left_x, top_left_y=top_left_y,
               box_w=box_w, box_h=box_h, font_size=FONT_SIZE)

    index_to_add_text = dashboard_html.find('</script>') - 1
    dashboard_html = (dashboard_html[:index_to_add_text] + html_text +
                      dashboard_html[index_to_add_text:])
    return dashboard_html


class Dashboard(dict):
    def __init__(self, content=None):
        if content is None:
            content = {}

        if not content:
            self['layout'] = _empty_box()
            self['version'] = 2
            self['settings'] = {}
        else:
            self['layout'] = content['layout']
            self['version'] = content['version']
            self['settings'] = content['settings']

        self._set_container_sizes()

    def _compute_box_ids(self):
        box_ids_to_path = {}
        all_nodes = list(node_generator(self['layout']))

        for node in all_nodes:
            if (node[1] != () and node[0]['type'] == 'box'
                    and node[0]['boxType'] != 'empty'):
                try:
                    max_id = max(box_ids_to_path.keys())
                except ValueError:
                    max_id = 0
                box_ids_to_path[max_id + 1] = list(node[1])

        return box_ids_to_path

    def _insert(self, box_or_container, path):
        if any(first_second not in ['first', 'second']
               for first_second in path):
            raise exceptions.PlotlyError(
                "Invalid path. Your 'path' list must only contain "
                "the strings 'first' and 'second'."
            )

        if 'first' in self['layout']:
            loc_in_dashboard = self['layout']
            for index, first_second in enumerate(path):
                if index != len(path) - 1:
                    loc_in_dashboard = loc_in_dashboard[first_second]
                else:
                    loc_in_dashboard[first_second] = box_or_container

        else:
            self['layout'] = box_or_container

    def _set_container_sizes(self):
        all_nodes = list(node_generator(self['layout']))

        all_paths = []
        for node in all_nodes:
            all_paths.append(list(node[1]))
        if ['second'] in all_paths:
            all_paths.remove(['second'])

        # set dashboard_height proportional to max_path_len
        max_path_len = max(len(path) for path in all_paths)
        dashboard_height = 500 + 250 * max_path_len
        self['layout']['size'] = dashboard_height
        self['layout']['sizeUnit'] = 'px'

        for path in all_paths:
            if len(path) != 0:
                if self._path_to_box(path)['type'] == 'split':
                    self._path_to_box(path)['size'] = 50
                    self._path_to_box(path)['sizeUnit'] = '%'

    def _path_to_box(self, path):
        loc_in_dashboard = self['layout']
        for first_second in path:
            loc_in_dashboard = loc_in_dashboard[first_second]
        return loc_in_dashboard

    def get_box(self, box_id):
        """Returns box from box_id number."""
        box_ids_to_path = self._compute_box_ids()
        loc_in_dashboard = self['layout']

        if box_id not in box_ids_to_path.keys():
            raise exceptions.PlotlyError(ID_NOT_VALID_MESSAGE)
        for first_second in box_ids_to_path[box_id]:
            loc_in_dashboard = loc_in_dashboard[first_second]
        return loc_in_dashboard

    def get_preview(self):
        """
        Returns JSON or HTML respresentation of the dashboard.

        If IPython is not imported, returns a pretty print of the dashboard
        dict. Otherwise, returns an IPython.core.display.HTML display of the
        dashboard.

        The algorithm - iteratively go through all paths of the dashboards
        moving from shorter to longer paths. Checking the box or container
        that sits at the end each path, if you find a container, draw a line
        to divide the current box into two, and record the top-left
        coordinates and box width and height resulting from the two boxes
        along with the corresponding path. When the path points to a box,
        draw the number associated with that box in the center of the box.
        """
        if IPython is None:
            pprint.pprint(self)
            return

        x = 0
        y = 0
        box_w = MASTER_WIDTH
        box_h = MASTER_HEIGHT
        html_figure = dashboard_html
        box_ids_to_path = self._compute_box_ids()
        # used to store info about box dimensions
        path_to_box_specs = {}
        first_box_specs = {
            'top_left_x': x,
            'top_left_y': y,
            'box_w': box_w,
            'box_h': box_h
        }
        # uses tuples to store paths as for hashable keys
        path_to_box_specs[('first',)] = first_box_specs

        # generate all paths
        all_nodes = list(node_generator(self['layout']))

        all_paths = []
        for node in all_nodes:
            all_paths.append(list(node[1]))
        if ['second'] in all_paths:
            all_paths.remove(['second'])

        max_path_len = max(len(path) for path in all_paths)
        for path_len in range(1, max_path_len + 1):
            for path in [path for path in all_paths if len(path) == path_len]:
                current_box_specs = path_to_box_specs[tuple(path)]

                if self._path_to_box(path)['type'] == 'split':
                    html_figure = _draw_line_through_box(
                        html_figure,
                        current_box_specs['top_left_x'],
                        current_box_specs['top_left_y'],
                        current_box_specs['box_w'],
                        current_box_specs['box_h'],
                        direction=self._path_to_box(path)['direction']
                    )

                    # determine the specs for resulting two boxes from split
                    is_horizontal = (
                        self._path_to_box(path)['direction'] == 'horizontal'
                    )
                    x = current_box_specs['top_left_x']
                    y = current_box_specs['top_left_y']
                    box_w = current_box_specs['box_w']
                    box_h = current_box_specs['box_h']

                    if is_horizontal:
                        new_box_w = box_w / 2
                        new_box_h = box_h
                        new_top_left_x = x + box_w / 2
                        new_top_left_y = y

                    else:
                        new_box_w = box_w
                        new_box_h = box_h / 2
                        new_top_left_x = x
                        new_top_left_y = y + box_h / 2

                    box_1_specs = {
                        'top_left_x': x,
                        'top_left_y': y,
                        'box_w': new_box_w,
                        'box_h': new_box_h
                    }
                    box_2_specs = {
                        'top_left_x': new_top_left_x,
                        'top_left_y': new_top_left_y,
                        'box_w': new_box_w,
                        'box_h': new_box_h
                    }

                    path_to_box_specs[tuple(path) + ('first',)] = box_1_specs
                    path_to_box_specs[tuple(path) + ('second',)] = box_2_specs

                elif self._path_to_box(path)['type'] == 'box':
                    for box_id in box_ids_to_path:
                        if box_ids_to_path[box_id] == path:
                            number = box_id

                    html_figure = _add_html_text(
                        html_figure, number,
                        path_to_box_specs[tuple(path)]['top_left_x'],
                        path_to_box_specs[tuple(path)]['top_left_y'],
                        path_to_box_specs[tuple(path)]['box_w'],
                        path_to_box_specs[tuple(path)]['box_h'],
                    )

        # display HTML representation
        return IPython.display.HTML(html_figure)

    def insert(self, box, side='above', box_id=None):
        """
        Insert a box into your dashboard layout.

        :param (dict) box: the box you are inserting into the dashboard.
        :param (str) side: specifies where your new box is going to be placed
            relative to the given 'box_id'. Valid values are 'above', 'below',
            'left', and 'right'.
        :param (int) box_id: the box id which is used as the reference box for
            the insertion of the box.
        """
        box_ids_to_path = self._compute_box_ids()
        init_box = {
            'type': 'box',
            'boxType': 'plot',
            'fileId': '',
            'shareKey': None,
            'title': ''
        }

        # force box to have all valid box keys
        for key in init_box.keys():
            if key not in box.keys():
                box[key] = init_box[key]

        # doesn't need box_id or side specified for first box
        if 'first' not in self['layout']:
            self._insert(_container(box, _empty_box()), [])
        else:
            if box_id is None:
                raise exceptions.PlotlyError(
                    "Make sure the box_id is specfied if there is at least "
                    "one box in your dashboard."
                )
            if box_id not in box_ids_to_path:
                raise exceptions.PlotlyError(ID_NOT_VALID_MESSAGE)
            if side == 'above':
                old_box = self.get_box(box_id)
                self._insert(
                    _container(box, old_box, direction='vertical'),
                    box_ids_to_path[box_id]
                )
            elif side == 'below':
                old_box = self.get_box(box_id)
                self._insert(
                    _container(old_box, box, direction='vertical'),
                    box_ids_to_path[box_id]
                )
            elif side == 'left':
                old_box = self.get_box(box_id)
                self._insert(
                    _container(box, old_box, direction='horizontal'),
                    box_ids_to_path[box_id]
                )
            elif side == 'right':
                old_box = self.get_box(box_id)
                self._insert(
                    _container(old_box, box, direction='horizontal'),
                    box_ids_to_path[box_id]
                )
            else:
                raise exceptions.PlotlyError(
                    "If there is at least one box in your dashboard, you "
                    "must specify a valid side value. You must choose from "
                    "'above', 'below', 'left', and 'right'."
                )

        self._set_container_sizes()

    def remove(self, box_id):
        """Remove a box from the dashboard by its box_id."""
        box_ids_to_path = self._compute_box_ids()
        if box_id not in box_ids_to_path:
            raise exceptions.PlotlyError(ID_NOT_VALID_MESSAGE)

        path = box_ids_to_path[box_id]
        if path != ['first']:
            container_for_box_id = self._path_to_box(path[:-1])
            if path[-1] == 'first':
                adjacent_path = 'second'
            elif path[-1] == 'second':
                adjacent_path = 'first'
            adjacent_box = container_for_box_id[adjacent_path]

            self._insert(adjacent_box, path[:-1])
        else:
            self['layout'] = _empty_box()

        self._set_container_sizes()

    def swap(self, box_id_1, box_id_2):
        """Swap two boxes with their specified ids."""
        box_ids_to_path = self._compute_box_ids()
        box_1 = self.get_box(box_id_1)
        box_2 = self.get_box(box_id_2)

        box_1_path = box_ids_to_path[box_id_1]
        box_2_path = box_ids_to_path[box_id_2]

        for pairs in [(box_1_path, box_2), (box_2_path, box_1)]:
            loc_in_dashboard = self['layout']
            for first_second in pairs[0][:-1]:
                loc_in_dashboard = loc_in_dashboard[first_second]
            loc_in_dashboard[pairs[0][-1]] = pairs[1]

        self._set_container_sizes()
