import requests
from urllib.parse import urlparse
from entries.models import Entry

def extract_github_username(url):
    """Extract username from a GitHub profile URL."""
    if not url:
        return None
    path = urlparse(url).path.strip('/')
    return path.split('/')[0] if path else None


def fetch_github_activity(username):
    """Fetch recent public events from GitHub for a given username."""
    if not username:
        return []

    url = f"https://api.github.com/users/{username}/events/public"
    try:
        response = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"})
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching GitHub data for {username}: {e}")
    return []


def create_github_entries_for_author(author):
    """Convert GitHub activity into Entry objects."""
    username = extract_github_username(author.github)
    events = fetch_github_activity(username)
    if not events:
        return 0

    created_count = 0

    for event in events:
        event_id = event.get("id")
        event_type = event.get("type")
        repo = event.get("repo", {}).get("name", "")
        created_at = event.get("created_at")

        # Avoid duplicates based on event ID
        if Entry.objects.filter(source_id=event_id).exists():
            continue

        # Format the content depending on the event type
        if event_type == "PushEvent":
            commits = event["payload"].get("commits", [])
            commit_count = len(commits) if commits else 1  # assume at least one push occurred
            content = f"**{author.display_name}** pushed {commit_count} commit(s) to [{repo}](https://github.com/{repo})"

            if commits:
                content += ":\n" + "\n".join(f"- {c['message']}" for c in commits)
            else:
                # Add link to the branch head if no commit messages are available
                head_sha = event["payload"].get("head")
                if head_sha:
                    content += f"\n[View latest commit](https://github.com/{repo}/commit/{head_sha})"


        elif event_type == "IssuesEvent":
            issue = event["payload"].get("issue", {})
            issue_title = issue.get("title", "")
            issue_url = issue.get("html_url", "")
            content = f"**{author.display_name}** opened a new issue in [{repo}](https://github.com/{repo}): [{issue_title}]({issue_url})"

        elif event_type == "ForkEvent":
            forkee = event["payload"].get("forkee", {}).get("html_url", "")
            content = f"**{author.display_name}** forked [{repo}](https://github.com/{repo}) → [{forkee}]({forkee})"

        else:
            continue  # Skip events not included above

        Entry.objects.create(
            author=author,
            title=f"GitHub Activity: {repo}",
            content=content,
            content_type="text/markdown",
            visibility="PUBLIC",
            source_id=event_id,
        )
        created_count += 1

    return created_count
