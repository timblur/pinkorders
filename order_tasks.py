import requests
import json
import tasks
import os
import helpers
from google.cloud import firestore
from dataclasses import dataclass


db = firestore.Client()

test_todo_list = "638135460ac202010129917d"
test_shop = "pink-test-store.myshopify.com"


@dataclass
class TrelloShop:
    """Class for keeping track of an item in inventory."""
    todo_list: str
    domain: str


def get_shop(shop_domain):
    shops = [
        TrelloShop(
            todo_list="638135460ac202010129917d",
            domain="pink-test-store.myshopify.com",
        ),
    ]

    for s in shops:
        if s.domain == shop_domain:
            return s
    raise ValueError("No matching shop")


@tasks.task(queue="shopify-webhook")
def process_shopify_webhook(webhook_id):
    doc_ref = db.collection("shopifyWebhook").document(webhook_id)
    doc = doc_ref.get()

    if doc.get("webhook_attributes.X-Shopify-Topic") == "orders/create":
        create_card(webhook_id=webhook_id)


@tasks.task(queue="trello")
def create_card(webhook_id):
    doc_ref = db.collection("shopifyWebhook").document(webhook_id)
    doc = doc_ref.get()
    shop_domain = doc.get("webhook_attributes.X-Shopify-Shop-Domain")
    trello_shop = get_shop(shop_domain=shop_domain)

    url = "https://api.trello.com/1/cards"
    headers = {
        "Accept": "application/json"
    }

    query = {
        'name': helpers.card_name(doc=doc),
        'description': helpers.card_description(doc=doc, trello_shop=trello_shop),
        'idList': trello_shop.todo_list,
        'key': os.environ['TRELLO_API_KEY'],
        'token': os.environ['TRELLO_API_SECRET']
    }

    try:
        address1 = doc.get("shipping_address.address1")
        city = doc.get("shipping_address.city")
        zip_code = doc.get("shipping_address.zip")
        country_code = doc.get("shipping_address.country_code")
        query['locationName'] = address1
        query['address'] = f"{address1}, {city}, {zip_code}, {country_code}"
    except KeyError:
        pass

    response = requests.request(
        "POST",
        url,
        headers=headers,
        params=query
    )

    print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))