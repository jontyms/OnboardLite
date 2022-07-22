# Onboard

*Onboard* is a web application for managing school organizations at the Univeristy of Central Florida. It was created as a part of a mission to improve analytics, promote DEI and accessibility, and to make signing in as easy as possible ~~because I am sick and tired of writing my name and Knights Email over and over again at meetings~~.

## Goals

Onboard was designed to meet the following goals:

- **Reliable:** Onboard should be able to still work under load, and should be secure.
- **Understandable:** The source code should be self-documenting. All APIs are also auto-documented by FastAPI, the repository structure should be organized and the code should be thouroughly commented, making reading the code a pleasant experience.
- **Usable:** End users should not have to think to use the web UI. Tasks should be automated or slimmed-down when possible while not losing functionality.
	- Creating an account (joining the club) should be done in *one* workflow
	- Prefer cookies, then WebAuthn, then Discord for authenticating users.
	- If possible, adopt Apple Pay, Google Pay, and similar technologies via Stripe/Square.
- **Frugal:** Onboard is built to be a native AWS application, allowing us to reduce costs while preserving scalability and ease of deployment (via CloudFormation)

## Getting Started (local)
```py
# Requires >= Python3.8
pip3 install -r requirements.txt
python3 index.py
```

## Deploying

(coming soon to a `us-east-1` near you!)