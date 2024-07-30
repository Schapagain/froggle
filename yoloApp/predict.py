import os
import typing
import numpy as np
from typing import Callable
from ultralytics import YOLO
model_sgd = YOLO("./model/best.pt")
model_adam = YOLO("./model/best.pt")
model_adam_w = YOLO("./model/best.pt")


# Log initial message
DEFAULT_MODEL = "sgd"


def getModelFromLabel(model: str = ""):
    '''
    Returns the corresponding model from its name. Defaults to SGD
    '''
    if not model:
        model = DEFAULT_MODEL
    model_map = dict(
        sgd=model_sgd,
        adam=model_adam,
        adam_w=model_adam_w)
    return model_map.get(model, model_sgd)


def non_max_suppression(
        boxes, scores, iou_threshold=0.5,
        class_agnostic=False, class_labels=[]
):
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
            sorted_indices = sorted_indices[1:][ious <=
                                                iou_threshold | ~class_filter]

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
    x_center, y_center, width, height = (pred[:, 1], pred[:, 2],
                                         pred[:, 3], pred[:, 4])
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
    x1, y1, x2, y2 = (selected_boxes[:, 0], selected_boxes[:, 1],
                      selected_boxes[:, 2], selected_boxes[:, 3])
    x_center = (x1 + x2) / 2
    y_center = (y1 + y2) / 2
    width = x2 - x1
    height = y2 - y1
    selected_pred[:, 1:5] = np.stack(
        [x_center, y_center, width, height], axis=1)

    return selected_pred


def runDetection(prediction_dir,
                 model: str = DEFAULT_MODEL,
                 progress_callback: typing.Optional[
                     Callable[
                         [int], None]] = None):

    os.makedirs(prediction_dir, exist_ok=True)
    processed_img_count = 0
    predictions = []
    prediction_model = getModelFromLabel(model)
    for image in os.listdir(prediction_dir):
        if progress_callback is not None:
            progress_callback(processed_img_count)
        image_path = os.path.join(prediction_dir, image)
        name = os.path.splitext(image)[0]
        if os.path.isdir(image_path):
            continue
        prediction_model.predict(
            source=image_path, classes=[0, 1],
            project=prediction_dir, agnostic_nms=True,
            conf=0.25, max_det=500, save=False,
            save_txt=True, save_conf=True,
            show_labels=False, show_conf=False,
            show_boxes=True, line_width=3, exist_ok=True)

        # Apply NMS
        # Load the predicted labels from YOLO
        pred_path = os.path.join(
            prediction_dir, 'predict', 'labels', f'{name}.txt')
        if not os.path.exists(pred_path):
            continue  # Skip if the label file doesn't exist

        pred = np.loadtxt(pred_path)
        if pred.ndim == 1:
            # Ensure pred is 2D for a single prediction case
            pred = np.expand_dims(pred, axis=0)

        if len(pred) == 0:
            continue  # Skip if there are no predictions

        class_labels = pred[:, 0]
        boxes = convert_to_corners(pred)  # Convert to corner format for NMS
        scores = pred[:, 5]  # Confidence scores are at index 5
        selected_boxes, selected_indices = non_max_suppression(
            boxes, scores,
            iou_threshold=0.5, class_agnostic=True,
            class_labels=class_labels)
        # Convert back to YOLO format
        pred = convert_to_yolo_format(pred, selected_boxes, selected_indices)
        num_fertilized = sum(
            1 if pred_line[0] == 0 else 0 for pred_line in pred)
        num_unfertilized = len(pred) - num_fertilized
        predictions.append(f"{name} {num_unfertilized} {num_fertilized}")
        # Save the filtered predictions
        np.savetxt(pred_path, pred, fmt='%f')
        processed_img_count += 1
    with open(
            os.path.join(prediction_dir, 'predict', 'prediction_counts.txt'),
            'w+') as f:
        f.write('\n'.join(predictions))
    return predictions
