# OnboardLite

OnboardLite is the result of the Influx Initiative, our vision for an improved student organization lifecycle at the University of Central Florida

This is to be replaced by Influx in the future, a more fleshed-out approach with increased scope.

## Getting Started (local)
```py
# Requires >= Python3.8
python3 -m pip install -r requirements.txt
python3 index.py
```

## Deploying

1. Deploy a box.
2. Make sure the AWS CLI is set up and that `~/.aws` is populated.
- Create a new AWS user with the policies `AmazonDynamoDBFullAccess` and `PowerUserAccess` (or preferrably, a policy that includes the actions `dynamodb:*` and `sso:account:access`)
- [Install the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- Run `aws configure sso` on the host machine. See [this article](https://docs.aws.amazon.com/cli/latest/userguide/sso-configure-profile-token.html) for more details.
- Create a new DynamoDB table named "hackucf_members" (default) with partition key `id`
3. Make sure Stripe is configured to work with a webhook at `$URL/pay/webhook/validate` and the account is activated.
- Create the webhook at the desired domain. Include the events `checkout.session.*`.
- Create a product to represent dues payments in the dashboard. This should be $10 + $0.60 to account for Stripe fees.
4. Request a configuration file with all the neccesary secrets/configurations for AWS, Stripe, Discord, and others.
5. Install dependencies: `sudo apt install -y nginx certbot build-essential python3.11 python3.11-dev` (or later versions of python3). You may need to use [get-pip.py](https://bootstrap.pypa.io/get-pip.py) to install `pip3.11` as well.
6. Install Python dependencies: `python3.11 -m pip install -r requirements.txt`
7. Configure `nginx` (recommended) to proxy to port 80/443 + enable HTTPS. Set headers like `Content-Security-Policy`.
- If you use nginx, PLEASE use HTTPS (if you can; Cloudflare will probably disagree and want to use its own cert).
8. Install redis ``sudo apt install redis``
9. Drop the following `systemd` service, replacing values as appropiate:
```conf
[Unit]
Description=Uvicorn instance to serve OnboardLite
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/onboard-user/OnboardLite/
Environment="PATH=/home/onboard-user/OnboardLite/"
ExecStart=/home/onboard-user/.local/bin/uvicorn index:app --host 127.0.0.1 --port 8000 --workers 2

[Install]
WantedBy=multi-user.target
```
10. Drop the following nginx site config:
```conf
server {
        listen 80;
        listen [::]:80;

        server_name join.hackucf.org;

        proxy_set_header X-Forwarded-For $proxy_protocol_addr; # To forward the original client's IP address
        proxy_set_header X-Forwarded-Proto $scheme; # to forward the  original protocol (HTTP or HTTPS)
        proxy_set_header Host $host; # to forward the original host requested by the client

        root /var/www/html;
        index index.html;

        location ^~ / {
                proxy_pass http://127.0.0.1:8000;
        }
}
```
11. Start and enable the service using `systemctl`. Do the same for `nginx` if installed.
12. Put the service behind Cloudflare (optional).
13. Generate the Apple Wallet secrets and place them in `config/pki`. See [this tutorial](https://github.com/alexandercerutti/passkit-generator/wiki/Generating-Certificates) for details.
14. Profit!

## Editing Form Data

To edit questions on a form, edit the JSON files in the `forms/` folder. Each JSON is a separate page that acts as a discrete form, with each value correlated to a database entry. OnboardLite uses a file format based on a simplified [Sileo Native Depiction](https://developer.getsileo.app/native-depictions) and achieves the same goal: render a UI from a JSON schema. The schema is, honestly, poorly documented, but is rendered by `util/kennelish.py`. In short, each object in an array is a discrete element that is rendered.

Database entries must be defined in `models/user.py` before being called in a form. Data type valdiation is enforced by Pydantic.

## Sudo Mode

Administrators are classified as trusted Operations members and are *not* the same thing as Executives. These are people who can view roster logs, and should be FERPA-trained by UCF (either using the RSO training or the general TA training). The initial administrator has to be set via DynamoDB's user interface.

## Security Concerns

Please report security vulnerabilities to `execs@hackucf.org`.


## Discord
add redirect for http://localhost:8000/api/oauth/?redir=_redir


## Teraform
Run teraform init
