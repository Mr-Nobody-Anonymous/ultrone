# ULTRONE Auto-Update Feature

This feature automatically checks for new ULTRONE releases and updates the Helm deployment daily.

## How It Works

1. **CronJob** runs daily at midnight (configurable)
2. **Python script** checks GitHub for latest release
3. If a new version is found:
   - Sends notification (webhook)
   - If `autoUpdate: true`, automatically upgrades the Helm release
4. **RBAC** permissions allow the job to manage Helm releases and read secrets

## Configuration

Enable auto-update in `values.yaml`:

```yaml
autoupdate:
  enabled: true
  schedule: "0 0 * * *"  # Daily at midnight (cron format)
  autoUpdate: false  # Set to true for automatic updates
  githubRepo: "Mr-Nobody-Anonymous/ultrone"
  githubToken: ""  # Optional: GitHub PAT for higher rate limits
```

## Setup Instructions

### 1. Create GitHub Personal Access Token (Optional)

For higher API rate limits, create a GitHub PAT:
1. Go to GitHub → Settings → Developer Settings → Personal Access Tokens
2. Generate token with `public_repo` scope
3. Add to secrets:

```bash
kubectl create secret generic ultrone-secrets \
  --from-literal=GITHUB_TOKEN='your_token_here' \
  -n ultrone
```

Or set in values.yaml:
```yaml
autoupdate:
  githubToken: "your_token_here"
```

### 2. Configure Helm RBAC

The service account needs permissions to manage Helm releases:

```yaml
rbac:
  create: true
  clusterWide: true  # Required for Helm Tiller-like operations
```

### 3. Deploy with Auto-Update

```bash
helm install ultrone ./infra/helm/ultrone \
  --set autoupdate.enabled=true \
  --set autoupdate.autoUpdate=false  # Set true for auto-updates
```

## Notification Webhooks

Configure webhook for notifications:

```bash
helm install ultrone ./infra/helm/ultrone \
  --set autoupdate.enabled=true \
  --set autoupdate.autoUpdate=true \
  --set global.env.WEBHOOK_URL="https://hooks.slack.com/services/..."
```

Supported webhooks:
- Slack
- Discord
- Microsoft Teams
- Custom HTTP endpoints

## Manual Trigger

Trigger update manually:

```bash
kubectl create job --from=cronjob/ultrone-autoupdate ultrone-autoupdate-manual -n ultrone
```

## View Logs

```bash
# Check cronjob status
kubectl get jobs -n ultrone

# View logs of latest run
kubectl logs -l job-name=ultrone-autoupdate -n ultrone --tail=100
```

## Security Considerations

1. **GitHub Token**: Store securely in Kubernetes secrets, never commit to git
2. **Helm Permissions**: The auto-update job has significant permissions - restrict access
3. **Auto-Update**: Disabled by default for safety. Test with `autoUpdate: false` first
4. **Rollback**: Helm maintains release history for easy rollback

## Rollback Procedure

If an update causes issues:

```bash
# List release history
helm history ultrone -n ultrone

# Rollback to previous version
helm rollback ultrone <revision> -n ultrone
```

## Troubleshooting

### CronJob not running

```bash
# Check cronjob status
kubectl get cronjob ultrone-autoupdate -n ultrone

# Check events
kubectl describe cronjob ultrone-autoupdate -n ultrone
```

### Permission errors

```bash
# Verify service account has correct permissions
kubectl get clusterrole ultrone -n ultrone
kubectl describe clusterrole ultrone
```

### GitHub API rate limits

Use a GitHub PAT to increase rate limits from 60 to 5000 requests/hour.

## Architecture

```
┌─────────────┐
│   CronJob   │ (Daily at midnight)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ autoupdate  │
│   .py       │
└──────┬──────┘
       │
       ├──► GitHub API (check latest release)
       │
       ├──► Helm CLI (get current version)
       │
       ├──► Compare versions
       │
       ├──► Send notification
       │
       └──► Helm upgrade (if autoUpdate=true)
```

## License

MIT License - Part of ULTRONE project