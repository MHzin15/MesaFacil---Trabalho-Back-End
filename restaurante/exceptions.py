from rest_framework.exceptions import APIException


class Conflict(APIException):
    status_code = 409
    default_detail = 'Os dados mudaram. Atualize a página e confira novamente.'
    default_code = 'conflict'
