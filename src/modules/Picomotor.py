import usb.core
import usb.util
from usb.backend import libusb1
import re
from ..utils.utils import Logger


'''
Adapted from python_newport_controller

https://github.com/bdhammel/python_newport_controller
'''


NEWFOCUS_COMMAND_REGEX = re.compile("([0-9]{0,1})([a-zA-Z?]{2,})([0-9+-]*)")
MOTOR_TYPE = {
        "0":"No motor connected",
        "1":"Motor Unknown",
        "2":"'Tiny' Motor",
        "3":"'Standard' Motor"
        }


class PicoMotor(Logger):
    """Picomotor Controller
    Example:
        >>> controller = Controller(idProduct=0x4000, idVendor=0x104d)
        >>> controller.command('VE?')
        
        >>> controller.start_console()
    """


    def __init__(self, master, idProduct=0x4000, idVendor=0x104d):
        """Initialize the Picomotor class with the spec's of the attached device
        Call self._connect to set up communication with usb device and endpoints 
        
        Args:
            idProduct (hex): Product ID of picomotor controller (from device manager)
            idVendor (hex): Vendor ID of picomotor controller
        """
        self.willStop = False
        self.master = master
        self.master.register(self)
        
        self.idProduct = idProduct
        self.idVendor = idVendor
        
        self.connected_motors = []
        
        if not self.master.TEST_MODE:
            self._connect()
        
        
    def stop(self):
        if self.master.TEST_MODE:
            return
        if hasattr(self, 'dev'):
            self.dev.reset()
            usb.util.dispose_resources(self.dev)
            # del self.dev
            self.log('USB interface closed')


    def _connect(self):
        """Connect class to USB device 
        Find device from Vendor ID and Product ID
        Setup taken from [1]
        Raises:
            ValueError: if the device cannot be found by the Vendor ID and Product
                ID
            Assert False: if the input and outgoing endpoints can't be established
        """
        # find the device
        backend = libusb1.get_backend(find_library=lambda x: "modules/libusb-1.0.dll")
        
        # TODO: Fix backend path!! ^^
        self.dev = usb.core.find(
                        backend=backend,
                        idProduct=self.idProduct,
                        idVendor=self.idVendor
                        )
       
        if self.dev is None:
            raise ValueError('Device not found')

        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        self.dev.set_configuration()

        # get an endpoint instance
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0,0)]

        self.ep_out = usb.util.find_descriptor(
            intf,
            # match the first OUT endpoint
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_OUT)

        self.ep_in = usb.util.find_descriptor(
            intf,
            # match the first IN endpoint
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_IN)

        assert (self.ep_out and self.ep_in) is not None
        
        # Confirm connection to user
        resp = self.command('VE?')
        self.log("Connected to Motor Controller Model {}. Firmware {} {} {}\n".format(
                                                    *resp.split(' ')
                                                    ))
        for m in range(1,3):
            resp = self.command("{}QM?".format(m))
            print("Motor #{motor_number}: {status}".format(
                                                    motor_number=m,
                                                    status=MOTOR_TYPE[resp[-1]]
                                                    ))
            if (resp[-1] == '2' or resp[-1] == '3'):
                self.connected_motors.append(m)



    def send_command(self, usb_command, get_reply=False):
        """Send command to USB device endpoint
        
        Args:
            usb_command (str): Correctly formated command for USB driver
            get_reply (bool): query the IN endpoint after sending command, to 
                get controller's reply
        Returns:
            Character representation of returned hex values if a reply is 
                requested
        """
        if self.master.TEST_MODE:
            return
        self.ep_out.write(usb_command)
        if get_reply:
            return self.ep_in.read(100)
            

    def parse_command(self, newfocus_command):
        """Convert a NewFocus style command into a USB command
        Args:
            newfocus_command (str): of the form xxAAnn
                > The general format of a command is a two character mnemonic (AA). 
                Both upper and lower case are accepted. Depending on the command, 
                it could also have optional or required preceding (xx) and/or 
                following (nn) parameters.
                cite [2 - 6.1.2]
        """
        m = NEWFOCUS_COMMAND_REGEX.match(newfocus_command)
        # m = True

        # Check to see if a regex match was found in the user submitted command
        if m:

            # Extract matched components of the command
            driver_number, command, parameter = m.groups()


            usb_command = command

            # Construct USB safe command
            if driver_number:
                usb_command = '1>{driver_number} {command}'.format(
                                                    driver_number=driver_number,
                                                    command=usb_command
                                                    )
            if parameter:
                usb_command = '{command} {parameter}'.format(
                                                    command=usb_command,
                                                    parameter=parameter
                                                    )

            usb_command += '\r'

            return usb_command
        else:
            self.log("ERROR! Command {} was not a valid format".format(
                                                            newfocus_command
                                                            ))


    def parse_reply(self, reply):
        """Take controller's reply and make human readable
        Args:
            reply (list): list of bytes returns from controller in hex format
        Returns:
            reply (str): Cleaned string of controller reply
        """

        # convert hex to characters 
        reply = ''.join([chr(x) for x in reply])
        return reply.rstrip()


    def command(self, newfocus_command):
        """Send NewFocus formated command
        Args:
            newfocus_command (str): Legal command listed in usermanual [2 - 6.2] 
        Returns:
            reply (str): Human readable reply from controller
        """
        if self.master.TEST_MODE:
            return
        usb_command = self.parse_command(newfocus_command)

        # if there is a '?' in the command, the user expects a response from
        # the driver
        if '?' in newfocus_command:
            get_reply = True
        else:
            get_reply = False

        reply = self.send_command(usb_command, get_reply)

        # if a reply is expected, parse it
        if get_reply:
            return self.parse_reply(reply)
                           
    
    def step(self, n_steps):
        '''
        Step pico motor the requested number of steps
        Args:
            n_steps: signed int
        '''
        if not type(n_steps) == int:
            print('Invalid input to PicoMotor')
            return
        
        self.command(f'1PR{n_steps}')
        
        
    def halt(self):
        '''
        Send a halt command immediately
        '''
        self.command('AB')
        
    
    def move_y(self, dist):
        '''
        Step y-axis pico motor the appropriate number of steps to move
        the requested distance
        Args:
            dist: int, distance in microns
        '''
        n_steps = int(dist/0.03)
        self.log(f'Moving {n_steps} steps on y piezo.')
        
        if 2 in self.connected_motors:
            self.command(f'2PR{n_steps}')
            return True
        return False
        
        
    def start_console(self):
        """Continuously ask user for a command
        """
        print('''
        Picomotor Command Line
        ---------------------------
        Enter a valid NewFocus command, or 'quit' to exit the program.
        Common Commands:
            xMV[+-]: .....Indefinitely move motor 'x' in + or - direction
                 ST: .....Stop all motor movement
              xPRnn: .....Move motor 'x' 'nn' steps
        \n
        ''')

        while True:
            command = input("Input > ")
            if command.lower() in ['q', 'quit', 'exit']: 
                break
            else:
                rep = self.command(command)
                if rep:
                    print("Output: {}".format(rep))
        
        
        




if __name__ == '__main__':

    controller = PicoMotor()
    controller.start_console()
    controller.close()
    
    
    
    
    
    
    
    
