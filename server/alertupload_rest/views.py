from alertupload_rest.serializers import UploadAlertSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.http import JsonResponse
from threading import Thread
from django.core.mail import send_mail
import re
from django.conf import settings

def start_new_thread(function):
    def decorator(*args, **kwargs):
        t = Thread(target=function, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()
    return decorator

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
    # Regex pattern for email only
    email_pattern = re.compile(r'^[^@]+@[^@]+\.[^@]+$')

    if email_pattern.match(alert_receiver):
        print("Valid Email")
        send_email(data)
    else:
        print("Invalid Email")

@start_new_thread
def send_email(data):
    send_mail(
        'Forest Fire Detected — FireGuard Alert',
        prepare_alert_message(data),
        'rjrohit2264@gmail.com',
        [data['alert_receiver']],
        fail_silently=True,
    )

def prepare_alert_message(data):
    image_val = data.get('image', '')
    image_data = split(image_val, ".")
    if len(image_data) > 3:
        uuid = split(image_data[3], '/')
        if len(uuid) > 2:
            url = 'https://surveilix.onrender.com/alert' + uuid[2]
        else:
            url = 'https://surveilix.onrender.com/alert'
    else:
        url = 'https://surveilix.onrender.com/alert'
    return 'A possible forest fire was detected. View the alert frame and details at ' + url

def split(value, key):
    return str(value).split(key)
