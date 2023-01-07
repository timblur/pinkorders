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

    timeslot = timeslot.split(" - ")[0]
    for fmt in ["%d %b %Y_%H:%M", "%d %b %Y_%H%p", "%d %b %Y_%H:%M%p", "%Y-%m-%d_%H:%M"]:
        try:
            dt = datetime.datetime.strptime(f'{date}_{timeslot}', fmt)
        except ValueError:
            pass
        else:
            return dt.replace(tzinfo=datetime.timezone.utc)

    logging.error(f"Unable to phase due date: {date}_{timeslot}")
    return None


def _description_order_link(order, trello_shop):
    order_id = order.get("id")
    order_number = order.get("name")
    return f"Shopify order [{order_number}](https://{trello_shop.domain}/admin/orders/{order_id})"


def _description_address(order):
    try:
        address1 = order.get("shipping_address.address1")
        city = order.get("shipping_address.city")
        zip_code = order.get("shipping_address.zip")
        return ", ".join([address1, city, zip_code])
    except KeyError:
        return ""


def _description_notes(order):
    note = order.get("note")
    if not note:
        return ""

    return f"###Notes\n{note}"


def card_description(order, trello_shop):
    order_link = _description_order_link(order=order, trello_shop=trello_shop)
    address = _description_address(order=order)
    notes = _description_notes(order=order)
    return f"{order_link}\n{address}\n{notes}"


def location_details(query, order):
    try:
        lat = order.get("shipping_address.latitude")
        long = order.get("shipping_address.longitude")
        if lat and long:
            query['coordinates'] = f"{lat},{long}"

        address1 = order.get("shipping_address.address1")
        city = order.get("shipping_address.city")
        zip_code = order.get("shipping_address.zip")
        country_code = order.get("shipping_address.country_code")
        query['locationName'] = address1
        query['address'] = f"{address1}, {city}, {zip_code}, {country_code}"
    except KeyError:
        pass


def card_name(order, index):
    line_items = order.get("line_items")
    item = line_items[index]

    order_number = order.get("name")
    contact_email = order.get("contact_email")
    phone = order.get("phone")
    if not phone:
        phone = ""

    try:
        shipping_name = order.get("shipping_address.name")
    except KeyError:
        shipping_name = order.get("billing_address.name")
    billing_name = order.get("billing_address.name")
    name = shipping_name if shipping_name == billing_name else f"{shipping_name} ({billing_name})"

    quantity = item["quantity"]
    item_name = item["name"]

    properties = line_item_properties(line_item=item)
    delivery_type = ""
    delivery = properties.get("delivery")
    if delivery:
        delivery_type = f" · {delivery}"

    human_index = index + 1
    total_line_items = len(line_items)
    return f"{order_number} · {human_index}/{total_line_items} · {quantity} x {item_name} {delivery_type} · " \
           f"{name} {contact_email} {phone}"
