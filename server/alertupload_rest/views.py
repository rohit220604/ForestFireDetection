from alertupload_rest.serializers import UploadAlertSerializer
from rest_framework.decorators import api_view
from django.http import JsonResponse
from threading import Thread
from django.core.mail import send_mail, get_connection
import re
import logging
from django.conf import settings

SMTP_TIMEOUT_SECONDS = 15
logger = logging.getLogger(__name__)
EMAIL_PATTERN = re.compile(r'^[^@]+@[^@]+\.[^@]+$')


def start_new_thread(function):
    def decorator(*args, **kwargs):
        t = Thread(target=function, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()
    return decorator


def _from_email():
    return settings.DEFAULT_FROM_EMAIL


def _smtp_configured():
    return bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def _send_mail(subject, message, recipient):
    if not _smtp_configured():
        raise RuntimeError(
            'SMTP not configured on server. In Render Environment set '
            'EMAIL_HOST_USER (your Gmail) and EMAIL_HOST_PASSWORD (Gmail app password).'
        )

    connection = get_connection(
        backend=settings.EMAIL_BACKEND,
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        timeout=SMTP_TIMEOUT_SECONDS,
    )
    send_mail(
        subject,
        message,
        _from_email(),
        [recipient],
        fail_silently=False,
        connection=connection,
    )


@api_view(['POST'])
def post_alert(request):
    serializer = UploadAlertSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        identify_email(data=serializer.data)
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'error': 'Unable to process data'}, status=400)


def identify_email(data):
    alert_receiver = data.get('alert_receiver', '')
    if EMAIL_PATTERN.match(alert_receiver):
        send_fire_alert_email_async(data)
    else:
        logger.warning('Invalid alert_receiver email: %s', alert_receiver)


@api_view(['POST'])
def post_detection_started(request):
    location = request.data.get('location', '').strip()
    alert_receiver = request.data.get('alert_receiver', '').strip()

    if not location or not alert_receiver:
        return JsonResponse(
            {'error': 'location and alert_receiver are required'},
            status=400,
        )

    if not EMAIL_PATTERN.match(alert_receiver):
        return JsonResponse({'error': 'Invalid email address'}, status=400)

    if not _smtp_configured():
        return JsonResponse(
            {
                'success': False,
                'email_queued': False,
                'error': (
                    'SMTP not configured on server. Add EMAIL_HOST_USER and '
                    'EMAIL_HOST_PASSWORD in Render Environment, then redeploy.'
                ),
                'recipient': alert_receiver,
            },
            status=500,
        )

    send_detection_started_email_async(location, alert_receiver)
    return JsonResponse({
        'success': True,
        'email_queued': True,
        'recipient': alert_receiver,
        'message': f'Notification email is being sent to {alert_receiver}.',
    })


@start_new_thread
def send_detection_started_email_async(location, alert_receiver):
    try:
        _send_mail(
            'Forest Fire Monitoring Started — FireGuard',
            (
                f'Detection has been started at: {location}\n\n'
                'You will receive another email if a possible forest fire is detected.'
            ),
            alert_receiver,
        )
        logger.info('Detection started email sent to %s', alert_receiver)
    except Exception:
        logger.exception('Failed to send detection started email to %s', alert_receiver)


@start_new_thread
def send_fire_alert_email_async(data):
    recipient = data['alert_receiver']
    try:
        _send_mail(
            'Forest Fire Detected — FireGuard Alert',
            prepare_alert_message(data),
            recipient,
        )
        logger.info('Fire alert email sent to %s', recipient)
    except Exception:
        logger.exception('Failed to send fire alert email to %s', recipient)


def prepare_alert_message(data):
    image_val = data.get('image', '')
    image_data = split(image_val, ".")
    if len(image_data) > 3:
        uuid = split(image_data[3], '/')
        if len(uuid) > 2:
            url = 'https://forestfiredetection-y938.onrender.com/alert' + uuid[2]
        else:
            url = 'https://forestfiredetection-y938.onrender.com/alert'
    else:
        url = 'https://forestfiredetection-y938.onrender.com/alert'
    return (
        'A possible forest fire was detected. View the alert frame and details at '
        + url
    )


def split(value, key):
    return str(value).split(key)
