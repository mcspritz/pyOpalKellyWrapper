__author__ = 'Luca Parmesan'

import imp
import csv
from platform import architecture, system
from warnings import warn
from os import getcwd


class OpalKelly:
    """A simplified version of the Opal Kelly class"""
    if system() == 'Windows':
        if architecture()[0] == '32bit':
            ok = imp.load_source('ok', './opalkelly_beta/32bit/ok/ok.py')
        elif architecture()[0] == '64bit':
            ok = imp.load_source('ok', './opalkelly_beta/64bit/ok/ok.py')
        else:
            raise Exception('Architecture not recognised')
    else:
        raise Exception('OS not recognised')

    _registers_ = []
    pll_info = {}

    _clk_sources_ = {'REF': 0,
                     'PLL0-0': 2,
                     'PLL0-180': 3,
                     'PLL1-0': 4,
                     'PLL1-180': 5,
                     'PLL2-0': 6,
                     'PLL2-180': 7,
                     }

    # Opal Kelly error codes
    _ok_errors_ = {0: 'NoError',
                   -1: 'Failed',
                   -2: 'Timeout',
                   -3: 'DoneNotHigh',
                   -4: 'TransferError',
                   -5: 'CommunicationError',
                   -6: 'InvalidBitstream',
                   -7: 'FileError',
                   -8: 'DeviceNotOpen',
                   -9: 'InvalidEndpoint',
                   -10: 'InvalidBlockSize',
                   -11: 'I2CRestrictedAddress',
                   -12: 'I2CBitError',
                   -13: 'I2CNack',
                   -14: 'I2CUnknownStatus',
                   -15: 'UnsupportedFeature',
                   -16: 'FIFOUnderflow',
                   -17: 'FIFOOverflow',
                   -18: 'DataAlignmentError',
                   -19: 'InvalidResetProfile',
                   -20: 'InvalidParameter',
                   }

    def __init__(self, bit_file, register_file):
        """Initialisation of the Opal Kelly and its PLL"""

        self._xem_ = self.ok.FrontPanel()
        self._info_ = self.ok.okTDeviceInfo()

        self._xem_.OpenBySerial('')
        self._xem_.GetDeviceInfo(self._info_)

        # choosing the right PLL
        self._pll = self.ok.PLL22150()
        if self._xem_.GetPLL22150Configuration(self._pll) == 0:
            self._whichPLL_ = 'PLL22150'
            #self.pll_info = self._xem.GetPLL22150Configuration(self._pll)
            self._update_pll_()
        else:
            del self._pll
            self._pll = self.ok.PLL22393()
            if self._xem_.GetPLL22393Configuration(self._pll) == 0:
                self._whichPLL_ = 'PLL22393'
                self.pll_info = self._xem_.GetPLL22393Configuration(self._pll)
                self._update_pll_()

        config = self._xem_.ConfigureFPGA(bit_file)
        if config is not 0:
            raise Exception('Wrong bit file selected')

        self.device_name = self._xem_.GetDeviceID()

        # same as self.xem.GetDeviceID()
        #self.board_name = self.ok.okCFrontPanel_GetBoardModelString(self.xem.GetBoardModel())

        with open(register_file, 'rU') as f:
            reader = csv.reader(f, delimiter=',')
            for row in reader:
                if len(row) > 0:
                    if row[0] is not '#':
                        self._registers_.append([row[1],
                                                row[2],
                                                int('0x%s' % row[3], 0),
                                                row[4],
                                                int(row[5]),
                                                row[6],
                                                row[7],
                                                row[8],
                                                row[9],
                                                int(row[10])])

        print('You are using: %s' % self.device_name)

    def set_register(self, register_name, register_value):
        """Set the 'register_value' to the OK register 'register_name'

        The 'register_name' must be one of the names specified in the csv input file"""
        register = []
        i = 0
        founded = False
        while i < len(self._registers_) and not founded:
            if self._registers_[i][3] == register_name:
                founded = True
                register = self._registers_[i]
            else:
                i += 1
        if isinstance(register_value, basestring):
            register_value = int(register_value, 0)
        elif isinstance(register_value, float):
            register_value = int(register_value)
        if founded is True:
            if register[0] == 'FromPC' and register[1] == 'Wire':
                if register_value > 2**register[4] - 1:
                    print('Warning: The register value exceed the maximum value')
                else:
                    a = register[2]
                    v = register_value << register[9]
                    m = 2 ** register[4] - 1 << register[9]
                    self._xem_.SetWireInValue(a, v, m)
                    self._xem_.UpdateWireIns()
            else:
                print(' Warning: the register selected is not to write')
        else:
            print(' Warning: Register name \'%s\' not found' % register_name)

    def get_register(self, register_name):
        """Return the value of the OK register 'register_name'

        The 'register_name' must be one of the names specified in the input csv configuration file"""
        register = []
        i = 0
        founded = False
        while i < len(self._registers_) and not founded:
            if self._registers_[i][3] == register_name:
                founded = True
                register = self._registers_[i]
            else:
                i += 1
        if founded is True:
            if register[0] == 'ToPC' and register[1] == 'Wire':
                self._xem_.UpdateWireOuts()
                return self._xem_.GetWireOutValue(register[2])
            else:
                print(' Warning: the register selected is not to read')
        else:
            print(' Warning: Register name \'%s\' not found' % register_name)

    def set_block_pipe(self, register_name):
        """Send a byte stream to the OK fifo

        Function not implemented yet
        """
        print(' Warning: Function not implemented yet')

    def get_block_pipe(self, register_name, data_length, block_size):
        """Read a byte stream from the OK fifo named 'register_name' in the input csv configuration file

        data_length = size of the byte stream per 16 bit data (2 bytes per data)
        block_size = size of the data packet from the OK over the USB connection
        """
        register = []
        i = 0
        founded = False
        while i < len(self._registers_) and not founded:
            if self._registers_[i][3] == register_name:
                founded = True
                register = self._registers_[i]
            else:
                i += 1
        if founded is True:
            if register[0] == 'ToPC' and register[1] == 'BTPipe':
                buf = bytearray(2*data_length)
                out_buf = self._xem_.ReadFromBlockPipeOut(register[2], block_size, buf)
                if out_buf < 0:
                    raise Exception('Opal Kelly error %s' % self._ok_errors_[out_buf])
                return buf
            else:
                print(' Warning: the stream selected is not to read')
        else:
            print(' Warning: Register name \'%s\' not found' % register_name)

    def get_pipe(self, register_name, data_length):
        """Read a byte stream from the OK fifo named 'register_name' in the input csv configuration file

        data_length = size of the byte stream per 16 bit data (2 bytes per data)

        Note: this function does not wait for a ready state to read the fifo
        """
        register = []
        i = 0
        founded = False
        while i < len(self._registers_) and not founded:
            if self._registers_[i][3] == register_name:
                founded = True
                register = self._registers_[i]
            else:
                i += 1
        if founded is True:
            if register[0] == 'ToPC' and register[1] == 'BTPipe':
                buf = bytearray(data_length*2)
                out_buf = self._xem_.ReadFromPipeOut(register[2], buf)
                if out_buf < 0:
                    raise Exception('Opal Kelly error %s' % self._ok_errors_[out_buf])
                return buf
            else:
                print(' Warning: the stream selected is not to read')
        else:
            print(' Warning: Register name \'%s\' not found' % register_name)

    def set_trigger(self, register_name):
        """Send a trigger to the OK of the register 'register_name'

        register_name = name of the register in the input csv configuration file
        """
        register = []
        i = 0
        founded = False
        while i < len(self._registers_) and not founded:
            if self._registers_[i][3] == register_name:
                founded = True
                register = self._registers_[i]
            else:
                i += 1
        if founded is True:
            if register[0] == 'FromPC' and register[1] == 'Trigger':
                a = register[2]
                m = register[9]
                self._xem_.ActivateTriggerIn(a, m)
            else:
                print(' Warning: the register selected is not to write')
        else:
            print(' Warning: Register name \'%s\' not found' % register_name)

    def get_trigger(self, register_name):
        """Check if a trigger occurred in the OK

        Note: Not implemented yet
        """
        print(' Warning: Function not implemented yet')

    def set_pll(self, pll_number, pll_p, pll_q, pll_enable):
        """Set the PLL parameters P, Q, Enable

        pll_number: which PLL to set
        pll_p: P factor
        pll_q: Q factor
        pll_enable: Enable the PLL

        Note: does not work
        """
        if pll_p < 6:
            raise Exception('PLL P parameter must be greater than 6')
        if pll_p > 2053:
            raise Exception('PLL P parameter must be smaller than 2053')
        if pll_q < 2:
            raise Exception('PLL Q parameter must be greater than 2')
        if pll_p > 257:
            raise Exception('PLL Q parameter must be smaller than 257')

        self._pll.SetPLLParameters(pll_number, pll_p, pll_q, pll_enable)
        if self._whichPLL_ == 'PLL22393':
            self._xem_.SetPLL22393Configuration(self._pll)
            self._xem_.SetEepromPLL22393Configuration(self._pll)
        elif self._whichPLL_ == 'PLL22150':
            self._xem_.SetPLL22150Configuration(self._pll)
            self._xem_.SetEepromPLL22150Configuration(self._pll)

        self._update_pll_()

    def get_pll(self, parameter):
        """Return a PLL or a SYSCLK parameter with the 'parameter'

        parameter (str): 'Crystal Frequency',
                         'PLL0 Frequency', 'PLL0 P', 'PLL0 Q', 'PLL0 Enable',
                         'PLL1 Frequency', 'PLL1 P', 'PLL1 Q', 'PLL1 Enable',
                         'PLL2 Frequency', 'PLL2 P', 'PLL2 Q', 'PLL2 Enable',
                         'SYSCLK1 Frequency', 'SYSCLK1 Source', 'SYSCLK1 Divider', 'SYSCLK1 Enable'
                         'SYSCLK2 Frequency', 'SYSCLK2 Source', 'SYSCLK2 Divider', 'SYSCLK2 Enable'
                         'SYSCLK3 Frequency', 'SYSCLK3 Source', 'SYSCLK3 Divider', 'SYSCLK3 Enable'
                         'SYSCLK4 Frequency', 'SYSCLK4 Source', 'SYSCLK4 Divider', 'SYSCLK4 Enable'
                         'SYSCLK5 Frequency', 'SYSCLK5 Source', 'SYSCLK5 Divider', 'SYSCLK5 Enable'
        """
        self._update_pll_()
        return self.pll_info[parameter]

    def set_sys_clk(self, sys_clk_number, sys_clk_source, sys_clk_divider, sys_clk_enable=True):
        """Set the clock of the OK

        sys_clk_number (1 to 5): select on of SYSCLK1 to SYSCLK5
        sys_clk_source (str: REF, PLL0-0, PLL0-180, PLL1-0, PLL1-180, PLL2-0, PLL2-180):
            set the source of the SYSCLK selected
        sys_clk_divider (int): specifies the frequency divider for the SYSCLK selected
        sys_clk_enable (boolean): enable/disable the SYSCLK selected

        Note: does not work
        """
        if sys_clk_divider > 127:
            raise Exception('Clock divider cannot be greater than 127')
        if sys_clk_divider < 0:
            raise Exception('Clock divider cannot be negative')
        if sys_clk_source not in self._clk_sources_.keys():
            raise Exception('Clock source must be chosen between these parameters: %s' %
                            'REF, PLL0-0, PLL0-180, PLL1-0, PLL1-180, PLL2-0, PLL2-180')
        if sys_clk_number == 5:
            warn('Ignoring the Clock source, SYS_CLK5 source it is fixed to PLL0-0')
        else:
            self._pll.SetOutputSource(sys_clk_number - 1, self._clk_sources_[sys_clk_source])
        self._pll.SetOutputDivider(sys_clk_number - 1, sys_clk_divider)
        self._pll.SetOutputEnable(sys_clk_number - 1, sys_clk_enable)
        self._update_pll_()

    def _update_pll_(self):
        """Update the _pll state

        Note: internal use only
        """

        if self._whichPLL_ == 'PLL22393':
            self._xem_.GetPLL22393Configuration(self._pll)
            self.pll_info = {'Crystal Frequency': self._pll.GetReference(),
                             'PLL0 Frequency': self._pll.GetPLLFrequency(0),
                             'PLL1 Frequency': self._pll.GetPLLFrequency(1),
                             'PLL2 Frequency': self._pll.GetPLLFrequency(2),
                             'PLL0 P': self._pll.GetPLLP(0),
                             'PLL1 P': self._pll.GetPLLP(1),
                             'PLL2 P': self._pll.GetPLLP(2),
                             'PLL0 Q': self._pll.GetPLLQ(0),
                             'PLL1 Q': self._pll.GetPLLQ(1),
                             'PLL2 Q': self._pll.GetPLLQ(2),
                             'PLL0 Enable': self._pll.IsPLLEnabled(0),
                             'PLL1 Enable': self._pll.IsPLLEnabled(1),
                             'PLL2 Enable': self._pll.IsPLLEnabled(2),
                             'SYSCLK1 Frequency': self._pll.GetOutputFrequency(0),
                             'SYSCLK2 Frequency': self._pll.GetOutputFrequency(1),
                             'SYSCLK3 Frequency': self._pll.GetOutputFrequency(2),
                             'SYSCLK4 Frequency': self._pll.GetOutputFrequency(3),
                             'SYSCLK5 Frequency': self._pll.GetOutputFrequency(4),
                             'SYSCLK1 Source': self._pll.GetOutputSource(0),
                             'SYSCLK2 Source': self._pll.GetOutputSource(1),
                             'SYSCLK3 Source': self._pll.GetOutputSource(2),
                             'SYSCLK4 Source': self._pll.GetOutputSource(3),
                             'SYSCLK5 Source': self._pll.GetOutputSource(4),
                             'SYSCLK1 Divider': self._pll.GetOutputDivider(0),
                             'SYSCLK2 Divider': self._pll.GetOutputDivider(1),
                             'SYSCLK3 Divider': self._pll.GetOutputDivider(2),
                             'SYSCLK4 Divider': self._pll.GetOutputDivider(3),
                             'SYSCLK5 Divider': self._pll.GetOutputDivider(4),
                             'SYSCLK1 Enable': self._pll.IsOutputEnabled(0),
                             'SYSCLK2 Enable': self._pll.IsOutputEnabled(1),
                             'SYSCLK3 Enable': self._pll.IsOutputEnabled(2),
                             'SYSCLK4 Enable': self._pll.IsOutputEnabled(3),
                             'SYSCLK5 Enable': self._pll.IsOutputEnabled(4),
                             }
        elif self._whichPLL_ == 'PLL22150':
            self._xem_.GetPLL22150Configuration(self._pll)
