#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import subprocess
import platform


def run_node_watch():
    """Run 'npm run watch' to compile CSS and JS in the background."""
    try:
        # Check the operating system to run in the background correctly
        if platform.system() == 'Windows':
            # On Windows, we use 'start' to open a new process
            subprocess.Popen(['start', 'npm', 'run', 'build:all'], shell=True)
        else:
            # On Unix systems (Linux, Mac), we use '&' to run in the background
            subprocess.Popen(['npm', 'run', 'build:all'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print(f"Error running npm commands: {e}")


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hivik2.settings')

    # if 'runserver' in sys.argv:
    #     # If the command is 'runserver', also run 'npm run watch:css' and 'npm run watch:js'
    #     run_node_watch()

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
