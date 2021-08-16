# openstack-sandbox-manager

## Usage

* Create `clouds.yml` on basis of `clouds.yml.sample`
* Create `secure.yml` on basis of `secure.yml.sample`

Show resources that are older than `THRESHOLD` days:

```
$ tox -- --cloud service --project PROJECT --threshold THRESHOLD
```

Send a notification to an owner whose resource is older than `THRESHOLD` days:

```
$ tox -- --cloud service --project PROJECT --threshold THRESHOLD --mailgun-key MAILGUN_API_KEY
```
