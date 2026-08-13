import re
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.urls import reverse

from apps.content_security.models import HLSPackage

SEGMENT_NAME_PATTERN = re.compile(r'^seg_\d{4}\.ts$')


def package_lesson_video(lesson):
    """Transcodes lesson.video_file into an AES-128 encrypted HLS package (.m3u8 + .ts
    segments). Runs synchronously via ffmpeg — for very large libraries this should be
    moved behind a task queue, but a direct call keeps the dependency surface minimal."""

    from apps.courses.models import Lesson

    if lesson.content_type != Lesson.TYPE_VIDEO or not lesson.video_file:
        raise ValueError('Cette leçon ne contient pas de vidéo à transcoder.')

    package, _ = HLSPackage.objects.get_or_create(lesson=lesson)
    package.status = HLSPackage.STATUS_PROCESSING
    package.error_message = ''
    package.save(update_fields=['status', 'error_message'])

    output_dir_rel = f'hls/{lesson.id}'
    output_dir = Path(settings.MEDIA_ROOT) / output_dir_rel
    output_dir.mkdir(parents=True, exist_ok=True)

    key_bytes = secrets.token_bytes(16)
    iv_bytes = secrets.token_bytes(16)

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            # ffmpeg needs a real local path — copy the source out of its storage
            # backend (local disk or a remote one like R2) into the temp dir first.
            source_path = Path(tmp_dir) / f'source{Path(lesson.video_file.name).suffix}'
            with lesson.video_file.open('rb') as src, open(source_path, 'wb') as dst:
                shutil.copyfileobj(src, dst)

            key_file_path = Path(tmp_dir) / 'enc.key'
            key_file_path.write_bytes(key_bytes)

            keyinfo_path = Path(tmp_dir) / 'keyinfo.txt'
            keyinfo_path.write_text(f'urn:lmspro:hls-key\n{key_file_path}\n{iv_bytes.hex()}\n')

            segment_duration = settings.HLS_SEGMENT_DURATION_SECONDS
            command = [
                settings.FFMPEG_BINARY, '-y', '-i', str(source_path),
                '-vf', "scale='min(1280,iw)':-2",
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                '-c:a', 'aac', '-b:a', '128k',
                '-hls_time', str(segment_duration),
                '-hls_playlist_type', 'vod',
                '-hls_key_info_file', str(keyinfo_path),
                '-hls_segment_filename', str(output_dir / 'seg_%04d.ts'),
                str(output_dir / 'playlist.m3u8'),
            ]
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=settings.HLS_PACKAGING_TIMEOUT_SECONDS
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr[-2000:])

        segment_count = len(list(output_dir.glob('seg_*.ts')))

        package.status = HLSPackage.STATUS_READY
        package.output_dir = output_dir_rel
        package.segment_count = segment_count
        package.segment_duration_seconds = segment_duration
        package.encryption_key_hex = key_bytes.hex()
        package.encryption_iv_hex = iv_bytes.hex()
        package.save()
    except Exception as exc:
        package.status = HLSPackage.STATUS_FAILED
        package.error_message = str(exc)
        package.save(update_fields=['status', 'error_message'])
        raise

    return package


def build_secure_manifest(package, request, token):
    playlist_path = Path(settings.MEDIA_ROOT) / package.output_dir / 'playlist.m3u8'
    original = playlist_path.read_text()

    key_url = request.build_absolute_uri(reverse('secure-hls-key', args=[package.lesson_id])) + f'?token={token}'

    lines = []
    for line in original.splitlines():
        if line.startswith('#EXT-X-KEY'):
            line = re.sub(r'URI="[^"]*"', f'URI="{key_url}"', line)
        elif line and not line.startswith('#'):
            segment_name = line.strip()
            line = (
                request.build_absolute_uri(reverse('secure-hls-segment', args=[package.lesson_id, segment_name]))
                + f'?token={token}'
            )
        lines.append(line)

    return '\n'.join(lines)


def get_segment_path(package, segment_name):
    if not SEGMENT_NAME_PATTERN.match(segment_name):
        return None
    path = Path(settings.MEDIA_ROOT) / package.output_dir / segment_name
    return path if path.exists() else None
