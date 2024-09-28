import os
from PIL import Image, ImageDraw
import typing
from typing import Callable


def centerToBoundingBox(
    center_coords: tuple[int, int], size: tuple[int, int]
) -> tuple[int, int, int, int]:
    center_x, center_y = center_coords
    width, height = size
    top_left_x = round(center_x - width / 2)
    top_left_y = round(center_y - height / 2)
    bot_right_x = round(center_x + width / 2)
    bot_right_y = round(center_y + height / 2)
    return (top_left_x, top_left_y, bot_right_x, bot_right_y)


def addPredictionAnnotations(pred_image_path,
                             progress_callback: typing.Optional[Callable[[int], None]] = None):
    # Create a prediction folder
    annotated_image_path = os.path.join(
        pred_image_path, 'predict', 'annotated_images')
    os.makedirs(annotated_image_path, exist_ok=True)

    processed_images = 0
    for image_path in os.listdir(pred_image_path):
        if os.path.isdir(os.path.join(pred_image_path, image_path)):
            continue
        # Load the image
        name = os.path.splitext(image_path)[0]
        name = name.split("/")[-1]
        image = Image.open(os.path.join(
            pred_image_path, image_path)).convert("RGBA")
        image_draw = ImageDraw.Draw(image, mode="RGBA")
        image_width, image_height = image.size

        # Load and parse the text file
        coordinates_path = os.path.join(
            pred_image_path, 'predict', 'labels', f'{name}.txt')
        with open(coordinates_path, 'r') as file:
            lines = file.readlines()

        # Draw bounding boxes
        for line in lines:
            label, x_center, y_center, width, height, confidence = map(
                float, line.strip().split())
            # Convert normalized coordinates to actual coordinates
            x_center = int(x_center * image_width)
            y_center = int(y_center * image_height)
            box_width = int(width * image_width)
            box_height = int(height * image_height)
            annotation_bounding_box = centerToBoundingBox(
                (x_center, y_center), (box_width, box_height))
            # Draw the bounding box
            # Green for label Fertilized, Purple for label unfertilized
            color = (155, 255, 0) if label == 0 else (255, 0, 255)
            image_draw.rectangle(annotation_bounding_box,
                                 outline=color, width=10)

        image.save(f"{annotated_image_path}/{name}.png")
        processed_images += 1

        if progress_callback is not None:
            progress_callback(processed_images)
