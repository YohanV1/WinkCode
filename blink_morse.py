import math
from imutils.video import VideoStream
from imutils import face_utils
import imutils
import dlib
import cv2
import keyboard
import morse_code
import constants


def main():
    config = {
        "landmark_predictor": "shape_predictor_68_face_landmarks.dat"
    }

    video_stream, face_detector, landmark_predictor, left_eye_indices, right_eye_indices = initialize_video(config)
    morse_code_sequence = process_video_stream(video_stream, face_detector, landmark_predictor, left_eye_indices, right_eye_indices)
    terminate_stream(video_stream)
    display_results(morse_code_sequence)


def compute_eye_aspect_ratio(eye_points):
    # Calculate the vertical distances between the eye landmarks
    vertical_dist_1 = math.dist(eye_points[1], eye_points[5])
    vertical_dist_2 = math.dist(eye_points[2], eye_points[4])

    # Calculate the horizontal distance between the eye landmarks
    horizontal_dist = math.dist(eye_points[0], eye_points[3])

    # Compute the eye aspect ratio (EAR)
    ear = (vertical_dist_1 + vertical_dist_2) / (2.0 * horizontal_dist)

    return ear


def initialize_video(config):
    print("Initializing facial landmark detector...")
    face_detector = dlib.get_frontal_face_detector()
    landmark_predictor = dlib.shape_predictor(config["landmark_predictor"])

    # Get the indices of facial landmarks for the eyes
    left_eye_indices, right_eye_indices = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"], face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

    print("Starting video stream...")
    print("Press 'q' or close eyes for {} frames to stop.".format(constants.BREAK_LOOP_FRAMES))
    video_stream = VideoStream(src=0).start()

    return video_stream, face_detector, landmark_predictor, left_eye_indices, right_eye_indices


def process_video_stream(video_stream, face_detector, landmark_predictor, left_eye_indices, right_eye_indices):
    blink_counter, exit_counter, open_eyes_counter = 0, 0, 0
    eyes_closed = False
    word_pause = False
    pause_active = False

    complete_morse_code = ""
    morse_word = ""
    current_morse_char = ""

    while True:
        frame = video_stream.read()
        frame = imutils.resize(frame, width=450)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detected_faces = face_detector(gray_frame, 0)

        for face in detected_faces:
            facial_landmarks = landmark_predictor(gray_frame, face)
            facial_landmarks = face_utils.shape_to_np(facial_landmarks)

            left_eye = facial_landmarks[left_eye_indices[0]:left_eye_indices[1]]
            right_eye = facial_landmarks[right_eye_indices[0]:right_eye_indices[1]]
            left_ear = compute_eye_aspect_ratio(left_eye)
            right_ear = compute_eye_aspect_ratio(right_eye)
            average_ear = (left_ear + right_ear) / 2.0

            left_eye_hull = cv2.convexHull(left_eye)
            right_eye_hull = cv2.convexHull(right_eye)
            cv2.drawContours(frame, [left_eye_hull], -1, (0, 255, 0), 1)
            cv2.drawContours(frame, [right_eye_hull], -1, (0, 255, 0), 1)

            if average_ear < constants.EYE_AR_THRESH:
                blink_counter += 1
                exit_counter += 1

                if blink_counter >= constants.EYE_AR_CONSEC_FRAMES:
                    eyes_closed = True

                if not pause_active:
                    current_morse_char = ""

                if exit_counter >= constants.BREAK_LOOP_FRAMES:
                    break
            else:
                if exit_counter < constants.BREAK_LOOP_FRAMES:
                    exit_counter = 0
                open_eyes_counter += 1

                if blink_counter >= constants.EYE_AR_CONSEC_FRAMES_CLOSED:
                    morse_word += "-"
                    complete_morse_code += "-"
                    current_morse_char += "-"
                    blink_counter = 0
                    eyes_closed = False
                    pause_active = True
                    open_eyes_counter = 0
                elif eyes_closed:
                    morse_word += "."
                    complete_morse_code += "."
                    current_morse_char += "."
                    blink_counter = 1
                    eyes_closed = False
                    pause_active = True
                    open_eyes_counter = 0
                elif pause_active and open_eyes_counter >= constants.PAUSE_CONSEC_FRAMES:
                    morse_word += "/"
                    complete_morse_code += "/"
                    current_morse_char = "/"
                    pause_active = False
                    word_pause = True
                    eyes_closed = False
                    open_eyes_counter = 0
                    keyboard.write(morse_code.from_morse(morse_word))
                    morse_word = ""
                elif word_pause and open_eyes_counter >= constants.WORD_PAUSE_CONSEC_FRAMES:
                    complete_morse_code += "¦/"
                    current_morse_char = ""
                    word_pause = False
                    eyes_closed = False
                    open_eyes_counter = 0
                    keyboard.write(morse_code.from_morse("¦/"))

            cv2.putText(frame, "EAR: {:.2f}".format(average_ear), (300, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, "{}".format(current_morse_char), (100, 200),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)

            print("\033[K", "morse_word: {}".format(morse_word), end="\r")

        cv2.imshow("Video Stream", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or exit_counter >= constants.BREAK_LOOP_FRAMES:
            keyboard.write(morse_code.from_morse(morse_word))
            break

    return complete_morse_code


def terminate_stream(video_stream):
    cv2.destroyAllWindows()
    video_stream.stop()


def display_results(complete_morse_code):
    print("Morse Code Sequence: ", complete_morse_code.replace("¦", " "))
    print("Decoded Message: ", morse_code.from_morse(complete_morse_code))


if __name__ == "__main__":
    main()
