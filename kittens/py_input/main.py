#!/usr/bin/env python3
# vim:fileencoding=utf-8
# License: GPL v3 Copyright: 2018, Kovid Goyal <kovid at kovidgoyal.net>

import os
import sys
import subprocess
from struct import pack, unpack  # NOQA

from kitty.constants import cache_dir

from ..tui.operations import alternate_screen, styled

readline = None


def get_history_items():
    return list(map(readline.get_history_item, range(1, readline.get_current_history_length() + 1)))


def sort_key(item):
    return len(item), item.lower()


class HistoryCompleter:

    def __init__(self, name=None):
        self.matches = []
        self.history_path = None
        if name:
            ddir = os.path.join(cache_dir(), 'py_input')
            try:
                os.makedirs(ddir)
            except FileExistsError:
                pass
            self.history_path = os.path.join(ddir, name)

    def complete(self, text, state):
        response = None
        if state == 0:
            history_values = get_history_items()
            if text:
                self.matches = sorted(
                        (h for h in history_values if h and h.startswith(text)), key=sort_key)
            else:
                self.matches = []
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        return response

    def __enter__(self):
        if self.history_path:
            if os.path.exists(self.history_path):
                readline.read_history_file(self.history_path)
            readline.set_completer(self.complete)
        return self

    def __exit__(self, *a):
        if self.history_path:
            readline.write_history_file(self.history_path)


def j(*arg):
    ls = []
    for a in arg:
        try:
            a = list(a)
            ls += a
        except Exception:
            ls += [a]
    return "".join([chr(c) if isinstance(c, int) else "%s" % c for c in ls])


def r(start, stop):
    return j([chr(i) for i in range(start, stop+1)])


def cmd(command):
    return subprocess.check_output(command).decode("utf-8")


def inp(fname):
    with open(os.path.expanduser(os.path.expandvars(fname)), "r") as f:
        return f.read()


def rlinput(prompt, prefill=''):
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    readline.redisplay()
    try:
        return input(prompt)
    finally:
        readline.set_startup_hook()


def main(args):
    # For some reason importing readline in a key handler in the main kitty process
    # causes a crash of the python interpreter, probably because of some global
    # lock
    global readline
    import readline as rl
    readline = rl
    from kitty.shell import init_readline

    init_readline(readline)

    error = None
    exc_type = None
    exc_value = None
    exc_traceback = None
    prompt_text = ""
    user_inp = '"'
    while True:
        with alternate_screen(), HistoryCompleter('py_input'):
            print(
                "Insert raw python commands to insert as text\n"
                "You can use the following shortcuts:\n"
                "%s Execute a shell-command\n"
                "%s Read file\n"
                "%s Join list\n"
                "%s Character range\n"
                % (
                    styled("cmd(<command>)   :\t", bold=True),
                    styled("inp(<filename>)  :\t", bold=True),
                    styled("j  (<list>)      :\t", bold=True),
                    styled("r  (start, stop) :\t", bold=True),
                  )
                )
            if error is not None:
                print(styled(error, bold=True))

            print(prompt_text)
            prompt_text = ""

            prompt = '> '
            try:
                user_inp = rlinput(prompt, prefill=user_inp)
            except (KeyboardInterrupt, EOFError):
                return ""
            if user_inp == "?":
                import traceback
                if error is not None:
                    prompt_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                continue

            try:
                response = eval(user_inp)
                return response
            except Exception as e:
                error = e
                exc_type, exc_value, exc_traceback = sys.exc_info()

    return response


def handle_result(args, text, target_window_id, boss):
    w = boss.window_id_map.get(target_window_id)
    if w is not None:
        w.paste(text)


if __name__ == '__main__':
    ans = main(sys.argv)
    if ans:
        print(ans)
