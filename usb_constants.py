""" Constants for usb_comm.py file """

INFO_IN_ENDPOINT = 0x81
OUT_ENDPOINT = 2
DATA_STREAM_ENDPOINT = 0x83
USB_INFO_BYTES_SIZE = 5
USB_DATA_BYTE_SIZE = 64
USB_TERMINATION_SIGNAL = 255 * 257
USB_OUT_BYTE_SIZE = 32
TEST_MESSAGE = "USB Test"
RECIEVED_TEST_MESSAGE = b"USB Test - Plant_Acq"
TERMINATION_CODE = -16384

ADC_RESOLUTION = 14
MAX_16_BIT_VALUE = 2**16
MAX_ADC_COUNTS = 2 ** ADC_RESOLUTION
MAX_ADC_COUNTS_SATURATION = MAX_ADC_COUNTS * 1.2  # the saturation range is slightly larger
MAX_ADC_VOLTAGE = 2048

ADC_CHANNEL_DATA_SIZE = 4082
PACKETS_PER_CHANNEL = 64  # 2402 bytes / 64 bytes per packet

CALIBRATION_RANGE = 80  # mV
