import json
import requests
import urllib3
from http.server import BaseHTTPRequestHandler, HTTPServer
from flask import Flask
from flask import request
import threading


myList = [
    {
        "id": "1",
        "type": "voice",
        "trigger": "All on",
        "actions": {
            "turnon": {
                "nodeName": "Light",
                "nodeLocation": "Kitchen",
                "delay": "0"
            },
            "turnoff": {
                "nodeName": "Light",
                "nodeLocation": "Kitchen",
                "delay": "0"
            },
            "iraction": {
                "nodeName": "TV",
                "nodeLocation": "Bedroom",
                "task": "ON",
                "delay": "2"
            }
        }
    }
]

url = "http://localhost:8080/"
headers = {'content-type':'application/json'}
print(json.dumps(myList))
print(type(json.dumps(myList)))
res = requests.post(url, data=(json.dumps(myList) + "\nEND\n"), headers=headers)
print(res)

class CustomHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        content_len = int(self.headers.get('Content-Length'))
        print(content_len)
        post_body = self.rfile.read(content_len)
        print(type(post_body))
        print(post_body)
        string = post_body.decode('utf-8')
        print(string)
        myList = list(string)
        print(type(myList))
        print(myList)
def startServer():
    global serverStart
    global server
    try:
        server = HTTPServer(('', 8080), CustomHandler)
        serverStart = True
        #print("Starting Server: ", str(serverStart))
        server.serve_forever()
    except Exception as e:
        print("Error Starting Server: {0}".format(e))

#startServer()
app = Flask(__name__)
@app.route('/postjson', methods=['GET', 'POST'])
def postJsonHandler():
    if request.method == 'POST':
        user = request.args.get('data')
        print(user)
        content = request.get_json()
        print(content)
        print(type(content))
        print(request.environ['REMOTE_ADDR'])

    elif request.method == 'GET':
        print("GET Received")
        user = request.args.get('data')
        print(user)
        user = user.split('$')
        user.pop()
        printThread = threading.Thread(target=printThis, args=[user])
        printThread.start()

    return "HTTP/1.1 200 OK\n\n"


def printThis(string):
    for i in string:
        print(i)


app.run('localhost', 8080)
print("Post run ----------------------------")

