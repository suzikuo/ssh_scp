# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import curses
import json
with open("./ssh_commands.json","r",encoding="utf-8") as f:
    ssh_commands:dict = json.loads(f.read())
def main(stdscr):
    # 初始化
    curses.initscr()
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(100)
    stdscr.keypad(1)

    selected_option = 0
    flat = True
    while flat:
        stdscr.erase()
        # clear_screen(stdscr)

        # 显示菜单选项
        for i, key in enumerate(ssh_commands.keys()):
            option = key
            # option = f"{key}. {ssh_commands[key]}"
            if i == selected_option:
                stdscr.addstr(option, curses.A_REVERSE)
            else:
                stdscr.addstr(option)
            stdscr.addstr("\n")

        # 获取键盘输入
        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected_option = (selected_option - 1) % len(ssh_commands)
        elif key == curses.KEY_DOWN:
            selected_option = (selected_option + 1) % len(ssh_commands)
        elif key == ord('\n'):
            selected_key = list(ssh_commands.keys())[selected_option]
            ssh_command = ssh_commands[selected_key]
            curses.endwin()
            pem = ssh_command.get("pem",None)
            password = ssh_command.get("pwd","None")
            host = ssh_command["host"]
            if password:
                ssh = f"ssh {host}"
            if pem:
                ssh = f"ssh -i {pem} {host}"
            
            # 执行 SSH 命令
            import subprocess
            try:
                print(ssh)
                subprocess.call(ssh, shell=True)
            except Exception as e:
                print(e,111111111111111111111)
            flat = False
        elif key == ord('q'):
            flat = False
        else:
            selected_option = selected_option

def clear_screen(stdscr):
    stdscr.clear()
    stdscr.refresh()

# 在需要清屏的地方调用 clear_screen() 函数

# 在需要清屏的地方调用 clear_screen() 函数

if __name__ == "__main__":
    curses.wrapper(main)