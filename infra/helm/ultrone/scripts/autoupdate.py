#!/usr/bin/env python3
"""
ULTRONE Auto-Update Script
Checks for new releases and updates the Helm release automatically.
"""

import os
import sys
import subprocess
import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_latest_release(repo, token=None):
    """Fetch the latest release from GitHub repository."""
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'

    url = f'https://api.github.com/repos/{repo}/releases/latest'
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        release_data = response.json()
        return {
            'tag': release_data['tag_name'],
            'name': release_data['name'],
            'published_at': release_data['published_at'],
            'url': release_data['html_url']
        }
    except Exception as e:
        logger.error(f"Failed to fetch latest release: {e}")
        return None


def get_current_version():
    """Get the currently deployed version."""
    try:
        result = subprocess.run(
            ['helm', 'list', '-n', os.getenv('HELM_NAMESPACE', 'ultrone'), '-o', 'json'],
            capture_output=True,
            text=True,
            check=True
        )
        import json
        releases = json.loads(result.stdout)
        for release in releases:
            if release['name'] == os.getenv('HELM_RELEASE_NAME'):
                return release['chart']
    except Exception as e:
        logger.error(f"Failed to get current version: {e}")
    return None


def update_helm_release(chart_path, release_name, namespace):
    """Update the Helm release."""
    try:
        # First, check if there are any changes
        result = subprocess.run(
            ['helm', 'upgrade', release_name, chart_path, '-n', namespace, '--dry-run'],
            capture_output=True,
            text=True
        )
        
        if 'has no deployed releases' in result.stderr:
            logger.info("No existing deployment found, performing install")
            cmd = ['helm', 'install', release_name, chart_path, '-n', namespace]
        else:
            logger.info("Upgrading existing deployment")
            cmd = ['helm', 'upgrade', release_name, chart_path, '-n', namespace]
        
        # Add auto-approve flag
        cmd.append('--atomic')
        cmd.append('--timeout')
        cmd.append('5m')
        
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Update successful!")
            logger.info(result.stdout)
            return True
        else:
            logger.error(f"Update failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to update Helm release: {e}")
        return False


def send_notification(webhook_url, message):
    """Send notification to webhook (Slack, Discord, etc.)."""
    if not webhook_url:
        return
    
    try:
        requests.post(webhook_url, json={'text': message}, timeout=10)
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")


def main():
    """Main update logic."""
    logger.info("Starting ULTRONE auto-update check")
    
    # Configuration from environment
    github_repo = os.getenv('GITHUB_REPO', 'Mr-Nobody-Anonymous/ultrone')
    github_token = os.getenv('GITHUB_TOKEN')
    helm_release = os.getenv('HELM_RELEASE_NAME', 'ultrone')
    helm_namespace = os.getenv('HELM_NAMESPACE', 'ultrone')
    helm_chart = os.getenv('HELM_CHART', './infra/helm/ultrone')
    auto_update = os.getenv('AUTO_UPDATE', 'false').lower() == 'true'
    webhook_url = os.getenv('WEBHOOK_URL')
    
    # Get current version
    current_version = get_current_version()
    logger.info(f"Current version: {current_version}")
    
    # Get latest release
    latest_release = get_latest_release(github_repo, github_token)
    if not latest_release:
        logger.error("Failed to fetch latest release, exiting")
        sys.exit(1)
    
    logger.info(f"Latest version: {latest_release['tag']}")
    logger.info(f"Release URL: {latest_release['url']}")
    
    # Compare versions
    if current_version and latest_release['tag'] in current_version:
        logger.info("Already on latest version, no update needed")
        sys.exit(0)
    
    # Check if auto-update is enabled
    if not auto_update:
        message = f"🔄 New ULTRONE release available: {latest_release['tag']}\n" \
                 f"Current: {current_version}\n" \
                 f"Release notes: {latest_release['url']}\n" \
                 f"Auto-update is disabled. Please update manually."
        logger.info(message)
        send_notification(webhook_url, message)
        sys.exit(0)
    
    # Perform update
    message = f"🚀 Updating ULTRONE from {current_version} to {latest_release['tag']}"
    logger.info(message)
    send_notification(webhook_url, message)
    
    if update_helm_release(helm_chart, helm_release, helm_namespace):
        success_message = f"✅ ULTRONE successfully updated to {latest_release['tag']}"
        logger.info(success_message)
        send_notification(webhook_url, success_message)
        sys.exit(0)
    else:
        error_message = f"❌ ULTRONE update failed"
        logger.error(error_message)
        send_notification(webhook_url, error_message)
        sys.exit(1)


if __name__ == '__main__':
    main()