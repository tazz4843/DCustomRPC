# coding=utf-8
import time
import pypresence
import ruamel.yaml
import os
import logging
import threading
import webbrowser
import requests
from io import StringIO
# Imports go here.

# Imports tkinter if it can.
try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    tk = messagebox = None

# Tries to import PIL and pystray.
try:
    import pystray
    from PIL import Image
except ImportError:
    pystray = Image = None

cycle = True
# Sets whether we are cycling games.


class ConfigNotFound(Exception):
    pass
# The config not found exception.


class ConfigOpenError(Exception):
    pass
# The exception when the config cannot be opened.


class ClientIDNotProvided(Exception):
    pass
# The exception when a client ID is not provided.


def dict2class(_dict: dict):
    class DictBasedClass:
        def __getattribute__(self, item):
            self.__getattr__(item)

    for key in _dict:
        setattr(DictBasedClass, key, _dict[key])

    return DictBasedClass
# Converts a dictionary to a class.


def load_config(config_location: str):
    if not os.path.isfile(config_location):
        raise ConfigNotFound(
            "Could not find the config."
        )

    try:
        with open(config_location, "r", encoding="utf8") as file_stream:
            loaded_file = ruamel.yaml.load(file_stream, Loader=ruamel.yaml.Loader)
    except ruamel.yaml.YAMLError:
        raise ConfigOpenError(
            "The YAML config seems to be malformed."
        )
    except FileNotFoundError:
        raise ConfigNotFound(
            "Could not find the config."
        )
    except IOError:
        raise ConfigOpenError(
            "Could not open the config file."
        )

    return dict2class(loaded_file)
# Loads the config.


logger = logging.getLogger("dcustomrpc")
# Sets the logger.


current_dir = os.path.dirname(os.path.abspath(__file__))
# The current_dir folder for DCustomRPC.


# Tries to show a error.
def try_show_error_box(exception):
    if tk:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "DCustomRPC", "{}".format(exception)
        )


def listening_sleeper(_time):
    global cycle
    ticks = _time / 0.1
    count = 0
    while cycle and count != ticks:
        try:
            time.sleep(0.1)
            count += 1
        except KeyboardInterrupt:
            cycle = False
            return
# Listens and sleeps.


log_stream = StringIO()
# The stream of the logger.


def main():
    logging.basicConfig(
        level=logging.INFO
    )

    formatting = logging.Formatter(
        "%(levelname)s:%(name)s:%(message)s"
    )

    log = logging.StreamHandler(log_stream)
    log.setLevel(logging.INFO)
    log.setFormatter(formatting)
    logger.addHandler(log)

    logger.info("Loading the config.")
    config = load_config(current_dir + "/config.yaml")

    try:
        client_id = config.client_id
    except AttributeError:
        raise ClientIDNotProvided(
            "No client ID was provided in the config."
        )

    try:
        game_cycle = config.game_cycle
        logger.info("Found a list of games to cycle.")
    except AttributeError:
        game_cycle = {
            "time_until_cycle": 10,
            "games": [
                {
                    "state": "No cycle found.",
                    "details": "Nothing to cycle."
                }
            ]
        }

    if config.enable_tray_icon:
        tray = TrayIcon()
        tray.start()

    if not config.enable_gui:
        # noinspection PyGlobalUndefined
        global tk
        # noinspection PyGlobalUndefined
        global messagebox
        tk = messagebox = None

    client = pypresence.Presence(
        client_id,
        pipe=0
    )

    logger.info("Connecting the client.")
    while True:
        try:
            client.connect()
        except Exception as e:
            logger.exception("Failed to connect! Waiting 5 seconds.", exc_info=e)
            time.sleep(5)
        else:
            logger.info("Connected!")
            break

    try:
        games = game_cycle.get("games", [
                {
                    "state": "No cycle found.",
                    "details": "Nothing to cycle."
                }
        ])
        time_until_cycle = game_cycle.get(
            "time_until_cycle", 10)
        while cycle:
            for game in games:
                if not cycle:
                    break

                try:
                    client.update(**game)
                    logger.info("Changed the game.")
                    listening_sleeper(time_until_cycle)
                except TypeError:
                    logger.error("The game is formatted wrong.")

        client.close()
    except Exception as e:
        try_show_error_box(e)
        logger.exception(e)
        # ignore and pass
# The main script that is executed.


class TrayIcon(threading.Thread):
    # Initialises the thread.
    def __init__(self):
        super().__init__()
        self.daemon = True

    # Exits the application.
    @staticmethod
    def exit_app():
        global cycle
        cycle = False

    # Displays logs from the past 15 minutes.
    @staticmethod
    def display_logs():
        post = requests.post(
            "https://hastebin.com/documents",
            data=log_stream.getvalue()
        )
        webbrowser.open(
            "https://hastebin.com/" +
            post.json()["key"] + ".txt"
        )

    # The main function.
    def main_function(self):
        image = Image.open(current_dir + "/logo.ico")

        menu = pystray.Menu(
            pystray.MenuItem(
                "Exit", self.exit_app
            ),
            pystray.MenuItem(
                "Show Logs", self.display_logs
            )
        )

        tray_icon = pystray.Icon(
            "DCustomRPC", image,
            "DCustomRPC", menu
        )

        # noinspection PyUnusedLocal
        def setup(icon):
            tray_icon.visible = True

        tray_icon.run(setup)

    # Tries to launch the task tray.
    def run(self):
        # noinspection PyBroadException
        try:
            self.main_function()
        except Exception:
            pass


# Flushes the log every 15 minutes.
def flush_log_every_15_minutes():
    while True:
        time.sleep(900)
        log_stream.truncate(0)
        log_stream.seek(0)


if __name__ == '__main__':
    threading.Thread(
        target=flush_log_every_15_minutes,
        daemon=True
    ).start()

    try:
        main()
    except Exception as exc:
        try_show_error_box(exc)
        logger.exception(exc)
# Starts the script.
