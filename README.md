# OnboardLite

> Hack@UCF's modern membership management and onboarding system

OnboardLite is a comprehensive membership lifecycle platform built for student organizations at the University of Central Florida. Part of the Influx Initiative, it streamlines member registration, dues payment, and infrastructure provisioning.

## Features

- **Discord OAuth Integration** - Seamless authentication using Discord accounts
- **Stripe Payment Processing** - Automated dues collection and verification
- **Mobile Wallet Support** - Apple Wallet and Google Wallet membership passes
- **Infrastructure Provisioning** - Automated private cloud access for members
- **Admin Dashboard** - Comprehensive member management and analytics
- **Form System** - Flexible JSON-based form rendering with Kennelish
- **API Access** - RESTful API with JWT authentication and API key support
- **Security First** - CSRF protection, secure session management, and comprehensive audit logging

## Quick Start

### Prerequisites

- Python 3.11+
- SQLite (development) or PostgreSQL (production)
- Discord Application (for OAuth)
- Stripe Account (for payments)

### Local Development

```bash
# Clone repository
git clone https://github.com/HackUCF/OnboardLite.git
cd OnboardLite

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up pre-commit hooks
uv run pre-commit install

# Create config directory
mkdir -p config database
cp options-example.yml config/options.yml

# Edit config/options.yml with your settings
# See DEVELOPER_GUIDE.md for detailed configuration

# Run development server
uv run uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000` to see the application.

### Docker Development

```bash
docker compose -f docker-compose-dev.yml up --watch
```



## Architecture

OnboardLite is built with:

- **FastAPI** - Modern Python web framework
- **SQLModel** - SQL database ORM with Pydantic integration
- **Jinja2** - Server-side template rendering
- **Stripe** - Payment processing
- **Discord OAuth** - User authentication
- **Google/Apple Wallet APIs** - Mobile pass generation

### Project Structure

```
OnboardLite/
├── app/
│   ├── main.py              # Application entry point
│   ├── models/              # Database models
│   ├── routes/              # API endpoints
│   ├── util/                # Utilities and helpers
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS, JS, images
├── forms/                   # Kennelish form definitions
├── config/                  # Configuration files
└── tests/                   # Test suite
```

## Configuration

OnboardLite uses YAML configuration files. Key settings:

```yaml
# Discord OAuth
discord:
  client_id: your_client_id
  secret: your_secret
  redirect_base: http://localhost:8000/api/oauth/
  public_key: your_application_public_key  # for the /onboard-qr slash command

# JWT Authentication
jwt:
  secret: your_random_secret_32chars_min
  lifetime_user: 9072000  # 15 weeks
  lifetime_sudo: 86400    # 1 day

# Database
database:
  url: "sqlite:///database/database.db"

# Stripe Payments
stripe:
  api_key: sk_test_...
  webhook_secret: whsec_...
  pause_payments: false
```

See `options-example.yml` for complete configuration reference.

## Security

OnboardLite implements modern web security practices:

- **Secure Sessions** - HTTP-only cookies with configurable lifetimes
- **API Authentication** - JWT tokens and API keys with admin-level access
- **Input Validation** - Pydantic models for all user input
- **SQL Injection Prevention** - SQLModel ORM with parameterized queries

### Reporting Security Issues

Please report security vulnerabilities to `execs@hackucf.org` or through [GitHub Security Advisories](https://github.com/HackUCF/OnboardLite/security).


## Development

### Running Tests

```bash
uv run pytest
```

### Code Quality

```bash
# Format code
uv run ruff format ./

# Lint
uv run ruff check app/

```

### VS Code Debugging

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8000"]
    }
  ]
}
```

## Deployment

### Production with Docker

```bash
# Build and run
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Environment Variables

Production deployments should use environment variables for secrets:

```bash
export DISCORD_CLIENT_SECRET=...
export STRIPE_API_KEY=...
export JWT_SECRET=...
```


## Admin Setup

The first admin must be set manually:

1. Access the database (SQLite or PostgreSQL)
2. Update the user's `sudo` field to `true`:

```sql
UPDATE usermodel SET sudo = true WHERE discord_id = 'YOUR_DISCORD_ID';
```

## Discord Slash Commands

Members can run `/onboard-qr` in the Hack@UCF Discord to get their membership QR code (the same code as on `/profile` and in the wallet passes) as an ephemeral message. Slash commands are served by the app itself at `POST /discord/interactions` — no bot process runs. To set it up:

1. In the [Discord developer portal](https://discord.com/developers/applications), copy the application's **Public Key** into `discord.public_key`.
2. Make sure the bot was invited to the guild with the `applications.commands` scope.
3. Set the application's **Interactions Endpoint URL** to `https://join.hackucf.org/discord/interactions`. Discord only saves it if the app answers its PING and rejects bad signatures, so the app must be deployed with the key first.
4. Register the commands with the guild. This runs inside the container so it uses the same config and secrets as the app:

```bash
docker compose run --rm onboardlite register-discord-commands
# or locally:
uv run app/entry.py register-discord-commands
```

## Kennelish Forms

OnboardLite uses a custom form system called Kennelish (inspired by Sileo Native Depictions):

```json
[
  {
    "type": "text",
    "key": "first_name",
    "label": "First Name",
    "required": true
  },
  {
    "type": "email",
    "key": "email",
    "label": "Email Address"
  }
]
```

Forms are stored in `forms/` and rendered dynamically.

## API Usage

### Authentication

**Web Users (Discord OAuth):**
- Authenticate via `/discord/new`
- Receive JWT in HTTP-only cookie
- Session lifetime: 15 weeks (regular), 1 day (admin)

**API Keys:**
```bash
curl -H "Authorization: Bearer onboard_live_your_key_here" \
     https://join.hackucf.org/admin/list
```

API keys are configured in `config/options.yml` and have full admin access.



### Getting Help

- **Issues** - [GitHub Issues](https://github.com/HackUCF/OnboardLite/issues)
- **Discussions** - [GitHub Discussions](https://github.com/HackUCF/OnboardLite/discussions)

## License

OnboardLite is licensed under the MIT License. See [LICENSE](LICENSE) for details.

Copyright (c) 2026 Collegiate Cyber Defense Club

## Acknowledgments

Built with ❤️ by [Hack@UCF](https://hackucf.org)
