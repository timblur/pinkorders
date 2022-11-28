

def _address_line(doc, attr):
    try:
        value = doc.get(f"shipping_address.{attr}")
    except KeyError:
        return ""
    return f"{value}\n"


def _description_address(doc):
    name = _address_line(doc=doc, attr="name")
    address1 = _address_line(doc=doc, attr="address1")
    address2 = _address_line(doc=doc, attr="address2")
    city = _address_line(doc=doc, attr="city")
    zip_code = _address_line(doc=doc, attr="zip")

    address = f"{name}{address1}{address2}{city}{zip_code}"

    if not address:
        return ""

    return f"""Address
    ---
    
    {address}
    """


def _description_order_link(doc, trello_shop):
    order_id = doc.get("id")
    order_number = doc.get("name")
    return f"[{order_number}] (https://{trello_shop.domain}/admin/orders/{order_id})"


def _description_items(doc):
    items = []
    for item in doc.get("line_items"):
        items.append(
            f"{item.name}"
        )

    items = "\n".join(items)

    return f"""Items
        ---

        {items}
        """


def card_description(doc, trello_shop):
    order_link = _description_order_link(doc=doc, trello_shop=trello_shop)
    address = _description_address(doc=doc)
    items = _description_items(doc=doc)

    return f"""
        {order_link}
        {items}
        {address}
    """


def card_name(doc):
    order_number = ""
    contact_email = doc.get("contact_email")
    phone = doc.get("phone")
    if not phone:
        phone = ""
    billing_name = doc.get("billing_address.name")
    shipping_name = doc.get("shipping_address.name")
    name = shipping_name if shipping_name == billing_name else f"{shipping_name} ({billing_name})"

    return f"{order_number} {name} {contact_email} {phone}"
