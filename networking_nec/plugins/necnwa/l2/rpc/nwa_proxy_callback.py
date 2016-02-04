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

from oslo_log import log as logging
from oslo_serialization import jsonutils

LOG = logging.getLogger(__name__)


class NwaProxyCallback(object):
    RPC_API_VERSION = '1.0'

    def __init__(self, context, agent):
        self.context = context
        self.agent = agent

    def create_general_dev(self, context, **kwargs):
        LOG.debug("Rpc callback kwargs=%s", jsonutils.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))
        return self.agent.create_general_dev(context, **kwargs)

    def delete_general_dev(self, context, **kwargs):
        LOG.debug("Rpc callback kwargs=%s", jsonutils.dumps(
            kwargs,
            indent=4,
            sort_keys=True
        ))
        return self.agent.delete_general_dev(context, **kwargs)
