import os
import re
import sys
import logging

from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from jira import JIRA, JIRAError

sys.path.insert(1, "vendor")

jira_url = os.environ.get("JIRA_URL")
jira_user = os.environ.get("JIRA_USER")
jira_pass = os.environ.get("JIRA_PASS")
jira_regex_pattern = "(?:\s|^|\/)([A-Z,a-z]+-[0-9]+)"

# process_before_response must be True when running on FaaS
app = App(process_before_response=True)


@app.message(re.compile(jira_regex_pattern))
def message_hello(ack, message, say, context):
    ack()
    message_blocks = []

    logging.debug(f"Message: {message}")
    matches = re.findall(jira_regex_pattern, message["text"])

    jira = JIRA(jira_url, auth=(jira_user, jira_pass))

    for jira_id in set(matches):

        try:
            issue = jira.issue(jira_id)

            summary = issue.fields.summary
            status = issue.fields.status.name
            reporter = issue.fields.reporter.displayName

            if hasattr(issue.fields.assignee, "displayName"):
                assignee = issue.fields.assignee.displayName
            else:
                assignee = "Unassigned"

            if len(issue.fields.fixVersions) > 0:
                fix_version = issue.fields.fixVersions[0].name
            else:
                fix_version = "None"

            message_blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*<{jira_url}/browse/{jira_id}|[{jira_id}] {summary}>*",
                    },
                },
            )
            message_blocks.append(
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Status:* {status}"},
                        {"type": "mrkdwn", "text": f"*version:* {fix_version}"},
                        {"type": "mrkdwn", "text": f"*Reporter:* {reporter}"},
                        {"type": "mrkdwn", "text": f"*Assignee:* {assignee}"},
                    ],
                },
            )

        except JIRAError:
            logging.error(f"Odd, I cant find a summary for {jira_id}")

    say(blocks=message_blocks)


SlackRequestHandler.clear_all_log_handlers()
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)


def lambda_handler(event, context):
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
