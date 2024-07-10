import os
import subprocess
from pathlib import Path
from shiny import App, ui, reactive, render, Inputs, Outputs, Session
import shutil
import zipfile

# Define UI
app_ui = ui.page_fluid(
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.input_file("image_zip", "Choose a ZIP file with images", multiple=False, accept=['.zip']),
            ui.input_action_button("process_button", "Run YOLO and Bounding Box")
        ),
        ui.panel_main(
            ui.output_ui("results_ui")
        )
    )
)

# Define server logic
def server(input: Inputs, output: Outputs, session: Session):
    processed_folder = reactive.Value(None)

    @reactive.Effect
    @reactive.event(input.process_button)
    def process_images():
        uploaded_file = input.image_zip()
        if uploaded_file:
            zip_path = uploaded_file[0]['datapath']

            # Extract the zip file to folder below
            dest_folder = "TestImages2Processed"
            if os.path.exists(dest_folder):
                shutil.rmtree(dest_folder)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(dest_folder)

            # Run YOLOtesting.py
            yolo_script = "YOLOtesting.py"
            subprocess.run(["python3.11", yolo_script], check=True)

            # Run boundingbox.py
            bbox_script = "DisplayPredboundingbox.sh"
            subprocess.run(["sh", bbox_script], check=True)

            processed_folder.set(dest_folder)
        else:
            processed_folder.set(None)

app = App(app_ui, server)
