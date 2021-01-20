# App performance testing with Hetzner cloud

Use Hetzner cloud top machine to run the app performance tests:

```
# docker-machine rm demo
docker-machine create \
--driver=hetzner \
--hetzner-api-token=$HETZNER_TOKEN \
--hetzner-server-type=cx51 \
--hetzner-server-location=fsn1 \
demo
```
Using Hetzner console add the machine to the local network (`network-1`)
and setup docker networking:
```
docker network create -d bridge \
-o com.docker.network.bridge.host_binding_ipv4=$(ifconfig ens10 | grep "inet " | awk '{print $2}') \
intranet
```
Run all tests using the machine created:
```
eval $(docker-machine env demo)
```
The cluster is using HAPROXY as a load balancer. It is configured to send logs
to the host machine `rsyslog`. Configuration file is `/etc/rsyslog.d/haproxy.conf`:
```
$ModLoad imudp
$UDPServerAddress 0.0.0.0
$UDPServerRun 514
local0.* /var/log/haproxy-traffic.log
local0.notice /var/log/haproxy-admin.log
```

## One node app testing

Confluence Fields plugin is an integration app that takes its data from
Confluence and populates JIRA custom fields with this data. Thus the test
setup includes both Confluence server and JIRA DC.

### General cluster tests

Clone Atlassian DC performance toolkit:
```
git clone https://github.com/atlassian/dc-app-performance-toolkit.git dcapt.orig
cd dcapt.orig
```
Set JIRA address and credentials in `app/jira.yml` and run the test:
```
docker run --shm-size=4g --rm -v "$PWD:/dc-app-performance-toolkit" atlassian/dcapt jira.yml
```
Install Confluence Fields plugin and repeat the test.

### App-specific tests

Confluence Fields plugin actions to test are:

- view and update custom field with JIRA UI (selenium)
- query JIRA for Confluence pages to populate custom field options (locust)

The selenium UI test opens a browse issue page, calculates the number of pages
in a Confluence field, updates the issue by adding an extra page to the field
via EditIssue web action, then calculates the number of pages again to make
sure that it equals the initial value + 1.

Updating a field via UI takes longer seconds to test due to a number of waits
that I had to introduce in the test code:

- 2s wait to get AUI select2 fully initialized
- 1s wait to get selected option copied to the field's input
- 1s wait after edit dialog submit

These are not a part of the plugin code, but of a test code.

Locust endpoint test is set to make sure that the plugin's REST endpoint actually
returns correct number of Confluence pages to populate a custom field. This is
the only general-purpose endpoint in the plugin, others are used for administration
and configuration.

To run app-specific tests:
```
git clone https://github.com/mesilat/dc-app-performance-toolkit.git dcapt.apps
cd dcapt.apps
docker run --shm-size=4g --rm -v "$PWD:/dc-app-performance-toolkit" atlassian/dcapt jira.yml
```
If need running app-specific tests locally:
```
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.txt
cd app
bzt jira.yml
```
