try:
    from Foundation import *
    from AppKit import *
except ImportError:
    pass
try:
    import winClip
except ImportError:
    pass
try:
    import gtk
except ImportError:
    pass


class OSXClipObject(object):
    def __init__(self, theData):
        pasteboard = NSPasteboard.generalPasteboard()
        typeArray = NSArray.arrayWithObject_(NSHTMLPboardType)
        pasteboard.declareTypes_owner_(typeArray, None)
        pasteboard.setString_forType_(theData, NSHTMLPboardType)


class WinClipObject(object):
    def __init__(self, theData):
        winClip.putHTML(theData)


class LinuxClipObject(object):
    def __init__(self, theData):
        clip = gtk.Clipboard()
        clip.set_can_store(None)
        target = "text/html"
        flags = gtk.TARGET_SAME_APP
        integerID = 80085
        self.myData = theData
        clip.set_with_data((target, flags, integerID), self.returnStringData, self.clearTheClipboard, None)

    def returnStringData(clipboard, selectionData, info, data):
        selectionData.set("CLIPBOARD", 8, self.myData)

    def clearTheClipboard(clipboard, data):
        clipboard.clear()
