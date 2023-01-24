#!/usr/bin/env python

import atexit
import ssl
from ansible.module_utils.basic import AnsibleModule

try:
    from pyVim import connect
    from pyVmomi import vim
    from pyVmomi import vmodl
    pyvmomi_import_failure = False
except ImportError:
    pyvmomi_import_failure = True


def _get_container_view(content, view_type):
    """
    Gets a container view for the vCenter connection of the specified type
    Args:
        view_type (str): A string specifying the `vim.ManagedObject`_
            type: vim.ComputeResource, vim.Datacenter, vim.Folder,
                vim.VirtualMachine, etc.
    Returns:
        vim.view.ContainerView: The `ContainerView`_
        with the objects for the requested type
    """
    container = content.rootFolder
    recursive = True
    container_view = content.viewManager.CreateContainerView(
        container,
        view_type, recursive)
    return container_view


def _init_virtual_machines(content):
    """
    Initializes the virtual machines in the datacenter
    for the specified region
    Returns:
        sets the class attribute virtual_machines
    """
    virtual_machines = {"vm_names": [], "vm_objs": {}}
    vimtype = [vim.VirtualMachine]
    vm_container_view = _get_container_view(content, vimtype)
    vm_indx = 0
    for vm in vm_container_view.view:
        try:
            if isinstance(vm, vim.VirtualMachine):
                virtual_machines["vm_objs"][vm_indx] = vm
                virtual_machines["vm_names"].append(vm.name)
                vm_indx += 1
        except Exception as e:
            if e.message == 'The object has already been deleted or \
                             has not been completely created':
                pass
    return virtual_machines


def main():
    module = AnsibleModule(
        argument_spec=dict(
            vcenter_host=dict(required=True, default=None),
            vcenter_user=dict(required=True, default=None),
            vcenter_password=dict(required=True, default=None),
            vcenter_port=dict(required=True, type='int', default=None),
            vm_name=dict(required=True, default=None)
        )
    )

    if pyvmomi_import_failure is True:
        module.fail_json(msg='pyVmomi is required')

    vcenter_host = module.params.get('vcenter_host')
    vcenter_user = module.params.get('vcenter_user')
    vcenter_password = module.params.get('vcenter_password')
    vcenter_port = module.params.get('vcenter_port')
    vm_name = module.params.get('vm_name')

    try:
        # Disable ssl verification
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE
        # @todo - Need to add error handler for connection timeout?
        service_instance = connect.SmartConnect(host=vcenter_host,
                                                user=vcenter_user,
                                                pwd=vcenter_password,
                                                port=vcenter_port,
                                                sslContext=context)

        atexit.register(connect.Disconnect, service_instance)
        content = service_instance.RetrieveContent()
        virtual_machines = _init_virtual_machines(content)
        if vm_name in virtual_machines['vm_names']:
            module.exit_json(msg="Appliance exists!")
        else:
            module.exit_json(msg="Appliance does not exist.")

    except vmodl.MethodFault as error:
        module.fail_json(msg="vmodl.MethodFault: " + str(error))


if __name__ == "__main__":
    main()
