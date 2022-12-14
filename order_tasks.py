import requests
import tasks
import os
import helpers
import logging
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
            todo_list="63812e1e7a005401ad39232c",
            domain="pinkcakeshop.myshopify.com",
        ),
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
    order = doc_ref.get()
    webhook_attributes = order.get("webhook_attributes")
    topic = webhook_attributes['X-Shopify-Topic']
    if topic == "orders/create":
        create_card(webhook_id=webhook_id)


@tasks.task(queue="trello")
def create_card(webhook_id, index=0):
    doc_ref = db.collection("shopifyWebhook").document(webhook_id)
    order = doc_ref.get()
    line_items = order.get("line_items")
    total_line_items = len(line_items)
    item = line_items[index]
    webhook_attributes = order.get("webhook_attributes")
    shop_domain = webhook_attributes['X-Shopify-Shop-Domain']
    trello_shop = get_shop(shop_domain=shop_domain)

    url = "https://api.trello.com/1/cards"
    headers = {
        "Accept": "application/json"
    }

    query = {
        'name': helpers.card_name(order=order, index=index),
        'desc': helpers.card_description(order=order, trello_shop=trello_shop),
        'idList': trello_shop.todo_list,
        'pos': 'top',
        'key': os.environ['TRELLO_API_KEY'],
        'token': os.environ['TRELLO_API_SECRET']
    }

    due = helpers.datetime_from_properties(line_item=item)
    if due:
        query['due'] = due.isoformat().replace("+00:00", "Z")

    helpers.location_details(query=query, order=order)

    response = requests.request(
        "POST",
        url,
        headers=headers,
        params=query
    )
    logging.info(response.json())
    response.raise_for_status()
    card = response.json()
    save_card(card_id=card["id"], webhook_id=webhook_id)

    if index != total_line_items - 1:
        create_card(webhook_id, index+1)


@tasks.task(queue="trello")
def save_card(card_id, webhook_id):
    order = db.collection("shopifyWebhook").document(webhook_id).get()
    order_number = order.get("order_number")
    db.collection("trelloCard").document(str(order_number)).set({
        "card_id": card_id,
        "order_number": order_number,
        "order_id": order.get("id")
    })
