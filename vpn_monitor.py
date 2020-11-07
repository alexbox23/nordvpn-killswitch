"""Script for monitoring the connection status of the NordVPN Linux app.

The Linux app's Kill Switch feature disables system-wide internet access if the
VPN disconnects, but that prevents remote access. This script implements a
targeted kill switch to only stop certain processes, and restart them once the
VPN reconnects.
"""
import os
import re
import signal
import subprocess
import time


class Sentry:
    """Class for monitoring VPN status and arranging for certain processes to
    run iff the VPN is connected.
    """

    def __init__(self):
        # Time in seconds to check VPN status.
        self.poll_rate = 20

        # List of commands that should only be run under VPN.
        self.command_list = ['deluged', 'deluge-web']

        # Store the subprocess.Popen object for each command so that when
        # the process dies, the zombie process can be cleared.
        self.processes = {}

    def connect_vpn(self):
        """Run `nordvpn c`."""
        subprocess.call(['nordvpn', 'c'])

    def check_vpn(self):
        """Run `nordvpn status` and parse console output.

        Returns:
            bool: True if connected.
        """
        result = subprocess.run(['nordvpn', 'status'], stdout=subprocess.PIPE)
        output = result.stdout.decode('utf-8')

        match = re.search(r"Status: (\w+)", output)
        groups = () if match is None else match.groups()

        return "Connected" in groups

    def parse_ps(self):
        """Parse the output of `ps -x` for known commands.

        Returns:
            dict: A map where keys are the command strings and values are lists
                of integers for every pid matching the command.
        """
        command_pids = {}
        processes_found = []

        result = subprocess.run(['ps', '-x'], stdout=subprocess.PIPE)
        output = result.stdout.decode('utf-8')

        for line in output.split('\n'):
            match = re.fullmatch(r"^\s*(\d+) (.*)$", line)
            if match:
                pid, details = match.groups()
                pid = int(pid)

                for cmd in self.command_list:
                    if cmd in details:
                        processes_found.append((cmd, pid, details))

        for cmd, pid, details in processes_found:
            if "<defunct>" in details and cmd in self.processes:
                # Kill zombie processes.
                self.processes[cmd].wait()
                self.processes.pop(cmd)
            else:
                if cmd in command_pids:
                    command_pids[cmd].append(pid)
                else:
                    command_pids[cmd] = [pid]

        return command_pids

    def run_commands(self):
        """Run the commands."""
        running_cmds = self.parse_ps().keys()

        for cmd in self.command_list:
            if cmd not in running_cmds:
                print("Starting %s..." % cmd)
                self.processes[cmd] = subprocess.Popen(cmd)

    def kill_processes(self):
        """Kill the processes."""
        command_pids = self.parse_ps()
        for cmd in command_pids:
            print("Killing {}{}...".format(cmd, command_pids[cmd]))
            for pid in command_pids[cmd]:
                os.kill(pid, signal.SIGKILL)

    def loop(self):
        """Main loop for polling VPN status."""
        connected = False

        while True:
            if self.check_vpn():
                if not connected:
                    connected = True
                    print("Connected to VPN.")

                self.run_commands()

                time.sleep(self.poll_rate)
            else:
                if connected:
                    connected = False
                    print("VPN disconnected.")

                self.kill_processes()

                print("Connecting to VPN...")
                self.connect_vpn()

    def run(self):
        """Start the loop, and kill processes if the loop breaks."""
        try:
            self.loop()
        finally:
            print("Loop terminated.")
            self.kill_processes() 


def main():
    sentry = Sentry()
    sentry.run()


if __name__ == '__main__':
    main()

