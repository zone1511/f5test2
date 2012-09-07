from __future__ import absolute_import

import bottle
from f5test.web.tasks import nosetests, add
from celery.result import AsyncResult

try:
    import json
except ImportError:
    import simplejson as json


@bottle.route('/add/<a:int>/<b:int>')
def add_handler(a, b):
    result = add.delay(a, b).get()  # @UndefinedVariable
    return "result: {0}".format(result)


@bottle.route('/status/:task_id')
def status_handler(task_id):
    #status = nosetests.delay() #@UndefinedVariable
    result = AsyncResult(task_id)
    return "task: {0}<br>status: {0.status}<br>result: {0.result}".format(result)


@bottle.route('/bigip_bvt_request', method='POST')
def main_handler():
    data = json.load(bottle.request.body)
    status = nosetests.delay(data)  # @UndefinedVariable
    return "Queued: <a href='/status/{0}'>{0}</a>\n".format(status)

if __name__ == '__main__':
    bottle.run(host='0.0.0.0', port=8081)
