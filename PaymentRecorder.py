from __future__ import print_function
import os.path
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time

class PaymentRecorder:
    def getMessageIds(self):
        nextPage = None
        c = 0
        threads = []

        count = self.db["last_access"].count_documents({"_id": 1})
        last_access = int(time.time())

        q = "from: alerts@axisbank.com"

        if(count == 0):
            # insert current at last accessed
            db = self.db["last_access"].insert_one({"_id": 1, "last_time": int(time.time())})
        else:
            res = self.db["last_access"].find_one({})
            # print(res)
            last_access = res["last_time"]
            q = q + " after: " + str(last_access)
            self.db["last_access"].update_one({"_id": 1}, { "$set" : {"last_time": int(time.time())} })

        # q = q + str(last_access)
        print("q:\t" + q)
        while(c ==0 or nextPage):
            c += 1
            results = self.service.users().messages().list(pageToken = nextPage, q = q, userId = "me").execute()
            # print("results:\t", results)
            messages = results.get("messages", None)

            if messages is None:
                print("No new mails")
                return None

            for i in messages:
                threads.append(i["id"])
            nextPage = results.get("nextPageToken", None)

        return threads

    def getMessage(self, threadId):
        msg = self.service.users().messages().get(userId = "me", id = threadId).execute()

        # print("msg:\t", msg)

        message = msg["payload"]["parts"][0]["body"]["data"]
        msg_text = base64.urlsafe_b64decode(message)

        soup = BeautifulSoup(msg_text, "lxml")
        soup = soup.find("body")

        msg_text = soup.get_text().strip()
        # print(msg_text)

        return (msg_text)


    def getCreditInfo(self, string):
        infos = []


        msg = "INR {} credited to A/c no. {} on {} at {} IST. Info- {}Avl Bal- INR {} - Axis Bank"
        if "Info:" in string:
            msg = "INR {} credited to A/c no. {} on {} at {} IST. Info: {}Avl Bal- INR {} - Axis Bank"

        if string.startswith("Dear Customer,"):
            msg = "Dear Customer, INR {} credited to A/c no. {} on {} at {} IST. Info- {}Avl Bal- INR {} - Axis Bank"

            if "Info:" in string:
                msg = "Dear Customer, INR {} credited to A/c no. {} on {} at {} IST. Info: {}Avl Bal: INR {} - Axis Bank"

        keywords = msg.split("{}")

        n = len(keywords)

        last = string.find(keywords[0]) + len(keywords[0])

        for i in range(1, n):
            next = string.find(keywords[i])
            if next == -1:
                return
            info = ''.join(string[last : next])
            infos.append(info)
            last = next + len(keywords[i])

        # print("\n\n\n")
        # return infos
        print("============Credit=========")
        print("\n".join(infos), "\n\n")
        self.db["Credits"].insert_one({"_id" : infos[4], "amount": infos[0], "pay_time" : infos[2]+infos[3], "balance" : infos[5]})

    def getDebitInfo(self, string):
        infos = []

        msg = "Dear Customer, We wish to inform you that INR {} has been debited from your A/c no. {} on {} at {} Available balance: INR {} Please"

        if not msg.startswith("Dear Customer,"):
            msg = "INR {} debited to A/c no. {} on {} at {} IST. Info- {}Avl Bal- INR {} - Axis Bank"
            



        keywords = msg.split("{}")
        # print(keywords)

        n = len(keywords)

        last = string.find(keywords[0]) + len(keywords[0])

        for i in range(1, n):
            next = string.find(keywords[i])
            info = string[last : next]
            infos.append(info)
            last = next + len(keywords[i])

        # print("\n\n\n")
        # return infos
        print("============Debit=========")
        print("\n".join(infos), "\n\n")
        self.db["Debits"].insert_one({"_id" : infos[3], "amount": infos[0], "pay_time" : infos[2], "balance" : infos[4]})

    def __init__(self):
        SCOPES = ['https://mail.google.com/']
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        try:
            self.service = build('gmail', 'v1', credentials=creds)

        except HttpError as error:
            print(f'An error occurred: {error}')

        # self.db = Database("PaymentsInfo")
        data = json.load(open("mongo_info.json"))
        self.client = MongoClient(data["url"])
        self.db = self.client["PaymentsInfo"]

    def start(self):
        msgIds = self.getMessageIds()

        if msgIds is None:
            return

        for i in range(len(msgIds)):

            msg = self.getMessage(msgIds[i])
            # print(msg)
            msg = msg.split("\n")[0]
            

            if("credited" in msg):
                # print("\n\n===credited===")
                res = self.getCreditInfo(msg)
                # print("\n".join(res))

            else:
                # print("\n\n===Debited===")
                res = self.getDebitInfo(msg)
                # print("\n".join(res))


p1 = PaymentRecorder()
p1.start()