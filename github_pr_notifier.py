#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests>=2.32.5",
#     "blink1>=0.4.0",
# ]
# ///
"""
GitHub PR Notification Script for blink(1)

Monitors GitHub pull requests for comments and approvals, triggering
blink(1) device notifications for different event types.
"""

import os
import time
import json
import logging
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import argparse

try:
    from blink1.blink1 import Blink1, Blink1ConnectionFailed
except ImportError:
    print("blink1 library not found. Install with: pip install blink1")
    exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('github_pr_notifier.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class PREvent:
    """Represents a PR event (comment or review)"""
    pr_number: int
    event_type: str  # 'comment', 'approved', 'changes_requested', 'dismissed'
    author: str
    created_at: str
    body: Optional[str] = None
    

class GitHubPRMonitor:
    """Monitors GitHub PRs and triggers blink(1) notifications"""
    
    def __init__(self, username: str, poll_interval: int = 60, test_mode: bool = False):
        self.username = username
        self.poll_interval = poll_interval
        self.test_mode = test_mode
        
        # Track processed events to avoid duplicates
        self.processed_events: Set[str] = set()
        
        # Last check time - look back 1 hour to catch recent activity
        self.last_check = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Initialize blink(1) device
        self.blink1 = None
        self._init_blink1()
        
        # Verify gh CLI is available
        self._check_gh_cli()
    
    def _init_blink1(self):
        """Initialize blink(1) device connection"""
        try:
            self.blink1 = Blink1()
            logger.info(f"Connected to blink(1) device: {self.blink1.get_serial_number()}")
        except Blink1ConnectionFailed as e:
            logger.error(f"Failed to connect to blink(1) device: {e}")
            self.blink1 = None
    
    def _check_gh_cli(self):
        """Verify gh CLI is installed and authenticated"""
        try:
            result = subprocess.run(['gh', 'auth', 'status'], 
                                  capture_output=True, text=True, check=True)
            logger.info("gh CLI is authenticated and ready")
        except subprocess.CalledProcessError as e:
            logger.error("gh CLI is not authenticated. Run 'gh auth login' first")
            raise Exception("gh CLI authentication required")
        except FileNotFoundError:
            logger.error("gh CLI not found. Please install GitHub CLI")
            raise Exception("gh CLI not installed")
    
    
    def get_user_prs(self) -> List[Dict]:
        """Get all open PRs created by the user"""
        # Use gh search to find user's open PRs
        try:
            env = os.environ.copy()
            env['GH_PAGER'] = ''
            
            result = subprocess.run([
                'gh', 'search', 'prs', '--author', self.username, '--state', 'open', 
                '--limit', '100', '--json', 'number,title,repository,url'
            ], capture_output=True, text=True, check=True, env=env)
            data = json.loads(result.stdout) if result.stdout.strip() else []
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get user PRs: {e}")
            return []
        
        if not data:
            return []
        
        prs = []
        for item in data:
            prs.append({
                'number': item['number'],
                'title': item['title'],
                'repository': item['repository']['nameWithOwner'],
                'url': item['url']
            })
        
        return prs
    
    def get_pr_comments(self, repo: str, pr_number: int) -> List[PREvent]:
        """Get comments on a specific PR since last check"""
        events = []
        
        # Get issue comments using gh pr view
        try:
            env = os.environ.copy()
            env['GH_PAGER'] = ''
            
            # Get PR comments
            result = subprocess.run(['gh', 'pr', 'view', str(pr_number), '--repo', repo, '--json', 'comments'], 
                                  capture_output=True, text=True, check=True, env=env)
            pr_data = json.loads(result.stdout)
            
            if 'comments' in pr_data:
                for comment in pr_data['comments']:
                    created_at = datetime.fromisoformat(comment['createdAt'].replace('Z', '+00:00'))
                    # In test mode, include own comments; in normal mode, exclude them
                    author_filter = True if self.test_mode else comment['author']['login'] != self.username
                    if created_at > self.last_check and author_filter:
                        event_id = f"comment_{repo}_{pr_number}_{comment['id']}"
                        if event_id not in self.processed_events:
                            events.append(PREvent(
                                pr_number=pr_number,
                                event_type='comment',
                                author=comment['author']['login'],
                                created_at=comment['createdAt'],
                                body=comment['body'][:100] + '...' if len(comment['body']) > 100 else comment['body']
                            ))
                            self.processed_events.add(event_id)
            
            # Get PR reviews
            result = subprocess.run(['gh', 'pr', 'view', str(pr_number), '--repo', repo, '--json', 'reviews'], 
                                  capture_output=True, text=True, check=True, env=env)
            pr_data = json.loads(result.stdout)
            
            if 'reviews' in pr_data:
                for review in pr_data['reviews']:
                    # Include all review types: APPROVED, CHANGES_REQUESTED, and COMMENTED
                    if review['state'] in ['APPROVED', 'CHANGES_REQUESTED', 'COMMENTED']:
                        created_at = datetime.fromisoformat(review['submittedAt'].replace('Z', '+00:00'))
                        # In test mode, include own reviews; in normal mode, exclude them
                        author_filter = True if self.test_mode else review['author']['login'] != self.username
                        if created_at > self.last_check and author_filter:
                            event_id = f"review_{repo}_{pr_number}_{review['id']}"
                            if event_id not in self.processed_events:
                                if review['state'] == 'APPROVED':
                                    event_type = 'approved'
                                elif review['state'] == 'CHANGES_REQUESTED':
                                    event_type = 'changes_requested'
                                else:  # COMMENTED
                                    event_type = 'commented'
                                    
                                events.append(PREvent(
                                    pr_number=pr_number,
                                    event_type=event_type,
                                    author=review['author']['login'],
                                    created_at=review['submittedAt'],
                                    body=review.get('body', '')
                                ))
                                self.processed_events.add(event_id)
                                
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to get PR {pr_number} data from {repo}: {e}")
        
        return events
    
    def flash_for_event(self, event: PREvent):
        """Flash blink(1) based on event type"""
        if not self.blink1:
            logger.warning("blink(1) not available, skipping flash")
            return
        
        try:
            if event.event_type == 'comment':
                # Blue flash for comments
                logger.info(f"Flashing BLUE for comment from {event.author}")
                self.blink1.play_pattern('3, #0000FF,0.3,0, #000000,0.3,0')
                
            elif event.event_type == 'approved':
                # Green flash for approvals
                logger.info(f"Flashing GREEN for approval from {event.author}")
                self.blink1.play_pattern('5, #00FF00,0.5,0, #000000,0.2,0')
                
            elif event.event_type == 'changes_requested':
                # Red flash for change requests
                logger.info(f"Flashing RED for change request from {event.author}")
                self.blink1.play_pattern('2, #FF0000,1.0,0, #000000,0.5,0')
                
            elif event.event_type == 'commented':
                # Yellow flash for review comments
                logger.info(f"Flashing YELLOW for review comment from {event.author}")
                self.blink1.play_pattern('3, #FFFF00,0.3,0, #000000,0.3,0')
                
        except Exception as e:
            logger.error(f"Failed to flash blink(1): {e}")
    
    def check_for_updates(self):
        """Check for new PR events and trigger notifications"""
        logger.info("Checking for PR updates...")
        
        prs = self.get_user_prs()
        logger.info(f"Monitoring {len(prs)} open PRs")
        
        new_events = []
        for pr in prs:
            repo = pr['repository']
            pr_number = pr['number']
            
            events = self.get_pr_comments(repo, pr_number)
            new_events.extend(events)
        
        # Process new events
        for event in new_events:
            logger.info(f"New {event.event_type} on PR #{event.pr_number} by {event.author}")
            if event.body:
                logger.info(f"Content: {event.body}")
            
            self.flash_for_event(event)
            time.sleep(2)  # Small delay between flashes
        
        self.last_check = datetime.now(timezone.utc)
        logger.info(f"Check completed. Found {len(new_events)} new events")
    
    def run(self):
        """Main monitoring loop"""
        logger.info(f"Starting GitHub PR monitor for user: {self.username}")
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        
        while True:
            try:
                self.check_for_updates()
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("Stopping monitor...")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.poll_interval)
        
        # Cleanup
        if self.blink1:
            self.blink1.off()
            self.blink1.close()


def main():
    parser = argparse.ArgumentParser(description='GitHub PR notification monitor for blink(1) using gh CLI')
    parser.add_argument('--username', help='GitHub username (or set GITHUB_USERNAME env var)')
    parser.add_argument('--interval', type=int, default=60, help='Poll interval in seconds (default: 60)')
    parser.add_argument('--test', action='store_true', help='Test blink(1) connection and exit')
    parser.add_argument('--test-mode', action='store_true', help='Include your own comments/reviews for testing')
    
    args = parser.parse_args()
    
    # Get username
    username = args.username or os.getenv('GITHUB_USERNAME')
    
    if not username:
        # Try to get username from gh CLI
        try:
            env = os.environ.copy()
            env['GH_PAGER'] = ''
            result = subprocess.run(['gh', 'api', 'user', '--jq', '.login'], 
                                  capture_output=True, text=True, check=True, env=env)
            username = result.stdout.strip()
            logger.info(f"Using GitHub username from gh CLI: {username}")
        except subprocess.CalledProcessError:
            print("GitHub username required. Set GITHUB_USERNAME env var, use --username, or ensure gh CLI is authenticated")
            exit(1)
    
    if args.test:
        # Test blink(1) connection
        try:
            b1 = Blink1()
            print(f"✓ blink(1) connected: {b1.get_serial_number()}")
            print("Testing flash patterns...")
            b1.play_pattern('2, #FF0000,0.5,0, #000000,0.5,0')  # Red
            time.sleep(3)
            b1.play_pattern('2, #00FF00,0.5,0, #000000,0.5,0')  # Green
            time.sleep(3)
            b1.play_pattern('2, #0000FF,0.5,0, #000000,0.5,0')  # Blue
            time.sleep(3)
            b1.off()
            b1.close()
            print("✓ Test complete")
        except Exception as e:
            print(f"✗ blink(1) test failed: {e}")
        exit(0)
    
    # Start monitoring
    if args.test_mode:
        logger.info("TEST MODE: Will flash for your own comments/reviews")
    monitor = GitHubPRMonitor(username, args.interval, test_mode=args.test_mode)
    monitor.run()


if __name__ == '__main__':
    main()
