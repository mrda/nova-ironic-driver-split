# Copyright 2014 Red Hat, Inc.
# All Rights Reserved.
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

from ironicclient import client as ironic_client
from ironicclient import exc as ironic_exception
import mock
from oslo.config import cfg

from nova import exception
from nova import test
from nova.tests.virt.ironic import utils as ironic_utils
from nova.virt.ironic import client_wrapper

CONF = cfg.CONF

FAKE_CLIENT = ironic_utils.FakeClient()


class IronicClientWrapperTestCase(test.NoDBTestCase):

    def setUp(self):
        super(IronicClientWrapperTestCase, self).setUp()
        self.icli = client_wrapper.IronicClientWrapper()
        # Do not waste time sleeping
        cfg.CONF.set_override('api_retry_interval', 0, 'ironic')

    @mock.patch.object(client_wrapper.IronicClientWrapper, '_multi_getattr')
    @mock.patch.object(client_wrapper.IronicClientWrapper, '_get_client')
    def test_call_good_no_args(self, mock_get_client, mock_multi_getattr):
        mock_get_client.return_value = FAKE_CLIENT
        self.icli.call("node.list")
        mock_get_client.assert_called_once_with()
        mock_multi_getattr.assert_called_once_with(FAKE_CLIENT, "node.list")
        mock_multi_getattr.return_value.assert_called_once_with()

    @mock.patch.object(client_wrapper.IronicClientWrapper, '_multi_getattr')
    @mock.patch.object(client_wrapper.IronicClientWrapper, '_get_client')
    def test_call_good_with_args(self, mock_get_client, mock_multi_getattr):
        mock_get_client.return_value = FAKE_CLIENT
        self.icli.call("node.list", 'test', associated=True)
        mock_get_client.assert_called_once_with()
        mock_multi_getattr.assert_called_once_with(FAKE_CLIENT, "node.list")
        mock_multi_getattr.return_value.assert_called_once_with(
            'test', associated=True)

    @mock.patch.object(ironic_client, 'get_client')
    def test__get_client_no_auth_token(self, mock_ir_cli):
        self.flags(admin_auth_token=None, group='ironic')
        icli = client_wrapper.IronicClientWrapper()
        # dummy call to have _get_client() called
        icli.call("node.list")
        expected = {'os_username': CONF.ironic.admin_username,
                    'os_password': CONF.ironic.admin_password,
                    'os_auth_url': CONF.ironic.admin_url,
                    'os_tenant_name': CONF.ironic.admin_tenant_name,
                    'os_service_type': 'baremetal',
                    'os_endpoint_type': 'public'}
        mock_ir_cli.assert_called_once_with(CONF.ironic.api_version,
                                            **expected)

    @mock.patch.object(ironic_client, 'get_client')
    def test__get_client_with_auth_token(self, mock_ir_cli):
        self.flags(admin_auth_token='fake-token', group='ironic')
        icli = client_wrapper.IronicClientWrapper()
        # dummy call to have _get_client() called
        icli.call("node.list")
        expected = {'os_auth_token': 'fake-token',
                    'ironic_url': CONF.ironic.api_endpoint}
        mock_ir_cli.assert_called_once_with(CONF.ironic.api_version,
                                            **expected)

    @mock.patch.object(client_wrapper.IronicClientWrapper, '_multi_getattr')
    @mock.patch.object(client_wrapper.IronicClientWrapper, '_get_client')
    def test_call_fail(self, mock_get_client, mock_multi_getattr):
        cfg.CONF.set_override('api_max_retries', 2, 'ironic')
        test_obj = mock.Mock()
        test_obj.side_effect = ironic_exception.HTTPServiceUnavailable
        mock_multi_getattr.return_value = test_obj
        mock_get_client.return_value = FAKE_CLIENT
        self.assertRaises(exception.NovaException, self.icli.call, "node.list")
        self.assertEqual(2, test_obj.call_count)

    @mock.patch.object(client_wrapper.IronicClientWrapper, '_multi_getattr')
    @mock.patch.object(client_wrapper.IronicClientWrapper, '_get_client')
    def test_call_fail_unexpected_exception(self, mock_get_client,
                                            mock_multi_getattr):
        test_obj = mock.Mock()
        test_obj.side_effect = ironic_exception.HTTPNotFound
        mock_multi_getattr.return_value = test_obj
        mock_get_client.return_value = FAKE_CLIENT
        self.assertRaises(ironic_exception.HTTPNotFound, self.icli.call,
                          "node.list")

    @mock.patch.object(ironic_client, 'get_client')
    def test__get_client_unauthorized(self, mock_get_client):
        mock_get_client.side_effect = ironic_exception.Unauthorized
        self.assertRaises(exception.NovaException, self.icli._get_client)

    @mock.patch.object(ironic_client, 'get_client')
    def test__get_client_unexpected_exception(self, mock_get_client):
        mock_get_client.side_effect = ironic_exception.ConnectionRefused
        self.assertRaises(ironic_exception.ConnectionRefused,
                          self.icli._get_client)

    def test__multi_getattr_good(self):
        response = self.icli._multi_getattr(FAKE_CLIENT, "node.list")
        self.assertEqual(FAKE_CLIENT.node.list, response)

    def test__multi_getattr_fail(self):
        self.assertRaises(AttributeError, self.icli._multi_getattr,
                          FAKE_CLIENT, "nonexistent")
