# Security Policy

## Supported Versions

Only the latest version of PriceRecon receives security updates. Please ensure you're running the most recent release.

## Reporting a Vulnerability

If you discover a security vulnerability in PriceRecon, please report it responsibly.

**Do not** open a public issue or pull request for security vulnerabilities.

### How to Report

Send an email to: **jtstothard@gmail.com**

Include:
- A description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact
- Any suggested fixes (optional)

### What to Expect

- **Response time**: I aim to acknowledge within 48 hours
- **Disclosure timeline**: Vulnerabilities are typically fixed within 7-14 days, depending on severity and complexity
- **Public disclosure**: I'll coordinate with you on a disclosure timeline after the fix is deployed
- **Credit**: With your permission, I'll credit you in the security advisory

### Severity Assessment

I use CVSS 3.1 for severity assessment:
- **Critical** (9.0-10.0): Patches within 7 days
- **High** (7.0-8.9): Patches within 14 days
- **Medium** (4.0-6.9): Patches within 30 days
- **Low** (0.1-3.9): Patches in next minor release

## Security Features

PriceRecon includes several security features:
- API key authentication for protected endpoints
- Secret scanning enabled on GitHub (detects accidentally committed secrets)
- Push protection enabled on GitHub (blocks pushes with known secrets)
- Dependency updates automated via Dependabot

## Best Practices for Users

1. **Never commit API keys or secrets** to the repository
2. **Use environment variables** for all sensitive configuration (see `.env.example`)
3. **Keep dependencies updated** - Dependabot will open PRs for security updates
4. **Run behind a reverse proxy** (nginx, Caddy) in production with HTTPS
5. **Restrict network access** - PriceRecon only needs outbound HTTP/HTTPS to connector sources
6. **Review connector configurations** - Only enable connectors you trust with your credentials

## Third-Party Security

PriceRecon integrates with external services (eBay, Facebook Marketplace, etc.). Review the [privacy and security terms](README.md#supported-sources) for each service you configure.