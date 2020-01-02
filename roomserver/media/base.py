from .session import KurentoSession


class MediaBase:
    def __init__(self, session: KurentoSession):
        self.session = session
