from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from .models import UserRegistrationModel
from .forms import UserRegistrationForm
from ultralytics import YOLO
import cv2
import numpy as np
import os

# Create your views here.
def UserRegisterActions(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            print('Data is Valid')
            form.save()
            messages.success(request, 'You have been successfully registered')
            form = UserRegistrationForm()
        else:
            messages.success(request, 'Email or Mobile Already Existed')
            print("Invalid form")
    else:
        form = UserRegistrationForm()
    return render(request, 'UserRegister.html', {'form': form})

def UserLoginCheck(request):
    if request.method == "POST":
        loginid = request.POST.get('loginid')
        pswd = request.POST.get('pswd')
        print("Login ID = ", loginid, ' Password = ', pswd)
        try:
            check = UserRegistrationModel.objects.get(
                loginid=loginid, password=pswd)
            status = check.status
            print('Status is = ', status)
            if status == "activated":
                request.session['id'] = check.id
                request.session['loggeduser'] = check.name
                request.session['loginid'] = loginid
                request.session['email'] = check.email
                print("User id At", check.id, status)
                return render(request, 'users/UserHome.html', {})
            else:
                messages.success(request, 'Your Account Not at activated')
        except Exception as e:
            print('Exception is ', str(e))
            pass
        messages.success(request, 'Invalid Login id and password')
    return render(request, 'UserLogin.html', {})

def UserHome(request):
    return render(request, 'Users/UserHome.html', {})


# Path to YOLOv8 model
MODEL_PATH = os.path.join(settings.MEDIA_ROOT, 'yolov8n.pt')

def upload_video(request):
    if request.method == "POST" and request.FILES.get('video'):
        uploaded_file = request.FILES['video']
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploaded_videos'))
        filename = fs.save(uploaded_file.name, uploaded_file)
        uploaded_video_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_videos', filename)
        
        # Process the uploaded video
        output_video_path = process_video(uploaded_video_path)
        video_url = os.path.join(settings.MEDIA_URL, 'output_videos', os.path.basename(output_video_path))
        
        return render(request, 'Users/result.html', {'video_url': video_url})
    return render(request, 'Users/upload.html')

def process_video(video_path):
    output_dir = os.path.join(settings.MEDIA_ROOT, 'output_videos')
    os.makedirs(output_dir, exist_ok=True)
    output_video_path = os.path.join(output_dir, f'processed_{os.path.basename(video_path)}')
    
    model = YOLO(MODEL_PATH)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Error opening video file.")
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))
    
    scale_factor = 0.05
    prev_positions = {}
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        results = model(frame)
        
        for result in results[0].boxes:
            x1, y1, x2, y2 = result.xyxy[0].cpu().numpy()
            class_id = int(result.cls.cpu().item())
            
            if class_id == 2:  # Car class ID in COCO dataset
                car_id = str(int(x1))
                curr_bbox = (x1, y1, x2, y2)
                
                if car_id in prev_positions:
                    speed = estimate_speed(prev_positions[car_id], curr_bbox, fps, scale_factor)
                    cv2.putText(frame, f"Speed: {speed:.2f} km/h", (int(x1), int(y1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                prev_positions[car_id] = curr_bbox
        
        out.write(frame)
    
    cap.release()
    out.release()
    return output_video_path

def estimate_speed(prev_bbox, curr_bbox, fps, scale_factor):
    prev_center = ((prev_bbox[0] + prev_bbox[2]) / 2, (prev_bbox[1] + prev_bbox[3]) / 2)
    curr_center = ((curr_bbox[0] + curr_bbox[2]) / 2, (curr_bbox[1] + curr_bbox[3]) / 2)
    distance = np.linalg.norm(np.array(curr_center) - np.array(prev_center))
    return (distance * scale_factor) * fps * 3.6




from django.shortcuts import render
from django.http import StreamingHttpResponse
from ultralytics import YOLO
import cv2
import os
from django.conf import settings

MODEL_PATH = os.path.join(settings.MEDIA_ROOT, 'yolov8n.pt')

def detect_live_stream():
    model = YOLO(MODEL_PATH)
    cap = cv2.VideoCapture(0)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps == 0:  # If FPS detection fails, use a default value
        fps = 30
    
    prev_detections = {}
    scale_factor = 0.1  # Meters per pixel, adjust based on your camera setup

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)  # Run YOLO model
        current_detections = {}

        for result in results[0].boxes:
            x1, y1, x2, y2 = result.xyxy[0].cpu().numpy()
            class_id = int(result.cls.cpu().item())
            confidence = float(result.conf.cpu().item())

            # Only process cars (class_id 2) with high confidence
            if class_id == 2 and confidence > 0.5:
                bbox = (int(x1), int(y1), int(x2), int(y2))
                center = ((x1 + x2) / 2, (y1 + y2) / 2)
                
                # Calculate speed if we have previous detection
                speed = None
                for car_id, prev_bbox in prev_detections.items():
                    # Check if this is likely the same car (based on position)
                    prev_center = ((prev_bbox[0] + prev_bbox[2]) / 2, (prev_bbox[1] + prev_bbox[3]) / 2)
                    distance = ((center[0] - prev_center[0])**2 + (center[1] - prev_center[1])**2)**0.5
                    
                    if distance < 100:  # Threshold for considering it the same car
                        speed = estimate_speed(prev_bbox, bbox, fps, scale_factor)
                        current_detections[car_id] = bbox
                        break
                
                if speed is None:
                    # New car detected
                    car_id = len(current_detections)
                    current_detections[car_id] = bbox
                    speed = 0

                # Draw bounding box and speed
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                speed_text = f"Speed: {speed:.1f} km/h"
                cv2.putText(frame, speed_text, (int(x1), int(y1) - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(frame, f"Confidence: {confidence:.2f}", (int(x1), int(y1) - 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        prev_detections = current_detections.copy()

        _, jpeg = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

    cap.release()

def live_feed(request):
    return StreamingHttpResponse(detect_live_stream(), content_type='multipart/x-mixed-replace; boundary=frame')

def live_stream_page(request):
    return render(request, 'Users/live.html')


# ==========================
# 2. Image-Based Speed Detection
# ==========================
def upload_image(request):
    if request.method == "POST" and request.FILES.get('image'):
        try:
            uploaded_file = request.FILES['image']
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploaded_images'))
            file_path = fs.save(uploaded_file.name, uploaded_file)
            uploaded_image_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_images', file_path)

            # Process the image
            processed_image_path = process_image(uploaded_image_path)
            
            if processed_image_path:
                return render(request, 'Users/display.html', {
                    'filename': os.path.basename(processed_image_path)
                })
            else:
                return render(request, 'Users/display.html', {
                    'error_message': 'No vehicles detected in the image.'
                })
                
        except Exception as e:
            return render(request, 'Users/display.html', {
                'error_message': f'Error processing image: {str(e)}'
            })

    return render(request, 'Users/upload_image.html')

def process_image(image_path):
    try:
        model = YOLO(MODEL_PATH)
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Could not read the image file")

        results = model(img)
        vehicles_detected = False

        for result in results[0].boxes:
            x1, y1, x2, y2 = result.xyxy[0].cpu().numpy()
            class_id = int(result.cls.cpu().item())
            confidence = float(result.conf.cpu().item())

            # Class 2 is car in COCO dataset
            if class_id == 2 and confidence > 0.5:
                vehicles_detected = True
                cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(img, f"Car ({confidence:.2f})", (int(x1), int(y1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        if not vehicles_detected:
            return None

        # Save the processed image
        processed_image_path = image_path.replace("uploaded_images", "processed_images")
        os.makedirs(os.path.dirname(processed_image_path), exist_ok=True)
        cv2.imwrite(processed_image_path, img)

        return processed_image_path

    except Exception as e:
        print(f"Error in process_image: {str(e)}")
        raise

# ==========================
# Speed Calculation Helper
# ==========================
def estimate_speed(prev_bbox, curr_bbox, fps, scale_factor):
    prev_center = ((prev_bbox[0] + prev_bbox[2]) / 2, (prev_bbox[1] + prev_bbox[3]) / 2)
    curr_center = ((curr_bbox[0] + curr_bbox[2]) / 2, (curr_bbox[1] + curr_bbox[3]) / 2)
    distance = np.sqrt((curr_center[0] - prev_center[0]) ** 2 +
                       (curr_center[1] - prev_center[1]) ** 2)
    return (distance * scale_factor) * fps * 3.6  # Convert m/s to km/h
