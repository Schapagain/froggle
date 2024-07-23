import zipfile
import sys
import os
import shutil

from PyQt6.QtCore import Qt, pyqtSlot
from YOLOtesting import runDetection
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel, QPushButton,
    QVBoxLayout,
    QWidget,)
from PyQt6.QtGui import QIcon, QPixmap

from UIComponents import CustomDialog, TableView


class AppGUI(QWidget):
    INTRO_TEXT = """
    <h2>Egg Counting: Fertilized vs Unfertilized</h2>
    <br><br>
    <b>The tool allows users to count the number of
    fertilized vs unfertilized eggs.</b>
    <br><br>
    <ol>
    <li>To generate predictions, upload a ZIP file containing images</li>
    <li>Upon clicking the 'Run YOLO Model' button, the images will be processed
     using YOLO for object detection and a bounding box script.</li>
    <li>The predicted classifications will be shown here,
     along with annotated images</li>
    </ol>
    """

    def __init__(self, appController):
        super().__init__()
        self.controller = appController
        self.title = 'YOLO Egg Detection'
        self.left = 10
        self.top = 10
        screen = self.screen()
        if screen:
            print('screen sizes:', screen.availableSize())
            width = screen.availableSize().width()
            height = screen.availableSize().height()
            self.resize(int(width*0.8), int(height*0.8))
        else:
            self.resize(700, 550)
        self.setWindowIcon(QIcon("LSU-logo.png"))

        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(30)
        self.setLayout(layout)

        split_panel = QHBoxLayout()
        layout.addLayout(split_panel)

        left_panel = QVBoxLayout()
        split_panel.addLayout(left_panel)

        upload_button = QPushButton('Upload Zip File')
        upload_button.setToolTip('Select zip file with images')
        upload_button.clicked.connect(self.onUploadZipFile)

        run_model_button = QPushButton('Run YOLO Model')
        run_model_button.clicked.connect(self.controller.runDetectionModel)

        left_panel.addWidget(upload_button)
        left_panel.addWidget(run_model_button)

        right_panel = QVBoxLayout()
        split_panel.addLayout(right_panel)

        intro_text = QLabel()
        intro_text.setText(AppGUI.INTRO_TEXT)
        intro_text.setStyleSheet("padding-left:30px;")
        intro_text.setWordWrap(True)
        right_panel.addWidget(intro_text)

        self.container = layout
        self.left_panel = left_panel
        self.right_panel = right_panel

        self.show()

    def _addWidget(self, widget):
        layout = self.layout()
        if layout:
            layout.addWidget(widget)

    def addPredictionsTable(self, table: TableView):
        self.left_panel.addWidget(table)

    @pyqtSlot()
    def _nextPredictionImage(self):
        idx = (self.annotated_img_idx + 1) % self.annotated_img_ct
        self.annotated_img_idx = idx
        for image_path in os.listdir(self.annotated_dir):
            if os.path.isdir(image_path):
                continue
            if idx > 0:
                idx -= 1
                continue
            self.annotated_label_container.setText(image_path)
            self.annotated_img_container.setPixmap(QPixmap(os.path.join(
                self.annotated_dir, image_path)).scaled(700, 700))
            break

    @pyqtSlot()
    def _prevPredictionImage(self):
        idx = (self.annotated_img_idx -
               1) if self.annotated_img_idx > 0 else self.annotated_img_ct - 1
        self.annotated_img_idx = idx
        for image_path in os.listdir(self.annotated_dir):
            if os.path.isdir(image_path):
                continue
            if idx > 0:
                idx -= 1
                continue
            self.annotated_label_container.setText(image_path)
            self.annotated_img_container.setPixmap(QPixmap(os.path.join(
                self.annotated_dir, image_path)).scaled(700, 700))
            break

    def addPredictionsImages(self, parent_directory: str):
        if (not os.path.exists(parent_directory) or
                not os.path.isdir(parent_directory)):
            return
        annotated_directory = os.path.join(
            parent_directory, 'annotated_images')
        self.annotated_dir = annotated_directory
        self.annotated_img_container = QLabel()
        self.annotated_label_container = QLabel()
        self.annotated_img_idx = -1
        self.annotated_img_ct = 0
        for image_path in os.listdir(annotated_directory):
            if not os.path.isdir(image_path):
                self.annotated_img_ct += 1
        self._nextPredictionImage()
        nav_button_group = QHBoxLayout()
        self.right_panel.addLayout(nav_button_group)

        prev_image_button = QPushButton("<< Prev")
        next_image_button = QPushButton("Next >>")
        next_image_button.clicked.connect(self._nextPredictionImage)
        prev_image_button.clicked.connect(self._prevPredictionImage)
        nav_button_group.addWidget(prev_image_button)
        nav_button_group.addWidget(next_image_button)

        self.right_panel.addWidget(self.annotated_label_container)
        self.right_panel.addWidget(self.annotated_img_container)

    def openFileNameDialog(self):
        dialog = QFileDialog()
        options = QFileDialog.options(dialog)
        fileName, _ = QFileDialog.getOpenFileName(
            self, "QFileDialog.getOpenFileName()",
            "", "Zip File (*.zip)", options=options)
        if fileName:
            self.controller.extractZipFile(fileName)

    def onUploadZipFile(self):
        self.openFileNameDialog()

    def showImagesNotLoadedError(self):
        errorDialog = CustomDialog()
        print(errorDialog.exec())


class App():
    def __init__(self):
        self.gui = AppGUI(self)
        self.working_dir = ".YOLOEggDetection"
        self.images_dir = os.path.join(self.working_dir, 'test_images')
        self.images_loaded = False
        if os.path.exists(self.working_dir):
            shutil.rmtree(self.working_dir)
        os.makedirs(self.images_dir, exist_ok=True)

    def extractZipFile(self, zip_path):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                filename = os.path.basename(member)
                # Skip directories and unwanted files
                if (not filename
                    or filename.startswith('._')
                        or member.startswith('__MACOSX/')):
                    continue
                source = zip_ref.open(member)
                target = open(os.path.join(self.images_dir, filename), "wb")
                print('saving files in ', os.path.join(
                    self.working_dir, filename))
                with source, target:
                    shutil.copyfileobj(source, target)
            self.images_loaded = True

    def runDetectionModel(self):
        if not self.images_loaded:
            self.gui.showImagesNotLoadedError()
        else:
            print('Running detection model')
            predictions = runDetection(self.images_dir)
            pred_table = TableView(predictions, len(predictions), 3)
            self.gui.addPredictionsTable(pred_table)
            self.gui.addPredictionsImages(self.working_dir)
            print('Done running detection', predictions)


if __name__ == '__main__':
    q_app = QApplication(sys.argv)
    q_app.setStyleSheet(
        """
        QPushButton {
            border: none;
            outline: none;
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0,
                                y2: 1, stop: 0 #f6f7fa, stop: 1 #dadbde);
            min-width: 80px;
            color: #1e1e1e;
            max-width: 250px;
            padding: 15px 20px;
            }
        """
    )
    app = App()

    sys.exit(q_app.exec())
