# App performance testing with Hetzner cloud

## Test setup

### Docker machine

I use Hetzner cloud (nearly) top-level machine to run the app performance tests:

```
docker-machine create \
--driver=hetzner \
--hetzner-api-token=$HETZNER_TOKEN \
--hetzner-server-type=cx51 \
--hetzner-server-location=fsn1 \
demo
```
As this JIRA cluster is not for public use I create a local network (`network-1`)
and setup docker networking as follows:
```
docker network create --driver=bridge \
-o com.docker.network.bridge.host_binding_ipv4=$(ifconfig ens10 | grep "inet " | awk '{print $2}') \
--subnet=172.20.0.0/24 \
--ip-range=172.20.0.0/24 \
--gateway=172.20.0.1 \
intranet
```

### Load Balancer

I am using `haproxy` as a load balancer and I want to have access to its logs
for troubleshooting. Docker machine uses `rsyslog` so I create a new configuration
file `/etc/rsyslog.d/99-haproxy.conf` to enable remote logging:

```
$ModLoad imudp
$UDPServerAddress 172.20.0.1
$UDPServerRun 514
local0.* /var/log/haproxy-traffic.log
local0.notice /var/log/haproxy-admin.log
```
The matching part in `haproxy.cfg` is:
```
global
  log 172.20.0.1:514 local0

defaults
  log global
  option httplog
```

### Running Cluster

I use `docker-compose` to create a cluster in one-node, two-nodes and four-nodes
configuration. The configuration files (`haproxy.cfg` and `docker-compose.yml`)
could be found in folders `onenode`, `twonodes` and `fournodes` respectively.

### Running Tests

For me running locust test produced errors:
```
selenium.common.exceptions.SessionNotCreatedException: Message: session not created: This version of ChromeDriver only supports Chrome version 86
Current browser version is 88.0.4324.96 with binary path /usr/bin/google-chrome      
```
So I reverted to a previous version that was known to be working without this issue:
```
docker image rm atlassian/dcapt
docker image pull atlassian/dcapt@sha256:5137458ea19ddc966e9aa579ca9d52da98dbce27331c0ecbba87631354b0c074
docker run --shm-size=4g --rm -v "$PWD:/dc-app-performance-toolkit" atlassian/dcapt@sha256:5137458ea19ddc966e9aa579ca9d52da98dbce27331c0ecbba87631354b0c074 jira.yml
```

### App Dataset

The app tested (`Confluence Custom Fields`) is an integration plugin that takes
a list of pages from Confluence and renders it as a custom field in JIRA. Thus the
test setup requires a Confluence container as well. Confluence is pre-filled with
100 pages with some basic company data. In JIRA there is a custom field `Clients`
that takes its values from Confluence company data pages.

App-specific dataset utilises Atlassian's DC performance toolkit sample data.
Issues in project `KANS` were edited to have 1 to 10 Confluence pages in
its Clients field to the total of 4000+ issues:

```
const testLoadCCF = async (issues) => {
  // read companies from Confluence
  const recs = await confClient.listPagesByLabel('company-demo');
  const companies = recs.map(rec => ({ id: rec.id, title: rec.title }));
  expect(companies.length).toBe(100);

  for (let i = 0; i < issues.length; i ++) {
    const issue = issues[i];

    // random number of companies to add to the issue
    const countCompanies = getRandom(10) + 1;
    // use map here as we don't want companies duplicated
    const companiesField = {};
    for (let j = 0; j < countCompanies; j++) {
      const company = companies[getRandom(companies.length)];
      companiesField[company.id] = company;
    }
    const value = [];
    Object.values(companiesField).forEach(rec => value.push(JSON.stringify(rec)));
    console.debug(`Issue ${issue.id}`, value.join(','));
    try {
      await jiraClient.updateIssue(issue.id, { customfield_11100: value.join(',') });
    } catch (err) {
      console.debug('Failed');
    }
  }
}
```


## App-specific Tests

The `Confluence Custom Fields` plugin actions to test are:

- view and update custom field with JIRA UI (selenium)
- query JIRA for Confluence pages to populate custom field options (locust)

### Selenium UI Test

The selenium UI [test](app/extension/jira/extension_ui,py)
opens a browse issue page, calculates the number of pages
in a Confluence custom field, updates the issue by adding an extra value to the field
via EditIssue web action. Then it calculates the number of pages again to make
sure that it equals initial value + 1.

Updating a field via UI takes longer seconds to test due to a number of waits
that I had to introduce in the test code:

- 2s wait to get AUI select2 fully initialized
- 1s wait to get selected option copied to the field's input
- 1s wait after edit dialog submit

These are not part of the plugin code, but of the test code.

### Locust

Locust [test](app/extension/jira/extension_locust,py)
is set to make sure that the plugin's REST endpoint actually
returns correct number of Confluence pages to populate a custom field. This is
the general-purpose endpoint in the plugin, while other endpoints are used for
the plugin administration and configuration.

To run app-specific tests:
```
git clone https://github.com/mesilat/dc-app-performance-toolkit.git dcapt.apps
cd dcapt.apps
docker run --shm-size=4g --rm -v "$PWD:/dc-app-performance-toolkit" atlassian/dcapt@sha256:5137458ea19ddc966e9aa579ca9d52da98dbce27331c0ecbba87631354b0c074 jira.yml
```
If need to run app-specific tests locally:
```
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.txt
cd app
bzt jira.yml
```
