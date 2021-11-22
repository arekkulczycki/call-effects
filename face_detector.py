import time
from multiprocessing.shared_memory import SharedMemory
from pickle import UnpicklingError

import numpy
from deepface.detectors.FaceDetector import detect_faces, build_model


class FaceDetector:
    def run(self, frame_pipe, face_pipe):
        print("face detection started...")

        deepface_detector = build_model("opencv")

        # detector = face_detection.build_detector(
        #     "RetinaNetMobileNetV1", confidence_threshold=0.5, nms_iou_threshold=0.3
        # )

        shm_frame = SharedMemory(name="frame")
        # shm_face = SharedMemory(name="face")

        while True:
            id = self.get_from_pipe(frame_pipe)
            frame = self.get_from_shm(shm_frame)

            if id is None or frame is None:
                time.sleep(0.005)
                continue

            try:
                # faces = detector.batched_detect()
                # t0 = time.time()

                # faces = detector.detect(frame)
                faces = detect_faces(deepface_detector, "opencv", frame, align=False)

                # print(time.time() - t0)
                if len(faces) > 0:
                    # xmin, ymin, xmax, ymax, _ = faces[0]
                    xmin, ymin, w, h, = faces[
                        0
                    ][1]
                    xmax, ymax = xmin + w, ymin + h

                    # print(f'sending: {time.time()}')
                    face_pipe.send([xmin, ymin, xmax, ymax])
            except Exception as e:
                print(e)
            else:
                time.sleep(0.005)

    @staticmethod
    def get_from_shm(shm):
        return numpy.ndarray(shape=(720, 1280, 3), dtype=numpy.uint8, buffer=shm.buf)

    @staticmethod
    def get_from_pipe(output):
        while output.poll():
            try:
                id = output.recv()
                return id
            except UnpicklingError:
                print("unpickling error")
            except EOFError:
                print("ran out of input")
            except FileNotFoundError:
                print("file not found")
