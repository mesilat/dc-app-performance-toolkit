import re
from locustio.common_utils import init_logger, jira_measure
import random

logger = init_logger(app_type='jira')
data = {'': 10, 'al': 4, 'ba': 3,'co': 7, 'op': 0, 'chi': 6, 'ame': 1}

@jira_measure
def app_specific_action(locust):
    # Make sure that query returns expected number of Confluence pages
    q = random.choice(list(data.keys()))
    r = locust.get(f"/rest/confield/1.0/field/KANS/11100/pages?q={q}&offset=0&max-results=10", catch_response=True)
    size = r.json().get('size')
    assert size == data[q]
