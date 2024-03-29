import mysql.connector
import pytest
import socket
import threading
import time
from httplib2 import Http
from json import dumps
import requests

_total = 0
_executed = 0
_pass = 0
_fail = 0
_skip = 0
_error = 0
_xpass = 0
_xfail = 0
_current_error = ""
_suite_name = None
_test_name = None
_test_status = None
_test_start_time = None
_excution_time = 0
_duration = 0
_previous_suite_name = "None"
_initial_trigger = True
_spass_tests = 0
_sfail_tests = 0
_sskip_tests = 0
_serror_tests = 0
_sxfail_tests = 0
_sxpass_tests = 0
pytest_historic = False
pname = None
con = None
ocon = None
id = None
host = None
edesc = None
versions = None


def pytest_addoption(parser):
    group = parser.getgroup('phistoric')
    group.addoption(
        '--historic',
        action='store',
        dest='historic',
        default="False",
        help='Enable or disable pushing results to mysql'
    )
    group.addoption(
        '--hshost',
        action='store',
        dest='hshost',
        default="localhost",
        help='MySQL hosted machine ip address'
    )
    group.addoption(
        '--hsname',
        action='store',
        dest='hsname',
        default="superuser",
        help='MYSQL credentials: User name'
    )
    group.addoption(
        '--hspwd',
        action='store',
        dest='hspwd',
        default="passw0rd",
        help='MYSQL credentials: Password'
    )
    group.addoption(
        '--hname',
        action='store',
        dest='hname',
        help='Project Name'
    )
    group.addoption(
        '--hdesc',
        action='store',
        dest='hdesc',
        help='Execution description'
    )


@pytest.hookimpl()
def pytest_sessionstart(session):
    global pytest_historic, pname, host, edesc
    pytest_historic = session.config.option.historic

    if pytest_historic == "False":
        return

    host = session.config.option.hshost
    uname = session.config.option.hsname
    pwd = session.config.option.hspwd
    pname = session.config.option.hname
    edesc = session.config.option.hdesc

    global con
    con = connect_to_mysql_db(host, uname, pwd, pname)
    global ocon
    ocon = connect_to_mysql_db(host, uname, pwd, "pytesthistoric")
    # insert values into execution table
    global id
    id = insert_into_execution_table(con, ocon, edesc, 0, 0, 0, 0, 0, 0, 0, 0, pname)


def pytest_runtest_setup(item):
    if pytest_historic == "False":
        return

    global _test_start_time
    _test_start_time = time.time()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield

    if pytest_historic == "False":
        return

    rep = outcome.get_result()

    global _suite_name
    _suite_name = rep.nodeid.split("::")[0]

    if _initial_trigger:
        update_previous_suite_name()
        set_initial_trigger()

    if str(_previous_suite_name) != str(_suite_name):
        insert_suite_results(_previous_suite_name)
        update_previous_suite_name()
        reset_counts()
    else:
        update_counts(rep)

    if rep.when == "call" and rep.passed:
        if hasattr(rep, "wasxfail"):
            increment_xpass()
            update_test_status("xPASS")
            global _current_error
            update_test_error("")
        else:
            increment_pass()
            update_test_status("PASS")
            update_test_error("")

    if rep.failed:
        if getattr(rep, "when", None) == "call":
            if hasattr(rep, "wasxfail"):
                increment_xpass()
                update_test_status("xPASS")
                update_test_error("")
            else:
                increment_fail()
                update_test_status("FAIL")
                if rep.longrepr:
                    for line in rep.longreprtext.splitlines():
                        exception = line.startswith("E   ")
                        if exception:
                            update_test_error(line.replace("E    ", ""))
        else:
            increment_error()
            update_test_status("ERROR")
            if rep.longrepr:
                for line in rep.longreprtext.splitlines():
                    update_test_error(line)

    if rep.skipped:
        if hasattr(rep, "wasxfail"):
            increment_xfail()
            update_test_status("xFAIL")
            if rep.longrepr:
                for line in rep.longreprtext.splitlines():
                    exception = line.startswith("E   ")
                    if exception:
                        update_test_error(line.replace("E    ", ""))
        else:
            increment_skip()
            update_test_status("SKIP")
            if rep.longrepr:
                for line in rep.longreprtext.splitlines():
                    update_test_error(line)


def pytest_runtest_teardown(item, nextitem):
    if pytest_historic == "False":
        return

    _test_end_time = time.time()

    global _test_name
    _test_name = item.name

    global _duration
    try:
        _duration = _test_end_time - _test_start_time
    except Exception as e:
        print(e)
        _duration = 0

    # create list to save content
    insert_test_results()


def pytest_sessionfinish(session):
    if pytest_historic == "False":
        return

    insert_suite_results(_suite_name)
    reset_counts()


def post_webhook(results_url, failures_url, build_version, summary, webhook_url):
    """Hangouts Chat incoming webhook quickstart."""
    url = webhook_url
    msg = f'Build: {build_version}\n{summary}\nResults: {results_url}\nFailures: {failures_url}'
    bot_message = {
        'text': msg}

    message_headers = {'Content-Type': 'application/json; charset=UTF-8'}

    http_obj = Http()

    response = http_obj.request(
        uri=url,
        method='POST',
        headers=message_headers,
        body=dumps(bot_message),
    )

    print(response)


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def upload_report(version_file, report_file):
    url = f'http://10.240.0.87:5000/upload-pytest-results'
    files = {'version_file': open(version_file, 'rb'),
             'report_file': open(report_file, 'rb')}
    requests.post(url, files=files)


def update_description(con, eid, description):
    cursorObj = con.cursor()
    sql = "UPDATE TB_EXECUTION SET Execution_Desc=%s WHERE Execution_Id=%s;" % (description, eid)
    cursorObj.execute(sql)
    con.commit()


@pytest.hookimpl(hookwrapper=True)
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    global host, pname, edesc, versions

    yield

    if pytest_historic == "False":
        return

    global _excution_time
    _excution_time = time.time() - terminalreporter._sessionstarttime

    # global _total
    # _total =  _pass + _fail + _xpass + _xfail + _skip + _error

    global _executed
    _executed = _pass + _fail + _xpass + _xfail

    version_file = None
    report_file = None
    pipeline_link = ""

    if hasattr(config, '_metadata') and 'versions' in config._metadata.keys():
        versions = config._metadata['versions']
    if hasattr(config, '_metadata') and 'sw_version' in config._metadata.keys():
        sw_version = config._metadata['sw_version']
    if hasattr(config, '_metadata') and 'version_file' in config._metadata.keys():
        version_file = config._metadata['version_file']
    if hasattr(config, '_metadata') and 'report_file' in config._metadata.keys():
        report_file = config._metadata['report_file']
    if hasattr(config, '_metadata') and 'pipeline_link' in config._metadata.keys():
        pipeline_link = config._metadata['pipeline_link']

    # update_description(con, id, sw_version)

    if version_file and report_file:
        upload_report(version_file, report_file)

    update_execution_table(con, ocon, id, int(_executed), int(_pass), int(_fail), int(_skip), int(_xpass), int(_xfail),
                           str(_error), round(_excution_time, 2), str(pname), versions, pipeline_link)

    webhook_url = get_webhook(con, ocon, pname)
    if webhook_url:

        hostname = f'{get_ip()}:5000' if host == "localhost" else host
        summary = f"{_pass} passed"
        if _fail:
            summary += f", {_fail} failed"
        if _xfail:
            summary += f", {_xfail} xfailed"
        if _xpass:
            summary += f", {_xpass} xpassed"
        if _skip:
            summary += f", {_skip} skipped"
        if _error:
            summary += f", {_error} error(s)"
        summary += f" in {round(_excution_time, 2)}s"
        port = ":5000" if ":5000" not in hostname else ""
        results_url = f'http://{hostname}{port}/{pname}/metrics/{id}#'
        failures_url = f'http://{hostname}{port}/{pname}/failures/{id}'
        t = threading.Thread(target=post_webhook, args=(results_url, failures_url, edesc, summary, webhook_url))
        try:
            t.start()
        except Exception as e:
            print(e)


def insert_suite_results(name):
    _sexecuted = _spass_tests + _sfail_tests + _sxpass_tests + _sxfail_tests
    insert_into_suite_table(con, id, str(name), _sexecuted, _spass_tests, _sfail_tests, _sskip_tests, _sxpass_tests,
                            _sxfail_tests, _serror_tests)


def insert_test_results():
    full_name = str(_suite_name) + " - " + str(_test_name)
    insert_into_test_table(con, id, full_name, str(_test_status), round(_duration, 2), str(_current_error))


def set_initial_trigger():
    global _initial_trigger
    _initial_trigger = False


def update_previous_suite_name():
    global _previous_suite_name
    _previous_suite_name = _suite_name


def update_counts(rep):
    global _sfail_tests, _spass_tests, _sskip_tests, _serror_tests, _sxfail_tests, _sxpass_tests

    if rep.when == "call" and rep.passed:
        if hasattr(rep, "wasxfail"):
            _sxpass_tests += 1
        else:
            _spass_tests += 1

    if rep.failed:
        if getattr(rep, "when", None) == "call":
            if hasattr(rep, "wasxfail"):
                _sxpass_tests += 1
            else:
                _sfail_tests += 1
        else:
            _serror_tests += 1

    if rep.skipped:
        if hasattr(rep, "wasxfail"):
            _sxfail_tests += 1
        else:
            _sskip_tests += 1


def reset_counts():
    global _sfail_tests, _spass_tests, _sskip_tests, _serror_tests, _sxfail_tests, _sxpass_tests
    _spass_tests = 0
    _sfail_tests = 0
    _sskip_tests = 0
    _serror_tests = 0
    _sxfail_tests = 0
    _sxpass_tests = 0


def reset_suite_counts():
    global _fail, _pass, _skip, _error, _xfail, _xpass
    _pass = 0
    _fail = 0
    _skip = 0
    _error = 0
    _xfail = 0
    _xpass = 0


def update_test_error(msg):
    global _current_error
    _current_error = msg


def update_test_status(status):
    global _test_status
    _test_status = status


def increment_xpass():
    global _xpass
    _xpass += 1


def increment_xfail():
    global _xfail
    _xfail += 1


def increment_pass():
    global _pass
    _pass += 1


def increment_fail():
    global _fail
    _fail += 1


def increment_skip():
    global _skip
    _skip += 1


def increment_error():
    global _error
    _error += 1


'''

# * # * # * # * Re-usable methods out of class * # * # * # * #

'''


def connect_to_mysql_db(host, user, pwd, db):
    try:
        mydb = mysql.connector.connect(
            host=host,
            user=user,
            passwd=pwd,
            database=db
        )
        return mydb
    except Exception:
        print("Couldn't connect to Database")
        print(Exception)


def insert_into_execution_table(con, ocon, name, executed, passed, failed, skip, xpass, xfail, error, ctime,
                                projectname):
    cursorObj = con.cursor()
    # rootCursorObj = ocon.cursor()
    sql = "INSERT INTO TB_EXECUTION (Execution_Id, Execution_Date, Execution_Desc, Execution_Executed, Execution_Pass, Execution_Fail, Execution_Skip, Execution_XPass, Execution_XFail, Execution_Error, Execution_Time) VALUES (%s, now(), %s, %s, %s, %s, %s, %s, %s, %s, %s);"
    val = (0, name, executed, passed, failed, skip, xpass, xfail, error, ctime)
    cursorObj.execute(sql, val)
    con.commit()
    cursorObj.execute(
        "SELECT Execution_Id, Execution_Pass, Execution_Executed FROM TB_EXECUTION ORDER BY Execution_Id DESC LIMIT 1;")
    rows = cursorObj.fetchone()
    # update robothistoric.tb_project table
    # rootCursorObj.execute("UPDATE TB_PROJECT SET Last_Updated = now(), Total_Executions = %s, Recent_Pass_Perc =%s WHERE Project_Name='%s';" % (rows[0], float("{0:.2f}".format((rows[1]/rows[2]*100))), projectname))
    # ocon.commit()
    return str(rows[0])


def get_webhook(con, ocon, projectname):
    rootCursorObj = ocon.cursor()
    sql = "SELECT Project_Webhook FROM TB_PROJECT WHERE Project_Name = %s;"
    val = (projectname,)
    rootCursorObj.execute(sql, val)
    webhook_url = rootCursorObj.fetchone()[0]
    return webhook_url


def update_execution_table(con, ocon, eid, executed, passed, failed, skip, xpass, xfail, error, duration, projectname,
                           versions, pipeline_link):
    cursorObj = con.cursor()
    rootCursorObj = ocon.cursor()
    sql = "UPDATE TB_EXECUTION SET Execution_Executed=%s, Execution_Pass=%s, Execution_Fail=%s, Execution_Skip=%s, Execution_XPass=%s, Execution_XFail=%s, Execution_Error=%s, Execution_Time=%s, Execution_Version='%s', Pipeline_Link='%s' WHERE Execution_Id=%s;" % (
        executed, passed, failed, skip, xpass, xfail, error, duration, versions, pipeline_link, eid)
    print(sql)
    cursorObj.execute(sql)
    con.commit()
    cursorObj.execute("SELECT Execution_Pass, Execution_Executed FROM TB_EXECUTION ORDER BY Execution_Id DESC LIMIT 1;")
    rows = cursorObj.fetchone()
    cursorObj.execute("SELECT COUNT(*) FROM TB_EXECUTION;")
    execution_rows = cursorObj.fetchone()
    # update robothistoric.tb_project table
    if rows[1] != 0:
        rootCursorObj.execute(
            "UPDATE TB_PROJECT SET Last_Updated = now(), Total_Executions = %s, Recent_Pass_Perc =%s WHERE Project_Name='%s';" % (
                execution_rows[0], float("{0:.2f}".format((rows[0] / rows[1] * 100))), projectname))
    else:
        rootCursorObj.execute(
            "UPDATE TB_PROJECT SET Last_Updated = now(), Total_Executions = %s, Recent_Pass_Perc =%s WHERE Project_Name='%s';" % (
                execution_rows[0], 0, projectname))
    ocon.commit()


def insert_into_suite_table(con, eid, name, executed, passed, failed, skip, xpass, xfail, error):
    cursorObj = con.cursor()
    sql = "INSERT INTO TB_SUITE (Suite_Id, Execution_Id, Suite_Name, Suite_Executed, Suite_Pass, Suite_Fail, Suite_Skip, Suite_XPass, Suite_XFail, Suite_Error) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    val = (0, eid, name, executed, passed, failed, skip, xpass, xfail, error)
    cursorObj.execute(sql, val)
    # Skip commit to avoid load on db (commit once execution is done as part of close)
    # con.commit()


def insert_into_test_table(con, eid, test, status, duration, msg):
    global _fail, _sfail_tests, _xfail, _sxfail_tests
    cursorObj = con.cursor()
    sql = "SELECT count(Test_Name) FROM TB_TEST WHERE Test_Name = %s and Execution_Id = %s"
    val = (test, eid)
    cursorObj.execute(sql, val)
    count = cursorObj.fetchone()[0]
    if count == 0:
        sql = "INSERT INTO TB_TEST (Test_Id, Execution_Id, Test_Name, Test_Status, Test_Time, Test_Error) VALUES (%s, %s, %s, %s, %s, %s)"
        val = (0, eid, test, status, duration, msg)
        cursorObj.execute(sql, val)
    else:
        sql = "SELECT Test_Status FROM TB_TEST  WHERE Test_Name = %s and Execution_Id = %s"
        val = (test, eid)
        cursorObj.execute(sql, val)
        prev_status = cursorObj.fetchone()[0]
        if prev_status == "FAIL":
            _fail -= 1
            _sfail_tests -= 1
        else:
            _xfail -= 1
            _sxfail_tests -= 1
        sql = "UPDATE TB_TEST SET Test_Status = %s, Test_Time = %s, Test_Error = %s WHERE Test_Name = %s and Execution_Id = %s"
        val = (status, duration, msg, test, eid)
        cursorObj.execute(sql, val)

    # Skip commit to avoid load on db (commit once execution is done as part of close)
    # con.commit()
