import datetime
import functools
import json
import logging
import os
import google.auth
from flask import request, blueprints
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2, duration_pb2

tasks_blueprint = blueprints.Blueprint('tasks', __name__, url_prefix="/api/tasks")

_, project_id = google.auth.default()
service_account_email = f'{project_id}@appspot.gserviceaccount.com'

task_client = tasks_v2.CloudTasksClient()

RUN_TASKS_IMMEDIATELY = bool(os.getenv("RUN_TASKS_IMMEDIATELY", False))


def task(func=None, *, queue='main', location='europe-west2', in_seconds=None, dispatch_deadline=None):
    if func is None:
        return functools.partial(task, queue=queue, in_seconds=in_seconds, dispatch_deadline=dispatch_deadline)

    def push_queue_handler():
        if request.headers.get('X-Cloudtasks-Taskname') is None:
            raise Exception('Invalid Task, No X-Cloudtasks-Taskname request header found')

        request_data = request.get_data()
        request_data = request_data.decode()
        request_data = json.loads(request_data)

        func(*request_data["args"], **request_data["kwargs"])
        return "", 200

    tasks_blueprint.add_url_rule(
        f"/{func.__module__}/{func.__name__}",
        methods=["POST"],
        view_func=push_queue_handler,
        endpoint=f"task_{func.__module__}_{func.__name__}")

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        task_url = f"https://{request.host}{tasks_blueprint.url_prefix}/{func.__module__}/{func.__name__}"
        logging.info(f"{task_url=}")
        if bool(os.getenv("RUN_TASKS_IMMEDIATELY", False)):
            logging.info(f"running task immediately: {task_url}")
            func(*args, **kwargs)
        else:
            payload = {
                "args": args,
                "kwargs": kwargs
            }
            encoded_payload = json.dumps(payload).encode()

            parent = task_client.queue_path(project=project_id, location=location, queue=queue)
            data = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": task_url,
                    "body": encoded_payload,
                    "oidc_token": {"service_account_email": service_account_email},
                    # "headers": {"Content-type": "application/json"}
                }
            }

            if in_seconds is not None:
                # Convert "seconds from now" into an rfc3339 datetime string.
                d = datetime.datetime.utcnow() + datetime.timedelta(seconds=in_seconds)

                # Create Timestamp protobuf.
                timestamp = timestamp_pb2.Timestamp()
                timestamp.FromDatetime(d)

                # Add the timestamp to the tasks.
                data["schedule_time"] = timestamp

            if dispatch_deadline is not None:
                minimum = 15
                maximum = 1800
                clamped_deadline = max(minimum, min(dispatch_deadline, maximum))

                duration = duration_pb2.Duration()
                duration.FromSeconds(clamped_deadline)

                data["dispatch_deadline"] = duration

            response = task_client.create_task(request={"parent": parent, "task": data})
            logging.info("Created task {}".format(response.name))
            return response
    return wrapper


# X-CloudTasks-QueueName	The name of the queue.
# X-CloudTasks-TaskName	The "short" name of the task, or, if no name was specified at creation, a unique system-generated id. This is the my-task-id value in the complete task name, ie, task_name = projects/my-project-id/locations/my-location/queues/my-queue-id/tasks/my-task-id.
# X-CloudTasks-TaskRetryCount	The number of times this task has been retried. For the first attempt, this value is 0. This number includes attempts where the task failed due to a lack of available instances and never reached the execution phase.
# X-CloudTasks-TaskExecutionCount	The total number of times that the task has received a response from the handler. Since Cloud Tasks deletes the task once a successful response has been received, all previous handler responses were failures. This number does not include failures due to a lack of available instances.
# X-CloudTasks-TaskETA	The schedule time of the task, specified in seconds since January 1st 1970.
# In addition, requests from Cloud Tasks might contain the following headers:
#
# Header	Description
# X-CloudTasks-TaskPreviousResponse	The HTTP response code from the previous retry.
# X-CloudTasks-TaskRetryReason
