#!/bin/bash

# Loop through each jpg image in the TestImages directory
for image in ProcessedImages/TestImages2/*.jpg; do
    # Extract the name without extension and directory
    name=$(basename "$image" .jpg)
    
    # Check if the corresponding text file exists
    if [ -e "ProcessedImages/predict/labels/$name.txt" ]; then
        # Run the bounding box script
        echo "Processing $image with bounding box data from ProcessedImages/predict/labels/$name.txt"
        python3.11 boundingbox.py "$image" "ProcessedImages/predict/labels/$name.txt"
    else
        echo "No bounding box file found for $image. Skipping..."
    fi
done

