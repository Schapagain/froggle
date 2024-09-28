import os
import typing
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QVBoxLayout,
    QDialog, QDialogButtonBox,
    QLabel, QTableWidget,
    QTableWidgetItem, QWidget,
    QProgressBar)
import qtawesome as qta


class LabelWithIcon(QWidget):

    HorizontalSpacing = 2

    def __init__(self, qta_id, iconSize, text="", final_stretch=True):
        super(QWidget, self).__init__()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        layout.addSpacing(self.HorizontalSpacing)
        self.label = QLabel(text)
        layout.addWidget(self.label)
        self.icon = QLabel()
        self.setIcon(
            qta.icon(
                qta_id,
            ).pixmap(iconSize))
        layout.addWidget(self.icon)

        if final_stretch:
            layout.addStretch()

    def setText(self, text):
        self.label.setText(text)

    def setIcon(self, icon):
        self.icon.setPixmap(icon)


class ProgressBar(QWidget):
    IconSize = QSize(20, 20)

    def __init__(self, progress_text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pbar = QProgressBar()
        self.pbar.setGeometry(30, 40, 200, 10)
        self.text = progress_text
        self.label = LabelWithIcon(
            "fa5s.circle-notch", self.IconSize, text=self.text)
        self.done = False
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.label)
        layout.addWidget(self.pbar)

    def setProgress(self,
                    progress,
                    progress_count: typing.Union[int, None] = None,
                    total_count: typing.Union[int, None] = None
                    ):
        self.pbar.setValue(progress)
        progress_text = ""
        if progress_count is not None and total_count is not None:
            progress_text = f"({progress_count}/{total_count} done)"
        if progress == 100:
            self.label.setText(self.text + " (Done)")
            self.pbar.setVisible(False)
            self.label.setIcon(
                qta.icon(
                    "fa5s.check-circle",
                    color='green'
                ).pixmap(self.IconSize))
        else:
            self.label.setText(f"{self.text} {progress_text}")
            self.label.setIcon(
                qta.icon(
                    "fa5s.circle-notch"
                ).pixmap(self.IconSize))
            self.pbar.setVisible(True)


class TableView(QTableWidget):
    def __init__(self, data, row, col):
        super(TableView, self).__init__()
        self.setRowCount(row)
        self.setColumnCount(col)
        self.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._data = data
        self._selected_row = 1
        self.setData()
        self.setFixedWidth(400)
        self._resize()
        self.show()

    def _resize(self):
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

        header = self.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def highlightRow(self, row: int):
        self.selectRow(row)

    def setData(self):
        for i, row in enumerate(self._data["rows"]):
            for j, col in enumerate(row):
                self.setItem(i, j, QTableWidgetItem(str(col)))
        self.setHorizontalHeaderLabels(self._data["headers"])

    def updateData(self, data):
        self._data = data
        num_rows = len(data["rows"])
        num_cols = len(data["rows"][0])
        self.setColumnCount(num_cols)
        self.setRowCount(num_rows)
        self.setData()
        self._resize()

    def toCSV(self, directory: typing.Union[str, os.PathLike]):
        '''
        Save table data as a csv file in the given directory
        '''
        DEFAULT_FILE_NAME = 'Egg_Counts.csv'
        with open(os.path.join(directory, DEFAULT_FILE_NAME), 'w+') as fo:
            fo.writelines(",".join(self._data["headers"]))
            fo.write("\n")
            for row in self._data["rows"]:
                fo.write(",".join(row) + "\n")


class CustomDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("HELLO!")

        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message = QLabel("Images are not loaded yet. Select a zip file first")
        layout.addWidget(message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
