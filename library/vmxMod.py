#!usr/bin/env python
from __future__ import print_function

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
            ip_address=dict(required=True, default=None)
        )
    )

    if pyvmomi_import_failure is True:
        module.fail_json(msg='pyVmomi is required')

    vcenter_host = module.params.get('vcenter_host')
    vcenter_user = module.params.get('vcenter_user')
    vcenter_password = module.params.get('vcenter_password')
    vcenter_port = module.params.get('vcenter_port')
    ip_address = module.params.get('ip_address')

    try:
        # Disable ssl verification
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE

        # Creates connection to the VC..
        service_instance = None
        try:
            service_instance = connect.SmartConnect(host=vcenter_host,
                                                    user=vcenter_user,
                                                    pwd=vcenter_password,
                                                    port=vcenter_port,
                                                    sslContext=context)

            atexit.register(connect.Disconnect, service_instance)
        except IOError:
            pass

        if not service_instance:
            raise SystemExit("Unable to connect to the vCenter."
                             "Please check the info and try again")

        # Query the inventory for a specific managed entity by attributes.
        search_index = service_instance.content.searchIndex

        vm = None
        try:
            vm = search_index.FindByIp(None, ip_address, True)
        except:
            raise SystemExit("Could not find virtual machine."
                             "Please check the vm is powered on"
                             "and IP address")

        print("Found: {0}".format(vm.name))

        # The ConfigSpec data object type encapsulates configuration settings
        # when creating or reconfiguring a virtual machine.
        spec = vim.vm.ConfigSpec()
        opt = vim.option.OptionValue()
        spec.extraConfig = []

        # Setting key/values to add. This will disable quiescing
        opt.key = 'disk.EnableUUID'
        opt.value = "FALSE"
        spec.extraConfig.append(opt)
        opt = vim.option.OptionValue()
        TASK = vm.ReconfigVM_Task(spec)
        wait_for_tasks(service_instance, [TASK])

    except Exception as e:
        module.fail_json(msg="vmxMod.py: " + str(e))

    # Get the value of the key and check that it matches what's expected afterwards
    keys_and_vals = vm.config.extraConfig

    for opts in keys_and_vals:
        if opts.key == "disk.EnableUUID" and opts.value == "FALSE":
            print ("Value matches what's expected: " + opts.value)
            break
    else:
        raise SystemExit("Value is incorrect.")
    module.exit_json(msg="Success")


if __name__ == "__main__":
    main()
