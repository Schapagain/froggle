import zipfile
import sys
import os
import shutil
from gui.gui import AppGUI
from predict import runDetection
from boundingbox import addPredictionAnnotations

from PyQt6.QtCore import (QObject, QRunnable,
                          QThreadPool,
                          pyqtSignal, pyqtSlot)
from PyQt6.QtWidgets import (
    QApplication,
)


class App():
    def __init__(self):
        self.working_dir = os.path.join(os.path.dirname(__file__),".YOLOEggDetection")
        self.valid_extensions = [".jpg", ".jpeg", ".png"]
        self.images_dir = os.path.join(self.working_dir, 'test_images')
        self.images_loaded = False
        self.images_loaded_count = 0
        self.available_models = ["SGD", "Adam-W", "Adam"]
        self.selected_model_idx = 0
        self.threadpool = QThreadPool()
        print("Multithreading supported. Max available threads = {}".format(
            self.threadpool.maxThreadCount()))
        self.gui = AppGUI(self)

    def getAvailableModels(self):
        '''
        Returns all the models available for running predictions
        '''
        return self.available_models

    def setModel(self, idx):
        '''
        Set the model at index idx from all the available model as
        the selected model for predictions
        '''
        if idx > 0 and idx < len(self.getAvailableModels()):
            self.selected_model_idx = idx
        return self.selected_model_idx

    def getImageCount(self):
        '''
        Returns the number of images provided by the user
        '''
        return self.images_loaded_count

    def getWorkingDirectory(self):
        '''
        Returns the working directory where all files (images,prediction logs)
        should be stored
        '''
        return self.working_dir

    def getValidExtensions(self):
        '''
        Returns all image extensions supported by the application
        '''
        return self.valid_extensions

    def extractZipFile(self, zip_path):
        '''
        Extract the zip at the given path, and store the contents
        in the "working directory"
        '''
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            totalFiles = len(zip_ref.namelist())
            if os.path.exists(self.working_dir):
                shutil.rmtree(self.working_dir)
            os.makedirs(self.images_dir, exist_ok=True)
            validImageCount = 0
            for member in zip_ref.namelist():
                self.gui.showImageExtractionProgress(
                    validImageCount // totalFiles)
                filename = os.path.basename(member)
                _, file_extension = os.path.splitext(filename)
                # Skip directories and unwanted files
                if (not filename or filename.startswith('._')
                        or member.startswith('__MACOSX/')
                        or file_extension not in self.valid_extensions):
                    continue

                source = zip_ref.open(member)
                target = open(os.path.join(self.images_dir, filename), "wb")
                with source, target:
                    shutil.copyfileobj(source, target)
                    validImageCount += 1
            self.gui.showImageExtractionProgress(100)
            self.images_loaded = validImageCount > 0
            self.images_loaded_count = validImageCount
            self.gui.toggleRunModelButton(enable=validImageCount > 0)

    def runDetectionModel(self):
        '''
        Run object detection model if images have been loaded properly,
        and add the results to the UI
        '''
        if not self.images_loaded:
            self.gui.showImagesNotLoadedError()
        else:
            self.gui.setModelLoading(True)
            self.gui.toggleRunModelButton(enable=False)
            self.gui.toggleUploadButton(enable=False)
            detectionWorker = Worker(
                runDetection,
                self.images_dir,
                model=self.available_models[self.selected_model_idx])
            detectionWorker.signals.result.connect(self.onDetectionDone)
            detectionWorker.signals.err.connect(self.onWorkerError)
            detectionWorker.signals.progress.connect(self.onDetectionProgress)
            self.threadpool.start(detectionWorker)

    def annotateImagesWithPredictions(self):
        '''
        Annotate uploaded images with predicted classifications
        '''
        if not self.images_loaded:
            self.gui.showImagesNotLoadedError()
        else:
            annotationWorker = Worker(
                addPredictionAnnotations, self.images_dir)
            self.gui.toggleRunModelButton(enable=False)
            self.gui.toggleUploadButton(enable=False)
            annotationWorker.signals.result.connect(self.onAnnotationDone)
            annotationWorker.signals.err.connect(self.onWorkerError)
            annotationWorker.signals.progress.connect(
                self.onAnnotationProgress)
            self.gui.showAnnotationProgress(0)
            self.threadpool.start(annotationWorker)

    def onDetectionProgress(self, numImageProcessed):
        '''
        Handler to receive detection progress signals
        '''
        progress = int(numImageProcessed*100/self.images_loaded_count)
        self.gui.showDetectionProgress(progress)

    def onAnnotationProgress(self, numImageProcessed):
        '''
        Handler to receive annotation progress signals
        '''
        if numImageProcessed == 1:
            self.gui.initPredictionImages(self.getWorkingDirectory())
            self.gui.setModelLoading(False)
        progress = int(numImageProcessed*100/self.images_loaded_count)
        self.gui.updateAnnotatedImageCount(numImageProcessed)
        self.gui.showAnnotationProgress(progress)

    def onAnnotationDone(self):
        '''
        Handler to run when all images are annotated
        with model predictions
        '''
        self.gui.showAnnotationProgress(100)
        self.gui.toggleRunModelButton(enable=True)
        self.gui.toggleUploadButton(enable=True)

    def onDetectionDone(self, predictions):
        '''
        Handler to run when detection model is done
        and process results appropriately
        '''
        self.gui.addPredictionsTable(data=predictions)
        self.annotateImagesWithPredictions()
        self.gui.showDetectionProgress(100)

    def onWorkerError(self, err):
        '''
        Handler to run if detection model errors out
        '''
        print('ERROR: something went wrong while running detection model', err)


class WorkerSignal(QObject):

    progress = pyqtSignal(int)
    result = pyqtSignal(object)
    err = pyqtSignal(object)


class Worker(QRunnable):
    '''
    Worker thread to run computationally heavy tasks

    :param fn: The function callback to run on this worker thread.
                Supplied args and kwargs will be passed to the fn.
    :param args: Arguments to pass to the callback fn
    :param kwargs: Keywords to pass to the callback fn

    '''

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignal()
        self.kwargs["progress_callback"] = self.onProgressCallback

    def onProgressCallback(self, *args, **kwargs):
        self.signals.progress.emit(*args, **kwargs)

    @ pyqtSlot()
    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            self.signals.err.emit(e)
        else:
            self.signals.result.emit(res)


if __name__ == '__main__':
    q_app = QApplication(sys.argv)
    app = App()

    sys.exit(q_app.exec())
