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

logs = []


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


def wait_for_tasks(service_instance, tasks):
    """Given the service instance si and tasks, it returns after all the
   tasks are complete
   """
    property_collector = service_instance.content.propertyCollector
    task_list = [str(task) for task in tasks]
    # Create filter
    obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                 for task in tasks]
    property_spec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task,
                                                               pathSet=[],
                                                               all=True)
    filter_spec = vmodl.query.PropertyCollector.FilterSpec()
    filter_spec.objectSet = obj_specs
    filter_spec.propSet = [property_spec]
    pcfilter = property_collector.CreateFilter(filter_spec, True)
    try:
        version, state = None, None
        # Loop looking for updates till the state moves to a completed state.
        while len(task_list):
            update = property_collector.WaitForUpdates(version)
            for filter_set in update.filterSet:
                for obj_set in filter_set.objectSet:
                    task = obj_set.obj
                    for change in obj_set.changeSet:
                        if change.name == 'info':
                            state = change.val.state
                        elif change.name == 'info.state':
                            state = change.val
                        else:
                            continue

                        if not str(task) in task_list:
                            continue

                        if state == vim.TaskInfo.State.success:
                            # Remove task from taskList
                            task_list.remove(str(task))
                        elif state == vim.TaskInfo.State.error:
                            raise task.info.error
            # Move to next version
            version = update.version
    finally:
        if pcfilter:
            pcfilter.Destroy()


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
        vm_indx = 0
        for name in virtual_machines['vm_names']:
            if name == vm_name:
                delete_vm(virtual_machines['vm_objs'][vm_indx], service_instance, module)
            vm_indx += 1

        module.exit_json(msg="Appliance does not exist. No action taken.", meta=logs)

    except vmodl.MethodFault as error:
        module.fail_json(msg="vmodl.MethodFault: " + str(error), meta=logs)


def delete_vm(vm, service_instance, module):

    logs.append("Found: {0}".format(vm.name))
    logs.append("The current powerState is: {0}".format(vm.runtime.powerState))
    if vm.runtime.powerState == 'poweredOn':
        logs.append("Attempting to power off {0}".format(vm.name))
        TASK = vm.PowerOffVM_Task()
        wait_for_tasks(service_instance, [TASK])
        logs.append("{0}".format(TASK.info.state))

    logs.append("Destroying VM from vSphere.")
    TASK = vm.Destroy_Task()
    wait_for_tasks(service_instance, [TASK])
    logs.append("Done.")
    module.exit_json(msg="Appliance exists! - Destroying!", meta=logs)


if __name__ == "__main__":
    main()
