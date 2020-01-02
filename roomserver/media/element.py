from typing import Optional

from .base import MediaBase
from .pipeline import MediaPipeline
from .session import KurentoSession


class MediaElement(MediaBase):
    element_id: Optional[str] = None

    def __init__(self, pipeline: MediaPipeline, session: KurentoSession):
        super().__init__(session)
        self.pipeline = pipeline
