#
# libupddapi bindings for Python

import ctypes
import platform

if platform.system() == "Windows":
    upddSharedLibraryPath = "C:/Program Files/UPDD/upddapi.dll"
elif platform.system() == "Linux":
    upddSharedLibraryPath = "/opt/updd/usrlib/libupddapi.so"
elif platform.system() == "Darwin":
    upddSharedLibraryPath = "/Library/Application Support/UPDD/libupddapi.7.0.0.dylib"
else:
    raise OSError(f"Unsupported platform: {platform.system()}")


_EventTypeXY = 0x0001  #  pointer co-ordinates
_EventTypeEval = 0x0002  #  change in evaluation state
_EventTypeRaw = 0x0008  #  raw data
_EventTypeToolbar = 0x0010  #  toolbar events
_EventConfiguration = 0x0020  #  OBSOLESCENT - typo for _EventTypeConfiguration, this value will be removed in due course
_EventTypeConfiguration = 0x0020  #  notifications of changes to driver configuration and state
_EventTypeRelative = 0x0100  #  notifications of relative movement
_EventTypeUnload = 0x0200  #  the driver is about to attempt an unload
_EventTypeXYNoMask = 0x1000  #  same as _EventTypeXY but not masked by toolbars and surrounds used for calibration  -- WAS _EventTypeXYCal prior to V6
_EventTypeInteractiveTouch = 0x4000  #  mouse pointer state events for interactive touch mode
_EventTypeGesture = 0x8000
_EventTypePlayUPDDSound = 0x800000  #  play a sound defined for this device
_EventTypeMouseEvent = 0x1000000  #  raw data sent to mouse port
_EventTypeSecBlock = 0x2000000  #  touch data was received when a security block was in place
_EventTypeRawMouse = 0x8000000  #  internal use only
_EventTypeLogicalEvent = 0x20000000  #  state changes passed to operating system
_EventTypePhysicalEvent = 0x40000000  #  changes in the actual "touching" state OBSOLESCENT
_EventTypeDigitiserEvent = 0x4000000

_EventTypeFlagsEvent = 0x80000000  #  EVNN / L / R bits OBSOLESCENT

CONFIG_EVENT_SETTINGS = 1  #  one or more updd settings have been changed
CONFIG_EVENT_CONCURRENCY_SIGNAL = 2  #  a signal was requested by a call to TBApiRegisterProgram
CONFIG_EVENT_CONNECT = 3  #  a client connection to the driver has been established
CONFIG_EVENT_DISCONNECT = 4  #  the client connection to the driver has disconnected
CONFIG_EVENT_UNLOAD = (
    5  #  the driver has requested termination of this application, typically for uninstallation
)
CONFIG_EVENT_DEVICE = 6  #  notification of a change in physical device state
CONFIG_EVENT_AUTOCONFIGURE = 7  #  an auto configure operation has been triggered
CONFIG_EVENT_CONCURRENCY_CHANGE = (
    8  #  a program was registered with TBApiRegisterProgram or deregistered
)
CONFIG_EVENT_MONITOR_DETECT = 9  #  sent at beginning and end of a monitor detection sequence
CONFIG_EVENT_INTERNAL = 10  #  reserved for internal use
CONFIG_EVENT_DEVICE_BIND = 11  #  notification of a change in logical device state
CONFIG_EVENT_INTERNAL_2 = 12  #  reserved for internal use

TOUCH_BIT_FLAGS_LEFT = 0x1
TOUCH_BIT_FLAGS_RIGHT = 0x2
TOUCH_BIT_FLAGS_IN_RANGE = 0x8

PEN_BIT_FLAGS_TIP = 0x1
PEN_BIT_FLAGS_BARREL = 0x2
PEN_BIT_FLAGS_ERASER = 0x4
PEN_BIT_FLAGS_IN_RANGE = 0x8
PEN_BIT_FLAGS_INVERT = 0x10

DIGITIZER_TYPE_PEN = 0x2
DIGITIZER_TYPE_TOUCH = 0x4

TB_INVALID_HANDLE_VALUE = 0x00

MAXSTYLENAME = 32
MAXCALPOINTS = 25

INJECT_FLAG_IGNORE_MP_DISABLED = 2
INJECT_FLAG_GENERATE_POINTER_EVENTS = 4
INJECT_FLAG_GENERATE_COMPATIBILITY_EVENTS = 8
INJECT_FLAG_INTERNAL_COORDINATES = 16
INJECT_FLAG_RAW_COORDINATES = 32
INJECT_FLAG_NOT_LAST_CONTACT = 64

NOTIFY_LEVEL_OTHER = 0
NOTIFY_LEVEL_CONFIG_WARNINGS = 1
NOTIFY_LEVEL_EVAL_AND_CRITICAL = 2


libupddapi = ctypes.CDLL(upddSharedLibraryPath)


class struct__PointerEvent(ctypes.Structure):
    pass


class union__pe(ctypes.Union):
    pass


class struct__digitiserEvent(ctypes.Structure):
    pass


class union__de(ctypes.Union):
    pass


class struct__penEvent(ctypes.Structure):
    pass


struct__penEvent._pack_ = 1  # source:False
struct__penEvent._fields_ = [
    ("tipSwitch", ctypes.c_ubyte, 1),
    ("barrelSwitch", ctypes.c_ubyte, 1),
    ("invert", ctypes.c_ubyte, 1),
    ("inrange", ctypes.c_ubyte, 1),
    ("eraser", ctypes.c_ubyte, 1),
    ("reserved2", ctypes.c_ubyte, 1),
    ("reserved3", ctypes.c_ubyte, 1),
    ("reserved4", ctypes.c_ubyte, 1),
    ("reserved5", ctypes.c_uint32),
]


class struct__touchEvent(ctypes.Structure):
    pass


struct__touchEvent._pack_ = 1  # source:False
struct__touchEvent._fields_ = [
    ("touchingLeft", ctypes.c_ubyte, 1),
    ("touchingRight", ctypes.c_ubyte, 1),
    ("unused", ctypes.c_ubyte, 1),
    ("inrange", ctypes.c_ubyte, 1),
    ("PADDING_0", ctypes.c_uint8, 4),
]

union__de._pack_ = 1  # source:False
union__de._fields_ = [
    ("penEvent", struct__penEvent),
    ("touchEvent", struct__touchEvent),
    ("PADDING_0", ctypes.c_ubyte * 4),
]

struct__digitiserEvent._pack_ = 1  # source:False
struct__digitiserEvent._fields_ = [
    ("de", union__de),
    ("deltaBits", ctypes.c_ubyte),
    ("validBits", ctypes.c_ubyte),
    ("screenx", ctypes.c_int32),
    ("screeny", ctypes.c_int32),
    ("internalx", ctypes.c_int32),
    ("internaly", ctypes.c_int32),
    ("calx", ctypes.c_int32),
    ("caly", ctypes.c_int32),
    ("zSupport", ctypes.c_uint16),
    ("z", ctypes.c_uint32),
    ("isTimed", ctypes.c_uint16),
    ("isToolbar", ctypes.c_uint16),
    ("stylusSupport", ctypes.c_uint16),
    ("digitizerType", ctypes.c_ubyte),
    ("lastContact", ctypes.c_uint16),
    ("internal_event_number", ctypes.c_int32),
    ("contact_width", ctypes.c_uint32),
    ("contact_height", ctypes.c_uint32),
    ("xtilt", ctypes.c_byte),
    ("ytilt", ctypes.c_byte),
    ("rawx", ctypes.c_int32),
    ("rawy", ctypes.c_int32),
]


class struct__xy(ctypes.Structure):
    pass


struct__xy._pack_ = 1  # source:False
struct__xy._fields_ = [
    ("rawx", ctypes.c_int32),
    ("rawy", ctypes.c_int32),
    ("calx", ctypes.c_int32),
    ("caly", ctypes.c_int32),
    ("calx_rotated", ctypes.c_int32),
    ("caly_rotated", ctypes.c_int32),
    ("screenx", ctypes.c_int32),
    ("screeny", ctypes.c_int32),
    ("internalx", ctypes.c_int32),
    ("internaly", ctypes.c_int32),
]


class struct__z(ctypes.Structure):
    pass


struct__z._pack_ = 1  # source:False
struct__z._fields_ = [
    ("rawz", ctypes.c_uint32),
]


class struct__logicalEvent(ctypes.Structure):
    pass


struct__logicalEvent._pack_ = 1  # source:False
struct__logicalEvent._fields_ = [
    ("left", ctypes.c_uint16),
    ("state", ctypes.c_uint16),
    ("timed", ctypes.c_uint16),
]


class struct__physicalEvent(ctypes.Structure):
    pass


struct__physicalEvent._pack_ = 1  # source:False
struct__physicalEvent._fields_ = [
    ("state", ctypes.c_uint16),
    ("timed", ctypes.c_uint16),
]


class struct__raw(ctypes.Structure):
    pass


struct__raw._pack_ = 1  # source:False
struct__raw._fields_ = [
    ("byte", ctypes.c_ubyte * 64),
]


class struct__toolbar(ctypes.Structure):
    pass


struct__toolbar._pack_ = 1  # source:False
struct__toolbar._fields_ = [
    ("htoolbar", ctypes.c_int16),
    ("row", ctypes.c_int16),
    ("column", ctypes.c_int16),
    ("touching", ctypes.c_ubyte),
    ("on", ctypes.c_ubyte),
]


class struct__interactiveTouch(ctypes.Structure):
    pass


struct__interactiveTouch._pack_ = 1  # source:False
struct__interactiveTouch._fields_ = [
    ("ticks", ctypes.c_uint32),
    ("maxTicks", ctypes.c_uint32),
]


class struct__sound(ctypes.Structure):
    pass


struct__sound._pack_ = 1  # source:False
struct__sound._fields_ = [
    ("file", ctypes.c_uint32),
    ("reserved1", ctypes.c_uint32),
    ("reserved2", ctypes.c_uint32),
]


class struct__eval(ctypes.Structure):
    pass


struct__eval._pack_ = 1  # source:False
struct__eval._fields_ = [
    ("clicksRemaining", ctypes.c_uint16),
    ("packageExpired", ctypes.c_uint32),
]


class struct__config(ctypes.Structure):
    pass


class union__ce(ctypes.Union):
    pass


union__ce._pack_ = 1  # source:False
union__ce._fields_ = [
    ("configText", ctypes.c_ubyte * 60),
    ("signalValue", ctypes.c_uint32),
    ("PADDING_0", ctypes.c_ubyte * 56),
]


class struct__internal(ctypes.Structure):
    pass


struct__internal._pack_ = 1  # source:False
struct__internal._fields_ = [
    ("v1", ctypes.c_uint32),
    ("v2", ctypes.c_uint32),
    ("v3", ctypes.c_uint32),
]

struct__config._pack_ = 1  # source:False
struct__config._fields_ = [
    ("configEventType", ctypes.c_uint16),
    ("configEventLevel", ctypes.c_uint16),
    ("ce", union__ce),
    ("internal", struct__internal),
    ("originatingPID", ctypes.c_int64),
]

union__pe._pack_ = 1  # source:False
union__pe._fields_ = [
    ("digitiserEvent", struct__digitiserEvent),
    ("xy", struct__xy),
    ("z", struct__z),
    ("logicalEvent", struct__logicalEvent),
    ("physicalEvent", struct__physicalEvent),
    ("raw", struct__raw),
    ("toolbar", struct__toolbar),
    ("interactiveTouch", struct__interactiveTouch),
    ("sound", struct__sound),
    ("eval", struct__eval),
    ("config", struct__config),
]

struct__PointerEvent._pack_ = 1  # source:False
struct__PointerEvent._fields_ = [
    ("hDevice", ctypes.c_ubyte),
    ("hStylus", ctypes.c_ubyte),
    ("type", ctypes.c_uint64),
    ("length", ctypes.c_uint64),
    ("touchDelegated", ctypes.c_ubyte),
    ("usbConfiguration", ctypes.c_ubyte),
    ("usbInterface", ctypes.c_ubyte),
    ("hidEndpoint", ctypes.c_ubyte),
    ("hidReportid", ctypes.c_ubyte),
    ("calibrating", ctypes.c_ubyte),
    ("monitor_number", ctypes.c_ubyte),
    ("timestamp", ctypes.c_uint32),
    ("priority", ctypes.c_ubyte),
    ("reserved_byte", ctypes.c_ubyte * 2),
    ("reserved", ctypes.c_uint32 * 14),
    ("pe", union__pe),
]

_PointerEvent = struct__PointerEvent


class struct__HIDPacket(ctypes.Structure):
    pass


class union__h(ctypes.Union):
    pass


class struct__touch(ctypes.Structure):
    pass


class struct__contact(ctypes.Structure):
    pass


struct__contact._pack_ = 1  # source:False
struct__contact._fields_ = [
    ("touching", ctypes.c_ubyte, 1),
    ("unused", ctypes.c_ubyte, 2),
    ("contact_number", ctypes.c_ubyte, 5),
    ("x", ctypes.c_uint16),
    ("unused_2", ctypes.c_uint16),
    ("y", ctypes.c_uint16),
    ("w", ctypes.c_uint16),
    ("h", ctypes.c_uint16),
]

struct__touch._pack_ = 1  # source:False
struct__touch._fields_ = [
    ("contact", struct__contact * 5),
    ("scan_rate", ctypes.c_ubyte),
    ("unused", ctypes.c_ubyte),
    ("contact_count", ctypes.c_ubyte),
]


class struct__pen(ctypes.Structure):
    pass


struct__pen._pack_ = 1  # source:False
struct__pen._fields_ = [
    ("in_range", ctypes.c_ubyte, 1),
    ("invert", ctypes.c_ubyte, 1),
    ("unused", ctypes.c_ubyte, 1),
    ("eraser", ctypes.c_ubyte, 1),
    ("barrel", ctypes.c_ubyte, 1),
    ("tip", ctypes.c_ubyte, 1),
    ("PADDING_0", ctypes.c_uint8, 2),
    ("x", ctypes.c_uint16),
    ("y", ctypes.c_uint16),
    ("z", ctypes.c_uint16),
    ("unused_2", ctypes.c_uint16),
    ("dummy", ctypes.c_ubyte * 10),
]


class struct__touch_mouse(ctypes.Structure):
    pass


struct__touch_mouse._pack_ = 1  # source:False
struct__touch_mouse._fields_ = [
    ("button_left", ctypes.c_ubyte, 1),
    ("button_right", ctypes.c_ubyte, 1),
    ("button_middle", ctypes.c_ubyte, 1),
    ("unused", ctypes.c_ubyte, 5),
    ("x", ctypes.c_uint16),
    ("y", ctypes.c_uint16),
]


class struct__regular_mouse(ctypes.Structure):
    pass


struct__regular_mouse._pack_ = 1  # source:False
struct__regular_mouse._fields_ = [
    ("button_left", ctypes.c_ubyte, 1),
    ("button_right", ctypes.c_ubyte, 1),
    ("button_middle", ctypes.c_ubyte, 1),
    ("unused", ctypes.c_ubyte, 5),
    ("x", ctypes.c_ubyte, 8),
    ("y", ctypes.c_byte),
]


class struct__keyboard(ctypes.Structure):
    pass


struct__keyboard._pack_ = 1  # source:False
struct__keyboard._fields_ = [
    ("modifier_lctrl", ctypes.c_ubyte, 1),
    ("modifier_lshift", ctypes.c_ubyte, 1),
    ("modifier_lalt", ctypes.c_ubyte, 1),
    ("modifier_lmeta", ctypes.c_ubyte, 1),
    ("modifier_rctrl", ctypes.c_ubyte, 1),
    ("modifier_rshift", ctypes.c_ubyte, 1),
    ("modifier_ralt", ctypes.c_ubyte, 1),
    ("modifier_rmeta", ctypes.c_ubyte, 1),
    ("unused", ctypes.c_ubyte, 8),
    ("key", ctypes.c_ubyte * 6),
    ("unused2", ctypes.c_ubyte * 50),
]

union__h._pack_ = 1  # source:False
union__h._fields_ = [
    ("touch", struct__touch),
    ("pen", struct__pen),
    ("touch_mouse", struct__touch_mouse),
    ("regular_mouse", struct__regular_mouse),
    ("keyboard", struct__keyboard),
]

struct__HIDPacket._pack_ = 1  # source:False
struct__HIDPacket._fields_ = [
    ("report_id", ctypes.c_ubyte),
    ("h", union__h),
]

_HIDPacket = struct__HIDPacket
TB_EVENT_CALL = ctypes.CFUNCTYPE(None, ctypes.c_uint64, ctypes.POINTER(struct__PointerEvent))
TB_EVENT_CALL_SOURCE = ctypes.CFUNCTYPE(None, ctypes.POINTER(struct__PointerEvent))
try:
    TBApiOpen = libupddapi.TBApiOpen
    TBApiOpen.restype = None
    TBApiOpen.argtypes = []
except AttributeError:
    pass
try:
    TBApiClose = libupddapi.TBApiClose
    TBApiClose.restype = None
    TBApiClose.argtypes = []
except AttributeError:
    pass
uint16_t = ctypes.c_uint16
try:
    TBApiIsDriverConnected = libupddapi.TBApiIsDriverConnected
    TBApiIsDriverConnected.restype = uint16_t
    TBApiIsDriverConnected.argtypes = []
except AttributeError:
    pass
try:
    TBApiIsDriverConnectedNoDispatch = libupddapi.TBApiIsDriverConnectedNoDispatch
    TBApiIsDriverConnectedNoDispatch.restype = uint16_t
    TBApiIsDriverConnectedNoDispatch.argtypes = []
except AttributeError:
    pass
try:
    TBApiGetDriverVersion = libupddapi.TBApiGetDriverVersion
    TBApiGetDriverVersion.restype = uint16_t
    TBApiGetDriverVersion.argtypes = [ctypes.POINTER(ctypes.c_char)]
except AttributeError:
    pass
try:
    TBApiGetApiVersion = libupddapi.TBApiGetApiVersion
    TBApiGetApiVersion.restype = None
    TBApiGetApiVersion.argtypes = [ctypes.POINTER(ctypes.c_char)]
except AttributeError:
    pass
try:
    TBApiGetRelativeDevice = libupddapi.TBApiGetRelativeDevice
    TBApiGetRelativeDevice.restype = ctypes.c_ubyte
    TBApiGetRelativeDevice.argtypes = [ctypes.c_int32]
except AttributeError:
    pass
try:
    TBApiGetRelativeDeviceFromHandle = libupddapi.TBApiGetRelativeDeviceFromHandle
    TBApiGetRelativeDeviceFromHandle.restype = ctypes.c_int32
    TBApiGetRelativeDeviceFromHandle.argtypes = [ctypes.c_ubyte]
except AttributeError:
    pass
try:
    TBApiGetRelativeDeviceExcludeHidden = libupddapi.TBApiGetRelativeDeviceExcludeHidden
    TBApiGetRelativeDeviceExcludeHidden.restype = ctypes.c_ubyte
    TBApiGetRelativeDeviceExcludeHidden.argtypes = [ctypes.c_int32]
except AttributeError:
    pass
try:
    TBApiGetRotate = libupddapi.TBApiGetRotate
    TBApiGetRotate.restype = uint16_t
    TBApiGetRotate.argtypes = [ctypes.c_ubyte, ctypes.POINTER(ctypes.c_int32)]
except AttributeError:
    pass
try:
    TBApiMousePortInterfaceEnable = libupddapi.TBApiMousePortInterfaceEnable
    TBApiMousePortInterfaceEnable.restype = uint16_t
    TBApiMousePortInterfaceEnable.argtypes = [ctypes.c_ubyte, uint16_t]
except AttributeError:
    pass
try:
    TBApiRegisterEvent = libupddapi.TBApiRegisterEvent
    TBApiRegisterEvent.restype = uint16_t
    TBApiRegisterEvent.argtypes = [ctypes.c_ubyte, ctypes.c_uint64, ctypes.c_uint64, TB_EVENT_CALL]
except AttributeError:
    pass
try:
    TBApiUnregisterEvent = libupddapi.TBApiUnregisterEvent
    TBApiUnregisterEvent.restype = uint16_t
    TBApiUnregisterEvent.argtypes = [TB_EVENT_CALL]
except AttributeError:
    pass
try:
    TBApiUnregisterEventContext = libupddapi.TBApiUnregisterEventContext
    TBApiUnregisterEventContext.restype = uint16_t
    TBApiUnregisterEventContext.argtypes = [ctypes.c_uint64]
except AttributeError:
    pass
try:
    TBApiGetSetting = libupddapi.TBApiGetSetting
    TBApiGetSetting.restype = uint16_t
    TBApiGetSetting.argtypes = [
        ctypes.c_ubyte,
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_int32,
    ]
except AttributeError:
    pass
try:
    TBApiGetSettingAsInt = libupddapi.TBApiGetSettingAsInt
    TBApiGetSettingAsInt.restype = uint16_t
    TBApiGetSettingAsInt.argtypes = [
        ctypes.c_ubyte,
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_int32),
    ]
except AttributeError:
    pass
try:
    TBApiSetSetting = libupddapi.TBApiSetSetting
    TBApiSetSetting.restype = uint16_t
    TBApiSetSetting.argtypes = [
        ctypes.c_ubyte,
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        uint16_t,
    ]
except AttributeError:
    pass
int32_t = ctypes.c_int32
try:
    TBApiSetSettingFromInt = libupddapi.TBApiSetSettingFromInt
    TBApiSetSettingFromInt.restype = uint16_t
    TBApiSetSettingFromInt.argtypes = [
        ctypes.c_ubyte,
        ctypes.POINTER(ctypes.c_char),
        int32_t,
        uint16_t,
    ]
except AttributeError:
    pass
try:
    TBApiSetDefault = libupddapi.TBApiSetDefault
    TBApiSetDefault.restype = uint16_t
    TBApiSetDefault.argtypes = [
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
    ]
except AttributeError:
    pass
try:
    TBApiGetControllerSetting = libupddapi.TBApiGetControllerSetting
    TBApiGetControllerSetting.restype = uint16_t
    TBApiGetControllerSetting.argtypes = [
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_int32,
    ]
except AttributeError:
    pass
try:
    TBApiGetBootstrapSetting = libupddapi.TBApiGetBootstrapSetting
    TBApiGetBootstrapSetting.restype = None
    TBApiGetBootstrapSetting.argtypes = [
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_int32,
    ]
except AttributeError:
    pass
try:
    TBApiRemove = libupddapi.TBApiRemove
    TBApiRemove.restype = uint16_t
    TBApiRemove.argtypes = [ctypes.c_ubyte, ctypes.POINTER(ctypes.c_char)]
except AttributeError:
    pass
try:
    TBApiGetSettingSize = libupddapi.TBApiGetSettingSize
    TBApiGetSettingSize.restype = uint16_t
    TBApiGetSettingSize.argtypes = [
        ctypes.c_ubyte,
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_int32),
    ]
except AttributeError:
    pass
try:
    TBApiGetControllerSettingSize = libupddapi.TBApiGetControllerSettingSize
    TBApiGetControllerSettingSize.restype = uint16_t
    TBApiGetControllerSettingSize.argtypes = [
        ctypes.c_ubyte,
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_int32),
    ]
except AttributeError:
    pass
try:
    TBApiAddDevice = libupddapi.TBApiAddDevice
    TBApiAddDevice.restype = uint16_t
    TBApiAddDevice.argtypes = [
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_ubyte),
    ]
except AttributeError:
    pass
try:
    TBApiDeleteDevice = libupddapi.TBApiDeleteDevice
    TBApiDeleteDevice.restype = uint16_t
    TBApiDeleteDevice.argtypes = [ctypes.c_ubyte]
except AttributeError:
    pass
try:
    TBApiEnableApiTrace = libupddapi.TBApiEnableApiTrace
    TBApiEnableApiTrace.restype = None
    TBApiEnableApiTrace.argtypes = [uint16_t]
except AttributeError:
    pass
try:
    TBApiPostPacketBytes = libupddapi.TBApiPostPacketBytes
    TBApiPostPacketBytes.restype = uint16_t
    TBApiPostPacketBytes.argtypes = [ctypes.c_ubyte, ctypes.POINTER(ctypes.c_char)]
except AttributeError:
    pass
uint32_t = ctypes.c_uint32
try:
    TBApiPostPacketBytesEx = libupddapi.TBApiPostPacketBytesEx
    TBApiPostPacketBytesEx.restype = uint16_t
    TBApiPostPacketBytesEx.argtypes = [ctypes.c_ubyte, ctypes.POINTER(ctypes.c_char), uint32_t]
except AttributeError:
    pass
try:
    TBApiInjectTouch = libupddapi.TBApiInjectTouch
    TBApiInjectTouch.restype = uint16_t
    TBApiInjectTouch.argtypes = [
        ctypes.c_ubyte,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        uint16_t,
    ]
except AttributeError:
    pass
try:
    TBApiGetMonitorMetricsForMonitor = libupddapi.TBApiGetMonitorMetricsForMonitor
    TBApiGetMonitorMetricsForMonitor.restype = uint16_t
    TBApiGetMonitorMetricsForMonitor.argtypes = [
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_int64),
        ctypes.POINTER(ctypes.c_int64),
        ctypes.POINTER(ctypes.c_int64),
        ctypes.POINTER(ctypes.c_int64),
    ]
except AttributeError:
    pass
try:
    TBApiGetLastError = libupddapi.TBApiGetLastError
    TBApiGetLastError.restype = None
    TBApiGetLastError.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.c_int32]
except AttributeError:
    pass
try:
    TBApiRegisterProgram = libupddapi.TBApiRegisterProgram
    TBApiRegisterProgram.restype = uint16_t
    TBApiRegisterProgram.argtypes = [ctypes.POINTER(ctypes.c_char), uint16_t, uint16_t, uint16_t]
except AttributeError:
    pass
uint8_t = ctypes.c_uint8
try:
    TBApiRegisterProgramEx = libupddapi.TBApiRegisterProgramEx
    TBApiRegisterProgramEx.restype = uint16_t
    TBApiRegisterProgramEx.argtypes = [
        ctypes.POINTER(ctypes.c_char),
        uint16_t,
        uint16_t,
        uint16_t,
        uint8_t,
    ]
except AttributeError:
    pass
try:
    TBApiLicence = libupddapi.TBApiLicence
    TBApiLicence.restype = uint16_t
    TBApiLicence.argtypes = [ctypes.POINTER(ctypes.c_char)]
except AttributeError:
    pass
try:
    TBApiPostPointerEvent = libupddapi.TBApiPostPointerEvent
    TBApiPostPointerEvent.restype = uint16_t
    TBApiPostPointerEvent.argtypes = [ctypes.POINTER(struct__PointerEvent)]
except AttributeError:
    pass
try:
    TBApiIsDeviceConnected = libupddapi.TBApiIsDeviceConnected
    TBApiIsDeviceConnected.restype = uint16_t
    TBApiIsDeviceConnected.argtypes = [ctypes.c_ubyte, ctypes.POINTER(ctypes.c_uint16)]
except AttributeError:
    pass
try:
    TBApiHidSetFeature = libupddapi.TBApiHidSetFeature
    TBApiHidSetFeature.restype = uint16_t
    TBApiHidSetFeature.argtypes = [ctypes.c_ubyte, ctypes.c_int32, ctypes.POINTER(None), uint32_t]
except AttributeError:
    pass
try:
    TBApiHidGetFeature = libupddapi.TBApiHidGetFeature
    TBApiHidGetFeature.restype = uint16_t
    TBApiHidGetFeature.argtypes = [ctypes.c_ubyte, ctypes.c_int32, ctypes.POINTER(None), uint32_t]
except AttributeError:
    pass
try:
    TBApiGetSettings = libupddapi.TBApiGetSettings
    TBApiGetSettings.restype = uint16_t
    TBApiGetSettings.argtypes = [
        ctypes.c_ubyte,
        uint16_t,
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_int32),
    ]
except AttributeError:
    pass
try:
    TBApiGetSettingHelp = libupddapi.TBApiGetSettingHelp
    TBApiGetSettingHelp.restype = uint16_t
    TBApiGetSettingHelp.argtypes = [
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_int32),
    ]
except AttributeError:
    pass
try:
    TBApiCalibrate = libupddapi.TBApiCalibrate
    TBApiCalibrate.restype = uint16_t
    TBApiCalibrate.argtypes = [ctypes.c_ubyte, ctypes.c_int32, ctypes.POINTER(ctypes.c_char)]
except AttributeError:
    pass
try:
    TBApiExportSettings = libupddapi.TBApiExportSettings
    TBApiExportSettings.restype = uint16_t
    TBApiExportSettings.argtypes = [
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        uint16_t,
    ]
except AttributeError:
    pass
try:
    TBApiImportSettings = libupddapi.TBApiImportSettings
    TBApiImportSettings.restype = uint16_t
    TBApiImportSettings.argtypes = [ctypes.POINTER(ctypes.c_char)]
except AttributeError:
    pass
try:
    TBApiGetSettingByIndex = libupddapi.TBApiGetSettingByIndex
    TBApiGetSettingByIndex.restype = uint16_t
    TBApiGetSettingByIndex.argtypes = [
        ctypes.c_ubyte,
        ctypes.POINTER(ctypes.c_char),
        uint16_t,
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_int32,
    ]
except AttributeError:
    pass
try:
    TBApiResetSettings = libupddapi.TBApiResetSettings
    TBApiResetSettings.restype = uint16_t
    TBApiResetSettings.argtypes = []
except AttributeError:
    pass
int16_t = ctypes.c_int16
try:
    TBApiGetRelativeToolbar = libupddapi.TBApiGetRelativeToolbar
    TBApiGetRelativeToolbar.restype = int16_t
    TBApiGetRelativeToolbar.argtypes = [ctypes.c_int32]
except AttributeError:
    pass
try:
    TBApiAddToolbar = libupddapi.TBApiAddToolbar
    TBApiAddToolbar.restype = int16_t
    TBApiAddToolbar.argtypes = [
        ctypes.POINTER(ctypes.c_char),
        uint16_t,
        uint16_t,
        uint16_t,
        uint16_t,
    ]
except AttributeError:
    pass
try:
    TBApiRemoveToolbar = libupddapi.TBApiRemoveToolbar
    TBApiRemoveToolbar.restype = uint16_t
    TBApiRemoveToolbar.argtypes = [int16_t]
except AttributeError:
    pass
try:
    TBApiGetToolbarSetting = libupddapi.TBApiGetToolbarSetting
    TBApiGetToolbarSetting.restype = uint16_t
    TBApiGetToolbarSetting.argtypes = [
        int16_t,
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_int32,
    ]
except AttributeError:
    pass
try:
    TBApiGetToolbarSettingAsInt = libupddapi.TBApiGetToolbarSettingAsInt
    TBApiGetToolbarSettingAsInt.restype = uint16_t
    TBApiGetToolbarSettingAsInt.argtypes = [
        int16_t,
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_int32),
    ]
except AttributeError:
    pass
try:
    TBApiSetToolbarSetting = libupddapi.TBApiSetToolbarSetting
    TBApiSetToolbarSetting.restype = uint16_t
    TBApiSetToolbarSetting.argtypes = [
        int16_t,
        ctypes.POINTER(ctypes.c_char),
        ctypes.POINTER(ctypes.c_char),
    ]
except AttributeError:
    pass
try:
    TBApiEnableToolbars = libupddapi.TBApiEnableToolbars
    TBApiEnableToolbars.restype = uint16_t
    TBApiEnableToolbars.argtypes = [int16_t]
except AttributeError:
    pass
try:
    TBApiDisableToolbars = libupddapi.TBApiDisableToolbars
    TBApiDisableToolbars.restype = uint16_t
    TBApiDisableToolbars.argtypes = [int16_t]
except AttributeError:
    pass
try:
    TBApiPostHIDPacket = libupddapi.TBApiPostHIDPacket
    TBApiPostHIDPacket.restype = uint16_t
    TBApiPostHIDPacket.argtypes = [ctypes.c_ubyte, uint16_t, ctypes.POINTER(struct__HIDPacket)]
except AttributeError:
    pass
__all__ = [
    "TBApiAddDevice",
    "TBApiAddToolbar",
    "TBApiCalibrate",
    "TBApiClose",
    "TBApiDeleteDevice",
    "TBApiDisableToolbars",
    "TBApiEnableApiTrace",
    "TBApiEnableToolbars",
    "TBApiExportSettings",
    "TBApiGetApiVersion",
    "TBApiGetBootstrapSetting",
    "TBApiGetControllerSetting",
    "TBApiGetControllerSettingSize",
    "TBApiGetDriverVersion",
    "TBApiGetLastError",
    "TBApiGetMonitorMetricsForMonitor",
    "TBApiGetRelativeDevice",
    "TBApiGetRelativeDeviceExcludeHidden",
    "TBApiGetRelativeDeviceFromHandle",
    "TBApiGetRelativeToolbar",
    "TBApiGetRotate",
    "TBApiGetSetting",
    "TBApiGetSettingAsInt",
    "TBApiGetSettingByIndex",
    "TBApiGetSettingHelp",
    "TBApiGetSettingSize",
    "TBApiGetSettings",
    "TBApiGetToolbarSetting",
    "TBApiGetToolbarSettingAsInt",
    "TBApiHidGetFeature",
    "TBApiHidSetFeature",
    "TBApiImportSettings",
    "TBApiInjectTouch",
    "TBApiIsDeviceConnected",
    "TBApiIsDriverConnected",
    "TBApiIsDriverConnectedNoDispatch",
    "TBApiLicence",
    "TBApiMousePortInterfaceEnable",
    "TBApiOpen",
    "TBApiPostHIDPacket",
    "TBApiPostPacketBytes",
    "TBApiPostPacketBytesEx",
    "TBApiPostPointerEvent",
    "TBApiRegisterEvent",
    "TBApiRegisterProgram",
    "TBApiRegisterProgramEx",
    "TBApiRemove",
    "TBApiRemoveToolbar",
    "TBApiResetSettings",
    "TBApiSetDefault",
    "TBApiSetSetting",
    "TBApiSetSettingFromInt",
    "TBApiSetToolbarSetting",
    "TBApiUnregisterEvent",
    "TBApiUnregisterEventContext",
    "TB_EVENT_CALL",
    "TB_EVENT_CALL_SOURCE",
    "_HIDPacket",
    "_PointerEvent",
    "int16_t",
    "int32_t",
    "struct__HIDPacket",
    "struct__PointerEvent",
    "struct__config",
    "struct__contact",
    "struct__digitiserEvent",
    "struct__eval",
    "struct__interactiveTouch",
    "struct__internal",
    "struct__keyboard",
    "struct__logicalEvent",
    "struct__pen",
    "struct__penEvent",
    "struct__physicalEvent",
    "struct__raw",
    "struct__regular_mouse",
    "struct__sound",
    "struct__toolbar",
    "struct__touch",
    "struct__touchEvent",
    "struct__touch_mouse",
    "struct__xy",
    "struct__z",
    "uint16_t",
    "uint32_t",
    "uint8_t",
    "union__ce",
    "union__de",
    "union__h",
    "union__pe",
]


# Some convenience functions:

# Hangs on to references to the callbacks so that Python doesn't deallocate
# them:
_callbacks = {}


def create_event_callback(func):
    """Sets up a ctypes callback for func, that will receive for its second
    parameter a _PointerEvent struct rather than a _PointerEvent pointer,
    in order to avoid potential crashes with memory being deallocated"""
    if func in _callbacks:
        return _callbacks[func][1]

    def closure(eventType, eventPtr):
        event = _PointerEvent()
        ctypes.pointer(event)[0] = eventPtr[0]
        func(eventType, event)

    ret = (closure, TB_EVENT_CALL(closure))
    _callbacks[func] = ret
    return ret[1]


def create_event_callback_async(async_func, event_loop=None):
    """Sets up a ctypes callback for async_func, an asynchronous function,
    that will be called on the given event_loop, or the current event loop
    if event_loop is None, and receive for its second parameter a
    _PointerEvent struct rather than a _PointerEvent pointer, in order to
    avoid potential crashes with memory being deallocated"""
    import asyncio

    if async_func in _callbacks:
        return _callbacks[async_func][1]

    if event_loop is None:
        event_loop = asyncio.get_running_loop()

    def closure(eventType, eventPtr):
        event = _PointerEvent()
        ctypes.pointer(event)[0] = eventPtr[0]
        event_loop.call_soon_threadsafe(asyncio.create_task, async_func(eventType, event))

    ret = (closure, TB_EVENT_CALL(closure))
    _callbacks[async_func] = ret
    return ret[1]
