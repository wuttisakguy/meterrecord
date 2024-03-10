from ultralytics import YOLO
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import os

class MeterReader:
    """
    A class to read meter values using a YOLO model. It processes an image to detect digits and interprets
    the meter reading, ensuring that exactly four digits are read, or returns 'Undefined' if the conditions are not met.

    Attributes:
        model (YOLO): The YOLO model used for digit detection.
        confidence_level (float): The confidence threshold for digit detection.

    Methods:
        read_meter(file_path): Reads the meter value from an image file.
        read_meter_with_plot(file_path): Reads the meter value and plots the image with bounding boxes.
    """
    def __init__(self, model_path, confidence_level=0.6):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
        self.model = YOLO(model_path)
        self.confidence_level = confidence_level

    def _load_and_process_image(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image file not found at {file_path}")
        image = Image.open(file_path).resize((640, 640))
        return np.array(image)

    def _filter_and_sort_digits(self, boxes_data):
        digit_centers = [(box[0], box[1], box[2], box[3], box[5]) for box in boxes_data if box[4] > self.confidence_level]
        digit_centers.sort(key=lambda x: x[0])  # Sort based on x_min value

        filtered_digits = []
        i = 0
        #Check if two digits might be detected in the same horizontal space and  very close to each other horizontally
        while i < len(digit_centers):
            if i < len(digit_centers) - 1 and abs(digit_centers[i][0] - digit_centers[i+1][0]) < 10: # 10 is threshold from visualize distance between two digits 
                # Check if the digits are vertically aligned (similar x position)
                top_digit = digit_centers[i] if digit_centers[i][1] < digit_centers[i+1][1] else digit_centers[i+1]
                bottom_digit = digit_centers[i+1] if digit_centers[i][1] < digit_centers[i+1][1] else digit_centers[i]
                
                # Assuming a forward-moving meter, choose the bottom digit
                filtered_digits.append(bottom_digit)
                i += 2  # Skip the next digit as it's part of a transitioning pair
            else:
                filtered_digits.append(digit_centers[i])
                i += 1

        if len(filtered_digits) == 4:
            return ''.join([str(int(digit[4])) for digit in filtered_digits])
        return "Undefined"


    def _detect_digits(self, image_np):
        results = self.model.predict(image_np)
        if len(results) == 0:
            return None
        return results[0].boxes.data.cpu()

    def read_meter(self, file_path):
        image_np = self._load_and_process_image(file_path)
        boxes_data = self._detect_digits(image_np)
        return "No digits detected" if boxes_data is None else self._filter_and_sort_digits(boxes_data)

    def read_meter_with_plot(self, file_path):
        image_np = self._load_and_process_image(file_path)
        boxes_data = self._detect_digits(image_np)

        if boxes_data is None:
            print("No digits detected")
            return "Undefined"

        fig, ax = plt.subplots(1)
        ax.imshow(image_np)

        for box in boxes_data:
            x_min, y_min, x_max, y_max, confidence, class_label = box
            if confidence > self.confidence_level:
                rect = plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min, fill=False, color='red')
                ax.add_patch(rect)
                ax.text(x_min, y_min, str(int(class_label)), color='black', fontsize=6, fontweight='bold', bbox=dict(facecolor='white', edgecolor='none', pad=2.0))

        meter_reading = self._filter_and_sort_digits(boxes_data)
        print("Meter Reading:", meter_reading)
        plt.show()
        return meter_reading
    

    def read_meter_value_only(self, file_path):
        image_np = self._load_and_process_image(file_path)
        boxes_data = self._detect_digits(image_np)

        if boxes_data is None:
            print("No digits detected")
            return "Undefined"

        fig, ax = plt.subplots(1)
        ax.imshow(image_np)

        for box in boxes_data:
            x_min, y_min, x_max, y_max, confidence, class_label = box
            if confidence > self.confidence_level:
                rect = plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min, fill=False, color='red')
                ax.add_patch(rect)
                ax.text(x_min, y_min, str(int(class_label)), color='black', fontsize=6, fontweight='bold', bbox=dict(facecolor='white', edgecolor='none', pad=2.0))

        meter_reading = self._filter_and_sort_digits(boxes_data)
        # print("Meter Reading:", meter_reading)
        # plt.show()
        return meter_reading
