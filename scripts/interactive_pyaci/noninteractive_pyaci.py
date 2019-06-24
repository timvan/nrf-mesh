import time
import logging

from argparse import ArgumentParser

from aci.aci_uart import Uart
from aci.aci_utils import STATUS_CODE_LUT
from aci.aci_config import ApplicationConfig
import aci.aci_cmd as cmd
import aci.aci_evt as evt

from mesh.database import MeshDB
from interactive_pyaci import Interactive
from mesh.provisioning import Provisioner

class Manager(object):

    def __init__(self, device, db_path="database/example_database.json"):
        self.device = device
        self.db = MeshDB(db_path)

    def provision(self):
        self.p = Provisioner(self.device, self.db)
        self.p.scan_start()
        time.sleep(5)
        self.p.scan_stop()
        self.p.provision(name="Client")
    
    def run(self):
        self.provision()

if __name__ == '__main__':

    parser = ArgumentParser(
        description="nRF5 SDK for Mesh Interactive PyACI")
    parser.add_argument("-d", "--device",
                        dest="devices",
                        nargs="+",
                        required=False,
                        default=["/dev/tty.usbmodem0006822145041"],
                        help=("Device Communication port, e.g., COM216 or "
                              + "/dev/ttyACM0. You may connect to multiple "
                              + "devices. Separate devices by spaces, e.g., "
                              + "\"-d COM123 COM234\""))
    parser.add_argument("-b", "--baudrate",
                        dest="baudrate",
                        required=False,
                        default='115200',
                        help="Baud rate. Default: 115200")
    parser.add_argument("--no-logfile",
                        dest="no_logfile",
                        action="store_true",
                        required=False,
                        default=False,
                        help="Disables logging to file.")
    parser.add_argument("-l", "--log-level",
                        dest="log_level",
                        type=int,
                        required=False,
                        default=3,
                        help=("Set default logging level: "
                              + "1=Errors only, 2=Warnings, 3=Info, 4=Debug"))
    options = parser.parse_args()

    if options.log_level == 1:
        options.log_level = logging.ERROR
    elif options.log_level == 2:
        options.log_level = logging.WARNING
    elif options.log_level == 3:
        options.log_level = logging.INFO
    else:
        options.log_level = logging.DEBUG


    dev_com = options.devices[0]
    device = Interactive(Uart(port=dev_com,
                                  baudrate=options.baudrate,
                                  device_name=dev_com.split("/")[-1]))

    m = Manager(device)
    m.run()