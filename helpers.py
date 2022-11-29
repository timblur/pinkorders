import datetime


def _address_line(doc, attr):
    try:
        value = doc.get(f"shipping_address.{attr}")
    except KeyError:
        value = ""
    if value:
        return f"{value}\n"
    return ""


def _description_address(doc):
    name = _address_line(doc=doc, attr="name")
    address1 = _address_line(doc=doc, attr="address1")
    address2 = _address_line(doc=doc, attr="address2")
    city = _address_line(doc=doc, attr="city")
    zip_code = _address_line(doc=doc, attr="zip")

    address = f"{name}{address1}{address2}{city}{zip_code}"

    if not address:
        return ""

    return f"###Address\n{address}"


def _description_order_link(doc, trello_shop):
    order_id = doc.get("id")
    order_number = doc.get("name")
    return f"###Shopify order\n[{order_number}](https://{trello_shop.domain}/admin/orders/{order_id})"


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

    return datetime.datetime.strptime(f'{date}_{timeslot}', "%Y-%m-%d_%H:%M").replace(tzinfo=datetime.timezone.utc)


def card_description(doc, trello_shop):
    order_link = _description_order_link(doc=doc, trello_shop=trello_shop)
    address = _description_address(doc=doc)

    return f"{order_link}\n{address}"


def card_name(doc):
    order_number = doc.get("name")
    contact_email = doc.get("contact_email")
    phone = doc.get("phone")
    if not phone:
        phone = ""
    billing_name = doc.get("billing_address.name")
    shipping_name = doc.get("shipping_address.name")
    name = shipping_name if shipping_name == billing_name else f"{shipping_name} ({billing_name})"

    return f"{order_number} {name} {contact_email} {phone}"
