import logging

from roomserver.media.element import MediaElement
from roomserver.media.pipeline import MediaPipeline
from roomserver.media.session import KurentoSession

logger = logging.getLogger(__name__)


class WebRTCEndPoint(MediaElement):
    def __init__(self, pipeline: MediaPipeline, session: KurentoSession):
        super().__init__(pipeline, session)

    async def create(self):
        try:
            a_response = await self.session.send_request(method="create", params={
                "type": "WebRtcEndpoint",
                "constructorParams": {
                    "mediaPipeline": self.pipeline.pipeline_id
                },
                "properties": {},
            })
            result = await a_response
        except Exception:
            logger.exception('COMMAND: ')
            return
        else:
            pipeline_id, element_id = result['value'].split('/')
            assert self.pipeline.pipeline_id == pipeline_id
            self.element_id = element_id
            logger.info("WebRtcEndpoint created: %s", self.element_id)
