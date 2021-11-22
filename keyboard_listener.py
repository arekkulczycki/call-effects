from pynput.keyboard import Key, Listener


class KeyboardListener:
    def run(self, queue):
        self.typing = False
        self.alt_held = False
        self.queue = queue

        with Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            print("keyboard listener started...")
            listener.join()

    def on_press(self, key):
        if key == Key.alt:
            self.alt_held = True

    def on_release(self, key):
        str_key = str(key)

        if key == Key.alt:
            self.alt_held = False

        elif self.alt_held and key not in (
            Key.shift,
            Key.alt,
            Key.ctrl,
            Key.cmd,
            Key.tab,
        ):
            self.queue.send(key)

        elif self.typing and (
            str_key.replace("'", "").isalpha()
            or str_key in ("'!'", "'?'", "Key.space", "Key.backspace")
        ):
            self.queue.send(key)

        if self.alt_held and str_key == "'t'":
            self.typing = True

        elif self.alt_held and key == Key.enter:
            self.typing = False
