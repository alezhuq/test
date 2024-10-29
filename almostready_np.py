import json
import time
from datetime import datetime

import requests

"""
ADD NP_TOKEN
ADD GET_DOCUMENT_PRICE : https://developers.novaposhta.ua/view/model/a90d323c-8512-11ec-8ced-005056b2dbe1/method/a91f115b-8512-11ec-8ced-005056b2dbe1

"""
np_token = "3b4774ff70c9a3eafc0ac65238ad9c37"


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
    print(address_full)
    address_ref = address_full['data'][0]['Ref']

    warehouse_index = address_full['data'][0]['WarehouseIndex']
    return address_ref, warehouse_index


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


def get_sender_ref():
    # Retrieve sender reference from Nova Poshta
    countr = {
        "apiKey": np_token,
        "modelName": "Counterparty",
        "calledMethod": "getCounterparties",
        "methodProperties": {
            "CounterpartyProperty": "Sender",
            "Page": "1"
        }
    }
    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=countr)
    content = response.content
    countr_full = json.loads(content)
    countr_ref = countr_full['data'][0]['Ref']
    return countr_ref


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
            "MiddleName": middlename,
            "LastName": lastname,
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


def create_ttn(name, middlename, lastname, payerType, paymentMethod, length, height, width, weight, description, price,
               city, shipdate, phonenum, senderCity, senderStreet, sender_warehouse_str, recipient_warehouse_str):
    # Step 1: Get the sender's reference and contact information
    countr_ref = get_sender_ref()
    countr_cont_full_ref, countr_cont_full_phones = get_phone_full_ref(countr_ref)

    # Step 2: Create a new recipient and obtain their contact information
    new_recepient_full_ref, new_recepient_contact_ref = get_rec_info(name, middlename, lastname, phonenum)

    # Step 3: Get references for sender's and recipient's cities and streets
    sender_city_ref, sender_street_ref = get_city_and_street_refs(senderCity, senderStreet)
    recipient_warehouse, recipient_warehouse_index = get_warehouse_by_string(city, recipient_warehouse_str)
    # Step 4: Create the recipient's address
    # get_adress_ref = create_recipient_address(new_recepient_full_ref, sender_street_ref, building, flat)
    sender_warehouse, sender_warehouse_index = get_warehouse_by_string(senderCity, sender_warehouse_str)
    # Step 5: Prepare shipment data
    date = shipdate
    params1 = {
        "apiKey": np_token,
        "modelName": "InternetDocument",
        "calledMethod": "save",
        "methodProperties": {
            "PayerType": payerType,
            "PaymentMethod": paymentMethod,
            "DateTime": date,
            "CargoType": "Parcel",
            "VolumeGeneral": length * height * width,
            "Weight": weight,
            "ServiceType": "WarehouseWarehouse",
            "SeatsAmount": "1",
            "Description": description,
            "Cost": price if price > 300.01 else 300.01,
            "CitySender": sender_city_ref,
            "Sender": countr_ref,
            "SenderAddress": sender_warehouse,
            "ContactSender": countr_cont_full_ref,
            "SendersPhone": countr_cont_full_phones,
            "CityRecipient": sender_city_ref,
            "Recipient": new_recepient_full_ref,
            "RecipientAddress": recipient_warehouse,
            "ContactRecipient": new_recepient_contact_ref,
            "RecipientsPhone": phonenum,
            "RecipientWarehouseIndex": recipient_warehouse_index,
            "SenderWarehouseIndex": sender_warehouse_index,
        }
    }

    response = requests.post('https://api.novaposhta.ua/v2.0/json/', json=params1)
    content = response.content
    result = json.loads(content)
    print(content)
    e_waybill_ref = result['data'][0]['Ref']

    # Step 7: Return the e-waybill reference as the result
    return e_waybill_ref


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


# Usage example:
new_tnn = create_ttn(
    name="Олег",
    middlename="Ігорович",
    lastname="Кутрик",
    phonenum="0685141364",
    payerType="Sender",
    paymentMethod="Cash",
    length=0.5,
    height=0.2,
    width=0.2,
    weight=1,
    description="Опис",
    price=500,
    city="Чортків",
    building="35",
    flat="28",
    shipdate=datetime.now().strftime("%d.%m.%Y"),
    senderCity="Київ",
    senderStreet="Правди",
    sender_warehouse_str="Відділення №1",
    recipient_warehouse_str="Відділення №1",
)

print("E-Waybill Reference:", new_tnn)
