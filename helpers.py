import datetime
import logging


def line_item_properties(line_item):
    return {prop['name']: prop['value'] for prop in line_item['properties']}


def datetime_from_properties(line_item):
    properties = line_item_properties(line_item=line_item)
    timeslot = properties.get("timeslot")
    if not timeslot:
        timeslot = "09:00"
    date = properties.get("date")
    if not date:
        return None

    for fmt in ["%d %b %Y_%H:%M", "%d %b %Y_%H%p", "%Y-%m-%d_%H:%M"]:
        try:
            dt = datetime.datetime.strptime(f'{date}_{timeslot}', fmt)
        except ValueError:
            pass
        else:
            return dt.replace(tzinfo=datetime.timezone.utc)

    logging.error(f"Unable to phase due date: {date}_{timeslot}")

    return None


def _description_order_link(doc, trello_shop):
    order_id = doc.get("id")
    order_number = doc.get("name")
    return f"Shopify order [{order_number}](https://{trello_shop.domain}/admin/orders/{order_id})"


def _description_address(doc):
    address1 = doc.get("shipping_address.address1")
    city = doc.get("shipping_address.city")
    zip_code = doc.get("shipping_address.zip")
    return ", ".join([address1, city, zip_code])


def _description_notes(doc):
    note = doc.get("note")
    if not note:
        return ""

    return f"###Notes\n{note}"


def card_description(doc, trello_shop):
    order_link = _description_order_link(doc=doc, trello_shop=trello_shop)
    address = _description_address(doc=doc)
    notes = _description_notes(doc=doc)
    return f"{order_link}\n{address}\n{notes}"


def card_name(doc):
    order_number = doc.get("name")
    contact_email = doc.get("contact_email")
    phone = doc.get("phone")
    if not phone:
        phone = ""
    shipping_name = doc.get("shipping_address.name")
    billing_name = doc.get("billing_address.name")
    name = shipping_name if shipping_name == billing_name else f"{shipping_name} ({billing_name})"

    return f"{order_number} {name} {contact_email} {phone}"
