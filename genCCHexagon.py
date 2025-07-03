import cv2
import numpy as np
from datetime import datetime, timezone
from PIL import ImageFont, ImageDraw, Image
import qrcode
import textwrap
import re
import os
import logging
import sys

here = os.path.abspath(os.path.dirname(__file__))
y_draw = 20

# Set up logging
log_level = os.getenv("LOG_LEVEL", "DEBUG")
numeric_level = getattr(logging, log_level.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {log_level}")

logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

def break_into_lines(text, max_length=20):
    # Define a regex pattern to split on punctuation (except apostrophes and other pronunciation marks)
    pattern = r"[\s,.;:!?\-—]|\\x[0-9A-Fa-f]{2}"
    # Split the text into parts based on the pattern
    parts = re.split(pattern, text)
    # Reconstruct the text with spaces around punctuation for proper wrapping
    reconstructed_text = " ".join([part if part.strip() else " " for part in parts])
    # Use textwrap to wrap the text into lines of max_length
    wrapped_lines = textwrap.wrap(
        reconstructed_text, width=max_length, break_long_words=False
    )
    return wrapped_lines

def drawTextCenteredFit(
    draw,
    image_size,
    text,
    font_path,
    fill,
    max_width=550,
    max_height=300,
    y_center=250,
    font_size=180,
):
    og_font_size = font_size
    spacing = font_size / 18  # Spacing between lines
    lines = []
    # Break text into lines
    for line in break_into_lines(text, max_length=15 + len(text) / 5):
        lines.append({"content": line})
    logging.debug(lines)
    # Adjust font size until the text fits within the bounds
    while True:
        font = ImageFont.truetype(font_path, font_size)
        total_height = 0
        max_line_width = 0
        # Calculate the total height and maximum line width
        for line in lines:
            bbox = font.getbbox(line["content"])
            line["width"] = bbox[2] - bbox[0]
            line["height"] = bbox[3] - bbox[1]
            total_height += line["height"] + spacing
            if line["width"] > max_line_width:
                max_line_width = line["width"]
        # Check if the text fits within the bounds
        if max_line_width <= max_width and total_height <= max_height:
            break
        else:
            # Reduce the font size and try again
            font_size -= 1
            if font_size < 1:
                raise ValueError("Text cannot fit within the specified bounds.")
            else:
                spacing = 10 * font_size / og_font_size
    # Calculate the starting y-position for vertical centering
    total_height -= spacing  # Remove the last spacing
    ypos = y_center - (total_height / 2)
    # Draw the text line by line
    for line in lines:
        bbox = font.getbbox(line["content"])
        x = (image_size - line["width"]) // 2  # Center horizontally
        draw.text((x, ypos), line["content"], font=font, fill=fill)
        ypos += line["height"] + spacing  # Add spacing between lines

def drawTextCentered(draw, image_size, text, font, fill):
    global y_draw
    """Draw text centered horizontally on the given y-coordinate."""
    # Use font.getbbox for text dimensions
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]  # Calculate width from bounding box
    text_height = bbox[3] - bbox[1]  # Calculate height from bounding box
    x = (image_size - text_width) // 2  # Calculate horizontal center
    draw.text((x, y_draw), text, font=font, fill=fill)
    y_draw += text_height + 20

def generate_hex(image_size, font_large, font_medium):
    global y_draw
    # Create a blank transparent image (RGBA)
    image = np.zeros((image_size, image_size, 4), dtype=np.uint8)
    # Define the center and radius for the hexagon
    center = (image_size // 2, image_size // 2)
    radius = image_size // 2.05
    # Calculate the vertices of the hexagon
    hexagon = []
    for i in range(6):
        angle = np.deg2rad(i * 60)  # Convert angle to radians
        x = int(center[0] + radius * np.cos(angle))
        y = int(center[1] + radius * np.sin(angle))
        hexagon.append((x, y))
    hexagon = np.array(hexagon, dtype=np.int32)  # Convert to numpy array
    # Create a mask for the hexagon
    mask = np.zeros((image_size, image_size), dtype=np.uint8)
    cv2.fillPoly(mask, [hexagon], color=255)
    # Generate a gradient
    gradient_start_color = np.array([255, 100, 50, 255])  # RGBA start color
    gradient_end_color = np.array([0, 0, 0, 255])  # RGBA end color
    # Get coordinates of the masked points
    mask_points = np.where(mask > 0)
    y_coords, x_coords = mask_points
    # Normalize y-coordinates for gradient interpolation
    alpha = y_coords / float(image_size)
    # Interpolate gradient colors
    gradient_colors = (
        (1 - alpha[:, None]) * gradient_start_color
        + alpha[:, None] * gradient_end_color
    ).astype(np.uint8)
    # Assign gradient colors to the hexagon in the image
    image[y_coords, x_coords] = gradient_colors
    # Draw the hexagon outline
    cv2.polylines(
        image, [hexagon], isClosed=True, color=(255, 255, 255, 255), thickness=13
    )
    # Convert image to PIL format for text addition
    pil_image = Image.fromarray(image)
    draw = ImageDraw.Draw(pil_image)
    y_draw = int(image_size * 0.40)
    drawTextCentered(
        draw, image_size, "Code Collective", font_large, (255, 255, 255, 255)
    )
    return pil_image, draw

def generate_badge(output_file):
    time = datetime.now(timezone.utc)  # Get the current time in UTC
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S_%Z")  # Include timezone name
    global y_draw
    y_draw = 30
    image_size = 1920
    font_path = "./nofile"  # Adjust font path as needed
    font_large = ImageFont.truetype(font_path, image_size // 10)
    font_medium = ImageFont.truetype(font_path, image_size // 16)
    font_small = ImageFont.truetype(font_path, image_size // 60)
    
    pil_image, draw = generate_hex(image_size, font_large, font_medium)
    
    # Save the final image
    final_image = np.array(pil_image)
    cv2.imwrite(output_file, final_image)
    
    logging.debug(f"Badge with text and QR code saved to {output_file}")
    print(f"Badge saved to: {output_file}")
    return output_file

if __name__ == "__main__":
    generate_badge("cchex.webp")