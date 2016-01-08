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

# -*- mode: python, coding: utf-8 -*-
# GIT: $Id$

import eventlet
import requests
eventlet.import_patched('requests.__init__')
import json
import re
import hmac
import hashlib
import base64
import datetime
import six.moves.urllib.parse as urlparse
import sys
import copy
import traceback

from oslo_log import log as logging
from networking_nec.plugins.necnwa.common import config as nwaconf
# from neutron.plugins.nec.common import exceptions as nexc


LOG = logging.getLogger(__name__)

cfgNWA = nwaconf.cfg.CONF.NWA

date_header_format = '%a, %d %b %Y %H:%M:%S GMT'
CRLF = '\x0D\x0A'

UMF_API_VERSION = '2.0.2.1.201502'
OLD_UMF_API_VERSION = '2.0.2.201402'

rest_api_debug = False


class NwaException(Exception):
    '''Raised when there is an error in Nwa.
    '''
    def __init__(self, http_status, errmsg, orgexc=None):
        self.http_status = http_status
        self.errmsg = errmsg
        self.orgexc = orgexc

    def __str__(self):
        return 'http status: {0}, {1}'.format(self.http_status, self.errmsg)


class NwaWorkflow(object):
    '''Workflow definition of NWA.
    '''
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
    def init(self, name):
        pass                                    # pragma: no cover

    @staticmethod
    def path(name):
        """Returns path of workflow.

        :param name: The name of workflow.
        """
        return (NwaWorkflow._path_prefix +
                '{0}/execute'.format(NwaWorkflow._nameid[name]))

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
            if isinstance(errmsg, basestring):
                m = re.search('ErrorNumber=(\d+)', errmsg)
                if m:
                    return m.group(1)
                m = re.search('ReservationErrorCode = (\d+)', errmsg, re.M)
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
        return '{0}://{1}:{2}{3}'.format(protocol, self.host, self.port, path)

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
        LOG.debug('NWA HTTP Headers {0}'.format(str(headers)))
        res = requests.request(method, url, data=body, headers=headers,
                               verify=False, proxies={'no': 'pass'})
        return res

    def rest_api(self, method, url, body=None):
        if isinstance(body, dict):
            body = json.dumps(body, indent=4, sort_keys=True)

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
                data = json.loads(data)
            except (ValueError, TypeError):
                pass
            status_code = int(res.status_code)
            if 200 <= status_code and status_code <= 209:
                return (status_code, data)
            else:
                msg = ("NWA failed: {0} {1}:{2}{3} "
                       "(HTTP/1.1 {4} {5}) body={6}"
                       .format(method, self.host, self.port, url,
                               res.status_code, res.reason, data))
                LOG.warning(msg)
                raise NwaException(status_code, msg)
        except requests.exceptions.RequestException as e:
            msg = "NWA Failed to connect {0}:{1}: {2}".format(
                self.host, self.port, str(e))
            LOG.error(msg)
            tback = sys.exc_info()[2]
            raise NwaException(status_code, msg, e), None, tback

    def _report_workflow_error(self, data, errno):
        if not getattr(self, 'post_data', None):
            return ''
        post_url, post_body = self.post_data
        if isinstance(post_body, dict):
            post_body = json.dumps(post_body, indent=4, sort_keys=True)
        name = (NwaWorkflow.name(post_url) or post_url)
        reason = NwaWorkflow.strerror(errno)
        msg = ("NWA workflow: {0} reason({1})={2} request={3}, response={4}"
               .format(name, errno, reason, post_body,
                       json.dumps(data, indent=4, sort_keys=True)))
        return msg

    def rest_api_return_check(self, method, url, body=None):
        status_code = 200
        try:
            name = NwaWorkflow.name(url)
            body_str = ''
            if isinstance(body, dict):
                body_str = json.dumps(body, sort_keys=True)
            if name:
                msg = "NWA workflow: {0} {1}".format(name, body_str)
            else:
                msg = "NWA {0} {1} {2}".format(
                    method, self.url(url), body_str)
            LOG.info(msg)

            status_code, data = self.rest_api(method, url, body)

            status = ''
            progress = ''
            if isinstance(data, dict) and data.get('status'):
                status = data.get('status')
                progress = data.get('progress')

            LOG.info("NWA HTTP {0} {1} {2}".format(
                status_code, status, progress))

            if status == 'FAILED':
                errno = NwaWorkflow.get_errno_from_resultdata(data)
                msg = self._report_workflow_error(data, errno)
                LOG.error(msg)
            elif status == 'SUCCEED':
                name = ''
                if getattr(self, 'post_data', None):
                    post_url, post_body = self.post_data
                    name = (NwaWorkflow.name(post_url) or post_url)
                LOG.info("NWA workflow: {0} {1}".format(
                    name, json.dumps(data, indent=4, sort_keys=True)))
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
    '''Client class of NWA rest.
    '''

    def __init__(self, *args, **kwargs):
        c = cfgNWA
        access_key_id = kwargs.pop('access_key_id',
                                   getattr(c, 'AccessKeyId', None))
        secret_access_key = kwargs.pop('secret_access_key',
                                       getattr(c, 'SecretAccessKey', None))

        self._init_default(
            kwargs,
            url=getattr(c, 'ServerURL', None),
            auth=self.define_auth_function(access_key_id, secret_access_key)
        )
        super(NwaRestClient, self).__init__(*args, **kwargs)

        self.workflow_first_wait = getattr(c, 'ScenarioPollingFirstTimer', 2)
        self.workflow_wait_sleep = getattr(c, 'ScenarioPollingTimer', 10)
        self.workflow_retry_count = getattr(c, 'ScenarioPollingCount', 6)
        LOG.info('NWA init: host={0} port={1} use_ssl={2} auth={3}'.format(
            self.host, self.port, self.use_ssl, self.auth))
        LOG.info('NWA init: workflow wait: {0}s + {1}s x {2} times.'.format(
            self.workflow_first_wait,
            self.workflow_wait_sleep,
            self.workflow_retry_count))
        LOG.info('NWA init: umf api version: {0}'.format(
            self.umf_api_version))

    def define_auth_function(self, access_key_id, secret_access_key):
        def azure_auth(datestr, path):
            signature = hmac.new(
                secret_access_key,
                datestr + CRLF + path,
                hashlib.sha256
            ).digest()
            return 'SharedKeyLite {0}:{1}'.format(
                access_key_id,
                base64.encodestring(signature).rstrip()
            )

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
    def get_tenant_semaphore(self, tenant_id):
        if not isinstance(tenant_id, basestring) or tenant_id == '':
            raise TypeError('{} is not a string'.format(tenant_id))
        with Semaphore.lock:
            if tenant_id not in Semaphore.tenants:
                LOG.info('create semaphore for {}'.format(tenant_id))
                Semaphore.tenants[tenant_id] = Semaphore()
            return Semaphore.tenants[tenant_id]

    @classmethod
    def delete_tenant_semaphore(self, tenant_id):
        with Semaphore.lock:
            if tenant_id in Semaphore.tenants:
                LOG.info('delete semaphore for {}'.format(tenant_id))
                del Semaphore.tenants[tenant_id]

    @classmethod
    def any_locked(self):
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
                LOG.debug('NWA search_history - hit name={} url={} body={}'.
                          format(name, url, body))
                return hr['http_status'], hr['rj']
        LOG.debug('NWA search_history - no hit')
        return None, None

    def push_history(self, call, url, body, http_status, rj):
        while len(self.histrun) > self.histsiz:
            self.histrun.pop()
        (hs, rb) = self.search_history(call, url, body)
        if rb is not None:
            return
        if isinstance(rj, dict) and rj.get('status') == 'SUCCEED':
            hr = {
                'call': call.__name__,
                'url': url,
                'body': body,
                'http_status': http_status,
                'rj': rj
            }
            self.histrun.insert(0, hr)
            LOG.debug('NWA push_history - hr={}'.format(hr))

    def create_general_dev_history(self, call, creurl, body, http_status, rj):
        name = call.__name__
        url = NwaWorkflow.path('DeleteGeneralDev')
        for hr in self.histrun:
            if hr['call'] == name and hr['url'] == url:
                create = body['CreateNW_VlanLogicalName1']
                delete = hr['body']['DeleteNW_VlanLogicalName1']
                if create == delete:
                    hr['url'], hr['body'] = None, None
                    LOG.debug('NWA delete_history - hit name={} url={} body={}'.
                              format(name, url, body))
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
                    LOG.debug('NWA delete_history - hit name={} url={} body={}'.
                              format(name, url, body))
        self.push_history(call, delurl, body, http_status, rj)


class NwaClient(NwaRestClient):
    '''Client class of NWA.
    '''
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
            LOG.warning('VLAN logical name and id to be specified'
                        'in the exclusive.')
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
            LOG.warning('VLAN logical name and id to be specified'
                        'in the exclusive.')
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
        try:
            (http_status, rj) = call(url, body)
        except NwaException as e:
            raise

        if not isinstance(rj, dict):
            return (http_status, None)

        exeid = rj.get('executionid')
        if not isinstance(exeid, basestring):
            LOG.error(exeid)
        try:
            wait_time = self.workflow_first_wait
            eventlet.sleep(wait_time)
            for i in range(self.workflow_retry_count):
                (http_status, rw) = self.workflowinstance(exeid)
                if not isinstance(rw, dict):
                    LOG.error([http_status, rw])
                    return (http_status, None)
                if rw.get('status') != 'RUNNING':
                    LOG.debug(rw)
                    return (http_status, rw)
                eventlet.sleep(wait_time)
                wait_time = self.workflow_wait_sleep
            LOG.warning('NWA workflow: retry over. retry count is {0}.'
                        .format(self.workflow_retry_count))
        except Exception as e:
            LOG.error(str(e))
        return (http_status, None)

    def call_workflow(self, make_request, tenant_id, *args, **kwargs):
        post, url, body = make_request(tenant_id, *args, **kwargs)
        wkf = Semaphore.get_tenant_semaphore(tenant_id)
        if wkf.sem.locked():
            LOG.info('NWA sem {0}: {1} {2} {3}'.format(
                wkf.sem.balance,
                str(post.__name__), url, body))
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
                if isinstance(rj, dict) and rj.get('status') == 'SUCCEED':
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
                LOG.error(str(e) + '\n ' + traceback.format_exc())
                failure(ctx, http_status, None, *args, **kwargs)
            #return (http_status, None)
            return http_status, rj

        """
        LOG.debug('NWA spawn start: running {}'.
                  format(NwaClient.pool.running()))
        gt = NwaClient.pool.spawn(execute_workflow_and_wait_result)
        eventlet.sleep(0.01)
        LOG.debug('NWA spawn done:  running {}'.
                  format(NwaClient.pool.running()))
        return Thread(gt)
        """
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
        except:
            return None, None

    def update_workflow_list(self):
        st, rj = self.get_workflow_list()
        nameid = {}
        if isinstance(rj, dict) and rj.get('Workflows'):
            def new_nameid(workflow):
                path = workflow.get('Path')
                if isinstance(path, basestring):
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
            rd['status'] = 'SUCCEED'
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


def test_usage():                         # pragma: no cover
    import sys
    print('''usage: nwaclient options command
options:
  --tenant-id TENANT-ID
  --host NWA-HOST
  --port NWA-PORT
  --umf-api-version=[2.0.2.1.201502|2.0.2.201402]
  --debug

commands:
  create-tenant
  delete-tenant
  create-tenant-nw dcresgrp    (ex OpenStack/DC1/Common/Pod1Grp/Pod1)
  delete-tenant-nw
  create-vlan ipaddr mask      (ex 10.0.0.1 24)
  delete-vlan vlan-name        (ex LNW_BusinessVLAN_129)
  list-vlan
  create-tenant-fw dcresgrp name devaddr
             (ex OpenStack/DC1/Common/App1Grp/App1 LNW_BusinessVLAN_129
                 172.16.0.254)
  update-tenant-fw dcresgrp name devaddr [disconnect|connect]
  delete-tenant-fw device_name device_type (ex TFW0 TFW)

  update-nat tfw vlan_name vlan_type local_ip global_ip
  setting-nat tfw vlan_name vlan_type local_ip global_ip
  delete-nat tfw vlan_name vlan_type local_ip global_ip
  setting-fw-policy tfw props
  setting-lb-policy lb props
  create-tenant-lb dcresgrp vlan_name ipaddr [vlan_type]
  update-tenant-lb device_name old_vlan_name old_vlan_type
                               new_vlan_name new_vlan_type new_ip
  delete-tenant-lb device_name

  create-general-dev dcresgrp logical_name [vlan_type [port_type]]
  delete-general-dev dcresgrp logical_name [vlan_type [port_type]]

  list-dcresgrp [dcresgrp-name] (ex OpenStack/DC1/Common/Pod1Grp/Pod1)
  get-workflowinstance execution-id
  cancel-workflow execution-id
  get-workflow-list
    ''')
    sys.exit(2)


def test_ok(ctx, http_status, rj, *args, **kwargs):   # pragma: no cover
    print('ok'),
    print(json.dumps({'context': ctx,
                      'http_status': http_status,
                      'json_body': rj}, indent=4, sort_keys=True))
    if rest_api_debug:
        print(args)
        print(kwargs)


def test_ng(ctx, http_status, rj, *args, **kwargs):   # pragma: no cover
    # errno = NwaWorkflow.get_errno_from_resultdata(rj)
    # print(json.dumps(rj, indent=4, sort_keys=True))
    print('ng'),
    print(json.dumps({'context': ctx,
                      'http_status': http_status,
                      'json_body': rj}, indent=4, sort_keys=True))


def test_client():                        # pragma: no cover
    import getopt
    import os
    import sys
    global rest_api_debug

    for ini in ['nwa.ini', '/etc/nwa/nwa.ini']:
        if os.path.exists(ini):
            LOG.info('load ini: {0}'.format(ini))
            nwaconf.cfg.CONF(args=[], default_config_files=[ini])
            break

    tenant_id = os.getenv('NWA_TENANT_ID')
    host = os.getenv('NWA_HOST')
    port = os.getenv('NWA_PORT')
    umf_api_version = UMF_API_VERSION

    try:
        longopts = ['tenant-id=', 'host=', 'port=',
                    'umf-api-version=',
                    'debug', ]
        opts, args = getopt.getopt(sys.argv[1:], 'v', longopts)
        for opt, arg in opts:
            if opt in ('--tenant-id'):
                tenant_id = arg
            elif opt in ('--host'):
                host = arg
            elif opt in ('--port'):
                port = arg
            elif opt in ('--umf-api-version'):
                umf_api_version = arg
            elif opt in ('-v'):
                pass
            elif opt in ('--debug'):
                rest_api_debug = True
                logger = logging.getLogger(__name__)
                logger.setLevel(logging.DEBUG)
    except getopt.error as e:
        sys.stdout = sys.stderr
        print(str(e))
        test_usage()

    if not tenant_id:
        tenant_id = 'DefaultTenant'

    nargs = len(args)
    if nargs == 0:
        test_usage()
    cmd = args[0]
    if cmd == 'help':
        test_usage()

    if host and port:
        nwa = NwaClient(host=host, port=port,
                        umf_api_version=umf_api_version)
    else:
        nwa = NwaClient(umf_api_version=umf_api_version)

    def shift(a, default=None):
        if len(a) >= 1:
            x = a.pop(1)
            if x is not None:
                return x
        return default

    def overwrite_with_args(props, args):
        def get_from_dict(datadict, maplist):
            return reduce(lambda d, k: d[k], maplist, datadict)

        def set_in_dict(datadict, maplist, v):
            get_from_dict(datadict, maplist[:-1])[maplist[-1]] = v

        def num(s):
            try:
                return int(s)
            except ValueError:
                return s

        for arg in args:
            if arg is None or re.search('=', arg) is None:
                continue
            k, v = arg.split('=')
            if re.search('.', k) is None:
                ks = [k]
            else:
                ks = k.split('.')
            ks = [num(t) for t in ks]
            set_in_dict(props, ks, v)
        return props

    args += [None, None, None, None, None]  # avoid index error
    vlan_type = 'BusinessVLAN'

    if cmd == 'create-tenant':
        print nwa.create_tenant(tenant_id)

    elif cmd == 'delete-tenant':
        print nwa.delete_tenant(tenant_id)

    elif cmd == 'list-vlan':
        st, rj = nwa.get_tenant_resource(tenant_id)
        for node in rj.get('GroupNode'):
            vlans = []
            for vlan in node.get('VLAN'):
                vlans.append({key: value for key, value in vlan.items()
                              if key in ('FWIPAddress',
                                         'ID',
                                         'IPSubnetAddress',
                                         'IPSubnetMask',
                                         'LogicalName',
                                         'SSLIPAddress',
                                         'SharedType',
                                         'TenantIPRange')})
            print(json.dumps({node.get('Type'): vlans},
                             indent=4, sort_keys=True))

    elif cmd == 'create-vlan':
        if nargs < 3:
            print('usage: create-vlan ipaddr mask')
        else:
            if nargs == 4:
                vlan_type = args[3]
            nwa.create_vlan(
                test_ok, test_ng, 0, tenant_id, args[1], args[2], vlan_type
            )

    elif cmd == 'delete-vlan':
        if nargs < 2:
            print('usage: delete-vlan vlan-name')
        else:
            if nargs == 3:
                vlan_type = args[2]
            nwa.delete_vlan(
                test_ok, test_ng, 0, tenant_id, args[1], vlan_type
            )

    elif cmd == 'create-tenant-nw':
        if nargs < 2:
            print('usage: create-tenant-nw dcresgrp')
        else:
            nwa.create_tenant_nw(test_ok, test_ng, 0, tenant_id, args[1])
    elif cmd == 'delete-tenant-nw':
        nwa.delete_tenant_nw(test_ok, test_ng, 0, tenant_id)
    elif cmd == 'create-tenant-fw':
        if nargs < 4:
            print('usage: create-tenant-fw'
                  ' dcresgrp name devaddr [vlan_type [router_id]]')
        else:
            dc_resource_group_name = shift(args)
            logical_name = shift(args)
            vlan_devaddr = shift(args)
            vlan_type = shift(args, 'BusinessVLAN')
            router_id = shift(args)
            nwa.create_tenant_fw(
                test_ok, test_ng, 0, tenant_id,
                dc_resource_group_name,
                vlan_devaddr, logical_name,
                vlan_type, router_id=router_id
            )
    elif cmd == 'update-tenant-fw':
        if nargs < 4:
            print('usage: update-tenant-fw fwname devaddr vlan_name '
                  '[BusinessVLAN [connect|disconnect] [router_id]]')
        else:
            fw_name = shift(args)
            vlan_devaddr = shift(args)
            vlan_name = shift(args)
            vlan_type = shift(args, 'BusinessVLAN')
            connect = shift(args)
            router_id = shift(args)
            nwa.update_tenant_fw(
                test_ok, test_ng, 0, tenant_id,
                fw_name, vlan_devaddr,
                vlan_name, vlan_type, connect=connect, router_id=router_id
            )
    elif cmd == 'delete-tenant-fw':
        if nargs < 3:
            print('usage: delete-tenant-fw devname devtype [router_id]')
        else:
            device_name = shift(args)
            device_type = shift(args)
            router_id = shift(args)
            nwa.delete_tenant_fw(
                test_ok, test_ng, 0, tenant_id,
                device_name, device_type, router_id=router_id
            )
    elif cmd == 'setting-nat':
        if nargs < 6:
            print('usage: setting-nat fw_name vlan_name vlan_type '
                  'local_ip global_ip [router_id]')
        else:
            dev_name = shift(args)
            vlan_name = shift(args)
            vlan_type = shift(args)
            local_ip = shift(args)
            global_ip = shift(args)
            router_id = shift(args)
            nwa.setting_nat(
                test_ok, test_ng, 0, tenant_id,
                vlan_name, vlan_type, local_ip, global_ip,
                dev_name, data=None, router_id=router_id
            )
    elif cmd == 'update-nat':
        if nargs != 6:
            print('usage: update-nat fw_name vlan_name vlan_type '
                  'local_ip global_ip')
        else:
            dev_name = args[1]
            vlan_name = args[2]
            vlan_type = args[3]
            local_ip = args[4]
            global_ip = args[5]
            nwa.update_nat(
                test_ok, test_ng, 0, tenant_id,
                vlan_name, vlan_type, local_ip, global_ip, dev_name
            )
    elif cmd == 'delete-nat':
        if nargs < 6:
            print('usage: delete-nat fw_name vlan_name vlan_type '
                  'local_ip global_ip [router_id]')
        else:
            dev_name = shift(args)
            vlan_name = shift(args)
            vlan_type = shift(args)
            local_ip = shift(args)
            global_ip = shift(args)
            router_id = shift(args)
            nwa.delete_nat(
                test_ok, test_ng, 0, tenant_id,
                vlan_name, vlan_type, local_ip, global_ip,
                dev_name, data=None, router_id=router_id
            )
    elif cmd == 'setting-fw-policy':
        if nargs < 3:
            print('usage: setting-fw-policy fw_name FILENAME [K1=V1 K2=V2 ...]')
            print('    or setting-fw-policy fw_name propertyAsDict')
            print(' K is dict key, nested access if K is dot separated')
        else:
            fw_name = shift(args)
            pname = shift(args)
            props = None
            try:
                with open(pname) as f:
                    props = json.load(f)
            except IOError:
                pass
            if props is None:
                try:
                    props = json.loads(pname)
                except Exception as e:
                    print 'arg2: JSON Error: {}'.format(str(e))
                    sys.exit(1)

            props = overwrite_with_args(props, args)
            print json.dumps(props, indent=4, sort_keys=True)
            rd = nwa.setting_fw_policy(tenant_id, fw_name, props)
            print json.dumps(rd, indent=4, sort_keys=True)
    elif cmd == 'setting-lb-policy':
        if nargs < 3:
            print('usage: setting-lb-policy lb_name FILENAME [K1=V1 K2=V2 ...]')
            print('    or setting-lb-policy lb_name propertyAsDict')
            print(' K is dict key, nested access if K is dot separated')
        else:
            lb_name = shift(args)
            pname = shift(args)
            props = None
            try:
                with open(pname) as f:
                    props = json.load(f)
            except IOError:
                pass
            if props is None:
                try:
                    props = json.loads(pname)
                except Exception as e:
                    print 'arg2: JSON Error: {}'.format(str(e))
                    sys.exit(1)

            props = overwrite_with_args(props, args)
            print json.dumps(props, indent=4, sort_keys=True)
            rd = nwa.setting_lb_policy(
                test_ok, test_ng, 0, tenant_id, lb_name, props)
            print json.dumps(rd, indent=4, sort_keys=True)
    elif cmd == 'create-tenant-lb':
        if nargs < 4:
            print('usage: create-tenant-lb dcresgrp NAME IPADDR [vlan-type]')
            print(' vlan-type: BusinessVLAN | PublicVLAN')
        else:
            dc_resource_group_name = args[1]
            vlan_name = args[2]
            ipaddr = args[3]
            vlan_type = args[4] or 'BusinessVLAN'
            nwa.create_tenant_lb(
                test_ok, test_ng, 0, tenant_id,
                dc_resource_group_name,
                vlan_name, vlan_type, ipaddr
            )
    elif cmd == 'update-tenant-lb':
        if nargs < 3:
            print('usage: update-tenant-lb NAME ACTION1 [ACTION2 ...]')
            print(' ACTION: connect:LWN_BusinessVLAN_100:192.168.0.1')
            print('   or    disconnect:LWN_BusinessVLAN_100:192.168.0.1')
        else:
            device_name = args[1]
            nwa.update_tenant_lbn(
                test_ok, test_ng, 0, tenant_id,
                device_name,
                [v.split(':') for v in args[2:] if v is not None]
            )
    elif cmd == 'delete-tenant-lb':
        if nargs != 2:
            print('usage: delete-tenant-lb NAME')
        else:
            device_name = args[1]
            nwa.delete_tenant_lb(
                test_ok, test_ng, 0, tenant_id,
                device_name
            )
    elif cmd == 'create-general-dev':
            dc_resource_group_name = args[1]
            logical_name = args[2]
            vlan_type = args[3] or 'BusinessVLAN'
            port_type = args[4]
            openstack_network_id = args[5]
            nwa.create_general_dev(
                test_ok, test_ng, 0, tenant_id,
                dc_resource_group_name,
                logical_name,
                vlan_type,
                port_type,
                openstack_network_id
            )
    elif cmd == 'delete-general-dev':
            dc_resource_group_name = args[1]
            logical_name = args[2]
            vlan_type = args[3] or 'BusinessVLAN'
            port_type = args[4]
            openstack_network_id = args[5]
            nwa.create_general_dev(
                test_ok, test_ng, 0, tenant_id,
                dc_resource_group_name,
                logical_name,
                vlan_type,
                port_type,
                openstack_network_id
            )
    elif cmd == 'list-dcresgrp':
        if nargs > 1:
            grpname = args[1]
        else:
            grpname = None
        st, rj = nwa.get_dc_resource_groups(grpname)
        print(json.dumps(rj, indent=4, sort_keys=True))
    elif cmd == 'get-workflowinstance':
        print nwa.workflowinstance(args[1])
    elif cmd == 'cancel-workflow':
        print nwa.stop_workflowinstance(args[1])
    elif cmd == 'get-workflow-list':
        st, rj = nwa.get_workflow_list()
        rj = {x['Path']: x['Id'] for x in rj['Workflows']}
        print(json.dumps(rj, indent=4, sort_keys=True))
    else:
        test_usage()


if __name__ == '__main__':                # pragma: no cover
    import logging
    log_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s,%(msecs).03d - %(filename)s:%(lineno)d - %(message)s',
        '%H:%M:%S'
    )
    log_handler.setFormatter(formatter)
    log_handler.propagate = False
    logger = logging.getLogger(__name__)
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
    test_client()
