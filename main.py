
import http.server
import threading
from urllib.parse import urlparse
from threading import Lock
import requests
import time
import speech_recognition as sr
import os
import nltk
from nltk.tokenize import word_tokenize

nltk.download('punkt')


port = 8080
appNodeId = 0
maxNodes = 15
lock = Lock()
triggerWord = "Jarvis"

deviceList = dict()
destination = dict()
actions = dict()
helper = ["switch", "turn", "launch", "start"]

class Node:
    nodeCount = 0

    @classmethod
    def initiateAsNonIr(cls, self, ip, nodeName, type, location, relayStat = 0):
        self.ip = ip
        self.nodeName = nodeName
        self.type = type
        self.relayStat = relayStat
        self.conStat = 1
        self.irActions = set()
        self.notifiedAppofDisconnect = False
        self.location = location

    @classmethod
    def initiateAsIr(cls, self, ip, nodeName, type, irActions, location, relayStat = 0):
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

    def __init__(self):
        print("Empty Node Created")


nodeList = []


def printNodeList():

    print("IP      ID Name     Type Cstat Rstat Location Actions")
    for node in nodeList:
        print(node.ip + " " + str(node.id) + " " + node.nodeName + " " + str(node.type) + " " + str(node.conStat) + " " + str(node.relayStat) + " " + node.location, end=" ")
        for i in node.irActions:
            print(i, end=", ")

    print("App node ID: ", appNodeId)
    print("Node Count: ", Node.nodeCount)


def forwardRequest(toId, parameters):
    message = "client@esp$" + parameters[1] + "$1$"
    for i in range(3, 7):
        message += parameters[i] + "$"
    requestThread(nodeList[toId-1].ip, port, message)


def sendNodeListToApp():
    for node in nodeList:
        if node.id != appNodeId:
            sendNodeStat(node.id, 0)
            time.sleep(1)
    print("Node List Sent!")


def sendNodeStat(nodeId, destinationType):
    global nodeList
    global appNodeId
    node = nodeList[nodeId - 1]
    toIP = ""
    if destinationType == 0:
        toIP = nodeList[appNodeId - 1].ip
    else:
        toIP = node.ip
    message = "client@esp$action@stat$" + str(node.type) + "$" + str(node.id) + "$" + node.nodeName

    if node.type == 3:
        hasIrAction = False
        for i in node.irActions:
            message += "_" + i.upper()
            hasIrAction = True
        if hasIrAction:
            message += "_"
    message += "$" + str(node.conStat) + "$" + str(node.relayStat) + "$" + node.location + "$"
    requestThread(toIP, port, message)


def setNodeStat(parameters):
    global nodeList
    global appNodeId
    nodeId = int(parameters[3])
    index = nodeId - 1

    if index < Node.nodeCount and index >=0:
        removeNameFromDict(nodeList[index].nodeName)
        removeLocationFromDict(nodeList[index].location)
        nodeList[index].relayStat = int(parameters[6])
        nodeList[index].conStat = int(parameters[5])
        nodeList[index].location = parameters[7]
        temp = parameters[4]
        tempName = temp

        i = tempName.find("_")

        if i != -1:
            nodeList[index].irActions.clear()
            tempName = tempName[:i]
            i+=1
            temp = temp[i:]
            startI = 0
            endI = 0
            while startI < len(temp):
                endI = temp.find("_", startI)
                nodeList[index].irActions.add(temp[startI:endI])
                startI = endI + 1
        else:
            nodeList[index].irActions.clear()
        nodeList[index].nodeName = tempName
        addNodeLocationinDict(parameters[7])
        addNodeNameinDict(tempName)

    printNodeList()
    if int(parameters[2]) == 0:
        sendNodeStat(nodeId, 2)
    elif appNodeId != 0:
        sendNodeStat(nodeId, 0)

def printDictionaries():
    print("\n--------------Printing Dictionaries--------------------")
    for device in deviceList:
        print(device + ":" + str(deviceList[device]))
    for location in destination:
        print(location + ":" + str(destination[location]))
    for action in actions:
        print(action + ":" + str(actions[action]))

def addNodeNameinDict(name):
    print("\nAdding Name in Dict")
    global deviceList
    name = name.lower()
    if name in deviceList:
        deviceList[name] = deviceList[name] + 1
    else:
        deviceList[name] = 1

    printDictionaries()


def addNodeLocationinDict(location):
    print("\nAdding Location in Dict")
    global destination
    location = location.lower()
    if location in destination:
        destination[location] = destination[location] + 1
    else:
        destination[location] = 1

    printDictionaries()


def addNodeActionsinDict(actionSet):
    print("\nAdding Action Set in Dict")
    global actions

    for action in actionSet:
        action = action.lower()
        if action in actions:
            actions[action] = actions[action] + 1
        else:
            actions[action] = 1

    printDictionaries()


def removeNameFromDict(name):
    print("\nRemoving Node Name from Dict")
    global deviceList

    if name in deviceList:
        if deviceList[name] > 0:
            deviceList[name] = deviceList[name] - 1

    printDictionaries()


def removeLocationFromDict(location):
    print("\nRemoving Node Location from Dict")
    global destination

    if location in destination:
        if destination[location] > 0:
            destination[location] = destination[location] - 1

    printDictionaries()


def removeActionFromDict(action):
    print("\nRemoving Node Action from Dict")
    global actions

    if action in actions:
        if actions[action] > 0:
            actions[action] = actions[action] - 1

    printDictionaries()


def nodeConfig(clientIP, parameters):
    global nodeList
    global appNodeId
    print("Node Config")

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
        print("i: ", i)
        tempSet = set()
        if i != -1:
            nodeName = nodeName[:i]
            i+=1
            temp = parameters[4][i:]
            startI = 0
            endI = 0
            while startI < len(temp):
                endI = temp.find("_", startI)
                tempSet.add(temp[startI:endI].lower())
                startI = endI + 1

        newNode.initiateAsIr(newNode, clientIP, nodeName, type, tempSet, parameters[7], int(parameters[6]))

    print(newNode.nodeName)
    print(newNode.type)
    print(newNode.conStat)

    added = False
    for node in nodeList:
        if node.ip == clientIP and type == node.type:
            newNode.id = node.id
            nodeList[newNode.id-1] = newNode
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

    if added:
        addNodeNameinDict(newNode.nodeName)
        addNodeLocationinDict(newNode.location)
        if newNode.type == 2:
            addNodeActionsinDict({"on", "off"})
        elif newNode.type == 3:
            addNodeActionsinDict(newNode.irActions)
    message = "client@esp$action@config$1$" + str(newNode.id) + "$ESP$" + str(newNode.conStat) + "$" + str(newNode.relayStat) + "$" + newNode.location + "$"
    requestThread(clientIP, port, message)
    print("New Node ID: ", newNode.id)
    printNodeList()

    if type != 0 and appNodeId != 0:
        sendNodeStat(newNode.id, 0)
    elif type == 0:
        appNodeId = newNode.id




def decodeParameters(clientIP, parameters):
    if parameters[1] == "action@stat":
        setNodeStat(parameters)
    elif parameters[1] == "action@config":
        print("Got Config, current Node Count: ", Node.nodeCount)
        if Node.nodeCount < maxNodes:
            nodeConfig(clientIP, parameters)
        else:
            print("Node List Full")
    elif parameters[1] == "action@getnodelist":
        print("Node List Request Received")
        sendNodeListToApp()
    elif parameters[1] == "action@recordIR" or parameters[1] == "action@saveIR" or parameters[1] == "action@task" or parameters[1] == "action@remove":
        print("IR Request")
        requestNodeId = int(parameters[3])
        if requestNodeId > 0 and requestNodeId <= Node.nodeCount:
            print("Forwarding Request")
            forwardRequest(requestNodeId, parameters)


def configureExistingNodes():
    existingIPList = getExistingNodeList()

    message = "client@esp$action@reconfig$1$0$ESP$0$0$ESP"
    for ip in existingIPList:
        requestThread(ip, port, message)
        time.sleep(1)


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

"""def backgroundCheckOfClients():
    global nodeList

    while True:
        try:
            ipList = getExistingNodeList()

            print("Current IPs:")
            for ip in ipList:
                print(ip)

            for node in nodeList:
                if node.type != 0
                    present = False
                    for ip in ipList:
                        if node.ip == ip:
                            present = True
                            break;
                    if not present:
                        nodeList[node.id - 1].conStat = 0
                        if not nodeList[node.id - 1].notifiedAppofDisconnect:
                            sendNodeStat(node.id, 0)
                            nodeList[node.id - 1].notifiedAppofDisconnect = True

            printNodeList()
        except Exception as e:
            print("Exception in Background Client Check: {0}".format(e))
        time.sleep(100)

def startClientListCheckThread():
    thread = threading.Thread(target=backgroundCheckOfClients())
    thread.start()
"""
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
        #decodeParameters(self.client_address[0], parameters)


def startServer():
    global serverStart
    try:
        server = http.server.HTTPServer(('', port), CustomHandler)
        print("Starting Server")
        serverStart = True
        print(serverStart)
        server.serve_forever()
    except Exception as e:
        print("Error Starting Server: {0}".format(e))


def startServerThread():
    serverThread = threading.Thread(target=startServer)
    serverThread.start()
    time.sleep(3)
    print(serverStart)
    if serverStart:
        configureExistingNodes()


def requestThread(clientIP, port, message):
    reqThread = threading.Thread(target=sendRequest, args=[clientIP, port, message])
    reqThread.start()

def sendRequest(clientIP, port, message):
    i = 2
    while i!=0:
        lock.acquire()
        url = "http://" + clientIP + ":" + str(port) + "/message?data=" + message
        print("Connecting URL: ", url)
        try:
            res = requests.get(url)
            print("Res Code: ", res.status_code)
            lock.release()
            if (res.status_code != 200):
                time.sleep(2)
                print("Trying Again....")
            else:
                break
        except Exception as e:
            lock.release()
            print("Request Exception: {0}".format(e))
            print("Trying Again....")
            time.sleep(2)

        i -= 1


def sendIRRequest(nodeId, action):
    index = nodeId - 1
    message = "client@esp$action@task$1$" + nodeList[index].id + "$" + nodeList[index].nodeName + "$" + nodeList[index].conStat + "$" + action + "$" + nodeList[index].location
    requestThread(nodeList[index].ip, port, message)
    print("Sent IR Request to: ", nodeList[index].nodeName)

def processOnlyAction(curAction):
    print("Processing Only Action")
    if curAction != "ON" and curAction != "OFF":
        for node in nodeList:
            if node.type == 3:
                for action in node.irActions:
                    if action == curAction:
                        sendIRRequest(node.id, curAction)


def processCommand(curAction, curDevice, curDestination):
    print("Command Processing")
    for node in nodeList:
        if node.nodeName.lower() == curDevice and node.location.lower() == curDestination:
            if node.type == 2:
                if curAction.lower() == "on":
                    nodeList[node.id - 1].relayStat = 1
                    sendNodeStat(node.id, 2)
                    sendNodeStat(node.id, 0)
                elif curAction.lower() == "off":
                    nodeList[node.id - 1].relayStat = 0
                    sendNodeStat(node.id, 2)
                    sendNodeStat(node.id, 0)
            elif node.type == 3:
                for action in node.irActions:
                    if action.lower() == curAction.lower():
                        sendIRRequest(node.id, curAction)
                        break;
            break;


def processCommandWithoutDestination(curAction, curDevice):
    print("Command Processing Without Destination")
    for node in nodeList:
        if node.nodeName.lower() == curDevice:
            if node.type == 2:
                if curAction == "on":
                    nodeList[node.id - 1].relayStat = 1
                    sendNodeStat(node.id, 2)
                elif curAction == "off":
                    nodeList[node.id - 1].relayStat = 0
                    sendNodeStat((node.id, 2))
            elif node.type == 3:
                for action in node.irActions:
                    if action.lower() == curAction:
                        sendIRRequest(node.id, curAction)
                        break;
            break;


def decodeVoiceCommand(command):
    tokens = word_tokenize(command)
    print(tokens)
    print(type(tokens))
    curDevice = ""
    curDestination = ""
    curAction = ""
    gotDevice = False
    gotDestination = False
    gotAction = False

    for word in tokens:
        word = word.lower()
        if word in actions:
            curAction = word.upper()
            gotAction = True
            continue

        if word in deviceList:
            curDevice = word
            gotDevice = True
            continue

        if word in destination:
            curDestination = word
            gotDestination = True
            continue

    if gotAction:
        if gotDevice:
            if gotDestination:
                processCommand(curAction, curDevice, curDestination)
            else:
                processCommandWithoutDestination(curAction, curDevice)
        else:
            processOnlyAction(curAction)


#mic_name = "USB Audio Device: - (hw:1,0)"
mic_name = "HDA Intel PCH: ALC295 Analog (hw:0,0)"
sample_rate = 48000
chunk_size = 2048
recognizer = sr.Recognizer()
mic_list = sr.Microphone.list_microphone_names()
micrSet = False
serverStart = False

for i, microphone_name in enumerate(mic_list):
    if microphone_name == mic_name:
        device_id = i
        micrSet = True
        break

def voiceListen():
    global triggerWord
    with sr.Microphone(device_index=device_id, sample_rate=sample_rate, chunk_size=chunk_size) as source:

        recognizer.adjust_for_ambient_noise(source, duration=1.5)
        print(recognizer.energy_threshold)
        while True:

            print("Waiting For Trigger Word")
            audio = recognizer.listen(source)
            print("Listen Done 1")

            try:
                initial = recognizer.recognize_google(audio)
                print("You Said: ", initial)
                if triggerWord in initial:
                    #recognizer.adjust_for_ambient_noise(source, duration=1)
                    print("Waiting For Command");
                    audio = recognizer.listen(source)
                    print("Got Command")

                    try:
                        voiceCommand = recognizer.recognize_google(audio)
                        print("Command: ", voiceCommand)
                        decodeVoiceCommand(voiceCommand)
                    except sr.UnknownValueError:
                        print("Google Speech Recognition could not understand audio")

                    except sr.RequestError as e:
                        print("Could not request results from GoogleSpeechRecognitionservice;{0}".format(e))
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")

            except sr.RequestError as e:
                print("Could not request results from GoogleSpeechRecognitionservice;{0}".format(e))


startServerThread()
#startClientListCheckThread()
#if micrSet:
    #has mic
  #  print("Got Mic")
    #voiceListen()
#else:
   # print("Couldnt Find USB Microphone")
#startVoiceRecognitionThread()



