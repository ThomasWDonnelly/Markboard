import os
import tempfile
import threading
import subprocess
import sublime
import sublime_plugin
import markdown2
import MarkboardClippers

'''
    OS X docs: http://www.libertypages.com/clarktech/?p=3299
    Windows docs: http://code.activestate.com/recipes/474121-getting-html-from-the-windows-clipboard/
    Linux docs: http://www.pygtk.org/docs/pygtk/class-gtkclipboard.html#method-gtkclipboard--store
                http://developer.gnome.org/gtkmm/stable/classGtk_1_1Clipboard.html
                http://stackoverflow.com/questions/1992869/how-to-paste-html-to-clipboard-with-gtk
                http://gtk.php.net/manual/en/gtk.enum.targetflags.php
'''


def err(theError):
    print "[Markboard: " + theError + "]"


class markboardCopyFormattedCommand(sublime_plugin.TextCommand):
    """
        Renders the contents of the buffer in Markdown and copies
        the formatted text to the clipboard.
    """

    def run(self, edit):
        selections = self.view.sel()
        threads = []

        pandoc = sublime.load_settings("Markboard.sublime-settings").get("use_pandoc", False)
        env = os.environ.copy()
        env['PATH'] = env['PATH'] + ":" + sublime.load_settings("Markboard.sublime-settings").get("pandoc_path", "/usr/local/bin")

        f = tempfile.NamedTemporaryFile(mode="w+", suffix=".mdown", delete=False)
        self.globalWriter = f.name
        f.close()
        self.runningThreadBuffer = ""

        singleCursors = passedSelections = 0
        for theSelection in selections:
            theSubstring = self.view.substr(theSelection)
            if len(theSubstring) == 0:
                singleCursors += 1
            else:
                normalString = self.normalize_line_endings(theSubstring)
                f = open(self.globalWriter, "a")
                normalString = normalString.encode("utf-8")
                f.write(normalString + "\n\n")
                passedSelections += 1

        if singleCursors > 0 and passedSelections < 1:
            theBuffer = self.view.substr(sublime.Region(0, self.view.size()))
            normalString = self.normalize_line_endings(theBuffer)
            f = open(self.globalWriter, "a")
            normalString = normalString.encode("utf-8")
            f.write(normalString + "\n\n")

        newThread = MarkboardMarkdownProcessor(self.globalWriter) if not pandoc else MarkboardPandocMarkdownProcessor(self.globalWriter, self.view.window(), env)
        threads.append(newThread)
        newThread.start()

        self.manageThreads(threads)

    def manageThreads(self, theThreads, offset=0, i=0, direction=1):
        next_threads = []
        for aThread in theThreads:
            if aThread.is_alive():
                next_threads.append(aThread)
                continue
            self.runningThreadBuffer += "\n\n"
            self.runningThreadBuffer += aThread.result
        theThreads = next_threads

        if len(theThreads):
            before = i % 8
            after = 7 - before
            if not after:
                direction = -1
            if not before:
                direction = 1
            i += direction
            self.view.set_status("markboard", "Markdown markup... [%s=%s]" %
                                 (" " * before, " " * after))

            sublime.set_timeout(lambda: self.manageThreads(theThreads, offset, i, direction), 100)
            return
        clipObject = self.clipboardCopy()
        if clipObject:
            self.view.erase_status("markboard")
            sublime.status_message("Formatted text copied.")
        else:
            self.view.erase_status("markboard")
            sublime.status_message("Fatal error formatting text.")

    def normalize_line_endings(self, string):
        string = string.replace('\r\n', '\n').replace('\r', '\n')
        line_endings = self.view.settings().get('default_line_ending')
        if line_endings == 'windows':
            string = string.replace('\n', '\r\n')
        elif line_endings == 'mac':
            string = string.replace('\n', '\r')
        return string

    def clipboardCopy(self):
        plat = sublime.platform()
        if plat == "osx":
            return MarkboardClippers.OSXClipObject(self.runningThreadBuffer)
        if plat == "windows":
            return MarkboardClippers.WinClipObject(self.runningThreadBuffer)
        if plat == "linux":
            return MarkboardClippers.LinuxClipObject(self.runningThreadBuffer)


class MarkboardMarkdownProcessor(threading.Thread):
    def __init__(self, theFilename):
        self.myFilename = theFilename
        self.result = None
        threading.Thread.__init__(self)

    def run(self):
        extras = ["fenced-code-blocks", "footnotes", "smarty-pants"]
        self.result = markdown2.markdown_path(self.myFilename, extras=extras)


class MarkboardPandocMarkdownProcessor(threading.Thread):
    def __init__(self, theFilename, theWindow, env):
        self.myFilename = theFilename
        self.result = None
        self.window = theWindow
        self.env = env
        threading.Thread.__init__(self)

    def run(self):
        f = tempfile.NamedTemporaryFile(mode="w+", suffix=".html", delete=False)
        # f.write("\n")
        outFile = f.name
        f.close()
        cmd = ['pandoc', self.myFilename, '--output=%s' % outFile, '--from=markdown', '--to=html', '--smart', '--normalize']
        try:
            subprocess.call(cmd, env=self.env)
        except Exception as e:
            err("Exception: " + str(e))
            self.result = False
        else:
            f = open(outFile)
            self.result = f.read()
