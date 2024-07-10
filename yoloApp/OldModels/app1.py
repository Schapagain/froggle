import os
import numpy as np
import cv2
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image
from ultralytics import YOLO
from shiny import App, ui, render, reactive

# Load a pretrained YOLOv8n model
model = YOLO("./model/best.pt")

def non_max_suppression(boxes, scores, iou_threshold=0.5, class_agnostic=False, class_labels=None):
    sorted_indices = np.argsort(scores)[::-1]
    sorted_boxes = boxes[sorted_indices]
    selected_boxes = []
    selected_indices = []
    
    while len(sorted_boxes) > 0:
        current_box = sorted_boxes[0]
        selected_boxes.append(current_box)
        selected_indices.append(sorted_indices[0])
        rest_boxes = sorted_boxes[1:]
        ious = compute_iou(current_box, rest_boxes)
        
        if class_agnostic:
            sorted_boxes = rest_boxes[ious <= iou_threshold]
            sorted_indices = sorted_indices[1:][ious <= iou_threshold]
        else:
            current_class = class_labels[sorted_indices[0]]
            class_filter = class_labels[sorted_indices[1:]] == current_class
            sorted_boxes = rest_boxes[ious <= iou_threshold | ~class_filter]
            sorted_indices = sorted_indices[1:][ious <= iou_threshold | ~class_filter]
    
    return np.array(selected_boxes), selected_indices

def compute_iou(box, boxes):
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    
    inter_area = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    box_area = (box[2] - box[0]) * (box[3] - box[1])
    boxes_area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    
    union_area = box_area + boxes_area - inter_area
    iou = inter_area / union_area
    
    return iou

def convert_to_corners(pred):
    # Convert from [x_center, y_center, width, height] to [x1, y1, x2, y2]
    x_center, y_center, width, height = pred[:, 1], pred[:, 2], pred[:, 3], pred[:, 4]
    x1 = x_center - width / 2
    y1 = y_center - height / 2
    x2 = x_center + width / 2
    y2 = y_center + height / 2
    return np.stack([x1, y1, x2, y2], axis=1)

def convert_to_yolo_format(pred, selected_boxes, selected_indices):
    # Create a new array for the selected predictions
    selected_pred = np.zeros((len(selected_boxes), pred.shape[1]))
    selected_pred[:, 0] = pred[selected_indices, 0]  # class
    selected_pred[:, 5] = pred[selected_indices, 5]  # confidence

    # Convert from [x1, y1, x2, y2] back to [x_center, y_center, width, height]
    x1, y1, x2, y2 = selected_boxes[:, 0], selected_boxes[:, 1], selected_boxes[:, 2], selected_boxes[:, 3]
    x_center = (x1 + x2) / 2
    y_center = (y1 + y2) / 2
    width = x2 - x1
    height = y2 - y1
    selected_pred[:, 1:5] = np.stack([x_center, y_center, width, height], axis=1)

    return selected_pred

def draw_bounding_boxes(image_path, pred_path, save_path):
    # Load the image
    image = cv2.imread(image_path)
    image_height, image_width, _ = image.shape

    # Load and parse the text file
    with open(pred_path, 'r') as file:
        lines = file.readlines()

    # Draw bounding boxes
    for line in lines:
        label, x_center, y_center, width, height = map(float, line.strip().split())
        # Convert normalized coordinates to actual coordinates
        x_center *= image_width
        y_center *= image_height
        box_width = width * image_width
        box_height = height * image_height
        # Calculate the top-left corner of the bounding box
        top_left_x = int(x_center - box_width / 2)
        top_left_y = int(y_center - box_height / 2)
        bottom_right_x = int(x_center + box_width / 2)
        bottom_right_y = int(y_center + box_height / 2)
        # Draw the bounding box
        color = (0, 255, 0) if label == 0 else (0, 0, 255)  # Green for label 0, Red for label 1
        cv2.rectangle(image, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), color, 2)

    # Save the image with bounding boxes
    cv2.imwrite(save_path, image)

    # Convert BGR to RGB for displaying with matplotlib
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Convert image to PNG bytes
    pil_image = Image.fromarray(image_rgb)
    buf = BytesIO()
    pil_image.save(buf, format="png")
    img_str = buf.getvalue()

    return img_str

# Directory to save all predictions
prediction_dir = "TestImages2Prediction"
os.makedirs(prediction_dir, exist_ok=True)

app_ui = ui.page_fluid(
    ui.input_file("files", "Select Images", multiple=True),
    ui.input_numeric("iou_threshold", "IOU Threshold", value=0.5),
    ui.input_action_button("predict", "Predict"),
    ui.output_text_verbatim("output"),
    ui.output_image("bounding_box_image"),
    ui.download_button("download_image", "Download Image with Bounding Boxes")
)

def server(input, output, session):
    saved_image_path = reactive.Value("")

    @output
    @render.text
    def output():
        if input.predict():
            files = input.files()
            iou_threshold = input.iou_threshold()

            results = []

            for file in files:
                file_path = file["datapath"]
                name = os.path.splitext(file["name"])[0]
                pred_path = os.path.join(prediction_dir, f"{name}.txt")

                # Perform YOLO prediction and save the results
                validation_results = model.predict(source=file_path, classes=[0, 1], project=prediction_dir, agnostic_nms=True, conf=0.25, max_det=500, save=True, save_txt=True, save_conf=True, show_labels=False, show_conf=False, show_boxes=True, line_width=3, exist_ok=True)

                # The YOLO model will save predictions in the predict/labels directory
                labels_dir = os.path.join(prediction_dir, "predict", "labels")
                label_path = os.path.join(labels_dir, f"{name}.txt")

                if not os.path.exists(label_path):
                    continue  # Skip if the label file doesn't exist
                
                pred = np.loadtxt(label_path)
                if pred.ndim == 1:
                    pred = np.expand_dims(pred, axis=0)  # Ensure pred is 2D for a single prediction case
                
                if len(pred) == 0:
                    continue  # Skip if there are no predictions
                
                class_labels = pred[:, 0]
                boxes = convert_to_corners(pred)  # Convert to corner format for NMS
                scores = pred[:, 5]  # Confidence scores are at index 5
                selected_boxes, selected_indices = non_max_suppression(boxes, scores, iou_threshold=iou_threshold, class_agnostic=True, class_labels=class_labels)
                pred = convert_to_yolo_format(pred, selected_boxes, selected_indices)  # Convert back to YOLO format
                
                # Save the filtered predictions
                np.savetxt(pred_path, pred, fmt='%f')
                results.append(f"Processed {file['name']}")

                # Save and display the image with bounding boxes
                save_path = os.path.join(prediction_dir, f"{name}_with_boxes.png")
                img_str = draw_bounding_boxes(file_path, pred_path, save_path)
                output["bounding_box_image"] = render.image(data=img_str, mime_type="image/png")
                saved_image_path.set(save_path)

            return "\n".join(results)

    @session.download(filename="image_with_boxes.png")
    def download_image():
        return saved_image_path.get()

app = App(app_ui, server)

# Run the app
if __name__ == "__main__":
    app.run()
