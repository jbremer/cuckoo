# Copyright (C) 2010-2013 Claudio Guarnieri.
# Copyright (C) 2014-2016 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import base64

from django.http import JsonResponse

from cuckoo.web.bin.utils import api_post, json_error_response
from cuckoo.web.controllers.analysis.analysis import AnalysisController

class AnalysisNetworkApi:
    @staticmethod
    def _request_response(report, protocol, request_index):
        network = report["analysis"]["network"][protocol][request_index]
        if "path" in network:
            request = open(network["path"], "rb").read()
            response = ""
        elif "reqpath" in network:
            request = open(network["reqpath"], "rb").read()
            response = open(network["resppath"], "rb").read()
        return base64.b64encode(request), base64.b64encode(response)

    @api_post
    def http_data(request, body):
        task_id = body.get("task_id", None)
        request_body = body.get("request_body", False)
        protocol = body.get("protocol", None)
        request_index = body.get("request_index", None)

        if not task_id or not isinstance(request_index, int):
            return json_error_response("missing task_id or valid request_index")

        try:
            report = AnalysisController.get_report(task_id)

            if request_body:
                # @TO-DO: parse raw http request data, filter out body
                req = ""
                resp = report["analysis"]["network"]["http"][request_index]["data"]
            else:
                req, resp = AnalysisNetworkApi._request_response(
                    report, protocol, request_index
                )

            return JsonResponse({
                "request": req,
                "response": resp,
            }, safe=False)
        except Exception as e:
            return json_error_response("error: %s" % str(e))
