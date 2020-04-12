import http.server
import threading
from urllib.parse import urlparse
from threading import Lock
from datetime import date
import requests
import time
import speech_recognition as sr
import os
import datetime
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
#import RPi.GPIO as GPIO
from subprocess import call
from google.cloud import texttospeech
from playsound import playsound
import pyowm
import json
from flask import Flask
from flask import request

nltk.download("stopwords")

ps = PorterStemmer()
port = 8080
routinePort = 8081
appNodeId = 0
watchId = 0
maxNodes = 15
serverStart = False
lock = Lock()
waitingForCommand = False
processingTrigger = False
waitingForGoogleBool = False
tempSpeaking = False
dateSpeaking = False

red = 17
blue2 = 27
red2 = 22
blue = 5
btn = 15

"""GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(red, GPIO.OUT)
GPIO.output(red, GPIO.LOW)
GPIO.setup(blue2, GPIO.OUT)
GPIO.output(blue2, GPIO.LOW)
GPIO.setup(red2, GPIO.OUT)
GPIO.output(red2, GPIO.LOW)
GPIO.setup(blue, GPIO.OUT)
GPIO.output(blue, GPIO.LOW)
GPIO.setup(btn, GPIO.IN, pull_up_down=GPIO.PUD_UP)

class CustomHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        url = urlparse(self.path)
        print(url)
        value = url.query[5::]
        print(value)
        parameters = value.split("$")
        parameters.pop()

        decodeThread = threading.Thread(target=decodeParameters, args=[self.client_address[0], parameters])
        decodeThread.start()
"""


class Node:
    nodeCount = 0

    @classmethod
    def initiateAsNonIr(cls, self, ip, nodeName, type, location, relayStat=0):
        self.ip = ip
        self.nodeName = nodeName
        self.type = type
        self.relayStat = relayStat
        self.conStat = 1
        self.irActions = set()
        self.notifiedAppofDisconnect = False
        self.location = location

    @classmethod
    def initiateAsIr(cls, self, ip, nodeName, type, irActions, location, relayStat=0):
        self.ip = ip
        self.nodeName = nodeName
        self.type = type
        self.irActions = irActions
        self.relayStat = relayStat
        self.conStat = 1
        self.notifiedAppofDisconnect = False
        self.location = location

    @classmethod
    def initiateAsApp(cls, self, ip):
        self.ip = ip
        self.nodeName = "App"
        self.type = 0
        self.conStat = 1
        self.relayStat = 0
        self.location = "Home"
        self.irActions = set()

    @classmethod
    def initiateAsWatch(cls, self, ip):
        self.ip = ip
        self.nodeName = "Watch"
        self.type = 4
        self.conStat = 1
        self.relayStat = 0
        self.location = "Wrist"
        self.irActions = set()

    def __init__(self):
        print("Empty Node Created")


nodeList = []
deviceList = dict()
destination = dict()
actions = dict()
helper = ["switch", "turn", "launch", "start"]
micSetBool = False
sample_rate = 48000
chunk_size = 8192
device_id = -1
recognizer = sr.Recognizer()
triggerWord = "Alexa"

city = "Ahmedabad"
country = "IN"

routineList = list()
userData = dict()

defaultRoutines = {}


# ----------------------------------------- helper functions ----------------------------------------------
def setUpDefaultRoutines():
    defaultRoutineActions = [
        {
            "actions": {
                "speakMorning": {
                    "delay": "0"
                },
                "speakDateAndTime": {
                    "delay": "0"
                },
                "speakTemperature": {
                    "delay": "0"
                }
            },
        },
        {
            "actions": {
                "speakEvening": {
                    "delay": "0"
                }
            }
        },
        {
            "actions": {
                "speakNight": {
                    "delay": "0"
                }
            }
        },
        {
            "actions": {
                "speakTemperature": {
                    "delay": "0"
                }
            }
        },
        {
            "actions": {
                "speakDateAndTime": {
                    "delay": "0"
                }
            }
        },
        {
            "actions": {
                "turnallon": {
                    "delay": "0"
                }
            }
        },
        {
            "actions": {
                "turnalloff": {
                    "delay": "0"
                }
            }
        }
    ]

    tup0 = ("good morning", "morning")
    tup1 = ("good evening", "evening")
    tup2 = ("good night", "night")
    tup3 = ("temperature", "how hot is it?", "weather", "weather conditions")
    tup4 = ("date", "time", "date and time", "time and date")
    tup5 = ("let there be light")
    tup6 = ("turn off all the lights", "darkness", "turn off all lights", "turn off everything")

    global defaultRoutines
    defaultRoutines[tup0] = defaultRoutineActions[0]
    defaultRoutines[tup1] = defaultRoutineActions[1]
    defaultRoutines[tup2] = defaultRoutineActions[2]
    defaultRoutines[tup3] = defaultRoutineActions[3]
    defaultRoutines[tup4] = defaultRoutineActions[4]
    defaultRoutines[tup5] = defaultRoutineActions[5]
    defaultRoutines[tup6] = defaultRoutineActions[6]


def printNodeList():
    print("IP      ID Name  Type Cstat Rstat Location Actions")
    for node in nodeList:
        print(node.ip + " " + str(node.id) + " " + node.nodeName + " " + str(node.type) + " " + str(
            node.conStat) + " " + str(node.relayStat) + " " + node.location, end=" ")
        for i in node.irActions:
            print(i, end=", ")
        print("")

    print("App node ID: ", appNodeId)
    print("Node Count: ", Node.nodeCount)


def printDictionaries():
    print("\n--------------Printing Dictionaries--------------------")
    for device in deviceList:
        print(device + ":" + str(deviceList[device]))
    print("")
    for location in destination:
        print(location + ":" + str(destination[location]))
    print("")
    for action in actions:
        print(action + ":" + str(actions[action]))


def getExistingNodeList():
    try:
        stream = os.popen('iw dev ap0 station dump | grep Station | cut -f 2 -s -d" "')
        macList = stream.read()
        macList = macList.split("\n")
        macList.pop()

        ipList = list()
        for mac in macList:
            command = 'cat /var/lib/misc/dnsmasq.leases | cut -f 2,3,4 -s -d" " | grep ' + mac + ' | cut -f 2 -s -d" "'
            stream = os.popen(command)
            ip = stream.read()
            ip = ip.rstrip()
            ipList.append(ip)
        return ipList
    except Exception as e:
        print("Existing Node Exception: {0}".format(e))
    return ipList


def setClientInactive(clientIP):
    global watchId, appNodeId, nodeList
    for node in nodeList:
        if node.ip == clientIP:
            nodeList[node.id - 1].conStat = 0

            if node.type == 4:
                watchId = 0
            elif node.type == 0:
                appNodeId = 0
            # printNodeList()


def shutdownSequence():
    GPIO.setmode(GPIO.BCM)
    GPIO.output(blue2, GPIO.LOW)
    GPIO.output(red2, GPIO.LOW)
    GPIO.output(blue, GPIO.LOW)
    # server.shutdown()
    # server.socket.close()
    time.sleep(1)
    GPIO.cleanup()
    call("sudo shutdown -h now", shell=True)


def setWiFiParameters(ssid, password):
    GPIO.setmode(GPIO.BCM)
    GPIO.output(blue, GPIO.HIGH)
    GPIO.output(blue2, GPIO.HIGH)
    file = open('/etc/wpa_supplicant/wpa_supplicant.conf', 'r+')
    line = file.readline()
    while line != '#userconfig\n':
        line = file.readline()

    file.truncate(file.tell())
    file.close()

    file = open('/etc/wpa_supplicant/wpa_supplicant.conf', 'a')
    file.write("\n")
    file.write("network={\n")
    file.write("\tssid=\"" + ssid + "\"\n")
    file.write("\tpsk=\"" + password + "\"\n")
    file.write("\tkey_mgmt=WPA-PSK\n")
    file.write("\tpriority=1\n")
    file.write("\tid_str=\"location3\"\n")
    file.write("}")

    file.close()
    call("sudo wpa_cli -i wlan0 reconfigure", shell=True)
    GPIO.output(blue, GPIO.LOW)
    GPIO.output(blue2, GPIO.LOW)


def turnon(nodeId):
    global nodeList
    if nodeList[nodeId - 1].type == 2 and nodeList[nodeId - 1].conStat:
        nodeList[nodeId - 1].relayStat = 1
        sendNodeStat(nodeId, 2)
        sendNodeStat(nodeId, 0)
        sendNodeStat(nodeId, 4)


def turnoff(nodeId):
    global nodeList
    if nodeList[nodeId - 1].type == 2 and nodeList[nodeId - 1].conStat:
        nodeList[nodeId - 1].relayStat = 0
        sendNodeStat(nodeId, 2)
        sendNodeStat(nodeId, 0)
        sendNodeStat(nodeId, 4)


def turnon(nodeName, nodeLocation):
    global nodeList
    for node in nodeList:
        if node.type == 2 and node.nodeName.lower == nodeName.lower() and node.location.lower() == nodeLocation.lower() and node.conStat:
            nodeList[node.id - 1].relayStat = 1
            sendNodeStat(node.id, 2)
            sendNodeStat(node.id, 0)
            sendNodeStat(node.id, 4)
            break


def turnoff(nodeName, nodeLocation):
    global nodeList
    for node in nodeList:
        if node.type == 2 and node.nodeName.lower == nodeName.lower() and node.location.lower() == nodeLocation.lower() and node.conStat:
            nodeList[node.id - 1].relayStat = 0
            sendNodeStat(node.id, 2)
            sendNodeStat(node.id, 0)
            sendNodeStat(node.id, 4)
            break


def turnOnAllSwitches():
    global nodeList
    for node in nodeList:
        turnon(node.id)


def turnOffAllSwitches():
    global nodeList
    for node in nodeList:
        turnoff(node.id)


def sendIRRequestByName(name, location, action):
    for node in nodeList:
        if node.nodeName.lower() == name.lower() and node.location.lower() == location.lower():
            sendIRRequest(node.id, action)


# ------------------------ State Send or Action Request ----------------------------------------------------

def sendNodeListToApp():
    for node in nodeList:
        if node.id != appNodeId and node.id != watchId:
            sendNodeStat(node.id, 0)
            time.sleep(1)
    # print("Node List Sent!")


def setNodeStat(parameters):
    # reconfigure routine if change in name or location ==========> save old loc and name and compare at end of method
    global nodeList
    global appNodeId
    nodeId = int(parameters[3])
    index = nodeId - 1

    if index < Node.nodeCount and index >= 0:
        removeNameFromDict(nodeList[index].nodeName.lower())
        removeLocationFromDict(nodeList[index].location.lower())

        for action in nodeList[index].irActions:
            removeActionFromDict(action.lower())

        nodeList[index].relayStat = int(parameters[6])
        nodeList[index].conStat = int(parameters[5])
        nodeList[index].location = parameters[7]
        temp = parameters[4]
        tempName = temp

        i = tempName.find("_")
        nodeList[index].irActions.clear()
        if i != -1:

            tempName = tempName[:i]
            i += 1
            temp = temp[i:]
            startI = 0
            endI = 0
            while startI < len(temp):
                endI = temp.find("_", startI)
                nodeList[index].irActions.add(temp[startI:endI])
                startI = endI + 1

            addNodeActionsinDict(nodeList[index].irActions)

        nodeList[index].nodeName = tempName
        addNodeLocationinDict(parameters[7])
        addNodeNameinDict(tempName)
        # printDictionaries()

    # printNodeList()
    if int(parameters[2]) == 0:
        sendNodeStat(nodeId, 2)
        if watchId != 0:
            sendNodeStat(nodeId, 4)
    if int(parameters[2]) == 4:
        sendNodeStat(nodeId, 2)
        if appNodeId != 0:
            sendNodeStat(nodeId, 0)
    if int(parameters[2]) == 2 or int(parameters[2]) == 3:
        if appNodeId != 0:
            sendNodeStat(nodeId, 0)
        if watchId != 0:
            sendNodeStat(nodeId, 4)


def sendIRRequest(nodeId, action):
    index = nodeId - 1
    message = "client@rpi$action@task$1$" + str(nodeList[index].id) + "$" + nodeList[index].nodeName + "$" + str(
        nodeList[index].conStat) + "$" + action + "$" + nodeList[index].location
    requestThread(nodeList[index].ip, port, message)
    # print("Sent IR Request to: ", nodeList[index].nodeName)


def sendNodeStat(nodeId, destinationType):
    global nodeList
    global appNodeId
    node = nodeList[nodeId - 1]
    perform = False
    if destinationType == 0 and appNodeId != 0:
        toIP = nodeList[appNodeId - 1].ip
        perform = True
    if destinationType == 4 and watchId != 0:
        toIP = nodeList[watchId - 1].ip
        perform = True
    if destinationType != 0 and destinationType != 4:
        toIP = node.ip
        perform = True

    if perform:
        message = "client@rpi$action@stat$" + str(node.type) + "$" + str(node.id) + "$" + node.nodeName

        if node.type == 3:
            hasIrAction = False
            for i in node.irActions:
                message += "_" + i.upper()
                hasIrAction = True
            if hasIrAction:
                message += "_"
        message += "$" + str(node.conStat) + "$" + str(node.relayStat) + "$" + node.location + "$"
        requestThread(toIP, port, message)


# ---------------------------- Configurations ---------------------------------------------------------

def configureExistingNodes():
    existingIPList = getExistingNodeList()

    message = "client@rpi$action@reconfig$1$0$RPI$0$0$RPI"
    for ip in existingIPList:
        if ip != '':
            requestThread(ip, port, message)
            time.sleep(1)


def configWatch(clientIP, parameters):
    global nodeList
    global watchId
    newNode = Node()
    newNode.initiateAsWatch(newNode, clientIP)
    mayBeId = 0
    added = False
    type = 4
    for node in nodeList:
        if node.ip == clientIP and type == node.type:
            # print("Overwrite")
            newNode.id = node.id
            nodeList[newNode.id - 1] = newNode
            added = True
            break;
        if node.conStat != 1:
            mayBeId = node.id
    if not added:
        if mayBeId != 0:
            newNode.id = mayBeId
            nodeList[mayBeId - 1] = newNode
            added = True

        if not added:
            Node.nodeCount += 1
            newNode.id = Node.nodeCount
            nodeList.append(newNode)
            added = True

    watchId = newNode.id
    time = datetime.datetime.now()
    today = date.today()

    message = "client@watch$action@config$" + str(time.second) + "$" + str(time.minute) + "$" + str(
        time.hour) + "$" + str(today.day) + "$" + str(today.month) + "$" + str(watchId) + "$"
    for node in nodeList:
        if (node.type == 2 or node.type == 3) and node.conStat == 1:
            name = node.nodeName
            if node.type == 3:
                hasIRActions = False
                for action in node.irActions:
                    name += "_" + action.upper()
                    hasIRActions = True
                if hasIRActions:
                    name += "_"
            message += str(node.type) + "$" + str(node.id) + "$" + name + "$" + str(node.conStat) + "$" + str(
                node.relayStat) + "$" + node.location + "$"
    requestThread(clientIP, port, message)
    # printNodeList()
    #startLedThread(1)


def nodeConfig(clientIP, parameters):
    global nodeList
    global appNodeId
    # print("Node Config")

    type = int(parameters[2])
    mayBeId = 0

    newNode = Node()
    if type == 0:
        newNode.initiateAsApp(newNode, clientIP)
    elif type == 2:
        newNode.initiateAsNonIr(newNode, clientIP, parameters[4], type, parameters[7], int(parameters[6]))
    elif type == 3:
        nodeName = parameters[4]
        i = nodeName.find("_")
        tempSet = set()
        if i != -1:
            nodeName = nodeName[:i]
            i += 1
            temp = parameters[4][i:]
            startI = 0
            endI = 0
            while startI < len(temp):
                endI = temp.find("_", startI)
                tempSet.add(temp[startI:endI].lower())
                startI = endI + 1

        newNode.initiateAsIr(newNode, clientIP, nodeName, type, tempSet, parameters[7], int(parameters[6]))

    added = False
    for node in nodeList:
        if node.ip == clientIP and type == node.type:
            # print("Overwrite")
            newNode.id = node.id
            nodeList[newNode.id - 1] = newNode
            added = True
            break;
        if node.conStat != 1:
            mayBeId = node.id
    if not added:
        if mayBeId != 0:
            newNode.id = mayBeId
            nodeList[mayBeId - 1] = newNode
            added = True

        if not added:
            Node.nodeCount += 1
            newNode.id = Node.nodeCount
            nodeList.append(newNode)
            added = True

    if added and newNode.type != 0:
        addNodeNameinDict(newNode.nodeName)
        addNodeLocationinDict(newNode.location)
        if newNode.type == 2:
            addNodeActionsinDict({"on", "off"})
        elif newNode.type == 3:
            addNodeActionsinDict(newNode.irActions)
    message = "client@rpi$action@config$1$" + str(newNode.id) + "$ESP$" + str(newNode.conStat) + "$" + str(
        newNode.relayStat) + "$" + newNode.location + "$"
    requestThread(clientIP, port, message)
    # print("New Node ID: ", newNode.id)
    # printNodeList()
    # printDictionaries()
    #startLedThread(1)

    if type != 0 and appNodeId != 0:
        sendNodeStat(newNode.id, 0)
    if type != 4 and watchId != 0 and type != 0:
        sendNodeStat(newNode.id, 4)
    if type == 0:
        appNodeId = newNode.id


# --------------------------------------- request Handling -------------------------------------------------------

def decodeParameters(clientIP, parameters):
    print("In decodeP")
    if parameters[1] == "action@stat":
        setNodeStat(parameters)
    elif parameters[1] == "action@config":
        if parameters[0] == "client@watch":
            configWatch(clientIP, parameters)
        else:
            # print("Got Config, current Node Count: ", Node.nodeCount)
            if Node.nodeCount < maxNodes:
                nodeConfig(clientIP, parameters)
            else:
                print("Node List Full")
    elif parameters[1] == "action@getnodelist":
        # print("Node List Request Received")
        sendNodeListToApp()
    elif parameters[1] == "action@recordIR" or parameters[1] == "action@saveIR" or parameters[1] == "action@task" or \
            parameters[1] == "action@remove":
        requestNodeId = int(parameters[3])
        if requestNodeId > 0 and requestNodeId <= Node.nodeCount:
            # print("Forwarding Request")
            forwardRequest(requestNodeId, parameters)
            if parameters[1] == "action@remove":
                removeActionFromDict(parameters[6])
                # printDictionaries()
                forwardRequestToWatch(parameters)
            elif parameters[1] == "action@saveIR":
                temp = set()
                temp.add(parameters[6])
                addNodeActionsinDict(temp)
                # printDictionaries()
                forwardRequestToWatch(parameters)
    elif parameters[1] == "action@wificonfig" and parameters[0] == "client@app":
        setWiFiParameters(parameters[2], parameters[3])
    elif parameters[1] == "action@routinelist":
        message = "client@rpi$action@routinelist$"
        sendJsonPostThread(clientIP, routinePort, message, routineList)


def forwardRequest(toId, parameters):
    message = "client@rpi$" + parameters[1] + "$1$"
    for i in range(3, 7):
        message += parameters[i] + "$"
    requestThread(nodeList[toId - 1].ip, port, message)


def forwardRequestToWatch(parameters):
    message = "client@rpi$" + parameters[1] + "$1$"
    for i in range(3, 7):
        message += parameters[i] + "$"
    requestThread(nodeList[watchId - 1].ip, port, message)


def sendRequest(clientIP, port, message):
    tries = 2
    success = False
    while tries != 0:
        lock.acquire()
        url = "http://" + clientIP + ":" + str(port) + "/message?data=" + message
        # print("Connecting URL: ", url)
        try:
            res = requests.get(url, timeout=4)
            # print("Res Code: ", res.status_code)
            lock.release()
            if res.status_code == 200:
                success = True
                break
        except Exception as e:
            lock.release()
            # print(tries)
            # print("Request Exception: {0}".format(e))
            if tries > 0:
                time.sleep(4 - tries)
            tries -= 1
    if not success:
        setClientInactive(clientIP)


def sendJsonPost(clientIP, port, message, data):
    success = False
    try:
        lock.acquire()
        url = "http://" + clientIP + ":" + str(port) + "/message?data=" + message
        headers = {'content-type': 'application/json'}
        postreq = requests.post(url, data=(json.dumps(data) + "\nEND\n"), headers=headers)
        if postreq.status_code == 200:
            success = True
        lock.release()
    except Exception as e:
        lock.release()


# --------------------------------------- server initiation -------------------------------------------
app = Flask(__name__)


@app.route('/message', methods=['GET', 'POST'])
def postJsonHandler():
    global serverStart
    if request.method == 'POST':
        parameters = request.args.get('data')
        parameters = parameters.split('$')
        parameters.pop()
        if parameters[1] == 'action@routine':
            routine = request.get_json()
            print(routine)
            print(type(routine))
            modifyRoutineThread(routine)


    elif request.method == 'GET':
        print("GET Received")
        parameters = request.args.get('data')
        print(parameters)
        parameters = parameters.split('$')
        parameters.pop()
        clientIP = request.environ['REMOTE_ADDR']
        decodeThread = threading.Thread(target=decodeParameters, args=[clientIP, parameters])
        decodeThread.start()

    return "HTTP/1.1 200 OK\n\n"


def startServer():
    """global serverStart
    global server
    try:
        server = http.server.HTTPServer(('', port), CustomHandler)
        serverStart = True
        #print("Starting Server: ", str(serverStart))
        server.serve_forever()
    except Exception as e:
        print("Error Starting Server: {0}".format(e))"""
    global app
    app.run('192.168.4.1', 8080)


# ---------------------------------------- background client management --------------------------------
def backgroundCheckOfClients():
    global nodeList
    global appNodeId

    while True:
        try:
            ipList = getExistingNodeList()
            for node in nodeList:
                present = False
                #  print("Checking..." + node.nodeName)
                for ip in ipList:
                    if node.ip == ip:
                        #         print("present")
                        present = True
                        break;
                    elif ip == '' and node.type == 4:
                        present = True
                        #        print("present")
                        break;
                if not present:
                    #   print("not present")
                    nodeList[node.id - 1].conStat = 0
                    if nodeList[node.id - 1].type == 0:
                        appNodeId = 0
                        continue
                    elif nodeList[node.id - 1].type == 4:
                        watchId = 0
                        continue

                    if not nodeList[node.id - 1].notifiedAppofDisconnect and appNodeId != 0:
                        sendNodeStat(node.id, 0)
                        nodeList[node.id - 1].notifiedAppofDisconnect = True

            # printNodeList()
        except Exception as e:
            print("Exception in Background Client Check: {0}".format(e))
        time.sleep(5)


# ------------------------------ Routine Manipulation and Execution --------------------------------

def doRoutine(routine):
    print(routine["id"], end=", ")
    print(routine["type"], end=", ")
    print(routine["trigger"], end=", ")
    print(routine["action"])

    actions = routine["actions"]
    for actionName, actionDetail in actions.items():
        time.sleep(int(actionDetail["delay"]))
        if actionName == "speakText":
            speakThread(actionDetail["text"])
        elif actionName == "speakMorning":
            speakFile("goodmorning.mp3")
        elif actionName == "speakNight":
            speakFile("goodnight.mp3")
        elif actionName == "speakEvening":
            speakFile("goodevening.mp3.mp3")
        elif actionName == "speakDateAndTime":
            speakDateAndTime()
        elif actionName == "speakTemperature":
            speakTemperature()
        elif actionName == "turnallon":
            turnOnAllSwitches()
        elif actionName == "turnalloff":
            turnOffAllSwitches()
        elif actionName == "turnon":
            turnon(actionDetail["nodeName"], actionDetail["nodeLocation"])
        elif actionName == "turnoff":
            turnoff(actionDetail["nodeName"], actionDetail["nodeLocation"])
        elif actionName == "iraction":
            sendIRRequestByName(actionDetail["nodeName"], actionDetail["modeLocation"], actionDetail["task"])


def delRoutine(routineId):
    global routineList
    for routine, j in zip(routineList, range(len(routineList))):
        if routine["id"] == routineId:
            del routineList[j]
            print("Routine Deleted")


def checkForScheduledRoutines():
    while True:
        time = datetime.datetime.now()
        hour = time.hour
        hour %= 12
        if hour == 0:
            hour = 12
        minute = time.minute

        for routine in routineList:
            if routine["type"] == "scheduled":
                timeStr = routine["trigger"]
                hour2 = int(timeStr[0]) * 10 + int(timeStr[1])
                minute2 = int(timeStr[3]) * 10 + int(timeStr[4])
                if hour == hour2 and minute == minute2:
                    doRoutineThread(routine)
            time.sleep(2)
        time.sleep(10)


def modifyRoutine(routine):
    pass


# ---------------------------- Dictionary Manipulation for Voice--------------------------------------------
def addNodeNameinDict(name):
    # print("\nAdding Name in Dict")
    global deviceList
    name = name.lower()
    if name in deviceList:
        deviceList[name] = deviceList[name] + 1
    else:
        deviceList[name] = 1


def addNodeLocationinDict(location):
    # print("\nAdding Location in Dict")
    global destination
    location = location.lower()
    if location in destination:
        destination[location] = destination[location] + 1
    else:
        destination[location] = 1


def addNodeActionsinDict(actionSet):
    # print("\nAdding Action Set in Dict")
    global actions

    for action in actionSet:
        action = action.lower()
        if action in actions:
            actions[action] = actions[action] + 1
        else:
            actions[action] = 1


def removeNameFromDict(name):
    # print("\nRemoving Node Name from Dict")
    global deviceList
    name = name.lower()
    if name in deviceList:
        if deviceList[name] > 0:
            deviceList[name] = deviceList[name] - 1


def removeLocationFromDict(location):
    # print("\nRemoving Node Location from Dict")
    global destination
    location = location.lower()
    if location in destination:
        if destination[location] > 0:
            destination[location] = destination[location] - 1


def removeActionFromDict(action):
    # print("\nRemoving Node Action from Dict")
    global actions
    action = action.lower()
    if action in actions:
        if actions[action] > 0:
            actions[action] = actions[action] - 1


# --------------------------------- Voice Related Code ----------------------------------------------

def processOnlyAction(curAction):
    # print("Processing Only Action")
    if curAction != "on" and curAction != "off":
        for node in nodeList:
            if node.type == 3:
                for action in node.irActions:
                    if action == curAction:
                        sendIRRequest(node.id, curAction)
                        break


def processCommand(curAction, curDevice, curDestination):
    # print("Command Processing, " + curAction + curDevice + curDestination)
    for node in nodeList:
        if node.nodeName.lower() == curDevice and node.location.lower() == curDestination:
            # print("nodematched")
            if node.type == 2:
                if curAction == "on":
                    turnon(node.id)
                    # nodeList[node.id - 1].relayStat = 1
                    # sendNodeStat(node.id, 2)
                    # sendNodeStat(node.id, 0)
                    # sendNodeStat(node.id, 4)
                elif curAction == "off":
                    turnoff(node.id)
                    # nodeList[node.id - 1].relayStat = 0
                    # sendNodeStat(node.id, 2)
                    # sendNodeStat(node.id, 0)
                    # sendNodeStat(node.id, 4)
            elif node.type == 3:
                for action in node.irActions:
                    if action == curAction:
                        sendIRRequest(node.id, curAction)
                        break;
            break;


def processCommandWithoutDestination(curAction, curDevice):
    # print("Command Processing Without Destination")
    for node in nodeList:
        if node.nodeName.lower() == curDevice:
            if node.type == 2:
                if curAction == "on":
                    turnon(node.id)
                    # nodeList[node.id - 1].relayStat = 1
                    # sendNodeStat(node.id, 2)
                elif curAction == "off":
                    turnoff(node.id)
                    # nodeList[node.id - 1].relayStat = 0
                    # sendNodeStat(node.id, 2)
                time.sleep(1)
                sendNodeStat(node.id, 0)
            elif node.type == 3:
                for action in node.irActions:
                    if action == curAction:
                        sendIRRequest(node.id, curAction)
                        break;
            break;


def decodeVoiceCommand(command):
    stop_words = set(stopwords.words('english'))
    tempTokens = word_tokenize(command)
    tokens = list()
    for w in tempTokens:
        if w not in stop_words:
            tokens.append(w)
    print(tokens)
    curDevice = ""
    curDestination = ""
    curAction = ""
    gotDevice = False
    gotDestination = False
    gotAction = False
    shutdown = False

    for word in tokens:
        word = word.lower()
        if word in actions:
            curAction = word
            gotAction = True
            continue

        if ps.stem(word) in deviceList:
            word = ps.stem(word)
            curDevice = word
            gotDevice = True
            continue

        if ps.stem(word) in destination:
            word = ps.stem(word)
            curDestination = word
            gotDestination = True
            continue

        if word == "shutdown":
            shutdown = True
            continue

    if gotAction:
        if gotDevice:
            if gotDestination:
                processCommand(curAction, curDevice, curDestination)
            else:
                processCommandWithoutDestination(curAction, curDevice)
        else:
            processOnlyAction(curAction)
    elif shutdown:
        shutdownSequence()
    else:
        done = False
        # check in user defined routines, if not present, check default routines
        for routine in routineList:
            if routine["type"] == "voice":
                if routine["trigger"].lower() == command.lower():
                    doRoutineThread(routine)
                    done = True
        if not done:
            for defRoutineTuple in defaultRoutines:
                if command.lower() in defRoutineTuple:
                    doRoutineThread(defaultRoutines[defRoutineTuple])


def voiceListen():
    global triggerWord
    global device_id
    global sample_rate
    global chunk_size
    global waitingForCommand, processingTrigger, waitingForGoogleBool
    with sr.Microphone(device_index=device_id, sample_rate=sample_rate, chunk_size=chunk_size) as source:

        recognizer.adjust_for_ambient_noise(source, duration=1.5)
        recognizer.dynamic_energy_threshold = True
        #startLedThread(2)
        while True:

            # print("Waiting For Trigger Word")
            audio = recognizer.listen(source)
            processingTrigger = True
          #  gotTriggerIndication()

            try:
                initial = recognizer.recognize_google(audio)
                processingTrigger = False
                print("You Said: ", initial)
                if triggerWord in initial:
                    waitingForCommand = True
           #         startLedThread(0)
                    audio = recognizer.listen(source, timeout=5)
                    waitingForCommand = False

                    try:
                        waitingForGoogleBool = True
            #            waitingForGoogleResultsThread()
                        voiceCommand = recognizer.recognize_google(audio)
                        waitingForGoogleBool = False
                        print("Command: ", voiceCommand)
                        decodeVoiceCommand(voiceCommand)
                    except sr.UnknownValueError:
                        waitingForGoogleBool = False
                        print("Google Speech Recognition could not understand audio")

                    except sr.RequestError as e:
                        print("Could not onrequest results from GoogleSpeechRecognitionservice;{0}".format(e))
                        waitingForGoogleBool = False
             #           noInternetIndicationThread()
            except sr.UnknownValueError:
                processingTrigger = False
                print("Google Speech Recognition could not understand audio")

            except sr.RequestError as e:
                processingTrigger = False
                print("Could not request results from GoogleSpeechRecognitionservice;{0}".format(e))
              #  noInternetIndicationThread()
            except Exception as e:
                print("Listen Timeout")
                processingTrigger = False
                waitingForCommand = False


def micSetUp():
    mic_name = "USB Audio Device: - (hw:1,0)"
    # mic_name = "HDA Intel PCH: ALC295 Analog (hw:0,0)"
    global micSetBool
    global device_id
    mic_list = sr.Microphone.list_microphone_names()
    for i, microphone_name in enumerate(mic_list):
        if microphone_name == mic_name:
            device_id = i
            micSetBool = True
            # print("MIc Set")
            break


# ------------------------------code for led and shutdown --------------------------------------------------

"""def ledShow(times=0):
    GPIO.setmode(GPIO.BCM)
    p1 = GPIO.PWM(red, 1000)
    p1.start(0)
    p2 = GPIO.PWM(blue2, 1000)
    p2.start(0)
    p3 = GPIO.PWM(blue, 1000)
    p3.start(0)
    p4 = GPIO.PWM(red2, 1000)
    p4.start(0)

    if times == 0:
        exp = waitingForCommand
        # print("Using BOOL: " + str(exp))
    else:
        exp = times
        # print("using int, exp: " + str(exp))

    try:
        while exp:
            for dc in range(0, 101, 10):
                p1.ChangeDutyCycle(dc)
                time.sleep(0.01)
                p2.ChangeDutyCycle(dc)
                time.sleep(0.01)
                p3.ChangeDutyCycle(dc)
                time.sleep(0.01)
                p4.ChangeDutyCycle(dc)
                time.sleep(0.01)
            for dc in range(100, -1, -10):
                p1.ChangeDutyCycle(dc)
                time.sleep(0.01)
                p2.ChangeDutyCycle(dc)
                p3.ChangeDutyCycle(dc)
                time.sleep(0.01)
                p4.ChangeDutyCycle(dc)
                time.sleep(0.01)

            if isinstance(exp, bool):
                exp = waitingForCommand
            else:
                exp -= 1

        else:
            GPIO.output(red, GPIO.LOW)
            GPIO.output(blue2, GPIO.LOW)
            GPIO.output(red2, GPIO.LOW)
            GPIO.output(blue, GPIO.LOW)

    except KeyboardInterrupt:
        p1.stop()
        p2.stop()
        p3.stop()
        p4.stop()
        GPIO.cleanup()


def noInternetIndication():
    GPIO.setmode(GPIO.BCM)
    GPIO.output(red2, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(red2, GPIO.LOW)
    time.sleep(0.5)
    GPIO.output(red2, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(red2, GPIO.LOW)


def gotTriggerLed():
    GPIO.setmode(GPIO.BCM)
    while processingTrigger:
        GPIO.output(red, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(red, GPIO.LOW)
        time.sleep(0.5)
    else:
        GPIO.output(red, GPIO.LOW)


def waitingForGoogle():
    GPIO.setmode(GPIO.BCM)
    while waitingForGoogleBool:
        GPIO.output(red, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(red, GPIO.LOW)
        GPIO.output(blue, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(blue, GPIO.LOW)
        GPIO.output(red2, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(red2, GPIO.LOW)
        GPIO.output(blue2, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(blue2, GPIO.LOW)


def checkForShutdown():
    GPIO.setmode(GPIO.BCM)
    while True:
        if GPIO.input(btn) == GPIO.LOW:
            GPIO.output(red, GPIO.HIGH)
            time.sleep(1)
            shutdownSequence()
        time.sleep(2)
"""

# ---------------------------- Text To Speech -----------------------------------------------------------
def setUpTTS():
    global voice, audio_config, ttsClient
    ttsClient = texttospeech.TextToSpeechClient()
    voice = texttospeech.types.VoiceSelectionParams(language_code='en-US',
                                                    ssml_gender=texttospeech.enums.SsmlVoiceGender.FEMALE)
    audio_config = texttospeech.types.AudioConfig(audio_encoding=texttospeech.enums.AudioEncoding.MP3)


def speakThread(string):
    global dateSpeaking, tempSpeaking
    synthesis_input = texttospeech.types.SynthesisInput(text=string)
    response = ttsClient.synthesize_speech(synthesis_input, voice, audio_config)
    with open('tempspeak.mp3', 'wb') as out:
        out.write(response.audio_content)
        print("Written")

    if dateSpeaking:
        speakFile("date.mp3")
        dateSpeaking = False
    elif tempSpeaking:
        speakFile("temperature.mp3")

    playsound('tempspeak.mp3')

    if tempSpeaking:
        playsound(userData["temperatureUnit"] + ".mp3")
        tempSpeaking = False


# ------------------------------------- Weather Concerning ---------------------------------------------------

def setUpOWM():
    global owm
    owm = pyowm.OWM('dd61e86e90664667777f2cee9e1ec09c')


def getTemperature():
    global tempSpeaking
    weatherAt = owm.weather_at_place(userData["city"] + ", " + userData["country"])
    w = weatherAt.get_weather()
    tempSpeaking = True
    return w.get_temperature(userData["temperatureUnit"])['temp']


def speakTemperature():
    speakThread(str(getTemperature()) + 'Degree' + userData["temperatureUnit"])
    speakFile("temperature.mp3")


def speakDateAndTime():
    time = datetime.datetime.now()
    month = time.strftime("%b")
    today = date.today()
    day = today.day
    global dateSpeaking

    """if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1]
    """
    pm = False
    hour = time.hour
    if hour > 11:
        pm = True
    hour %= 12
    if hour == 0:
        hour = 12

    string = str(day) + " " + month + str(hour) + ":" + str(time.minute)
    if pm:
        string += "pm"
    else:
        string += "am"
    print(string)

    dateSpeaking = True
    speakThread(string)


def speakFile(filename):
    playsound(filename)


# ---------------------------------- JSON Getters Setters ---------------------------------------------------------

def getUserData():
    global userData
    try:
        file = open("userdata.json", "r")
        userData = json.load(file)
        file.close()
    except Exception as e:
        print(e)


def saveUserData():
    global userData
    try:
        file = open("userdata.json", "w")
        json.dump(userData, file)
        file.close()
    except Exception as e:
        print(e)


def saveRoutines():
    global routineList
    try:
        file = open("routines.json", "w")
        json.dump(routineList, file)
        file.close()
    except Exception as e:
        print(e)


def getRoutines():
    global routineList
    try:
        file = open("routines.json", "r")
        routineList = json.load(file)
        file.close()
    except Exception as e:
        print(e)


# ------------------------------ Thread Starters ----------------------------------------------------------
def modifyRoutineThread(routine):
    thread = threading.Thread(target=modifyRoutine, args=[routine])
    thread.start()


def checkForScheduledRoutinesThread():
    thread = threading.Thread(target=checkForScheduledRoutines)
    thread.start()


def delRoutineThread(routineId):
    thread = threading.Thread(target=delRoutine, args=[routineId])
    thread.start()


def doRoutineThread(routine):
    thread = threading.Thread(target=doRoutine, args=[routine])
    thread.start()


def speak(string):
    thread = threading.Thread(target=speakThread, args=[string])
    thread.start()


def requestThread(clientIP, port, message):
    reqThread = threading.Thread(target=sendRequest, args=[clientIP, port, message])
    reqThread.start()


def sendJsonPostThread(clientIP, port, message, data):
    reqThread = threading.Thread(target=sendJsonPost, args=[clientIP, port, message, data])
    reqThread.start()


def startServerThread():
    serverThread = threading.Thread(target=startServer)
    serverThread.start()
    time.sleep(1)
    while not serverStart:
        pass

    #configureExistingNodes()


def startBackgroundCheck():
    while not serverStart:
        pass

    thread = threading.Thread(target=backgroundCheckOfClients)
    thread.start()


"""def startLedThread(times=0):
    thread = threading.Thread(target=ledShow, args=[times])
    thread.start()


def gotTriggerIndication():
    thread = threading.Thread(target=gotTriggerLed)
    thread.start()


def waitingForGoogleResultsThread():
    thread = threading.Thread(target=waitingForGoogle)
    thread.start()


def noInternetIndicationThread():
    thread = threading.Thread(target=noInternetIndication)
    thread.start()


def checkForShutdownThread():
    thread = threading.Thread(target=checkForShutdown)
    thread.start()
"""

# -------------------------------------- Initial Calling -----------------------------------------------------------

getUserData()
getRoutines()
print(routineList)
print(len(routineList))
for i in routineList:
    print(i)
setUpDefaultRoutines()
startServerThread()
#checkForShutdownThread()
startBackgroundCheck()
setUpTTS()
setUpOWM()

while not micSetBool:
    micSetUp()
    time.sleep(0.5)
if micSetBool:
    voiceListen()
