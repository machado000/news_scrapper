"""
This driver module is part of an ETL project (extract, transform, load).
It's meant to be imported by main.py script and used to send e-mails using Gmail for Workspace
v.2023-07-29
"""
from __future__ import print_function
import base64

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from ._drv_hashicorp_vault import HashiVaultClient


class GmailSender:
    def __init__(self, refresh_token_json):
        self.refresh_token_json = refresh_token_json
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        self.creds = Credentials.from_authorized_user_info(self.refresh_token_json, self.SCOPES)
        self.service = build('gmail', 'v1', credentials=self.creds)

    def create_message(self, sender, to, subject, *message_texts):
        msg = MIMEMultipart()
        msg['from'] = sender
        msg['to'] = to
        msg['subject'] = subject

        for message_text in message_texts:
            msg.attach(MIMEText(message_text, 'html'))

        return {'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode()}

    def send_message(self, user_id, message):
        try:
            message = (self.service.users().messages().send(userId=user_id, body=message).execute())
            print('Message Id: %s' % message['id'])
            return message
        except Exception as error:
            print(f"ERROR - {error}")


def main():

    hashivault_secret = "gcp-gmail-oauth-refresh-token"
    _, metadata = HashiVaultClient().get_secret(hashivault_secret)
    refresh_token_json = metadata

    email_service = GmailSender(refresh_token_json)

    from_address = '"HOLOS Company Report" <tool@holos.company>'
    to_addresses = "machado000@gmail.com, joao.brito@holos.company"  # Use "," for multiple addresses
    subject = "TEST - Email Subject"

    html_content_1 = '''
    <body>
    <h1 id="header-1">Header 1</h1>
        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore \
            et dolore magna aliqua.</p>
        <h2 id="header-2">Header 2</h2>
        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore \
            et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut \
            aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse \
            cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in \
            culpa qui officia deserunt mollit anim id est laborum.</p>
    </body>
    '''
    html_content_2 = "<table><thead><tr><th>Coluna 1</th><th>Coluna 2</th><th>Coluna 3</th></tr></thead><tbody><tr><td>Item 1</td><td>123</td><td>789</td></tr><tr><td>Item 2</td><td>456</td><td>012</td></tr></tbody></table>"  # noqa

    message_obj = email_service.create_message(from_address, to_addresses, subject, html_content_1, html_content_2)

    email_service.send_message(user_id='tool@holos.company', message=message_obj)


if __name__ == "__main__":
    main()
