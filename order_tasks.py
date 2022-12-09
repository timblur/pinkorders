import requests
import logging
import json
import tasks
import os
import helpers
from google.cloud import firestore
from dataclasses import dataclass


db = firestore.Client()


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
    webhook_attributes = doc.get("webhook_attributes")
    topic = webhook_attributes['X-Shopify-Topic']
    if topic == "orders/create":
        create_card(webhook_id=webhook_id)


@tasks.task(queue="trello")
def create_card(webhook_id):
    doc_ref = db.collection("shopifyWebhook").document(webhook_id)
    doc = doc_ref.get()
    webhook_attributes = doc.get("webhook_attributes")
    shop_domain = webhook_attributes['X-Shopify-Shop-Domain']
    trello_shop = get_shop(shop_domain=shop_domain)

    url = "https://api.trello.com/1/cards"
    headers = {
        "Accept": "application/json"
    }

    query = {
        'name': helpers.card_name(doc=doc),
        'desc': helpers.card_description(doc=doc, trello_shop=trello_shop),
        'idList': trello_shop.todo_list,
        'pos': 'top',
        'key': os.environ['TRELLO_API_KEY'],
        'token': os.environ['TRELLO_API_SECRET']
    }

    try:
        # lat = doc.get("shipping_address.latitude")
        # long = doc.get("shipping_address.longitude")
        address1 = doc.get("shipping_address.address1")
        city = doc.get("shipping_address.city")
        zip_code = doc.get("shipping_address.zip")
        country_code = doc.get("shipping_address.country_code")
        # query['coordinates'] = f"{lat},{long}"
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

    card = response.json()
    save_card(card_id=card["id"], webhook_id=webhook_id)


@tasks.task(queue="trello")
def save_card(card_id, webhook_id):
    order = db.collection("shopifyWebhook").document(webhook_id).get()
    order_number = order.get("order_number")
    db.collection("trelloCard").document(str(order_number)).set({
        "card_id": card_id,
        "order_number": order_number,
        "order_id": order.get("id")
    })

    url = f"https://api.trello.com/1/cards/{card_id}/checklists"

    query = {
        'name': "Items",
        'pos': 'top',
        'key': os.environ['TRELLO_API_KEY'],
        'token': os.environ['TRELLO_API_SECRET']
    }

    response = requests.request(
        "POST",
        url,
        params=query
    )

    checklist = response.json()
    add_checklist_items(checklist_id=checklist["id"], webhook_id=webhook_id)


@tasks.task(queue="trello")
def add_checklist_items(checklist_id, webhook_id, index=0):
    order = db.collection("shopifyWebhook").document(webhook_id).get()
    line_items = order.get("line_items")
    item = line_items[index]

    url = f"https://api.trello.com/1/checklists/{checklist_id}/checkItems"

    quantity = item["quantity"]
    name = item["name"]

    properties = helpers.line_item_properties(line_item=item)
    delivery_type = ""
    delivery = properties.get("delivery")
    if delivery:
        delivery_type = f"({delivery})"

    logging.info(name)

    query = {
        'name': f'{quantity}x {name}{delivery_type}',
        'pos': 'bottom',
        'key': os.environ['TRELLO_API_KEY'],
        'token': os.environ['TRELLO_API_SECRET']
    }

    due = helpers.datetime_from_properties(line_item=item)
    if due:
        query['due'] = due.isoformat().replace("+00:00", "Z")

    response = requests.request(
        "POST",
        url,
        params=query
    )

    logging.info(response.json())

    if index != len(line_items) - 1:
        add_checklist_items(checklist_id, webhook_id, index+1)
