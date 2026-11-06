"""Local, face-guided camera crops. No identity or active-speaker recognition."""
import hashlib
import json
import math
import logging
from pathlib import Path

import av

MODEL = Path(__file__).parent / 'resources' / 'yunet' / 'face_detection_yunet_2023mar.onnx'
MODEL_SHA256 = '8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4'
VERSION = 1


def source_region(info, clip):
    """Retained source rectangle after removing an edge caption band."""
    width, height = info['width'], info['height']
    top, bottom = 0, height
    if clip.get('cover_source_captions'):
        method = clip.get('source_caption_method', 'cover')
        if method == 'crop_bottom':
            bottom = int(height * clip.get('source_caption_y', 75) / 100 / 2) * 2
        elif method == 'crop_top':
            top = math.ceil(height * (clip.get('source_caption_y', 75) + clip.get('source_caption_height', 25)) / 100 / 2) * 2
    if bottom - top < max(2, height * .1):
        raise ValueError('Keep at least 10% of the source picture when cropping old captions.')
    return width, bottom - top, top


def choose_face(faces, previous, preference, size):
    """Stay near the same visible face; initial crop controls select a subject."""
    if not faces:
        return None
    width, height = size
    anchor = previous or preference
    def cost(face):
        x, y, w, h = face[:4]
        distance = ((x + w / 2 - anchor[0]) / width) ** 2 + ((y + h / 2 - anchor[1]) / height) ** 2
        return distance - min(.08, w * h / (width * height))
    return min(faces, key=cost)


def analyze(source, directory, clip, info, crop_width, crop_height):
    """Decode once, detect at 2 Hz on <=640px frames, and cache the private path."""
    source = Path(source)
    region_w, region_h, region_top = source_region(info, clip)
    initial_x = (region_w - crop_width) * clip.get('crop_x', 50) / 100
    initial_y = (region_h - crop_height) * clip.get('crop_y', 50) / 100
    duration = clip['end'] - clip['start']
    fallback = {'points': [[0, initial_x, initial_y], [duration, initial_x, initial_y]], 'samples': 0, 'detected': 0,
                'notice': 'No visible face detected. Full-screen framing uses your selected crop position.'}
    if region_w - crop_width < 2 and region_h - crop_height < 2:
        return {**fallback, 'notice': 'The source already fills this frame; no moving crop is needed.'}
    signature = {'version': VERSION, 'source': [str(source.resolve()), source.stat().st_size, source.stat().st_mtime_ns],
                 'range': [clip['start'], clip['end']], 'crop': [crop_width, crop_height],
                 'region': [region_w, region_h, region_top], 'initial': [initial_x, initial_y],
                 'webcam': [clip.get(k) for k in ('hide_webcam', 'webcam_x', 'webcam_y', 'webcam_width', 'webcam_height')]}
    key = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:24]
    cache = Path(directory) / f'face-path-{key}.json'
    try:
        if cache.is_file():
            saved = json.loads(cache.read_text(encoding='utf-8'))
            if saved.get('key') == key and saved.get('points'):
                return saved
    except (OSError, ValueError):
        pass
    try:
        import cv2
        cv2.setNumThreads(1)
        if hashlib.sha256(MODEL.read_bytes()).hexdigest() != MODEL_SHA256:
            raise ValueError('Face detector model verification failed')
        detector = cv2.FaceDetectorYN.create(str(MODEL), '', (320, 320), .75, .3, 5000)
        points, samples, detected = [], 0, 0
        previous = None
        preference = (initial_x + crop_width / 2, initial_y + crop_height * .33)
        current_x, current_y = initial_x, initial_y
        next_sample = clip['start']
        with av.open(str(source)) as container:
            stream = container.streams.video[0]
            stream.codec_context.thread_count = 2
            origin = float((stream.start_time or 0) * stream.time_base)
            container.seek(int((origin + clip['start']) / stream.time_base), stream=stream)
            for frame in container.decode(stream):
                if frame.time is None:
                    continue
                timestamp = float(frame.time) - origin
                if timestamp < next_sample - .001:
                    continue
                if timestamp >= clip['end']:
                    break
                scale = min(1, 640 / info['width'])
                image = frame.reformat(width=max(2, round(info['width'] * scale)), height=max(2, round(info['height'] * scale)), format='bgr24').to_ndarray()
                if clip.get('hide_webcam'):
                    x = round(image.shape[1] * clip.get('webcam_x', 75) / 100)
                    y = round(image.shape[0] * clip.get('webcam_y', 0) / 100)
                    right = math.ceil(image.shape[1] * (clip.get('webcam_x', 75) + clip.get('webcam_width', 25)) / 100)
                    bottom = math.ceil(image.shape[0] * (clip.get('webcam_y', 0) + clip.get('webcam_height', 35)) / 100)
                    image[y:bottom, x:right] = 0
                image = image[round(region_top * scale):round((region_top + region_h) * scale)].copy()
                detector.setInputSize((image.shape[1], image.shape[0]))
                _, results = detector.detect(image)
                faces = [] if results is None else [(row[:4] / scale).tolist() for row in results]
                face = choose_face(faces, previous, preference, (region_w, region_h))
                if face is not None:
                    x, y, w, h = face
                    previous = (x + w / 2, y + h / 2)
                    target_x = min(region_w - crop_width, max(0, previous[0] - crop_width / 2))
                    target_y = min(region_h - crop_height, max(0, previous[1] - crop_height * .33))
                    # Small dead zone prevents detector jitter; keep up with real movement.
                    alpha = 1 if not detected else .8
                    if abs(target_x - current_x) > region_w * .008 or not detected:
                        current_x += alpha * (target_x - current_x)
                    if abs(target_y - current_y) > region_h * .008 or not detected:
                        current_y += alpha * (target_y - current_y)
                    detected += 1
                samples += 1
                points.append([round(max(0, timestamp - clip['start']), 4), round(current_x, 2), round(current_y, 2)])
                next_sample = timestamp + .5
        if detected:
            points[0][0] = 0
            points.append([duration, *points[-1][1:]])
            result = {'points': points, 'samples': samples, 'detected': detected,
                      'notice': 'Following a visible face. Check the preview at scene changes; this does not identify the active speaker.'}
        else:
            result = {**fallback, 'samples': samples}
        result['key'] = key
        cache.write_text(json.dumps(result), encoding='utf-8')
        return result
    except Exception as exc:
        logging.getLogger(__name__).warning('Face following unavailable; keeping filled manual crop', exc_info=True)
        return {**fallback, 'notice': f'Face following unavailable ({type(exc).__name__}). Full-screen framing uses your selected crop position.'}


def crop_filter(result, directory, crop_width, crop_height):
    """Use a command file to avoid Windows command-line limits on long clips.

    Runtime crop expressions interpolate at every frame, before speed changes.
    Paths contain only generated hex and live inside the private project folder.
    """
    points = result['points']
    commands = []
    for first, second in zip(points, points[1:]):
        t, x, y = first
        end, nx, ny = second
        if end <= t:
            continue
        for axis, a, b in (('x', x, nx), ('y', y, ny)):
            commands.append(f"{t:.4f} crop@follow {axis} '{a:.2f}+({b-a:.2f})*clip((t-{t:.4f})/{end-t:.4f},0,1)';")
    content = '\n'.join(commands)
    filename = 'face-crop-' + hashlib.sha256(content.encode()).hexdigest()[:24] + '.cmd'
    (Path(directory) / filename).write_text(content, encoding='ascii')
    return f'setpts=PTS-STARTPTS,sendcmd=f={filename},crop@follow={crop_width}:{crop_height}:{points[0][1]}:{points[0][2]}'
