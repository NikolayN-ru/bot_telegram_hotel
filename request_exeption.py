class ResponseError(BaseException):
    def __str__(self):
        return 'Что-то пошло не так'