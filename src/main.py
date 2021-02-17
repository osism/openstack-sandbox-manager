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

PROJECT_NAME = 'list'
CONF = cfg.CONF
opts = [
  cfg.BoolOpt('all', required=False, default=False),
  cfg.BoolOpt('debug', required=False, default=False),
  cfg.StrOpt('cloud', help='Managed cloud', default='service'),
  cfg.StrOpt('domain', help='Domain', required=True),
  cfg.StrOpt('projectname', help='Project name, required=True', default='common-sandbox'),
  cfg.IntOpt('threshold', help='Threshold in days', default=30),
  cfg.StrOpt('mailgunapi', default='https://api.mailgun.net/v3/betacloud.io/messages'),
  cfg.StrOpt('mailgunkey', required=False),
  cfg.StrOpt('mailgunfrom', default='Betacloud Operations <noreply@betacloud.io>')
]
CONF.register_cli_opts(opts)
CONF(sys.argv[1:], project=PROJECT_NAME)

if CONF.debug:
    level = logging.DEBUG
else:
    level = logging.INFO
logging.basicConfig(format='%(asctime)s - %(message)s', level=level, datefmt='%Y-%m-%d %H:%M:%S')


# NOTE(berendt): http://matthiaseisen.com/pp/patterns/p0198/
def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)


def send_mail(to, payload, mailgunfrom, mailgunapi, mailgunkey):
    logging.info("send mail to %s" % to)
    result = requests.post(
        mailgunapi,
        auth=("api", mailgunkey),
        data={"from": mailgunfrom,
              "to": to,
              "subject": payload["subject"],
              "text": payload["body"]})
    logging.debug(result.text)


if __name__ == '__main__':
    cloud = openstack.connect(cloud=CONF.cloud)
    project = cloud.get_project(CONF.projectname, domain_id=CONF.domain)

    utc = pytz.UTC
    now = utc.localize(datetime.now())

    threshold = timedelta(days=(CONF.threshold + 1))

    for instance in cloud.list_servers(filters={"project_id": project.id}):
        logging.debug("checking instance %s" % instance.name)

        created_at = parser.parse(instance.created_at)
        expiration = created_at + threshold

        if ((not CONF.all and instance.status == "ACTIVE") or CONF.all) and expiration < now:
            user = cloud.get_user(instance.user_id)
            logging.info("instance %s (%s) from %s: %s" % (instance.name, instance.id, user.name, created_at.strftime("%Y-%m-%d %H:%M")))

            if CONF.mailgunkey:
                diff = now - created_at
                context = {
                    "diff": diff.days,
                    "id":  instance.id,
                    "name":  instance.name,
                    "project": project.name,
                    "threshold": CONF.threshold,
                    "type": "instance"
                }
                payload = yaml.load(render("templates/outdated-resource.yml.j2", context), Loader=yaml.SafeLoader)
                send_mail(user.email, payload, CONF.mailgunfrom, CONF.mailgunapi, CONF.mailgunkey)
