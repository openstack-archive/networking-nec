# Copyright 2015-2016 NEC Corporation.  All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import eventlet
import requests
eventlet.import_patched('requests.__init__')
import base64
import copy
import datetime
import hashlib
import hmac
import re
import six
import six.moves.urllib.parse as urlparse
import sys

from oslo_log import log as logging
from oslo_serialization import jsonutils

from networking_nec._i18n import _, _LI, _LW, _LE
from networking_nec.plugins.necnwa.common import config as nwaconf


LOG = logging.getLogger(__name__)

cfgNWA = nwaconf.cfg.CONF.NWA

date_header_format = '%a, %d %b %Y %H:%M:%S GMT'
CRLF = '\x0D\x0A'

UMF_API_VERSION = '2.0.2.1.201502'
OLD_UMF_API_VERSION = '2.0.2.201402'

rest_api_debug = False


class NwaException(Exception):
    '''Raised when there is an error in Nwa. '''
    def __init__(self, http_status, errmsg, orgexc=None):
        self.http_status = http_status
        self.errmsg = errmsg
        self.orgexc = orgexc

    def __str__(self):
        return 'http status: %s, %s' % (self.http_status, self.errmsg)


class NwaWorkflow(object):
    '''Workflow definition of NWA. '''
    _path_prefix = '/umf/workflow/'
    _nameid_initialized = False
    _nameid = {
        'CreateTenantNW': '40030001',
        'DeleteTenantNW': '40030016',
        'CreateVLAN': '40030002',
        'DeleteVLAN': '40030018',
        'CreateGeneralDev': '40030021',
        'DeleteGeneralDev': '40030022',
        'CreateTenantFW': '40030019',
        'UpdateTenantFW': '40030009',
        'DeleteTenantFW': '40030020',
        'SettingNAT': '40030005',
        'DeleteNAT': '40030011',
        'SettingFWPolicy': '40030081',
        'SettingLBPolicy': '40030091',
        'CreateTenantLB': '40030092',
        'UpdateTenantLB': '40030093',
        'DeleteTenantLB': '40030094',
    }
    _errno = {
        '1': 'Unknown parent node',
        '2': 'Already exists',
        '3': 'Resources are insufficient',
        '4': 'Unknown node',
        '5': 'Can not access the file',
        '6': 'Unknown parameters',
        '7': 'Undefined parameters',
        '8': 'Permission error',
        '9': 'It is not possible to remove because it is in use',
        '10': 'An error occurred while deleting the node',
        '11': 'Execution environment is invalid',
        '31': 'Specified IP subnet does not exist',
        '32': 'Specified IP address does not exist',
        '33': 'Can not allocate IP subnet to be paid out',
        '34': 'IP subnet will not exceed the threshold',
        '101': 'An unknown error has occurred',
        '102': 'An internal error has occurred',
        '103': 'Failed to connect to CMDB',
        '104': 'Out of memory',
        '105': 'An error occurred in the select process to the CMDB',
        '106': 'An error occurred in the update process to the CMDB',
        '107': 'An error occurred in the insert process to the CMDB',
        '108': 'Input parameter is invalid',
        '109': 'An error occurred in the file processing',
        '110': 'An error occurred in the delete process to the CMDB',
        '201': 'There is no free VLAN ID',
        '202': 'Exceeded the threshold of VLAN',
        '203': 'Exceeded the threshold ot Tenant equipment',
        '204': 'Resource group is not specified in the input',
        '205': 'Tenant-ID is not specified in the input',
        '206': 'Tenant-Network is already created',
        '207': 'There is no available devices',
        '208': 'IP address depletion for assignment of LB',
        '209': 'The device in the cluster group is 0 or 2 or more',
        '210': 'The device in the cluster group is 0',
        '211': 'There is no specified resource group',
        '212': 'There is no character "/" in the resource group name',
        '213': 'Tenant-FW is not specified one',
        '214': 'Tenant-FW is specified two or more',
        '215': 'Can not be extended because there is no PFS',
        '216': 'Logical NW name is not specified',
        '217': 'There is no Registered SSL-VPN equipment',
        '218': 'Tenant network is not yet created',
        '219': 'There is no free LoadBalancer',
        '220': 'Can not get the physical server uuid',
        '221': 'There is no deletion of VLAN',
        '222': 'Tenant ID in use is still exists',
        '223': 'Tenant-FW not found',
        '224': 'There is no specified device name',
        '225': 'Can not get the information of tenant vlan',
        '226': 'There is no specified logical NW',
        '227': 'Can not get the device information of the tenant in use',
        '228': 'For updated is in use, it could not be updated',
        '229': 'For deletion is in use, it could not be deleted',
        '230': 'Exceeded the threshold',
        '231': 'Exceeded the allocation possible number',
        '232': 'Exceeded the allocation range',
        '233': 'Authentication setting is incorrect',
        '234': 'Usable IP address range setting of is invalid',
        '235': 'IP address specified is invalid',
        '236': 'There is no available for allocation Tenant FW',
        '237': 'IP address depletion for assignment of FW',
        '238': 'IP address is invalid',
        '239': 'Can not set the number of records to zero',
        '240': 'The specification does not include a payout already IP subnet',
        '241': 'Not specified LogicalPort under the same controller or domain',
        '242': 'IP address depletion for assignment of SSL',
        '243': 'IP address is invalid',
        '244': 'The type of controller is invalid',
        '245': 'Device or VDOM name is invalid specified',
        '246': 'Exceeds the upper limit of naming convention',
        '251': 'In the same tenant, scenario there are still concurrent or '
               'reservation ID',
        '252': '(unused)',
        '253': 'The preceding scenario, can not be reserved',
        '254': 'Can not get the reserved id because of the preceding scenario',
        '298': 'Resources are insufficient',
        '299': 'Unknown error',
    }

    @staticmethod
    def init(name):
        pass                                    # pragma: no cover

    @staticmethod
    def path(name):
        """Returns path of workflow.

        :param name: The name of workflow.
        """
        return '%s%s/execute' % (NwaWorkflow._path_prefix,
                                 NwaWorkflow._nameid[name])

    @staticmethod
    def name(path):
        """Returns name of workflow.

        :param name: The name of workflow.
        """
        wid = path[len(NwaWorkflow._path_prefix):-len('/execute')]
        for (name, id) in NwaWorkflow._nameid.items():
            if id == wid:
                return name
        return None

    @staticmethod
    def strerror(errno):
        """Returns error name of errno.

        :param errno: The number of error.
        """
        return NwaWorkflow._errno.get(errno)

    @staticmethod
    def get_errno_from_resultdata(data):
        resultdata = data.get('resultdata')
        if resultdata:
            errmsg = resultdata.get('ErrorMessage')
            if isinstance(errmsg, six.string_types):
                m = re.search(r'ErrorNumber=(\d+)', errmsg)
                if m:
                    return m.group(1)
                m = re.search(r'ReservationErrorCode = (\d+)', errmsg, re.M)
                if m:
                    return m.group(1)
        return None

    @staticmethod
    def update_nameid(new_nameid):
        if NwaWorkflow._nameid_initialized:
            return
        if len(new_nameid) > 0:
            NwaWorkflow._nameid = new_nameid
            NwaWorkflow._nameid_initialized = True


class RestClient(object):
    """A HTTP/HTTPS client for NEC NWA Drivers."""

    def __init__(self, host=None, port=None, use_ssl=None, auth=None,
                 umf_api_version=UMF_API_VERSION):
        """Creates a new client to some NWA.

        :param host: The host where service resides
        :param port: The port where service resides
        :param use_ssl: True to use SSL, False to use HTTP
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.auth = auth
        self.umf_api_version = umf_api_version

    def _init_default(self, kwargs, url=None, auth=None):
        if url:
            url_parts = urlparse.urlparse(url)
            if not kwargs.get('host'):
                kwargs['host'] = url_parts.hostname
            if not kwargs.get('port'):
                kwargs['port'] = url_parts.port
            if not kwargs.get('use_ssl'):
                if url_parts.scheme == 'https':
                    kwargs['use_ssl'] = True
                else:
                    kwargs['use_ssl'] = False
        if auth:
            kwargs['auth'] = auth

    def url(self, path):
        protocol = "http"
        if self.use_ssl:
            protocol = "https"
        return '%s://%s:%s%s' % (protocol, self.host, self.port, path)

    def _make_headers(self, path):
        datestr = datetime.datetime.utcnow().strftime(date_header_format)
        headers = {
            'Authorization': self.auth(datestr, path),
            'Content-Type': 'application/json',
            'Date': datestr,
            'X-UMF-API-Version': self.umf_api_version
        }
        return headers

    def _send_receive(self, method, path, body=None):
        scheme = "http"
        if self.use_ssl:
            scheme = "https"

        url = "%s://%s:%d%s" % (scheme, self.host, int(self.port), path)
        headers = self._make_headers(path)
        LOG.debug('NWA HTTP Headers %s', headers)
        res = requests.request(method, url, data=body, headers=headers,
                               verify=False, proxies={'no': 'pass'})
        return res

    def rest_api(self, method, url, body=None):
        if isinstance(body, dict):
            body = jsonutils.dumps(body, indent=4, sort_keys=True)

        if rest_api_debug:                # pragma: no cover
            LOG.debug("NWA %(method)s %(host)s:%(port)s%(url)s body=%(body)s",
                      {'method': method, 'host': self.host, 'port': self.port,
                       'url': url, 'body': body})

        status_code = -1
        try:
            res = self._send_receive(method, url, body)
            data = res.text

            if rest_api_debug:            # pragma: no cover
                LOG.debug("NWA returns: httpStatus=%(status)s body=%(data)s",
                          {'status': res.status_code,
                           'data': data})
            try:
                data = jsonutils.loads(data)
            except (ValueError, TypeError):
                pass
            status_code = int(res.status_code)
            if 200 <= status_code and status_code <= 209:
                return (status_code, data)
            else:
                msg = _("NWA failed: %(method)s %(host)s:%(port)s%(url)s "
                        "(HTTP/1.1 %(status_code)s %(reason)s) body=%(data)s")
                msg_params = {'method': method,
                              'host': self.host,
                              'port': self.port,
                              'url': url,
                              'status_code': res.status_code,
                              'reason': res.reason,
                              'data': data}
                LOG.warning(msg, msg_params)
                raise NwaException(status_code, msg % msg_params)
        except requests.exceptions.RequestException as e:
            msg = _("NWA Failed to connect %(host)s:%(port)s: %(reason)s")
            msg_params = {'host': self.host,
                          'port': self.port,
                          'reason': e}
            LOG.error(msg, msg_params)
            tback = sys.exc_info()[2]
            raise NwaException(status_code, msg % msg_params, e), None, tback

    def _report_workflow_error(self, data, errno):
        if not hasattr(self, 'post_data'):
            return ''
        post_url, post_body = self.post_data
        if isinstance(post_body, dict):
            post_body = jsonutils.dumps(post_body, indent=4, sort_keys=True)
        name = (NwaWorkflow.name(post_url) or post_url)
        reason = NwaWorkflow.strerror(errno)
        LOG.error(_LE("NWA workflow: %(name)s reason(%(errno)s)=%(reason)s "
                      "request=%(request)s, response=%(response)s"),
                  {'name': name,
                   'errno': errno,
                   'reason': reason,
                   'request': post_body,
                   'response': jsonutils.dumps(data, indent=4, sort_keys=True)
                   })

    def rest_api_return_check(self, method, url, body=None):
        status_code = 200
        try:
            name = NwaWorkflow.name(url)
            body_str = ''
            if isinstance(body, dict):
                body_str = jsonutils.dumps(body, sort_keys=True)
            if name:
                LOG.info(_LI('NWA workflow: %(name)s %(body)s'),
                         {'name': name, 'body': body_str})
            else:
                LOG.info(_LI('NWA %(method)s %(url)s %(body)s'),
                         {'method': method,
                          'url': self.url(url),
                          'body': body_str})

            status_code, data = self.rest_api(method, url, body)

            status = ''
            progress = ''
            if isinstance(data, dict) and data.get('status'):
                status = data.get('status')
                progress = data.get('progress')

            LOG.info(_LI("NWA HTTP %(code)s %(status)s %(progress)s"),
                     {'code': status_code,
                      'status': status, 'progress': progress})

            if status == 'FAILED':
                errno = NwaWorkflow.get_errno_from_resultdata(data)
                self._report_workflow_error(data, errno)
            elif status == 'SUCCESS':
                name = ''
                if hasattr(self, 'post_data'):
                    post_url, post_body = self.post_data
                    name = (NwaWorkflow.name(post_url) or post_url)
                LOG.info(_LI("NWA workflow: %(name)s %(workflow)s"),
                         {'name': name,
                          'workflow': jsonutils.dumps(data, indent=4,
                                                      sort_keys=True)
                          })
            return status_code, data

        except NwaException as e:
            status_code = e.http_status

        return status_code, None

    def get(self, url):
        return self.rest_api_return_check("GET", url)

    def post(self, url, body=None):
        return self.rest_api_return_check("POST", url, body=body)

    def put(self, url, body=None):
        return self.rest_api_return_check("PUT", url, body=body)

    def delete(self, url):
        return self.rest_api_return_check("DELETE", url)


class NwaRestClient(RestClient):
    '''Client class of NWA rest. '''

    def __init__(self, *args, **kwargs):
        c = cfgNWA
        access_key_id = kwargs.pop('access_key_id',
                                   getattr(c, 'access_key_id', None))
        secret_access_key = kwargs.pop('secret_access_key',
                                       getattr(c, 'secret_access_key', None))

        self._init_default(
            kwargs,
            url=getattr(c, 'server_url', None),
            auth=self.define_auth_function(access_key_id, secret_access_key)
        )
        super(NwaRestClient, self).__init__(*args, **kwargs)

        self.workflow_first_wait = getattr(c, 'scenario_polling_first_timer',
                                           2)
        self.workflow_wait_sleep = getattr(c, 'scenario_polling_timer', 10)
        self.workflow_retry_count = getattr(c, 'scenario_polling_count', 6)
        LOG.info(
            _LI('NWA init: host=%(host)s port=%(port)s use_ssl=%(use_ssl)s '
                'auth=%(auth)s'),
            {'host': self.host, 'port': self.port, 'use_ssl': self.use_ssl,
             'auth': self.auth}
        )
        LOG.info(_LI('NWA init: workflow wait: %(first_wait)ss + '
                     '%(wait_sleep)ss x %(retry_count)s times.'),
                 {'first_wait': self.workflow_first_wait,
                  'wait_sleep': self.workflow_wait_sleep,
                  'retry_count': self.workflow_retry_count})
        LOG.info(_LI('NWA init: umf api version: %s'),
                 self.umf_api_version)

    def define_auth_function(self, access_key_id, secret_access_key):
        def azure_auth(datestr, path):
            signature = hmac.new(
                secret_access_key,
                datestr + CRLF + path,
                hashlib.sha256
            ).digest()
            return ('SharedKeyLite %s:%s' %
                    (access_key_id,
                     base64.encodestring(signature).rstrip()))

        auth = None
        if access_key_id and secret_access_key:
            auth = azure_auth
        return auth


class Thread(object):
    def __init__(self, thread):
        self.thread = thread

    def stop(self):
        self.thread.kill()

    def wait(self):
        return self.thread.wait()


class Semaphore(object):
    lock = eventlet.semaphore.Semaphore(1)
    tenants = {}

    @classmethod
    def get_tenant_semaphore(cls, tenant_id):
        if not isinstance(tenant_id, six.string_types) or tenant_id == '':
            raise TypeError('%s is not a string' % tenant_id)
        with Semaphore.lock:
            if tenant_id not in Semaphore.tenants:
                LOG.info(_LI('create semaphore for %s'), tenant_id)
                Semaphore.tenants[tenant_id] = Semaphore()
            return Semaphore.tenants[tenant_id]

    @classmethod
    def delete_tenant_semaphore(cls, tenant_id):
        with Semaphore.lock:
            if tenant_id in Semaphore.tenants:
                LOG.info(_LI('delete semaphore for %s'), tenant_id)
                del Semaphore.tenants[tenant_id]

    @classmethod
    def any_locked(cls):
        with Semaphore.lock:
            for t in Semaphore.tenants:
                if Semaphore.tenants[t].sem.locked():
                    return True
        return False

    def __init__(self):
        self._sem = eventlet.semaphore.Semaphore(1)
        self._histrun = []
        self._histsiz = 2

    @property
    def sem(self):
        return self._sem

    @property
    def histrun(self):
        return self._histrun

    @property
    def histsiz(self):
        return self._histsiz

    def search_history(self, call, url, body):
        name = call.__name__
        for hr in self.histrun:
            if hr['call'] == name and hr['url'] == url and hr['body'] == body:
                LOG.debug('NWA search_history - hit name=%(name)s url=%(url)s '
                          'body=%(body)s',
                          {'name': name, 'url': url, 'body': body})
                return hr['http_status'], hr['rj']
        LOG.debug('NWA search_history - no hit')
        return None, None

    def push_history(self, call, url, body, http_status, rj):
        while len(self.histrun) > self.histsiz:
            self.histrun.pop()
        (hs, rb) = self.search_history(call, url, body)
        if rb is not None:
            return
        if isinstance(rj, dict) and rj.get('status') == 'SUCCESS':
            hr = {
                'call': call.__name__,
                'url': url,
                'body': body,
                'http_status': http_status,
                'rj': rj
            }
            self.histrun.insert(0, hr)
            LOG.debug('NWA push_history - hr=%s', hr)

    def create_general_dev_history(self, call, creurl, body, http_status, rj):
        name = call.__name__
        url = NwaWorkflow.path('DeleteGeneralDev')
        for hr in self.histrun:
            if hr['call'] == name and hr['url'] == url:
                create = body['CreateNW_VlanLogicalName1']
                delete = hr['body']['DeleteNW_VlanLogicalName1']
                if create == delete:
                    hr['url'], hr['body'] = None, None
                    LOG.debug('NWA delete_history - hit name=%(name)s '
                              'url=%(url)s body=%(body)s',
                              {'name': name, 'url': url, 'body': body})
        self.push_history(call, creurl, body, http_status, rj)

    def delete_general_dev_history(self, call, delurl, body, http_status, rj):
        name = call.__name__
        url = NwaWorkflow.path('CreateGeneralDev')
        for hr in self.histrun:
            if hr['call'] == name and hr['url'] == url:
                create = hr['body']['CreateNW_VlanLogicalName1']
                delete = body['DeleteNW_VlanLogicalName1']
                if create == delete:
                    hr['url'], hr['body'] = None, None
                    LOG.debug('NWA delete_history - hit name=%(name)s '
                              'url=%(url)s body=%(body)s',
                              {'name': name, 'url': url, 'body': body})
        self.push_history(call, delurl, body, http_status, rj)


class NwaClient(NwaRestClient):
    '''Client class of NWA. '''
    pool = eventlet.GreenPool()
    workflow_list_is_loaded = False

    def __init__(self, *args, **kwargs):
        load_workflow_list = kwargs.pop('load_workflow_list', True)
        super(NwaClient, self).__init__(*args, **kwargs)
        if load_workflow_list and NwaClient.workflow_list_is_loaded is False:
            self.update_workflow_list()
            NwaClient.workflow_list_is_loaded = True

    # --- Tenant Network ---

    def _create_tenant_nw(self, tenant_id, dc_resource_group_name):
        body = {
            "TenantID": tenant_id,
            "CreateNW_DCResourceGroupName": dc_resource_group_name,
            'CreateNW_OperationType': 'CreateTenantNW'
        }
        return self.post, NwaWorkflow.path('CreateTenantNW'), body

    def _delete_tenant_nw(self, tenant_id):
        body = {
            "TenantID": tenant_id,
        }
        return self.post, NwaWorkflow.path('DeleteTenantNW'), body

    # --- VLan ---

    def _create_vlan(self, tenant_id, vlan_type, ipaddr, mask, openid):
        body = {
            'TenantID': tenant_id,
            'CreateNW_VlanType1': vlan_type,
            'CreateNW_IPSubnetAddress1': ipaddr,
            'CreateNW_IPSubnetMask1': mask
        }
        if openid:
            body['CreateNW_VlanLogicalID1'] = openid
        return self.post, NwaWorkflow.path('CreateVLAN'), body

    def _delete_vlan(self, tenant_id, vlan_name, vlan_type):
        body = {
            'TenantID': tenant_id,
            'DeleteNW_VlanLogicalName1': vlan_name,
            'DeleteNW_VlanType1': vlan_type
        }
        return self.post, NwaWorkflow.path('DeleteVLAN'), body

    # --- Tenant FW ---

    def _create_tenant_fw(self, tenant_id, dc_resource_group_name,
                          vlan_devaddr, vlan_logical_name,
                          vlan_type='BusinessVLAN', router_id=None):
        body = {
            'CreateNW_DeviceType1': 'TFW',
            'TenantID': tenant_id,
            'CreateNW_Vlan_DeviceAddress1': vlan_devaddr,
            'CreateNW_VlanLogicalName1': vlan_logical_name,
            'CreateNW_VlanType1': vlan_type,
            'CreateNW_DCResourceGroupName': dc_resource_group_name
        }
        return self.post, NwaWorkflow.path('CreateTenantFW'), body

    def _update_tenant_fw(self, tenant_id, device_name, vlan_devaddr,
                          vlan_logical_name, vlan_type, connect=None,
                          router_id=None, nocache=False):
        body = {
            'ReconfigNW_DeviceName1': device_name,
            'ReconfigNW_DeviceType1': 'TFW',
            'ReconfigNW_Vlan_DeviceAddress1': vlan_devaddr,
            'ReconfigNW_VlanLogicalName1': vlan_logical_name,
            'ReconfigNW_VlanType1': vlan_type,
            'TenantID': tenant_id
        }
        if connect:
            body['ReconfigNW_Vlan_ConnectDevice1'] = connect
        return self.post, NwaWorkflow.path('UpdateTenantFW'), body

    def _delete_tenant_fw(self, tenant_id, device_name, device_type,
                          router_id=None):
        body = {
            'DeleteNW_DeviceName1': device_name,
            'DeleteNW_DeviceType1': device_type,
            'TenantID': tenant_id
        }
        return self.post, NwaWorkflow.path('DeleteTenantFW'), body

    # --- Nat ---

    def _setting_nat(self, tenant_id, vlan_logical_name, vlan_type,
                     local_ip, global_ip, dev_name, data=None,
                     router_id=None, nocache=False):
        body = {
            'ReconfigNW_DeviceName1': dev_name,
            'ReconfigNW_DeviceType1': 'TFW',
            'ReconfigNW_VlanLogicalName1': vlan_logical_name,
            'ReconfigNW_VlanType1': vlan_type,
            'LocalIP': local_ip,
            'GlobalIP': global_ip,
            'TenantID': tenant_id,
        }
        return self.post, NwaWorkflow.path('SettingNAT'), body

    def _delete_nat(self, tenant_id, vlan_logical_name, vlan_type,
                    local_ip, global_ip, dev_name, data=None,
                    router_id=None, nocache=False):
        body = {
            'DeleteNW_DeviceName1': dev_name,
            'DeleteNW_DeviceType1': 'TFW',
            'DeleteNW_VlanLogicalName1': vlan_logical_name,
            'DeleteNW_VlanType1': vlan_type,
            'LocalIP': local_ip,
            'GlobalIP': global_ip,
            'TenantID': tenant_id,
        }
        return self.post, NwaWorkflow.path('DeleteNAT'), body

    # --- FWaaS ---

    def _setting_fw_policy(self, tenant_id, fw_name, props):
        body = {
            'TenantID': tenant_id,
            'DCResourceType': 'TFW_Policy',
            'DCResourceOperation': 'Setting',
            'DeviceInfo': {
                'Type': 'TFW',
                'DeviceName': fw_name,
            },
            'Property': props
        }
        return self.post, NwaWorkflow.path('SettingFWPolicy'), body

    def _setting_lb_policy(self, tenant_id, lb_name, props):
        body = {
            'TenantID': tenant_id,
            'DCResourceType': 'LB_Policy',
            'DCResourceOperation': 'Setting',
            'DeviceInfo': {
                'Type': 'LB',
                'DeviceName': lb_name,
            },
            'Property': props
        }
        return self.post, NwaWorkflow.path('SettingLBPolicy'), body

    # --- LBaaS ---

    def _create_tenant_lb(self, tenant_id, dc_resource_group_name,
                          vlan_logical_name, vlan_type, vif_ipaddr):
        body = {
            'CreateNW_DeviceType1': 'LB',
            'TenantID': tenant_id,
            'CreateNW_Vlan_DeviceAddress1': vif_ipaddr,
            'CreateNW_VlanLogicalName1': vlan_logical_name,
            'CreateNW_VlanType1': vlan_type,
            'CreateNW_DCResourceGroupName': dc_resource_group_name
        }
        return self.post, NwaWorkflow.path('CreateTenantLB'), body

    def _update_tenant_lb(self, tenant_id, device_name,
                          old_name, old_type,
                          new_name, new_type, new_ipaddr):
        body = {
            'ReconfigNW_DeviceName1': device_name,
            'ReconfigNW_DeviceType1': 'LB',
            'ReconfigNW_Vlan_DeviceAddress2': new_ipaddr,
            'ReconfigNW_Vlan_ConnectDevice2': 'connect',
            'ReconfigNW_VlanLogicalName2': new_name,
            'ReconfigNW_VlanType2': new_type,
            'ReconfigNW_Vlan_ConnectDevice1': 'disconnect',
            'ReconfigNW_VlanLogicalName1': old_name,
            'ReconfigNW_VlanType1': old_type,
            'TenantID': tenant_id,
        }
        return self.post, NwaWorkflow.path('UpdateTenantLB'), body

    def _update_tenant_lbn(self, tenant_id, device_name,
                           actions):
        body = {
            'ReconfigNW_DeviceName1': device_name,
            'ReconfigNW_DeviceType1': 'LB',
            'TenantID': tenant_id
        }
        for n, a in enumerate(actions):
            i = str(n + 1)
            if a[0] is not None:
                body['ReconfigNW_Vlan_ConnectDevice' + i] = a[0]
            lwn = a[1]
            body['ReconfigNW_VlanLogicalName' + i] = lwn
            if len(a) > 2:
                body['ReconfigNW_Vlan_DeviceAddress' + i] = a[2]
            if len(a) > 3:
                body['ReconfigNW_VlanType' + i] = a[3]
            else:
                if re.search(lwn, '_PublicVLAN_'):
                    body['ReconfigNW_VlanType' + i] = 'PublicVLAN'
                else:
                    body['ReconfigNW_VlanType' + i] = 'BusinessVLAN'
        return self.post, NwaWorkflow.path('UpdateTenantLB'), body

    def _delete_tenant_lb(self, tenant_id, device_name):
        body = {
            'DeleteNW_DeviceName1': device_name,
            'DeleteNW_DeviceType1': 'LB',
            'TenantID': tenant_id,
        }
        return self.post, NwaWorkflow.path('DeleteTenantLB'), body

    # --- General Dev ---

    def _create_general_dev(self, tenant_id, dc_resource_group_name,
                            vlan_logical_name, vlan_type,
                            port_type, open_id=None, nocache=False):
        body = {
            'CreateNW_DeviceType1': 'GeneralDev',
            'TenantID': tenant_id,
            'CreateNW_VlanLogicalName1': vlan_logical_name,
            'CreateNW_VlanType1': vlan_type,
            'CreateNW_DCResourceGroupName': dc_resource_group_name
        }
        if vlan_logical_name and open_id:
            LOG.warning(_LW('VLAN logical name and id to be specified '
                            'in the exclusive.'))
        if open_id:
            body['CreateNW_VlanLogicalID1'] = open_id
        if port_type:
            body['CreateNW_PortType1'] = port_type
        return self.post, NwaWorkflow.path('CreateGeneralDev'), body

    def _delete_general_dev(self, tenant_id, dc_resource_group_name,
                            vlan_logical_name, vlan_type,
                            port_type, open_id=None, nocache=False):
        body = {
            'DeleteNW_DeviceType1': 'GeneralDev',
            'TenantID': tenant_id,
            'DeleteNW_VlanLogicalName1': vlan_logical_name,
            'DeleteNW_VlanType1': vlan_type,
            'DeleteNW_DCResourceGroupName': dc_resource_group_name
        }
        if vlan_logical_name and open_id:
            LOG.warning(_LW('VLAN logical name and id to be specified '
                            'in the exclusive.'))
        if open_id:
            body['DeleteNW_VlanLogicalID1'] = open_id
        if port_type:
            body['DeleteNW_PortType1'] = port_type
        return self.post, NwaWorkflow.path('DeleteGeneralDev'), body

    def workflowinstance(self, execution_id):
        return self.get('/umf/workflowinstance/' + execution_id)

    def stop_workflowinstance(self, execution_id):
        return self.delete('/umf/workflowinstance/' + execution_id)

    def workflow_kick_and_wait(self, call, url, body):
        http_status = -1
        rj = None
        (http_status, rj) = call(url, body)

        if not isinstance(rj, dict):
            return (http_status, None)

        exeid = rj.get('executionid')
        if not isinstance(exeid, six.string_types):
            LOG.error(_LE('Invalid executin id %s'), exeid)
        try:
            wait_time = self.workflow_first_wait
            eventlet.sleep(wait_time)
            for i in range(self.workflow_retry_count):
                (http_status, rw) = self.workflowinstance(exeid)
                if not isinstance(rw, dict):
                    LOG.error(
                        _LE('NWA workflow: failed %(http_status)s %(body)s'),
                        {'http_status': http_status, 'body': rw}
                    )
                    return (http_status, None)
                if rw.get('status') != 'RUNNING':
                    LOG.debug('%s', rw)
                    return (http_status, rw)
                eventlet.sleep(wait_time)
                wait_time = self.workflow_wait_sleep
            LOG.warning(_LW('NWA workflow: retry over. retry count is %s.'),
                        self.workflow_retry_count)
        except Exception as e:
            LOG.error(_LE('NWA workflow: %s'), e)
        return (http_status, None)

    def call_workflow(self, make_request, tenant_id, *args, **kwargs):
        post, url, body = make_request(tenant_id, *args, **kwargs)
        wkf = Semaphore.get_tenant_semaphore(tenant_id)
        if wkf.sem.locked():
            LOG.info(_LI('NWA sem %s(count)s: %(name)s %(url)s %(body)s'),
                     {'count': wkf.sem.balance,
                      'name': post.__name__,
                      'url': url,
                      'body': body})
        with wkf.sem:
            n = copy.copy(self)
            n.post_data = (url, body)
            http_status, rj = n.workflow_kick_and_wait(post, url, body)
            return http_status, rj

    def apply_async(self, make_request, success, failure, ctx, tenant_id,
                    *args, **kwargs):
        def execute_workflow_and_wait_result():
            http_status = -1
            try:
                http_status, rj = self.call_workflow(
                    make_request, tenant_id, *args, **kwargs
                )
                if isinstance(rj, dict) and rj.get('status') == 'SUCCESS':
                    success(ctx, http_status, rj, *args, **kwargs)
                else:
                    failure(ctx, http_status, rj, *args, **kwargs)

            except NwaException as e:
                http_status = e.http_status
                if isinstance(e.orgexc.args[0], IOError):
                    kwargs['exception'] = {
                        'errno': e.orgexc.args[0][0],
                        'message': e.orgexc.args[0][1]
                    }
                else:
                    kwargs['exception'] = {
                        'errno': 0,
                        'message': str(e.orgexc)
                    }
                failure(ctx, http_status, None, *args, **kwargs)
            except Exception as e:
                LOG.exception(_LE('%s'), e)
                failure(ctx, http_status, None, *args, **kwargs)
            # return (http_status, None)
            return http_status, rj
        return execute_workflow_and_wait_result()

    def wait_workflow_done(self, thr):
        LOG.debug('*** start wait')
        thr.wait()
        LOG.debug('*** end wait')

    # --- sync api ---

    def create_tenant(self, tenant_id):
        body = {
            'TenantName': tenant_id,
        }
        return self.post('/umf/tenant/' + tenant_id, body)

    def delete_tenant(self, tenant_id):
        status_code, data = self.delete('/umf/tenant/' + tenant_id)
        if status_code == 200:
            Semaphore.delete_tenant_semaphore(tenant_id)
        return status_code, data

    def get_tenant_resource(self, tenant_id):
        return self.get('/umf/reserveddcresource/' + tenant_id)

    def get_dc_resource_groups(self, group=None):
        if group is None:
            url = '/umf/dcresource/groups'
        else:
            url = '/umf/dcresource/groups/' + str(group)
        return self.get(url)

    def get_reserved_dc_resource(self, tenant_id):
        url = '/umf/reserveddcresource/' + str(tenant_id)
        return self.get(url)

    def get_workflow_list(self):
        try:
            url = '/umf/workflow/list'
            return self.get(url)
        except Exception:
            return None, None

    def update_workflow_list(self):
        st, rj = self.get_workflow_list()
        nameid = {}
        if isinstance(rj, dict) and rj.get('Workflows'):
            def new_nameid(workflow):
                path = workflow.get('Path')
                if isinstance(path, six.string_types):
                    m = re.search(r'\\([a-zA-Z0-9_]+)$', path)
                    if m:
                        key = str(m.group(1))
                        nameid[key] = str(workflow.get('Id'))
            for wf in rj.get('Workflows'):
                new_nameid(wf)
        NwaWorkflow.update_nameid(nameid)

    def setting_fw_policy(self, tenant_id, fw_name, props):
        rd = {'status': 'FAILED'}

        def ok(ctx, hs, rj, *args, **kwargs):
            rd['status'] = 'SUCCESS'
            rd['http_status'] = hs
            rd['result'] = rj

        def ng(ctx, hs, rj, *args, **kwargs):
            rd['http_status'] = hs
            rd['result'] = rj
            rd['exception'] = kwargs.get('exception', None)

        return self.setting_fw_policy_async(
            ok, ng, 0, tenant_id, fw_name, props
        )

    # --- async api; workflow ---

    def create_tenant_nw(self, ok, ng, ctx, tenant_id,
                         dc_resource_group_name):
        return self.apply_async(
            self._create_tenant_nw, ok, ng, ctx, tenant_id,
            dc_resource_group_name
        )

    def delete_tenant_nw(self, ok, ng, ctx, tenant_id):
        return self.apply_async(
            self._delete_tenant_nw, ok, ng, ctx, tenant_id
        )

    def create_vlan(self, ok, ng, ctx, tenant_id, ipaddr, mask,
                    vlan_type='BusinessVLAN', openstack_network_id=None):
        return self.apply_async(
            self._create_vlan, ok, ng, ctx, tenant_id,
            vlan_type, ipaddr, mask, openstack_network_id
        )

    def delete_vlan(self, ok, ng, ctx, tenant_id, logical_name,
                    vlan_type='BusinessVLAN'):
        return self.apply_async(
            self._delete_vlan, ok, ng, ctx, tenant_id,
            logical_name, vlan_type
        )

    def create_tenant_fw(self, ok, ng, ctx, tenant_id,
                         dc_resource_group_name,
                         vlan_devaddr, vlan_logical_name,
                         vlan_type='BusinessVLAN', router_id=None):
        return self.apply_async(
            self._create_tenant_fw, ok, ng, ctx, tenant_id,
            dc_resource_group_name,
            vlan_devaddr, vlan_logical_name,
            vlan_type=vlan_type, router_id=router_id
        )

    def update_tenant_fw(self, ok, ng, ctx, tenant_id,
                         device_name, vlan_devaddr,
                         vlan_logical_name, vlan_type,
                         connect=None, router_id=None):
        return self.apply_async(
            self._update_tenant_fw, ok, ng, ctx, tenant_id,
            device_name, vlan_devaddr,
            vlan_logical_name, vlan_type, connect=connect,
            router_id=router_id, nocache=True
        )

    def delete_tenant_fw(self, ok, ng, ctx, tenant_id,
                         device_name, device_type, router_id=None):
        return self.apply_async(
            self._delete_tenant_fw, ok, ng, ctx, tenant_id,
            device_name, device_type, router_id=router_id
        )

    def setting_nat(self, ok, ng, ctx, tenant_id,
                    vlan_logical_name, vlan_type,
                    localip, global_ip, dev_name, data=None, router_id=None):
        return self.apply_async(
            self._setting_nat, ok, ng, ctx, tenant_id,
            vlan_logical_name, vlan_type,
            localip, global_ip, dev_name, data=data, router_id=router_id,
            nocache=True
        )

    def update_nat(self, ok, ng, ctx, tenant_id,
                   vlan_logical_name, vlan_type,
                   localip, global_ip, dev_name, data=None, router_id=None):
        def predel_nat(okctx, http_status, rj, *args, **kwargs):
            return self.apply_async(
                self._setting_nat, ok, ng, okctx, tenant_id,
                vlan_logical_name, vlan_type,
                localip, global_ip, dev_name, data=data, router_id=router_id)

        return self.apply_async(
            self._delete_nat, predel_nat, predel_nat, ctx, tenant_id,
            vlan_logical_name, vlan_type,
            localip, global_ip, dev_name, data=data
        )

    def delete_nat(self, ok, ng, ctx, tenant_id,
                   vlan_logical_name, vlan_type,
                   localip, global_ip, dev_name, data=None, router_id=None):
        return self.apply_async(
            self._delete_nat, ok, ng, ctx, tenant_id,
            vlan_logical_name, vlan_type,
            localip, global_ip, dev_name, data=data, router_id=router_id,
            nocache=True
        )

    def setting_fw_policy_async(self, ok, ng, ctx, tenant_id, fw_name, props):
        return self.apply_async(
            self._setting_fw_policy, ok, ng, ctx, tenant_id,
            fw_name, props
        )

    def setting_lb_policy(self, ok, ng, ctx, tenant_id, lb_name, props):
        return self.apply_async(
            self._setting_lb_policy, ok, ng, ctx, tenant_id,
            lb_name, props
        )

    def create_tenant_lb(self, ok, ng, ctx, tenant_id,
                         dc_resource_group_name,
                         vlan_logical_name, vlan_type, vif_ipaddr):
        return self.apply_async(
            self._create_tenant_lb, ok, ng, ctx, tenant_id,
            dc_resource_group_name,
            vlan_logical_name, vlan_type, vif_ipaddr
        )

    def update_tenant_lb(self, ok, ng, ctx, tenant_id,
                         device_name,
                         old_name, old_type,
                         new_name, new_type, new_ipaddr):
        return self.apply_async(
            self._update_tenant_lb, ok, ng, ctx, tenant_id,
            device_name,
            old_name, old_type,
            new_name, new_type, new_ipaddr
        )

    def update_tenant_lbn(self, ok, ng, ctx, tenant_id,
                          device_name, actions):
        return self.apply_async(
            self._update_tenant_lbn, ok, ng, ctx, tenant_id,
            device_name, actions
        )

    def delete_tenant_lb(self, ok, ng, ctx, tenant_id, device_name):
        return self.apply_async(
            self._delete_tenant_lb, ok, ng, ctx, tenant_id,
            device_name
        )

    def create_general_dev(self, ok, ng, ctx, tenant_id,
                           dc_resource_group_name, logical_name,
                           vlan_type='BusinessVLAN',
                           port_type=None,
                           openstack_network_id=None):
        return self.apply_async(
            self._create_general_dev, ok, ng, ctx, tenant_id,
            dc_resource_group_name, logical_name,
            vlan_type, port_type, openstack_network_id,
            nocache=Semaphore.create_general_dev_history
        )

    def delete_general_dev(self, ok, ng, ctx, tenant_id,
                           dc_resource_group_name, logical_name,
                           vlan_type='BusinessVLAN',
                           port_type=None,
                           openstack_network_id=None):
        return self.apply_async(
            self._delete_general_dev, ok, ng, ctx, tenant_id,
            dc_resource_group_name, logical_name,
            vlan_type, port_type, openstack_network_id,
            nocache=Semaphore.delete_general_dev_history
        )


def send_queue_is_not_empty():
    return Semaphore.any_locked()
