import cv2

for i in range(5):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)

    if cap.isOpened():
        ret, frame = cap.read()

        print("Camera:", i)
        print("Mo duoc:", cap.isOpened())
        print("Doc duoc anh:", ret)

        if ret and frame is not None:
            print("Kich thuoc:", frame.shape)

            cv2.imshow(f"Camera {i}", frame)
            cv2.waitKey(2000)
            cv2.destroyAllWindows()

    else:
        print("Camera", i, "khong mo duoc")

    cap.release()