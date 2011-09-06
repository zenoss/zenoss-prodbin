# ZenReports.Utils contains some useful helpers for creating records to return.
from Products.ZenReports import Utils


# The class name must patch the filename.
class example_plugin:

    # The run method will be executed when your report calls the plugin.
    def run(self, dmd, args):
        report = []
        for device in dmd.Devices.getSubDevicesGen():
            report.append(Utils.Record(
                device=device.titleOrId(),
                ip=device.manageIp,
                hardware="%s %s" % (
                    device.hw.getManufacturerName(),
                    device.hw.getProductName()),
                software="%s %s" % (
                    device.os.getManufacturerName(),
                    device.os.getProductName()),
                ))

        return report
