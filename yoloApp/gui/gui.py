

import typing
import os

from PyQt6.QtCore import (QSize, Qt,  pyqtSlot)
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,)
from PyQt6.QtGui import QIcon, QMovie, QPixmap, QFont, QFontDatabase

from gui.UIComponents import CustomDialog, TableView, ProgressBar
import qtawesome as qta

UPLOAD_BUTTON_DESC = "To get started, upload a zip file"
UPLOAD_BUTTON_LABEL = "Upload Zip File"
UPLOAD_BUTTON_TOOLTIP = "Select zip file with images"
RUN_MODEL_BUTTON_LABEL = "Run YOLO Predictions"
MODEL_SELECTION_TEXT = "Selected model:"
EXTRACT_PROGRESS_TEXT = "Extracting images..."
MODEL_PROGRESS_TEXT = "Running YOLO model on images..."
ANNOTATION_PROGRESS_TEXT = "Annotating images..."
SLIDER_NEXT_LABEL = "Next >>>"
SLIDER_PREV_LABEL = "<<< Prev"
CSV_DOWNLOAD_BUTTON_LABEL = "Download as CSV"
SELECT_DIRECTORY_TEXT = "Select directory"


class AppGUI(QWidget):
    ANNOTATED_IMG_SIZE = 500
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
            width = screen.availableSize().width()
            height = screen.availableSize().height()
            self.setFixedSize(min(1200,int(width*0.8)), min(800,int(height*0.8)))
        else:
            self.setFixedSize(1200, 800)
        self.setSizePolicy(QSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self.setWindowIcon(
            QIcon(os.path.join(os.path.realpath(__file__), "static/logo.png")))

        self.left_panel = None
        self.right_panel = None
        self.intro_text = None
        self.run_model_button = None
        self.select_model_dropdown = None

        self.predictionResultsLoaded = False
        self.annotated_img_container = None
        self.annotated_label_container = None
        self.next_image_button = None
        self.prev_image_button = None
        self.annotated_img_ct = 0
        self.extraction_progress = None
        self.pred_table = None
        self.detection_progress = None
        self.annotation_progress = None

        self._initUI()

    def _initUI(self):
        self._initFonts()
        self.setWindowTitle(self.title)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # layout.setSpacing(30)
        self.setLayout(layout)
        split_panel = QHBoxLayout()
        layout.addLayout(split_panel, stretch=1)
        left_panel = self._initLeftPanel()
        split_panel.addWidget(left_panel, stretch=1)
        right_panel = self._initRightPanel()
        split_panel.addWidget(right_panel, stretch=2)

        self.container = layout

        # self._initData()
        static_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), 'static')
        stylesheet = '''
            QComboBox {{
                border: none;
                outline: none;
                background-color:#fff;
                min-width: 80px;
                color: #1e1e1e;
                max-width: 80px;
                padding: 5px;
            }}
            QComboBox::drop-down {{
                outline: none;
                border: none;
                color: #1e1e1e;
            }}
            QComboBox QAbstractItemView {{
                color: #1e1e1e;
                background-color: #fff;
            }}
            QComboBox QAbstractItemView:hover {{
                color: #fff;
                background-color: #1e1e1e;
            }}
            QComboBox::down-arrow {{
                image: url({0});
                width: 20px;
                height: 15px;
            }}
            QPushButton {{
                border: none;
                outline: none;
                background-color:#fff;
                min-width: 200px;
                color: #1e1e1e;
                max-width: 200px;
                padding: 15px 20px;
            }}
            '''.format(os.path.join(static_path, 'down_arrow.png'))
        self.setStyleSheet(
            stylesheet
        )
        self.show()

    def _initLeftPanel(self):
        '''
        Initialize the left panel on the main UI
        '''
        left_panel = QFrame()
        left_panel_layout = QVBoxLayout()
        left_panel_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_panel.setLayout(left_panel_layout)

        upload_label = QLabel(text=UPLOAD_BUTTON_DESC)
        upload_button = QPushButton(UPLOAD_BUTTON_LABEL)
        upload_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        upload_button.setToolTip(UPLOAD_BUTTON_TOOLTIP)
        upload_button.clicked.connect(self.onUploadZipFile)

        model_selection_frame = QFrame()
        model_selection_layout = QHBoxLayout()
        model_selection_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        model_selection_frame.setLayout(model_selection_layout)

        model_selection_label = QLabel(MODEL_SELECTION_TEXT)
        select_model_dropdown = QComboBox()
        select_model_dropdown.addItems(self.controller.getAvailableModels())
        select_model_dropdown.currentIndexChanged.connect(
            self._onModelSelectionChange)
        run_model_button = QPushButton(RUN_MODEL_BUTTON_LABEL)
        run_model_button.clicked.connect(self.controller.runDetectionModel)
        self.run_model_button = run_model_button

        model_selection_layout.addWidget(
            model_selection_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        model_selection_layout.addWidget(select_model_dropdown)

        left_panel_layout.addWidget(upload_label)
        left_panel_layout.addWidget(
            upload_button, alignment=Qt.AlignmentFlag.AlignCenter)
        left_panel_layout.addWidget(
            model_selection_frame)
        left_panel_layout.addWidget(
            run_model_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.run_model_button = run_model_button
        self.select_model_dropdown = select_model_dropdown
        self.upload_button = upload_button
        self.left_panel = left_panel_layout
        self.toggleRunModelButton(False)
        return left_panel

    def _initRightPanel(self):
        '''
        Initialize the right panel on the main UI
        '''
        right_panel = QFrame()
        right_panel_layout = QVBoxLayout()
        right_panel_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_panel.setLayout(right_panel_layout)

        intro_text = QLabel(text=AppGUI.INTRO_TEXT)
        intro_text.setFont(QFont(self.font_families["body_serif"], 18))
        intro_text.setStyleSheet("padding-left:30px;")
        intro_text.setWordWrap(True)
        right_panel_layout.addWidget(intro_text)

        loading_widget = QLabel()
        loading_animation = QMovie(
            os.path.join(
                os.path.dirname(
                    os.path.realpath(__file__)),
                "static/loading.gif"))
        loading_widget.setMovie(loading_animation)
        loading_animation.setScaledSize(QSize(64, 64))
        loading_animation.setSpeed(100)
        self.loading_animation = loading_animation
        self.loading_widget = loading_widget
        right_panel_layout.addWidget(loading_widget)
        self.intro_text = intro_text
        self.right_panel = right_panel_layout
        return right_panel

    def _initData(self):
        '''
        Initialize the UI with existing data from previous load
        '''
        if self.intro_text:
            self.intro_text.setVisible(False)
        self.addPredictionsTable()
        self.initPredictionImages(self.controller.getWorkingDirectory())

    def _initFonts(self):
        '''
        Load fonts used by the application UI
        '''
        fonts_dir = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "static/fonts")
        for font_file_name in os.listdir(fonts_dir):
            QFontDatabase.addApplicationFont(
                os.path.join(fonts_dir, font_file_name)
            )
        self.font_families = dict(
            body_sans='Raleway',
            body_serif='Zilla Slab'
        )

    def _addWidget(self, widget):
        '''
        Helper method to add widget to the main container flow
        '''
        layout = self.layout()
        if layout:
            layout.addWidget(widget)

    def setModelLoading(self, loading=True):
        '''
        Hides the intro text on the right panel, and shows/hides
        the loading animation
        '''
        if self.intro_text:
            self.intro_text.setVisible(False)
        if loading:
            self.loading_widget.setVisible(True)
            self.loading_animation.start()
        else:
            self.loading_widget.setVisible(False)
            self.loading_animation.stop()
        if self.annotated_img_container:
            self.annotated_img_container.setVisible(not loading)
        if self.annotated_label_container:
            self.annotated_label_container.setVisible(not loading)
        if self.next_image_button:
            self.next_image_button.setVisible(not loading)
        if self.prev_image_button:
            self.prev_image_button.setVisible(not loading)

    def addPredictionsTable(self, data: typing.Optional[list[str]] = None):
        '''
        Display prediction counts on the UI.
        If "data" parameter is not provided, counts is expected at:
            "working directory" > test_images > predict > prediction_counts.txt
        '''
        prediction_counts_dir = self.controller.getWorkingDirectory()
        if data is None:
            counts_file_path = os.path.join(
                prediction_counts_dir, 'test_images',
                'predict', 'prediction_counts.txt')
            if not os.path.isfile(counts_file_path):
                return
            with open(counts_file_path, 'r') as f:
                data = f.readlines()
        table_data = dict(
            rows=list(map(lambda line: line.strip().split(' '), data)),
            headers=["Image", "Unfertilized", "Fertilized"])
        if self.pred_table is not None:
            self.pred_table.updateData(table_data)
        else:
            self.pred_table = TableView(table_data, len(data), 3)
            self.download_csv_button = QPushButton(
                text=CSV_DOWNLOAD_BUTTON_LABEL)
            self.download_csv_button.clicked.connect(self._saveTableAsCSV)
            if self.left_panel:
                self.left_panel.addWidget(
                    self.download_csv_button,
                    alignment=Qt.AlignmentFlag.AlignCenter)
                self.left_panel.addWidget(
                    self.pred_table,
                    alignment=Qt.AlignmentFlag.AlignLeft,
                )
            self.pred_table.cellClicked.connect(self._onPredictionsTableClick)

    @pyqtSlot(int)
    def _onModelSelectionChange(self, idx):
        '''
        '''
        self.controller.setModel(idx)

    @ pyqtSlot(int, int)
    def _onPredictionsTableClick(self, row, _):
        '''
        Highlight the entire table row when any cell is clicked.

        Also display the corresponding annotated image on the image slider
        '''
        if self.pred_table:
            self.pred_table.selectRow(row)
            self.selectPredictionImage(row)

    @ pyqtSlot()
    def _saveTableAsCSV(self):
        saveDirectory = self.openDirectorySelectDialog()
        if self.pred_table:
            self.pred_table.toCSV(saveDirectory)

    def initPredictionImages(
            self,
            parent_directory: typing.Union[str, os.PathLike]
    ):
        '''
        Initialize the slider on the right panel to show
        annotated images. This includes the image container,
        the label for the image,
        and the prev and next buttons to switch between images
        '''
        if self.annotated_img_container is None:
            annotated_directory = os.path.join(
                parent_directory, 'test_images', 'predict', 'annotated_images')
            if not os.path.isdir(annotated_directory):
                return

            self.annotated_dir = annotated_directory
            self.annotated_img_container = QLabel()
            self.annotated_label_container = QLabel()
            self.annotated_img_idx = -1
            self.annotated_img_ct = 1
            self._nextPredictionImage()
            nav_button_group = QHBoxLayout()

            prev_image_button = QPushButton(SLIDER_PREV_LABEL)
            next_image_button = QPushButton(SLIDER_NEXT_LABEL)
            next_image_button.clicked.connect(self._nextPredictionImage)
            prev_image_button.clicked.connect(self._prevPredictionImage)
            nav_button_group.addWidget(prev_image_button)
            nav_button_group.addWidget(next_image_button)
            if self.intro_text and self.right_panel:
                self.intro_text.setVisible(False)
                self.right_panel.addWidget(self.annotated_label_container)
                self.right_panel.addWidget(self.annotated_img_container)
                self.right_panel.addLayout(nav_button_group)
            self.prev_image_button = prev_image_button
            self.next_image_button = next_image_button

    def updateAnnotatedImageCount(self, count: int):
        '''
        Add prediction images to the UI generated at:
            parent_directory > test_images > predict > annotated_images
        '''
        self.annotated_img_ct = count

    @ pyqtSlot()
    def _nextPredictionImage(self):
        '''
        Load the next image in the annotated_dir directory onto the slider
        '''
        idx = (self.annotated_img_idx + 1) % self.annotated_img_ct
        self.selectPredictionImage(idx)

    @ pyqtSlot()
    def _prevPredictionImage(self):
        '''
        Load the previous image in the annotated_dir directory onto the slider
        '''
        idx = (self.annotated_img_idx -
               1) if self.annotated_img_idx > 0 else self.annotated_img_ct - 1
        self.selectPredictionImage(idx)

    def selectPredictionImage(self, idx):
        '''
        Set the prediction image shown on the carousel to the one
        at position `idx` in the annotated images directory

        Additionally highlights the corresponding row on the prediction table
        if the table has been initialized
        '''
        self.annotated_img_idx = idx
        if idx >= self.annotated_img_ct:
            return
        for image_path in os.listdir(self.annotated_dir):
            _, image_extension = os.path.splitext(image_path)
            if (os.path.isdir(image_path) or
                    image_extension not
                    in self.controller.getValidExtensions()):
                continue
            if idx > 0:
                idx -= 1
                continue
            if self.annotated_label_container:
                self.annotated_label_container.setText(
                    f"#{self.annotated_img_idx+1}: {image_path}")
            if self.annotated_img_container:
                self.annotated_img_container.setPixmap(QPixmap(os.path.join(
                    self.annotated_dir, image_path)).scaledToWidth(
                        AppGUI.ANNOTATED_IMG_SIZE))
            break
        if self.pred_table:
            self.pred_table.highlightRow(self.annotated_img_idx)

    def toggleUploadButton(self, enable=None):
        '''
        Enable/Disable the "Upload images" button on the UI
        '''
        if enable is None:
            enable = not self.upload_button
        if self.upload_button:
            self.upload_button.setEnabled(enable)
            if enable:
                self.upload_button.setStyleSheet("background-color:#fff")
            else:
                self.upload_button.setStyleSheet("background-color:gray")

    def toggleRunModelButton(self, enable=None):
        '''
        Enable/Disable the "Run Model" button on the UI
        Also enables/disables the model selection dropdown
        '''
        if enable is None:
            enable = not self.run_model_button or not self.select_model_dropdown
        if self.run_model_button and self.select_model_dropdown:
            self.run_model_button.setEnabled(enable)
            self.select_model_dropdown.setEnabled(enable)
            if enable:
                self.run_model_button.setStyleSheet("background-color:#fff")
                self.select_model_dropdown.setStyleSheet(
                    "background-color:#fff")
            else:
                self.run_model_button.setStyleSheet("background-color:gray")
                self.select_model_dropdown.setStyleSheet(
                    "background-color:gray")

    def openFileNameDialog(self):
        '''
        Open a dialog to prompt users to upload a zip file containing images
        '''
        dialog = QFileDialog()
        options = QFileDialog.options(dialog)
        fileName, _ = QFileDialog.getOpenFileName(
            self, "QFileDialog.getOpenFileName()",
            "", "Zip File (*.zip)", options=options)
        if fileName:
            self.controller.extractZipFile(fileName)

    def openDirectorySelectDialog(self):
        '''
        Open a dialog to prompt users to select an existing directory
        '''
        return QFileDialog.getExistingDirectory(
            self, SELECT_DIRECTORY_TEXT)

    def onUploadZipFile(self):
        self.openFileNameDialog()

    def showAnnotationProgress(self, progress):
        '''
        Initialize or update the image annotation progress
        '''
        if not self.annotation_progress:
            self.annotation_progress = ProgressBar(
                ANNOTATION_PROGRESS_TEXT)
            self.annotation_progress.setFont(
                QFont(self.font_families["body_serif"], 16))
            if self.left_panel:
                self.left_panel.addWidget(self.annotation_progress)
        self.annotation_progress.setProgress(
            progress,
            progress_count=self.annotated_img_ct,
            total_count=self.controller.getImageCount())

    def showDetectionProgress(self, progress):
        '''
        Initialize or update the egg detection progress.
        Additionally, reset the annotation progress if detection has just
        been started
        '''
        if not self.detection_progress:
            self.detection_progress = ProgressBar(
                MODEL_PROGRESS_TEXT)
            self.detection_progress.setFont(
                QFont(self.font_families["body_serif"], 16))
            if self.left_panel:
                self.left_panel.addWidget(self.detection_progress)
        num_images_done = int(
            progress * self.controller.getImageCount() * 0.01)
        self.detection_progress.setProgress(
            progress,
            progress_count=num_images_done,
            total_count=self.controller.getImageCount())
        if self.annotation_progress and progress == 0:
            self.updateAnnotatedImageCount(0)
            self.showAnnotationProgress(0)

    def showImageExtractionProgress(self, progress):
        '''
        Initialize or update the zip file extraction progress
        '''
        if not self.extraction_progress:
            self.extraction_progress = ProgressBar(EXTRACT_PROGRESS_TEXT)
            if self.left_panel:
                self.left_panel.addWidget(self.extraction_progress)
        self.extraction_progress.setProgress(progress)

    def showImagesNotLoadedError(self):
        '''
        Show error dialog if attempted to run detection or
        annotation without first loading images
        '''
        errorDialog = CustomDialog()
        print(errorDialog.exec())
