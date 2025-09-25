# Demo data for testing the Locus Assistant application
demo_orders_data = {
    "orders": [
        {
            "homebase": {
                "type": "HOMEBASE",
                "teams": [{"clientId": "illa-frontdoor", "version": None, "teamId": "101"}],
                "address": {
                    "id": None,
                    "placeName": None,
                    "localityName": None,
                    "formattedAddress": "689G+XVG، سرياقوس، مركز الخانكة،, Al Khankah, Al Qalyubia Governorate, Egypt",
                    "subLocalityName": None,
                    "pincode": None,
                    "city": None,
                    "state": None,
                    "countryCode": "EG",
                    "locationType": None,
                    "placeHash": None
                },
                "latLng": {"lat": 30.22011043856786, "lng": 31.32719883558217, "accuracy": 0},
                "contactId": None,
                "contact": None,
                "timeSlots": [],
                "transactionDuration": None,
                "pincodes": [],
                "crossDockInfo": None,
                "clientId": "illa-frontdoor",
                "id": "101",
                "name": "Front Door Warehouse",
                "code": None,
                "status": "ACTIVE",
                "version": 1,
                "customProperties": {}
            },
            "location": {
                "geocoded": True,
                "detectedTimeZone": "Africa/Cairo",
                "type": "CLIENT",
                "teams": [{"clientId": "illa-frontdoor", "version": None, "teamId": "101"}],
                "address": {
                    "id": "SPN-0102162622",
                    "placeName": "SPINNEYS MAZAR",
                    "localityName": None,
                    "formattedAddress": "3X36+J29, El-Bostan, Second Al Sheikh Zayed, Giza Governorate 3240484, Egypt",
                    "subLocalityName": None,
                    "pincode": None,
                    "city": "Sheikh Zayed",
                    "state": "Giza",
                    "countryCode": "EG",
                    "locationType": None,
                    "placeHash": None
                },
                "latLng": {"lat": 30.0540151, "lng": 30.9601188, "accuracy": 0},
                "contactId": None,
                "contact": None,
                "timeSlots": [
                    {"dayOfWeek": "MONDAY", "slots": [{"start": "08:00", "end": "18:00"}]},
                    {"dayOfWeek": "TUESDAY", "slots": [{"start": "08:00", "end": "18:00"}]}
                ],
                "transactionDuration": 3600,
                "clientId": "illa-frontdoor",
                "id": "SPN-0102162622",
                "name": "SPINNEYS MAZAR",
                "code": "SPN-0102162622",
                "status": "ACTIVE",
                "version": 8,
                "customProperties": {}
            },
            "parentOrderId": None,
            "orderStatus": "COMPLETED",
            "orderSubStatus": None,
            "channel": "TRACK_IQ",
            "mode": "DISPATCH_IQ",
            "masterLineItems": [],
            "orderMetadata": {
                "batchId": "2025-09-23-20-14-18",
                "planId": "bf32fb8835c248428f1dc0a901da3c07",
                "dispatchWaveId": None,
                "dispatchWaveName": None,
                "dispatchWaveBatchId": None,
                "planIteration": 1,
                "homebaseId": None,
                "latLng": {"lat": 30.0525356, "lng": 30.9614376},
                "trackingInfo": {"link": "<obfuscated>"},
                "customerSlotStart": None,
                "customerSlotEnd": None,
                "taskDate": None,
                "checklist": {
                    "Customer Delivery Photo": {"Customer Delivery Photo": "https://locus-api.com/v1/client/illa-frontdoor/task/1704776705/file/c3a9a57a-02e9-42bd-a9c9-a75c340f98bc"},
                    "Customer Confirmation Signature": {"Customer Confirmation Signature": "https://locus-api.com/v1/client/illa-frontdoor/task/1704776705/file/1fdbeb0a-66ef-4b11-865c-78d3a5ef65a8"},
                    "Proof Of Delivery Document": {"Proof Of Delivery Document": "https://locus-api.com/v1/client/illa-frontdoor/task/1704776705/file/2fb26192-ad1b-477c-9114-3255266b9587"}
                },
                "tourDetail": {
                    "tourId": "2025-09-23-20-14-18*bf32fb8835c248428f1dc0a901da3c07*tour-71",
                    "sequence": 3,
                    "riderId": "01097412077",
                    "riderName": "zeyad tamer",
                    "riderNumber": "+201097412077",
                    "transporterId": "default-transporter",
                    "transporterName": "default-transporter",
                    "vehicleModelId": "12",
                    "vehicleModelName": "Jumbo 7000 open NPR",
                    "vehicleId": "4783______",
                    "vehicleName": "4783______",
                    "vehicleRegistrationNumber": "4783______",
                    "tourStartTime": "2025-09-23T21:00:00.000+0000",
                    "tourEndTime": None,
                    "tourTravelDistance": None,
                    "isSortedForTour": False,
                    "costMetadata": None,
                    "isMultiTrip": None,
                    "parentTourId": None,
                    "customProperties": {}
                },
                "homebaseCompleteOn": "2025-09-24T07:40:12.243Z",
                "isInventoryVerified": True,
                "lineItems": [
                    {
                        "transactionStatus": {
                            "orderedWeight": {"value": "15475.0", "unit": "G"},
                            "transactedWeight": {"value": "15475.0", "unit": "G"},
                            "orderedVolume": {"value": "0.047", "unit": "CM"},
                            "transactedVolume": {"value": "0.047", "unit": "CM"},
                            "orderedQuantity": 5,
                            "transactedQuantity": 5,
                            "checklistValues": {},
                            "triggerTime": "2025-09-24T11:32:02.777+0000",
                            "actor": {"id": "illa-frontdoor/01097412077"},
                            "status": "DELIVERED"
                        },
                        "id": "3101110008090",
                        "reconcileQuantity": 0,
                        "handlingUnit": "QUANTITY"
                    },
                    {
                        "transactionStatus": {
                            "orderedWeight": {"value": "3832.0", "unit": "G"},
                            "transactedWeight": {"value": "3832.0", "unit": "G"},
                            "orderedVolume": {"value": "0.032", "unit": "CM"},
                            "transactedVolume": {"value": "0.032", "unit": "CM"},
                            "orderedQuantity": 1,
                            "transactedQuantity": 1,
                            "checklistValues": {},
                            "triggerTime": "2025-09-24T11:32:02.775+0000",
                            "actor": {"id": "illa-frontdoor/01097412077"},
                            "status": "DELIVERED"
                        },
                        "id": "31010108050",
                        "reconcileQuantity": 0,
                        "handlingUnit": "QUANTITY"
                    }
                ]
            }
        },
        {
            "homebase": {
                "type": "HOMEBASE",
                "teams": [{"clientId": "illa-frontdoor", "version": None, "teamId": "101"}],
                "address": {
                    "formattedAddress": "Front Door Warehouse, Cairo, Egypt",
                    "city": "Cairo",
                    "state": "Cairo",
                    "countryCode": "EG"
                },
                "latLng": {"lat": 30.0444, "lng": 31.2357, "accuracy": 0},
                "clientId": "illa-frontdoor",
                "id": "101",
                "name": "Front Door Warehouse",
                "status": "ACTIVE"
            },
            "location": {
                "type": "CLIENT",
                "teams": [{"clientId": "illa-frontdoor", "version": None, "teamId": "101"}],
                "address": {
                    "id": "CARREFOUR-MAADI",
                    "placeName": "CARREFOUR MAADI",
                    "formattedAddress": "Ring Rd, Maadi, Cairo Governorate, Egypt",
                    "city": "Cairo",
                    "state": "Cairo",
                    "countryCode": "EG"
                },
                "latLng": {"lat": 29.9597, "lng": 31.2735, "accuracy": 0},
                "clientId": "illa-frontdoor",
                "id": "CARREFOUR-MAADI",
                "name": "CARREFOUR MAADI",
                "status": "ACTIVE"
            },
            "orderStatus": "COMPLETED",
            "channel": "TRACK_IQ",
            "mode": "DISPATCH_IQ",
            "orderMetadata": {
                "batchId": "2025-09-24-08-30-45",
                "tourDetail": {
                    "riderId": "01234567890",
                    "riderName": "Ahmed Hassan",
                    "riderNumber": "+201234567890",
                    "vehicleRegistrationNumber": "ABC1234",
                    "vehicleModelName": "Toyota Hiace"
                },
                "homebaseCompleteOn": "2025-09-24T09:15:30.123Z",
                "lineItems": [
                    {
                        "transactionStatus": {
                            "orderedQuantity": 3,
                            "transactedQuantity": 3,
                            "status": "DELIVERED"
                        },
                        "id": "ITEM123",
                        "handlingUnit": "QUANTITY"
                    },
                    {
                        "transactionStatus": {
                            "orderedQuantity": 7,
                            "transactedQuantity": 7,
                            "status": "DELIVERED"
                        },
                        "id": "ITEM456",
                        "handlingUnit": "QUANTITY"
                    }
                ]
            }
        }
    ]
}