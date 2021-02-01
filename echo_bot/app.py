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

# process_before_response must be True when running on FaaS
app = App(process_before_response=True)


@app.message(re.compile("(?:\s|^)([A-Z,a-z]+-[0-9]+)(?=\s|$)"))
def message_hello(message, say, context):

    for jira_id in context["matches"]:

        jira = JIRA(jira_url, auth=(jira_user, jira_pass))

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

            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*<{jira_url}/browse/{jira_id}|[{jira_id}] {summary}>*",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Status:* {status}"},
                        {"type": "mrkdwn", "text": f"*version:* {fix_version}"},
                        {"type": "mrkdwn", "text": f"*Reporter:* {reporter}"},
                        {"type": "mrkdwn", "text": f"*Assignee:* {assignee}"},
                    ],
                },
            ]

            say(blocks=blocks)
        except JIRAError:
            say("Odd, I cant find a summary for it")


SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)


def lambda_handler(event, context):
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
