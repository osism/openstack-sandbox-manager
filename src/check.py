# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import timedelta, datetime
import logging
import os
import sys
import pytz

from dateutil import parser
import jinja2
from oslo_config import cfg
import openstack
import requests
import yaml

PROJECT_NAME = "openstack-sandbox-manager"
CONF = cfg.CONF
opts = [
    cfg.BoolOpt("debug", required=False, default=False),
    cfg.BoolOpt("dry-run", required=False, default=False),
    cfg.IntOpt("threshold", help="Threshold in days", default=60),
    cfg.StrOpt("cloud", help="Managed cloud", default="service"),
    cfg.StrOpt(
        "mailgun-api",
        default="https://api.mailgun.net/v3/betacloud.io/messages",
        required=False,
    ),
    cfg.StrOpt(
        "mailgun-from",
        default="Betacloud Operations <noreply@betacloud.io>",
        required=False,
    ),
    cfg.StrOpt("mailgun-key", required=False),
    cfg.StrOpt("openstack-project", help="OpenStack project", required="True"),
]
CONF.register_cli_opts(opts)
CONF(sys.argv[1:], project=PROJECT_NAME)

if CONF.debug:
    level = logging.DEBUG
else:
    level = logging.INFO
logging.basicConfig(
    format="%(asctime)s - %(message)s", level=level, datefmt="%Y-%m-%d %H:%M:%S"
)


# NOTE(berendt): http://matthiaseisen.com/pp/patterns/p0198/
def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    return (
        jinja2.Environment(loader=jinja2.FileSystemLoader(path or "./"))
        .get_template(filename)
        .render(context)
    )


def send_mail(to, payload, mailgunfrom, mailgunapi, mailgunkey):
    logging.info("send mail to %s" % to)
    logging.debug(payload)

    if not CONF.dry_run:
        result = requests.post(
            mailgunapi,
            auth=("api", mailgunkey),
            data={
                "from": mailgunfrom,
                "to": to,
                "subject": payload["subject"],
                "text": payload["body"],
            },
        )
        logging.debug(result.text)


if __name__ == "__main__":
    cloud = openstack.connect(cloud=CONF.cloud)

    utc = pytz.UTC
    now = utc.localize(datetime.now())

    threshold = timedelta(days=(CONF.threshold + 1))

    for instance in cloud.list_servers(filters={"project_id": CONF.openstack_project}):
        logging.debug("checking instance %s" % instance.name)

        created_at = parser.parse(instance.created_at)
        expiration = created_at + threshold

        if expiration < now:
            user = cloud.identity.get_user(instance.user_id)

            if user:
                logging.info(
                    "instance %s (%s) from %s: %s"
                    % (
                        instance.name,
                        instance.id,
                        user.name,
                        created_at.strftime("%Y-%m-%d %H:%M"),
                    )
                )

                if CONF.mailgun_key:
                    diff = now - created_at
                    context = {
                        "diff": diff.days,
                        "id": instance.id,
                        "name": instance.name,
                        "project": CONF.openstack_project,
                        "threshold": CONF.threshold,
                        "type": "instance",
                    }
                    payload = yaml.load(
                        render("templates/outdated-resource.yml.j2", context),
                        Loader=yaml.SafeLoader,
                    )
                    send_mail(
                        user.email,
                        payload,
                        CONF.mailgun_from,
                        CONF.mailgun_api,
                        CONF.mailgun_key,
                    )

                if not CONF.dry_run and instance.status == "ACTIVE":
                    logging.info(
                        "stopping instance %s (%s) from %s"
                        % (instance.name, instance.id, user.name)
                    )
                    cloud.compute.stop_server(instance.id)
            else:
                logging.info(
                    "instance %s (%s): %s (owned by non-findable user)"
                    % (
                        instance.name,
                        instance.id,
                        created_at.strftime("%Y-%m-%d %H:%M"),
                    )
                )
