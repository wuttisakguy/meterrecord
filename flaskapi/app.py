from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import json
import os
import base64
import io
from dotenv import load_dotenv
import sys
from pathlib import Path
from bson import binary

parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)

from MeterReader.meter_reader import MeterReader
from glob import glob
import random
from datetime import datetime,timedelta
from PIL import Image
from flask_cors import CORS, cross_origin
from flask import send_file
from datetime import datetime
from typing import Dict, Union

load_dotenv()

parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)

meter_reader = MeterReader(model_path=os.path.join(parent_dir, "MeterReader", "model", "best3.pt"), confidence_level=0.5)

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db_watermeter = client["meter_recording"]["meters_water"]
db_electmeter = client["meter_recording"]["meters_electric"]
db_waterbill = client["meter_recording"]["bills_water"]
db_electbill = client["meter_recording"]["bills_electric"]
db_config_water = client['meter_recording']['config_water_meter']
db_config_elec = client['meter_recording']['config_electric_meter']
db_unit_water = client['meter_recording']['unit_water']
db_unit_elec = client['meter_recording']['unit_electric']
    

def calculate_water_bills(unit:float):
    #203unit
    config_water = db_config_water.find_one()
    config_elec = db_config_elec.find_one()
    value = 579.00
 
    #51-60
    if(unit >= 51 and unit > 60):
        value += (10*config_water['waterunit_51_60'])
    elif(unit >=51 and unit <= 60):
        value += ((unit-50)*config_water['waterunit_51_60'])
    #61-80
    if(unit >= 61 and unit > 80):
        value += (20*config_water['waterunit_61_80'])
    elif(unit >=61 and unit <= 80):
        value += ((unit-60)*config_water['waterunit_61_80'])
    #81-100
    if(unit >= 81 and unit > 100):
        value += (20*config_water['waterunit_81_100'])
    elif(unit >=81 and unit <= 100):
        value += ((unit-80)*config_water['waterunit_81_100'])
    #101-120
    if(unit >= 101 and unit > 120):
        value += (20*config_water['waterunit_101_120'])
    elif(unit >=101 and unit <= 120):
        value += ((unit-100)*config_water['waterunit_101_120']) 
    #121-160
    if(unit >= 121 and unit > 160):
        value += (40*config_water['waterunit_121_160'])
    elif(unit >=121 and unit <= 160):
        value += ((unit-120)*config_water['waterunit_121_160']) 
    #161-200
    if(unit >= 161 and unit > 200):
        value += (40*config_water['waterunit_161_200'])
        value += ((unit-200)*config_water['waterunit_201'])
    elif(unit >=161 and unit <= 200):
        value += ((unit-160)*config_water['waterunit_161_200']) 
    return value

def calculate_elec_bills(unit:float) -> Dict[float, float]:
    config_elec = db_config_elec.find_one()

    value = 0
    #1-150
    if unit >= 1 and unit > 150 :
        value += (150*config_elec['unit1_150'])
    elif unit >= 1 and unit <= 150:
        value += ((unit-0)*config_elec['unit1_150'])
    #151-400
    if unit >= 151 and unit > 400 :
        value += (250*config_elec['unit151_400'])
        value += ((unit-400)*config_elec['unit401'])
    elif unit >= 151 and unit <= 400 :
        value += ((unit-150)*config_elec['unit151_400'])

    value = value + ((config_elec['ft'] * unit)/100)
    return value, config_elec['ft']

@app.route('/api/data_water', methods=['GET'])
@cross_origin()
def get_data_water():
    collection = db_watermeter
    data = list(collection.find({}, {'_id': 0, 'name': 1, 'id': 1, 'value': 1, 'datetime': 1, 'image': 1}))
    formatted_data = []

    for item in data:
        if 'image' in item:
            image_binary = item['image']
            image_base64 = base64.b64encode(image_binary).decode('utf-8')
            item['image'] = image_base64
        formatted_data.append(item)

    return jsonify(data)

@app.route('/api/data_elect', methods=['GET'])
@cross_origin()
def get_data_elect():
    collection = db_electmeter
    data = list(collection.find({}, {'_id': 0, 'name': 1, 'id': 1, 'value': 1, 'datetime': 1, 'image': 1}))
    formatted_data = []

    for item in data:
        if 'image' in item:
            image_binary = item['image']
            image_base64 = base64.b64encode(image_binary).decode('utf-8')
            item['image'] = image_base64
        formatted_data.append(item)

    return jsonify(data)

@app.route('/api/datatable_elect', methods=['GET'])
@cross_origin()
def get_datatable_elect():
    collection = db_electbill
    current_year = datetime.now().year
    pipeline = [
    {
        "$project": {
            "_id": 0,
            "name": 1,
            "id": 1,
            "unit": 1,
            "ft": 1,
            "bill": 1,
            "year": {"$year": "$datetime"}, 
            "month": {"$month": "$datetime"} 
        }
    },
    {
            "$match": {
                "year": current_year
            }
        },
    {
        "$sort": {"year": 1, "month": 1}
    }
]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)

@app.route('/api/datatable_water', methods=['GET'])
@cross_origin()
def get_datatable_water():
    collection = db_waterbill
    current_year = datetime.now().year
    pipeline = [
    {
        "$project": {
            "_id": 0,
            "name": 1,
            "id": 1,
            "unit": 1,
            "bill": 1,
            "year": {"$year": "$datetime"}, 
            "month": {"$month": "$datetime"} 
        }
    },
    {
            "$match": {
                "year": current_year
            }
        },
    {
        "$sort": {"year": 1, "month": 1}
    }
]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)

@app.route('/api/data_waterbillmonth', methods=['GET'])
@cross_origin()
def get_data_waterbillmonth():
    collection = db_waterbill
    pipeline = [
    {
        "$project": {
            "_id": 0,
            "name": 1,
            "id": 1,
            "bill": 1,
            "year": {"$year": "$datetime"}, 
            "month": {"$month": "$datetime"} 
        }
    },
    {
        "$group": {
            "_id": {"year": "$year", "month": "$month"},
            "total_bill": {"$sum": "$bill"}
        }
    },
    {
        "$project": {
            "_id": 0,
            "year": "$_id.year",
            "month": "$_id.month",
            "total_bill": 1
        }
    },
    {
        "$sort": {"year": 1, "month": 1} 
    }
]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)

@app.route('/api/data_waterbillmonthChart', methods=['GET'])
@cross_origin()
def get_data_waterbillmonthChart():
    collection = db_waterbill
    pipeline = [
        {
            "$project": {
                "_id": 0,
                "name": 1,
                "id": 1,
                "bill": 1,
                "year": {"$year": "$datetime"}, 
                "month": {"$month": "$datetime"} 
            }
        },
        {
            "$group": {
                "_id": {
                    "name": "$name",
                    "year": "$year",
                    "month": "$month"
                },
                "total_bill": {"$sum": "$bill"}
            }
        },
        {
            "$project": {
                "_id": 0,
                "name": "$_id.name",
                "year": "$_id.year",
                "month": "$_id.month",
                "total_bill": 1
            }
        },
        {
            "$sort": {"year": 1, "month": 1} 
        }
    ]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)

@app.route('/api/data_electricbillmonth', methods=['GET'])
@cross_origin()
def get_data_electricbillmonth():
    collection = db_electbill
    pipeline = [
    {
        "$project": {
            "_id": 0,
            "name": 1,
            "id": 1,
            "unit": 1,
            "bill": 1,
            "year": {"$year": "$datetime"}, 
            "month": {"$month": "$datetime"} 
        }
    },
    {
        "$group": {
            "_id": {"year": "$year", "month": "$month"},
            "total_bill": {"$sum": "$bill"}
        }
    },
    {
        "$project": {
            "_id": 0,
            "year": "$_id.year",
            "month": "$_id.month",
            "unit": 1,
            "total_bill": 1
        }
    },
    {
        "$sort": {"year": 1, "month": 1}
    }
]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)

@app.route('/api/data_electricbillunitperfloor', methods=['GET'])
@cross_origin()
def get_data_electricbillunitperfloor():
    collection = db_electbill
    pipeline = [
    {
        "$project": {
            "_id": 0,
            "name": 1,
            "id": 1,
            "unit": 1,
            "bill": 1,
            "year": {"$year": "$datetime"}, 
            "month": {"$month": "$datetime"} 
        }
    },
    {
        "$group": {
            "_id": {"year": "$year", 
                    "month": "$month" , 
                    "unit": "$unit" , 
                    "name": "$name"},
            "total_bill": {"$sum": "$bill"},
            
        }
    },
    {
        "$project": {
            "_id": 0,
            "year": "$_id.year",
            "month": "$_id.month",
            "unit": "$_id.unit",
            "name": "$_id.name",
            "total_bill": 1
        }
    },
    {
        "$sort": {"year": 1, "month": 1}
    }
]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)

@app.route('/api/data_watericbillunitperfloor', methods=['GET'])
@cross_origin()
def get_data_waterbillunitperfloor():
    collection = db_waterbill
    pipeline = [
    {
        "$project": {
            "_id": 0,
            "name": 1,
            "id": 1,
            "unit": 1,
            "bill": 1,
            "year": {"$year": "$datetime"}, 
            "month": {"$month": "$datetime"} 
        }
    },
    {
        "$group": {
            "_id": {"year": "$year", 
                    "month": "$month" , 
                    "unit": "$unit" , 
                    "name": "$name"},
            "total_bill": {"$sum": "$bill"},
            
        }
    },
    {
        "$project": {
            "_id": 0,
            "year": "$_id.year",
            "month": "$_id.month",
            "unit": "$_id.unit",
            "name": "$_id.name",
            "total_bill": 1
        }
    },
    {
        "$sort": {"year": 1, "month": 1}
    }
]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)


@app.route('/api/data_electricbillmonthChart', methods=['GET'])
@cross_origin()
def get_data_electricbillmonthChart():
    collection = db_electbill
    pipeline = [
        {
            "$project": {
                "_id": 0,
                "name": 1,
                "id": 1,
                "bill": 1,
                "year": {"$year": "$datetime"}, 
                "month": {"$month": "$datetime"} 
            }
        },
        {
            "$group": {
                "_id": {
                    "name": "$name",
                    "year": "$year",
                    "month": "$month"
                },
                "total_bill": {"$sum": "$bill"}
            }
        },
        {
            "$project": {
                "_id": 0,
                "name": "$_id.name",
                "year": "$_id.year",
                "month": "$_id.month",
                "total_bill": 1
            }
        },
        {
            "$sort": {"year": 1, "month": 1} 
        }
    ]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)

@app.route('/api/data_waterbillyear', methods=['GET'])
@cross_origin()
def get_data_waterbillyear():
    collection = db_waterbill
    pipeline = [
    {
        "$project": {
            "_id": 0,
            "name": 1,
            "id": 1,
            "bill": 1,
            "year": {"$year": "$datetime"},
        }
    },
    {
        "$group": {
            "_id": {"year": "$year"},
            "total_bill": {"$sum": "$bill"}
        }
    },
    {
        "$project": {
            "_id": 0,
            "year": "$_id.year",
            "total_bill": 1
        }
    },
    {
        "$sort": {"year": 1}
    }
]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)

@app.route('/api/data_electricbillyear', methods=['GET'])
@cross_origin()
def get_data_electricbillyear():
    collection = db_electbill
    pipeline = [
    {
        "$project": {
            "_id": 0,
            "name": 1,
            "id": 1,
            "bill": 1,
            "year": {"$year": "$datetime"},
        }
    },
    {
        "$group": {
            "_id": {"year": "$year"},
            "total_bill": {"$sum": "$bill"}
        }
    },
    {
        "$project": {
            "_id": 0,
            "year": "$_id.year",
            "total_bill": 1
        }
    },
    {
        "$sort": {"year": 1}
    }
]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)

@app.route('/api/data_chart_water', methods=['GET'])
@cross_origin()
def get_data_chart_water():
    collection = db_watermeter

    # Find today's date
    today = datetime.now().date()

    # Set start and end time for today
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())

    pipeline = [
        {
            "$match": {
                "datetime": {
                    "$gte": start_of_day,  # Greater than or equal to the start of the day
                    "$lt": end_of_day      # Less than the end of the day
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "name": 1,
                "value": {"$toString": "$value"},
                "time": {"$dateToString": {"format": "%H:%M", "date": "$datetime"}}
            }
        }
    ]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)

@app.route('/api/data_chart_elect', methods=['GET'])
@cross_origin()
def get_data_chart_elect():
    collection = db_electmeter
    today = datetime.now().date()

    # Set start and end time for today
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())

    pipeline = [
        {
            "$match": {
                "datetime": {
                    "$gte": start_of_day,  # Greater than or equal to the start of the day
                    "$lt": end_of_day      # Less than the end of the day
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "name": 1,
                "value": {"$toString": "$value"},
                "time": {"$dateToString": {"format": "%H:%M", "date": "$datetime"}}
            }
        }
    ]
    data = list(collection.aggregate(pipeline))
    return jsonify(data)

@app.route('/meter_reading', methods=['POST'])
def add_meter_reading():
    data = request.json
    position = data['position']
    typemeter = data['type']
    img_base64 = data['imageSrc']

    if img_base64.startswith("data:image"):
        img_base64 = img_base64.split(",")[1]

    # print("Length of base64 string:", len(img_base64))

    if len(img_base64) % 4 != 0:
        return jsonify({"error": "Invalid base64 string"}), 400

    try:
        img_bytes = base64.b64decode(img_base64)
        bson_binary = binary.Binary(img_bytes)
        img = Image.open(io.BytesIO(img_bytes))

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_number = random.randint(1000, 9999)
        filename = f"data_image_{timestamp}_{random_number}.png"
        image_path = os.path.join(parent_dir, "data_images", filename)
        img.save(image_path)

        value = meter_reader.read_meter_value_only(image_path)

        current_utc_datetime = datetime.utcnow()+timedelta(hours=7)

        meter_docs = {
            "name": position,
            "typemeter": typemeter,
            "value": int(value),
            "datetime": current_utc_datetime,
            "image": bson_binary
        }
        print(meter_docs)
        if typemeter == "watermeter":
            db_watermeter.insert_one(meter_docs)
            dt = current_utc_datetime-(timedelta(days=1))
            if current_utc_datetime.hour == 14:
                value_before = db_watermeter.find_one({'datetime':{'$gte': datetime(dt.year, dt.month, dt.day)}})['value']

                meter_unit_docs = {
                    "name": position,
                    "typemeter": typemeter,
                    "id": "101", #1ตัวแรกคือเลขชั้น 01คือลำดับเครื่อง
                    "unit": float(int(value)-int(value_before)),
                    "datetime": current_utc_datetime,
                }
                float(int(value)-int(value_before))
                db_unit_water.insert_one(meter_unit_docs)
        elif typemeter == "electricmeter":
            db_electmeter.insert_one(meter_docs)
            dt = current_utc_datetime-(timedelta(days=1))
            if current_utc_datetime.hour == 14:
                value_before = db_electmeter.find_one({'datetime':{'$gte': datetime(dt.year, dt.month, dt.day)}})['value']

                meter_unit_docs = {
                    "name": position,
                    "typemeter": typemeter,
                    "id": "101", #1ตัวแรกคือเลขชั้น 01คือลำดับเครื่อง
                    "unit": float(int(value)-int(value_before)),
                    "datetime": current_utc_datetime,
                }
                float(int(value)-int(value_before))
                db_unit_elec.insert_one(meter_unit_docs)
        else:
            print("Invalid typemeter value:", typemeter)
        #ค่าแรกของวันที่ 1 ของเดือนมีนา - ค่าแรกของวันที่ 1 กุมภา
        # #ค่าน้ำ
        if typemeter == "watermeter":
            if current_utc_datetime.day == 1:
                if current_utc_datetime.month == 1:
                    value_before = db_watermeter.find_one({'datetime':{'$lte': datetime(current_utc_datetime.year-1,12,2)}},sort=[("datetime",1)])['value']
                else:
                    value_before = db_watermeter.find_one({'datetime':{'$lte': datetime(current_utc_datetime.year,current_utc_datetime.month-1,2)}},sort=[("datetime",1)])['value']
        
                value_bills = calculate_water_bills(float(int(value)-int(value_before)))

                meter_bill_docs = {
                    "name": position,
                    "typemeter": typemeter,
                    "id": "101", #1ตัวแรกคือเลขชั้น 01คือลำดับเครื่อง
                    "unit": float(int(value)-int(value_before)),
                    "bill": value_bills,
                    "datetime": current_utc_datetime,
                }
                print(value_bills)
                db_waterbill.insert_one(meter_bill_docs)
        #ค่าไฟ 
        if typemeter == "electricmeter":
            if current_utc_datetime.day == 13:
                if current_utc_datetime.month == 1:
                    value_before = db_electmeter.find_one({'datetime':{'$lte': datetime(current_utc_datetime.year-1,12,2)}},sort=[("datetime",1)])['value']
                else:
                    value_before = db_electmeter.find_one({'datetime':{'$lte': datetime(current_utc_datetime.year,current_utc_datetime.month-1,2)}},sort=[("datetime",1)])['value']
                
                value_bills, ft = calculate_elec_bills(float(int(value)-int(value_before)))

                meter_bill_docs = {
                    "name": position,
                    "typemeter": typemeter,
                    "id": "101", #1ตัวแรกคือเลขชั้น 01คือลำดับเครื่อง
                    "unit": float(int(value)-int(value_before)),
                    "bill": value_bills,
                    "ft": ft,
                    "datetime": current_utc_datetime,
                }
                print(value_bills)
                db_electbill.insert_one(meter_bill_docs)

        return jsonify({"message": "success", "value": int(value)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
