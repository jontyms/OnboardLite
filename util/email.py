import smtplib, ssl
from email.mime.text import MIMEText
from util.options import Options

options = Options.fetch()


#from util.options import Options
options = Options.fetch()

email = options.get('email', {}).get('email', {})
password = options.get('email', {}).get('password', {})
smtp_host = options.get('email', {}).get('smtp_server', {})
print(email)
print(password)
print(smtp_host)
class Email:
    """
    This function handles sending emails.
    """
    def send_email(subject, body, recipient):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = email
        msg['To'] = recipient
        with smtplib.SMTP_SSL(smtp_host, 465) as smtp_server:
           print(msg.as_string())
           smtp_server.login(email, password)
           smtp_server.sendmail(email, recipient, msg.as_string())
        
