from pathlib import Path

import av
import cv2
import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from backend import main, media, tracking


@pytest.fixture(scope='module')
def moving_face(tmp_path_factory):
    folder = tmp_path_factory.mktemp('moving-face')
    path = folder / 'moving.mp4'
    face = np.asarray(Image.open(Path(__file__).parent / 'fixtures' / 'nasa-astronaut-face.png').convert('RGB'))
    with av.open(str(path), 'w') as video:
        stream = video.add_stream('libx264', rate=12)
        stream.width, stream.height, stream.pix_fmt = 640, 360, 'yuv420p'
        stream.options = {'crf': '18', 'preset': 'ultrafast'}
        for i in range(48):
            image = np.full((360, 640, 3), (70, 110, 150), dtype=np.uint8)
            x = round(20 + 400 * i / 47)
            image[30:222, x:x+192] = face
            # A saturated band represents old, burned-in captions.
            image[288:] = (220, 15, 15)
            frame = av.VideoFrame.from_ndarray(image, format='rgb24')
            for packet in stream.encode(frame):
                video.mux(packet)
        for packet in stream.encode():
            video.mux(packet)
    return path


def options(**changes):
    return {'id': 'reel-test', 'start': 0, 'end': 4,
            **main.EffectSettings(aspect='vertical', framing='follow', style='none', render_quality='fast').model_dump(), **changes}


def image_at(path, seconds):
    with av.open(str(path)) as container:
        for frame in container.decode(video=0):
            if float(frame.time) >= seconds:
                return frame.to_ndarray(format='rgb24')
    raise AssertionError('Missing output frame')


def faces_in(image):
    detector = cv2.FaceDetectorYN.create(str(tracking.MODEL), '', (image.shape[1], image.shape[0]), .7, .3, 5000)
    _, faces = detector.detect(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    return faces


def test_real_detector_tracks_movement_and_render_fills_the_reel(moving_face, tmp_path):
    output = tmp_path / 'reel.mp4'
    result = media.render(moving_face, tmp_path, options(), [], output)
    assert result['framing_analysis']['detected'] >= 6
    assert 'Following a visible face' in result['framing_notice']
    path = next(tmp_path.glob('face-path-*.json'))
    import json
    trajectory = json.loads(path.read_text())
    assert trajectory['points'][-1][1] - trajectory['points'][0][1] > 280
    info = media.probe(output)
    assert (info['width'], info['height']) == (480, 854)
    assert info['duration'] == pytest.approx(4, abs=.2)
    for seconds in (.1, 1.5, 3.5):
        image = image_at(output, seconds)
        detected = faces_in(image)
        assert detected is not None, f'Face lost at {seconds}s'
        x, y, w, h = detected[0][:4]
        assert .15 < (x+w/2)/image.shape[1] < .85
        # Real source color reaches all four edges; no letterbox padding.
        assert image[:6].mean() > 35
        assert image[-6:].mean() > 35
        assert image[:, :6].mean() > 35
        assert image[:, -6:].mean() > 35
    # Caption/style-only changes reuse the trajectory, avoiding a second decode.
    before = path.stat().st_mtime_ns
    tracking.analyze(moving_face, tmp_path, options(style='clean'), media.probe(moving_face), 202, 360)
    assert path.stat().st_mtime_ns == before


def test_bottom_source_caption_crop_removes_band_and_adds_new_captions(moving_face, tmp_path):
    output = tmp_path / 'clean-reel.mp4'
    clip = options(cover_source_captions=True, source_caption_method='crop_bottom', source_caption_y=80,
                   source_caption_height=20, style='clean', caption_mode='phrase', speed=2, sound_effect='ding')
    result = media.render(moving_face, tmp_path, clip, [{'start': 0, 'end': 4, 'text': 'NEW CAPTIONS'}], output)
    assert result['framing_analysis']['detected'] >= 6
    info = media.probe(output)
    assert (info['width'], info['height']) == (480, 854)
    assert info['duration'] == pytest.approx(2, abs=.2)
    assert info['has_audio']  # Composite sound-effects path also uses the moving crop.
    image = image_at(output, 1)
    assert image[-10:, :, 0].mean() < 130  # red old-caption band is gone
    assert image[-10:].mean() > 35  # no replacement black bar
    assert (image[620:780].min(axis=2) > 210).sum() > 100  # new white caption pixels
    assert 'NEW CAPTIONS' in next(tmp_path.glob('*.ass')).read_text(encoding='utf-8')


def test_no_face_fallback_is_filled_and_reports_honestly(tmp_path):
    source = tmp_path / 'plain.mp4'
    media.run(['-f', 'lavfi', '-i', 'color=c=0x467096:size=320x180:rate=10', '-t', '1', str(source)])
    output = tmp_path / 'output.mp4'
    result = media.render(source, tmp_path, options(end=1), [], output)
    assert result['framing_analysis']['detected'] == 0
    assert 'No visible face' in result['framing_notice']
    assert image_at(output, .4).mean() > 60


def test_top_crop_and_missing_detector_preserve_working_export(tmp_path, monkeypatch):
    source = tmp_path / 'plain.mp4'
    media.run(['-f', 'lavfi', '-i', 'color=white:size=320x180:rate=10', '-vf', 'drawbox=x=0:y=0:w=iw:h=36:color=red:t=fill', '-t', '1', str(source)])
    monkeypatch.setattr(tracking, 'MODEL', tmp_path / 'missing.onnx')
    output = tmp_path / 'output.mp4'
    result = media.render(source, tmp_path, options(end=1, cover_source_captions=True, source_caption_method='crop_top', source_caption_y=0, source_caption_height=20), [], output)
    assert 'unavailable' in result['framing_notice']
    assert image_at(output, .4)[:20].mean() > 220


def test_face_preference_stays_with_nearby_subject():
    faces = [[30, 20, 70, 100], [400, 20, 90, 110]]
    assert tracking.choose_face(faces, None, (450, 80), (640, 360)) == faces[1]
    assert tracking.choose_face(faces, (65, 70), (450, 80), (640, 360)) == faces[0]


@pytest.mark.parametrize('method,y,height', [('crop_bottom', 2, 20), ('crop_top', 75, 25)])
def test_old_caption_crop_cannot_remove_the_entire_picture(method, y, height):
    with pytest.raises(ValidationError, match='10%'):
        main.EffectSettings(cover_source_captions=True, source_caption_method=method, source_caption_y=y, source_caption_height=height)


def test_legacy_framing_and_cover_defaults_stay_compatible():
    legacy = main.EffectSettings()
    assert legacy.framing == 'fit' and legacy.source_caption_method == 'cover'
    assert main.EffectSettings(framing='follow').framing == 'follow'
    # Same-ratio footage needs no decode or detector setup.
    result = tracking.analyze(Path('not-opened.mp4'), Path('.'), options(aspect='original'), {'width': 640, 'height': 360}, 640, 360)
    assert result['samples'] == 0 and 'already fills' in result['notice']
