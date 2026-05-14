#!/bin/bash
caffeinate -d &
CAFF_PID=$!
trap "kill $CAFF_PID" EXIT INT TERM

while true; do
    python3 - <<'EOF'
import ctypes, sys

class _CGPoint(ctypes.Structure):
    _fields_ = [('x', ctypes.c_double), ('y', ctypes.c_double)]

# IOKit — primary: resets the idle state Teams actually monitors
iokit = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/IOKit.framework/IOKit')
cf = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
cf.CFStringCreateWithCString.restype = ctypes.c_void_p
cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
cf.CFRelease.restype = None
cf.CFRelease.argtypes = [ctypes.c_void_p]
iokit.IOPMAssertionDeclareUserActivity.restype = ctypes.c_uint32
iokit.IOPMAssertionDeclareUserActivity.argtypes = [
    ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)
]
name = cf.CFStringCreateWithCString(None, b"MSTeamsWaker", 0x08000100)
if name:
    assertion_id = ctypes.c_uint32(0)
    iokit.IOPMAssertionDeclareUserActivity(name, 0, ctypes.byref(assertion_id))
    cf.CFRelease(name)

# CoreGraphics — secondary: resets CGEvent idle timer
cg = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
cg.CGEventCreate.restype = ctypes.c_void_p
cg.CGEventCreate.argtypes = [ctypes.c_void_p]
cg.CGEventGetLocation.restype = _CGPoint
cg.CGEventGetLocation.argtypes = [ctypes.c_void_p]
cg.CGEventSourceCreate.restype = ctypes.c_void_p
cg.CGEventSourceCreate.argtypes = [ctypes.c_int]
cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p
cg.CGEventCreateMouseEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint32, _CGPoint, ctypes.c_uint32]
cg.CGEventPost.restype = None
cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
cg.CFRelease.restype = None
cg.CFRelease.argtypes = [ctypes.c_void_p]

source = cg.CGEventSourceCreate(1)
if not source:
    sys.exit(1)
try:
    temp = cg.CGEventCreate(None)
    if not temp:
        sys.exit(1)
    point = cg.CGEventGetLocation(temp)
    cg.CFRelease(temp)
    event = cg.CGEventCreateMouseEvent(source, 5, point, 0)
    if not event:
        sys.exit(1)
    try:
        cg.CGEventPost(0, event)
    finally:
        cg.CFRelease(event)
finally:
    cg.CFRelease(source)
EOF
    echo "Activity signal sent"
    sleep 300
done
