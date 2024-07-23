
from fastapi import FastAPI ,HTTPException,Request
from pymongo import MongoClient
from pydantic import BaseModel
from bson.objectid import ObjectId
import xml.etree.ElementTree as ET
import xmltodict,datetime


# Create a new client and connect to the server
client = MongoClient("mongodb+srv://guulue:AEp6Vk4LfGOwoEwp@cluster0.ej71rbs.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

db_events =client["events"]
conllection_events = db_events["events"]

db_people_count =client["events"]
conllection_people_count = db_people_count["people_counting"]

app = FastAPI()


class FillterCameras(BaseModel):
    ip_address:str 
    start_time:str 
    end_time:str 

# count_people
@app.post("/count_people")
async def count_people(filter_a: FillterCameras):
    try:
        if filter_a.ip_address== "":
            return {"Message": "IP Address is required !"}
        elif filter_a.start_time == "":
            return {"Message": "Start time is required !"}
        elif filter_a.end_time == "":
            return {"Message": "End time is required !"}
        # select data
        results=list(conllection_people_count.find({
            "ipAddress":filter_a.ip_address,
            "time" : { "$gte": filter_a.start_time },
            "time" : { "$lte": filter_a.end_time },
        }))

        # sum amount(Enter and Exit)
        total_enter =0
        total_exit =0
        for count_p in results :
             total_enter += int(count_p["enter"])
             total_exit += int(count_p["exit"])


        if results:
            return { 
                    "success": True,
                    "total_enter":total_enter,
                    "total_exit": total_exit
            }
        else :
             raise HTTPException(status_code=404, detail="Not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#detect
@app.post("/detect",status_code=200)
async def insert_event(request: Request):
    try:
        content_type = request.headers["Content-Type"] 
        if content_type == "application/xml":
            body = await request.body()

            body_content = xmltodict.parse(body)
            body_event= body_content['EventNotificationAlert']
            # check before insert 
            log_event=conllection_events.find_one({"ipAddress" : body_event["ipAddress"], "dateTime" : body_event["dateTime"]})
            if log_event: # it's true 
                return {"Status":"ERROR","Message":"Error Insert duplicate Key"}
            else: # it's false , precess to fn.insert store at events's collection 
                result = conllection_events.insert_one(body_event)

            # get id form process fn.insert 
            event_id= str(result.inserted_id)

            # precess to fn.insert store at people_counting's collection 
            body_counting = body_event["peopleCounting"]
            result = conllection_people_count.insert_one({
                "event_id"  : event_id,
                "ipAddress": body_event["ipAddress"],
                "time": datetime.datetime.strptime(body_counting["RealTime"]["time"], "%Y-%m-%dT%H:%M:%S%z").strftime("%Y%m%d%H%M%S"),
                "enter": body_counting["enter"],
                "exit": body_counting["exit"],
                "duplicatePeople": body_counting["duplicatePeople"],
                "countingSceneMode": body_counting["countingSceneMode"],

            })
            return {
                "Event ID": event_id,
                "Status":"OK"
            }
        else:
            raise HTTPException(status_code=400, detail="Content type {content_type} not supported")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
    

