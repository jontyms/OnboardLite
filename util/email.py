import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import commonmark

from util.options import Options

options = Options.fetch()


# from util.options import Options
options = Options.fetch()

email = options.get("email", {}).get("email", {})

email = options.get("email", {}).get("email", {})
password = options.get("email", {}).get("password", {})
smtp_host = options.get("email", {}).get("smtp_server", {})


class Email:
    """
    This function handles sending emails.
    """

    def send_email(subject, body, recipient):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = email
        msg["To"] = recipient
        text = body
        parser = commonmark.Parser()
        ast = parser.parse(body)
        renderer = commonmark.HtmlRenderer()
        html = renderer.render(ast)
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)
        with smtplib.SMTP_SSL(smtp_host, 465) as smtp_server:
            smtp_server.login(email, password)
            smtp_server.sendmail(email, recipient, msg.as_string())
