# import requests
import tasks


@tasks.task(queue="shopify-webhook")
def process_shopify_webhook(webhook_id):
