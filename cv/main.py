import cv2
import numpy as np

def createPattern(img):
    # Convert to HSV
    imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Define your color range
    lower = np.array([0, 79, 120])
    upper = np.array([179, 255, 255])
    # Create mask and apply it
    mask = cv2.inRange(imgHSV, lower, upper)
    imgResult = cv2.bitwise_and(img, img, mask=mask)
    # Edge detect on masked image
    imgCanny = cv2.Canny(imgResult, 100, 500)
    return imgCanny

def main():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Could not open webcam")
        return
    print("✅ Webcam opened. Press 'q' to quit.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to grab frame")
            break

        # Process frame
        edges = createPattern(frame)

        # Stack original and edges horizontally
        combined = np.hstack((frame, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)))

        cv2.imshow("Original (L) | Pattern Edges (R)", combined)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
