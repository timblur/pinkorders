import json
import base64
import google.auth
from google.cloud import pubsub


_, project_id = google.auth.default()
publisher = pubsub.PublisherClient()


class PubSubInvalidTokenError(ValueError):
    pass


def publish_topic(topic, data, **attrs):
    topic_path = publisher.topic_path(project=project_id, topic=topic)
    data_bytes = json.dumps(data, ensure_ascii=False).encode('utf8')
    # When you publish a message, the client returns a future.
    future = publisher.publish(
        topic_path, data=data_bytes, **attrs
    )
    return future.result()


def decode_data(data):
    envelope = json.loads(data.decode('utf-8'))
    payload = json.loads(base64.b64decode(envelope['message']['data']))
    return envelope, payload
