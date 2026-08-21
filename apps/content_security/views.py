from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content_security.hls import build_secure_manifest, get_segment_path, package_lesson_video
from apps.content_security.models import AccessLog, HLSPackage, SuspiciousActivityEvent
from apps.content_security.serializers import SuspiciousActivityEventSerializer
from apps.content_security.services import (
    can_download_lesson,
    can_download_resource,
    generate_stream_token,
    is_origin_allowed,
    verify_stream_token,
)
from apps.content_security.watermark import watermark_image, watermark_pdf, watermark_text
from apps.core.constants import Roles
from apps.core.permissions import HasRole
from apps.progression.services import is_lesson_accessible

IsContentManager = HasRole.for_roles(Roles.TRAINER, Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN)


class SecureStreamTicketView(APIView):
    """Step 1 of secure delivery (§25.2): authenticate the learner via JWT as usual, then
    issue a short-lived signed URL for the actual media — never expose raw file paths."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lesson_id):
        from apps.courses.models import Enrollment, Lesson

        try:
            lesson = Lesson.objects.select_related('chapter').get(pk=lesson_id)
        except Lesson.DoesNotExist:
            raise Http404

        if not is_origin_allowed(request):
            return Response({'detail': 'Origine non autorisée.'}, status=403)

        if not lesson.is_preview_free:
            from apps.tenants.services import has_active_b2c_subscription, has_active_team_subscription
            if has_active_team_subscription(request.user, lesson.course) or has_active_b2c_subscription(request.user, lesson.course):
                Enrollment.objects.get_or_create(user=request.user, course=lesson.course)
            elif not Enrollment.objects.filter(user=request.user, course=lesson.course).exists():
                return Response({'detail': "Vous n'êtes pas inscrit à cette formation."}, status=403)

        if not is_lesson_accessible(request.user, lesson):
            return Response({'detail': 'Ce chapitre est verrouillé (progression séquentielle).'}, status=403)

        token = generate_stream_token(request.user, lesson)

        hls_package = getattr(lesson, 'hls_package', None)
        if hls_package and hls_package.status == HLSPackage.STATUS_READY:
            manifest_url = request.build_absolute_uri(reverse('secure-hls-manifest', args=[lesson.id])) + f'?token={token}'
            payload = {'streaming_mode': 'hls', 'manifest_url': manifest_url}
        else:
            stream_url = request.build_absolute_uri(reverse('secure-media-file', args=[lesson.id])) + f'?token={token}'
            payload = {'streaming_mode': 'progressive', 'stream_url': stream_url}

        payload.update({
            'expires_in': settings.LMSPRO_CONTENT_SECURITY['SIGNED_URL_TTL_SECONDS'],
            'download_allowed': can_download_lesson(lesson, request.user),
            'watermark_text': watermark_text(request.user),
        })
        return Response(payload)


class SecureMediaFileView(APIView):
    """Step 2: serves the actual bytes. Auth happens via the signed token (not JWT headers)
    so this URL can be handed to a <video>/<iframe> tag directly, with built-in expiry."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, lesson_id):
        from apps.accounts.models import User
        from apps.courses.models import Lesson

        if not is_origin_allowed(request):
            return Response({'detail': 'Origine non autorisée.'}, status=403)

        token = request.query_params.get('token', '')
        data = verify_stream_token(token)
        if not data or data['lesson_id'] != lesson_id:
            return Response({'detail': 'Lien expiré ou invalide.'}, status=403)

        lesson = Lesson.objects.get(pk=lesson_id)
        user = User.objects.get(pk=data['user_id'])
        file_field = lesson.video_file or lesson.document_file or lesson.scorm_package
        if not file_field:
            raise Http404

        AccessLog.objects.create(
            user=user, path=request.path, method='GET', ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500], status_code=200,
            object_type='lesson', object_id=str(lesson.id),
        )

        from apps.core.storage import generate_presigned_download, is_r2_backed

        wants_download = request.query_params.get('download') == '1'
        if wants_download and can_download_lesson(lesson, user):
            if lesson.content_type == Lesson.TYPE_PDF:
                buffer = watermark_pdf(file_field.open('rb'), user)
                return FileResponse(buffer, as_attachment=True, filename=f'{lesson.title}.pdf')
            if lesson.content_type == Lesson.TYPE_IMAGE:
                buffer = watermark_image(file_field.open('rb'), user)
                return FileResponse(buffer, as_attachment=True, filename=f'{lesson.title}.jpg')
            filename = file_field.name.split('/')[-1]
            if is_r2_backed(file_field):
                return HttpResponseRedirect(generate_presigned_download(file_field.name, download_filename=filename))
            return FileResponse(file_field.open('rb'), as_attachment=True, filename=filename)

        # Video/audio/documents on R2: redirect straight to a short-lived signed R2 URL
        # instead of streaming the bytes through Django — django-storages' S3 file
        # wrapper buffers the *entire* object on open(), so without this every seek in
        # a large video re-downloaded the whole file through the VPS just to serve one
        # byte range. R2 handles Range requests natively and much faster.
        if is_r2_backed(file_field):
            return HttpResponseRedirect(generate_presigned_download(file_field.name))
        return FileResponse(file_field.open('rb'))


class SecureResourceTicketView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, resource_id):
        from apps.courses.models import LessonResource

        try:
            resource = LessonResource.objects.select_related('lesson__chapter').get(pk=resource_id)
        except LessonResource.DoesNotExist:
            raise Http404

        lesson = resource.lesson
        if not is_lesson_accessible(request.user, lesson):
            return Response({'detail': 'Ce chapitre est verrouillé.'}, status=403)

        token = generate_stream_token(request.user, lesson)
        stream_url = (
            request.build_absolute_uri(reverse('secure-resource-file', args=[resource.id])) + f'?token={token}'
        )
        return Response({
            'stream_url': stream_url,
            'download_allowed': can_download_resource(resource, request.user),
            'watermark_text': watermark_text(request.user),
        })


class SecureResourceFileView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, resource_id):
        from apps.accounts.models import User
        from apps.courses.models import LessonResource

        if not is_origin_allowed(request):
            return Response({'detail': 'Origine non autorisée.'}, status=403)

        token = request.query_params.get('token', '')
        data = verify_stream_token(token)
        if not data:
            return Response({'detail': 'Lien expiré ou invalide.'}, status=403)

        resource = LessonResource.objects.get(pk=resource_id)
        user = User.objects.get(pk=data['user_id'])

        AccessLog.objects.create(
            user=user, path=request.path, method='GET', ip_address=request.META.get('REMOTE_ADDR'),
            object_type='lesson_resource', object_id=str(resource.id), status_code=200,
        )

        if request.query_params.get('download') == '1' and can_download_resource(resource, user):
            return FileResponse(resource.file.open('rb'), as_attachment=True, filename=resource.title)
        return FileResponse(resource.file.open('rb'))


class MyAccessLogView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.content_security.serializers import AccessLogSerializer

        logs = AccessLog.objects.filter(user=request.user)[:200]
        return Response(AccessLogSerializer(logs, many=True).data)


class PackageLessonHLSView(APIView):
    """Trainer/admin action: transcode a lesson's video into an AES-128 encrypted HLS
    package. Synchronous — runs ffmpeg and blocks until done or until it times out."""

    permission_classes = [IsContentManager]

    def post(self, request, lesson_id):
        from apps.courses.models import Lesson

        try:
            lesson = Lesson.objects.get(pk=lesson_id)
        except Lesson.DoesNotExist:
            raise Http404

        try:
            package = package_lesson_video(lesson)
        except Exception as exc:
            return Response({'detail': f'Échec du transcodage HLS: {exc}'}, status=500)

        from apps.content_security.serializers import HLSPackageSerializer

        return Response(HLSPackageSerializer(package).data, status=201)


class SecureHLSManifestView(APIView):
    """Serves a per-session HLS manifest with segment/key URIs rewritten to carry the
    caller's signed token, so the whole playback session stays time-limited and traceable."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, lesson_id):
        if not is_origin_allowed(request):
            return Response({'detail': 'Origine non autorisée.'}, status=403)

        token = request.query_params.get('token', '')
        data = verify_stream_token(token)
        if not data or data['lesson_id'] != lesson_id:
            return Response({'detail': 'Lien expiré ou invalide.'}, status=403)

        try:
            package = HLSPackage.objects.get(lesson_id=lesson_id, status=HLSPackage.STATUS_READY)
        except HLSPackage.DoesNotExist:
            raise Http404

        manifest = build_secure_manifest(package, request, token)
        return HttpResponse(manifest, content_type='application/vnd.apple.mpegurl')


class SecureHLSSegmentView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, lesson_id, segment_name):
        if not is_origin_allowed(request):
            return Response({'detail': 'Origine non autorisée.'}, status=403)

        token = request.query_params.get('token', '')
        data = verify_stream_token(token)
        if not data or data['lesson_id'] != lesson_id:
            return Response({'detail': 'Lien expiré ou invalide.'}, status=403)

        try:
            package = HLSPackage.objects.get(lesson_id=lesson_id, status=HLSPackage.STATUS_READY)
        except HLSPackage.DoesNotExist:
            raise Http404

        segment_path = get_segment_path(package, segment_name)
        if not segment_path:
            raise Http404

        return FileResponse(open(segment_path, 'rb'), content_type='video/mp2t')


class SecureHLSKeyView(APIView):
    """Releases the raw 16-byte AES-128 key — only ever to a holder of a still-valid
    signed token, never embedded directly in the manifest (cahier §25.2)."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, lesson_id):
        from apps.accounts.models import User

        if not is_origin_allowed(request):
            return Response({'detail': 'Origine non autorisée.'}, status=403)

        token = request.query_params.get('token', '')
        data = verify_stream_token(token)
        if not data or data['lesson_id'] != lesson_id:
            return Response({'detail': 'Lien expiré ou invalide.'}, status=403)

        try:
            package = HLSPackage.objects.get(lesson_id=lesson_id, status=HLSPackage.STATUS_READY)
        except HLSPackage.DoesNotExist:
            raise Http404

        user = User.objects.get(pk=data['user_id'])
        AccessLog.objects.create(
            user=user, path=request.path, method='GET', ip_address=request.META.get('REMOTE_ADDR'),
            object_type='hls_key', object_id=str(lesson_id), status_code=200,
        )

        key_bytes = bytes.fromhex(package.encryption_key_hex)
        return HttpResponse(key_bytes, content_type='application/octet-stream')


class ReportSuspiciousActivityView(APIView):
    """§25.5 — receives signals the frontend/mobile app detected (devtools open,
    right-click blocked, tab blur during an exam, screen-recording API triggered...).
    No website can truly prevent screenshots or an external camera recording the screen
    — the cahier des charges says so itself — so the realistic goal here is dissuasion
    and traceability, which is exactly what this endpoint provides."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SuspiciousActivityEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save(
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        return Response(SuspiciousActivityEventSerializer(event).data, status=201)


class SuspiciousActivityEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SuspiciousActivityEventSerializer
    permission_classes = [HasRole.for_roles(Roles.COMPANY_ADMIN, Roles.HR)]
    filterset_fields = ['event_type', 'user', 'lesson']

    def get_queryset(self):
        user = self.request.user
        qs = SuspiciousActivityEvent.objects.select_related('user', 'lesson')
        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            return qs
        return qs.filter(user__company_id=user.company_id)
