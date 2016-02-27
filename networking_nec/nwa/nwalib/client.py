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

from networking_nec.nwa.nwalib import client_fwaas
from networking_nec.nwa.nwalib import client_l2
from networking_nec.nwa.nwalib import client_l3
from networking_nec.nwa.nwalib import client_lbaas
from networking_nec.nwa.nwalib import client_tenant
from networking_nec.nwa.nwalib import nwa_restclient


class NwaClient(nwa_restclient.NwaRestClient):
    '''Client class of NWA. '''

    def __init__(self, *args, **kwargs):
        super(NwaClient, self).__init__(*args, **kwargs)

        self.tenant = client_tenant.NwaClientTenant(self)
        self.l2 = client_l2.NwaClientL2(self)
        self.l3 = client_l3.NwaClientL3(self)
        self.fwaas = client_fwaas.NwaClientFWaaS(self)
        self.lbaas = client_lbaas.NwaClientLBaaS(self)
