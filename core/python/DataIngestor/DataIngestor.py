""" Data Ingestor Microservice -
The service will take form data and generate
the appropriate URL for the .gz file """

import json
import logging
import random
import requests
import uuid
import requests
import boto

from boto.s3.connection import S3Connection
from flask import Flask, render_template, request, url_for, render_template
from boto.s3.connection import S3Connection
from flask import jsonify, abort
from datetime import datetime
from flask import Flask
from kazoo.client import KazooClient
from kazoo.client import KazooState
from kazoo.exceptions import KazooException

app = Flask(__name__)


@app.route('/getUrl/<string:yy>/<string:mm>/<string:dd>/<string:stationId>/', methods=['GET'])
def generateMyURL(yy, mm, dd, stationId):
    #Error if trying to access non-existent file
    finalURL= ''
    if yy < '1991' or (yy == '1991' and mm < '6'):
        abort(404)
        #return jsonify(url = 'Invalid arguments!!! Records does not exist'), 404

    s3conn = boto.connect_s3(anon = True)
    bucket = s3conn.get_bucket('noaa-nexrad-level2',validate=False)
    print(bucket)
    keyGenerated = str(yy)+"/" +str(mm)+"/"+str(dd)

    #Sample Download Url :https://noaa-nexrad-level2.s3.amazonaws.com/1996/06/06/KVBX/KVBX19960606_001958.gz

    for k in bucket.get_all_keys(prefix=keyGenerated):
        #Reformatring the s3 content to match the .gz file
        searchKeySet = str(k).split("Key:")[1].split(">")[0].split(",")[1]
        print(searchKeySet,"p{")
        if keyGenerated in str(searchKeySet):
            finalURL = 'noaa-nexrad-level2.s3.amazonaws.com/'+searchKeySet
            print(finalURL)
            break

    if finalURL =='':
        abort(404)
    return finalURL ,200


@app.errorhandler(404)
def invalidArguments(e):
    return 'Error-Message Invalid arguments!!! Records does not exist' ,206


def getValue(sId, ec2IP, path):
    return json.dumps({"name": "dataIngestor",
                       "id": sId,
                       "address": ec2IP,
                       "port": 65000,
                       "sslPort": None,
                       "payload": None,
                       "registrationTimeUTC": (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds(),
                       "serviceType": "DYNAMIC",
                       "uriSpec": {"parts": [{"value": path,
                                              "variable": True}]}}, ensure_ascii=True).encode()


def my_listener(state):
    global ip
    if state == KazooState.LOST:
        zkIP = ip + ":2181"
        zk = KazooClient(hosts=zkIP)
        zk.start()
    elif state == KazooState.SUSPENDED:
        print("Connection Suspended")
    else:
        print("Connection Error")


def register():
    try:
        global ip
        sId = str(uuid.uuid4())
        zkIp = ip + ":2181"
        zk = KazooClient(hosts=zkIp)
        zk.start()
        zk.add_listener(my_listener)
        path = "http://" + ip + ":65000/getUrl/<string:yy>/<string:mm>/<string:dd>/<string:stationId>/"
        zk.create("/services/dataIngestor/" + sId, getValue(sId, ip, path), ephemeral=True, makepath=True)
    except KazooException as e:
        print(e.__doc__)
    logging.basicConfig()


if __name__ == '__main__':
    ip = requests.get("http://checkip.amazonaws.com/").text.split("\n")[0]
#    ip = "127.0.0.1"
    register()
    app.run(
        host="0.0.0.0",
        port=int(65000)
        # debug=True
    )