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

import sqlalchemy as sa
from sqlalchemy import and_

from neutron.plugins.ml2 import models as models_ml2
from oslo_utils import timeutils

from networking_nec.plugins.necnwa.db import models as nmodels

# 0 is autoincrement
NWA_MIN_ID = 0
NWA_MAX_ID = 65535


def add_nwa_tenant_binding(session, tenant_id, nwa_tenant_id, json_value):
    try:
        if isinstance(json_value, dict) is False:
            return False
        nwa = session.query(nmodels.NWATenantBindingN).filter(
            nmodels.NWATenantBindingN.tenant_id == tenant_id).all()
        if len(nwa) > 0:
            return False
        with session.begin(subtransactions=True):
            for json_key, json_value in json_value.items():
                item = nmodels.NWATenantBindingN(tenant_id, nwa_tenant_id,
                                                 json_key, json_value)
                session.add(item)
            session.flush()
        return True
    except sa.orm.exc.NoResultFound:
        return False


def chg_value(key, value):
    if key == "CreateTenant" or key == "CreateTenantNW":
        if value == "True":
            value = True
        elif value == "False":
            value = False
    return value


def get_nwa_tenant_binding(session, tenant_id, nwa_tenant_id):
    try:
        value_json = {}
        for nwa in session.query(nmodels.NWATenantBindingN).filter(
            nmodels.NWATenantBindingN.tenant_id == tenant_id).filter(
                nmodels.NWATenantBindingN.nwa_tenant_id ==
                nwa_tenant_id).all():
            value_json[nwa.json_key] = chg_value(nwa.json_key, nwa.json_value)
        if len(value_json):
            return nmodels.NWATenantBinding(tenant_id, nwa_tenant_id,
                                            value_json)
        else:
            return None
    except sa.orm.exc.NoResultFound:
        return None


def get_nwa_tenant_binding_by_tid(session, tenant_id):
    try:
        value_json = {}
        nwa_tenant_id = ""
        for nwa in session.query(nmodels.NWATenantBindingN).filter(
                nmodels.NWATenantBindingN.tenant_id == tenant_id).all():
            value_json[nwa.json_key] = chg_value(nwa.json_key, nwa.json_value)
            nwa_tenant_id = nwa.nwa_tenant_id
        if len(value_json):
            return nmodels.NWATenantBinding(tenant_id, nwa_tenant_id,
                                            value_json)
        else:
            return None
    except sa.orm.exc.NoResultFound:
        return None


def set_nwa_tenant_binding(session, tenant_id, nwa_tenant_id, value_json):
    item = get_nwa_tenant_binding(session, tenant_id, nwa_tenant_id)
    if item is None:
        return False
    _json = item.value_json
    if isinstance(_json, dict) is False:
        return False
    if isinstance(value_json, dict) is False:
        return False
    with session.begin(subtransactions=True):
        for key, value in value_json.items():
            if key in _json:
                if value != _json[key]:
                    # update
                    item = session.query(nmodels.NWATenantBindingN).filter(
                        and_(nmodels.NWATenantBindingN.tenant_id == tenant_id,
                             nmodels.NWATenantBindingN.json_key == key)).one()
                    item.json_value = value
            else:
                # insert
                # item = nmodels.NWATenantBindingN(
                #        tenant_id, nwa_tenant_id, key, value)
                # session.add(item)
                insert = ("INSERT INTO nwa_tenant_binding (tenant_id,"
                          "nwa_tenant_id,json_key,json_value) "
                          " VALUES (\'%s\',\'%s\',\'%s\',\'%s\') "
                          "ON DUPLICATE KEY UPDATE "
                          " json_value=\'%s\'" % (tenant_id, nwa_tenant_id,
                                                  key, value, value))
                session.execute(insert)
        for key, value in _json.items():
            if key not in value_json:
                # delete
                item = session.query(nmodels.NWATenantBindingN).filter(
                    and_(nmodels.NWATenantBindingN.tenant_id == tenant_id,
                         nmodels.NWATenantBindingN.json_key == key)).one()
                session.delete(item)
    session.flush()
    return True


def del_nwa_tenant_binding(session, tenant_id, nwa_tenant_id):
    try:
        with session.begin(subtransactions=True):
            item = get_nwa_tenant_binding(session, tenant_id, nwa_tenant_id)
            if item is None:
                return False
            with session.begin(subtransactions=True):
                session.query(nmodels.NWATenantBindingN).filter(
                    and_(nmodels.NWATenantBindingN.tenant_id == tenant_id,
                         nmodels.NWATenantBindingN.nwa_tenant_id ==
                         nwa_tenant_id)).delete()
            session.flush()
            return True
    except sa.orm.exc.NoResultFound:
        return False


# update json object: set result of /umf/tenant/(TenantID)
def update_json_nwa_tenant_id(value_json, nwa_tenant_id):
    value_json['NWA_tenant_id'] = nwa_tenant_id


# update json object: set result of /umf/workflowinstance/(executionid)
# for CreateTenantNW
def update_json_post_CreateTenantNW(value_json):
    value_json['CreateTenantNW'] = True


# sub-routine: set vlan value.
def update_json_vlanid(
    value_json,
    network_id,
    physical_network,
    segmentation_id,
        vlan_id):
    value_json[
        'VLAN_' +
        network_id +
        '_' +
        physical_network] = 'physical_network'
    value_json[
        'VLAN_' +
        network_id +
        '_' +
        physical_network +
        '_segmentation_id'] = segmentation_id
    value_json[
        'VLAN_' +
        network_id +
        '_' +
        physical_network +
        '_VlanID'] = vlan_id


# update json object: set result of /umf/workflowinstance/(executionid)
# for CreateVLAN
def update_json_post_CreateVLAN(
    value_json,
    network_id,
    network_name,
    subnet_id,
    cidr,
    logical_nw_name,
    physical_network,
    segmentation_id,
        vlan_id):
    value_json['NW_' + network_id] = network_name
    value_json['NW_' + network_id + '_network_id'] = network_id
    value_json['NW_' + network_id + '_subnet_id'] = subnet_id
    value_json['NW_' + network_id + '_subnet'] = cidr  # subnet['cidr']
    value_json[
        'NW_' +
        network_id +
        '_nwa_network_name'] = logical_nw_name
    # retJson['resultdata']['LogicalNWName']
    if vlan_id != '':  # retJson['resultdata']['VlanID'] != '':
        update_json_vlanid(
            value_json,
            network_id,
            physical_network,
            segmentation_id,
            vlan_id)


# update json object: set result of /umf/workflowinstance/(executionid)
# for CreateTenantFW
def update_json_post_CreateTenantFW(
    value_json,
    network_id,
    network_name,
    physical_network,
    segmentation_id,
    vlan_id,
    device_id,
    device_owner,
    tenant_nw_name,
    ip_address,
        mac_address):
    value_json['DEV_' + device_id] = 'device_id'
    value_json['DEV_' + device_id + '_physical_network'] = physical_network
    value_json['DEV_' + device_id + '_device_owner'] = device_owner
    value_json[
        'DEV_' +
        device_id +
        '_TenantFWName'] = tenant_nw_name
    # retJson['resultdata']['TenantFWName']
    value_json['DEV_' + device_id + '_' + network_id] = network_name
    value_json[
        'DEV_' +
        device_id +
        '_' +
        network_id +
        '_ip_address'] = ip_address
    # context._port['fixed_ips'][0]['ip_address']
    value_json[
        'DEV_' +
        device_id +
        '_' +
        network_id +
        '_mac_address'] = mac_address  # context._port['mac_address']
    if vlan_id != '':  # retJson['resultdata']['VlanID'] != '':
        update_json_vlanid(
            value_json,
            network_id,
            physical_network,
            segmentation_id,
            vlan_id)


# update json object: set result of /umf/workflowinstance/(executionid)
# for UpdateTenantFW
def update_json_post_UpdateTenantFW(
    value_json,
    network_id,
    network_name,
    physical_network,
    segmentation_id,
    vlan_id,
    device_id,
    ip_address,
        mac_address):
    value_json['DEV_' + device_id + '_' + network_id] = network_name
    value_json[
        'DEV_' +
        device_id +
        '_' +
        network_id +
        '_ip_address'] = ip_address
    # context._port['fixed_ips'][0]['ip_address']
    value_json[
        'DEV_' +
        device_id +
        '_' +
        network_id +
        '_mac_address'] = mac_address  # context._port['mac_address']
    if vlan_id != '':  # retJson['resultdata']['VlanID'] != '':
        update_json_vlanid(
            value_json,
            network_id,
            physical_network,
            segmentation_id,
            vlan_id)


# update json object: set result of /umf/workflowinstance/(executionid)
# for CreateGeneralDev
def update_json_post_CreateGeneralDev(
    value_json,
    physical_network,
    segmentation_id,
    network_id,
        vlan_id):
    update_json_vlanid(
        value_json,
        network_id,
        physical_network,
        segmentation_id,
        vlan_id)


# update json object: set result of '/umf/workflow/'+SettingNAT+'/execute'
# fip_id: floatingip id
def update_json_post_SettingNAT(
    value_json,
    device_id,
    fip_id,
    fip_network_id,
    fip_ip_address,
        fip_fixed_ip_address):
    value_json['NAT_' + fip_id] = device_id
    value_json['NAT_' + fip_id + '_network_id'] = fip_network_id
    value_json['NAT_' + fip_id + '_floating_ip_address'] = fip_ip_address
    value_json['NAT_' + fip_id + '_fixed_ip_address'] = fip_fixed_ip_address
    if 'NATnumber' not in value_json:
        value_json['NATnumber'] = 0
    value_json['NATnumber'] = str(int(value_json['NATnumber']) + 1)


def ensure_port_binding(session, port_id):

    with session.begin(subtransactions=True):
        try:
            record = (session.query(models_ml2.PortBindingLevel).
                      filter_by(port_id=port_id).
                      one())
        except sa.orm.exc.NoResultFound:
            # for kilo(re mearge)
            record = (session.query(models_ml2.PortBinding).
                      filter_by(port_id=port_id).
                      one())
        return record


def add_nwa_tenant_queue(session, tenant_id, nwa_tenant_id='', topic=''):
    try:
        nwa = session.query(nmodels.NWATenantQueue).filter(
            nmodels.NWATenantQueue.tenant_id == tenant_id).all()
        if len(nwa) > 0:
            return False
        with session.begin(subtransactions=True):
            nwa = nmodels.NWATenantQueue(
                tenant_id,
                nwa_tenant_id,
                topic
            )
            session.add(nwa)
        return True
    except sa.orm.exc.NoResultFound:
        return False


def get_nwa_tenant_queue(session, tenant_id):
    try:
        queue = session.query(nmodels.NWATenantQueue).filter(
            nmodels.NWATenantQueue.tenant_id == tenant_id).one()

        if queue:
            return queue
        else:
            return None
    except sa.orm.exc.NoResultFound:
        return None


def get_nwa_tenant_queues(session):
    try:
        queues = session.query(nmodels.NWATenantQueue).all()

        if len(queues) > 0:
            return queues
        else:
            return []
    except sa.orm.exc.NoResultFound:
        return None


def del_nwa_tenant_queue(session, tenant_id):
    try:
        with session.begin(subtransactions=True):
            item = get_nwa_tenant_queue(session, tenant_id)
            if item is None:
                return False
            with session.begin(subtransactions=True):
                session.query(nmodels.NWATenantQueue).filter(
                    nmodels.NWATenantQueue.tenant_id == tenant_id
                ).delete()
            session.flush()
            return True
    except sa.orm.exc.NoResultFound:
        return False


def add_nwa_firewall_rule(session, rule):
    try:
        recs = session.query(nmodels.NWAFirewallRule).filter(
            nmodels.NWAFirewallRule.id == rule['id']).all()
        if len(recs) > 0:
            return False

        with session.begin(subtransactions=True):
            rec = nmodels.NWAFirewallRule(
                rule
            )
            session.add(rec)
        return True

    except sa.orm.exc.NoResultFound:
        return False


# def create_fwaas_ids(session, tfw_name, max_index=65535):
def create_fwaas_ids(session, tfw_name, max_index=1024):
    try:
        recs = session.query(nmodels.NWAFirewallIds).filter(
            nmodels.NWAFirewallIds.tfw == tfw_name).all()

        if len(recs) > 0:
            return False

        with session.begin(subtransactions=True):
            recs = []
            for res_id in range(1, max_index + 1):
                recs.append(
                    nmodels.NWAFirewallIds(
                        res_id, tfw_name, None, used=False
                    )
                )
            session.add_all(recs)

        return True
    except Exception:
        return False


def get_fwaas_id(session, tfw, type):
    try:
        with session.begin(subtransactions=True):
            rec = session.query(nmodels.NWAFirewallIds).filter(
                nmodels.NWAFirewallIds.tfw == tfw
            ).filter(
                nmodels.NWAFirewallIds.used == 0
            ).order_by(
                nmodels.NWAFirewallIds.created_at
            ).order_by(
                nmodels.NWAFirewallIds.res_id
            ).first()

            if not rec:
                return 0

            rec.type = type
            rec.used = True
            rec.created_at = timeutils.utcnow()
            return rec.res_id
    except Exception:
        return 0


def blk_clear_fwaas_id(session, tfw, ids):
    try:
        with session.begin(subtransactions=True):
            for res_id in ids:
                rec = session.query(nmodels.NWAFirewallIds).filter(
                    nmodels.NWAFirewallIds.tfw == tfw
                ).filter(
                    nmodels.NWAFirewallIds.type == type
                ).filter(
                    nmodels.NWAFirewallIds.res_id == res_id
                ).one()

                rec.type = ''
                rec.used = False
                rec.created_at = timeutils.utcnow()

        return True

    except Exception:
        return False


def clear_fwaas_id(session, tfw, type, res_id):
    try:
        with session.begin(subtransactions=True):
            rec = session.query(nmodels.NWAFirewallIds).filter(
                nmodels.NWAFirewallIds.tfw == tfw
            ).filter(
                nmodels.NWAFirewallIds.type == type
            ).filter(
                nmodels.NWAFirewallIds.res_id == res_id
            ).one()

            rec.type = ''
            rec.used = False
            rec.created_at = timeutils.utcnow()
            return True
    except Exception:
        return False


def delete_fwaas_ids(session, tfw_name):
    try:
        with session.begin(subtransactions=True):
            recs = session.query(nmodels.NWAFirewallIds).filter(
                nmodels.NWAFirewallIds.tfw == tfw_name
            ).all()
            if not recs:
                return False
            query = (session.query(nmodels.NWAFirewallIds).
                     filter_by(tfw=tfw_name))
            query.delete()
        return True

    except Exception:
        return False


def add_nwa_fwaas(session, tenant_id, fwaas_id, tfw_name):
    try:
        fwaas = session.query(nmodels.NWAFWaaS).filter(
            nmodels.NWAFWaaS.tenant_id == tenant_id).all()
        if len(fwaas) > 0:
            return False
        with session.begin(subtransactions=True):
            nwa = nmodels.NWAFWaaS(
                tenant_id,
                fwaas_id,
                tfw_name
            )
            session.add(nwa)
        return True
    except sa.orm.exc.NoResultFound:
        return False


def add_nwa_address_group(session, id, tenant_id, policy_id):
    try:
        address_group = session.query(nmodels.NWAFWaaSAddressGroup).filter(
            nmodels.NWAFWaaSAddressGroup.id == id).all()

        if len(address_group) > 0:
            return False

        with session.begin(subtransactions=True):
            rec = nmodels.NWAFWaaSAddressGroup(
                id, tenant_id, policy_id
            )
            session.add(rec)
        return True
    except sa.orm.exc.NoResultFound:
        return False


# id       ... address member id 1-65535
# type     ... type
# rule_id  ... rule uuid
# subnet   ... subnet address
# address  ... ip address
def add_nwa_address_member(session, type, policy_id, rule_id, subnet, address,
                           id=0):
    try:
        num = id if isinstance(id, int) else int(id)
        if(
                num < NWA_MIN_ID or
                NWA_MAX_ID < num
        ):
            return None

        member = session.query(nmodels.NWAFWaaSAddressMember).filter(
            nmodels.NWAFWaaSAddressMember.id == num).all()

        if len(member) > 0:
            return None

        with session.begin(subtransactions=True):
            rec = nmodels.NWAFWaaSAddressMember(
                type, policy_id, rule_id, subnet, address, num
            )
            session.add(rec)

        return {
            'id': str(rec.id),
            'policy_id': rec.policy_id,
            'rule_id': rec.rule_id,
            'type': rec.type,
            'subnet': rec.subnet
        }

    except sa.orm.exc.NoResultFound:
        return None
    except ValueError:
        return None


def add_nwa_fwaas_policy(session, tenant_id, rule, id=0):
    try:
        num = id if isinstance(id, int) else int(id)
        if(
                num < NWA_MIN_ID or
                NWA_MAX_ID < num
        ):
            return None

        member = session.query(nmodels.NWAFWaaSPolicy).filter(
            nmodels.NWAFWaaSPolicy.id == num).all()

        if len(member) > 0:
            return None

        with session.begin(subtransactions=True):
            rec = nmodels.NWAFWaaSPolicy(
                num, rule['firewall_policy_id'], rule['id']
            )
            session.add(rec)
            print(rec)

        return {
            'id': rec.id
        }

    except sa.orm.exc.NoResultFound:
        return None

    except ValueError:
        return None
