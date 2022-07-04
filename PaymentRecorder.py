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


class PaymentRecorder:
    def getMessageIds(self):
        nextPage = None
        c = 0
        threads = []

        while(c ==0 or nextPage):
            c += 1
            results = self.service.users().messages().list(pageToken = nextPage, q = "from: alerts@axisbank.com", userId = "me").execute()
            messages = results["messages"]
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

        msg = "INR {} credited to A/c no. {} on {} at {}. Info- {}Avl Bal- INR {} - Axis Bank"

        keywords = msg.split("{}")

        n = len(keywords)

        last = string.find(keywords[0]) + len(keywords[0])

        for i in range(1, n):
            next = string.find(keywords[i])
            info = ''.join(string[last : next])
            infos.append(info)
            last = next + len(keywords[i])

        # print("\n\n\n")
        return infos

    def getDebitInfo(self, string):
        infos = []

        msg = "Dear Customer, We wish to inform you that INR {} has been debited from your A/c no. {} on {} at {} Available balance: INR {} Please"

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
        return infos

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

    def start(self):
        msgIds = self.getMessageIds()
        for i in range(10):

            msg = self.getMessage(msgIds[i])
            # print(msg)
            msg = msg.split("\n")[0]
            

            if("credited" in msg):
                print("\n\n===credited===")
                res = self.getCreditInfo(msg)
                print("\n".join(res))

            else:
                print("\n\n===Debited===")
                res = self.getDebitInfo(msg)
                print("\n".join(res))


p1 = PaymentRecorder()
p1.start()