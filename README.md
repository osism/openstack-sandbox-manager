# openstack-sandbox-manager

## Usage

* Create `clouds.yml` on basis of `clouds.yml.sample`
* Create `secure.yml` on basis of `secure.yml.sample`

Show resources that are older than `THRESHOLD` days:

```
$ tox -e list -- --cloud service --projectname sandbox --domain DOMAIN --threshold THRESHOLD
```

Send a notification to an owner whose resource is older than `THRESHOLD` days:

```
$ tox -e list -- --cloud service --projectname sandbox --domain DOMAIN --threshold THRESHOLD --mailgunkey MAILGUN_API_KEY
```
