import json
import time
from django.core.mail import EmailMessage
import requests
from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string

np_token = settings.NP_TOKEN
CITY = settings.CITY_NAME
WAREHOUSE = settings.WAREHOUSE_NAME

from django.core.cache import cache


@shared_task
def get_sender_address_ref_on_startup():
    # Fetch sender ref
    sender = {
        "apiKey": np_token,
        "modelName": "Counterparty",
        "calledMethod": "getCounterparties",
        "methodProperties": {
            "CounterpartyProperty": "Sender",
            "Page": "1"
        }
    }
    response_sender = requests.post('https://api.novaposhta.ua/v2.0/json/', json=sender)
    content_sender = response_sender.content
    sender_full = json.loads(content_sender)
    sender_ref = sender_full['data'][0]['Ref']
    key_sender = "sender_ref"
    cache.set(key_sender, sender_ref)

    # fetch other info

    info = {
        "apiKey": np_token,
        "modelName": "Counterparty",
        "calledMethod": "getCounterpartyAddresses",
        "methodProperties": {
            "Ref": sender_ref,
            "CounterpartyProperty": "Sender"
        }
    }
    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=info)
    content = json.loads(response.content)
    sender_address_ref = content["data"][0]["Ref"]
    # Save the data to the cache

    info = {
        "apiKey": np_token,
        "modelName": "Address",
        "calledMethod": "getWarehouses",
        "methodProperties": {
            "CityName": CITY,
            "FindByString": WAREHOUSE,
        }
    }
    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=info)
    content = response.content
    address_full = json.loads(content)
    wh_address_ref = address_full['data'][0]['Ref']
    city_ref = address_full['data'][0]['CityRef']
    print(f"{city_ref=}")
    warehouse_index = address_full['data'][0]['WarehouseIndex']
    key_address = "sender_address_ref"  # Key to store the data
    key_city = "city_ref"
    key_wh_index = "wh_index"
    key_wh_address = "wh_address"

    cache.set(key_address, sender_address_ref)
    cache.set(key_wh_address, wh_address_ref)
    cache.set(key_city, city_ref)
    cache.set(key_wh_index, warehouse_index)
    print(f"{sender_ref=}, {sender_address_ref=}")

    return wh_address_ref, warehouse_index, city_ref


@shared_task
def update_sender_ref_monthly():
    sender = {
        "apiKey": np_token,
        "modelName": "Counterparty",
        "calledMethod": "getCounterparties",
        "methodProperties": {
            "CounterpartyProperty": "Sender",
            "Page": "1"
        }
    }
    response_sender = requests.post('https://api.novaposhta.ua/v2.0/json/', json=sender)
    content_sender = response_sender.content
    sender_full = json.loads(content_sender)
    sender_ref = sender_full['data'][0]['Ref']
    key_sender = "sender_ref"
    cache.set(key_sender, sender_ref)


@shared_task
def update_warehouse_and_city_daily():
    sender_ref = cache.get("sender_ref")
    info = {
        "apiKey": np_token,
        "modelName": "Counterparty",
        "calledMethod": "getCounterpartyAddresses",
        "methodProperties": {
            "Ref": sender_ref,
            "CounterpartyProperty": "Sender"
        }
    }
    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=info)
    content = json.loads(response.content)
    sender_address_ref = content["data"][0]["Ref"]
    # Save the data to the cache

    info = {
        "apiKey": np_token,
        "modelName": "Address",
        "calledMethod": "getWarehouses",
        "methodProperties": {
            "CityName": CITY,
            "FindByString": WAREHOUSE,
        }
    }
    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=info)
    content = response.content
    address_full = json.loads(content)
    address_ref = address_full['data'][0]['Ref']
    city_ref = address_full['data'][0]['CityRef']
    warehouse_index = address_full['data'][0]['WarehouseIndex']
    key_address = "sender_address_ref"
    key_city = "city_ref"
    key_wh_index = "wh_index"

    cache.set(key_address, sender_address_ref)
    cache.set(key_city, city_ref)
    cache.set(key_wh_index, warehouse_index)

    return address_ref, warehouse_index, city_ref

@shared_task
def get_warehouse_by_string(city_name, warehouse_str):
    info = {
        "apiKey": np_token,
        "modelName": "Address",
        "calledMethod": "getWarehouses",
        "methodProperties": {
            "CityName": city_name,
            "FindByString": warehouse_str,
        }
    }
    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=info)

    content = response.content
    address_full = json.loads(content)
    address_ref = address_full['data'][0]['Ref']
    city_ref = address_full['data'][0]['CityRef']

    warehouse_index = address_full['data'][0]['WarehouseIndex']
    return address_ref, warehouse_index, city_ref


def get_sender_address(sender_ref):
    info = {
        "apiKey": np_token,
        "modelName": "Counterparty",
        "calledMethod": "getCounterpartyAddresses",
        "methodProperties": {
            "Ref": sender_ref,
            "CounterpartyProperty": "Sender"
        }
    }
    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=info)
    content = response.content
    address_full = json.loads(content)
    address_ref = address_full['data'][0]['Ref']
    return address_ref


def get_phone_full_ref(countr_ref):
    # Retrieve sender contact information from Nova Poshta
    countr_contact_pers = {
        "apiKey": np_token,
        "modelName": "Counterparty",
        "calledMethod": "getCounterpartyContactPersons",
        "methodProperties": {
            "Ref": countr_ref,
            "Page": "1"
        }
    }
    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=countr_contact_pers)
    content = response.content
    countr_cont_full = json.loads(content)
    countr_cont_full_ref = countr_cont_full['data'][0]['Ref']
    countr_cont_full_phones = countr_cont_full['data'][0]['Phones']
    return countr_cont_full_ref, countr_cont_full_phones


def get_rec_info(name, middlename, lastname, phonenum):
    # Create a new recipient in Nova Poshta
    create_recepient = {
        "apiKey": np_token,
        "modelName": "Counterparty",
        "calledMethod": "save",
        "methodProperties": {
            "FirstName": name,
            "MiddleName": lastname,
            "LastName": middlename,
            "Phone": phonenum,
            "Email": "",
            "CounterpartyType": "PrivatePerson",
            "CounterpartyProperty": "Recipient"
        }
    }

    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=create_recepient)
    content = response.content
    new_recepient_full = json.loads(content)
    new_recepient_full_ref = new_recepient_full['data'][0]['Ref']
    new_recepient_contact_ref = new_recepient_full['data'][0]['ContactPerson']["data"][0]['Ref']
    return new_recepient_full_ref, new_recepient_contact_ref


def get_city_and_street_refs(city, street):
    # Get city reference
    get_city = {
        "modelName": "Address",
        "calledMethod": "getCities",
        "methodProperties": {
            "FindByString": city
        },
        "apiKey": np_token
    }
    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=get_city)
    content = response.content
    get_city_full = json.loads(content)
    get_city_full_ref = get_city_full['data'][0]['Ref']
    # Get street reference
    get_street = {
        "modelName": "Address",
        "calledMethod": "getStreet",
        "methodProperties": {
            "CityRef": get_city_full_ref,
            "FindByString": street
        },
        "apiKey": np_token
    }
    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=get_street)
    content = response.content
    get_street_full = json.loads(content)
    get_street_full_ref = get_street_full['data'][0]['Ref']

    return get_city_full_ref, get_street_full_ref


@shared_task
def get_city_ref(city):
    # Get city reference
    get_city = {
        "modelName": "Address",
        "calledMethod": "getCities",
        "methodProperties": {
            "FindByString": city
        },
        "apiKey": np_token
    }
    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=get_city)
    content = response.content
    get_city_full = json.loads(content)
    get_city_full_ref = get_city_full['data'][0]['Ref']

    return get_city_full_ref


def create_recipient_address(recipient_ref, street_ref, building, flat):
    # Create recipient address
    get_adress = {
        "modelName": "Address",
        "calledMethod": "save",
        "methodProperties": {
            "CounterpartyRef": recipient_ref,
            "StreetRef": street_ref,
            "BuildingNumber": building,
            "Flat": flat,
        },
        "apiKey": np_token
    }
    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=get_adress)
    content = response.content
    get_adress_full = json.loads(content)
    get_adress_ref = get_adress_full['data'][0]['Ref']
    return get_adress_ref


@shared_task
def create_ttn(name, middlename, lastname, payerType, volume, weight, description, price,
               recipient_city_ref, shipdate, phonenum, recipient_warehouse_str, ):
    # Step 1: Get the sender's reference and contact information
    countr_ref = cache.get("sender_ref")

    # Step 2: Create a new recipient and obtain their contact information
    new_recepient_full_ref, new_recepient_contact_ref = get_rec_info(name, middlename, lastname, phonenum)

    # Step 3: Get references for sender's and recipient's cities and streets
    sender_warehouse = cache.get("wh_address")
    sender_warehouse_index = cache.get("wh_index"),
    sender_city_ref = cache.get("city_ref")
    countr_cont_full_ref, countr_cont_full_phones = get_phone_full_ref(countr_ref)
    # Step 4: Create the recipient's address

    # Step 5: Prepare shipment data
    date = shipdate
    params1 = {
        "apiKey": np_token,
        "modelName": "InternetDocument",
        "calledMethod": "save",
        "methodProperties": {
            "PayerType": payerType,
            # RETURN LATER https://novaposhta.ua/payment_korp_clients OK MB RIGHT
            "PaymentMethod": "Cash",
            "DateTime": date,
            "CargoType": "Parcel",
            "VolumeGeneral": volume,
            "Weight": weight,
            "ServiceType": "WarehouseWarehouse",
            "SeatsAmount": "1",
            "Description": description,
            "Cost": price if float(price) > 300.01 else 300.01,
            "CitySender": sender_city_ref,
            "Sender": countr_ref,
            "SenderAddress": sender_warehouse,
            "ContactSender": countr_cont_full_ref,
            "SendersPhone": countr_cont_full_phones,
            "CityRecipient": recipient_city_ref,
            "Recipient": new_recepient_full_ref,
            "RecipientAddress": recipient_warehouse_str,
            "ContactRecipient": new_recepient_contact_ref,
            "RecipientsPhone": phonenum,
        }
    }

    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=params1)
    content = response.content
    result = json.loads(content)
    print(result)
    DocNumber = result['data'][0]['IntDocNumber']
    print(f'{DocNumber=}')
    # Step 7: Return the e-waybill reference as the result
    return DocNumber


@shared_task
def calculate_shipment(weight, price, city, senderCity):
    # Step 1: Get the sender's reference and contact information
    # Step 2: Create a new recipient and obtain their contact informatio
    # Step 4: Create the recipient's address
    # Step 5: Prepare shipment data
    params1 = {
        "apiKey": np_token,
        "modelName": "InternetDocument",
        "calledMethod": "getDocumentPrice",
        "methodProperties": {
            "CitySender": senderCity,
            "CityRecipient": city,
            "Weight": str(weight / 1000),
            "ServiceType": "WarehouseWarehouse",
            "Cost": str(price),
            "CargoType": "Parcel",
            "SeatsAmount": "1"
        },
    }

    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=params1)
    print(response)
    print(f"{response.content}")
    content = response.content
    result = json.loads(content)
    price = result['data'][0]['Cost']
    print(price)
    # Step 7: Return the e-waybill reference as the result
    return price


@shared_task
def task1(mail_subject,date,products, user):
    # make async task for email sending
    message = render_to_string('order.html', {
        'user': user,
        "products":products,
        "date":date,
    })
    email = EmailMessage(
        mail_subject, message, to=[user.get("email")]
    )
    email.send()
# get_sender_ref.delay().get()
# get_warehouse_ref.delay()
