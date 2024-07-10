import os
import subprocess
import re
import pandas as pd
from pathlib import Path
from shiny import App, ui, reactive, render, Inputs, Outputs, Session
import shutil
import zipfile
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Define UI
app_ui = ui.page_fluid(
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.input_file("image_zip", "Choose a ZIP file with images", multiple=False, accept=['.zip']),
            ui.input_action_button("process_button", "Run YOLO and Bounding Box")
        ),
        ui.panel_main(
            ui.h2("YOLO and Bounding Box Tool"),
            ui.markdown(
                """
                **The tool allows users to count the number of fertilized vs unfertilized eggs.**
                
                - The images will be saved in the `ProcessedImages/TestImages2/predict/PredImages` folder.
                - To generate predictions, upload a ZIP file containing images.
                - Upon clicking the 'Run YOLO and Bounding Box' button, the images will be processed using YOLO for object detection and a bounding box script.
                - The processed images will be saved in a specific directory.
                """
            ),
            ui.output_text_verbatim("process_status"),
            ui.output_table("results_table")
        )
    ),
    # Footer with logo and copyright
    ui.div(
        ui.markdown(
            """
            ########################################################
            <br>@Copyright AGGRC 2024<br>
            Authors:
            1. Gopal Srivastava
            2. Monika Pandey
            3. Kiran Bist
            4. Dr Yue Liu *
            4. Prof Peter Wolenski *
            - *: Corresponding Authors
            """
        ),
        style="text-align: left; padding: 20px; position: fixed;bottom: 0; width: 100%; background-color: white;"
    )
)

# Define server logic
def server(input: Inputs, output: Outputs, session: Session):
    status_message = reactive.Value("")
    results = reactive.Value(pd.DataFrame(columns=["Image", "Fertilized (f)", "Under-fertilized (uf)"]))

    @reactive.Effect
    @reactive.event(input.process_button)
    async def process_images():
        uploaded_file = input.image_zip()
        if uploaded_file:
            zip_path = uploaded_file[0]['datapath']
            status_message.set("Processing images...")
            await reactive.flush()  # Force UI update

            # Define the destination folder
            dest_folder = "ProcessedImages/TestImages2"
            if os.path.exists(dest_folder):
                shutil.rmtree(dest_folder)
            os.makedirs(dest_folder, exist_ok=True)

            # Extract the zip file to the specified folder without creating a new folder
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    filename = os.path.basename(member)
                    # Skip directories and unwanted files
                    if not filename or filename.startswith('._') or member.startswith('__MACOSX/'):
                        continue
                    source = zip_ref.open(member)
                    target = open(os.path.join(dest_folder, filename), "wb")
                    with source, target:
                        shutil.copyfileobj(source, target)

            try:
                # Run YOLOtesting.py and capture output
                yolo_script = "YOLOtesting.py"
                logging.debug(f"Running YOLO script: {yolo_script}")
                result = subprocess.run(["python3.11", yolo_script], capture_output=True, text=True, check=True)
                yolo_output = result.stdout
                logging.debug(f"YOLO output: {yolo_output}")
            except subprocess.CalledProcessError as e:
                logging.error(f"Error running YOLO script: {e}")
                status_message.set(f"Error running YOLO script: {e}")
                return

            # Parse YOLO output
            pattern = re.compile(r"(\d+)/(\d+)\s+(.+):.+\s(\d+)\sfs,\s(\d+)\sufs")
            matches = pattern.findall(yolo_output)
            if matches:
                data = []
                for match in matches:
                    image_info = {
                        "Image": match[2].split("/")[-1],
                        "Fertilized (F)": int(match[3]),
                        "Unfertilized (UF)": int(match[4])
                    }
                    data.append(image_info)
                df = pd.DataFrame(data)
                results.set(df)

            try:
                # Run boundingbox.py
                bbox_script = "DisplayPredboundingbox.sh"
                logging.debug(f"Running bounding box script: {bbox_script}")
                subprocess.run(["sh", bbox_script], check=True)
            except subprocess.CalledProcessError as e:
                logging.error(f"Error running bounding box script: {e}")
                status_message.set(f"Error running bounding box script: {e}")
                return

            status_message.set(f"Processing completed.\nPlease go to ProcessedImages/TestImages2/predict/PredImages")
        else:
            status_message.set("No file selected.")

    @output
    @render.text
    def process_status():
        return status_message.get()

    @output
    @render.table
    def results_table():
        return results.get()

app = App(app_ui, server)
