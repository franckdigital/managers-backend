from rest_framework.views import exception_handler


def lmspro_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    response.data = {
        'success': False,
        'status_code': response.status_code,
        'errors': detail,
    }
    return response
