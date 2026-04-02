import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import close_old_connections
from django.utils import timezone

from ultralytics import YOLO

from .models import VideoInspection, ViolationSnapshot

DEFAULT_PERSON_MODEL = 'yolov8n.pt'

_model_lock = threading.Lock()
_cached_models = None


def _get_model_paths() -> Tuple[str, str, str]:
    person = getattr(settings, 'PPE_PERSON_MODEL_PATH', DEFAULT_PERSON_MODEL)
    helmet = getattr(settings, 'PPE_HELMET_MODEL_PATH', None)
    mask = getattr(settings, 'PPE_MASK_MODEL_PATH', None)
    if helmet is None or mask is None:
        raise RuntimeError('Добавь в settings.py PPE_HELMET_MODEL_PATH и PPE_MASK_MODEL_PATH (пути к best.pt).')
    return person, helmet, mask


def get_models():
    global _cached_models
    with _model_lock:
        if _cached_models is None:
            person_path, helmet_path, mask_path = _get_model_paths()
            _cached_models = {
                'person': YOLO(person_path),
                'helmet': YOLO(helmet_path),
                'mask': YOLO(mask_path),
            }
        return _cached_models


def iou(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    x1 = max(ax1, bx1)
    y1 = max(ay1, by1)
    x2 = min(ax2, bx2)
    y2 = min(ay2, by2)
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    denom = area_a + area_b - inter
    return inter / denom if denom > 0 else 0.0


def box_center(box: Tuple[float, float, float, float]) -> Tuple[float, float]:
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def make_head_zone(person_box: Tuple[float, float, float, float], img_w: int, img_h: int):
    px1, py1, px2, py2 = person_box
    w = px2 - px1
    h = py2 - py1
    zx1 = max(0, int(px1 - 0.15 * w))
    zy1 = max(0, int(py1))
    zx2 = min(img_w - 1, int(px2 + 0.15 * w))
    zy2 = min(img_h - 1, int(py1 + 0.60 * h))
    return (zx1, zy1, zx2, zy2)


def center_in_zone(det_box, zone) -> bool:
    cx, cy = box_center(det_box)
    zx1, zy1, zx2, zy2 = zone
    return zx1 <= cx <= zx2 and zy1 <= cy <= zy2


def select_best(dets: List[dict], zone, ok_name: str, bad_name: str):
    best_ok = None
    best_bad = None
    for det in dets:
        if det['class_name'] not in (ok_name, bad_name):
            continue
        if center_in_zone(det['box'], zone):
            if det['class_name'] == ok_name:
                if best_ok is None or det['conf'] > best_ok['conf']:
                    best_ok = det
            else:
                if best_bad is None or det['conf'] > best_bad['conf']:
                    best_bad = det

    if best_ok and best_bad:
        chosen = best_ok if best_ok['conf'] >= best_bad['conf'] else best_bad
        return chosen['class_name'], chosen
    if best_ok:
        return ok_name, best_ok
    if best_bad:
        return bad_name, best_bad
    return 'unknown', None


@dataclass
class Track:
    id: int
    box: Tuple[float, float, float, float]
    last_seen: int
    miss_helmet: int = 0
    miss_mask: int = 0
    miss_both: int = 0
    cooldown_until: int = 0


def _save_snapshot(inspection: VideoInspection, frame, crop_box, violation_type, ts_sec, frame_idx, track_id,
                   conf_helmet: Optional[float], conf_mask: Optional[float]):
    x1, y1, x2, y2 = crop_box
    x1 = max(0, int(x1))
    y1 = max(0, int(y1))
    x2 = min(frame.shape[1] - 1, int(x2))
    y2 = min(frame.shape[0] - 1, int(y2))

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return

    ok, buf = cv2.imencode('.jpg', crop)
    if not ok:
        return

    snap = ViolationSnapshot(
        inspection=inspection,
        timestamp_sec=float(ts_sec),
        frame_index=int(frame_idx),
        person_track_id=int(track_id),
        violation_type=violation_type,
        conf_helmet=conf_helmet,
        conf_mask=conf_mask,
    )
    filename = f"insp_{inspection.id}_t{int(ts_sec*1000)}_p{track_id}.jpg"
    snap.image.save(filename, ContentFile(buf.tobytes()), save=False)
    snap.save()


def run_inspection(inspection_id: int):
    """Обработка видео. Запускать в отдельном потоке."""
    close_old_connections()
    inspection = VideoInspection.objects.get(id=inspection_id)

    inspection.status = 'processing'
    inspection.started_at = timezone.now()
    inspection.error = ''
    inspection.save(update_fields=['status', 'started_at', 'error'])

    try:
        models = get_models()
        person_model = models['person']
        helmet_model = models['helmet']
        mask_model = models['mask']

        cap = cv2.VideoCapture(inspection.video.path)
        if not cap.isOpened():
            raise RuntimeError('Не удалось открыть видеофайл')

        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 25.0

        stride = max(1, int(inspection.frame_stride))
        eff_fps = fps / stride
        threshold_frames = max(1, int(round(inspection.violation_seconds * eff_fps)))

        PERSON_CONF = 0.25
        HELMET_CONF = 0.45
        MASK_CONF = 0.35
        IMG_SIZE = 640

        tracks: Dict[int, Track] = {}
        next_track_id = 1
        max_age = int(round(eff_fps * 2.0))  # 2 секунды без видимости

        frame_idx = 0
        processed_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            if (frame_idx - 1) % stride != 0:
                continue
            processed_idx += 1

            h, w = frame.shape[:2]
            ts_sec = (frame_idx - 1) / fps

            pres = person_model.predict(
                source=frame,
                conf=PERSON_CONF,
                imgsz=IMG_SIZE,
                classes=[0],
                verbose=False
            )[0]
            persons = [(b.xyxy[0].tolist()) for b in pres.boxes]
            persons = [(x1, y1, x2, y2) for x1, y1, x2, y2 in persons]

            helmet_dets = []
            if inspection.check_helmet:
                hres = helmet_model.predict(source=frame, conf=HELMET_CONF, imgsz=IMG_SIZE, verbose=False)[0]
                hnames = hres.names
                for b in hres.boxes:
                    cls_id = int(b.cls[0].item())
                    conf = float(b.conf[0].item())
                    x1, y1, x2, y2 = b.xyxy[0].tolist()
                    helmet_dets.append({'class_name': hnames[cls_id], 'conf': conf, 'box': (x1, y1, x2, y2)})

            mask_dets = []
            if inspection.check_mask:
                mres = mask_model.predict(source=frame, conf=MASK_CONF, imgsz=IMG_SIZE, verbose=False)[0]
                mnames = mres.names
                for b in mres.boxes:
                    cls_id = int(b.cls[0].item())
                    conf = float(b.conf[0].item())
                    x1, y1, x2, y2 = b.xyxy[0].tolist()
                    mask_dets.append({'class_name': mnames[cls_id], 'conf': conf, 'box': (x1, y1, x2, y2)})

            assigned: Dict[int, Tuple[float, float, float, float]] = {}
            used_tracks = set()

            for pb in persons:
                best_tid = None
                best_i = 0.0
                for tid, tr in tracks.items():
                    if tid in used_tracks:
                        continue
                    v = iou(pb, tr.box)
                    if v > best_i:
                        best_i = v
                        best_tid = tid

                if best_tid is not None and best_i >= 0.35:
                    tr = tracks[best_tid]
                    tr.box = pb
                    tr.last_seen = processed_idx
                    used_tracks.add(best_tid)
                    assigned[best_tid] = pb
                else:
                    tid = next_track_id
                    next_track_id += 1
                    tracks[tid] = Track(id=tid, box=pb, last_seen=processed_idx)
                    used_tracks.add(tid)
                    assigned[tid] = pb

            # удалить старые треки
            to_del = [tid for tid, tr in tracks.items() if processed_idx - tr.last_seen > max_age]
            for tid in to_del:
                tracks.pop(tid, None)

            for tid, pb in assigned.items():
                tr = tracks[tid]
                if processed_idx < tr.cooldown_until:
                    continue

                zone = make_head_zone(pb, w, h)

                helmet_status, helmet_det = ('unknown', None)
                mask_status, mask_det = ('unknown', None)

                if inspection.check_helmet:
                    helmet_status, helmet_det = select_best(helmet_dets, zone, 'helmet', 'no_helmet')
                if inspection.check_mask:
                    mask_status, mask_det = select_best(mask_dets, zone, 'mask', 'no_mask')

                miss_helmet_now = inspection.check_helmet and helmet_status == 'no_helmet'
                miss_mask_now = inspection.check_mask and mask_status == 'no_mask'
                miss_both_now = inspection.check_helmet and inspection.check_mask and miss_helmet_now and miss_mask_now

                tr.miss_helmet = tr.miss_helmet + 1 if miss_helmet_now else 0
                tr.miss_mask = tr.miss_mask + 1 if miss_mask_now else 0
                tr.miss_both = tr.miss_both + 1 if miss_both_now else 0

                violation_type = None
                if inspection.check_helmet and inspection.check_mask:
                    if tr.miss_both >= threshold_frames:
                        violation_type = 'no_helmet_no_mask'
                    elif tr.miss_helmet >= threshold_frames:
                        violation_type = 'no_helmet'
                    elif tr.miss_mask >= threshold_frames:
                        violation_type = 'no_mask'
                elif inspection.check_helmet:
                    if tr.miss_helmet >= threshold_frames:
                        violation_type = 'no_helmet'
                elif inspection.check_mask:
                    if tr.miss_mask >= threshold_frames:
                        violation_type = 'no_mask'

                if violation_type:
                    px1, py1, px2, py2 = pb
                    pw = px2 - px1
                    ph = py2 - py1
                    crop = (px1 - 0.05 * pw, py1 - 0.05 * ph, px2 + 0.05 * pw, py2 + 0.05 * ph)

                    conf_helmet = helmet_det['conf'] if helmet_det else None
                    conf_mask = mask_det['conf'] if mask_det else None

                    _save_snapshot(
                        inspection=inspection,
                        frame=frame,
                        crop_box=crop,
                        violation_type=violation_type,
                        ts_sec=ts_sec,
                        frame_idx=frame_idx,
                        track_id=tid,
                        conf_helmet=conf_helmet,
                        conf_mask=conf_mask,
                    )

                    tr.cooldown_until = processed_idx + threshold_frames
                    tr.miss_helmet = 0
                    tr.miss_mask = 0
                    tr.miss_both = 0

        cap.release()

        inspection.status = 'done'
        inspection.finished_at = timezone.now()
        inspection.save(update_fields=['status', 'finished_at'])

    except Exception as e:
        inspection.status = 'failed'
        inspection.finished_at = timezone.now()
        inspection.error = str(e)
        inspection.save(update_fields=['status', 'finished_at', 'error'])