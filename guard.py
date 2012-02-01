import sublime
import sublime_plugin
import thread
import subprocess
import os
import functools
import re

sublime_guard_controller = None


class GuardController(object):
    def __init__(self, listener):
        self.proc = None
        self.running = False
        self.listener = listener
        self.output_view = self.listener.window.get_output_panel('guard')
        self.enable_word_wrap()

    def open_file_paths(self):
        return [view.file_name() for view in self.listener.window.views() if view.file_name()]

    def open_folder_paths(self):
        return self.listener.window.folders()

    def path_has_guardfile(self, path):
        return os.path.exists(path + '/Guardfile')

    def path_has_gemfile(self, path):
        return os.path.exists(path + '/Gemfile')

    def find_project_root_path(self):
        project_root_path = None
        for path in self.open_folder_paths():
            print "Checking ... " + path
            if (self.path_has_guardfile(path) and self.path_has_gemfile(path)):
                project_root_path = path
                break
        return project_root_path

    def enable_word_wrap(self):
        self.output_view.settings().set("word_wrap", True)

    def start_guard(self):
        project_root_path = self.find_project_root_path()
        if (project_root_path == None):
            sublime.error_message("Failed to find Guardfile and Gemfile in any of the open folders.")
        else:
            package_path = sublime.packages_path()
            cmd_array = [package_path + "/Guard/guard_wrapper", package_path + "/Guard/run_guard.sh", project_root_path]
            self.proc = subprocess.Popen(cmd_array, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.running = True
            self.show_guard_view()
            if self.proc.stdout:
                thread.start_new_thread(self.read_stdout, ())
            if self.proc.stderr:
                thread.start_new_thread(self.read_stderr, ())

    def read_stdout(self):
        while True:
            data = os.read(self.proc.stdout.fileno(), 2 ** 15)
            if data != "":
                sublime.set_timeout(functools.partial(self.append_data, data), 0)
            else:
                self.proc.stdout.close()
                self.running = False
                break

    def read_stderr(self):
        while True:
            data = os.read(self.proc.stderr.fileno(), 2 ** 15)
            if data != "":
                sublime.set_timeout(functools.partial(self.append_data, data), 0)
            else:
                self.proc.stderr.close()
                self.running = False
                break

    def append_data(self, data):
        clean_data = data.decode("utf-8")
        clean_data = self.normalize_line_endings(clean_data)
        clean_data = self.remove_terminal_color_codes(clean_data)

        # actually append the data
        self.output_view.set_read_only(False)
        edit = self.output_view.begin_edit()
        self.output_view.insert(edit, self.output_view.size(), clean_data)

        # scroll to the end of the new insert
        self.scroll_to_end_of_guard_view()

        self.output_view.end_edit(edit)
        self.output_view.set_read_only(True)

    def normalize_line_endings(self, data):
        return data.replace('\r\n', '\n').replace('\r', '\n')

    def remove_terminal_color_codes(self, data):
        color_regex = re.compile("\\033\[[0-9;m]*", re.UNICODE)
        return color_regex.sub("", data)

    def scroll_to_end_of_guard_view(self):
        (cur_row, _) = self.output_view.rowcol(self.output_view.size())
        self.output_view.show(self.output_view.text_point(cur_row, 0))

    def show_guard_view(self):
        self.listener.window.run_command('show_panel', {'panel': 'output.guard'})

    def hide_guard_view(self):
        self.listener.window.run_command('hide_panel', {'panel': 'output.guard'})

    def stop_guard(self):
        self.proc.stdin.write('e\n')
        self.proc.stdin.flush()
        self.running = False

    def is_guard_running(self):
        return self.running

    def reload_guard(self):
        self.proc.stdin.write('r\n')
        self.proc.stdin.flush()

    def run_all_tests(self):
        self.proc.stdin.write('\n')
        self.proc.stdin.flush()

    def output_help(self):
        self.proc.stdin.write('h\n')
        self.proc.stdin.flush()

    def toggle_notifications(self):
        self.proc.stdin.write('n\n')
        self.proc.stdin.flush()

    def pause(self):
        self.proc.stdin.write('p\n')
        self.proc.stdin.flush()


def GuardControllerSingleton(listener):
    global sublime_guard_controller
    if sublime_guard_controller == None:
        sublime_guard_controller = GuardController(listener)
        return sublime_guard_controller
    else:
        return sublime_guard_controller


class StartGuardCommand(sublime_plugin.WindowCommand):

    def run(self):
        GuardControllerSingleton(self).start_guard()

    def is_enabled(self):
        return not GuardControllerSingleton(self).is_guard_running()


class StopGuardCommand(sublime_plugin.WindowCommand):

    def run(self):
        GuardControllerSingleton(self).stop_guard()

    def is_enabled(self):
        return GuardControllerSingleton(self).is_guard_running()


class HideGuardCommand(sublime_plugin.WindowCommand):

    def run(self):
        GuardControllerSingleton(self).hide_guard_view()

    def is_enabled(self):
        return True


class ShowGuardCommand(sublime_plugin.WindowCommand):

    def run(self):
        GuardControllerSingleton(self).show_guard_view()

    def is_enabled(self):
        return True


class ReloadGuardCommand(sublime_plugin.WindowCommand):

    def run(self):
        GuardControllerSingleton(self).reload_guard()

    def is_enabled(self):
        return GuardControllerSingleton(self).is_guard_running()


class RunAllTestsGuardCommand(sublime_plugin.WindowCommand):

    def run(self):
        GuardControllerSingleton(self).run_all_tests()

    def is_enabled(self):
        return GuardControllerSingleton(self).is_guard_running()


class OutputHelpGuardCommand(sublime_plugin.WindowCommand):

    def run(self):
        GuardControllerSingleton(self).output_help()

    def is_enabled(self):
        return GuardControllerSingleton(self).is_guard_running()


class ToggleNotificationsGuardCommand(sublime_plugin.WindowCommand):

    def run(self):
        GuardControllerSingleton(self).toggle_notifications()

    def is_enabled(self):
        return GuardControllerSingleton(self).is_guard_running()


class PauseGuardCommand(sublime_plugin.WindowCommand):

    def run(self):
        GuardControllerSingleton(self).pause()

    def is_enabled(self):
        return GuardControllerSingleton(self).is_guard_running()
