import google.cloud.logging
import os
from flask import Flask
from subscriptions import subscription
from tasks import tasks_blueprint


# logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
#                     datefmt='%Y-%m-%d:%H:%M:%S',
#                     level=logging.INFO)

logging_client = google.cloud.logging.Client()
logging_client.setup_logging()

app = Flask(__name__)

app.register_blueprint(subscription)
app.register_blueprint(tasks_blueprint)

if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(debug=False, port=server_port, host='0.0.0.0')
