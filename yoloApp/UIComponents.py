

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem)


class TableView(QTableWidget):
    def __init__(self, data, *args):
        QTableWidget.__init__(self, *args)
        self.data = data
        self.setData()
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.show()

    def setData(self):
        for i, row in enumerate(self.data):
            print(f'processing index: {i} and row: {row}')
            img = row.get("image_name")
            num_unfertilized = row.get("num_unfertilized")
            num_fertilized = row.get("num_fertilized")
            print(img, num_fertilized, num_unfertilized)
            self.setItem(i, 0, QTableWidgetItem(img))
            self.setItem(i, 1, QTableWidgetItem(
                str(num_unfertilized)))
            self.setItem(i, 2, QTableWidgetItem(
                str(num_fertilized)))
        self.setHorizontalHeaderLabels(["Image", "Unfertilized", "Fertilized"])


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
