class FedleticException(Exception):

    def __init__(self, code: str, message: str = None):
        self.code = code
        self.message = message


class UsernameExists(FedleticException):
    def __init__(self):
        super().__init__(
            code="username_exists", message="This username is already taken."
        )


class EmailAlreadyInUse(FedleticException):
    def __init__(self):
        super().__init__(
            code="email_already_in_use", message="This email address is already in use."
        )
