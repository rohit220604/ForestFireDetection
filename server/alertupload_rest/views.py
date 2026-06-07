from alertupload_rest.serializers import UploadAlertSerializer
from rest_framework.decorators import api_view
from django.http import JsonResponse
from threading import Thread
from django.core.mail import send_mail, get_connection
import re
import logging
import requests
from django.conf import settings

MAIL_TIMEOUT_SECONDS = max(int(getattr(settings, 'EMAIL_TIMEOUT', 30)), 1)
PROVIDER_ERROR_PREVIEW_CHARS = 300
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

def _mail_provider():
    return str(getattr(settings, 'EMAIL_PROVIDER', 'smtp') or 'smtp').strip().lower()


def _smtp_configured():
    return bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)

def _mail_provider_configured():
    provider = _mail_provider()
    if provider == 'smtp':
        return _smtp_configured()
    if provider == 'resend':
        return bool(str(getattr(settings, 'RESEND_API_KEY', '')).strip())
    if provider == 'sendgrid':
        return bool(str(getattr(settings, 'SENDGRID_API_KEY', '')).strip())
    return False


def _missing_mail_configuration_message():
    provider = _mail_provider()
    if provider == 'smtp':
        return (
            'SMTP not configured on server. In Render Environment set '
            'EMAIL_HOST_USER (your Gmail) and EMAIL_HOST_PASSWORD (Gmail app password).'
        )
    if provider == 'resend':
        return (
            'Resend not configured on server. Set EMAIL_PROVIDER=resend, '
            'RESEND_API_KEY, and DEFAULT_FROM_EMAIL (verified sender).'
        )
    if provider == 'sendgrid':
        return (
            'SendGrid not configured on server. Set EMAIL_PROVIDER=sendgrid, '
            'SENDGRID_API_KEY, and DEFAULT_FROM_EMAIL (verified sender).'
        )
    return (
        f'Unsupported EMAIL_PROVIDER "{provider}". '
        'Use one of: smtp, resend, sendgrid.'
    )


def _provider_error_detail(response):
    try:
        payload = response.json()
        if isinstance(payload, dict):
            text = payload.get('message') or payload.get('error') or str(payload)
        else:
            text = str(payload)
    except ValueError:
        text = response.text
    return str(text)[:PROVIDER_ERROR_PREVIEW_CHARS]


def _send_mail_via_resend(subject, message, recipient, sender):
    endpoint = str(
        getattr(settings, 'RESEND_API_URL', 'https://api.resend.com/emails')
    ).strip()
    api_key = str(getattr(settings, 'RESEND_API_KEY', '')).strip()
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'from': sender,
        'to': [recipient],
        'subject': subject,
        'text': message,
    }
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=MAIL_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f'Resend API request failed: {exc}') from exc

    if response.status_code >= 400:
        detail = _provider_error_detail(response)
        raise RuntimeError(
            f'Resend API rejected email ({response.status_code}): {detail}'
        )

    return 1


def _send_mail_via_sendgrid(subject, message, recipient, sender):
    endpoint = str(
        getattr(settings, 'SENDGRID_API_URL', 'https://api.sendgrid.com/v3/mail/send')
    ).strip()
    api_key = str(getattr(settings, 'SENDGRID_API_KEY', '')).strip()
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'personalizations': [{'to': [{'email': recipient}]}],
        'from': {'email': sender},
        'subject': subject,
        'content': [{'type': 'text/plain', 'value': message}],
    }
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=MAIL_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f'SendGrid API request failed: {exc}') from exc

    if response.status_code not in (200, 202):
        detail = _provider_error_detail(response)
        raise RuntimeError(
            f'SendGrid API rejected email ({response.status_code}): {detail}'
        )

    return 1


def _send_mail(subject, message, recipient):
    if not _mail_provider_configured():
        raise RuntimeError(_missing_mail_configuration_message())

    sender = str(_from_email()).strip()
    if not EMAIL_PATTERN.match(sender):
        raise RuntimeError(
            'DEFAULT_FROM_EMAIL is invalid. Set it to a valid sender email address.'
        )

    provider = _mail_provider()
    if provider == 'resend':
        return _send_mail_via_resend(subject, message, recipient, sender)
    if provider == 'sendgrid':
        return _send_mail_via_sendgrid(subject, message, recipient, sender)
    if provider != 'smtp':
        raise RuntimeError(
            f'Unsupported EMAIL_PROVIDER "{provider}". Use smtp, resend, sendgrid.'
        )

    connection = get_connection(timeout=MAIL_TIMEOUT_SECONDS)
    sent_count = send_mail(
        subject,
        message,
        sender,
        [recipient],
        fail_silently=False,
        connection=connection,
    )
    if sent_count != 1:
        raise RuntimeError(
            f'SMTP server did not accept the email for {recipient}.'
        )

    return sent_count


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

    if not _mail_provider_configured():
        return JsonResponse(
            {
                'success': False,
                'email_sent': False,
                'error': _missing_mail_configuration_message(),
                'recipient': alert_receiver,
            },
            status=500,
        )

    try:
        _send_mail(
            'Forest Fire Monitoring Started — FireGuard',
            (
                f'Detection has been started at: {location}\n\n'
                'You will receive another email if a possible forest fire is detected.'
            ),
            alert_receiver,
        )
    except Exception as exc:
        logger.error(
            'Failed to send detection started email to %s — %s: %s',
            alert_receiver,
            type(exc).__name__,
            exc,
        )
        return JsonResponse(
            {
                'success': False,
                'email_sent': False,
                'error': (
                    'Unable to send email notification. '
                    f'{type(exc).__name__}: {exc}'
                ),
                'recipient': alert_receiver,
            },
            status=502,
        )

    logger.info('Detection started email sent to %s', alert_receiver)
    return JsonResponse({
        'success': True,
        'email_sent': True,
        'recipient': alert_receiver,
        'message': f'Notification email sent to {alert_receiver}.',
    })


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
    except Exception as exc:
        logger.error(
            'Failed to send fire alert email to %s — %s: %s',
            recipient,
            type(exc).__name__,
            exc,
        )


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
