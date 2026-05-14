#!/bin/bash
caffeinate -d &
CAFF_PID=$!
trap "kill $CAFF_PID" EXIT INT TERM

while true; do
    python3 - <<'EOF'
import ctypes, sys, subprocess

class _CGPoint(ctypes.Structure):
    _fields_ = [('x', ctypes.c_double), ('y', ctypes.c_double)]

# 1. IOKit — resets IOKit-level idle timer
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
name = cf.CFStringCreateWithCString(None, b"MSTeamsWaker", 0x08000100)  # kCFStringEncodingUTF8
if name:
    try:
        assertion_id = ctypes.c_uint32(0)
        iokit.IOPMAssertionDeclareUserActivity(name, 0, ctypes.byref(assertion_id))  # kIOPMUserActiveLocal
    finally:
        cf.CFRelease(name)

# 2 & 3. CoreGraphics — session-level post + direct-to-Teams post
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
cg.CGEventPostToPid.restype = None
cg.CGEventPostToPid.argtypes = [ctypes.c_int32, ctypes.c_void_p]
cg.CFRelease.restype = None
cg.CFRelease.argtypes = [ctypes.c_void_p]

try:
    teams_pids = [int(p) for p in subprocess.check_output(
        ['pgrep', '-if', 'microsoft teams'], text=True, timeout=2
    ).split() if p.strip().isdigit()]
except Exception:
    teams_pids = []

source = cg.CGEventSourceCreate(1)  # kCGEventSourceStateCombinedSessionState
if not source:
    sys.exit(1)
try:
    temp = cg.CGEventCreate(None)
    if not temp:
        sys.exit(1)
    point = cg.CGEventGetLocation(temp)
    cg.CFRelease(temp)
    point.x += 1  # non-zero delta avoids zero-move filtering
    event = cg.CGEventCreateMouseEvent(source, 5, point, 0)  # kCGEventMouseMoved
    if not event:
        sys.exit(1)
    try:
        cg.CGEventPost(1, event)  # kCGSessionEventTap — no Accessibility needed
        for pid in teams_pids:
            cg.CGEventPostToPid(pid, event)  # direct into Teams' Electron event queue
    finally:
        cg.CFRelease(event)
finally:
    cg.CFRelease(source)
EOF
    echo "Activity signal sent"
    sleep 240
done
