# pytest-historic-hook

Hook to push pytest execution results to MySQL (for Pytest Historic report)

![PyPI version](https://badge.fury.io/py/pytest-historic-hook.svg)
[![Downloads](https://pepy.tech/badge/pytest-historic-hook)](https://pepy.tech/project/pytest-historic-hook)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)
![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)
![Open Source Love png1](https://badges.frapsoft.com/os/v1/open-source.png?v=103)
[![HitCount](http://hits.dwyl.io/adiralashiva8/pytest-historic-hook.svg)](http://hits.dwyl.io/adiralashiva8/pytest-historic-hook)

---

## Installation

 - Install `pytest-historic-hook`

    ```
    pip install pytest-historic-hook
    ```

---

## Usage

   Pytest Historic report required following information, users must pass respective info while using hook

    - --hshost --> mysql hosted machine ip address (default: localhost)
    - --hsname --> mysql user name (default: superuser)
    - --hspwd --> mysql password (default: passw0rd)
    - --hname --> project name in pytest historic
    - --hdesc --> execution info


 - Use `pytest-historic-hook` while executing tests

   ```
   > pytest --historic=True
    --hshost="<SQL_HOSTED_IP:3306>"
    --hsname="<NAME>"
    --hspwd="<PWD>"
    --hname="<PROJECT-NAME>"
    --hdesc="<EXECUTION-INFO>"
   ```

   __Example:__
   ```
   > pytest --historic=True
    --hshost="10.30.2.150:3306"
    --hsname="admin"
    --hspwd="Welcome1!"
    --hname="projec1"
    --hdesc="Smoke test on v1.0" <suite>
   ```
---

> For more info refer to [pytest-historic](https://github.com/adiralashiva8/pytest-historic)