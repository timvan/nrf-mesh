import sys

class StdioTest(object):

    def __init__(self):
        self.keep_runing = True
        self.n = 0

    def run(self):
        while self.keep_runing:
            msg = sys.stdin.readline()
            msg = msg.strip("\n")
            self.handle_message(msg)
            

    def handle_message(self, msg):
        if msg == "echo":
            self.send_message("hiii")

        sys.stdout.flush()

    def send_message(self, msg):
        print("Py TX{}: {}".format(self.n, msg))
        self.n += 1
        sys.stdout.flush()

if __name__ == "__main__":
    s = StdioTest()
    s.run()
