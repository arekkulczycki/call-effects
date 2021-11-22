import subprocess as sp
import traceback
from multiprocessing import Pipe, Process
from multiprocessing.shared_memory import SharedMemory

import cvzone
import numpy
import pyfakewebcam
from PIL import Image, ImageDraw, ImageFont
from cv2 import cv2
from cv2.cv2 import COLOR_BGR2RGB, IMREAD_UNCHANGED

# from numba import njit
from pygame import mixer

from face_detector import FaceDetector
from keyboard_listener import KeyboardListener

RES_WIDTH = 1280
RES_HEIGHT = 720


def run():
    d_size_frame = numpy.dtype(numpy.uint8).itemsize * numpy.prod((720, 1280, 3))
    try:
        shm_frame = SharedMemory(create=True, size=d_size_frame, name="frame")
    except FileExistsError:
        shm_frame = SharedMemory(create=False, size=d_size_frame, name="frame")
    d_size_face = numpy.dtype(numpy.uint8).itemsize * numpy.prod((5,))
    try:
        shm_face = SharedMemory(create=True, size=d_size_face, name="face")
    except FileExistsError:
        shm_face = SharedMemory(create=False, size=d_size_face, name="face")

    frame_output, frame_input = Pipe()
    face_output, face_input = Pipe()
    detector = FaceDetector()
    detecor_process = Process(
        target=detector.run,
        args=(
            frame_output,
            face_input,
        ),
    )
    detecor_process.start()

    listener_output, listener_input = Pipe()
    listener = KeyboardListener()
    listener_process = Process(target=listener.run, args=(listener_input,))
    listener_process.start()

    frame_output.close()
    face_input.close()
    listener_input.close()

    showing_question_mark = False
    question_mark = cv2.imread("images/question_simple.png", IMREAD_UNCHANGED)
    question_mark = cv2.flip(question_mark, 1)
    question_mark_height = question_mark.shape[0]
    question_mark_width = question_mark.shape[1]

    showing_cowboy_hat = False
    cowboy_hat = cv2.imread("images/cowboy2.png", IMREAD_UNCHANGED)
    cowboy_hat_height = cowboy_hat.shape[0]
    cowboy_hat_width = cowboy_hat.shape[1]

    typing = False
    typed_word = ""

    camera = pyfakewebcam.FakeWebcam("/dev/video6", RES_WIDTH, RES_HEIGHT)

    video_capture = cv2.VideoCapture(0)
    video_capture.set(3, RES_WIDTH)
    video_capture.set(4, RES_HEIGHT)

    face_center = [RES_HEIGHT / 2, RES_WIDTH / 2]
    face_height = 500

    try:
        k = 0
        while True:
            k += 1
            ret, frame = video_capture.read()

            if not ret:
                continue

            if k % 2 == 0:
                # frame_input.send(frame)

                a = numpy.ndarray(
                    shape=frame.shape, dtype=numpy.uint8, buffer=shm_frame.buf
                )
                a[:] = frame
                frame_input.send(k)

            # parse face
            face_data = get_from_pipe(face_output)
            if face_data:
                # print(f'receiving: {time.time()}')
                xmin, ymin, xmax, ymax = face_data
                # xmin, ymin, xmax, ymax, _ = numpy.ndarray(shape=(5,), dtype=numpy.uint8, buffer=shm_face.buf)
                face_center = [(xmin + xmax) / 2, (ymin + ymax) / 2]
                face_height = ymax - ymin
                face_width = xmax - xmin

            key = get_from_pipe(listener_output)
            if key:
                str_key = str(key)
                str_key_clean = str_key.replace("'", "")
                if typing:
                    if str_key == "Key.enter":
                        typing = False
                        typed_word = ""
                    elif str_key.replace("'", "").isalpha() or str_key in (
                        "'!'",
                        "'?'",
                    ):
                        typed_word += str_key_clean
                    elif str_key == "Key.space":
                        typed_word += " "
                    elif str_key == "Key.backspace":
                        typed_word = typed_word[:-1]

                elif str_key == "'p'":
                    print("playing sound")
                    # play_sound()
                elif str_key == "'a'":
                    print("playing applause")
                    play_applause()
                elif str_key == "'j'":
                    print("playing badumtss")
                    play_badumtss()
                elif str_key == "'?'":
                    print("toggling question mark")
                    showing_question_mark = not showing_question_mark
                elif str_key == "'h'":
                    print("toggling cowboy hat")
                    showing_cowboy_hat = not showing_cowboy_hat
                elif str_key == "'t'":
                    print("toggling typing")
                    typing = not typing

            if showing_question_mark:
                desired_size = (
                    int(question_mark_width * face_height / question_mark_height),
                    int(face_height),
                )
                resized = cv2.resize(question_mark, desired_size)

                position = [
                    min(
                        int(face_center[0] - question_mark_width / 2),
                        RES_WIDTH - question_mark_width,
                    ),
                    min(
                        int(face_center[1] - question_mark_height / 2),
                        RES_HEIGHT - question_mark_height,
                    ),
                ]
                try:
                    frame = cvzone.overlayPNG(
                        frame,
                        resized,
                        position,
                    )
                except ValueError:
                    pass

            if showing_cowboy_hat:
                desired_size = (
                    int(cowboy_hat_width * face_height / (1.5 * cowboy_hat_height)),
                    int(face_height / 1.5),
                )
                resized = cv2.resize(cowboy_hat, desired_size)

                position = [
                    min(
                        int(face_center[0] - desired_size[0] / 2),
                        RES_WIDTH - desired_size[0],
                    ),
                    max(0, int(face_center[1] - 0.95 * face_height)),
                ]

                try:
                    frame = cvzone.overlayPNG(
                        frame,
                        resized,
                        position,
                    )
                except ValueError:
                    pass

            if typing and typed_word:
                text_img, w, h = get_text_image(typed_word.upper())
                img_array = numpy.array(text_img)

                resized = cv2.resize(img_array, (int(w / h * 180), 180))
                position = [640 - int(180 * w / h / 2), 270]

                try:
                    frame = cvzone.overlayPNG(
                        frame,
                        resized,
                        position,
                    )
                except ValueError:
                    pass

            frame = cv2.cvtColor(frame, COLOR_BGR2RGB)

            camera.schedule_frame(frame)

    finally:
        listener_process.terminate()
        detecor_process.terminate()

        for shm in [shm_frame, shm_face]:
            shm.close()
            shm.unlink()

        teardown()


def get_from_pipe(output):
    msg = None
    while output.poll():
        msg = output.recv()
    return msg


def get_text_image(text, color=(255, 255, 255), font="fonts/DAGGERSQUARE_ITALIC.otf"):
    image = Image.new(mode="RGBA", size=(1280, 720), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font, 90)

    w, h = draw.textsize(text, font=font)
    draw.text((0, 0), text, font=font, fill=color)
    image = image.crop((0, 0, w, h))

    return image, w, h


def play_applause():
    mixer.init(devicename="Call-effects-sink", frequency=48000)
    mixer.music.load("sounds/applause-4.mp3")
    mixer.music.set_volume(2)
    mixer.music.play()


def play_badumtss():
    mixer.init(devicename="Call-effects-sink", frequency=48000)
    mixer.music.load("sounds/joke_drum_effect.mp3")
    mixer.music.set_volume(2)
    mixer.music.play()


def setup():
    # TODO: second command is specific to this pc
    commands = [
        "pactl load-module module-null-sink sink_name=call-effects-sink sink_properties=device.description=Call-Effects-sink",
        "pactl load-module module-loopback source=alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp_6__source sink=call-effects-sink latency_msec=20",
        "pactl load-module module-remap-source master=call-effects-sink.monitor source_properties=device.description=Call-Effects-mic",
    ]
    for command in commands:
        sp.call(command.split(" "))


def teardown():
    list_devices_command = "pactl list short modules"
    unload_command = "pactl unload-module"

    keys = [
        "master=call-effects-sink.monitor",
        "sink=call-effects-sink",
        "sink_name=call-effects-sink",
    ]

    devices = (
        sp.Popen(list_devices_command.split(" "), stdout=sp.PIPE)
        .stdout.read()
        .decode()
        .split("\n")
    )

    for device in devices:
        for key in keys:
            if key in device:
                try:
                    id = int(device.split("\t")[0])
                except ValueError:
                    print(traceback.format_exc())
                else:
                    retcode = sp.call(f"{unload_command} {id}".split(" "))
                    if retcode != 0:
                        # TODO: handle failures
                        print(f"teardown failed! leftover: {device}")

    print("teardown finished...")


if __name__ == "__main__":
    setup()
    run()
