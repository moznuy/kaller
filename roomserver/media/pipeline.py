import logging
from typing import Optional

from .base import MediaBase
from .session import KurentoSession

logger = logging.getLogger(__name__)


class MediaPipeline(MediaBase):
    pipeline_id: Optional[str] = None

    def __init__(self, session: KurentoSession):
        super().__init__(session)

    async def create(self):
        try:
            a_response = await self.session.send_request(method="create", params={
                "type": "MediaPipeline",
                "constructorParams": {},
                "properties": {}
            })
            result = await a_response
        except Exception:
            logger.exception('COMMAND: ')
            return
        else:
            self.pipeline_id = result['value']
            logger.info("MediaPipeline created: %s", self.pipeline_id)

