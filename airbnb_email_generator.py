from __future__ import print_function

import re
import base64
from email.mime.text import MIMEText
import os.path
import datetime
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
# SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SCOPES = ["https://mail.google.com/"]


def format_date(check_in_date, formatted_checkin_date):
    spanish_months_mapping = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Junio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre",
    }

    spanish_days_mapping = {
        0: "Lunes",
        1: "Martes",
        2: "Miercoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sabado",
        6: "Domingo",
    }

    weekday_spanish = spanish_days_mapping[formatted_checkin_date.weekday()]
    month_spanish = spanish_months_mapping[formatted_checkin_date.month]
    message_date = (
        f"el {weekday_spanish} {formatted_checkin_date.day} de {month_spanish}"
    )
    return message_date


def create_message(sender, to, subject, message_text):
    """Create a message for an email.

    Args:
      sender: Email address of the sender.
      to: Email address of the receiver.
      subject: The subject of the email message.
      message_text: The text of the email message.

    Returns:
      An object containing a base64url encoded email object.
    """
    message = MIMEText(message_text)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes())
    raw = raw.decode()
    return {"raw": raw}


def send_message(service, user_id, message):
    """Send an email message.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      message: Message to be sent.

    Returns:
      Sent Message.
    """
    try:
        message = service.users().messages().send(userId="me", body=message).execute()
        return message
    except Exception as e:
        print("An error occurred: %s" % e)

##I need to obtain ONLY the incoming reservations
##Read the API documentation. 
def retrieve_message_ids(service, creds):
    label_id = "Label_8156068733455595866" #Emails tagged with the "Airbnb" label.

    """Retrieve message ids associated with 
       the label_id from Gmail user's mailbox. 
    Args: Service and credentials
    Returns: Dictionary with message ids and threadIds. 
    """
    try: 
        return service.users().messages().list(userId="me", labelIds=label_id).execute()
    except: 
        pass
        ##Implement logging errors

    #{'messages': [{'id': '184cd5fad0646002', 'threadId': '184cd5fad0646002'}, 
    #              {'id': '184c4aa6c43cae4f','threadId': '184c4aa6c43cae4f'},
    #              {'id': '184c46e0c1daada9', 'threadId': '184c46e0c1daada9'}

def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # EA comment. Client ID definition:
            # To authenticate as an end user and access user data in your app, 
            # you need to create one or more OAuth 2.0 Client IDs.
            # A client ID is used to identify a single app to Google's OAuth 
            # servers.
            # If your app runs on multiple platforms, 
            # you need to create a separate client ID for each platform.
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret_1.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        airbnb_mails = retrieve_message_ids(service, creds)
        ##It seems I can use this query:
        ##airbnb after:2022/12/10 before:2022/12/17
        ##Check emails from the last 10 days
        ##To avoid sending an email twice for a reservation check 
        ##if you can check the "sent emails" folder.
        ##Can I create a class out of this?
        ##Another use case: Write a review could be a trigger to communicate to the 
        ##cleaning person that it needs to go.

        pending_reservations = []
        completed_reservations = []
        currentYear = datetime.datetime.today().year
        currentDate = datetime.datetime.today()

        message = ""
        # Read all lines from the control file.
        _ = open("complete_reservations.txt", "r+")
        completed_reservations = _.readlines()
        completed_reservations = [
            reservations.strip("\n") for reservations in completed_reservations
        ]
        _.close()

        for email in airbnb_mails["messages"]:
            # Pull the details for each specific email:
            results = (
                service.users().messages().get(
                    userId="me", id=email["id"]).execute()
            )
            # Subject: Reservation confirmed - Edward Alvarez arrives Feb 15
            subject = results["payload"]["headers"][20]["value"]
            if "Reservation confirmed" in subject:
                guest_name = re.search(
                    "Reservation confirmed - (.+?)arrives (.+)", subject
                ).group(1)
                check_in_date = re.search(
                    "Reservation confirmed - (.+?)arrives (.+)", subject
                ).group(2)
                formatted_checkin_date = datetime.datetime.strptime(
                    check_in_date + str(currentYear), "%b %d%Y"
                )
                reservation_name = guest_name + \
                    check_in_date + " " + str(currentYear)
                message_date = format_date(
                    check_in_date, formatted_checkin_date)
                if reservation_name not in completed_reservations:
                    print(
                        "Guest not in the control file, will need to send email to Soha admins:"
                    )
                    message = f"""Hola!\n El huesped {guest_name}se va a alojar en uno de nuestros apartamentos {message_date}.\nGracias!\n Atentamente, Lorena Tejada"""

                    # email_message = create_message(sender = "edwardalvarezm@gmail.com",
                    #                               to="edwardalvarezm@gmail.com",
                    #                               subject="Reservas Soha Panorama Apartamentos B2 y D6",
                    #                               message_text = message)
                    # send_message(service, user_id="me", message = email_message)

                    with open("complete_reservations.txt", "a") as reservations:
                        reservations.write(reservation_name + "\n")

        # send_message(service, user_id="me", message = email_message)

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
