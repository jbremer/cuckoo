# Copyright (C) 2016 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import django
import logging
import os
import tempfile
import zipfile
import json

from StringIO import StringIO
import pymongo
import mock

from cuckoo.core.database import Database, Task, Sample
from cuckoo.common.files import Folders, Files
from cuckoo.common.constants import CUCKOO_VERSION
from cuckoo.misc import cwd, set_cwd
from cuckoo.processing.static import Static

from django.http.response import StreamingHttpResponse
from django.conf import settings

logging.basicConfig(level=logging.DEBUG)

# These have to be imported after setting the django settings module
# environment variable as they're using the settings.MONGO variable.
from cuckoo.web.controllers.analysis.routes import AnalysisRoutes

CUCKOO_CONF = """
[database]
connection =

rooter = /tmp/cuckoo-rooter
"""

REPORTING_CONF = """
[mongodb]
enabled = on
db = cuckootest
store_memdump = yes
paginate = 100

[elasticsearch]
enabled = off

[moloch]
enabled = off
"""

ROUTING_CONF = """
[routing]
route = none
internet = none
drop = off

[inetsim]
enabled = off

[tor]
enabled = off

[vpn]
enabled = off
"""

class TestWebInterface(object):
    def setup(self):
        self.tmp_dir = tempfile.mkdtemp()
        set_cwd(self.tmp_dir)

        Folders.create(cwd(), ["conf", "web", "storage"])

        Files.create(cwd(), "conf/cuckoo.conf", CUCKOO_CONF)
        Files.create(cwd(), "conf/reporting.conf", REPORTING_CONF)
        Files.create(cwd(), "conf/routing.conf", ROUTING_CONF)
        Files.create(cwd(), "web/.secret_key", "A"*40)
        Files.create(cwd(), "web/local_settings.py", "")

        django.setup()
        self.db = DatabaseInterface()

        os.environ["CUCKOO_APP"] = "web"
        os.environ["CUCKOO_CWD"] = cwd()

        self.db.add_task(analysis_id=1)

    def test_index(self, client):
        assert client.get("/").status_code == 200

    def analysis_recent(self, client):
        assert client.get("/analysis/").status_code == 200

    def test_analysis_detail(self, client):
        pages = [
            "summary",
            "static",
            "behavior",
            "network",
            "misp",
            "dropped_files",
            "dropped_buffers",
            "procmemory",
            "options"
        ]

        for page in pages:
            assert client.get("/analysis/1/%s/" % page).status_code == 200

    def test_analysis_reboot(self, client):
        assert client.get("/analysis/%d/reboot/" % 1).status_code == 200

        db = Database()
        assert db.view_task(task_id=2).id == 2

    def test_analysis_latest(self, client):
        r = client.get("/analysis/latest/")
        assert r.status_code in (301, 302)

    def test_analysis_compare(self, client):
        self.db.add_report(analysis_id=2)

        assert client.get("/analysis/1/compare/").status_code == 200

    def test_analysis_remove(self, client):
        r = client.get("/analysis/remove/1/")
        assert r.status_code == 200
        assert "thanks for all the fish" in r.content.lower()
        assert Database().view_task(1) is None

    def test_analysis_compare_with(self, client):
        self.db.add_task(analysis_id=2)
        assert client.get("/analysis/1/compare/2/").status_code == 200

    # def test_analysis_chunk(self, client):
    #     # url(r"^chunk/(?P<task_id>\d+)/(?P<pid>\d+)/(?P<pagenum>\d+)/$", views.chunk),
    #     # url(r"^filtered/(?P<task_id>\d+)/(?P<pid>\d+)/(?P<category>\w+)/$", views.filtered_chunk),
    #     # @TODO: requires GridFS
    #     r = client.get("/analysis/latest/")

    # def test_analysis_search_behavior(self, client):
    #     # url(r"^search/(?P<task_id>\d+)/$", views.search_behavior),
    #     # @TODO: figure out how to deal with `results_db.calls.find({`
    #
    #     r = client.post("/analysis/search/1/", data={
    #         "search": ""
    #     })
    #     assert r

    # def test_analysis_search(self, client):
    #     # @TODO: requires ElasticSearch
    #     #
    #     r = client.get("/analysis/search/")
    #     assert r

    def test_analysis_pending(self, client):
        Database().set_status(1, "pending")
        r = client.get("/analysis/pending/")
        assert r.status_code == 200
        assert "tests/files/pdf0.pdf" in r.content

    # def test_analysis_pcapstream(self, client):
    #     # url(r"^(?P<task_id>\d+)/pcapstream/(?P<conntuple>[.,\w]+)/$", views.pcapstream),
    #     # @TODO: deal with GridFS
    #     r = client.get("/1/pcapstream/?udp/")
    #     assert r

    def test_analysis_import(self, client):
        r = client.get("/analysis/import/")
        assert r.status_code == 200

    def test_analysis_export(self, client):
        assert client.get("/analysis/%d/export/" % 1).status_code == 200

        r = client.post("/analysis/%d/export/" % 1, data={
            "dirs": ["shots", "memory", "logs", "reports", "network"],
            "files": [
                "analysis.json", "dump_sorted.pcap", "cuckoo.log",
                "reboot.json", "tlsmaster.txt", "binary", "analysis.log",
                "task.json", "action.json", "files.json"
            ]})

        assert r.has_header("content-type") is True
        assert r._headers["content-type"][1] == "application/zip"

        zip = StringIO()
        zip.write(r.content)
        zip.seek(0)

        zip = zipfile.ZipFile(zip)
        assert zip.read("reports/report.json") == ""

    def test_submission_index(self, client):
        r = client.get("/submission/")
        assert r.status_code == 200

    def test_summary_office1(self, request):
        with mock.patch("cuckoo.web.controllers.analysis.analysis.AnalysisController") as ac:
            ac._get_report.return_value = {
                "static": {
                    "office": {
                        "macros": [
                            {
                                "filename": "MACRO FILENAME",
                                "stream": "MACRO STREAM",
                                "orig_code": "MACRO CODE OBFUSCATED",
                                "deobf": "MACRO CODE DEOBFUSCATED",
                            },
                        ],
                    },
                },
            }

            r = AnalysisRoutes.detail(request, 1, "static").content
            assert "MACRO FILENAME" in r
            assert "MACRO STREAM" in r
            assert "MACRO CODE OBFUSCATED" in r
            assert "MACRO CODE DEOBFUSCATED" in r

    def test_summary_office2(self, request):
        s = Static()
        s.set_task({
            "category": "file",
            "package": "doc",
            "target": "createproc1.docm",
        })
        s.file_path = "tests/files/createproc1.docm"

        with mock.patch("cuckoo.web.controllers.analysis.analysis.AnalysisController") as ac:
            ac._get_report.return_value = {
                "static": s.run(),
            }
            r = AnalysisRoutes.detail(request, 1, "static").content
            assert "ThisDocument" in r
            assert "Sub AutoOpen" in r
            assert "process.Create" in r
            assert "notepad.exe" in r

class TestApiInterface(object):
    def setup(self):
        self.tmp_dir = tempfile.mkdtemp()
        set_cwd(self.tmp_dir)

        Folders.create(cwd(), ["conf", "web", "storage"])

        Files.create(cwd(), "conf/cuckoo.conf", CUCKOO_CONF)
        Files.create(cwd(), "conf/reporting.conf", REPORTING_CONF)
        Files.create(cwd(), "conf/routing.conf", ROUTING_CONF)
        Files.create(cwd(), "web/.secret_key", "A"*40)
        Files.create(cwd(), "web/local_settings.py", "")

        django.setup()
        self.db = DatabaseInterface()

        os.environ["CUCKOO_APP"] = "web"
        os.environ["CUCKOO_CWD"] = cwd()

        self.db.add_task(analysis_id=1)

    def test_analysis_tasks_list(self, client):
        for i in range(2, 6):
            self.db.add_task(analysis_id=i)

        # test limit filter
        data = {"limit": 3, "offset": 0, "owner": "", "status": "reported"}

        r = self._post(client, "/analysis/api/tasks/list/", data)
        assert len(r["data"]["tasks"]) == 3

        # test offset filter
        data = {"limit": 1, "offset": 1, "owner": "", "status": "reported"}
        r = self._post(client, "/analysis/api/tasks/list/", data)
        assert r["data"]["tasks"][0]["id"] == 2

        # test status filter
        Database().set_status(task_id=3, status="pending")
        data = {"limit": 5, "offset": 0, "owner": "", "status": "pending"}
        r = self._post(client, "/analysis/api/tasks/list/", data)
        assert r["data"]["tasks"][0]["id"] == 3

    def test_analysis_tasks_info(self, client):
        self.db.add_task(analysis_id=2)

        data = {"task_ids": [1, 2]}
        r = self._post(client, "/analysis/api/tasks/info/", data)

        assert len(r["data"].keys()) == 2
        assert r["data"]["1"]["id"] == 1
        assert r["data"]["2"]["id"] == 2

    def test_analysis_tasks_recent(self, client):
        for i in range(2, 6):
            self.db.add_task(analysis_id=i)

        # test normal operation
        data = {
            "limit": 5,
            "offset": 0,
            "cats": [],
            "packs": [],
            "score": ""
        }

        r = self._post(client, "/analysis/api/tasks/recent/", data)
        assert len(r["data"]) == 5

        # test category filter
        # data = {
        #     "limit": 5,
        #     "offset": 0,
        #     "cats": ["file"],
        #     "packs": [],
        #     "score": ""
        # }
        #
        # r = self._post(client, "/analysis/api/tasks/recent/", data)

    def test_cuckoo_status(self, client):
        r = client.get("/cuckoo/api/status/")
        content = json.loads(r.content)
        assert r.status_code == 200
        assert content["data"]["version"] == CUCKOO_VERSION

    def test_cuckoo_vpn_status(self, client):
        r = client.get("/cuckoo/api/vpn/status/")
        assert r.status_code == 200

    def test_files_view(self, client):
        """
        Function behaviour is depended on the type
        of report that is currently being tested.
        """
        md5 = "c57bd2a0b85befb9f33175ac0b5fa710"
        r = client.get("/files/api/view/md5/%s/" % md5)
        content = json.loads(r.content)
        assert content["data"]["sample"]["id"] == 1
        assert "PDF document" in content["data"]["sample"]["file_type"]

        sha256 = "fbb40b1e2773cb4b728733b6db3c8cc5a9b38576d7ebea935d3a0e158bda1114"
        r = client.get("/files/api/view/sha256/%s/" % sha256)
        content = json.loads(r.content)
        assert content["data"]["sample"]["id"] == 1
        assert "PDF document" in content["data"]["sample"]["file_type"]

        r = client.get("/files/api/view/id/1/")
        content = json.loads(r.content)
        assert content["data"]["sample"]["id"] == 1
        assert "PDF document" in content["data"]["sample"]["file_type"]

    def test_files_get(self, client):
        """
        Function behaviour is depended on the type
        of report that is currently being tested.
        """
        sha256 = "fbb40b1e2773cb4b728733b6db3c8cc5a9b38576d7ebea935d3a0e158bda1114"
        r = client.get("/files/api/get/%s/" % sha256)
        assert r.content.startswith("%PDF")

    def test_analysis_task_delete(self, client):
        r = client.get("/analysis/api/tasks/delete/1/")
        assert r.status_code == 200
        assert Database().view_task(task_id=1) is None

    def test_analysis_task_info(self, client):
        r = client.get("/analysis/api/task/info/1/")
        content = json.loads(r.content)
        assert r.status_code == 200
        assert content["data"]["task"]["id"] == 1

    def test_analysis_task_reschedule(self, client):
        r = client.get("/analysis/api/task/reschedule/1/1/")
        content = json.loads(r.content)
        assert r.status_code == 200

        rescheduled = Database().view_task(task_id=2)
        assert rescheduled is not None
        assert rescheduled.status == "pending"

    def test_analysis_task_report(self, client):
        # test html format
        r = client.get("/analysis/api/task/report/1/html/")
        assert r.status_code == 200
        assert len(r.getvalue()) >= 10

        # test json format
        r = client.get("/analysis/api/task/report/1/json/")
        assert r.status_code == 200
        assert r.getvalue() == ""

        # @TO-DO: test bz2/gz/tar formats

    def test_analysis_task_rereport(self, client):
        r = client.get("/analysis/api/task/rereport/1/")
        assert r.status_code == 200

        task = Database().view_task(task_id=1)
        assert task.status == "completed"

    def test_analysis_task_screenshots(self, client):
        # get all screenshots
        r = client.get("/analysis/api/task/screenshots/1/")
        assert isinstance(r, StreamingHttpResponse) is True
        assert r.status_code == 200

        # get specific screenshot
        r = client.get("/analysis/api/task/screenshots/1/0001/")
        assert r.status_code == 200

    def test_analysis_task_export_estimate_size(self, client):
        res1 = self._post(client, "/analysis/api/task/export_estimate_size/", data={
            "task_id": 1,
            "dirs": ["shots", "memory", "logs", "reports", "network"],
            "files": ["analysis.json"]
        })

        res2 = self._post(client, "/analysis/api/task/export_estimate_size/", data={
            "task_id": 1,
            "dirs": ["memory", "logs", "reports", "network"],
            "files": ["analysis.json"]
        })

        assert res1["data"]["size"]["size"] != res2["data"]["size"]["size"]

    # def test_analysis_task_get_files(self, client):
    #     # @TODO: finish this test (after submit has been properly implemented @ front-end)
    #     r = self._post(client, "/analysis/api/task/get_files/", data={
    #         "task_id": 1
    #     })

    def test_analysis_task_behavior_get_processes(self, client):
        r = self._post(client, "/analysis/api/task/behavior_get_processes/", data={
            "task_id": 1
        })
        assert len(r["data"]["data"]) >= 1

    # def test_analysis_task_behavior_get_watcher(self, client):
    #     """
    #     Function behaviour depends on the type of report that
    #     is currently being tested.
    #     """
    #     r = self._post(client, "/analysis/api/task/behavior_get_watcher/", data={
    #         "task_id": 1,
    #         "pid": 576,
    #         "watcher": ""
    #     })
    #     assert len(r["data"]["data"]) >= 1

    # def test_analysis_task_network_http_response_data(self, client):
    #     # @TODO: provide the report types 'with http', 'without' traffic in order to test this
    #     r = self._post(client, "/analysis/api/task/network_http_response_data/", data={
    #         "task_id": 1,
    #         "request_index": 0
    #     })

    def _post(self, client, url, data, validate=True):
        data = json.dumps(data)
        r = client.post(url, data=data,
                        content_type='application/json',
                        HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        content = json.loads(r.content)
        if validate:
            assert r.status_code == 200
            assert content["status"] is True
        return content

class DatabaseInterface:
    def __init__(self):
        Database().connect()
        self.mongo = settings.MONGO
        self.mongo.analysis.drop()

    def add_report(self, analysis_id):
        analysis_path = "%s/storage/analyses/%d/" % (cwd(), analysis_id)
        zf = zipfile.ZipFile("tests/files/report.json.zip")
        data = zf.read("report.json")
        report = json.loads(data)
        report["info"]["id"] = analysis_id
        report["info"]["analysis_path"] = analysis_path
        report["shots"] = []

        self.mongo.analysis.insert_one(report)

        report = self.mongo.analysis.find_one({
            "info.id": int(analysis_id)
        }, sort=[("_id", pymongo.DESCENDING)])

        assert report["info"]["id"] == analysis_id

    def add_task(self, analysis_id):
        db = Database()
        session = db.Session()
        analysis_path = "%s/storage/analyses/%d/" % (cwd(), analysis_id)
        Folders.copy("tests/files/sample_analysis_storage", analysis_path)

        task_id = Database().add_path(
            file_path="tests/files/pdf0.pdf",
            timeout=0,
            package="exe",
        )

        task = db.view_task(task_id)
        db.set_status(task_id, "reported")
        task.package = None
        task.target = analysis_path + "binary"
        session.commit()
        session.flush()

        self.add_report(analysis_id=analysis_id)

        _binaries = os.path.join(cwd(), "storage", "binaries")
        if not os.path.exists(_binaries):
            os.makedirs(_binaries)
        Files.copy("tests/files/pdf0.pdf", "%s/fbb40b1e2773cb4b728733b6db3c8cc5a9b38576d7ebea935d3a0e158bda1114" % _binaries)

        return task
