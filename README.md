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

1. Make sure the AWS CLI is set up and that `~/.aws` is populated.
2. Make sure Stripe is configured to work with a webhook at `$URL/pay/webhook/validate` and the account is activated.
3. Request a configuration file with all the neccesary secrets/configurations for AWS, Stripe, Discord, and others.
4. Install `uwsgi` and `python3.8`.
5. Drop the following `systemd` service, replacing values as appropiate:
```conf
[Unit]
Description=uWSGI instance to serve OnboardLite
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/OnboardLite/
Environment="PATH=/home/ubuntu/OnboardLite/"
ExecStart=/usr/bin/uwsgi --ini api.ini --plugin python38

[Install]
WantedBy=multi-user.target
```
6. Start and enable the service.
7. Put the service behind Cloudflare.
8. Profit!

## Editing Form Data

To edit questions on a form, edit the JSON files in the `forms/` folder. Each JSON is a separate page that acts as a discrete form, with each value correlated to a database entry. OnboardLite uses a file format based on a simplified [Sileo Native Depiction](https://developer.getsileo.app/native-depictions) and achieves the same goal: render a UI from a JSON schema. The schema is, honestly, poorly documented, but is rendered by `util/kennelish.py`. In short, each object in an array is a discrete element that is rendered.

Database entries must be defined in `models/user.py` before being called in a form. Data type valdiation is enforced by Pydantic.

## Sudo Mode

Administrators are classified as trusted Operations members and are *not* the same thing as Executives. These are people who can view roster logs, and should be FERPA-trained by UCF (either using the RSO training or the general TA training). The initial administrator has to be set via DynamoDB's user interface.

## Security Concerns

Please report security vulnerabilities to `execs@hackucf.org`.
