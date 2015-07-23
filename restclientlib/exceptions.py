class ClientException(Exception):
    def __init__(self, code, reason, body):
        super(ClientException, self).__init__()
        self.code = code
        self.reason = reason
        self.body = body

    def __str__(self):
        return ('Client is broken down with code {} ({})'
                .format(self.code,
                        self.reason))
