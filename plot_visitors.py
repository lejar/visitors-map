import collections
import math
import os
import typing

import bokeh.plotting
import bokeh.tile_providers
import geocoder
import pandas
from PySide6 import QtWidgets


EQUATORIAL_RADIUS = 6378137


class DataDict(typing.TypedDict):
    y: typing.List[float]
    x: typing.List[float]
    address: typing.List[str]
    sizes: typing.List[int]


def build_world_figure() -> bokeh.plotting.Figure:
    figure = bokeh.plotting.figure(
        x_range=(-math.pi * EQUATORIAL_RADIUS, math.pi * EQUATORIAL_RADIUS),
        y_range=(-math.pi * EQUATORIAL_RADIUS, math.pi * EQUATORIAL_RADIUS),
        x_axis_type='mercator',
        y_axis_type='mercator',
        plot_width=1920,
        plot_height=1080,
    )

    tile_provider = bokeh.tile_providers.get_provider(bokeh.tile_providers.OSM)
    figure.add_tile(tile_provider)

    return figure


def wgs84_to_web_mercator(latitude: float, longitude: float) -> typing.Tuple[float, float]:
    x = longitude * (EQUATORIAL_RADIUS * math.pi / 180.0)
    y = math.log(math.tan((90 + latitude) * math.pi / 360.0)) * EQUATORIAL_RADIUS
    return x, y


def get_latitude_longitude(address: str) -> typing.Union[typing.Tuple[float, float], None]:
    data = geocoder.osm(address)
    return data.latlng


class MainWindow(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        self.excel_data: typing.Optional[pandas.DataFrame] = None

        super().__init__(parent)
        self.setWindowTitle('Visitor Map Maker')

        layout = QtWidgets.QGridLayout(self)

        self.excel_file_label = QtWidgets.QLabel('Excel file to read')
        self.excel_file = QtWidgets.QLineEdit()
        self.excel_file.setReadOnly(True)

        self.excel_file_button = QtWidgets.QPushButton('...')
        self.excel_file_button.released.connect(self.import_excel_file)

        layout.addWidget(self.excel_file_label, 0, 0)
        layout.addWidget(self.excel_file, 0, 1)
        layout.addWidget(self.excel_file_button, 0, 2)

        # Address column text
        self.address_column_label = QtWidgets.QLabel('Address column text')
        self.address_column = QtWidgets.QComboBox()

        layout.addWidget(self.address_column_label, 1, 0)
        layout.addWidget(self.address_column, 1, 1)

        self.make_map_button = QtWidgets.QPushButton('Make map')
        self.make_map_button.setEnabled(False)
        self.make_map_button.released.connect(self.make_map)
        layout.addWidget(self.make_map_button, 2, 2)

    def import_excel_file(self) -> None:
        """
        Parses the chosen file and extracts the column names. The user then uses these column names to choose which
        column to read the addresses from.
        """
        # Ask for the excel file to parse.
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            None,
            'Choose Excel File',
            os.getcwd(),
            '*.xlsx',
        )

        # The user cancelled.
        if not filename:
            self.make_map_button.setEnabled(False)
            return None

        # Verify that the file exists.
        if not os.path.exists(filename):
            QtWidgets.QMessageBox.critical(
                None,
                'Error',
                f'File "{filename}" does not exist.',
            )
            self.make_map_button.setEnabled(False)
            return None

        self.excel_file.setText(filename)
        self.excel_data = pandas.read_excel(filename)
        columns = list(self.excel_data.columns)
        if not columns:
            QtWidgets.QMessageBox.critical(
                None,
                'Error',
                f'No columns found in "{filename}".',
            )
            self.make_map_button.setEnabled(False)
            return None

        self.address_column.clear()
        self.address_column.addItems(columns)
        self.make_map_button.setEnabled(True)

    def make_map(self) -> None:
        """
        Parses the given excel file and uses Open Street Map to get the lat/lon of each address. Then use bokeh to plot
        the addresses on a map of the world.
        """
        assert self.excel_data is not None
        addresses = [i.lower() for i in self.excel_data[self.address_column.currentText()]]

        # There was nothing in the column.
        if not addresses:
            QtWidgets.QMessageBox.critical(
                None,
                'Error',
                f'No entries found in the selected column.',
            )
            return

        # Get the latitude and longitude of all the unique addresses.
        address_count = collections.Counter(addresses)
        web_mercator_positions: typing.Dict[str, typing.Tuple[float, float]] = {}
        could_not_find: typing.List[str] = []

        progress = QtWidgets.QProgressBar(self)
        progress.setWindowTitle('Fetching Location Data...')
        progress.setRange(0, len(address_count))

        for i, address in enumerate(address_count.keys()):
            progress.setValue(i)

            latitude_longitude = get_latitude_longitude(address)
            # If open street maps does not find the address, the coordinates will be None.
            if latitude_longitude is None:
                could_not_find.append(address)
                continue

            web_mercator_positions[address] = wgs84_to_web_mercator(*latitude_longitude)

        progress.hide()

        if could_not_find:
            QtWidgets.QMessageBox.warning(
                None,
                'Warning',
                'Could not find the following addresses:\n' + '\n\t'.join(could_not_find),
            )

        # Populate the data for our world map. The size of the circle on the map will be proportional to the number of times
        # the address shows up.
        data_dict = DataDict({
            'y': [],
            'x': [],
            'address': [],
            'sizes': [],
        })
        for address, count in address_count.items():
            if address in could_not_find:
                continue

            data_dict['y'].append(web_mercator_positions[address][1])
            data_dict['x'].append(web_mercator_positions[address][0])
            data_dict['address'].append(address)
            # We limit the size of the circle, because otherwise a single location might get too big.
            data_dict['sizes'].append(min(count * 4, 20))

        source = bokeh.models.ColumnDataSource(data=data_dict)

        bokeh.plotting.output_file('tile.html')
        figure = build_world_figure()
        figure.circle(x='x', y='y', size='sizes', fill_color='blue', fill_alpha=0.8, source=source)

        TOOLTIPS = [
            ('Name', '@address'),
        ]
        figure.add_tools(bokeh.models.HoverTool(tooltips=TOOLTIPS))

        bokeh.plotting.show(figure)


def main() -> None:
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == '__main__':
    main()
