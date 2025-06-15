import cv2
import numpy as np
import subprocess
import os

videoname = "baltimorenight_15s.mp4"
temp_output = videoname.replace(".mp4", "_temp.avi")
final_output = videoname.replace(".mp4", "_crossfaded.mp4")
fade_duration = 2  # seconds

cap = cv2.VideoCapture(videoname)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fade_frames = int(fps * fade_duration)

if total_frames <= fade_frames * 2:
    raise ValueError("Video is too short for the desired crossfade duration.")

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Intermediate format
out = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))

# Read all frames
frames = []
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frames.append(frame)
cap.release()

# Extract segments
start = frames[:fade_frames]
middle = frames[fade_frames:-fade_frames]
end = frames[-fade_frames:]

# Write middle
for frame in middle:
    out.write(frame)

# Write crossfade from end to start
for i in range(fade_frames):
    alpha = 1.0 - (i / fade_frames)
    beta = 1.0 - alpha
    blended = cv2.addWeighted(end[i], alpha, start[i], beta, 0)
    out.write(blended)

out.release()

# Re-encode to web-optimized MP4 with H.264
subprocess.run([
    "ffmpeg", "-y", "-i", temp_output,
    "-c:v", "libx264", "-preset", "slow", "-crf", "23",  # Adjust CRF for quality
    "-movflags", "+faststart",  # For web streaming
    "-pix_fmt", "yuv420p",      # Ensures compatibility
    final_output
])

# Optional: remove temp file
os.remove(temp_output)

print("✅ Done:", final_output)
