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

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://mail.google.com/']


def printInfo(string, keywords= []):
    keywords = ["INR", "credited" ,"to", "A/c", "no.", "on", "at", "Info-", "Avl", "Bal-", "Axis", "Bank"]
    positions = []
    last = 0
    words = string.split(" ")

    n = len(words)

    for i in range(n):
        # print("last:\t", last)
        if (last < len(keywords)) and (words[i] == keywords[last]):
            last += 1
            positions.append(i)

    for i in range(len(positions)-1):
        w = " ".join(words[positions[i]+1:positions[i+1]])
        w = w.strip()

        if w != "":
            print(w)

    print()


def getMessage(service ,threadId = None):
    msg = service.users().messages().get(userId = "me", id = threadId).execute()

    # print("msg:\t", msg)

    message = msg["payload"]["parts"][0]["body"]["data"]
    msg_text = base64.urlsafe_b64decode(message)

    soup = BeautifulSoup(msg_text, "lxml")
    soup = soup.find("body")

    msg_text = soup.get_text().strip()
    # print(msg_text)

    return (msg_text)

def getMessageIds(service):
    nextPage = None
    c = 0
    threads = []

    while(c ==0 or nextPage):
        c += 1
        results = service.users().messages().list(pageToken = nextPage, q = "from: alerts@axisbank.com", userId = "me").execute()
        # print(json.dumps(results, indent = 4))
        messages = results["messages"]
        for i in messages:
            threads.append(i["id"])
        nextPage = results.get("nextPageToken", None)

    return threads

def main():
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
        service = build('gmail', 'v1', credentials=creds)
        msgIds = getMessageIds(service)
        k = 0
        for i in range(100):

            if(k == 3):
                break

            msg = getMessage(service, msgIds[i])
            # print(msg)
            msg = msg.split("\n")[0]
            

            if("credited" in msg):
                continue
                # k = k+1
                printInfo(msg)

            else:
                print(msg.split("\n")[0], "\n\n")
                k += 1
                # pass

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()