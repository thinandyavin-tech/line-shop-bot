# Security policy

## Reporting a vulnerability

Please do not open a public issue for a credential, webhook-authentication, payment-payload, or customer-data vulnerability. Use GitHub’s private vulnerability reporting for this repository, or contact the maintainer through the email on the profile.

Include the affected path, a minimal reproduction without secrets, and the impact. Remove channel tokens, PromptPay identifiers used in production, customer IDs, and real order data from reports.

## Deployment boundary

The bot verifies LINE webhook signatures and keeps prices in the checked-in menu, but a deployment still needs HTTPS, secret rotation, database backups, access control for the owner workflow, and reconciliation against the payment provider. The example project does not claim to verify that a bank transfer settled merely because a customer sent `paid`.
